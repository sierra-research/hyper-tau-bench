"""Typed, host-owned Client API defect deployment configuration.

Deployment manifests are immutable experiment inputs.  Mutable counters and
workflow data live in :class:`TrialDefectState`, which is created afresh for
every inner τ-bench trial.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from tau2.utils.utils import DATA_DIR

CLIENT_API_DEPLOYMENTS_DIR = DATA_DIR / "tau2" / "hyper" / "client_api_deployments"

DefectKind = Literal[
    "response_value_map",
    "response_amount_sign",
    "response_field_rename",
    "response_date_to_datetime",
    "async_completion",
    "projection_lag",
    "rate_limit",
    "post_commit_timeout",
    "pagination",
]


class _FrozenModel(BaseModel):
    """Strict immutable base for deployment inputs and host telemetry."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ClientAPITrialContext(_FrozenModel):
    """Host-only identity used for deterministic defect activation."""

    task_id: Optional[str] = Field(default=None, min_length=1)
    trial_id: Optional[str] = Field(default=None, min_length=1)
    execution_mode: Literal["final_evaluation", "developer_test"] = "final_evaluation"
    developer_test_scenario_id: Optional[str] = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )

    @model_validator(mode="after")
    def _validate_developer_test_identity(self) -> "ClientAPITrialContext":
        if (
            self.execution_mode == "developer_test"
            and self.developer_test_scenario_id is None
        ):
            raise ValueError("developer_test mode requires a host-computed scenario ID")
        if (
            self.execution_mode == "final_evaluation"
            and self.developer_test_scenario_id is not None
        ):
            raise ValueError(
                "developer_test_scenario_id is valid only in developer_test mode"
            )
        return self


class DeveloperTestExposure(_FrozenModel):
    """Deterministic local-test exposure for a final-task-scoped defect.

    ``exposure_rate`` is an unconditional per-scenario probability. Defects in
    the same ``mutually_exclusive_group`` occupy disjoint ranges of one shared
    deterministic draw, so at most one member can be active in a scenario.
    """

    exposure_rate: float = Field(ge=0, le=1)
    seed: int = 0
    mutually_exclusive_group: Optional[str] = Field(
        default=None,
        min_length=1,
        pattern=r"^[A-Za-z0-9_.-]+$",
    )


class DefectActivation(_FrozenModel):
    """Deterministic cohort and call selectors for one defect."""

    task_ids: tuple[str, ...] = ()
    call_ordinals: tuple[int, ...] = ()
    resource_ids: tuple[str, ...] = ()
    developer_test: Optional[DeveloperTestExposure] = None

    @model_validator(mode="after")
    def _validate_selectors(self) -> "DefectActivation":
        if len(set(self.task_ids)) != len(self.task_ids):
            raise ValueError("activation task_ids must be unique")
        if len(set(self.call_ordinals)) != len(self.call_ordinals):
            raise ValueError("activation call_ordinals must be unique")
        if any(ordinal < 1 for ordinal in self.call_ordinals):
            raise ValueError("activation call_ordinals must be positive")
        if len(set(self.resource_ids)) != len(self.resource_ids):
            raise ValueError("activation resource_ids must be unique")
        if self.developer_test is not None and not self.task_ids:
            raise ValueError(
                "developer_test exposure is valid only for task-scoped defects"
            )
        return self

    def matches(
        self,
        *,
        trial_context: ClientAPITrialContext,
        call_ordinal: int,
        resource_ids: tuple[str, ...] = (),
    ) -> bool:
        """Return whether all configured selectors match this request."""

        if (
            trial_context.execution_mode == "final_evaluation"
            and self.task_ids
            and trial_context.task_id not in self.task_ids
        ):
            return False
        if self.call_ordinals and call_ordinal not in self.call_ordinals:
            return False
        if self.resource_ids and not set(self.resource_ids).intersection(resource_ids):
            return False
        return True


