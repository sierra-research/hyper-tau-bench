"""
Data models for the Hyper-τ outer loop.

Defines state objects for the Client simulator, the Developer agent,
the result of an outer-loop run, and the HyperTask specification.
"""

from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator

from tau2.data_model.message import Message
from tau2.data_model.tasks import Task
from tau2.user.user_simulator_base import UserState

# ---------------------------------------------------------------------------
# Hyper-τ task definition (promoted / domain-ready shape)
# ---------------------------------------------------------------------------


# Fields accepted at the top level of task JSON and lifted into the nested
# ``hyper`` sub-model.
_HYPER_METADATA_FIELDS: frozenset[str] = frozenset(
    {
        "source_domain",
        "task_description",
        "client_instructions",
        "client_sections",
        "training_task_ids",
        "live_experiment_task_ids",
        "live_experiment_source_task_id",
        "test_task_ids",
        "test_tasks_path",
        "agent_llm",
        "allowed_agent_models",
        "agent_reasoning_effort",
        "user_llm",
        "user_reasoning_effort",
        "client_llm",
        "client_reasoning_effort",
        "client_enabled",
        "sandbox_config",
        "sop_document_path",
        "sop_variant_manifest_path",
        "composition_pipeline",
        "knowledge_base_path",
        "knowledge_base_documents",
        "starting_workspace_path",
        "client_api_mode",
        "client_api_deployment_manifest",
        "response_phrasing_rules_path",
        "response_phrasing_rule_ids",
        "developer_hint_profile",
        "performance_profile",
        "performance_requirements",
        "modality_profile",
    }
)


# TODO: Add other performance metrics such as actual provider cost, time to first
# token, and user-perceived latency when their benchmark semantics are settled.
class LatencyPerformanceRequirement(BaseModel):
    """A suite-level latency constraint for the constructed agent."""

    id: str = Field(description="Stable identifier used in result reporting.")
    type: Literal["latency"] = "latency"
    measurement: Literal["agent_generate_next_message"] = "agent_generate_next_message"
    percentile: Literal[50, 90] = Field(
        description="Percentile computed across all measured final-evaluation turns."
    )
    max_seconds: float = Field(
        gt=0,
        description="Maximum allowed latency at the configured percentile.",
    )


class CreditPerformanceRequirement(BaseModel):
    """A set-wide mean credit budget for constructed-agent model calls."""

    id: str = Field(description="Stable identifier used in result reporting.")
    type: Literal["credits"] = "credits"
    measurement: Literal["agent_model_calls"] = "agent_model_calls"
    budget: float = Field(
        gt=0,
        description="Allowed mean model-call credits across evaluated conversations.",
    )
    tier: Optional[str] = Field(
        default=None,
        description="Performance tier this budget belongs to, when tier-derived.",
    )
    models: Optional[list[str]] = Field(
        default=None,
        description=(
            "Model names this budget meters. When set, only credits incurred "
            "on these models count toward the set-wide mean; unset meters all "
            "agent credits (the pre-tier behavior)."
        ),
    )


PerformanceRequirement = Annotated[
    Union[LatencyPerformanceRequirement, CreditPerformanceRequirement],
    Field(discriminator="type"),
]


