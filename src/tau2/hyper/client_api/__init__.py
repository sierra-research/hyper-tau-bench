"""Developer-facing Client REST API contract for Hyper-τ construction.

The Developer sandbox receives :class:`ClientAPI`, a transport-only proxy. The
trusted host owns :class:`ClientAPIRuntime` and the sole business database.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from tau2.environment.toolkit import ToolKitBase

CLIENT_API_CONTRACT_VERSION = "3.1.0"
CLIENT_API_MAX_REQUEST_BYTES = 1_048_576
CLIENT_API_MAX_RESPONSE_BYTES = 4_194_304

_PUBLIC_BUSINESS_ERROR_MESSAGES = {
    "resource_not_found": "The requested resource was not found",
    "resource_conflict": "The resource's current state prevents the operation",
    "business_rule_violation": "The request violates a business constraint",
}


def _json_size_bytes(value: Any) -> int:
    """Return the compact UTF-8 JSON size used by the broker contract."""
    return len(
        json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )


def _local_client_error(status_code: int, code: str, message: str) -> ClientAPIResponse:
    """Build a Client-side rejection without invoking the broker transport."""
    body = {"error": {"code": code, "message": message}}
    return ClientAPIResponse(
        status_code=status_code,
        body=body,
        headers={
            "content-type": "application/json",
            "content-length": str(_json_size_bytes(body)),
        },
    )


def _json_value(value: Any) -> Any:
    """Convert tool results into JSON-compatible response bodies."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _value_at_json_path(value: Any, path: tuple[str | int, ...]) -> Any:
    """Resolve a validated host manifest path in a JSON-shaped value."""

    current = value
    for segment in path:
        current = current[segment]
    return current


class ClientAPIResponse(BaseModel):
    """A REST-shaped response returned to Developer-owned tool code."""

    status_code: int
    body: Any = None
    headers: dict[str, str] = Field(default_factory=dict)
    elapsed_seconds: float = 0.0

    def raise_for_status(self) -> None:
        """Raise a stable error when the client returned a non-2xx status."""
        if 200 <= self.status_code < 300:
            return
        message = None
        if isinstance(self.body, dict):
            error = self.body.get("error")
            if isinstance(error, dict):
                message = error.get("message")
        raise ClientAPIError(
            message or f"Client API request failed with status {self.status_code}",
            response=self,
        )


class ClientAPIError(RuntimeError):
    """Raised by :meth:`ClientAPIResponse.raise_for_status`."""

    def __init__(self, message: str, *, response: ClientAPIResponse):
        super().__init__(message)
        self.response = response


class ClientAPIOperationCall(BaseModel):
    """A trusted canonical operation or host-only response observation."""

    operation_id: str
    arguments: dict[str, Any]


class ClientAPIContext(BaseModel):
    """Trusted runtime context bound to one Client API conversation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    conversation_id: str = Field(min_length=1)


class ClientAPI:
    """REST client injected into a Developer-owned API-backed toolkit."""

    def __init__(
        self,
        transport: Callable[[dict[str, Any]], dict[str, Any]],
        *,
        context: Optional[ClientAPIContext] = None,
    ):
        self._transport = transport
        self._context = context

    @property
    def context(self) -> ClientAPIContext:
        """Return the trusted context for the active conversation."""
        if self._context is None:
            raise RuntimeError("Client API context has not been initialized")
        return self._context

    def _set_context(self, context: ClientAPIContext | dict[str, Any]) -> None:
        """Bind context delivered by the trusted host during trial reset."""
        self._context = ClientAPIContext.model_validate(context)

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[dict[str, Any]] = None,
        body: Any = None,
        headers: Optional[dict[str, str]] = None,
    ) -> ClientAPIResponse:
        """Issue one request through the sealed host broker."""
        payload = {
            "method": method.upper(),
            "path": path,
            "query": dict(query or {}),
            "body": body,
            "headers": dict(headers or {}),
        }
        try:
            request_size = _json_size_bytes(body)
            if query:
                request_size += _json_size_bytes(dict(query))
        except (TypeError, ValueError):
            return _local_client_error(
                400,
                "invalid_body",
                "JSON request query and body must be serializable",
            )
        if request_size > CLIENT_API_MAX_REQUEST_BYTES:
            return _local_client_error(
                413,
                "request_too_large",
                f"JSON request query and body exceed {CLIENT_API_MAX_REQUEST_BYTES} bytes",
            )
        response = ClientAPIResponse.model_validate(self._transport(payload))
        try:
            response_size = _json_size_bytes(response.body)
        except (TypeError, ValueError):
            return _local_client_error(
                502,
                "invalid_response_body",
                "The service returned a non-JSON response body",
            )
        if response_size > CLIENT_API_MAX_RESPONSE_BYTES:
            return _local_client_error(
                502,
                "response_too_large",
                f"JSON response body exceeds {CLIENT_API_MAX_RESPONSE_BYTES} bytes",
            )
        response.headers.setdefault("content-length", str(response_size))
        return response


class ClientAPIToolKitBase(ToolKitBase):
    """Base class for Developer tools backed only by :class:`ClientAPI`."""

    def __init__(self, client_api: ClientAPI):
        super().__init__(db=None)
        self.client_api = client_api