def _activations_may_overlap(left: DefectActivation, right: DefectActivation) -> bool:
    """Return whether two conjunctive selectors can match the same request."""

    for field_name in ("task_ids", "call_ordinals", "resource_ids"):
        left_values = set(getattr(left, field_name))
        right_values = set(getattr(right, field_name))
        if left_values and right_values and left_values.isdisjoint(right_values):
            return False
    return True


class _DefectBase(_FrozenModel):
    """Fields shared by every supported defect declaration."""

    id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_.-]+$")
    operation_id: str = Field(min_length=1)
    activation: DefectActivation = Field(default_factory=DefectActivation)


class ResponseValueMapDefect(_DefectBase):
    """Replace a JSON response value at a path using an explicit map."""

    kind: Literal["response_value_map"] = "response_value_map"
    path: tuple[str | int, ...] = Field(min_length=1)
    mapping: dict[str, JsonValue] = Field(min_length=1)


class ResponseAmountSignDefect(_DefectBase):
    """Normalize selected collection amounts to a configured sign."""

    kind: Literal["response_amount_sign"] = "response_amount_sign"
    collection_path: tuple[str | int, ...] = Field(min_length=1)
    discriminator_field: str = Field(min_length=1)
    discriminator_value: JsonValue
    amount_field: str = Field(min_length=1)
    sign: Literal["positive", "negative"]


class ResponseFieldRenameDefect(_DefectBase):
    """Rename one field in a JSON response object."""

    kind: Literal["response_field_rename"] = "response_field_rename"
    object_path: tuple[str | int, ...] = ()
    source_field: str = Field(min_length=1)
    target_field: str = Field(min_length=1)

    @model_validator(mode="after")
    def _field_names_differ(self) -> "ResponseFieldRenameDefect":
        if self.source_field == self.target_field:
            raise ValueError("response field rename requires different field names")
        return self


class ResponseDateToDatetimeDefect(_DefectBase):
    """Emit a canonical ISO date as a UTC-midnight datetime string."""

    kind: Literal["response_date_to_datetime"] = "response_date_to_datetime"
    path: tuple[str | int, ...] = Field(min_length=1)
    time_suffix: Literal["T00:00:00Z"] = "T00:00:00Z"


class AsyncCompletionDefect(_DefectBase):
    """Convert one synchronous mutation into a deterministic workflow."""

    kind: Literal["async_completion"] = "async_completion"
    status_path: str = Field(min_length=1, pattern=r"^/v1/[A-Za-z0-9_./{}-]+$")
    min_delay_seconds: float = Field(default=1.5, gt=0)
    max_delay_seconds: float = Field(default=5.0, gt=0)
    retry_after_seconds: int = Field(default=1, ge=1)
    seed: int = 0

    @model_validator(mode="after")
    def _status_path_has_workflow_id(self) -> "AsyncCompletionDefect":
        if re.findall(r"{([^{}]+)}", self.status_path) != ["workflow_id"]:
            raise ValueError(
                "status_path must contain exactly one {workflow_id} parameter"
            )
        if self.max_delay_seconds < self.min_delay_seconds:
            raise ValueError(
                "max_delay_seconds must be greater than or equal to min_delay_seconds"
            )
        return self


class RateLimitDefect(_DefectBase):
    """Reject one request ordinal until a deterministic monotonic deadline."""

    kind: Literal["rate_limit"] = "rate_limit"
    trigger_call_ordinal: int = Field(ge=1)
    min_delay_seconds: float = Field(default=1.5, gt=0)
    max_delay_seconds: float = Field(default=5.0, gt=0)
    retry_after_seconds: int = Field(default=2, ge=1)
    seed: int = 0

    @model_validator(mode="after")
    def _validate_delay_range(self) -> "RateLimitDefect":
        if self.max_delay_seconds < self.min_delay_seconds:
            raise ValueError(
                "max_delay_seconds must be greater than or equal to min_delay_seconds"
            )
        return self