class HyperMetadata(BaseModel):
    """All Hyper-τ-specific task fields, grouped under a single sub-model.

    This is nested inside :class:`HyperTask` (as ``task.hyper``) so that the
    standard :class:`tau2.data_model.tasks.Task` schema stays clean — any
    non-hyper tool that inspects a task can simply ignore the ``hyper``
    field. The field list mirrors the pre-promotion flat ``HyperTauTask``
    schema, minus the knobs retired with the structured meta-tool mode.
    """

    source_domain: str = Field(
        description="The τ-bench domain this task modifies, e.g. 'retail'."
    )

    # Task metadata
    task_description: str = Field(
        description="Human-readable description of what the Developer has to build."
    )

    # Client behavior — this IS the full system prompt for the Client LLM
    client_instructions: str = Field(
        default="",
        description=(
            "The full system prompt for the Client LLM simulator. "
            "Controls everything: persona, knowledge, opening message style, "
            "and how the Client responds to the Developer."
        ),
    )

    client_sections: Optional[list[str]] = Field(
        default=None,
        description=(
            "Section ids whose fact schemas define the Client's private "
            "knowledge. When set, the run renders the Client's system "
            "prompt from these sections at run time (see "
            "tau2.hyper.client_sim.instructions) and enables the Client "
            "even for construction tasks, where it is otherwise skipped. "
            "client_instructions must be empty when this is set."
        ),
    )

    @model_validator(mode="after")
    def _client_knowledge_single_source(self) -> "HyperMetadata":
        if self.client_sections and self.client_instructions:
            raise ValueError(
                "client_sections and client_instructions are mutually "
                "exclusive: rendered Client knowledge would silently "
                "override the hand-authored prompt"
            )
        return self

    # Inner-loop task splits
    training_task_ids: list[str] = Field(
        default_factory=list,
        description="Client-supplied sample scenario IDs available during development.",
    )
    live_experiment_task_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Hidden inner-loop traffic available through one live experiment "
            "during development. Must be disjoint from training tasks; MAY "
            "overlap final evaluation tasks — the pilot sample stays in the "
            "scored suite (Ben, 2026-08-29: no guarantee the Developer gets "
            "those conversations right, so they still count)."
        ),
    )
    live_experiment_source_task_id: Optional[str] = Field(
        default=None,
        description=(
            "Maintained source bundle from which a live-experiment variant "
            "was derived. Used for experiment provenance."
        ),
    )
    test_task_ids: list[str] = Field(
        description="Inner-loop task IDs used for final scoring."
    )

    @model_validator(mode="after")
    def _task_splits_are_disjoint(self) -> "HyperMetadata":
        live = set(self.live_experiment_task_ids)
        if len(live) != len(self.live_experiment_task_ids):
            raise ValueError("live_experiment_task_ids must be unique")
        if live & set(self.training_task_ids):
            raise ValueError(
                "training and live experiment task splits must be disjoint"
            )
        return self

    test_tasks_path: Optional[str] = Field(
        default=None,
        description=(
            "Path to a JSON file containing custom inner-loop test tasks, "
            "relative to the data directory. When set, test tasks are loaded "
            "from this file (filtered by test_task_ids) instead of from the "
            "source domain's tasks.json."
        ),
    )

    # Inner-loop model defaults
    agent_llm: Optional[str] = Field(
        default=None,
        description="Default LLM for the inner-loop Agent.",
    )
    allowed_agent_models: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description=(
            "Models available to a constructed Agent. Each entry contains a "
            "model name, an optional constraints mapping, and optional frozen "
            "input/output credit rates."
        ),
    )
    agent_reasoning_effort: Optional[str] = Field(
        default=None,
        description="Default reasoning effort for the inner-loop Agent.",
    )
    user_llm: Optional[str] = Field(
        default=None,
        description="Default LLM for the inner-loop User simulator.",
    )
    user_reasoning_effort: Optional[str] = Field(
        default=None,
        description="Default reasoning effort for the inner-loop User simulator.",
    )
    client_llm: Optional[str] = Field(
        default=None,
        description=(
            "Default LLM for the outer-loop Client simulator. The Client's "
            "persona is task-defined (``client_instructions``, "
            "``client_sections``), so the model voicing it belongs with the "
            "task. A ``--client-llm`` argument overrides this."
        ),
    )
    client_reasoning_effort: Optional[str] = Field(
        default=None,
        description="Default reasoning effort for the outer-loop Client simulator.",
    )

    # Outer-loop client configuration
    client_enabled: bool = Field(
        default=True,
        description=(
            "Whether the Client engages interactively after the opening "
            "brief. ``False`` means brief-only: the Developer works from "
            "the provided materials and cannot exchange messages with the "
            "Client. Defaults to ``True``. There is no cap on the number of "
            "client exchanges; the Client's knowledge scopes are the only "
            "control."
        ),
    )

    # Construction task SOP document.
    sop_document_path: Optional[str] = Field(
        default=None,
        description=(
            "Path (relative to the data directory) to an SOP/runbook document. "
            "Used for construction tasks where the Developer builds a domain "
            "from scratch. The SOP is included in the kit as sop.md. "
            "Construction tasks may set either this field or "
            "sop_variant_manifest_path."
        ),
    )
    sop_variant_manifest_path: Optional[str] = Field(
        default=None,
        description=(
            "Optional path (relative to the data directory) to a SOP variant "
            "manifest. The manifest assembles the construction SOP from a "
            "canonical SOP plus section-level replacements or appended "
            "sections, then includes the result in the kit as sop.md — or, "
            "when the manifest sets sop_delivery: uploaded_material, as a "
            "pooled customer document in uploaded_materials/."
        ),
    )
    composition_pipeline: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description=(
            "Ordered composition stages for construction tasks. For example, "
            "a transcript information-distribution task can depend on an "
            "earlier response-phrasing task and select only the phrasing "
            "rules that should apply before the transcript transformation."
        ),
    )
    knowledge_base_path: Optional[str] = Field(
        default=None,
        description=(
            "Optional path (relative to the data directory) to a raw knowledge "
            "base directory or file. Used for construction tasks where the SOP "
            "delegates operational details to supporting documents. The content "
            "is included in the kit as knowledge_base/."
        ),
    )
    knowledge_base_documents: Optional[list[str]] = Field(
        default=None,
        min_length=1,
        description=(
            "Optional list of document filenames to include from "
            "knowledge_base_path. When set, only these documents (minus any "
            "withheld by the SOP variant manifest) are copied into the kit, "
            "scoping a shared knowledge base to one bundle. Filenames that do "
            "not exist under knowledge_base_path fail the kit build."
        ),
    )
    starting_workspace_path: Optional[str] = Field(
        default=None,
        description=(
            "Optional path (relative to the data directory) to an authored "
            "starting-workspace directory (brownfield construction). The kit "
            "builder verifies the workspace's tree pins and copies tree/ into "
            "the kit's workspace/ instead of writing empty stubs. Only valid "
            "for construction tasks."
        ),
    )
    client_api_mode: Optional[Literal["rest"]] = Field(
        default=None,
        description=(
            "Use a client-owned REST API as the sole business-state boundary. "
            "The construction kit receives an OpenAPI contract and no database."
        ),
    )
    client_api_deployment_manifest: Optional[str] = Field(
        default=None,
        description=(
            "Host-owned versioned Client API deployment manifest reference. "
            "The Developer receives only its resulting contract and observed "
            "service behavior."
        ),
    )

    @model_validator(mode="after")
    def _deployment_manifest_requires_rest(self) -> "HyperMetadata":
        if self.client_api_deployment_manifest and self.client_api_mode != "rest":
            raise ValueError(
                "client_api_deployment_manifest requires client_api_mode='rest'"
            )
        return self

    response_phrasing_rules_path: Optional[str] = Field(
        default=None,
        description=(
            "Optional path (relative to the data directory) to a response "
            "phrasing rule pack. The rules are rendered into the construction "
            "kit and their assertions are applied to scoring tasks."
        ),
    )
    response_phrasing_rule_ids: Optional[list[str]] = Field(
        default=None,
        description=(
            "Optional subset of rule ids to select from the response phrasing "
            "pack for this composed construction task. When unset, all rules "
            "from the resolved pack are used."
        ),
    )
    developer_hint_profile: Optional[
        Literal[
            "small_model_context_routing_and_tool_review",
            "small_model_context_routing_tool_review_and_strict_workflows",
        ]
    ] = Field(
        default=None,
        description=(
            "Optional named solution-direction hint rendered into a construction "
            "kit's README. The profile selects framework-owned guidance rather "
            "than embedding free-form hidden instructions in the task."
        ),
    )
    performance_profile: Optional[
        Union[
            Literal["easy", "medium", "hard"],
            list[Literal["easy", "medium", "hard"]],
            dict[str, Any],
        ]
    ] = Field(
        default=None,
        description=(
            "Optional frozen model/rate-card/credit-budget profile. A bare "
            "tier name expands into allowed_agent_models and a domain credit "
            "requirement, exactly as before. A list activates several stock "
            "tiers at once; a mapping of tier -> {models, budget} additionally "
            "replaces a tier's model pool or overrides its credit budget "
            "(an explicit null budget removes the tier's cap). See "
            "tau2.hyper.performance_profiles.resolve_performance_profile_tiers."
        ),
    )
    performance_requirements: list[PerformanceRequirement] = Field(
        default_factory=list,
        description=(
            "Performance constraints applied to the constructed agent. Supports "
            "p50/p90 generate_next_message latency and model-call credit budgets."
        ),
    )
    modality_profile: Optional[str] = Field(
        default=None,
        description=(
            "Kit materialization profile: which artifact modalities the "
            "Developer's model class can consume, as a '+'-joined subset of "
            "text/image/audio/video (alias 'full'). One canonical bundle "
            "backs every profile; the kit builder substitutes text "
            "renditions for excluded modalities and upgrades phone-call "
            "records to audio when allowed. Unset uses the harness default "
            "(text+image+video), which reproduces pre-profile kits exactly."
        ),
    )

    @model_validator(mode="after")
    def _normalize_modality_profile(self) -> "HyperMetadata":
        """Canonicalize the profile string (and reject unknown modalities)."""
        if self.modality_profile is not None:
            from tau2.hyper.transformations.modality import (
                parse_modality_profile,
            )

            self.modality_profile = str(parse_modality_profile(self.modality_profile))
        return self

    @model_validator(mode="after")
    def resolve_performance_profile(self) -> "HyperMetadata":
        """Expand a named profile without allowing conflicting overrides."""
        if self.performance_profile is not None:
            if self.allowed_agent_models is not None:
                raise ValueError(
                    "performance_profile cannot be combined with allowed_agent_models"
                )
            if self.performance_requirements:
                raise ValueError(
                    "performance_profile cannot be combined with "
                    "performance_requirements"
                )

            if isinstance(self.performance_profile, str):
                # Legacy single-tier form: lowering is unchanged so existing
                # tasks, kit configs, and baselines stay byte-identical.
                from tau2.hyper.performance_profiles import get_performance_profile

                models, budget = get_performance_profile(
                    self.performance_profile,
                    self.source_domain,
                )
                self.allowed_agent_models = models
                self.performance_requirements = [
                    CreditPerformanceRequirement(
                        id=f"{self.performance_profile}_agent_credit_budget",
                        budget=budget,
                    )
                ]
            else:
                from tau2.hyper.performance_profiles import (
                    resolve_performance_profile_tiers,
                )

                models, tier_specs = resolve_performance_profile_tiers(
                    self.performance_profile,
                    self.source_domain,
                )
                self.allowed_agent_models = models
                self.performance_requirements = [
                    CreditPerformanceRequirement(
                        id=f"{spec['tier']}_agent_credit_budget",
                        budget=spec["budget"],
                        tier=spec["tier"],
                        models=spec["models"],
                    )
                    for spec in tier_specs
                    if spec["budget"] is not None
                ]

        credit_requirements = [
            requirement
            for requirement in self.performance_requirements
            if isinstance(requirement, CreditPerformanceRequirement)
        ]
        if credit_requirements:
            if not self.allowed_agent_models:
                raise ValueError(
                    "Credit performance requirements need allowed_agent_models"
                )
            metered_models: Optional[set[str]] = set()
            for requirement in credit_requirements:
                if requirement.models is None:
                    # An unscoped requirement meters every allowed model.
                    metered_models = None
                    break
                metered_models.update(requirement.models)
            unpriced_models = [
                config.get("model", "<unknown>")
                for config in self.allowed_agent_models
                if config.get("credit_rates") is None
                and (metered_models is None or config.get("model") in metered_models)
            ]
            if unpriced_models:
                raise ValueError(
                    "Credit performance requirements need credit_rates for "
                    f"every metered model; missing: {unpriced_models}"
                )
        return self

    # Sandbox runtime configuration.
    sandbox_config: Optional[dict] = Field(
        default=None,
        description=(
            "Configuration for sandbox mode. Keys: "
            "'max_time_seconds' (wall-clock limit; zero selects the "
            "eight-hour default), optional 'max_steps' (zero disables the "
            "step limit), 'command_timeout' (shell command timeout), "
            "'docker_image', 'docker_memory', "
            "'docker_cpus' (Docker runtime knobs)."
        ),
    )


