"""Host service for Developer-authored local simulation scenarios."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from tau2.hyper.runtime_contract import DEFAULT_CONSTRUCTION_RUNTIME_IMAGE


@dataclass(frozen=True)
class LocalTestWiring:
    """Host-held runtime wiring for candidate-only local simulations.

    This deliberately never enters the kit: anything on disk in the sandbox
    is Developer-readable, and the Developer has no use for the inner
    user-simulator settings or the source-domain name. The harness supplies
    it when constructing the local-test service.
    """

    domain: str
    user_llm: str
    user_llm_args: dict = field(default_factory=dict)
    client_api_mode: Optional[str] = None
    client_api_defect_profile: Optional[Any] = None
    capability_snapshot_provider: Optional[Callable[[], Any]] = None


class SandboxToolError(Exception):
    """Raised when a sandbox tool operation fails."""


_REST_PRIVATE_SETUP_ERROR = (
    "REST-mode Developer scenarios cannot initialize private Client state; "
    "use the documented development seed and assistant wrapper tools"
)

_LOCAL_CLIENT_API_CONFIG_KEYS = frozenset({"mode", "module", "config"})


def _parse_local_client_api_scenario(
    task_data: dict[str, Any],
    *,
    sandbox_root: Path,
    rest_mode: bool,
) -> tuple[dict[str, Any], Optional[str], Optional[dict[str, Any]]]:
    """Remove and validate the local-only Client API scenario extension."""
    cleaned = dict(task_data)
    raw = cleaned.pop("client_api", None)
    if not rest_mode:
        if raw is not None:
            raise SandboxToolError(
                "The client_api scenario field is available only in REST kits"
            )
        return cleaned, None, None

    if raw is None:
        return cleaned, "seeded", None
    if not isinstance(raw, dict):
        raise SandboxToolError("client_api must be a JSON object")
    unknown = sorted(set(raw) - _LOCAL_CLIENT_API_CONFIG_KEYS)
    if unknown:
        raise SandboxToolError(
            "Unknown client_api scenario fields: " + ", ".join(unknown)
        )
    mode = raw.get("mode")
    if mode == "seeded":
        if set(raw) != {"mode"}:
            raise SandboxToolError(
                "Seeded Client API scenarios cannot include mock module or config"
            )
        return cleaned, "seeded", None
    if mode != "mock":
        raise SandboxToolError("client_api.mode must be 'seeded' or 'mock'")

    module = raw.get("module")
    if not isinstance(module, str) or not module:
        raise SandboxToolError("Mock Client API scenarios require client_api.module")
    module_path = Path(module)
    workspace_root = (sandbox_root / "workspace").resolve()
    resolved_module = (sandbox_root / module_path).resolve()
    if (
        module_path.is_absolute()
        or module_path.suffix != ".py"
        or not resolved_module.is_relative_to(workspace_root)
    ):
        raise SandboxToolError(
            "client_api.module must be a relative .py file inside workspace/"
        )
    if not resolved_module.is_file():
        raise SandboxToolError(f"Client API mock module not found: {module}")
    mock_config = raw.get("config", {})
    if not isinstance(mock_config, dict):
        raise SandboxToolError("client_api.config must be a JSON object")
    return cleaned, "mock", {"module": module, "config": mock_config}


def _developer_test_scenario_id(task: Any) -> str:
    """Return a stable host-only digest for one Developer-authored scenario."""

    payload = task.model_dump(mode="json", exclude_none=False)
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _prepare_rest_developer_task(task):
    """Separate public candidate setup from forbidden private Client setup."""
    initial_state = task.initial_state
    if initial_state is None:
        return task, [], None
    if initial_state.initialization_data is not None:
        raise SandboxToolError(_REST_PRIVATE_SETUP_ERROR)

    actions = list(initial_state.initialization_actions or [])
    if any(action.env_type != "assistant" for action in actions):
        raise SandboxToolError(_REST_PRIVATE_SETUP_ERROR)

    development_fixture = initial_state.development_fixture
    sanitized_state = initial_state.model_copy(
        update={
            "initialization_actions": None,
            "development_fixture": None,
        }
    )
    return (
        task.model_copy(update={"initial_state": sanitized_state}),
        actions,
        development_fixture,
    )


def _validate_mock_client_api_task(
    task, development_fixture: Optional[str | list[str]]
) -> None:
    """Reject scenario features that require a real local Client database."""
    from tau2.data_model.tasks import RewardType

    if development_fixture is not None:
        raise SandboxToolError(
            "Mock Client API scenarios cannot use initial_state.development_fixture"
        )
    reward_basis = (
        task.evaluation_criteria.reward_basis
        if task.evaluation_criteria is not None
        else []
    )
    if RewardType.DB in reward_basis:
        raise SandboxToolError(
            "Mock Client API scenarios cannot use DB grading; choose transcript, "
            "response, action, or environment assertions instead"
        )


class LocalTestService:
    """Run Developer-authored scenarios against the sealed candidate runtime."""

    def __init__(
        self,
        sandbox_root: Path,
        *,
        docker_image: Optional[str] = None,
        docker_memory: Optional[str] = None,
        docker_cpus: Optional[str] = None,
        response_phrasing_pack: Optional[Any] = None,
        local_test_wiring: Optional[LocalTestWiring] = None,
    ):
        self.sandbox_root = Path(sandbox_root).resolve()
        if not self.sandbox_root.is_dir():
            raise ValueError(f"Sandbox root does not exist: {self.sandbox_root}")
        self.docker_image = docker_image or DEFAULT_CONSTRUCTION_RUNTIME_IMAGE
        self.docker_memory = docker_memory
        self.docker_cpus = docker_cpus
        self.response_phrasing_pack = response_phrasing_pack
        self.local_test_wiring = local_test_wiring

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to the sandbox root, blocking escapes."""
        resolved = (self.sandbox_root / path).resolve()
        if not resolved.is_relative_to(self.sandbox_root):
            raise SandboxToolError(
                f"Path escapes sandbox: {path!r} resolves to {resolved}"
            )
        return resolved

    def _collect_local_task_files(self, task_path: str) -> list[Path]:
        """Resolve a developer-authored scenario file or directory."""
        resolved = self._resolve_path(task_path)
        if resolved.is_file():
            return [resolved]
        if resolved.is_dir():
            return sorted(resolved.glob("*.json"))
        raise SandboxToolError(f"Scenario path not found: {task_path}")

    def _load_developer_manifest(self) -> dict:
        """Load the developer-facing deployment manifest from the kit."""
        manifest_path = self.sandbox_root / "framework" / "deployment_manifest.json"
        if not manifest_path.is_file():
            raise SandboxToolError(
                "framework/deployment_manifest.json not found in sandbox root"
            )
        try:
            return json.loads(manifest_path.read_text())
        except json.JSONDecodeError as e:
            raise SandboxToolError(f"Invalid {manifest_path.name}: {e}") from e

    def _resolve_local_test_wiring(self) -> LocalTestWiring:
        """Return the trusted runtime wiring supplied by the harness."""
        if self.local_test_wiring is None:
            raise SandboxToolError(
                "Local simulations need harness-supplied runtime wiring"
            )
        return self.local_test_wiring

    @staticmethod
    def _truncate_text(text: str, limit: int = 1200) -> str:
        """Keep tool output readable while preserving the important front."""
        if len(text) <= limit:
            return text
        return text[:limit] + f"... [truncated, {len(text)} chars total]"

    @classmethod
    def _format_projected_message(cls, index: int, message: dict) -> list[str]:
        """Format one projected simulation message for tool output."""
        role = message.get("role") or "unknown"
        lines = [f"  {index}. {role}"]
        content = message.get("content")
        if content:
            lines.append(f"     {cls._truncate_text(str(content), 1600)}")
        tool_calls = message.get("tool_calls") or []
        for tool_call in tool_calls:
            name = tool_call.get("name", "unknown")
            arguments = tool_call.get("arguments", {})
            try:
                rendered_args = json.dumps(arguments, sort_keys=True)
            except TypeError:
                rendered_args = str(arguments)
            lines.append(
                f"     tool_call: {name}({cls._truncate_text(rendered_args, 800)})"
            )
        return lines

    @classmethod
    def _format_local_test_result(
        cls,
        *,
        task_path: Path,
        task_id: str,
        reward: float,
        reward_breakdown: Optional[dict],
        nl_assertion_details: Optional[list[dict]],
        response_assertion_details: Optional[list[dict]],
        projected_messages: list[dict],
        verbose: bool,
        sandbox_root: Path,
    ) -> str:
        """Render one candidate-only simulation result for the Developer LLM."""
        rel_path = task_path.relative_to(sandbox_root).as_posix()
        status = "PASS" if reward >= 1.0 else "FAIL"
        lines = [
            f"Scenario: {task_id} ({rel_path})",
            f"Reward: {reward:.3f} [{status}]",
        ]
        if reward_breakdown:
            breakdown = ", ".join(
                f"{key}={value}" for key, value in reward_breakdown.items()
            )
            lines.append(f"Reward breakdown: {breakdown}")
        if nl_assertion_details:
            lines.append("NL assertions:")
            for assertion in nl_assertion_details:
                mark = "PASS" if assertion.get("met") else "FAIL"
                lines.append(f"  [{mark}] {assertion.get('assertion', '')}")
                justification = assertion.get("justification")
                if verbose and justification:
                    lines.append(f"    {cls._truncate_text(str(justification), 1200)}")
        if response_assertion_details:
            lines.append("Response assertions:")
            for assertion in response_assertion_details:
                mark = "PASS" if assertion.get("met") else "FAIL"
                assertion_info = assertion.get("assertion") or {}
                assertion_id = assertion_info.get("id", "")
                lines.append(f"  [{mark}] {assertion_id}")
                justification = assertion.get("justification")
                if verbose and justification:
                    lines.append(f"    {cls._truncate_text(str(justification), 1200)}")

        if projected_messages:
            lines.append("Transcript:" if verbose else "Recent transcript:")
            messages = projected_messages if verbose else projected_messages[-8:]
            first_index = 1 if verbose else len(projected_messages) - len(messages) + 1
            for offset, message in enumerate(messages):
                lines.extend(
                    cls._format_projected_message(first_index + offset, message)
                )
            if not verbose and len(projected_messages) > len(messages):
                lines.append(
                    "  [... earlier messages omitted; rerun with verbose=true "
                    "for the full transcript]"
                )
        return "\n".join(lines)

    def _new_local_test_artifact_path(self) -> Path:
        """Create a sandbox-local artifact path for a local simulation run."""
        simulations_dir = self._resolve_path("simulations")
        simulations_dir.mkdir(exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        candidate = simulations_dir / f"local_run_{timestamp}.json"
        suffix = 1
        while candidate.exists():
            candidate = simulations_dir / f"local_run_{timestamp}_{suffix}.json"
            suffix += 1
        return candidate

    def run_local_test(
        self,
        task_path: str,
        *,
        verbose: bool = False,
        max_steps: int = 100,
    ) -> str:
        """Run developer-authored scenarios against the candidate runtime.

        For Client API kits, local tests interact through the documented REST
        interface. Held-out tasks are not loaded. When the domain has
        customer-side tools, that simulator-facing side is supplied by the
        host.
        """
        wiring = self._resolve_local_test_wiring()
        domain = wiring.domain

        task_files = self._collect_local_task_files(task_path)
        if not task_files:
            raise SandboxToolError(f"No .json scenario files found at: {task_path}")

        # Import lazily to avoid a module cycle at import time:
        # builder -> tools -> orchestrator -> builder.
        from tau2.data_model.tasks import Task
        from tau2.hyper import _inner
        from tau2.hyper.agent_context import resolve_stock_constraints
        from tau2.hyper.client_api.runtime import create_domain_client_api_runtime
        from tau2.hyper.live_experiment import developer_visible_message_json
        from tau2.hyper.performance import (
            evaluate_performance_requirements,
            format_credit_summary,
            parse_performance_requirement,
        )
        from tau2.hyper.response_phrasing import (
            apply_response_phrasing_rule_pack_to_task,
        )
        from tau2.hyper.sandbox.sealed_runner import (
            SealedCandidateEnvironment,
            SealedRunnerConfig,
            create_sealed_candidate_agent,
        )

        manifest = self._load_developer_manifest()
        allowed_agent_models = manifest["allowed_agent_models"]
        stock_model_config = allowed_agent_models[0]
        agent_llm = stock_model_config["model"]
        agent_llm_args = resolve_stock_constraints(
            stock_model_config.get("constraints", {})
        )
        user_llm_args = dict(wiring.user_llm_args)
        sealed_config = SealedRunnerConfig(
            kit_path=self.sandbox_root,
            image=self.docker_image,
            memory=self.docker_memory,
            cpus=self.docker_cpus,
            domain=domain,
            client_api_mode=wiring.client_api_mode,
            client_api_factory=(
                (
                    lambda *, solo_mode=False: create_domain_client_api_runtime(
                        domain,
                        solo_mode=solo_mode,
                        development_seed=True,
                        **(
                            {
                                "deployment_snapshot": wiring.capability_snapshot_provider()
                            }
                            if wiring.capability_snapshot_provider is not None
                            else {}
                        ),
                        **(
                            {"defect_profile": wiring.client_api_defect_profile}
                            if wiring.client_api_defect_profile is not None
                            else {}
                        ),
                    )
                )
                if wiring.client_api_mode == "rest"
                else None
            ),
        )
        try:
            dev_env = SealedCandidateEnvironment.template(sealed_config)
        except Exception as error:
            raise SandboxToolError(
                f"Could not load the sealed candidate runtime: {error}"
            ) from error

        results = []
        credit_usages = []
        records = []
        mock_dev_env = None
        error_count = 0
        run_started_at = datetime.now(timezone.utc).isoformat()
        artifact_path = self._new_local_test_artifact_path()
        # The source-domain name is runtime wiring, not Developer-facing
        # information, so neither the tool output nor the sandbox-local run
        # artifact may carry it.
        output_blocks = [
            "Local simulation run",
            "Assistant implementation: Developer submission",
        ]
        if wiring.client_api_mode == "rest":
            output_blocks.append(
                "Client API: sandbox implementation of client_api/openapi.yaml"
            )
        output_blocks.extend(
            [
                f"Scenarios: Developer-authored ({len(task_files)})",
                "Customer/user runtime: enabled when the domain provides it",
                "",
            ]
        )

        for task_file in task_files:
            scenario_client_api_mode = None
            try:
                task_data = json.loads(task_file.read_text())
                task_data, scenario_client_api_mode, client_api_mock = (
                    _parse_local_client_api_scenario(
                        task_data,
                        sandbox_root=self.sandbox_root,
                        rest_mode=wiring.client_api_mode == "rest",
                    )
                )
                task = Task.model_validate(task_data)
                task = apply_response_phrasing_rule_pack_to_task(
                    task, self.response_phrasing_pack
                )
                developer_test_scenario_id = _developer_test_scenario_id(task)
                developer_setup_actions = []
                development_fixture = None
                scenario_env = dev_env
                if wiring.client_api_mode == "rest":
                    task, developer_setup_actions, development_fixture = (
                        _prepare_rest_developer_task(task)
                    )
                    if scenario_client_api_mode == "mock":
                        _validate_mock_client_api_task(task, development_fixture)
                        mock_base_config = replace(
                            sealed_config,
                            # Mock dispatch is implemented by the current
                            # candidate runtime. Maintained final scoring stays
                            # pinned to the task's existing image.
                            image=DEFAULT_CONSTRUCTION_RUNTIME_IMAGE,
                            client_api_factory=None,
                        )
                        if mock_dev_env is None:
                            mock_dev_env = SealedCandidateEnvironment.template(
                                mock_base_config
                            )
                        scenario_config = replace(
                            mock_base_config,
                            client_api_mock=client_api_mock,
                        )
                        scenario_env = SealedCandidateEnvironment(
                            scenario_config,
                            metadata=mock_dev_env.metadata,
                            runner=None,
                        )
                result = _inner.run_inner_simulation(
                    domain=domain,
                    task=task,
                    policy=scenario_env.policy,
                    agent_llm=agent_llm,
                    user_llm=wiring.user_llm,
                    agent_llm_args=agent_llm_args,
                    allowed_agent_models=allowed_agent_models,
                    user_llm_args=user_llm_args,
                    max_steps=max_steps,
                    agent_factory=create_sealed_candidate_agent,
                    custom_environment=scenario_env,
                    use_reference_gold_environment=False,
                    developer_setup_actions=developer_setup_actions,
                    development_fixture=development_fixture,
                    client_api_execution_mode="developer_test",
                    client_api_developer_test_scenario_id=developer_test_scenario_id,
                )
                projected_messages = _inner.project_messages(result.messages)
                developer_visible_result = result.model_dump(mode="json")
                developer_visible_result.pop("client_api_defect_report", None)
                # The sandbox-local run artifact is Developer-readable, so
                # messages must pass through the same allowlist seal as the
                # other feedback surfaces: a wholesale dump carries litellm's
                # ``raw_data`` request echo, including the user simulator's
                # system prompt.
                developer_visible_result["messages"] = [
                    developer_visible_message_json(message)
                    for message in result.messages
                ]
                results.append(result)
                credit_usages.append(result.agent_credit_usage)
                records.append(
                    {
                        "task_path": task_file.relative_to(
                            self.sandbox_root
                        ).as_posix(),
                        "task_id": result.task_id,
                        "reward": result.reward,
                        "status": "pass" if result.reward >= 1.0 else "fail",
                        "client_api_mode": scenario_client_api_mode,
                        "reward_breakdown": result.reward_breakdown,
                        "nl_assertion_details": result.nl_assertion_details,
                        "response_assertion_details": (
                            result.response_assertion_details
                        ),
                        "projected_messages": projected_messages,
                        "result": developer_visible_result,
                    }
                )
                formatted_result = self._format_local_test_result(
                    task_path=task_file,
                    task_id=result.task_id,
                    reward=result.reward,
                    reward_breakdown=result.reward_breakdown,
                    nl_assertion_details=result.nl_assertion_details,
                    response_assertion_details=(result.response_assertion_details),
                    projected_messages=projected_messages,
                    verbose=verbose,
                    sandbox_root=self.sandbox_root,
                )
                if scenario_client_api_mode is not None:
                    formatted_result = (
                        f"Client API mode: {scenario_client_api_mode}\n"
                        + formatted_result
                    )
                output_blocks.append(formatted_result)
            except Exception as e:
                error_count += 1
                credit_usages.append(None)
                error_record = {
                    "task_path": task_file.relative_to(self.sandbox_root).as_posix(),
                    "task_id": None,
                    "reward": 0.0,
                    "status": "error",
                    "client_api_mode": scenario_client_api_mode,
                    "error": {
                        "type": type(e).__name__,
                        "message": str(e),
                    },
                }
                mock_report = getattr(e, "client_api_mock_report", None)
                if mock_report is not None:
                    error_record["client_api_mock_report"] = mock_report
                records.append(error_record)
                output_blocks.append(
                    "\n".join(
                        [
                            *(
                                [f"Client API mode: {scenario_client_api_mode}"]
                                if scenario_client_api_mode is not None
                                else []
                            ),
                            f"Scenario: {task_file.relative_to(self.sandbox_root)}",
                            f"Reward: 0.000 [ERROR]",
                            f"Error: {type(e).__name__}: {e}",
                        ]
                    )
                )

        if results or error_count:
            avg_reward = sum(result.reward for result in results) / len(task_files)
            passed = sum(1 for result in results if result.reward >= 1.0)
            output_blocks.append(
                f"Summary: {passed}/{len(task_files)} passed, "
                f"avg reward={avg_reward:.3f}"
            )
        else:
            avg_reward = 0.0
            passed = 0
            output_blocks.append("Summary: no valid task results")

        performance_requirements = [
            parse_performance_requirement(requirement)
            for requirement in manifest.get("performance_requirements", [])
        ]
        performance = evaluate_performance_requirements(
            performance_requirements,
            [message for result in results for message in result.messages],
            credit_usages,
        )
        latency = performance["summary"]
        if latency["sample_count"]:
            output_blocks.append(
                "Agent turn latency: "
                f"n={latency['sample_count']}, "
                f"p50={latency['p50_seconds']:.3f}s, "
                f"p90={latency['p90_seconds']:.3f}s, "
                f"max={latency['max_seconds']:.3f}s"
            )
        for requirement in performance["requirements"]:
            if requirement["type"] != "latency":
                continue
            status = "PASS" if requirement["met"] else "FAIL"
            observed = requirement["observed_seconds"]
            rendered_observed = (
                f"{observed:.3f}s" if observed is not None else "no samples"
            )
            output_blocks.append(
                f"Latency requirement [{status}] {requirement['id']}: "
                f"p{requirement['percentile']}={rendered_observed} <= "
                f"{requirement['max_seconds']:g}s"
            )
        credit_line = format_credit_summary(performance["credit_summary"])
        if credit_line is not None:
            output_blocks.append(credit_line)
        adjusted_reward = (
            max(0.0, avg_reward - performance["penalty"]) * performance["reward"]
        )
        if performance_requirements:
            output_blocks.append(f"Performance-adjusted score: {adjusted_reward:.3f}")

        artifact_payload = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "started_at": run_started_at,
            "allowed_agent_models": allowed_agent_models,
            "max_steps": max_steps,
            "task_paths": [
                task_file.relative_to(self.sandbox_root).as_posix()
                for task_file in task_files
            ],
            "summary": {
                "total": len(task_files),
                "valid": len(results),
                "errors": error_count,
                "passed": passed,
                "avg_reward": avg_reward,
            },
            "performance": performance,
            "records": records,
        }
        artifact_path.write_text(json.dumps(artifact_payload, indent=2, default=str))
        output_blocks.append(
            f"Saved artifact: {artifact_path.relative_to(self.sandbox_root).as_posix()}"
        )

        return "\n\n".join(output_blocks)