class PostCommitTimeoutDefect(_DefectBase):
    """Lose a successful mutation response after its canonical commit.

    Idempotency applies to every request in the selected task/resource cohort,
    while ``activation.call_ordinals`` selects which committed response is
    replaced by a timeout. Records are trial-local and keyed by the public
    operation, concrete resource path, configured header, and request hash.
    """

    kind: Literal["post_commit_timeout"] = "post_commit_timeout"
    idempotency_header: str = Field(default="Idempotency-Key", min_length=1)
    timeout_status: Literal[504] = 504


class PaginationDefect(_DefectBase):
    """Page, truncate, or mis-order one collection response projection."""

    kind: Literal["pagination"] = "pagination"
    collection_path: tuple[str | int, ...] = Field(min_length=1)
    page_size: int = Field(ge=1)
    mode: Literal["cursor", "truncate", "lost_cursor", "limit_before_sort"] = "cursor"
    ordering: Literal["canonical", "reverse_canonical"] = "canonical"
    cursor_query_parameter: str = Field(default="cursor", min_length=1)
    cursor_response_field: str = Field(default="next_cursor", min_length=1)

    @model_validator(mode="after")
    def _validate_cursor_fields(self) -> "PaginationDefect":
        if self.mode != "cursor" and (
            self.cursor_query_parameter != "cursor"
            or self.cursor_response_field != "next_cursor"
        ):
            raise ValueError("cursor field overrides require cursor mode")
        return self


class ProjectionLagReadSurface(_FrozenModel):
    """One read projection on which an object's stale values may appear.

    A detail surface has no ``collection_path`` and may replace its entire
    response with the captured projection. A collection surface must name the
    response path containing its objects and the exact fields copied from the
    captured detail projection. This restriction is important: list entries
    are often intentionally narrower than detail resources, so replacing a
    whole list entry would fabricate fields and break its response schema.
    """

    operation_id: str = Field(min_length=1)
    resource_id_field: str = Field(min_length=1)
    collection_path: tuple[str | int, ...] = ()
    projected_fields: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _validate_surface_shape(self) -> "ProjectionLagReadSurface":
        if self.collection_path and not self.projected_fields:
            raise ValueError("collection projection surfaces require projected_fields")
        if not self.collection_path and self.projected_fields:
            raise ValueError(
                "detail projection surfaces must replace the complete response"
            )
        if len(set(self.projected_fields)) != len(self.projected_fields):
            raise ValueError("projection projected_fields must be unique")
        return self


