"""Telecom Client API schemas, operations, and response adapters."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal, Optional

from pydantic import Field, model_validator

from tau2.hyper.client_api.catalog import (
    APIModel,
    ClientOperation,
    ConversationTransferReceipt,
    ConversationTransferRequest,
    OperationInvocation,
)


class CustomerSearchResult(APIModel):
    customer_id: str
    full_name: str
    phone_number: str


class Customer(APIModel):
    customer_id: str
    full_name: str
    phone_number: str
    account_status: Literal["Active", "Suspended", "Pending Verification", "Closed"]
    line_ids: list[str]


class Plan(APIModel):
    plan_id: str
    name: str
    data_limit_gb: float
    price_per_month: float
    data_refueling_price_per_gb: float


class Device(APIModel):
    device_id: str
    device_type: Literal["phone", "router", "tablet", "watch", "other"]
    model: str
    is_esim_capable: bool
    activated: bool


class Line(APIModel):
    line_id: str
    phone_number: str
    status: Literal["Active", "Suspended", "Pending Activation", "Closed"]
    plan_id: str
    device_id: Optional[str] = None
    data_used_gb: float
    data_refueling_gb: float
    roaming_enabled: bool
    contract_end_date: Optional[date] = None
    suspension_start_date: Optional[date] = None


class BillLineItem(APIModel):
    description: str
    amount: float
    date: date


class Bill(APIModel):
    bill_id: str
    period_start: date
    period_end: date
    issue_date: date
    total_due: float
    due_date: date
    line_items: list[BillLineItem]
    status: Literal[
        "Draft", "Issued", "Awaiting Payment", "Paid", "Overdue", "Disputed"
    ]


class BillSummary(APIModel):
    bill_id: str
    period_start: date
    period_end: date
    total_due: float
    due_date: date
    status: Literal[
        "Draft", "Issued", "Awaiting Payment", "Paid", "Overdue", "Disputed"
    ]


class TelecomCustomerSearchRequest(APIModel):
    """Provide a phone number or a complete name-and-date-of-birth selector."""

    phone_number: Optional[str] = Field(default=None, min_length=1)
    full_name: Optional[str] = Field(default=None, min_length=1)
    date_of_birth: Optional[str] = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_selector(self) -> "TelecomCustomerSearchRequest":
        """Require exactly one complete supported customer selector."""

        has_name = self.full_name is not None
        has_birth_date = self.date_of_birth is not None
        if self.phone_number is not None:
            if has_name or has_birth_date:
                raise ValueError(
                    "phone_number cannot be combined with name or date-of-birth fields"
                )
            return self
        if not (has_name and has_birth_date):
            raise ValueError(
                "provide phone_number or the complete full_name and date_of_birth combination"
            )
        return self


class TelecomCustomerCollection(APIModel):
    customers: list[CustomerSearchResult]


class LineSuspensionRequest(APIModel):
    reason: str = Field(min_length=1)


class LineSuspension(APIModel):
    line_id: str
    status: Literal["Suspended"]
    suspension_start_date: date
    holding_fee_per_month: float


class LineResumption(APIModel):
    line_id: str
    status: Literal["Active"]


class TelecomBillQuery(APIModel):
    limit: int = Field(default=12, ge=1)


class TelecomBillCollection(APIModel):
    bills: list[BillSummary]


class PaymentRequest(APIModel):
    bill_id: str
    status: Literal["awaiting_payment"]


class DataUsageResult(APIModel):
    line_id: str
    data_used_gb: float
    data_limit_gb: float
    data_refueling_gb: float
    cycle_end_date: date


class RoamingRequest(APIModel):
    enabled: bool


class RoamingResult(APIModel):
    line_id: str
    roaming_enabled: bool


class DataRefuelRequest(APIModel):
    amount_gb: float = Field(gt=0)


class DataRefuelResult(APIModel):
    line_id: str
    added_gb: float
    total_refueled_gb: float
    charge: float


LINE_SUSPENSION_HOLDING_FEE_PER_MONTH = 5.0


def _data(value: Any) -> dict[str, Any]:
    """Return a JSON-shaped mapping from a private reference model."""

    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value)


def _customer_search_result(value: Any) -> dict[str, Any]:
    customer = _data(value)
    return {
        "customer_id": customer["customer_id"],
        "full_name": customer["full_name"],
        "phone_number": customer["phone_number"],
    }


def _customer(value: Any) -> dict[str, Any]:
    customer = _data(value)
    return {
        "customer_id": customer["customer_id"],
        "full_name": customer["full_name"],
        "phone_number": customer["phone_number"],
        "account_status": customer["account_status"],
        "line_ids": customer["line_ids"],
    }


def _line(value: Any) -> dict[str, Any]:
    line = _data(value)
    return {
        field: line.get(field)
        for field in (
            "line_id",
            "phone_number",
            "status",
            "plan_id",
            "device_id",
            "data_used_gb",
            "data_refueling_gb",
            "roaming_enabled",
            "contract_end_date",
            "suspension_start_date",
        )
    }


def _device(value: Any) -> dict[str, Any]:
    device = _data(value)
    return {
        field: device.get(field)
        for field in (
            "device_id",
            "device_type",
            "model",
            "is_esim_capable",
            "activated",
        )
    }


def _plan(value: Any) -> dict[str, Any]:
    plan = _data(value)
    return {
        field: plan[field]
        for field in (
            "plan_id",
            "name",
            "data_limit_gb",
            "price_per_month",
            "data_refueling_price_per_gb",
        )
    }


def _bill(value: Any) -> dict[str, Any]:
    bill = _data(value)
    return {
        "bill_id": bill["bill_id"],
        "period_start": bill["period_start"],
        "period_end": bill["period_end"],
        "issue_date": bill["issue_date"],
        "total_due": bill["total_due"],
        "due_date": bill["due_date"],
        "line_items": [
            {
                "description": item["description"],
                "amount": item["amount"],
                "date": item["date"],
            }
            for item in bill["line_items"]
        ],
        "status": bill["status"],
    }


def _bill_summary(value: Any) -> dict[str, Any]:
    bill = _data(value)
    return {
        field: bill[field]
        for field in (
            "bill_id",
            "period_start",
            "period_end",
            "total_due",
            "due_date",
            "status",
        )
    }


def _adapt_customer_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    return _customer(result)


def _adapt_line_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    return _line(result)


def _adapt_device_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    return _device(result)


def _adapt_bill_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    return _bill(result)


def _adapt_plan_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    return _plan(result)


def _telecom_line_arguments(path: dict[str, str]) -> dict[str, str]:
    return {
        "customer_id": path["customer_id"],
        "line_id": path["line_id"],
    }


def _telecom_detail_invocation(
    path: dict[str, str],
    *,
    parameter: str,
    prefix: str,
    resource_name: str,
) -> OperationInvocation:
    """Route a typed public resource to Telecom's private catch-all lookup."""

    resource_id = path[parameter]
    if not resource_id.startswith(prefix):
        raise ValueError(f"{resource_name} with ID {resource_id} not found")
    return OperationInvocation("get_details_by_id", {"id": resource_id})