def _synthesize_user_scenario(hyper: dict | HyperMetadata) -> dict:
    """Build a placeholder :class:`UserScenario` for a :class:`HyperTask`.

    Hyper-τ tasks don't carry a standard τ-bench ``UserScenario`` — the
    Client's behavior is driven entirely by ``hyper.client_instructions``.
    For the promoted :class:`HyperTask` (which extends :class:`Task` and
    therefore requires ``user_scenario``), we synthesize a minimal
    scenario that surfaces the client instructions so standard tooling
    (``tau2 view``, serializers, …) still has something sensible to render.
    """
    if isinstance(hyper, HyperMetadata):
        source_domain = hyper.source_domain
        client_instructions = hyper.client_instructions
    else:
        source_domain = hyper.get("source_domain", "hyper")
        client_instructions = hyper.get("client_instructions", "")
    return {
        "instructions": {
            "domain": source_domain,
            "reason_for_call": (
                "Hyper-τ outer-loop Client brief. The client_instructions "
                "field on the Hyper metadata is the full system prompt."
            ),
            "task_instructions": client_instructions,
        }
    }


class HyperTask(Task):
    """Promoted Hyper-τ task: a standard :class:`Task` plus ``hyper`` metadata.

    JSON stored on disk in the legacy flat shape also validates here — the
    ``_lift_legacy_shape`` model validator accepts dicts with the hyper
    fields at the top level and lifts them into the nested ``hyper``
    sub-model, synthesizing a :class:`UserScenario` when one isn't
    provided.

    Flat attribute access is preserved via properties (``task.source_domain``
    still works and is equivalent to ``task.hyper.source_domain``). This
    keeps code that was written against the pre-promotion flat
    ``HyperTauTask`` schema working without modification.
    """

    hyper: HyperMetadata = Field(
        description="Hyper-τ-specific construction metadata and budgets."
    )

    @model_validator(mode="before")
    @classmethod
    def _lift_legacy_shape(cls, data):
        if not isinstance(data, dict):
            return data
        data = dict(data)
        if "hyper" not in data:
            nested: dict = {}
            for field_name in list(data.keys()):
                if field_name in _HYPER_METADATA_FIELDS:
                    nested[field_name] = data.pop(field_name)
            if nested:
                data["hyper"] = nested
        if "user_scenario" not in data and "hyper" in data:
            data["user_scenario"] = _synthesize_user_scenario(data["hyper"])
        return data

    # ---- Flat attribute accessors for task metadata ----
    @property
    def source_domain(self) -> str:
        return self.hyper.source_domain

    @property
    def task_description(self) -> str:
        return self.hyper.task_description

    @property
    def client_instructions(self) -> str:
        return self.hyper.client_instructions

    @property
    def client_sections(self) -> Optional[list[str]]:
        return self.hyper.client_sections

    @property
    def training_task_ids(self) -> list[str]:
        return self.hyper.training_task_ids

    @property
    def live_experiment_task_ids(self) -> list[str]:
        return self.hyper.live_experiment_task_ids

    @property
    def live_experiment_source_task_id(self) -> Optional[str]:
        return self.hyper.live_experiment_source_task_id

    @property
    def test_task_ids(self) -> list[str]:
        return self.hyper.test_task_ids

    @property
    def test_tasks_path(self) -> Optional[str]:
        return self.hyper.test_tasks_path

    @property
    def agent_llm(self) -> Optional[str]:
        return self.hyper.agent_llm

    @property
    def allowed_agent_models(self) -> Optional[list[dict[str, Any]]]:
        return self.hyper.allowed_agent_models

    @property
    def agent_reasoning_effort(self) -> Optional[str]:
        return self.hyper.agent_reasoning_effort

    @property
    def user_llm(self) -> Optional[str]:
        return self.hyper.user_llm

    @property
    def user_reasoning_effort(self) -> Optional[str]:
        return self.hyper.user_reasoning_effort

    @property
    def client_llm(self) -> Optional[str]:
        return self.hyper.client_llm

    @property
    def client_reasoning_effort(self) -> Optional[str]:
        return self.hyper.client_reasoning_effort

    @property
    def client_enabled(self) -> bool:
        return self.hyper.client_enabled

    @property
    def sandbox_config(self) -> Optional[dict]:
        return self.hyper.sandbox_config

    @property
    def sop_document_path(self) -> Optional[str]:
        return self.hyper.sop_document_path

    @property
    def sop_variant_manifest_path(self) -> Optional[str]:
        return self.hyper.sop_variant_manifest_path

    @property
    def composition_pipeline(self) -> Optional[list[dict[str, Any]]]:
        return self.hyper.composition_pipeline

    @property
    def knowledge_base_path(self) -> Optional[str]:
        return self.hyper.knowledge_base_path

    @property
    def knowledge_base_documents(self) -> Optional[list[str]]:
        return self.hyper.knowledge_base_documents

    @property
    def starting_workspace_path(self) -> Optional[str]:
        return self.hyper.starting_workspace_path

    @property
    def client_api_mode(self) -> Optional[Literal["rest"]]:
        return self.hyper.client_api_mode

    @property
    def client_api_deployment_manifest(self) -> Optional[str]:
        return self.hyper.client_api_deployment_manifest

    @property
    def response_phrasing_rules_path(self) -> Optional[str]:
        return self.hyper.response_phrasing_rules_path

    @property
    def response_phrasing_rule_ids(self) -> Optional[list[str]]:
        return self.hyper.response_phrasing_rule_ids

    @property
    def developer_hint_profile(self) -> Optional[str]:
        return self.hyper.developer_hint_profile

    @property
    def performance_profile(
        self,
    ) -> Optional[Union[str, list[str], dict[str, Any]]]:
        return self.hyper.performance_profile

    @property
    def performance_requirements(self) -> list[PerformanceRequirement]:
        return self.hyper.performance_requirements

    @property
    def modality_profile(self) -> Optional[str]:
        return self.hyper.modality_profile