class ProjectionLagDefect(_DefectBase):
    """Delay read-model visibility without delaying the authoritative write.

    Requirements for a clean defect instance:

    * ``operation_id`` is a side-effect-free, individually addressable detail
      read and is included exactly once in ``read_surfaces``.
    * Every trigger is an explicit mutating public operation and exposes the
      resource identifier named by ``resource_id_argument``. Semantic replay
      must map its canonical tool name back to that public trigger.
    * ``before_trigger`` captures the detail response before a direct write;
      ``after_trigger`` creates a watcher after an initiating write. The latter
      must use ``projection_change`` so externally completed state changes arm
      propagation only when authoritative state actually changes.
    * All alternate read surfaces that expose the projected fields are listed.
      Collection surfaces copy only ``projected_fields`` from the captured
      detail response and identify entries with ``resource_id_field``.
    * A later trigger for the same resource supersedes the earlier generation.
      State, deadlines, and verification observations are trial-local.
    * Delays use an injected monotonic clock and a deterministic seed; reads do
      not advance completion. Projection rewriting happens before independent
      response-shape/value defects and never mutates canonical domain state.
    * ``verification_operation_ids`` are optional ordering assertions: each
      requires that an affected resource has first been observed converged.
      If ``require_trigger_before_verification`` is true, the instance must be
      scoped only by task IDs and a verification call without any prior trigger
      is also a violation. A genuinely converged response emits a trusted
      host-only semantic observation so grading replay preserves this ordering;
      a canonical read alone is not evidence that the stale window elapsed.
    """

    kind: Literal["projection_lag"] = "projection_lag"
    trigger_operation_ids: tuple[str, ...] = Field(min_length=1)
    capture_timing: Literal["before_trigger", "after_trigger"]
    start_condition: Literal["after_trigger", "projection_change"]
    resource_id_argument: str = Field(min_length=1)
    read_surfaces: tuple[ProjectionLagReadSurface, ...] = Field(min_length=1)
    min_delay_seconds: float = Field(default=1.5, gt=0)
    max_delay_seconds: float = Field(default=5.0, gt=0)
    seed: int = 0
    verification_operation_ids: tuple[str, ...] = ()
    require_trigger_before_verification: bool = False

    @model_validator(mode="after")
    def _validate_projection_contract(self) -> "ProjectionLagDefect":
        if self.max_delay_seconds < self.min_delay_seconds:
            raise ValueError(
                "max_delay_seconds must be greater than or equal to min_delay_seconds"
            )
        if len(set(self.trigger_operation_ids)) != len(self.trigger_operation_ids):
            raise ValueError("projection trigger operation IDs must be unique")
        if len(set(self.verification_operation_ids)) != len(
            self.verification_operation_ids
        ):
            raise ValueError("projection verification operation IDs must be unique")
        surface_ids = [surface.operation_id for surface in self.read_surfaces]
        if len(surface_ids) != len(set(surface_ids)):
            raise ValueError("projection read surface operation IDs must be unique")
        primary = [
            surface
            for surface in self.read_surfaces
            if surface.operation_id == self.operation_id
        ]
        if len(primary) != 1 or primary[0].collection_path:
            raise ValueError(
                "operation_id must identify exactly one detail read surface"
            )
        if self.capture_timing == "before_trigger" and self.start_condition != (
            "after_trigger"
        ):
            raise ValueError(
                "before_trigger capture requires after_trigger start_condition"
            )
        if self.capture_timing == "after_trigger" and self.start_condition != (
            "projection_change"
        ):
            raise ValueError(
                "after_trigger capture requires projection_change start_condition"
            )
        if self.require_trigger_before_verification and (
            not self.verification_operation_ids
            or self.activation.call_ordinals
            or self.activation.resource_ids
        ):
            raise ValueError(
                "required projection triggers need verification operation IDs and "
                "may be scoped only by task_ids"
            )
        return self


DefectDeclaration = Annotated[
    Union[
        ResponseValueMapDefect,
        ResponseAmountSignDefect,
        ResponseFieldRenameDefect,
        ResponseDateToDatetimeDefect,
        AsyncCompletionDefect,
        ProjectionLagDefect,
        RateLimitDefect,
        PostCommitTimeoutDefect,
        PaginationDefect,
    ],
    Field(discriminator="kind"),
]


class ClientDefectFact(_FrozenModel):
    """What the simulated Client knows about one deployed defect."""

    defect_id: str = Field(min_length=1)
    actual_behavior: str = Field(min_length=1)
    disclosure_conditions: tuple[str, ...] = Field(min_length=1)
    expected_remediation: str = Field(min_length=1)
    client_can_deploy_fix: bool

    @model_validator(mode="after")
    def _conditions_are_nonempty(self) -> "ClientDefectFact":
        if any(not condition.strip() for condition in self.disclosure_conditions):
            raise ValueError("disclosure conditions must be non-empty")
        return self


class ClientDeploymentFacts(_FrozenModel):
    """Host-only Client knowledge about the published and deployed APIs."""

    published_api_version: str = Field(min_length=1)
    deployed_api_version: str = Field(min_length=1)
    defects: tuple[ClientDefectFact, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_versions_and_references(self) -> "ClientDeploymentFacts":
        if self.published_api_version == self.deployed_api_version:
            raise ValueError("published and deployed API versions must differ")
        ids = [fact.defect_id for fact in self.defects]
        if len(ids) != len(set(ids)):
            raise ValueError("Client defect references must be unique")
        return self


class ClientCapabilityDeclaration(_FrozenModel):
    """One pre-authored operation the Client may enable during construction."""

    id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_.-]+$")
    operation_id: str = Field(min_length=1)
    missing_functionality: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_missing_functionality(self) -> "ClientCapabilityDeclaration":
        if not self.missing_functionality.strip():
            raise ValueError("capability missing functionality must be non-empty")
        return self


