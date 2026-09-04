"""
Sandbox orchestrator for Hyper-τ.

Manages the full lifecycle of a sandbox-mode evaluation:

1. Build a developer kit from a HyperTask.
2. Optionally run a Client interaction phase (text briefing).
3. Launch a SandboxBuilder to modify the kit.
4. Collect the submission (the kit directory after the builder finishes).
5. Score the submission using the inner-loop τ-bench evaluator.
6. Return an OuterLoopResult.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from statistics import mean
from typing import Optional

from loguru import logger

from tau2.data_model.tasks import Task
from tau2.hyper._inner import run_inner_simulations
from tau2.hyper.agent_context import constraints_allow, resolve_stock_constraints
from tau2.hyper.client import ClientContext
from tau2.hyper.client_api import CLIENT_API_CONTRACT_VERSION
from tau2.hyper.client_api.capabilities import (
    CapabilityDeploymentSession,
    DeploymentSnapshot,
    empty_deployment_snapshot,
)
from tau2.hyper.client_api.runtime import create_domain_client_api_runtime
from tau2.hyper.data_model import (
    HyperTask,
    OuterLoopResult,
    OuterLoopStep,
)
from tau2.hyper.live_experiment import (
    LiveExperimentContext,
    SampleScenariosContext,
    format_live_experiment_results,
    format_sample_scenario_results,
)
from tau2.hyper.performance import evaluate_performance_requirements
from tau2.hyper.response_phrasing import (
    apply_response_phrasing_rule_pack_to_tasks,
    load_selected_response_phrasing_rule_pack_for_task,
)
from tau2.hyper.run_defaults import (
    DEFAULT_AGENT_LLM,
    DEFAULT_CLIENT_LLM,
    DEFAULT_CLIENT_REASONING_EFFORT,
    DEFAULT_USER_LLM,
    DEFAULT_USER_REASONING_EFFORT,
    resolve_simulator_llm_args,
)
from tau2.hyper.runtime_contract import (
    CONSTRUCTION_RUNTIME_CONTRACT_VERSION,
    DEFAULT_CONSTRUCTION_RUNTIME_IMAGE,
)
from tau2.hyper.sandbox.builder import BuildBudget, SandboxBuilder
from tau2.hyper.sandbox.kit import build_kit
from tau2.hyper.sandbox.sealed_runner import (
    SealedCandidateEnvironment,
    SealedRunnerConfig,
    create_sealed_candidate_agent,
)
from tau2.hyper.sandbox.starting_workspace import contamination_patterns
from tau2.run import get_tasks as get_inner_loop_tasks
from tau2.runner.build import load_tasks_from_file

# In-world neutral: the kit's git identity is Developer-visible (git log),
# so it must not name the benchmark or harness.
_KIT_BASELINE_MESSAGE = "Initial import"


def _get_git_sha() -> Optional[str]:
    """Return the current repository commit SHA when available."""
    repo_root = Path(__file__).resolve().parents[4]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def initialize_kit_repository(kit_path: Path) -> str:
    """Create the single developer-visible baseline commit for a kit.

    Generated kits intentionally expose only files already present in the kit,
    never the benchmark repository's upstream history. An explicit kit path
    that already contains Git metadata is rejected rather than overwritten.
    """
    kit_path = Path(kit_path).resolve()
    if (kit_path / ".git").exists():
        raise ValueError(f"Kit already contains Git metadata: {kit_path}")

    commands = (
        ["git", "init", "--initial-branch", "main"],
        ["git", "config", "user.name", "Workspace"],
        ["git", "config", "user.email", "workspace@localhost"],
        ["git", "add", "--all"],
        [
            "git",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--no-gpg-sign",
            "-m",
            _KIT_BASELINE_MESSAGE,
        ],
    )
    for command in commands:
        result = subprocess.run(
            command,
            cwd=kit_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"Failed to initialize kit Git baseline: {detail}")

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=kit_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _hash_file(path: Path) -> str:
    """Compute a SHA-256 hash for a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _classify_workspace_provenance(
    kit_path: Path, baseline_commit: Optional[str]
) -> tuple[Optional[dict[str, str]], list[str]]:
    """Classify workspace files against the kit's baseline commit.

    Returns ``(provenance, deleted)`` where ``provenance`` maps kit-relative
    paths of files present on disk to ``"baseline"`` (shipped in the kit and
    untouched), ``"modified"``, or ``"new"``, and ``deleted`` lists baseline
    files the Developer removed. Seeded (brownfield) kits ship a non-empty
    workspace in the baseline commit, so "under workspace/" no longer implies
    "Developer-authored" — this classification is what separates the shipped
    starting code from the Developer's delta. Returns ``(None, [])`` when git
    provenance is unavailable (no baseline commit, or git failed).
    """
    if baseline_commit is None:
        return None, []

    def _run_git(*args: str) -> Optional[str]:
        result = subprocess.run(
            ["git", *args],
            cwd=kit_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logger.warning(
                f"Workspace provenance git call failed ({args[0]}): "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
            return None
        return result.stdout

    diff_output = _run_git(
        "diff", "--name-status", "--no-renames", baseline_commit, "--", "workspace"
    )
    untracked_output = _run_git(
        "ls-files", "--others", "--exclude-standard", "--", "workspace"
    )
    if diff_output is None or untracked_output is None:
        return None, []

    provenance: dict[str, str] = {}
    deleted: list[str] = []
    for line in diff_output.splitlines():
        if not line.strip():
            continue
        status, _, path = line.partition("\t")
        if not path:
            continue
        if status.startswith("D"):
            deleted.append(path)
        elif status.startswith("A"):
            provenance[path] = "new"
        else:
            provenance[path] = "modified"
    for path in untracked_output.splitlines():
        if path.strip():
            provenance[path.strip()] = "new"
    return provenance, sorted(deleted)


def _build_artifact_manifest(
    kit_path: Path, baseline_commit: Optional[str] = None
) -> list[dict]:
    """Build a manifest of workspace artifacts with per-file provenance.

    Every file present under ``workspace/`` is listed; when a baseline commit
    is available each entry carries ``provenance`` (baseline/modified/new)
    and baseline files the Developer deleted appear as explicit
    ``provenance: deleted`` entries.
    """
    workspace = kit_path / "workspace"
    if not workspace.exists():
        return []

    provenance, deleted = _classify_workspace_provenance(kit_path, baseline_commit)

    manifest = []
    for path in sorted(p for p in workspace.rglob("*") if p.is_file()):
        rel = path.relative_to(kit_path).as_posix()
        try:
            stat = path.stat()
            entry = {
                "path": rel,
                "size_bytes": stat.st_size,
                "sha256": _hash_file(path),
            }
        except OSError as e:
            entry = {"path": rel, "error": str(e)}
        if provenance is not None:
            entry["provenance"] = provenance.get(rel, "baseline")
        manifest.append(entry)
    for rel in deleted:
        manifest.append({"path": rel, "provenance": "deleted"})
    return manifest


def _build_contamination_report(
    kit_path: Path, domain: str, baseline_commit: Optional[str] = None
) -> dict:
    """Scan workspace files for obvious reference-domain leakage.

    When baseline provenance is available the scan covers only the
    Developer's delta (modified + new files): shipped starting-workspace
    files are gated for contamination at corpus-authoring time, and unseeded
    kits' baseline files are generated stubs. Without provenance the scan
    falls back to the full workspace.
    """
    workspace = kit_path / "workspace"
    # Canonical pattern list shared with the authoring-time gate on starting
    # workspaces: baseline files skipped here in delta mode were scanned
    # against the same patterns when the workspace was authored.
    patterns = contamination_patterns(domain)
    matches: list[dict] = []

    if not workspace.exists():
        return {"status": "workspace_missing", "patterns": patterns, "matches": []}

    provenance, _ = _classify_workspace_provenance(kit_path, baseline_commit)
    scope = "full" if provenance is None else "delta"
    skipped_baseline_files = 0

    for path in sorted(p for p in workspace.rglob("*") if p.is_file()):
        rel = path.relative_to(kit_path).as_posix()
        if provenance is not None and provenance.get(rel, "baseline") == "baseline":
            skipped_baseline_files += 1
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            for pattern in patterns:
                if pattern in line:
                    matches.append(
                        {
                            "path": rel,
                            "line": line_no,
                            "pattern": pattern,
                            "excerpt": line.strip()[:500],
                        }
                    )

    return {
        "status": "matches_found" if matches else "clean",
        "scope": scope,
        "skipped_baseline_files": skipped_baseline_files,
        "patterns": patterns,
        "matches": matches,
    }


class SandboxOrchestrator:
    """Orchestrator for sandbox-mode Hyper-τ evaluations.

    This orchestrator:

    1. Builds a self-contained kit directory from the task.
    2. Hands the kit to a :class:`SandboxBuilder` (LLM with file tools,
       subprocess to claude CLI, etc.).
    3. After the builder finishes, reads the modified kit and scores the
       result against final scoring tasks.

    The scoring pipeline uses :func:`run_inner_simulations` from
    :mod:`tau2.hyper._inner` to evaluate the sealed candidate.

    Args:
        task: The HyperTask to evaluate.
        builder: The SandboxBuilder implementation to use.
        agent_llm: LLM for inner-loop agent simulations.
        user_llm: LLM for inner-loop user simulations.
        agent_llm_args: Additional LLM kwargs for inner-loop agent.
        user_llm_args: Additional LLM kwargs for inner-loop user.
        budget: Budget constraints for the builder.
        kit_dir: Explicit directory for the kit. If None, a temp dir
            is used and cleaned up after.
        keep_kit: If True, don't clean up the kit directory after.
    """

    def __init__(
        self,
        task: HyperTask,
        builder: SandboxBuilder,
        *,
        client_llm: str = DEFAULT_CLIENT_LLM,
        client_llm_args: Optional[dict] = None,
        agent_llm: str = DEFAULT_AGENT_LLM,
        user_llm: str = DEFAULT_USER_LLM,
        agent_llm_args: Optional[dict] = None,
        allowed_agent_models: Optional[list[dict]] = None,
        user_llm_args: Optional[dict] = None,
        budget: Optional[BuildBudget] = None,
        kit_dir: Optional[Path] = None,
        keep_kit: bool = False,
    ):
        self.task = task
        self.builder = builder
        self.client_llm = client_llm
        self.client_llm_args = client_llm_args
        self.agent_llm = agent_llm
        self.user_llm = user_llm
        self.agent_llm_args = agent_llm_args
        self.allowed_agent_models = allowed_agent_models
        self.user_llm_args = user_llm_args
        self.budget = budget or BuildBudget()
        self.kit_dir = Path(kit_dir) if kit_dir else None
        self.keep_kit = keep_kit
        self._client_context: Optional[ClientContext] = None
        self._capability_session: Optional[CapabilityDeploymentSession] = None
        self._deployment_snapshot: Optional[DeploymentSnapshot] = None

    @classmethod
    def from_task(
        cls,
        task: HyperTask,
        builder: SandboxBuilder,
        *,
        client_llm: Optional[str] = None,
        client_llm_args: Optional[dict] = None,
        agent_llm: Optional[str] = None,
        user_llm: Optional[str] = None,
        agent_llm_args: Optional[dict] = None,
        user_llm_args: Optional[dict] = None,
        allowed_agent_models_override: Optional[list[dict]] = None,
        budget: Optional[BuildBudget] = None,
        kit_dir: Optional[Path] = None,
        keep_kit: bool = False,
    ) -> "SandboxOrchestrator":
        """Create a SandboxOrchestrator from a HyperTask.

        Construction tasks describe custom-agent inference through
        ``allowed_agent_models``. A concrete model is derived only for the
        stock-agent fallback. Explicit ``agent_llm`` arguments remain a
        single-model run override at this outer boundary. An
        ``allowed_agent_models_override`` narrows the models exposed to the
        constructed agent without changing the task's performance budget.
        """
        task_model_configs = (
            allowed_agent_models_override
            if allowed_agent_models_override is not None
            else task.hyper.allowed_agent_models
        ) or []
        stock_model_config = task_model_configs[0] if task_model_configs else None
        resolved_agent_llm = (
            agent_llm
            or task.hyper.agent_llm
            or (stock_model_config or {}).get("model")
            or DEFAULT_AGENT_LLM
        )
        resolved_user_llm = user_llm or task.hyper.user_llm or DEFAULT_USER_LLM
        resolved_client_llm = client_llm or task.hyper.client_llm or DEFAULT_CLIENT_LLM

        resolved_agent_llm_args = dict(agent_llm_args or {})
        if (
            task.hyper.agent_reasoning_effort
            and "reasoning_effort" not in resolved_agent_llm_args
        ):
            resolved_agent_llm_args["reasoning_effort"] = (
                task.hyper.agent_reasoning_effort
            )
        elif (
            agent_llm_args is None
            and task.hyper.agent_reasoning_effort is None
            and stock_model_config is not None
            and stock_model_config.get("model") == resolved_agent_llm
        ):
            resolved_agent_llm_args.update(
                resolve_stock_constraints(stock_model_config.get("constraints", {}))
            )

        resolved_user_llm_args = resolve_simulator_llm_args(
            user_llm_args,
            model=resolved_user_llm,
            task_effort=task.hyper.user_reasoning_effort,
            default_effort=DEFAULT_USER_REASONING_EFFORT,
        )
        resolved_client_llm_args = resolve_simulator_llm_args(
            client_llm_args,
            model=resolved_client_llm,
            task_effort=task.hyper.client_reasoning_effort,
            default_effort=DEFAULT_CLIENT_REASONING_EFFORT,
        )

        resolved_allowed_agent_models = task_model_configs or None
        if resolved_allowed_agent_models is not None:
            selected_configs = [
                config
                for config in resolved_allowed_agent_models
                if config.get("model") == resolved_agent_llm
            ]
            if not selected_configs:
                resolved_allowed_agent_models = None
            elif agent_llm_args is not None and not any(
                constraints_allow(
                    config.get("constraints", {}), resolved_agent_llm_args
                )
                for config in selected_configs
            ):
                allowed_constraints = [
                    dict(config.get("constraints", {})) for config in selected_configs
                ]
                raise ValueError(
                    f"Arguments for {resolved_agent_llm!r} must match its "
                    f"configured constraints: {allowed_constraints}"
                )
        if resolved_allowed_agent_models is None:
            resolved_allowed_agent_models = [
                {
                    "model": resolved_agent_llm,
                    "constraints": resolved_agent_llm_args,
                }
            ]

        # Read optional task-level sandbox budgets while normalizing zero/unset
        # wall-clock values to the benchmark-wide eight-hour default.
        resolved_budget = budget
        if resolved_budget is None and task.hyper.sandbox_config:
            sc = task.hyper.sandbox_config
            resolved_budget = BuildBudget(
                max_steps=sc.get("max_steps", 0),
                max_time_seconds=sc.get("max_time_seconds", 0),
            )

        return cls(
            task=task,
            builder=builder,
            client_llm=resolved_client_llm,
            client_llm_args=resolved_client_llm_args or None,
            agent_llm=resolved_agent_llm,
            user_llm=resolved_user_llm,
            agent_llm_args=resolved_agent_llm_args or None,
            allowed_agent_models=resolved_allowed_agent_models,
            user_llm_args=resolved_user_llm_args or None,
            budget=resolved_budget,
            kit_dir=kit_dir,
            keep_kit=keep_kit,
        )

    def _build_brief(self, client_opening: str) -> str:
        """Construct the brief given to the builder.

        Uses the Client's generated opening message (NOT the raw
        client_instructions, which are the Client LLM's system prompt
        and must never be shown to the Developer).

        Args:
            client_opening: The Client's opening message, generated by
                ``ClientSimulator.generate_initial_brief()``.
        """
        parts = []
        if self._client_enabled() and client_opening:
            parts.append(client_opening.strip())
            parts.append("\n---\n")
        parts.append(
            "Your goal is to produce a high-quality customer-service agent. "
            "Quality is measured by the proportion of unseen evaluation "
            "cases the agent passes, across routine, complex, and unusual "
            "customer requests. No particular architecture or development "
            "process is required.\n\n"
            "You have a developer kit directory. "
            "Start by reading README.md to understand the task and kit layout, "
            "then begin building."
        )
        if self._client_enabled():
            parts.append(
                "You can use `talk_to_client(message)` to ask the client "
                "business questions at any time."
            )
        if self.task.live_experiment_task_ids:
            parts.append(
                "You can call `run_live_experiment()` once to evaluate the "
                "current candidate on a small hidden sample of representative "
                "traffic. The attempt is consumed even if the candidate fails."
            )
        if self.task.training_task_ids:
            parts.append(
                "The client supplied "
                f"{len(self.task.training_task_ids)} sample customer "
                "scenarios recorded from their support operation. You can "
                "call `run_sample_scenarios()` to run the current candidate "
                "against all of them; the number of runs is limited, and a "
                "run is consumed even if the candidate fails."
            )
        parts.append("Call submit() when you're done.")
        return "\n\n".join(parts)

    def _apply_sandbox_config_to_builder(self) -> None:
        """Apply task-level sandbox runtime config to compatible builders."""
        sc = dict(self.task.hyper.sandbox_config or {})

        env_image = os.getenv("TAU2_SANDBOX_DOCKER_IMAGE")

        config_to_attr = {
            "command_timeout": "command_timeout",
            "docker_image": "docker_image",
            "docker_memory": "docker_memory",
            "docker_cpus": "docker_cpus",
        }

        if env_image:
            sc["docker_image"] = env_image

        for key, attr in config_to_attr.items():
            if key in sc and hasattr(self.builder, attr):
                setattr(self.builder, attr, sc[key])

        # Hand the grader's response-phrasing assertions to the builder so
        # run_local_test applies public phrasing checks. They deliberately never enter
        # the kit itself: the Developer sees only response_phrasing_rules.md.
        if hasattr(self.builder, "response_phrasing_pack"):
            from tau2.hyper.response_phrasing import (
                load_selected_response_phrasing_rule_pack_for_task,
            )

            self.builder.response_phrasing_pack = (
                load_selected_response_phrasing_rule_pack_for_task(self.task)
            )

        # Hand the candidate-runtime wiring for run_local_test to the builder.
        # It deliberately never enters the kit: anything on disk in the kit is
        # Developer-readable, and the Developer has no use for the inner
        # user-simulator settings, source-domain name, or selected defect profile.
        if hasattr(self.builder, "local_test_wiring"):
            from tau2.hyper.sandbox.local_test import LocalTestWiring

            defect_profile = None
            if self.task.client_api_deployment_manifest is not None:
                from tau2.hyper.client_api.defects import load_defect_profile

                defect_profile = load_defect_profile(
                    self.task.client_api_deployment_manifest,
                    expected_domain=self.task.source_domain,
                )
            self.builder.local_test_wiring = LocalTestWiring(
                domain=self.task.source_domain,
                user_llm=self.user_llm,
                user_llm_args={"reasoning_effort": "none"},
                client_api_mode=self.task.client_api_mode,
                client_api_defect_profile=defect_profile,
                capability_snapshot_provider=(
                    self._capability_session.freeze
                    if self._capability_session is not None
                    else None
                ),
            )

    def run(
        self,
        display=None,
    ) -> OuterLoopResult:
        """Run the full sandbox evaluation pipeline.

        1. Build kit from task.
        2. Run builder on the kit.
        3. Score the sealed candidate against final scoring tasks.
        4. Return OuterLoopResult.

        Args:
            display: Optional display adapter for live output.

        Returns:
            Final construction result and evaluation details.
        """
        domain = self.task.source_domain
        temp_dir = None

        # Determine kit directory
        if self.kit_dir is not None:
            kit_path = self.kit_dir
        else:
            temp_dir = tempfile.mkdtemp(prefix=f"hypertau_sandbox_{domain}_")
            # mkdtemp creates 0700; the sealed candidate container's
            # unprivileged user must be able to traverse the mounted kit.
            os.chmod(temp_dir, 0o755)
            kit_path = Path(temp_dir)
            logger.info(f"Using temp kit directory: {kit_path}")

        try:
            return self._run_impl(kit_path, display)
        finally:
            if temp_dir and not self.keep_kit:
                logger.debug(f"Cleaning up temp kit: {temp_dir}")
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _run_impl(self, kit_path: Path, display) -> OuterLoopResult:
        """Internal implementation of the run pipeline."""
        domain = self.task.source_domain
        self._client_context = None
        self._capability_session = None
        self._deployment_snapshot = None
        self._sample_scenarios_ctx = None

        # Phase 1: Build the kit
        logger.info(f"Phase 1: Building kit at {kit_path}")
        if display and hasattr(display, "show_task_info"):
            display.show_task_info(
                task=self.task,
                domain=domain,
                max_steps=self.budget.max_steps,
            )

        build_kit(
            self.task,
            kit_path,
            allowed_agent_models=self.allowed_agent_models,
        )
        kit_baseline_commit = initialize_kit_repository(kit_path)

        if self.task.live_experiment_task_ids:
            self.builder.set_live_experiment_context(
                LiveExperimentContext(
                    lambda: self._run_live_experiment(kit_path),
                    workspace_root=kit_path,
                )
            )

        if self.task.training_task_ids:
            self._sample_scenarios_ctx = SampleScenariosContext(
                lambda: self._run_sample_scenarios(kit_path)
            )
            self.builder.set_sample_scenarios_context(self._sample_scenarios_ctx)

        if display and hasattr(display, "show_sandbox_phase"):
            display.show_sandbox_phase(
                "kit_build",
                f"Kit ready at {kit_path}",
            )

        # Phase 1b: Set up Client simulator. Construction tasks run without
        # a Client unless they opt in via client_sections (rendered Client
        # knowledge from the section fact schemas) or hand-authored
        # client_instructions.
        if not self._client_enabled():
            client_opening = ""
            logger.info("Construction task — skipping Client initialization")
        else:
            from tau2.hyper.client import (
                ClientSimulator,
                client_capability_control_tools,
            )

            profile = self._client_api_defect_profile()
            client = ClientSimulator(
                llm=self.client_llm,
                client_instructions=self._resolve_client_instructions(),
                llm_args=self.client_llm_args,
                tools=(
                    client_capability_control_tools()
                    if profile is not None and profile.capabilities
                    else None
                ),
            )
            client_brief_msg, client_state = client.generate_initial_brief()
            client_opening = client_brief_msg.content or ""

            if display and hasattr(display, "show_client_message"):
                display.show_client_message(client_opening)

            if profile is not None and profile.capabilities:
                self._capability_session = CapabilityDeploymentSession(profile)
            self._client_context = ClientContext(
                client=client,
                client_state=client_state,
                deployment_manifest_id=(
                    profile.manifest_id if profile is not None else None
                ),
                deployment_manifest_sha256=(
                    profile.manifest_sha256 if profile is not None else None
                ),
                capability_session=self._capability_session,
            )
            self.builder.set_client_context(self._client_context)

        # Phase 2: Run the builder
        logger.info("Phase 2: Running sandbox builder")
        self._apply_sandbox_config_to_builder()

        brief = self._build_brief(client_opening)
        build_result = self.builder.build(kit_path, brief, self.budget, display=display)
        self._deployment_snapshot = (
            self._capability_session.seal()
            if self._capability_session is not None
            else empty_deployment_snapshot()
        )

        logger.info(
            f"Builder finished: {build_result.done_reason}, "
            f"{build_result.total_steps} steps, "
            f"{build_result.total_tool_calls} tool calls"
        )

        # Phase 3: Extract submission from the kit
        logger.info("Phase 3: Extracting submission")
        if display and hasattr(display, "show_sandbox_phase"):
            display.show_sandbox_phase(
                "extract",
                f"{build_result.total_steps} steps, "
                f"{build_result.total_tool_calls} tool calls, "
                f"{build_result.elapsed_seconds:.1f}s",
            )

        # Construction submissions are never imported into the host scorer.
        # The sealed runner loads their agent and toolkit inside Docker.
        agent_factory = create_sealed_candidate_agent

        # Phase 4: Score against test tasks
        logger.info("Phase 4: Scoring against test tasks")
        if display and hasattr(display, "show_final_eval_start"):
            display.show_final_eval_start()

        test_tasks = self._load_test_tasks()

        # Candidate code sees only its mounted kit, task-materialized DB state,
        # and visible messages. Hidden tasks and canonical tools stay in this
        # host process.
        sealed_config = self._sealed_runner_config(kit_path)
        dev_env = None
        load_error = None
        try:
            dev_env = SealedCandidateEnvironment.template(sealed_config)
            final_results = run_inner_simulations(
                test_tasks,
                domain=domain,
                policy="",
                agent_llm=self.agent_llm,
                user_llm=self.user_llm,
                agent_llm_args=self.agent_llm_args,
                allowed_agent_models=self.allowed_agent_models,
                user_llm_args=self.user_llm_args,
                agent_factory=agent_factory,
                custom_environment=dev_env,
                use_reference_gold_environment=True,
                client_api_mode=self.task.client_api_mode,
                display=display,
                eval_kind="test",
            )
            final_test_reward = (
                mean(r.reward for r in final_results) if final_results else 0.0
            )
        except Exception as error:
            logger.error(f"Sealed construction scoring failed: {error}")
            load_error = str(error)
            final_test_reward = 0.0
            final_results = []

        final_quality_reward = final_test_reward
        performance_details = evaluate_performance_requirements(
            self.task.performance_requirements,
            [message for result in final_results for message in result.messages],
            [result.agent_credit_usage for result in final_results],
        )
        performance_reward = performance_details["reward"]
        performance_penalty = performance_details["penalty"]
        final_test_reward = (
            max(0.0, final_quality_reward - performance_penalty) * performance_reward
        )

        # Build trajectory steps from build_result
        artifact_manifest = _build_artifact_manifest(kit_path, kit_baseline_commit)
        contamination_report = _build_contamination_report(
            kit_path, domain, kit_baseline_commit
        )
        steps = [
            OuterLoopStep(
                step_idx=bs.step_idx,
                action=(
                    ", ".join(tc["name"] for tc in bs.tool_calls)
                    if bs.tool_calls
                    else "text"
                ),
                action_args={
                    "timestamp": bs.timestamp,
                    "content": bs.content,
                    "reasoning_summary": bs.reasoning_summary,
                    "tool_calls": bs.tool_calls or [],
                    "tool_results": bs.tool_results or [],
                },
                result_summary=bs.content[:200] if bs.content else None,
            )
            for bs in build_result.steps
        ]

        run_metadata = {
            "task_id": self.task.id,
            "source_domain": domain,
            "kit_path": str(kit_path),
            "git_sha": _get_git_sha(),
            "kit_baseline_commit": kit_baseline_commit,
            "builder": build_result.metadata,
            "inner_loop": {
                "agent_llm": self.agent_llm,
                "agent_llm_args": self.agent_llm_args or {},
                "allowed_agent_models": self.allowed_agent_models or [],
                "user_llm": self.user_llm,
                "user_llm_args": self.user_llm_args or {},
            },
            "sandbox_config": dict(self.task.hyper.sandbox_config or {}),
            "build_result": {
                "submitted": build_result.submitted,
                "done_reason": build_result.done_reason,
                "elapsed_seconds": build_result.elapsed_seconds,
                "total_steps": build_result.total_steps,
                "total_tool_calls": build_result.total_tool_calls,
                "client_turns_used": build_result.client_turns_used,
            },
            "performance": performance_details,
            "live_experiment": {
                "enabled": bool(self.task.live_experiment_task_ids),
                "task_count": len(self.task.live_experiment_task_ids),
            },
            "sample_scenarios": {
                "enabled": bool(self.task.training_task_ids),
                "scenario_count": len(self.task.training_task_ids),
                "runs_used": (
                    self._sample_scenarios_ctx.runs_used
                    if self._sample_scenarios_ctx is not None
                    else 0
                ),
                "max_runs": (
                    self._sample_scenarios_ctx.max_runs
                    if self._sample_scenarios_ctx is not None
                    else 0
                ),
            },
        }
        if self._client_context is not None:
            run_metadata["client"] = self._client_context.result_metadata()
        if self.task.client_api_mode == "rest":
            contract_path = kit_path / "client_api" / "openapi.yaml"
            run_metadata["client_api"] = {
                "mode": "rest",
                "contract_version": CLIENT_API_CONTRACT_VERSION,
                "contract_sha256": hashlib.sha256(
                    contract_path.read_bytes()
                ).hexdigest(),
                "runtime_contract_version": CONSTRUCTION_RUNTIME_CONTRACT_VERSION,
            }
            if self.task.client_api_deployment_manifest is not None:
                from tau2.hyper.client_api.defects import load_defect_profile

                profile = load_defect_profile(
                    self.task.client_api_deployment_manifest,
                    expected_domain=domain,
                )
                run_metadata["client_api"]["deployment"] = {
                    "manifest_id": profile.manifest_id,
                    "manifest_sha256": profile.manifest_sha256,
                    "manifest_version": profile.manifest_version,
                }
        if dev_env is None:
            run_metadata["construction_load_error"] = load_error

        # Assemble the result
        outer_result = OuterLoopResult(
            domain=domain,
            final_test_reward=final_test_reward,
            final_quality_reward=final_quality_reward,
            performance_reward=performance_reward,
            performance_penalty=performance_penalty,
            performance_details=performance_details,
            test_details=[
                {
                    "task_id": r.task_id,
                    "reward": r.reward,
                    "error": r.error,
                    "reward_breakdown": r.reward_breakdown,
                    "nl_assertion_details": r.nl_assertion_details,
                    "response_assertion_details": r.response_assertion_details,
                    "agent_credit_usage": r.agent_credit_usage,
                    "agent_constraint_violations": r.agent_constraint_violations,
                    "messages": [
                        m.model_dump(mode="json") if hasattr(m, "model_dump") else m
                        for m in r.messages
                    ],
                }
                for r in final_results
            ],
            total_outer_steps=build_result.total_steps,
            client_turns_used=build_result.client_turns_used,
            steps=steps,
            run_metadata=run_metadata,
            artifact_manifest=artifact_manifest,
            contamination_report=contamination_report,
        )

        if display and hasattr(display, "show_result"):
            display.show_result(outer_result)

        logger.info(f"Sandbox evaluation complete: final={final_test_reward:.3f}")

        return outer_result

    def _client_enabled(self) -> bool:
        """Whether this run gets a live Client.

        Tasks opt in by declaring the Client's knowledge scope via
        ``client_sections``, by hand-authoring ``client_instructions``, or by
        configuring a Client API defect profile with a client or capabilities.
        """
        profile = self._client_api_defect_profile()
        return self.task.client_enabled and bool(
            self.task.client_sections
            or self.task.client_instructions.strip()
            or (
                profile is not None
                and (profile.client is not None or profile.capabilities)
            )
        )

    def _resolve_client_instructions(self) -> str:
        """The Client's system prompt: rendered from section fact schemas
        when the task declares ``client_sections``, else the task's
        hand-authored ``client_instructions``."""
        from tau2.hyper.client_sim.instructions import (
            resolve_task_client_instructions,
        )

        if self.task.client_sections:
            logger.info(
                f"Rendering Client instructions from sections "
                f"{self.task.client_sections}"
            )
        base_instructions = resolve_task_client_instructions(self.task)
        profile = self._client_api_defect_profile()
        if profile is None or (profile.client is None and not profile.capabilities):
            return base_instructions

        from tau2.hyper.client_sim.api_defect_overlay import (
            render_api_defect_client_overlay,
        )

        overlay = render_api_defect_client_overlay(profile)
        return "\n\n".join(part for part in (base_instructions, overlay) if part)

    def _client_api_defect_profile(self):
        """Load the task's host-only deployment profile, when configured."""

        reference = getattr(self.task, "client_api_deployment_manifest", None)
        if reference is None:
            return None
        from tau2.hyper.client_api.defects import load_defect_profile

        return load_defect_profile(reference, expected_domain=self.task.source_domain)

    def _load_test_tasks(self) -> list[Task]:
        """Load the tasks used for final scoring.

        Uses ``test_tasks_path`` when the task specifies a custom
        inner-loop tasks file, otherwise falls back to the domain's
        standard task set.
        """
        return self._load_inner_tasks(self.task.test_task_ids)

    def _load_inner_tasks(self, task_ids: list[str]) -> list[Task]:
        """Load one task partition through the task's configured source."""
        # Resolver, not the raw field: tasks that take phrasing through a
        # composition_pipeline stage have response_phrasing_rules_path=None,
        # and reading the field directly silently skipped phrasing grading
        # in scored traffic while run_local_test (which resolves) applied it.
        pack = load_selected_response_phrasing_rule_pack_for_task(self.task)
        if self.task.test_tasks_path:
            tasks = load_tasks_from_file(self.task.test_tasks_path, task_ids)
            return apply_response_phrasing_rule_pack_to_tasks(tasks, pack)

        domain = self.task.source_domain
        all_tasks = get_inner_loop_tasks(domain)
        by_id = {t.id: t for t in all_tasks}
        missing = [task_id for task_id in task_ids if task_id not in by_id]
        if missing:
            logger.warning(f"Task IDs not found in domain {domain}: {missing}")
        tasks = [by_id[task_id] for task_id in task_ids if task_id in by_id]
        return apply_response_phrasing_rule_pack_to_tasks(tasks, pack)

    def _sealed_runner_config(self, kit_path: Path) -> SealedRunnerConfig:
        """Build the candidate-only runtime configuration for scored traffic."""
        sandbox_config = dict(self.task.hyper.sandbox_config or {})
        defect_profile = None
        if self.task.client_api_deployment_manifest is not None:
            from tau2.hyper.client_api.defects import load_defect_profile

            defect_profile = load_defect_profile(
                self.task.client_api_deployment_manifest,
                expected_domain=self.task.source_domain,
            )
        deployment_snapshot = self._deployment_snapshot or (
            self._capability_session.freeze()
            if self._capability_session is not None
            else empty_deployment_snapshot()
        )
        return SealedRunnerConfig(
            kit_path=kit_path,
            image=(
                os.getenv("TAU2_SANDBOX_DOCKER_IMAGE")
                or sandbox_config.get("docker_image")
                or DEFAULT_CONSTRUCTION_RUNTIME_IMAGE
            ),
            memory=sandbox_config.get("docker_memory"),
            cpus=sandbox_config.get("docker_cpus"),
            domain=self.task.source_domain,
            client_api_mode=self.task.client_api_mode,
            client_api_factory=(
                (
                    lambda *, solo_mode=False: create_domain_client_api_runtime(
                        self.task.source_domain,
                        solo_mode=solo_mode,
                        deployment_snapshot=deployment_snapshot,
                        **(
                            {"defect_profile": defect_profile}
                            if defect_profile is not None
                            else {}
                        ),
                    )
                )
                if self.task.client_api_mode == "rest"
                else None
            ),
        )

    def _run_sample_scenarios(self, kit_path: Path) -> str:
        """Evaluate the current candidate on the client-supplied sample scenarios.

        The scenario set is the task's ``training_task_ids``, run host-side
        against the reference environment exactly like a live experiment, but
        repeatable within the context's run quota. Output case ids follow the
        fixed ``training_task_ids`` order so they stay stable across runs.
        """
        tasks = self._load_inner_tasks(self.task.training_task_ids)
        if not tasks:
            raise RuntimeError("The sample scenario set is empty")

        dev_env = SealedCandidateEnvironment.template(
            self._sealed_runner_config(kit_path)
        )
        try:
            results = run_inner_simulations(
                tasks,
                domain=self.task.source_domain,
                policy="",
                agent_llm=self.agent_llm,
                user_llm=self.user_llm,
                agent_llm_args=self.agent_llm_args,
                allowed_agent_models=self.allowed_agent_models,
                user_llm_args=self.user_llm_args,
                agent_factory=create_sealed_candidate_agent,
                custom_environment=dev_env,
                use_reference_gold_environment=True,
                client_api_mode=self.task.client_api_mode,
                eval_kind="train",
            )
            return format_sample_scenario_results(results)
        finally:
            dev_env.close()

    def _run_live_experiment(self, kit_path: Path) -> str:
        """Evaluate the current candidate on its one-shot hidden traffic sample."""
        tasks = self._load_inner_tasks(self.task.live_experiment_task_ids)
        if not tasks:
            raise RuntimeError("The live experiment task sample is empty")

        dev_env = SealedCandidateEnvironment.template(
            self._sealed_runner_config(kit_path)
        )
        try:
            results = run_inner_simulations(
                tasks,
                domain=self.task.source_domain,
                policy="",
                agent_llm=self.agent_llm,
                user_llm=self.user_llm,
                agent_llm_args=self.agent_llm_args,
                allowed_agent_models=self.allowed_agent_models,
                user_llm_args=self.user_llm_args,
                agent_factory=create_sealed_candidate_agent,
                custom_environment=dev_env,
                use_reference_gold_environment=True,
                client_api_mode=self.task.client_api_mode,
                eval_kind="live",
            )
            return format_live_experiment_results(results)
        finally:
            dev_env.close()