def _adapt_customer_search_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    customers = result if isinstance(result, list) else [result]
    return {"customers": [_customer_search_result(customer) for customer in customers]}


def _adapt_bill_collection_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    return {"bills": [_bill_summary(bill) for bill in result]}


def _adapt_line_suspension_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    line = _data(result["line"])
    return {
        "line_id": line["line_id"],
        "status": line["status"],
        "suspension_start_date": line["suspension_start_date"],
        "holding_fee_per_month": LINE_SUSPENSION_HOLDING_FEE_PER_MONTH,
    }


def _adapt_line_resumption_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    line = _data(result["line"])
    return {"line_id": line["line_id"], "status": line["status"]}


def _adapt_payment_request_response(
    invocation: OperationInvocation, _result: Any
) -> dict[str, Any]:
    return {
        "bill_id": invocation.arguments["bill_id"],
        "status": "awaiting_payment",
    }


def _adapt_roaming_response(
    invocation: OperationInvocation, _result: Any
) -> dict[str, Any]:
    return {
        "line_id": invocation.arguments["line_id"],
        "roaming_enabled": invocation.tool_name == "enable_roaming",
    }


def _adapt_data_refuel_response(
    invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    return {
        "line_id": invocation.arguments["line_id"],
        "added_gb": invocation.arguments["gb_amount"],
        "total_refueled_gb": result["new_data_refueling_gb"],
        "charge": result["charge"],
    }


def operations() -> tuple[ClientOperation, ...]:
    return (
        ClientOperation(
            "POST",
            "/v1/customers/search",
            "searchCustomers",
            "Search for customers",
            "Find customers using either a phone number or the complete name-and-date-of-birth selector.",
            TelecomCustomerCollection,
            lambda _path, _query, body: OperationInvocation(
                "get_customer_by_phone",
                {"phone_number": body.phone_number},
            )
            if body.phone_number is not None
            else OperationInvocation(
                "get_customer_by_name",
                {"full_name": body.full_name, "dob": body.date_of_birth},
            ),
            body_type=TelecomCustomerSearchRequest,
            response_adapter=_adapt_customer_search_response,
        ),
        ClientOperation(
            "GET",
            "/v1/customers/{customer_id}",
            "getCustomer",
            "Get a customer",
            "Return one telecom customer and their account relationships.",
            Customer,
            lambda path, _query, _body: OperationInvocation(
                "get_customer_by_id", {"customer_id": path["customer_id"]}
            ),
            response_adapter=_adapt_customer_response,
        ),
        ClientOperation(
            "GET",
            "/v1/lines/{line_id}",
            "getLine",
            "Get a service line",
            "Return one mobile service line identified by its line ID.",
            Line,
            lambda path, _query, _body: _telecom_detail_invocation(
                path,
                parameter="line_id",
                prefix="L",
                resource_name="Line",
            ),
            response_adapter=_adapt_line_response,
        ),
        ClientOperation(
            "GET",
            "/v1/devices/{device_id}",
            "getDevice",
            "Get a device",
            "Return one customer device identified by its device ID.",
            Device,
            lambda path, _query, _body: _telecom_detail_invocation(
                path,
                parameter="device_id",
                prefix="D",
                resource_name="Device",
            ),
            response_adapter=_adapt_device_response,
        ),
        ClientOperation(
            "GET",
            "/v1/bills/{bill_id}",
            "getBill",
            "Get a bill",
            "Return one customer bill and its current payment status.",
            Bill,
            lambda path, _query, _body: _telecom_detail_invocation(
                path,
                parameter="bill_id",
                prefix="B",
                resource_name="Bill",
            ),
            response_adapter=_adapt_bill_response,
        ),
        ClientOperation(
            "GET",
            "/v1/plans/{plan_id}",
            "getPlan",
            "Get a service plan",
            "Return one mobile service plan and its data and pricing terms.",
            Plan,
            lambda path, _query, _body: _telecom_detail_invocation(
                path,
                parameter="plan_id",
                prefix="P",
                resource_name="Plan",
            ),
            response_adapter=_adapt_plan_response,
        ),
        ClientOperation(
            "POST",
            "/v1/customers/{customer_id}/lines/{line_id}/suspensions",
            "createLineSuspension",
            "Suspend a service line",
            "Create a suspension for one customer line with the supplied reason.",
            LineSuspension,
            lambda path, _query, body: OperationInvocation(
                "suspend_line",
                {**_telecom_line_arguments(path), "reason": body.reason},
            ),
            body_type=LineSuspensionRequest,
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            response_adapter=_adapt_line_suspension_response,
        ),
        ClientOperation(
            "POST",
            "/v1/customers/{customer_id}/lines/{line_id}/resumptions",
            "createLineResumption",
            "Resume a service line",
            "Create a resumption for one customer line.",
            LineResumption,
            lambda path, _query, _body: OperationInvocation(
                "resume_line", _telecom_line_arguments(path)
            ),
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            response_adapter=_adapt_line_resumption_response,
            reference_tool_names=("resume_line",),
        ),
        ClientOperation(
            "GET",
            "/v1/customers/{customer_id}/bills",
            "listCustomerBills",
            "List customer bills",
            "Return summaries of the customer's most recent bills in descending issue-date order.",
            TelecomBillCollection,
            lambda path, query, _body: OperationInvocation(
                "get_bills_for_customer",
                {"customer_id": path["customer_id"], "limit": query.limit},
            ),
            query_type=TelecomBillQuery,
            response_adapter=_adapt_bill_collection_response,
        ),
        ClientOperation(
            "POST",
            "/v1/customers/{customer_id}/bills/{bill_id}/payment-requests",
            "createBillPaymentRequest",
            "Create a bill payment request",
            "Create a payment request for one customer bill.",
            PaymentRequest,
            lambda path, _query, _body: OperationInvocation(
                "send_payment_request",
                {
                    "customer_id": path["customer_id"],
                    "bill_id": path["bill_id"],
                },
            ),
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            response_adapter=_adapt_payment_request_response,
            reference_tool_names=("send_payment_request",),
        ),
        ClientOperation(
            "GET",
            "/v1/customers/{customer_id}/lines/{line_id}/data-usage",
            "getLineDataUsage",
            "Get line data usage",
            "Return current-cycle usage, allowance, refueled data, and cycle end date for one customer line.",
            DataUsageResult,
            lambda path, _query, _body: OperationInvocation(
                "get_data_usage", _telecom_line_arguments(path)
            ),
        ),
        ClientOperation(
            "PUT",
            "/v1/customers/{customer_id}/lines/{line_id}/roaming",
            "replaceLineRoaming",
            "Replace line roaming state",
            "Set whether international roaming is enabled for one customer line.",
            RoamingResult,
            lambda path, _query, body: OperationInvocation(
                "enable_roaming" if body.enabled else "disable_roaming",
                _telecom_line_arguments(path),
            ),
            body_type=RoamingRequest,
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            response_adapter=_adapt_roaming_response,
        ),
        ClientOperation(
            "POST",
            "/v1/customers/{customer_id}/lines/{line_id}/data-refuels",
            "createLineDataRefuel",
            "Add data to a service line",
            "Add the requested amount of data to one customer line.",
            DataRefuelResult,
            lambda path, _query, body: OperationInvocation(
                "refuel_data",
                {
                    **_telecom_line_arguments(path),
                    "gb_amount": body.amount_gb,
                },
            ),
            body_type=DataRefuelRequest,
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            response_adapter=_adapt_data_refuel_response,
        ),
        ClientOperation(
            "POST",
            "/v1/conversations/{conversation_id}/transfers",
            "createConversationTransfer",
            "Transfer a conversation to a human agent",
            "Create a live transfer of one active conversation to a human support agent. The conversation transcript and routing context are attached automatically.",
            ConversationTransferReceipt,
            lambda _path, _query, body: OperationInvocation(
                "transfer_to_human_agents", {"summary": body.summary}
            ),
            body_type=ConversationTransferRequest,
            success_status=201,
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            execution="conversation_transfer",
        ),
    )