class ClientAPIDeploymentManifest(_FrozenModel):
    """Versioned host configuration for one Client API deployment."""

    id: str = Field(min_length=1)
    version: int = Field(ge=1)
    domain: str = Field(min_length=1)
    defects: tuple[DefectDeclaration, ...] = ()
    capabilities: tuple[ClientCapabilityDeclaration, ...] = ()
    client: Optional[ClientDeploymentFacts] = None

    @model_validator(mode="after")
    def _defect_ids_are_unique(self) -> "ClientAPIDeploymentManifest":
        ids = [defect.id for defect in self.defects]
        if len(ids) != len(set(ids)):
            raise ValueError("defect ids must be unique within a deployment")
        capability_ids = [capability.id for capability in self.capabilities]
        if len(capability_ids) != len(set(capability_ids)):
            raise ValueError("capability ids must be unique within a deployment")
        capability_operations = [
            capability.operation_id for capability in self.capabilities
        ]
        if len(capability_operations) != len(set(capability_operations)):
            raise ValueError("capability operation IDs must be unique")
        if self.client is not None:
            client_ids = {fact.defect_id for fact in self.client.defects}
            unknown = sorted(client_ids - set(ids))
            if unknown:
                raise ValueError(
                    f"Client facts reference undeployed defects: {unknown}"
                )
            missing = sorted(set(ids) - client_ids)
            if missing:
                raise ValueError(f"Client facts missing deployed defects: {missing}")
        exposure_groups: dict[str, list[DefectDeclaration]] = {}
        for defect in self.defects:
            exposure = defect.activation.developer_test
            if exposure is not None and exposure.mutually_exclusive_group is not None:
                exposure_groups.setdefault(
                    exposure.mutually_exclusive_group, []
                ).append(defect)
        for group_id, members in exposure_groups.items():
            seeds = {member.activation.developer_test.seed for member in members}
            if len(seeds) != 1:
                raise ValueError(
                    f"developer-test exclusive group {group_id!r} must use one seed"
                )
            total_rate = sum(
                member.activation.developer_test.exposure_rate for member in members
            )
            if total_rate > 1.0 + 1e-12:
                raise ValueError(
                    f"developer-test exclusive group {group_id!r} exposure rates "
                    "must sum to at most 1"
                )
        async_defects = [
            defect for defect in self.defects if defect.kind == "async_completion"
        ]
        async_operation_ids = [defect.operation_id for defect in async_defects]
        if len(async_operation_ids) != len(set(async_operation_ids)):
            raise ValueError("async defect operation IDs must be unique")
        async_status_paths = [defect.status_path for defect in async_defects]
        if len(async_status_paths) != len(set(async_status_paths)):
            raise ValueError("async defect status paths must be unique")
        paginated_operation_ids = [
            defect.operation_id
            for defect in self.defects
            if defect.kind == "pagination"
        ]
        if len(paginated_operation_ids) != len(set(paginated_operation_ids)):
            raise ValueError("pagination defect operation IDs must be unique")
        post_commit_defects = [
            defect for defect in self.defects if defect.kind == "post_commit_timeout"
        ]
        for async_defect in async_defects:
            for post_commit_defect in post_commit_defects:
                final_overlap = _activations_may_overlap(
                    async_defect.activation, post_commit_defect.activation
                )
                async_exposure = async_defect.activation.developer_test
                timeout_exposure = post_commit_defect.activation.developer_test
                developer_overlap = (
                    async_exposure is not None
                    and timeout_exposure is not None
                    and (
                        async_exposure.mutually_exclusive_group is None
                        or async_exposure.mutually_exclusive_group
                        != timeout_exposure.mutually_exclusive_group
                    )
                )
                if async_defect.operation_id == post_commit_defect.operation_id and (
                    final_overlap or developer_overlap
                ):
                    raise ValueError(
                        "deployment has overlapping async and post-commit timeout "
                        f"cohorts for operation {async_defect.operation_id!r}: "
                        f"{async_defect.id!r} and {post_commit_defect.id!r}"
                    )
        return self


