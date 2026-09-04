"""Shared primitives and domain dispatch for explicit Client API catalogs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    """Strict base model for public Client API request and response schemas."""

    model_config = ConfigDict(extra="forbid")


class ConversationTransferRequest(APIModel):
    """Request to transfer an active conversation to a human agent."""

    summary: str = Field(min_length=1)


class ConversationTransferReceipt(APIModel):
    """Accepted live-transfer resource."""

    transfer_id: str = Field(min_length=1)
    status: Literal["accepted"]


@dataclass(frozen=True)
class OperationInvocation:
    """Private reference operation selected by a public Client API request."""

    tool_name: str
    arguments: dict[str, Any]
    discoverable: bool = False


ResponseAdapter = Callable[[OperationInvocation, Any], Any]
EnvironmentResponseAdapter = Callable[[OperationInvocation, Any, Any], Any]


class ClientOperationBusinessError(ValueError):
    """A reference operation rejected an otherwise valid Client request."""


@dataclass(frozen=True)
class ClientOperation:
    """One explicit public Client API operation and its private adapter.

    ``summary`` and ``description`` are unconditional public contract text. They
    must describe resource and transport mechanics without revealing business
    policy, eligibility gates, workflow ordering, or outcome rules.
    """

    method: str
    path: str
    operation_id: str
    summary: str
    description: str
    response_type: Any
    invoke: Callable[[dict[str, str], Any, Any], OperationInvocation]
    body_type: Any = None
    query_type: Any = None
    success_status: int = 200
    mutates_state: bool = False
    idempotency: Literal["safe", "not_guaranteed"] = "safe"
    automatic_retries: Literal["allowed", "forbidden"] = "allowed"
    response_adapter: Optional[ResponseAdapter] = None
    environment_response_adapter: Optional[EnvironmentResponseAdapter] = None
    execution: Literal["reference_tool", "conversation_transfer"] = "reference_tool"
    advertised: bool = True
    reference_tool_names: tuple[str, ...] = ()


def client_operations_for_domain(
    domain_name: str,
) -> tuple[ClientOperation, ...] | None:
    """Return the explicit catalog owned by a maintained domain module."""

    if domain_name == "retail_plus":
        from tau2.hyper.client_api.catalogs.retail import operations

        return operations()
    if domain_name == "airline_plus":
        from tau2.hyper.client_api.catalogs.airline import operations

        return operations()
    if domain_name == "telecom":
        from tau2.hyper.client_api.catalogs.telecom import operations

        return operations()
    if domain_name == "banking_knowledge":
        from tau2.hyper.client_api.catalogs.banking import operations

        return operations()
    return None


def adapt_operation_response(
    operation: ClientOperation,
    invocation: OperationInvocation,
    result: Any,
    environment: Any = None,
) -> Any:
    """Normalize a private result using its domain-owned response adapter."""

    if operation.environment_response_adapter is not None:
        return operation.environment_response_adapter(invocation, result, environment)
    if operation.response_adapter is None:
        return result
    return operation.response_adapter(invocation, result)
