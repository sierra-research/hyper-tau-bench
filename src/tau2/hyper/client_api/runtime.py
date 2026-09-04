"""Host-side Client API runtime for Hyper-τ construction.

This module is the trusted, host-only half of the Client API: the sandbox
server (`ClientAPIRuntime`) that executes seeded operations, applies
response defects, and builds the published OpenAPI contract. It must never
ship in the construction runtime image — the Developer-facing surface lives
in `tau2.hyper.client_api`, which imports nothing from this module.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional
from urllib.parse import unquote

from pydantic import TypeAdapter, ValidationError

from tau2.data_model.message import ToolCall, ToolMessage
from tau2.data_model.tasks import EnvFunctionCall, InitializationData
from tau2.environment.environment import Environment
from tau2.hyper.client_api.capabilities import (
    DeploymentSnapshot,
    empty_deployment_snapshot,
)
from tau2.hyper.client_api.defects import (
    AsyncCompletionDefect,
    ClientAPITrialContext,
    DefectEvent,
    DefectProfile,
    PaginationDefect,
    PostCommitTimeoutDefect,
    ProjectionLagDefect,
    RateLimitDefect,
    TrialDefectState,
    apply_response_defect,
)

if TYPE_CHECKING:
    # The catalog pins operation schemas to tau2.domains data models, which
    # the construction runtime image deliberately strips. The sealed
    # candidate_server imports this module, so the catalog may only be
    # loaded lazily by the host-side code paths that actually use it.
    from tau2.hyper.client_api.catalog import (
        ClientOperation,
        ConversationTransferReceipt,
    )

from tau2.hyper.client_api import (
    _PUBLIC_BUSINESS_ERROR_MESSAGES,
    CLIENT_API_CONTRACT_VERSION,
    CLIENT_API_MAX_REQUEST_BYTES,
    CLIENT_API_MAX_RESPONSE_BYTES,
    ClientAPIContext,
    ClientAPIOperationCall,
    ClientAPIResponse,
    _json_size_bytes,
    _json_value,
    _value_at_json_path,
)

_PROJECTION_OBSERVED_SEMANTIC_OPERATION = "__client_api_projection_observed__"


def _conversation_transfer_receipt(body: Any) -> "ConversationTransferReceipt":
    """Build the deterministic receipt shared by live execution and replay."""

    from tau2.hyper.client_api.catalog import (
        ConversationTransferReceipt,
        ConversationTransferRequest,
    )

    request = ConversationTransferRequest.model_validate(body)
    digest = hashlib.sha256(
        json.dumps(request, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return ConversationTransferReceipt(
        transfer_id=f"tr_{digest[:32]}",
        status="accepted",
    )


@dataclass
class _AsyncWorkflow:
    """Trial-local state for one deployed asynchronous operation."""

    workflow_id: str
    defect: AsyncCompletionDefect
    operation: Any
    invocation: Any
    call_ordinal: int
    resource_ids: tuple[str, ...]
    started_at: float
    ready_at: float
    delay_seconds: float
    completion_attempted: bool = False
    terminal_body: Optional[dict[str, Any]] = None


@dataclass
class _ProjectionLagState:
    """One trial-local stale projection generation for one resource."""

    defect: ProjectionLagDefect
    resource_id: str
    stale_projection: dict[str, Any]
    trigger_ordinal: int
    delay_seconds: float
    ready_at: Optional[float]
    converged_observed: bool = False


@dataclass(frozen=True)
class _IdempotencyRecord:
    """One successful response retained for a trial-local mutation request."""

    request_sha256: str
    status_code: int
    response_body: Any


def _tool_response_schema(tool) -> dict[str, Any]:
    """Unwrap tau2's internal ``returns`` model for a REST response body."""
    wrapper = tool.returns.model_json_schema()
    properties = wrapper.get("properties") or {}
    body_schema = dict(properties.get("returns") or {})
    if not body_schema:
        return wrapper
    if "$defs" in wrapper:
        body_schema["$defs"] = wrapper["$defs"]
    return body_schema


def _rewrite_schema_refs(value: Any, replacements: dict[str, str]) -> Any:
    """Rewrite local Pydantic definition references for an OpenAPI document."""
    if isinstance(value, dict):
        return {
            key: replacements.get(item, item)
            if key == "$ref"
            else _rewrite_schema_refs(item, replacements)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_rewrite_schema_refs(item, replacements) for item in value]
    return value


def _hoist_schema_definitions(
    schema: dict[str, Any],
    *,
    component_prefix: str,
    components: dict[str, Any],
) -> dict[str, Any]:
    """Move a Pydantic schema's local definitions into OpenAPI components."""
    schema = copy.deepcopy(schema)
    definitions = schema.pop("$defs", {})

    def component_name(name: str) -> str:
        return f"{component_prefix}_{name}" if component_prefix else name

    replacements = {
        f"#/$defs/{name}": f"#/components/schemas/{component_name(name)}"
        for name in definitions
    }
    for name, definition in definitions.items():
        components[component_name(name)] = _rewrite_schema_refs(
            definition, replacements
        )
    return _rewrite_schema_refs(schema, replacements)


def _error_response(description: str) -> dict[str, Any]:
    """Return a documented Client API error response."""
    return {
        "description": description,
        "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/APIError"}}
        },
    }


def _type_schema(annotation: Any) -> dict[str, Any]:
    """Build a JSON Schema for an explicit public API type."""

    return TypeAdapter(annotation).json_schema()


def _path_parameter_names(path: str) -> list[str]:
    return re.findall(r"{([^{}]+)}", path)


def _explicit_openapi_contract(
    environment: Environment,
    operations: tuple[ClientOperation, ...],
    *,
    defect_profile: Optional[DefectProfile] = None,
) -> dict[str, Any]:
    """Build OpenAPI from a maintained domain's explicit Client catalog."""

    schemas: dict[str, Any] = {
        "APIError": {
            "type": "object",
            "required": ["error"],
            "properties": {
                "error": {
                    "type": "object",
                    "required": ["code", "message"],
                    "properties": {
                        "code": {"type": "string"},
                        "message": {"type": "string"},
                        "details": {},
                    },
                }
            },
        }
    }
    paths: dict[str, Any] = {}
    for operation in operations:
        if not operation.advertised:
            continue
        capability = next(
            (
                capability
                for capability in (
                    defect_profile.capabilities if defect_profile else ()
                )
                if capability.operation_id == operation.operation_id
            ),
            None,
        )
        if capability is not None:
            continue
        response_schema = _hoist_schema_definitions(
            _type_schema(operation.response_type),
            component_prefix="",
            components=schemas,
        )
        operation_document: dict[str, Any] = {
            "operationId": operation.operation_id,
            "summary": operation.summary,
            "description": operation.description,
            "x-api-mutates-state": operation.mutates_state,
            "x-api-idempotency": operation.idempotency,
            "x-api-automatic-retries": operation.automatic_retries,
            "x-api-consistency": "strong",
            "x-api-pagination": "none",
            "x-api-request-body-max-bytes": CLIENT_API_MAX_REQUEST_BYTES,
            "x-api-response-body-max-bytes": CLIENT_API_MAX_RESPONSE_BYTES,
            "responses": {
                str(operation.success_status): {
                    "description": "Successful operation",
                    "content": {"application/json": {"schema": response_schema}},
                },
                "400": _error_response("Request does not match the operation schema"),
                "404": _error_response("The requested resource was not found"),
                "405": _error_response("HTTP method not allowed"),
                "409": _error_response(
                    "The resource's current state prevents the operation"
                ),
                "413": _error_response(
                    "JSON request query and body exceed the byte limit"
                ),
                "422": _error_response("The request violates a business constraint"),
                "502": _error_response(
                    "The service produced an invalid or oversized JSON response body"
                ),
            },
        }
        parameters = [
            {
                "name": name,
                "in": "path",
                "required": True,
                "schema": {"type": "string", "minLength": 1},
            }
            for name in _path_parameter_names(operation.path)
        ]
        if operation.query_type is not None:
            query_schema = _hoist_schema_definitions(
                _type_schema(operation.query_type),
                component_prefix="",
                components=schemas,
            )
            required_query = set(query_schema.get("required", []))
            for name, schema in query_schema.get("properties", {}).items():
                parameters.append(
                    {
                        "name": name,
                        "in": "query",
                        "required": name in required_query,
                        "schema": schema,
                    }
                )
        if parameters:
            operation_document["parameters"] = parameters
        if operation.body_type is not None:
            request_schema = _hoist_schema_definitions(
                _type_schema(operation.body_type),
                component_prefix="",
                components=schemas,
            )
            operation_document["requestBody"] = {
                "required": True,
                "content": {"application/json": {"schema": request_schema}},
            }
        paths.setdefault(operation.path, {})[operation.method.lower()] = (
            operation_document
        )
    return {
        "openapi": "3.1.0",
        "jsonSchemaDialect": "https://json-schema.org/draft/2020-12/schema",
        "info": {
            "title": "Customer Service API",
            "version": CLIENT_API_CONTRACT_VERSION,
            "description": (
                "REST API for programmatic access to customer service "
                "business resources. All operations exchange JSON over HTTPS."
            ),
        },
        "paths": paths,
        "components": {"schemas": schemas},
    }