class DefectProfile(_FrozenModel):
    """Validated immutable runtime profile compiled from a manifest."""

    manifest_id: str
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_version: int = Field(ge=1)
    domain: str
    defects: tuple[DefectDeclaration, ...] = ()
    capabilities: tuple[ClientCapabilityDeclaration, ...] = ()
    client: Optional[ClientDeploymentFacts] = None

    @staticmethod
    def _developer_test_draw(*parts: str) -> float:
        """Map stable host-only inputs to a reproducible value in ``[0, 1)``."""

        digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).digest()
        return int.from_bytes(digest, "big") / (1 << (8 * len(digest)))

    def developer_test_active_defect_ids(
        self, trial_context: ClientAPITrialContext
    ) -> frozenset[str]:
        """Select task-scoped defects for one Developer-authored scenario."""

        if trial_context.execution_mode != "developer_test":
            return frozenset()
        scenario_id = trial_context.developer_test_scenario_id
        if scenario_id is None:  # Protected by ClientAPITrialContext validation.
            raise ValueError("developer_test mode requires a scenario ID")

        selected: set[str] = set()
        grouped: dict[str, list[DefectDeclaration]] = {}
        for defect in self.defects:
            exposure = defect.activation.developer_test
            if exposure is None:
                continue
            group_id = exposure.mutually_exclusive_group
            if group_id is None:
                draw = self._developer_test_draw(
                    self.manifest_sha256,
                    "independent",
                    defect.id,
                    str(exposure.seed),
                    scenario_id,
                )
                if draw < exposure.exposure_rate:
                    selected.add(defect.id)
            else:
                grouped.setdefault(group_id, []).append(defect)

        for group_id, members in grouped.items():
            exposure = members[0].activation.developer_test
            draw = self._developer_test_draw(
                self.manifest_sha256,
                "exclusive",
                group_id,
                str(exposure.seed),
                scenario_id,
            )
            cumulative = 0.0
            for defect in members:
                cumulative += defect.activation.developer_test.exposure_rate
                if draw < cumulative:
                    selected.add(defect.id)
                    break
        return frozenset(selected)

    def defect_selected_for_trial(
        self,
        defect: DefectDeclaration,
        trial_context: ClientAPITrialContext,
    ) -> bool:
        """Return whether a declaration belongs to this final or local cohort."""

        if not defect.activation.task_ids:
            return True
        if trial_context.execution_mode == "final_evaluation":
            return trial_context.task_id in defect.activation.task_ids
        return defect.id in self.developer_test_active_defect_ids(trial_context)

    def matching_defects(
        self,
        *,
        kind: DefectKind,
        operation_id: str,
        trial_context: ClientAPITrialContext,
        call_ordinal: int,
        resource_ids: tuple[str, ...] = (),
    ) -> tuple[DefectDeclaration, ...]:
        """Return matching declarations in stable manifest order."""

        matches = []
        for defect in self.defects:
            if defect.kind != kind or defect.operation_id != operation_id:
                continue
            if not self.defect_selected_for_trial(defect, trial_context):
                continue
            if defect.activation.matches(
                trial_context=trial_context,
                call_ordinal=call_ordinal,
                resource_ids=resource_ids,
            ):
                matches.append(defect)
        return tuple(matches)


class DefectEvent(_FrozenModel):
    """Trusted trial-local telemetry for one defect transition."""

    defect_id: str
    kind: DefectKind
    operation_id: str
    phase: str = Field(min_length=1)
    call_ordinal: int = Field(ge=1)
    details: dict[str, Any] = Field(default_factory=dict)