# JSON back-compat alias. Code and stored JSON that still uses
# ``HyperTauTask`` continues to work; new code should prefer ``HyperTask``.
HyperTauTask = HyperTask


# ---------------------------------------------------------------------------
# Client state
# ---------------------------------------------------------------------------


class ClientState(UserState):
    """State of the Client simulator during the outer loop.

    Structurally identical to :class:`UserState` — kept as a subclass so
    callers that type-check against ``ClientState`` remain valid, and so
    :class:`ClientSimulator` can widen it in the future without churning
    call sites.
    """


class EvaluationResult(BaseModel):
    """Result of running the inner-loop τ-bench evaluation on a single task."""

    task_id: str
    reward: float
    messages: list[Message] = Field(
        default_factory=list,
        description="The simulation messages (failure traces).",
    )
    error: Optional[str] = Field(
        default=None,
        description=(
            "Set only on zero-reward results the runner synthesized from an "
            "exception. Prefixed 'infrastructure_error:' when a transient "
            "provider failure exhausted retries (the task never really ran), "
            "'task_error:' for genuine task-execution failures."
        ),
    )
    reward_breakdown: Optional[dict] = Field(
        default=None,
        description="Per-component reward breakdown (e.g. DB, NL_ASSERTION).",
    )
    nl_assertion_details: Optional[list[dict]] = Field(
        default=None,
        description="NL assertion results: [{assertion, met, justification}, ...].",
    )
    response_assertion_details: Optional[list[dict]] = Field(
        default=None,
        description="Response assertion results: [{assertion, met, justification}, ...].",
    )
    grounding_details: Optional[dict] = Field(
        default=None,
        description=(
            "Discoverable-call grounding check result for Client REST "
            "construction scoring: {passed, required, observed, missing, "
            "extra_mutating}."
        ),
    )
    agent_credit_usage: Optional[dict[str, Any]] = Field(
        default=None,
        description=(
            "Conversation-scoped usage for every constructed-agent model call."
        ),
    )
    agent_constraint_violations: Optional[dict[str, Any]] = Field(
        default=None,
        description=(
            "Inference-constraint violations detected post-hoc on provider "
            "responses (e.g. reasoning output from a seat whose constraints "
            "pin reasoning off). None when every verifiable constraint held."
        ),
    )
    client_api_mock_report: Optional[dict[str, Any]] = Field(
        default=None,
        description=(
            "Developer-local Client API mock trace and verification result. "
            "Present only for mock-backed local scenarios."
        ),
    )
    client_api_defect_report: Optional[dict[str, Any]] = Field(
        default=None,
        description=(
            "Trusted host-only deployed-defect events and verification result. "
            "Never supplied to the Developer sandbox or constructed agent."
        ),
    )