def build_openapi_contract(
    environment: Environment,
    *,
    defect_profile: Optional[DefectProfile] = None,
) -> dict[str, Any]:
    """Build the fixed OpenAPI 3.1 contract for one Client domain."""
    from tau2.hyper.client_api.catalog import client_operations_for_domain

    if defect_profile is not None and defect_profile.domain != environment.domain_name:
        raise ValueError(
            f"Client API defect profile targets {defect_profile.domain!r}, not "
            f"{environment.domain_name!r}"
        )
    explicit_operations = client_operations_for_domain(environment.domain_name)
    if explicit_operations is not None:
        return _explicit_openapi_contract(
            environment,
            explicit_operations,
            defect_profile=defect_profile,
        )
    paths: dict[str, Any] = {}
    schemas: dict[str, Any] = {
        "APIError": {
            "type": "object",
            "required": ["error"],
            "properties": {
                "error": {
                    "type": "object",
                    "required": ["code", "message"],
                    "properties": {
                        "code": {"type": "string"},
                        "message": {"type": "string"},
                    },
                }
            },
        }
    }
    for tool in environment.get_tools():
        function = tool.openai_schema["function"]
        request_schema = _hoist_schema_definitions(
            function.get("parameters")
            or {
                "type": "object",
                "properties": {},
            },
            component_prefix=f"{tool.name}_request",
            components=schemas,
        )
        response_schema = _hoist_schema_definitions(
            _tool_response_schema(tool),
            component_prefix=f"{tool.name}_response",
            components=schemas,
        )
        mutates_state = bool(tool.info.get("mutates_state", True))
        paths[f"/v1/tools/{tool.name}"] = {
            "post": {
                "operationId": tool.name,
                "summary": function.get("description", "").split("\n", 1)[0],
                "description": function.get("description", ""),
                "x-api-mutates-state": mutates_state,
                "x-api-idempotency": ("not_guaranteed" if mutates_state else "safe"),
                "x-api-automatic-retries": (
                    "forbidden" if mutates_state else "allowed"
                ),
                "x-api-consistency": "strong",
                "x-api-pagination": "none",
                "x-api-request-body-max-bytes": CLIENT_API_MAX_REQUEST_BYTES,
                "x-api-response-body-max-bytes": CLIENT_API_MAX_RESPONSE_BYTES,
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {"schema": request_schema},
                    },
                },
                "responses": {
                    "200": {
                        "description": "Successful operation",
                        "content": {"application/json": {"schema": response_schema}},
                    },
                    "400": _error_response("Malformed JSON request body"),
                    "404": _error_response("The requested operation was not found"),
                    "405": _error_response("HTTP method not allowed"),
                    "413": _error_response("JSON request body exceeds the byte limit"),
                    "422": _error_response(
                        "Request was valid but was rejected by a business constraint"
                    ),
                    "502": _error_response(
                        "The service produced an invalid or oversized JSON response body"
                    ),
                },
            }
        }
    return {
        "openapi": "3.1.0",
        "jsonSchemaDialect": "https://json-schema.org/draft/2020-12/schema",
        "info": {
            "title": "Customer Service API",
            "version": CLIENT_API_CONTRACT_VERSION,
            "description": (
                "REST API for programmatic access to customer service "
                "business resources. All operations exchange JSON over HTTPS."
            ),
        },
        "paths": paths,
        "components": {"schemas": schemas},
    }