@dataclass
class TrialDefectState:
    """Mutable defect mechanism state isolated to one inner trial."""

    call_counts: dict[str, int] = field(default_factory=dict)
    storage: dict[str, Any] = field(default_factory=dict)

    def next_call_ordinal(self, operation_id: str) -> int:
        """Increment and return the request ordinal for an operation."""

        ordinal = self.call_counts.get(operation_id, 0) + 1
        self.call_counts[operation_id] = ordinal
        return ordinal

    def reset(self) -> None:
        """Discard all mutable state before a fresh trial."""

        self.call_counts.clear()
        self.storage.clear()


def _value_at_path(value: Any, path: tuple[str | int, ...]) -> Any:
    """Resolve a trusted manifest path in a JSON-shaped response."""

    current = value
    for segment in path:
        if isinstance(segment, int):
            if not isinstance(current, list):
                raise ValueError(
                    f"Expected a list before response path index {segment}"
                )
            current = current[segment]
        else:
            if not isinstance(current, dict) or segment not in current:
                raise ValueError(f"Response path segment {segment!r} does not exist")
            current = current[segment]
    return current


def _mapping_key(value: Any) -> str:
    """Return the manifest key used for a JSON scalar value."""

    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def apply_response_defect(
    response_body: Any,
    defect: (
        ResponseValueMapDefect
        | ResponseAmountSignDefect
        | ResponseFieldRenameDefect
        | ResponseDateToDatetimeDefect
    ),
) -> tuple[Any, dict[str, Any]]:
    """Apply one response-only defect without mutating canonical domain state."""

    transformed = copy.deepcopy(response_body)
    if isinstance(defect, ResponseValueMapDefect):
        parent = _value_at_path(transformed, defect.path[:-1])
        leaf = defect.path[-1]
        if isinstance(leaf, int):
            if not isinstance(parent, list):
                raise ValueError(f"Expected a list before response path index {leaf}")
            original = parent[leaf]
            replacement = defect.mapping.get(_mapping_key(original), original)
            parent[leaf] = replacement
        else:
            if not isinstance(parent, dict) or leaf not in parent:
                raise ValueError(f"Response path segment {leaf!r} does not exist")
            original = parent[leaf]
            replacement = defect.mapping.get(_mapping_key(original), original)
            parent[leaf] = replacement
        return transformed, {
            "path": list(defect.path),
            "changed": replacement != original
            or type(replacement) is not type(original),
        }

    if isinstance(defect, ResponseFieldRenameDefect):
        target = _value_at_path(transformed, defect.object_path)
        if not isinstance(target, dict):
            raise ValueError("Configured response rename target is not an object")
        if defect.source_field not in target:
            raise ValueError(f"Response field {defect.source_field!r} does not exist")
        if defect.target_field in target:
            raise ValueError(f"Response field {defect.target_field!r} already exists")
        target[defect.target_field] = target.pop(defect.source_field)
        return transformed, {
            "object_path": list(defect.object_path),
            "source_field": defect.source_field,
            "target_field": defect.target_field,
        }

    if isinstance(defect, ResponseDateToDatetimeDefect):
        parent = _value_at_path(transformed, defect.path[:-1])
        leaf = defect.path[-1]
        if isinstance(leaf, int):
            if not isinstance(parent, list):
                raise ValueError(f"Expected a list before response path index {leaf}")
            original = parent[leaf]
        else:
            if not isinstance(parent, dict) or leaf not in parent:
                raise ValueError(f"Response path segment {leaf!r} does not exist")
            original = parent[leaf]
        if not isinstance(original, str):
            raise ValueError("Configured response date is not a string")
        date.fromisoformat(original)
        replacement = f"{original}{defect.time_suffix}"
        parent[leaf] = replacement
        return transformed, {
            "path": list(defect.path),
            "source_format": "date",
            "target_format": "utc_datetime",
        }

    collection = _value_at_path(transformed, defect.collection_path)
    if not isinstance(collection, list):
        raise ValueError("Configured response amount collection is not a list")
    changed = 0
    for item in collection:
        if not isinstance(item, dict):
            raise ValueError(
                "Configured response amount collection contains a non-object"
            )
        if item.get(defect.discriminator_field) != defect.discriminator_value:
            continue
        amount = item.get(defect.amount_field)
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValueError("Configured response amount is not numeric")
        replacement = abs(amount) if defect.sign == "positive" else -abs(amount)
        if replacement != amount:
            changed += 1
        item[defect.amount_field] = replacement
    return transformed, {
        "collection_path": list(defect.collection_path),
        "changed_items": changed,
    }