class EvaluationSummary(BaseModel):
    """Summary of an inner-loop evaluation across multiple tasks."""

    results: list[EvaluationResult]
    mean_reward: float


class OuterLoopStep(BaseModel):
    """A record of one step in the outer loop."""

    step_idx: int
    action: str = Field(description="The tool/action the Developer took.")
    action_args: Optional[dict] = None
    result_summary: Optional[str] = None


class OuterLoopResult(BaseModel):
    """The result of a complete outer-loop run."""

    domain: str
    final_test_reward: float = Field(
        default=0.0,
        description=(
            "Final Hyper-τ reward after applying any performance requirement "
            "gate or penalty to the Developer's quality reward."
        ),
    )
    final_quality_reward: Optional[float] = Field(
        default=None,
        description=(
            "Mean task-quality reward before applying performance requirements."
        ),
    )
    performance_reward: float = Field(
        default=1.0,
        description="Binary multiplier retained for hard performance gates.",
    )
    performance_penalty: float = Field(
        default=0.0,
        description="Additive penalty from soft performance requirements.",
    )
    performance_details: dict = Field(
        default_factory=dict,
        description="Measured performance summaries and per-requirement results.",
    )
    test_details: Optional[list[dict]] = Field(
        default=None,
        description="Per-task final evaluation results.",
    )

    # Budget usage
    total_outer_steps: int
    client_turns_used: int

    # Trajectory
    steps: list[OuterLoopStep] = Field(default_factory=list)
    developer_messages: list[Message] = Field(default_factory=list)
    run_metadata: dict = Field(
        default_factory=dict,
        description=(
            "Run-level metadata such as model settings, sandbox backend, "
            "builder budget, task ID, and git SHA."
        ),
    )
    artifact_manifest: list[dict] = Field(
        default_factory=list,
        description=(
            "Manifest of Developer-authored artifacts, including paths, "
            "sizes, and content hashes."
        ),
    )
    contamination_report: dict = Field(
        default_factory=dict,
        description=(
            "Best-effort scan for references to private tau2 domain source "
            "or data in Developer-authored artifacts."
        ),
    )