class ClientAPIRuntime:
    """Trusted host runtime containing the authoritative client state."""

    def __init__(
        self,
        environment: Environment,
        *,
        conversation_id: Optional[str] = None,
        defect_profile: Optional[DefectProfile] = None,
        trial_context: Optional[ClientAPITrialContext] = None,
        deployment_snapshot: Optional[DeploymentSnapshot] = None,
        monotonic_clock: Callable[[], float] = time.monotonic,
    ):
        from tau2.hyper.client_api.catalog import client_operations_for_domain

        self.environment = environment
        if (
            defect_profile is not None
            and defect_profile.domain != environment.domain_name
        ):
            raise ValueError(
                f"Client API defect profile targets {defect_profile.domain!r}, not "
                f"{environment.domain_name!r}"
            )
        self.context = ClientAPIContext(
            conversation_id=conversation_id or f"conv_{uuid.uuid4().hex}"
        )
        self.defect_profile = defect_profile
        self.trial_context = trial_context or ClientAPITrialContext()
        self.deployment_snapshot = deployment_snapshot or empty_deployment_snapshot()
        if defect_profile is None and self.deployment_snapshot.enabled_capability_ids:
            raise ValueError(
                "A non-empty deployment snapshot requires a defect profile"
            )
        if defect_profile is not None:
            allowlisted_capabilities = {
                capability.id for capability in defect_profile.capabilities
            }
            snapshot_capabilities = set(self.deployment_snapshot.enabled_capability_ids)
            unknown_snapshot_capabilities = sorted(
                snapshot_capabilities - allowlisted_capabilities
            )
            if unknown_snapshot_capabilities:
                raise ValueError(
                    "Deployment snapshot contains capabilities not allowlisted "
                    f"by the manifest: {unknown_snapshot_capabilities}"
                )
        self._clock = monotonic_clock
        self._async_lock = threading.Lock()
        self.defect_state = TrialDefectState()
        self._defect_events: list[DefectEvent] = []
        self._explicit_operations = client_operations_for_domain(
            environment.domain_name
        )
        self._operations = (
            {f"/v1/tools/{tool.name}": tool.name for tool in environment.get_tools()}
            if self._explicit_operations is None
            else {}
        )
        if defect_profile is not None:
            known_operation_ids = (
                {operation.operation_id for operation in self._explicit_operations}
                if self._explicit_operations is not None
                else set(self._operations.values())
            )
            unknown_operation_ids = sorted(
                {
                    defect.operation_id
                    for defect in defect_profile.defects
                    if defect.operation_id not in known_operation_ids
                }
            )
            if unknown_operation_ids:
                raise ValueError(
                    "Client API defect profile references unknown operation IDs: "
                    f"{unknown_operation_ids}"
                )
            unknown_capability_operations = sorted(
                capability.operation_id
                for capability in defect_profile.capabilities
                if capability.operation_id not in known_operation_ids
            )
            if unknown_capability_operations:
                raise ValueError(
                    "Client API capabilities reference unknown operation IDs: "
                    f"{unknown_capability_operations}"
                )
            if self._explicit_operations is not None:
                operations_by_id = {
                    operation.operation_id: operation
                    for operation in self._explicit_operations
                }
                for defect in defect_profile.defects:
                    if isinstance(defect, AsyncCompletionDefect):
                        operation = operations_by_id[defect.operation_id]
                        if not operation.mutates_state:
                            raise ValueError(
                                "Async completion requires a mutating Client "
                                f"operation: {defect.operation_id!r}"
                            )
                        if operation.execution != "reference_tool":
                            raise ValueError(
                                "Async completion does not support special "
                                f"execution: {defect.operation_id!r}"
                            )
                        if any(
                            candidate.path == defect.status_path
                            for candidate in self._explicit_operations
                        ):
                            raise ValueError(
                                "Async status path collides with a published "
                                f"operation: {defect.status_path!r}"
                            )
                    elif isinstance(defect, ProjectionLagDefect):
                        referenced = {
                            defect.operation_id,
                            *defect.trigger_operation_ids,
                            *defect.verification_operation_ids,
                            *(surface.operation_id for surface in defect.read_surfaces),
                        }
                        unknown = sorted(referenced - operations_by_id.keys())
                        if unknown:
                            raise ValueError(
                                "Projection lag references unknown operation IDs: "
                                f"{unknown}"
                            )
                        primary = operations_by_id[defect.operation_id]
                        if (
                            primary.mutates_state
                            or primary.body_type is not None
                            or primary.query_type is not None
                            or _path_parameter_names(primary.path)
                            != [defect.resource_id_argument]
                        ):
                            raise ValueError(
                                "Projection lag primary operation must be a "
                                "side-effect-free detail read addressed only by "
                                f"{defect.resource_id_argument!r}"
                            )
                        non_mutating = sorted(
                            operation_id
                            for operation_id in (
                                *defect.trigger_operation_ids,
                                *defect.verification_operation_ids,
                            )
                            if not operations_by_id[operation_id].mutates_state
                        )
                        if non_mutating:
                            raise ValueError(
                                "Projection lag trigger/verification operations "
                                f"must mutate state: {non_mutating}"
                            )
                        invalid_trigger_identity = sorted(
                            operation_id
                            for operation_id in defect.trigger_operation_ids
                            if defect.resource_id_argument
                            not in _path_parameter_names(
                                operations_by_id[operation_id].path
                            )
                        )
                        if invalid_trigger_identity:
                            raise ValueError(
                                "Projection lag triggers must expose the resource "
                                f"ID as a path parameter: {invalid_trigger_identity}"
                            )
                        replay_unsafe = sorted(
                            operation_id
                            for operation_id in defect.trigger_operation_ids
                            if not operations_by_id[operation_id].reference_tool_names
                        )
                        if replay_unsafe:
                            raise ValueError(
                                "Projection lag triggers must declare canonical "
                                f"replay mappings: {replay_unsafe}"
                            )
                        invalid_surfaces = sorted(
                            surface.operation_id
                            for surface in defect.read_surfaces
                            if operations_by_id[surface.operation_id].mutates_state
                        )
                        if invalid_surfaces:
                            raise ValueError(
                                "Projection lag read surfaces must be "
                                f"side-effect-free: {invalid_surfaces}"
                            )
                    elif isinstance(defect, RateLimitDefect):
                        if operations_by_id[defect.operation_id].mutates_state:
                            raise ValueError(
                                "Rate limiting currently supports only safe read "
                                f"operations: {defect.operation_id!r}"
                            )
                    elif isinstance(defect, PostCommitTimeoutDefect):
                        if not operations_by_id[defect.operation_id].mutates_state:
                            raise ValueError(
                                "Post-commit timeout requires a mutating Client "
                                f"operation: {defect.operation_id!r}"
                            )
                    elif isinstance(defect, PaginationDefect):
                        operation = operations_by_id[defect.operation_id]
                        if operation.mutates_state:
                            raise ValueError(
                                "Pagination requires a side-effect-free Client "
                                f"operation: {defect.operation_id!r}"
                            )
        self._operation_calls: list[ClientAPIOperationCall] = []
        self._conversation_transfer: Optional[ConversationTransferReceipt] = None

    @property
    def operation_calls(self) -> tuple[ClientAPIOperationCall, ...]:
        """Return successful canonical operations in execution order."""
        return tuple(self._operation_calls)

    @property
    def defect_events(self) -> tuple[DefectEvent, ...]:
        """Return trusted defect telemetry for the active trial."""

        return tuple(self._defect_events)

    @property
    def conversation_transfer(self) -> Optional[ConversationTransferReceipt]:
        """Return the accepted live transfer for this conversation, if any."""
        return self._conversation_transfer

    def set_state(
        self,
        initialization_data: Optional[InitializationData],
        initialization_actions: Optional[list[EnvFunctionCall]],
        message_history: list,
    ) -> None:
        """Initialize the sole client-side business state for one trial."""
        with self._async_lock:
            self._operation_calls.clear()
            self._conversation_transfer = None
            self.defect_state.reset()
            self._defect_events.clear()
        self.environment.set_state(
            initialization_data=initialization_data,
            initialization_actions=initialization_actions,
            message_history=message_history,
        )

    def set_trial_context(
        self, context: ClientAPITrialContext | dict[str, Any]
    ) -> None:
        """Bind private trial identity without exposing it through ClientAPI."""

        self.trial_context = ClientAPITrialContext.model_validate(context)

    def record_defect_event(self, event: DefectEvent) -> None:
        """Append one trusted trial-local telemetry event."""

        self._defect_events.append(event)

    def deployment_metadata(self) -> dict[str, Any]:
        """Return stable host result metadata for this deployment."""

        if self.defect_profile is None:
            return {}
        return {
            "manifest_id": self.defect_profile.manifest_id,
            "manifest_sha256": self.defect_profile.manifest_sha256,
            "manifest_version": self.defect_profile.manifest_version,
        }

    def _projection_defects(self) -> tuple[ProjectionLagDefect, ...]:
        if self.defect_profile is None:
            return ()
        return tuple(
            defect
            for defect in self.defect_profile.defects
            if isinstance(defect, ProjectionLagDefect)
            and self.defect_profile.defect_selected_for_trial(
                defect, self.trial_context
            )
        )

    def _retry_defects(
        self, operation_id: str
    ) -> tuple[RateLimitDefect | PostCommitTimeoutDefect, ...]:
        if self.defect_profile is None:
            return ()
        return tuple(
            defect
            for defect in self.defect_profile.defects
            if isinstance(defect, (RateLimitDefect, PostCommitTimeoutDefect))
            and defect.operation_id == operation_id
            and self.defect_profile.defect_selected_for_trial(
                defect, self.trial_context
            )
        )

    def _pagination_defect(
        self, operation_id: str, resource_ids: tuple[str, ...]
    ) -> Optional[PaginationDefect]:
        if self.defect_profile is None:
            return None
        return next(
            (
                defect
                for defect in self.defect_profile.defects
                if isinstance(defect, PaginationDefect)
                and defect.operation_id == operation_id
                and self.defect_profile.defect_selected_for_trial(
                    defect, self.trial_context
                )
                and (
                    not defect.activation.resource_ids
                    or set(defect.activation.resource_ids).intersection(resource_ids)
                )
            ),
            None,
        )

    def _pagination_cursor_offset(
        self,
        *,
        defect: PaginationDefect,
        cursor: Optional[str],
        query: dict[str, Any],
        started: float,
    ) -> int | ClientAPIResponse:
        if cursor is None:
            return 0
        if not isinstance(cursor, str):
            return self._explicit_error(
                400,
                "invalid_cursor",
                "The pagination cursor must be a string",
                started=started,
            )
        record = self.defect_state.storage.setdefault("pagination_cursors", {}).get(
            cursor
        )
        query_sha256 = hashlib.sha256(
            json.dumps(
                query, sort_keys=True, separators=(",", ":"), default=str
            ).encode()
        ).hexdigest()
        if (
            record is None
            or record["defect_id"] != defect.id
            or record["query_sha256"] != query_sha256
        ):
            return self._explicit_error(
                400,
                "invalid_cursor",
                "The pagination cursor is invalid for this query",
                started=started,
            )
        return int(record["offset"])

    def _apply_pagination(
        self,
        *,
        defect: PaginationDefect,
        response_body: Any,
        query: dict[str, Any],
        offset: int,
        call_ordinal: int,
    ) -> Any:
        transformed = copy.deepcopy(response_body)
        collection = _value_at_json_path(transformed, defect.collection_path)
        if not isinstance(collection, list):
            raise ValueError("Configured pagination collection is not a list")
        ordered = list(collection)
        if defect.mode != "limit_before_sort" and defect.ordering == (
            "reverse_canonical"
        ):
            ordered.reverse()
        page = ordered[offset : offset + defect.page_size]
        if defect.mode == "limit_before_sort" and defect.ordering == (
            "reverse_canonical"
        ):
            page.reverse()
        parent = _value_at_json_path(transformed, defect.collection_path[:-1])
        leaf = defect.collection_path[-1]
        parent[leaf] = page
        next_offset = offset + len(page)
        if defect.mode == "cursor" and next_offset < len(ordered):
            query_sha256 = hashlib.sha256(
                json.dumps(
                    query, sort_keys=True, separators=(",", ":"), default=str
                ).encode()
            ).hexdigest()
            digest = hashlib.sha256(
                f"{defect.id}:{query_sha256}:{next_offset}".encode()
            ).hexdigest()
            cursor = f"cur_{digest[:24]}"
            self.defect_state.storage.setdefault("pagination_cursors", {})[cursor] = {
                "defect_id": defect.id,
                "query_sha256": query_sha256,
                "offset": next_offset,
            }
            if not isinstance(transformed, dict):
                raise ValueError("Cursor pagination requires an object response")
            transformed[defect.cursor_response_field] = cursor
        self.record_defect_event(
            DefectEvent(
                defect_id=defect.id,
                kind=defect.kind,
                operation_id=defect.operation_id,
                phase="page_returned",
                call_ordinal=call_ordinal,
                details={
                    "offset": offset,
                    "page_items": len(page),
                    "total_items": len(ordered),
                    "mode": defect.mode,
                },
            )
        )
        return transformed

    def _deterministic_delay(
        self,
        defect: RateLimitDefect,
        *,
        call_ordinal: int,
        resource_ids: tuple[str, ...],
    ) -> float:
        identity = {
            "domain": self.environment.domain_name,
            "defect_id": defect.id,
            "seed": defect.seed,
            "task_id": self.trial_context.task_id,
            "trial_id": self.trial_context.trial_id,
            "call_ordinal": call_ordinal,
            "resource_ids": resource_ids,
        }
        digest = hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        fraction = int(digest[:16], 16) / ((1 << 64) - 1)
        return defect.min_delay_seconds + fraction * (
            defect.max_delay_seconds - defect.min_delay_seconds
        )

    @staticmethod
    def _normalized_headers(headers: Optional[dict[str, str]]) -> dict[str, str]:
        """Normalize request header names without exposing them to operations."""

        return {
            str(name).lower(): str(value) for name, value in (headers or {}).items()
        }

    def _apply_rate_limit(
        self,
        *,
        defect: RateLimitDefect,
        call_ordinal: int,
        resource_ids: tuple[str, ...],
        started: float,
    ) -> Optional[ClientAPIResponse]:
        state = self.defect_state.storage.setdefault("rate_limits", {})
        ready_at = state.get(defect.id)
        if ready_at is None:
            if (
                call_ordinal != defect.trigger_call_ordinal
                or not defect.activation.matches(
                    trial_context=self.trial_context,
                    call_ordinal=call_ordinal,
                    resource_ids=resource_ids,
                )
            ):
                return None
            delay = self._deterministic_delay(
                defect, call_ordinal=call_ordinal, resource_ids=resource_ids
            )
            ready_at = self._clock() + delay
            state[defect.id] = ready_at
            self.record_defect_event(
                DefectEvent(
                    defect_id=defect.id,
                    kind=defect.kind,
                    operation_id=defect.operation_id,
                    phase="rate_limited",
                    call_ordinal=call_ordinal,
                    details={"delay_seconds": delay},
                )
            )
        if self._clock() < ready_at:
            return self._explicit_error(
                429,
                "rate_limited",
                "The request rate exceeds the deployed service limit",
                started=started,
                headers={"Retry-After": str(defect.retry_after_seconds)},
            )
        state.pop(defect.id, None)
        self.record_defect_event(
            DefectEvent(
                defect_id=defect.id,
                kind=defect.kind,
                operation_id=defect.operation_id,
                phase="quota_replenished",
                call_ordinal=call_ordinal,
            )
        )
        return None

    def _projection_states(self) -> dict[tuple[str, str], _ProjectionLagState]:
        return self.defect_state.storage.setdefault("projection_lag", {})

    def _operation_by_id(self, operation_id: str) -> Any:
        return next(
            operation
            for operation in self._explicit_operations or ()
            if operation.operation_id == operation_id
        )

    def _operation_enabled(self, operation: Any) -> bool:
        if self.defect_profile is None:
            return True
        capability = next(
            (
                capability
                for capability in self.defect_profile.capabilities
                if capability.operation_id == operation.operation_id
            ),
            None,
        )
        return capability is None or self.deployment_snapshot.enables(capability.id)

    def _capture_detail_projection(
        self, defect: ProjectionLagDefect, resource_id: str
    ) -> dict[str, Any]:
        """Read a canonical detail projection without producing a public call."""

        from tau2.hyper.client_api.catalog import adapt_operation_response

        operation = self._operation_by_id(defect.operation_id)
        invocation = operation.invoke(
            {defect.resource_id_argument: resource_id}, None, None
        )
        result = self.environment.make_tool_call(
            invocation.tool_name,
            requestor="assistant",
            **invocation.arguments,
        )
        normalized = adapt_operation_response(
            operation, invocation, result, self.environment
        )
        adapter = TypeAdapter(operation.response_type)
        body = adapter.dump_python(
            adapter.validate_python(normalized), mode="json", exclude_none=True
        )
        if not isinstance(body, dict):
            raise ValueError("Projection lag detail reads must return JSON objects")
        if (
            body.get(
                next(
                    surface.resource_id_field
                    for surface in defect.read_surfaces
                    if surface.operation_id == defect.operation_id
                )
            )
            != resource_id
        ):
            raise ValueError("Projection lag detail response resource ID mismatched")
        return body

    @staticmethod
    def _projection_resource_id(
        defect: ProjectionLagDefect, arguments: dict[str, Any]
    ) -> Optional[str]:
        value = arguments.get(defect.resource_id_argument)
        return str(value) if value is not None else None

    def _projection_delay(
        self,
        defect: ProjectionLagDefect,
        resource_id: str,
        trigger_ordinal: int,
        arguments: dict[str, Any],
    ) -> float:
        identity = {
            "domain": self.environment.domain_name,
            "defect_id": defect.id,
            "seed": defect.seed,
            "task_id": self.trial_context.task_id,
            "trial_id": self.trial_context.trial_id,
            "resource_id": resource_id,
            "trigger_ordinal": trigger_ordinal,
            "arguments": arguments,
        }
        digest = hashlib.sha256(
            json.dumps(
                identity, sort_keys=True, separators=(",", ":"), default=str
            ).encode("utf-8")
        ).hexdigest()
        fraction = int(digest[:16], 16) / ((1 << 64) - 1)
        return defect.min_delay_seconds + fraction * (
            defect.max_delay_seconds - defect.min_delay_seconds
        )

    def _install_projection_state(
        self,
        *,
        defect: ProjectionLagDefect,
        resource_id: str,
        stale_projection: dict[str, Any],
        trigger_ordinal: int,
        arguments: dict[str, Any],
        arm_now: bool,
    ) -> None:
        delay = self._projection_delay(defect, resource_id, trigger_ordinal, arguments)
        ready_at = self._clock() + delay if arm_now else None
        self._projection_states()[(defect.id, resource_id)] = _ProjectionLagState(
            defect=defect,
            resource_id=resource_id,
            stale_projection=copy.deepcopy(stale_projection),
            trigger_ordinal=trigger_ordinal,
            delay_seconds=delay,
            ready_at=ready_at,
        )
        self.record_defect_event(
            DefectEvent(
                defect_id=defect.id,
                kind=defect.kind,
                operation_id=defect.operation_id,
                phase="propagation_started" if arm_now else "projection_watched",
                call_ordinal=trigger_ordinal,
                details={
                    "resource_id": resource_id,
                    "delay_seconds": delay,
                },
            )
        )

    def _prepare_projection_triggers(
        self, operation_id: str, arguments: dict[str, Any], call_ordinal: int
    ) -> list[tuple[ProjectionLagDefect, str, dict[str, Any]]]:
        prepared = []
        for defect in self._projection_defects():
            if operation_id not in defect.trigger_operation_ids:
                continue
            resource_id = self._projection_resource_id(defect, arguments)
            if resource_id is None or not defect.activation.matches(
                trial_context=self.trial_context,
                call_ordinal=call_ordinal,
                resource_ids=(resource_id,),
            ):
                continue
            if defect.capture_timing == "before_trigger":
                try:
                    projection = self._capture_detail_projection(defect, resource_id)
                except Exception:
                    self.record_defect_event(
                        DefectEvent(
                            defect_id=defect.id,
                            kind=defect.kind,
                            operation_id=defect.operation_id,
                            phase="capture_failed",
                            call_ordinal=call_ordinal,
                            details={"resource_id": resource_id},
                        )
                    )
                else:
                    prepared.append((defect, resource_id, projection))
        return prepared

    def _finish_projection_triggers(
        self,
        operation_id: str,
        arguments: dict[str, Any],
        call_ordinal: int,
        prepared: list[tuple[ProjectionLagDefect, str, dict[str, Any]]],
    ) -> None:
        prepared_by_id = {
            defect.id: (resource_id, body) for defect, resource_id, body in prepared
        }
        for defect in self._projection_defects():
            if operation_id not in defect.trigger_operation_ids:
                continue
            resource_id = self._projection_resource_id(defect, arguments)
            if resource_id is None or not defect.activation.matches(
                trial_context=self.trial_context,
                call_ordinal=call_ordinal,
                resource_ids=(resource_id,),
            ):
                continue
            if defect.capture_timing == "before_trigger":
                prepared_projection = prepared_by_id.get(defect.id)
                if prepared_projection is None:
                    continue
                resource_id, stale = prepared_projection
                arm_now = True
            else:
                try:
                    stale = self._capture_detail_projection(defect, resource_id)
                except Exception:
                    self.record_defect_event(
                        DefectEvent(
                            defect_id=defect.id,
                            kind=defect.kind,
                            operation_id=defect.operation_id,
                            phase="capture_failed",
                            call_ordinal=call_ordinal,
                            details={"resource_id": resource_id},
                        )
                    )
                    continue
                arm_now = False
            self._install_projection_state(
                defect=defect,
                resource_id=resource_id,
                stale_projection=stale,
                trigger_ordinal=call_ordinal,
                arguments=arguments,
                arm_now=arm_now,
            )

    def sync_environment(self) -> None:
        """Synchronize canonical tools and arm watched projection changes."""

        self.environment.sync_tools()
        for state in self._projection_states().values():
            if state.ready_at is not None:
                continue
            try:
                current = self._capture_detail_projection(
                    state.defect, state.resource_id
                )
            except Exception:
                self.record_defect_event(
                    DefectEvent(
                        defect_id=state.defect.id,
                        kind=state.defect.kind,
                        operation_id=state.defect.operation_id,
                        phase="capture_failed",
                        call_ordinal=state.trigger_ordinal,
                        details={"resource_id": state.resource_id},
                    )
                )
                continue
            if current == state.stale_projection:
                continue
            state.ready_at = self._clock() + state.delay_seconds
            self.record_defect_event(
                DefectEvent(
                    defect_id=state.defect.id,
                    kind=state.defect.kind,
                    operation_id=state.defect.operation_id,
                    phase="propagation_started",
                    call_ordinal=state.trigger_ordinal,
                    details={
                        "resource_id": state.resource_id,
                        "delay_seconds": state.delay_seconds,
                    },
                )
            )

    def _apply_projection_lag(
        self, operation_id: str, response_body: dict[str, Any], call_ordinal: int
    ) -> dict[str, Any]:
        transformed = copy.deepcopy(response_body)
        for defect in self._projection_defects():
            surface = next(
                (
                    candidate
                    for candidate in defect.read_surfaces
                    if candidate.operation_id == operation_id
                ),
                None,
            )
            if surface is None:
                continue
            candidates = (
                [transformed]
                if not surface.collection_path
                else _value_at_json_path(transformed, surface.collection_path)
            )
            if not isinstance(candidates, list):
                candidates = [candidates]
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                resource_id = candidate.get(surface.resource_id_field)
                state = self._projection_states().get((defect.id, str(resource_id)))
                if state is None or state.ready_at is None:
                    continue
                if self._clock() < state.ready_at:
                    if surface.collection_path:
                        for field in surface.projected_fields:
                            candidate[field] = copy.deepcopy(
                                state.stale_projection[field]
                            )
                    else:
                        transformed = copy.deepcopy(state.stale_projection)
                    self.record_defect_event(
                        DefectEvent(
                            defect_id=defect.id,
                            kind=defect.kind,
                            operation_id=operation_id,
                            phase="stale_read",
                            call_ordinal=call_ordinal,
                            details={"resource_id": state.resource_id},
                        )
                    )
                elif not state.converged_observed:
                    state.converged_observed = True
                    self._operation_calls.append(
                        ClientAPIOperationCall(
                            operation_id=_PROJECTION_OBSERVED_SEMANTIC_OPERATION,
                            arguments={
                                "defect_id": defect.id,
                                "resource_id": state.resource_id,
                            },
                        )
                    )
                    self.record_defect_event(
                        DefectEvent(
                            defect_id=defect.id,
                            kind=defect.kind,
                            operation_id=operation_id,
                            phase="converged",
                            call_ordinal=call_ordinal,
                            details={"resource_id": state.resource_id},
                        )
                    )
        return transformed

    def _record_projection_verification(self, operation_id: str) -> None:
        states = tuple(self._projection_states().values())
        for defect in self._projection_defects():
            if operation_id not in defect.verification_operation_ids:
                continue
            matching_states = [
                state for state in states if state.defect.id == defect.id
            ]
            task_selected = self.defect_profile.defect_selected_for_trial(
                defect, self.trial_context
            )
            if (
                defect.require_trigger_before_verification
                and task_selected
                and not matching_states
            ):
                violations = self.defect_state.storage.setdefault(
                    "projection_verification_violations", []
                )
                violation = {
                    "defect_id": defect.id,
                    "operation_id": operation_id,
                    "reason": "projection_trigger_not_observed",
                }
                if violation not in violations:
                    violations.append(violation)
            for state in matching_states:
                if state.converged_observed:
                    continue
                violations = self.defect_state.storage.setdefault(
                    "projection_verification_violations", []
                )
                violation = {
                    "defect_id": state.defect.id,
                    "operation_id": operation_id,
                    "resource_id": state.resource_id,
                }
                if violation not in violations:
                    violations.append(violation)

    def defect_report(self) -> dict[str, Any]:
        """Return host-only defect verification; never exposed to candidates."""

        violations = copy.deepcopy(
            self.defect_state.storage.get("projection_verification_violations", [])
        )
        violations.extend(
            copy.deepcopy(self.defect_state.storage.get("retry_safety_violations", []))
        )
        for ambiguity in self.defect_state.storage.get(
            "unresolved_post_commit_timeouts", {}
        ).values():
            violations.append(
                {
                    "defect_id": ambiguity["defect_id"],
                    "reason": "post_commit_outcome_not_verified",
                    "resource_ids": list(ambiguity["resource_ids"]),
                }
            )
        return {
            "verification": {
                "status": "failed" if violations else "passed",
                "violations": violations,
            },
            "events": [event.model_dump(mode="json") for event in self.defect_events],
        }

    def replay_operation(self, operation: ToolCall) -> ToolMessage:
        """Replay one trusted canonical operation against authoritative state."""

        if operation.requestor != "assistant":
            raise ValueError(
                "Trusted Client API semantic operations must be assistant calls"
            )
        if operation.name == _PROJECTION_OBSERVED_SEMANTIC_OPERATION:
            if set(operation.arguments) != {"defect_id", "resource_id"} or not all(
                isinstance(operation.arguments[field], str)
                for field in ("defect_id", "resource_id")
            ):
                raise ValueError("Trusted projection observation is malformed")
            defect_id = operation.arguments.get("defect_id")
            resource_id = operation.arguments.get("resource_id")
            state = self._projection_states().get((defect_id, str(resource_id)))
            if state is None:
                raise ValueError(
                    "Trusted projection observation has no matching projection "
                    f"state: {defect_id!r}/{resource_id!r}"
                )
            if state.converged_observed:
                raise ValueError("Trusted projection observation was replayed twice")
            state.converged_observed = True
            self.record_defect_event(
                DefectEvent(
                    defect_id=state.defect.id,
                    kind=state.defect.kind,
                    operation_id=state.defect.operation_id,
                    phase="convergence_replayed",
                    call_ordinal=state.trigger_ordinal,
                    details={"resource_id": state.resource_id},
                )
            )
            return ToolMessage(
                id=operation.id,
                role="tool",
                content=json.dumps({"projection_observed": True}),
            )
        with self._async_lock:
            matching_workflows = [
                workflow
                for workflow in self._workflows(create=False).values()
                if workflow.invocation.tool_name == operation.name
                and workflow.invocation.arguments == operation.arguments
            ]
            if len(matching_workflows) > 1:
                raise ValueError(
                    "Trusted canonical operation ambiguously matches multiple "
                    f"pending workflows: {operation.name!r}"
                )
            if matching_workflows:
                workflow = matching_workflows[0]
                if workflow.completion_attempted:
                    raise ValueError(
                        "Trusted canonical operation repeats an async workflow "
                        f"completion: {workflow.workflow_id!r}"
                    )
                terminal = self._complete_async_workflow(workflow)
                if terminal["status"] != "succeeded":
                    raise ValueError(
                        "Trusted canonical operation failed while restoring async "
                        f"workflow {workflow.workflow_id!r}"
                    )
                return ToolMessage(
                    id=operation.id,
                    role="tool",
                    content=json.dumps(terminal["result"]),
                )
        replay_trigger = next(
            (
                candidate
                for candidate in self._explicit_operations or ()
                if operation.name in candidate.reference_tool_names
            ),
            None,
        )
        replay_ordinal = (
            self.defect_state.next_call_ordinal(replay_trigger.operation_id)
            if replay_trigger is not None
            else 1
        )
        if replay_trigger is not None:
            self._record_projection_verification(replay_trigger.operation_id)
        prepared = (
            self._prepare_projection_triggers(
                replay_trigger.operation_id,
                operation.arguments,
                replay_ordinal,
            )
            if replay_trigger is not None
            else []
        )
        is_conversation_transfer = operation.name == "transfer_to_human_agents" and any(
            candidate.execution == "conversation_transfer"
            for candidate in self._explicit_operations or ()
        )
        if is_conversation_transfer:
            if self._conversation_transfer is not None:
                raise ValueError(
                    "Trusted canonical conversation transfer was replayed twice"
                )
            self._conversation_transfer = _conversation_transfer_receipt(
                operation.arguments
            )
            response = ToolMessage(
                id=operation.id,
                role="tool",
                content=json.dumps(self._conversation_transfer.model_dump()),
            )
        else:
            tools = self.environment.tools
            if tools is None or not tools.has_tool(operation.name):
                raise ValueError(
                    f"Trusted canonical operation {operation.name!r} is unavailable"
                )
            response = self.environment.get_response(operation)
        if response.error:
            raise ValueError(
                f"Trusted canonical operation {operation.name!r} failed during "
                f"replay: {response.content}"
            )
        self.sync_environment()
        if replay_trigger is not None:
            self._finish_projection_triggers(
                replay_trigger.operation_id,
                operation.arguments,
                replay_ordinal,
                prepared,
            )
        self._operation_calls.append(
            ClientAPIOperationCall(
                operation_id=operation.name,
                arguments=copy.deepcopy(operation.arguments),
            )
        )
        return response

    def snapshot(self) -> Optional[dict[str, Any]]:
        """Return authoritative assistant-visible state for trusted scoring."""
        tools = self.environment.tools
        if tools is None or tools.db is None:
            return None
        return tools.db.model_dump(mode="json", by_alias=True)

    def request(
        self,
        *,
        method: str,
        path: str,
        query: Optional[dict[str, Any]] = None,
        body: Any = None,
        headers: Optional[dict[str, str]] = None,
    ) -> ClientAPIResponse:
        """Execute a REST request against the trusted client environment."""
        normalized_headers = self._normalized_headers(headers)
        started = self._clock()
        response_headers = {"content-type": "application/json"}
        try:
            request_size = _json_size_bytes(body)
            if query:
                request_size += _json_size_bytes(dict(query))
        except (TypeError, ValueError):
            return ClientAPIResponse(
                status_code=400,
                body={
                    "error": {
                        "code": "invalid_body",
                        "message": "JSON request query and body must be serializable",
                    }
                },
                headers=response_headers,
                elapsed_seconds=self._clock() - started,
            )
        if request_size > CLIENT_API_MAX_REQUEST_BYTES:
            return ClientAPIResponse(
                status_code=413,
                body={
                    "error": {
                        "code": "request_too_large",
                        "message": (
                            "JSON request query and body exceed "
                            f"{CLIENT_API_MAX_REQUEST_BYTES} bytes"
                        ),
                    }
                },
                headers=response_headers,
                elapsed_seconds=self._clock() - started,
            )
        if self._explicit_operations is not None:
            return self._request_explicit(
                method=method,
                path=path,
                query=dict(query or {}),
                body=body,
                headers=normalized_headers,
                started=started,
            )
        if method.upper() != "POST":
            return ClientAPIResponse(
                status_code=405,
                body={
                    "error": {
                        "code": "method_not_allowed",
                        "message": "This operation requires POST",
                    }
                },
                headers={**response_headers, "allow": "POST"},
                elapsed_seconds=self._clock() - started,
            )
        tool_name = self._operations.get(path)
        if tool_name is None:
            return ClientAPIResponse(
                status_code=404,
                body={
                    "error": {
                        "code": "operation_not_found",
                        "message": f"No client operation exists at {path}",
                    }
                },
                headers=response_headers,
                elapsed_seconds=self._clock() - started,
            )
        arguments: dict[str, Any] = {}
        if query:
            arguments.update(query)
        if body is not None:
            if not isinstance(body, dict):
                return ClientAPIResponse(
                    status_code=400,
                    body={
                        "error": {
                            "code": "invalid_body",
                            "message": "JSON request body must be an object",
                        }
                    },
                    headers=response_headers,
                    elapsed_seconds=self._clock() - started,
                )
            arguments.update(body)
        try:
            result = self.environment.make_tool_call(
                tool_name,
                requestor="assistant",
                **arguments,
            )
            self.sync_environment()
            self._operation_calls.append(
                ClientAPIOperationCall(
                    operation_id=tool_name,
                    arguments=copy.deepcopy(arguments),
                )
            )
            status_code = 200
            response_body = _json_value(result)
        except Exception:
            status_code = 422
            response_body = {
                "error": {
                    "code": "operation_rejected",
                    "message": "The operation rejected the request",
                }
            }
        try:
            response_size = _json_size_bytes(response_body)
        except (TypeError, ValueError):
            status_code = 502
            response_body = {
                "error": {
                    "code": "invalid_response_body",
                    "message": "The operation returned a non-JSON response body",
                }
            }
            response_size = _json_size_bytes(response_body)
        if response_size > CLIENT_API_MAX_RESPONSE_BYTES:
            status_code = 502
            response_body = {
                "error": {
                    "code": "response_too_large",
                    "message": (
                        "JSON response body exceeds "
                        f"{CLIENT_API_MAX_RESPONSE_BYTES} bytes"
                    ),
                }
            }
            response_size = _json_size_bytes(response_body)
        response_headers["content-length"] = str(response_size)
        return ClientAPIResponse(
            status_code=status_code,
            body=response_body,
            headers=response_headers,
            elapsed_seconds=self._clock() - started,
        )

    @staticmethod
    def _match_path_template(template: str, path: str) -> Optional[dict[str, str]]:
        """Match and decode a concrete request path against a path template."""

        cursor = 0
        pattern_parts = ["^"]
        for match in re.finditer(r"{([^{}]+)}", template):
            pattern_parts.append(re.escape(template[cursor : match.start()]))
            pattern_parts.append(f"(?P<{match.group(1)}>[^/]+)")
            cursor = match.end()
        pattern_parts.append(re.escape(template[cursor:]))
        pattern_parts.append("$")
        matched = re.match("".join(pattern_parts), path)
        if matched is None:
            return None
        return {name: unquote(value) for name, value in matched.groupdict().items()}

    @classmethod
    def _match_operation_path(
        cls, operation: ClientOperation, path: str
    ) -> Optional[dict[str, str]]:
        """Match one published operation route."""

        return cls._match_path_template(operation.path, path)

    @staticmethod
    def _path_specificity(operation: ClientOperation) -> tuple[int, int]:
        """Rank literal routes ahead of overlapping parameterized routes."""

        parameter_count = len(_path_parameter_names(operation.path))
        literal_length = len(re.sub(r"{[^{}]+}", "", operation.path))
        return (-parameter_count, literal_length)

    def _explicit_error(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        started: float,
        details: Any = None,
        headers: Optional[dict[str, str]] = None,
    ) -> ClientAPIResponse:
        error: dict[str, Any] = {"code": code, "message": message}
        if details is not None:
            error["details"] = details
        return ClientAPIResponse(
            status_code=status_code,
            body={"error": error},
            headers={"content-type": "application/json", **(headers or {})},
            elapsed_seconds=self._clock() - started,
        )

    @staticmethod
    def _classify_business_error(error: Exception) -> tuple[int, str]:
        message = str(error).lower()
        if "not found" in message or "does not exist" in message:
            return 404, "resource_not_found"
        conflict_fragments = (
            "non-pending",
            "not pending",
            "non-delivered",
            "not delivered",
            "already",
            "not available",
            "not enough seats",
            "number of passengers does not match",
            "cannot be",
        )
        if any(fragment in message for fragment in conflict_fragments):
            return 409, "resource_conflict"
        return 422, "business_rule_violation"

    def _json_response(
        self,
        status_code: int,
        body: dict[str, Any],
        *,
        started: float,
        headers: Optional[dict[str, str]] = None,
    ) -> ClientAPIResponse:
        """Build one bounded JSON response using the injected monotonic clock."""

        try:
            response_size = _json_size_bytes(body)
        except (TypeError, ValueError):
            return self._explicit_error(
                502,
                "invalid_response_body",
                "The workflow returned a non-JSON response body",
                started=started,
            )
        if response_size > CLIENT_API_MAX_RESPONSE_BYTES:
            return self._explicit_error(
                502,
                "response_too_large",
                f"JSON response body exceeds {CLIENT_API_MAX_RESPONSE_BYTES} bytes",
                started=started,
            )
        return ClientAPIResponse(
            status_code=status_code,
            body=body,
            headers={
                "content-type": "application/json",
                "content-length": str(response_size),
                **(headers or {}),
            },
            elapsed_seconds=self._clock() - started,
        )

    def _async_defects(self) -> tuple[AsyncCompletionDefect, ...]:
        """Return the active deployment's async declarations."""

        if self.defect_profile is None:
            return ()
        return tuple(
            defect
            for defect in self.defect_profile.defects
            if isinstance(defect, AsyncCompletionDefect)
        )

    def _workflows(self, *, create: bool = True) -> dict[str, _AsyncWorkflow]:
        """Return the mutable workflow map owned by the current trial."""

        if create:
            return self.defect_state.storage.setdefault("async_workflows", {})
        return self.defect_state.storage.get("async_workflows", {})

    def _accept_async_workflow(
        self,
        *,
        defect: AsyncCompletionDefect,
        operation: ClientOperation,
        invocation: Any,
        call_ordinal: int,
        resource_ids: tuple[str, ...],
        started: float,
    ) -> ClientAPIResponse:
        """Store an async workflow without executing its canonical mutation."""

        profile = self.defect_profile
        if profile is None:
            raise RuntimeError("Async completion requires a deployment profile")
        identity = {
            "domain": self.environment.domain_name,
            "defect_id": defect.id,
            "seed": defect.seed,
            "task_id": self.trial_context.task_id,
            "trial_id": self.trial_context.trial_id,
            "operation_id": operation.operation_id,
            "call_ordinal": call_ordinal,
            "resource_ids": resource_ids,
            "arguments": invocation.arguments,
        }
        digest = hashlib.sha256(
            json.dumps(
                identity,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest()
        workflow_id = f"wf_{digest[:24]}"
        fraction = int(digest[24:40], 16) / ((1 << 64) - 1)
        delay_seconds = defect.min_delay_seconds + fraction * (
            defect.max_delay_seconds - defect.min_delay_seconds
        )
        now = self._clock()
        workflow = _AsyncWorkflow(
            workflow_id=workflow_id,
            defect=defect,
            operation=operation,
            invocation=invocation,
            call_ordinal=call_ordinal,
            resource_ids=resource_ids,
            started_at=now,
            ready_at=now + delay_seconds,
            delay_seconds=delay_seconds,
        )
        with self._async_lock:
            workflows = self._workflows()
            if workflow_id in workflows:
                raise RuntimeError(f"Duplicate async workflow ID: {workflow_id}")
            workflows[workflow_id] = workflow
        location = defect.status_path.replace("{workflow_id}", workflow_id)
        self.record_defect_event(
            DefectEvent(
                defect_id=defect.id,
                kind=defect.kind,
                operation_id=operation.operation_id,
                phase="accepted",
                call_ordinal=call_ordinal,
                details={
                    "workflow_id": workflow_id,
                    "delay_seconds": delay_seconds,
                },
            )
        )
        return self._json_response(
            202,
            {"workflow_id": workflow_id, "status": "pending"},
            started=started,
            headers={
                "Location": location,
                "Retry-After": str(defect.retry_after_seconds),
            },
        )

    def _complete_async_workflow(self, workflow: _AsyncWorkflow) -> dict[str, Any]:
        """Execute and cache one terminal workflow transition exactly once."""

        if workflow.terminal_body is not None:
            return workflow.terminal_body
        if workflow.completion_attempted:
            raise RuntimeError(
                f"Async workflow {workflow.workflow_id!r} has no terminal result"
            )
        workflow.completion_attempted = True
        phase = "completed"
        event_details: dict[str, Any] = {"workflow_id": workflow.workflow_id}
        prepared = self._prepare_projection_triggers(
            workflow.operation.operation_id,
            workflow.invocation.arguments,
            workflow.call_ordinal,
        )
        try:
            result = self.environment.make_tool_call(
                workflow.invocation.tool_name,
                requestor="assistant",
                **workflow.invocation.arguments,
            )
        except Exception as error:
            phase = "failed"
            _, code = self._classify_business_error(error)
            terminal_body = {
                "workflow_id": workflow.workflow_id,
                "status": "failed",
                "error": {
                    "code": code,
                    "message": _PUBLIC_BUSINESS_ERROR_MESSAGES[code],
                },
            }
        else:
            # Once the canonical tool returns, the mutation is authoritative. Record
            # that fact before response-presentation work that can still fail.
            self._operation_calls.append(
                ClientAPIOperationCall(
                    operation_id=workflow.invocation.tool_name,
                    arguments=copy.deepcopy(workflow.invocation.arguments),
                )
            )
            try:
                self.sync_environment()
                self._finish_projection_triggers(
                    workflow.operation.operation_id,
                    workflow.invocation.arguments,
                    workflow.call_ordinal,
                    prepared,
                )
                from tau2.hyper.client_api.catalog import adapt_operation_response

                normalized = adapt_operation_response(
                    workflow.operation,
                    workflow.invocation,
                    result,
                    self.environment,
                )
                response_adapter = TypeAdapter(workflow.operation.response_type)
                result_body = response_adapter.dump_python(
                    response_adapter.validate_python(normalized),
                    mode="json",
                    exclude_none=True,
                )
                if self.defect_profile is not None:
                    for kind in (
                        "response_value_map",
                        "response_amount_sign",
                        "response_field_rename",
                        "response_date_to_datetime",
                    ):
                        for response_defect in self.defect_profile.matching_defects(
                            kind=kind,
                            operation_id=workflow.operation.operation_id,
                            trial_context=self.trial_context,
                            call_ordinal=workflow.call_ordinal,
                            resource_ids=workflow.resource_ids,
                        ):
                            result_body, details = apply_response_defect(
                                result_body, response_defect
                            )
                            self.record_defect_event(
                                DefectEvent(
                                    defect_id=response_defect.id,
                                    kind=response_defect.kind,
                                    operation_id=workflow.operation.operation_id,
                                    phase="response_transformed",
                                    call_ordinal=workflow.call_ordinal,
                                    details=details,
                                )
                            )
                terminal_body = {
                    "workflow_id": workflow.workflow_id,
                    "status": "succeeded",
                    "result": result_body,
                }
                event_details["response_available"] = True
            except Exception:
                # A presentation error cannot roll back a completed mutation. Keep
                # terminal status truthful and redact the private adapter failure.
                terminal_body = {
                    "workflow_id": workflow.workflow_id,
                    "status": "succeeded",
                    "result": None,
                    "warning": {
                        "code": "invalid_response_body",
                        "message": (
                            "The completed operation could not normalize its response"
                        ),
                    },
                }
                event_details["response_available"] = False
        workflow.terminal_body = terminal_body
        self.record_defect_event(
            DefectEvent(
                defect_id=workflow.defect.id,
                kind=workflow.defect.kind,
                operation_id=workflow.operation.operation_id,
                phase=phase,
                call_ordinal=workflow.call_ordinal,
                details=event_details,
            )
        )
        return terminal_body

    def _request_async_status(
        self,
        *,
        method: str,
        path: str,
        query: dict[str, Any],
        body: Any,
        started: float,
    ) -> Optional[ClientAPIResponse]:
        """Serve an unadvertised deployed workflow-status resource."""

        selected = None
        for defect in self._async_defects():
            parameters = self._match_path_template(defect.status_path, path)
            if parameters is not None:
                selected = (defect, parameters["workflow_id"])
                break
        if selected is None:
            return None
        defect, workflow_id = selected
        if method.upper() != "GET":
            return self._explicit_error(
                405,
                "method_not_allowed",
                "This resource requires GET",
                started=started,
                headers={"allow": "GET"},
            )
        if query or body not in (None, {}):
            return self._explicit_error(
                400,
                "invalid_request",
                "Workflow status does not accept query parameters or a body",
                started=started,
            )
        with self._async_lock:
            workflow = self._workflows(create=False).get(workflow_id)
            if workflow is None or workflow.defect.id != defect.id:
                return self._explicit_error(
                    404,
                    "workflow_not_found",
                    "The requested workflow was not found",
                    started=started,
                )
            if workflow.terminal_body is not None:
                terminal_body = workflow.terminal_body
            elif self._clock() < workflow.ready_at:
                return self._json_response(
                    200,
                    {"workflow_id": workflow_id, "status": "pending"},
                    started=started,
                    headers={"Retry-After": str(defect.retry_after_seconds)},
                )
            else:
                terminal_body = self._complete_async_workflow(workflow)
        return self._json_response(200, terminal_body, started=started)

    def _request_explicit(
        self,
        *,
        method: str,
        path: str,
        query: dict[str, Any],
        body: Any,
        headers: dict[str, str],
        started: float,
    ) -> ClientAPIResponse:
        """Validate and execute one explicit maintained-domain operation."""

        async_status = self._request_async_status(
            method=method,
            path=path,
            query=query,
            body=body,
            started=started,
        )
        if async_status is not None:
            return async_status

        path_matches: list[tuple[ClientOperation, dict[str, str]]] = []
        for operation in self._explicit_operations or ():
            if not self._operation_enabled(operation):
                continue
            path_parameters = self._match_operation_path(operation, path)
            if path_parameters is not None:
                path_matches.append((operation, path_parameters))
        if not path_matches:
            return self._explicit_error(
                404,
                "operation_not_found",
                f"No client operation exists at {path}",
                started=started,
            )
        highest_specificity = max(
            self._path_specificity(operation) for operation, _ in path_matches
        )
        path_matches = [
            (operation, parameters)
            for operation, parameters in path_matches
            if self._path_specificity(operation) == highest_specificity
        ]
        selected = next(
            (
                (operation, path_parameters)
                for operation, path_parameters in path_matches
                if operation.method == method.upper()
            ),
            None,
        )
        if selected is None:
            allowed = sorted({operation.method for operation, _ in path_matches})
            return self._explicit_error(
                405,
                "method_not_allowed",
                f"This resource requires one of: {', '.join(allowed)}",
                started=started,
                headers={"allow": ", ".join(allowed)},
            )
        operation, path_parameters = selected
        resource_ids = tuple(path_parameters.values())
        pagination_defect = self._pagination_defect(
            operation.operation_id, resource_ids
        )
        pagination_cursor = None
        if pagination_defect is not None:
            query = dict(query)
            pagination_cursor = query.pop(
                pagination_defect.cursor_query_parameter, None
            )
        if self._conversation_transfer is not None:
            return self._explicit_error(
                409,
                "conversation_transferred",
                "The conversation has already been transferred",
                started=started,
            )
        if (
            operation.execution == "conversation_transfer"
            and path_parameters.get("conversation_id") != self.context.conversation_id
        ):
            return self._explicit_error(
                404,
                "conversation_not_found",
                "The requested conversation was not found",
                started=started,
            )
        try:
            if operation.query_type is None:
                if query:
                    raise ValueError("This operation does not accept query parameters")
                parsed_query = None
            else:
                parsed_query = TypeAdapter(operation.query_type).validate_python(query)
            if operation.body_type is None:
                if body not in (None, {}):
                    raise ValueError("This operation does not accept a request body")
                parsed_body = None
            else:
                parsed_body = TypeAdapter(operation.body_type).validate_python(body)
        except (ValidationError, ValueError) as error:
            details = (
                error.errors(
                    include_url=False,
                    include_context=False,
                    include_input=False,
                )
                if isinstance(error, ValidationError)
                else None
            )
            return self._explicit_error(
                400,
                "invalid_request",
                "Request does not match the operation schema",
                started=started,
                details=details,
            )
        prospective_call_ordinal = (
            self.defect_state.call_counts.get(operation.operation_id, 0) + 1
        )
        pagination_offset: int | ClientAPIResponse = 0
        if pagination_defect is not None:
            if not pagination_defect.activation.matches(
                trial_context=self.trial_context,
                call_ordinal=prospective_call_ordinal,
                resource_ids=resource_ids,
            ):
                pagination_defect = None
            else:
                pagination_offset = self._pagination_cursor_offset(
                    defect=pagination_defect,
                    cursor=pagination_cursor,
                    query=query,
                    started=started,
                )
                if isinstance(pagination_offset, ClientAPIResponse):
                    return pagination_offset
        call_ordinal = self.defect_state.next_call_ordinal(operation.operation_id)
        try:
            invocation = operation.invoke(
                path_parameters,
                parsed_query,
                parsed_body,
            )
            unresolved = self.defect_state.storage.setdefault(
                "unresolved_post_commit_timeouts", {}
            )
            if operation.operation_id == "getCustomer":
                for ambiguity_key, ambiguity in list(unresolved.items()):
                    if set(ambiguity["resource_ids"]).intersection(resource_ids):
                        unresolved.pop(ambiguity_key)
                        self.record_defect_event(
                            DefectEvent(
                                defect_id=ambiguity["defect_id"],
                                kind="post_commit_timeout",
                                operation_id=operation.operation_id,
                                phase="outcome_reconciled",
                                call_ordinal=call_ordinal,
                            )
                        )
            retry_defects = self._retry_defects(operation.operation_id)
            timeout_defect = next(
                (
                    defect
                    for defect in retry_defects
                    if isinstance(defect, PostCommitTimeoutDefect)
                    and (
                        not defect.activation.resource_ids
                        or set(defect.activation.resource_ids).intersection(
                            resource_ids
                        )
                    )
                ),
                None,
            )
            idempotency_key = None
            idempotency_record_key = None
            request_sha256 = None
            if timeout_defect is not None:
                idempotency_key = headers.get(timeout_defect.idempotency_header.lower())
                if idempotency_key:
                    request_sha256 = hashlib.sha256(
                        json.dumps(
                            {"query": query, "body": body},
                            sort_keys=True,
                            separators=(",", ":"),
                            default=str,
                        ).encode()
                    ).hexdigest()
                    idempotency_record_key = (
                        timeout_defect.id,
                        operation.operation_id,
                        path,
                        idempotency_key,
                    )
                    record = self.defect_state.storage.setdefault(
                        "idempotency_records", {}
                    ).get(idempotency_record_key)
                    if record is not None:
                        if record.request_sha256 != request_sha256:
                            return self._explicit_error(
                                409,
                                "idempotency_key_reused",
                                "The idempotency key was already used for a different request",
                                started=started,
                            )
                        self.record_defect_event(
                            DefectEvent(
                                defect_id=timeout_defect.id,
                                kind=timeout_defect.kind,
                                operation_id=operation.operation_id,
                                phase="idempotency_replayed",
                                call_ordinal=call_ordinal,
                            )
                        )
                        unresolved.pop(
                            (timeout_defect.id, operation.operation_id, path), None
                        )
                        return self._json_response(
                            record.status_code,
                            copy.deepcopy(record.response_body),
                            started=started,
                        )
            for retry_defect in retry_defects:
                if isinstance(retry_defect, RateLimitDefect):
                    limited = self._apply_rate_limit(
                        defect=retry_defect,
                        call_ordinal=call_ordinal,
                        resource_ids=resource_ids,
                        started=started,
                    )
                    if limited is not None:
                        return limited
            if (
                timeout_defect is not None
                and (timeout_defect.id, operation.operation_id, path) in unresolved
                and not idempotency_key
            ):
                self.defect_state.storage.setdefault(
                    "retry_safety_violations", []
                ).append(
                    {
                        "defect_id": timeout_defect.id,
                        "reason": "ambiguous_write_retried_without_idempotency",
                        "resource_ids": list(resource_ids),
                    }
                )
            matching_async = (
                self.defect_profile.matching_defects(
                    kind="async_completion",
                    operation_id=operation.operation_id,
                    trial_context=self.trial_context,
                    call_ordinal=call_ordinal,
                    resource_ids=resource_ids,
                )
                if self.defect_profile is not None
                else ()
            )
            self._record_projection_verification(operation.operation_id)
            if matching_async:
                async_defect = matching_async[0]
                if not isinstance(async_defect, AsyncCompletionDefect):
                    raise RuntimeError("Invalid async defect declaration")
                return self._accept_async_workflow(
                    defect=async_defect,
                    operation=operation,
                    invocation=invocation,
                    call_ordinal=call_ordinal,
                    resource_ids=resource_ids,
                    started=started,
                )
            prepared_projection = self._prepare_projection_triggers(
                operation.operation_id,
                invocation.arguments,
                call_ordinal,
            )
            if operation.execution == "conversation_transfer":
                # The receipt id must be a deterministic function of the
                # request: grading re-executes the conversation's recorded
                # tool calls against a fresh runtime (fresh conversation_id),
                # and a random id would diverge from the recorded WRITE
                # output and fail the strict replay. At most one transfer is
                # accepted per conversation, so a body-derived id is unique
                # within its conversation's scope.
                result = _conversation_transfer_receipt(parsed_body)
                self._conversation_transfer = result
            elif invocation.discoverable:
                tools = self.environment.tools
                discoverable_tools = (
                    tools.get_discoverable_tools() if tools is not None else {}
                )
                discovered_operation = discoverable_tools.get(invocation.tool_name)
                if discovered_operation is None:
                    raise ValueError(
                        f"Client operation {invocation.tool_name!r} is unavailable"
                    )
                result = discovered_operation(**invocation.arguments)
                self.sync_environment()
            else:
                result = self.environment.make_tool_call(
                    invocation.tool_name,
                    requestor="assistant",
                    **invocation.arguments,
                )
                self.sync_environment()
            self._finish_projection_triggers(
                operation.operation_id,
                invocation.arguments,
                call_ordinal,
                prepared_projection,
            )
            self._operation_calls.append(
                ClientAPIOperationCall(
                    operation_id=invocation.tool_name,
                    arguments=copy.deepcopy(invocation.arguments),
                )
            )
        except Exception as error:
            status_code, code = self._classify_business_error(error)
            return self._explicit_error(
                status_code,
                code,
                _PUBLIC_BUSINESS_ERROR_MESSAGES[code],
                started=started,
            )
        try:
            from tau2.hyper.client_api.catalog import (
                ClientOperationBusinessError,
                adapt_operation_response,
            )

            normalized = adapt_operation_response(
                operation,
                invocation,
                result,
                self.environment,
            )
            response_adapter = TypeAdapter(operation.response_type)
            response_body = response_adapter.dump_python(
                response_adapter.validate_python(normalized),
                mode="json",
                exclude_none=True,
            )
            response_body = self._apply_projection_lag(
                operation.operation_id, response_body, call_ordinal
            )
            status_code = operation.success_status
            if self.defect_profile is not None:
                for kind in (
                    "response_value_map",
                    "response_amount_sign",
                    "response_field_rename",
                    "response_date_to_datetime",
                ):
                    for defect in self.defect_profile.matching_defects(
                        kind=kind,
                        operation_id=operation.operation_id,
                        trial_context=self.trial_context,
                        call_ordinal=call_ordinal,
                        resource_ids=resource_ids,
                    ):
                        response_body, details = apply_response_defect(
                            response_body, defect
                        )
                        self.record_defect_event(
                            DefectEvent(
                                defect_id=defect.id,
                                kind=defect.kind,
                                operation_id=operation.operation_id,
                                phase="response_transformed",
                                call_ordinal=call_ordinal,
                                details=details,
                            )
                        )
            if pagination_defect is not None:
                response_body = self._apply_pagination(
                    defect=pagination_defect,
                    response_body=response_body,
                    query=query,
                    offset=pagination_offset,
                    call_ordinal=call_ordinal,
                )
            if idempotency_record_key is not None:
                self.defect_state.storage.setdefault("idempotency_records", {})[
                    idempotency_record_key
                ] = _IdempotencyRecord(
                    request_sha256=request_sha256,
                    status_code=status_code,
                    response_body=copy.deepcopy(response_body),
                )
            if timeout_defect is not None and timeout_defect.activation.matches(
                trial_context=self.trial_context,
                call_ordinal=call_ordinal,
                resource_ids=resource_ids,
            ):
                self.record_defect_event(
                    DefectEvent(
                        defect_id=timeout_defect.id,
                        kind=timeout_defect.kind,
                        operation_id=operation.operation_id,
                        phase="response_lost_after_commit",
                        call_ordinal=call_ordinal,
                        details={"idempotency_key_present": bool(idempotency_key)},
                    )
                )
                unresolved[(timeout_defect.id, operation.operation_id, path)] = {
                    "defect_id": timeout_defect.id,
                    "resource_ids": resource_ids,
                }
                return self._explicit_error(
                    timeout_defect.timeout_status,
                    "upstream_timeout",
                    "The upstream service timed out after accepting the request",
                    started=started,
                )
        except ClientOperationBusinessError as error:
            status_code, code = self._classify_business_error(error)
            return self._explicit_error(
                status_code,
                code,
                _PUBLIC_BUSINESS_ERROR_MESSAGES[code],
                started=started,
            )
        except ValidationError as error:
            return self._explicit_error(
                502,
                "invalid_response_body",
                "The operation returned a response outside its schema",
                started=started,
                details=error.errors(
                    include_url=False,
                    include_context=False,
                    include_input=False,
                ),
            )
        except Exception:
            return self._explicit_error(
                502,
                "invalid_response_body",
                "The operation could not normalize its response",
                started=started,
            )
        try:
            response_size = _json_size_bytes(response_body)
        except (TypeError, ValueError):
            return self._explicit_error(
                502,
                "invalid_response_body",
                "The operation returned a non-JSON response body",
                started=started,
            )
        if response_size > CLIENT_API_MAX_RESPONSE_BYTES:
            return self._explicit_error(
                502,
                "response_too_large",
                f"JSON response body exceeds {CLIENT_API_MAX_RESPONSE_BYTES} bytes",
                started=started,
            )
        return ClientAPIResponse(
            status_code=status_code,
            body=response_body,
            headers={
                "content-type": "application/json",
                "content-length": str(response_size),
            },
            elapsed_seconds=self._clock() - started,
        )

    def dispatch(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a broker payload and return a JSON-compatible response."""
        return self.request(
            method=str(payload.get("method", "")),
            path=str(payload.get("path", "")),
            query=payload.get("query"),
            body=payload.get("body"),
            headers=payload.get("headers"),
        ).model_dump(mode="json")


def create_domain_client_api_runtime(
    domain: str,
    *,
    solo_mode: bool = False,
    conversation_id: Optional[str] = None,
    development_seed: bool = False,
    deployment_manifest: Optional[str] = None,
    deployment_manifest_sha256: Optional[str] = None,
    defect_profile: Optional[DefectProfile] = None,
    trial_context: Optional[ClientAPITrialContext] = None,
    deployment_snapshot: Optional[DeploymentSnapshot] = None,
    monotonic_clock: Callable[[], float] = time.monotonic,
) -> ClientAPIRuntime:
    """Create a trusted client runtime from a registered maintained domain.

    ``development_seed`` is reserved for Developer-authored local tests. Final
    evaluation callers use the ordinary reference state.
    """
    from tau2.registry import registry

    configured_profiles = sum(
        value is not None
        for value in (
            deployment_manifest,
            deployment_manifest_sha256,
            defect_profile,
        )
    )
    if configured_profiles > 1:
        raise ValueError(
            "Provide only one of deployment_manifest, "
            "deployment_manifest_sha256, or defect_profile"
        )
    if deployment_manifest is not None:
        from tau2.hyper.client_api.defects import load_defect_profile

        defect_profile = load_defect_profile(
            deployment_manifest,
            expected_domain=domain,
        )
    elif deployment_manifest_sha256 is not None:
        from tau2.hyper.client_api.defects import load_defect_profile_by_hash

        defect_profile = load_defect_profile_by_hash(
            deployment_manifest_sha256,
            expected_domain=domain,
        )

    constructor = registry.get_env_constructor(domain)
    environment = constructor(solo_mode=solo_mode)
    if development_seed:
        from tau2.hyper.client_api.development import apply_development_seed

        apply_development_seed(environment)
    return ClientAPIRuntime(
        environment,
        conversation_id=conversation_id,
        defect_profile=defect_profile,
        trial_context=trial_context,
        deployment_snapshot=deployment_snapshot,
        monotonic_clock=monotonic_clock,
    )