def _canonical_manifest_bytes(manifest: ClientAPIDeploymentManifest) -> bytes:
    """Serialize semantic manifest content for stable hashing."""

    payload = manifest.model_dump(mode="json", exclude_none=True)
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _resolve_manifest_path(reference: str, root: Path) -> Path:
    """Resolve a logical manifest ID while rejecting traversal and suffixes."""

    if not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+", reference):
        raise ValueError(
            f"Invalid Client API deployment manifest reference: {reference!r}"
        )
    if reference.endswith(".json") or ".." in reference.split("/"):
        raise ValueError(
            f"Invalid Client API deployment manifest reference: {reference!r}"
        )
    root = root.resolve()
    path = (root / f"{reference}.json").resolve()
    if not path.is_relative_to(root):
        raise ValueError(
            f"Invalid Client API deployment manifest reference: {reference!r}"
        )
    return path


def compile_defect_profile(
    manifest: ClientAPIDeploymentManifest,
) -> DefectProfile:
    """Compile a validated manifest into its immutable runtime profile."""

    return DefectProfile(
        manifest_id=manifest.id,
        manifest_sha256=hashlib.sha256(_canonical_manifest_bytes(manifest)).hexdigest(),
        manifest_version=manifest.version,
        domain=manifest.domain,
        defects=manifest.defects,
        capabilities=manifest.capabilities,
        client=manifest.client,
    )


def load_defect_profile(
    reference: str,
    *,
    expected_domain: Optional[str] = None,
    root: Path = CLIENT_API_DEPLOYMENTS_DIR,
) -> DefectProfile:
    """Load and validate one logical deployment manifest reference."""

    path = _resolve_manifest_path(reference, Path(root))
    if not path.is_file():
        raise FileNotFoundError(
            f"Client API deployment manifest not found: {reference}"
        )
    manifest = ClientAPIDeploymentManifest.model_validate_json(path.read_text())
    if manifest.id != reference:
        raise ValueError(
            f"Client API deployment manifest id {manifest.id!r} does not match "
            f"reference {reference!r}"
        )
    if expected_domain is not None and manifest.domain != expected_domain:
        raise ValueError(
            f"Client API deployment manifest {reference!r} targets domain "
            f"{manifest.domain!r}, not {expected_domain!r}"
        )
    return compile_defect_profile(manifest)


def load_defect_profile_by_hash(
    manifest_sha256: str,
    *,
    expected_domain: str,
    root: Path = CLIENT_API_DEPLOYMENTS_DIR,
) -> DefectProfile:
    """Resolve an opaque kit-visible profile hash to its host manifest."""

    if not re.fullmatch(r"[0-9a-f]{64}", manifest_sha256):
        raise ValueError("Invalid Client API deployment manifest hash")
    domain_root = (Path(root) / expected_domain).resolve()
    root_resolved = Path(root).resolve()
    if not domain_root.is_relative_to(root_resolved) or not domain_root.is_dir():
        raise FileNotFoundError(
            f"No Client API deployment manifests exist for {expected_domain!r}"
        )
    for path in sorted(domain_root.rglob("*.json")):
        reference = path.relative_to(root_resolved).with_suffix("").as_posix()
        profile = load_defect_profile(
            reference,
            expected_domain=expected_domain,
            root=root_resolved,
        )
        if profile.manifest_sha256 == manifest_sha256:
            return profile
    raise FileNotFoundError(
        f"No Client API deployment manifest matches hash {manifest_sha256}"
    )
