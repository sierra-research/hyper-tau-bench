"""Banking Knowledge Client API catalog and discovery visibility boundary."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, create_model, model_validator

from tau2.hyper.client_api.catalog import (
    APIModel,
    ClientOperation,
    ClientOperationBusinessError,
    ConversationTransferReceipt,
    ConversationTransferRequest,
    OperationInvocation,
)


class BankingCustomerSearchRequest(APIModel):
    """Select a customer using exactly one supported identifier."""

    customer_id: Optional[str] = Field(default=None, min_length=1)
    customer_name: Optional[str] = Field(default=None, min_length=1)
    email: Optional[str] = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_selector(self) -> "BankingCustomerSearchRequest":
        """Require exactly one complete customer selector."""

        values = (self.customer_id, self.customer_name, self.email)
        if sum(value is not None for value in values) != 1:
            raise ValueError(
                "provide exactly one of customer_id, customer_name, or email"
            )
        return self


class CustomerEmailRequest(APIModel):
    email: str = Field(min_length=1)


class VerificationRequest(APIModel):
    name: str = Field(min_length=1)
    address: str = Field(min_length=1)
    email: str = Field(min_length=1)
    phone_number: str = Field(min_length=1)
    date_of_birth: str = Field(min_length=1)
    time_verified: str = Field(min_length=1)


class SelfServiceActionRequest(APIModel):
    action_name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ActivationRequest(APIModel):
    activation_kind: Literal["new", "replacement", "reissued"]
    last_4_digits: str = Field(min_length=4, max_length=4)
    expiration_date: str = Field(min_length=1)
    cvv: str = Field(min_length=3)
    pin: str = Field(min_length=1)


class FrozenStateRequest(APIModel):
    frozen: bool


class PaymentHistoryQuery(APIModel):
    months: int = Field(ge=1)


class CustomerSearchResult(APIModel):
    customer_id: str
    name: str


class BankingCustomer(APIModel):
    customer_id: str
    name: str
    address: str
    email: str
    phone_number: str
    date_of_birth: str
    rho_bank_plus_subscription: Optional[bool] = None


class CustomerEmail(APIModel):
    customer_id: str
    email: str


class Referral(APIModel):
    referral_id: str
    customer_id: str
    account_type: str
    status: str
    referred_on: str


class CreditCardTransaction(APIModel):
    transaction_id: str
    customer_id: str
    account_id: Optional[str] = None
    card_type: str
    merchant: str
    amount: float
    transaction_date: str
    category: str
    status: str
    rewards_earned: str


class CreditCardAccount(APIModel):
    account_id: str
    customer_id: str
    card_type: str
    status: str
    standing: Optional[str] = None
    opened_on: str
    balance: float
    credit_limit: Optional[float] = None
    past_due_amount: Optional[float] = None
    reward_points: str


class BankAccount(APIModel):
    account_id: str
    customer_id: str
    account_type: str
    account_class: str
    status: str
    opened_on: str
    balance: float
    closed_on: Optional[str] = None


class CustomerAccounts(APIModel):
    bank_accounts: list[BankAccount]
    credit_card_accounts: list[CreditCardAccount]


class BankAccountTransaction(APIModel):
    transaction_id: str
    account_id: str
    transaction_type: str
    amount: float
    description: str
    transaction_date: str
    status: str


class DebitCard(APIModel):
    card_id: str
    account_id: str
    last_four: str
    expiration_date: str
    status: str
    issue_reason: str
    issued_on: str
    card_design: Optional[str] = None


class VerificationReceipt(APIModel):
    verification_id: str
    customer_id: str
    status: Literal["logged"]
    verified_at: str


class ServerTime(APIModel):
    timestamp: str


class SelfServiceActionReceipt(APIModel):
    action_name: str
    status: Literal["offered"]


class RewardsUpdateReceipt(APIModel):
    transaction_id: str
    rewards_earned: str


class CreditCardDispute(APIModel):
    dispute_id: str
    transaction_id: str
    customer_id: str
    status: str
    dispute_reason: str
    resolution_requested: str
    partial_refund_amount: Optional[float] = None
    provisional_credit_eligible: bool
    provisional_credit_issued: bool
    submitted_on: str
    card_action: str


class DebitCardDispute(APIModel):
    dispute_id: str
    transaction_id: str
    account_id: str
    card_id: str
    customer_id: str
    status: str
    category: str
    disputed_amount: float
    provisional_credit_eligible: bool
    provisional_credit_issued: bool
    provisional_credit_amount: Optional[float] = None
    maximum_liability_amount: float
    submitted_on: str
    card_action: str


class ReplacementOrder(APIModel):
    order_id: str
    account_id: str
    customer_id: str
    status: str
    reason: str
    shipping_address: str
    expedited: bool
    ordered_on: str
    expected_delivery: str


class ClosureReason(APIModel):
    closure_reason_id: str
    account_id: str
    customer_id: str
    reason: str
    status: str
    logged_on: str


class CreditLimitRequest(APIModel):
    request_id: str
    account_id: str
    customer_id: str
    status: str
    requested_amount: Optional[float] = None
    previous_limit: Optional[float] = None
    new_limit: Optional[float] = None
    increase_amount: Optional[float] = None
    denial_reason: Optional[str] = None
    submitted_on: Optional[str] = None
    decided_on: Optional[str] = None


class Payment(APIModel):
    payment_id: Optional[str] = None
    payment_date: str
    amount: float
    status: str


class PaymentHistory(APIModel):
    account_id: str
    requested_months: int
    consecutive_on_time_payments: int
    payments: list[Payment]


class AtmDepositCheck(APIModel):
    check_number: Optional[str] = None
    drawn_on: Optional[str] = None
    payee: Optional[str] = None
    amount: float
    memo: Optional[str] = None
    signature_status: Optional[str] = None
    date_on_check: Optional[str] = None


class CashDenomination(APIModel):
    count: int
    denomination: float
    total: float


class AtmDepositCash(APIModel):
    amount: float
    denominations: list[CashDenomination]


class AtmImageQuality(APIModel):
    envelope_scan: Optional[str] = None
    check_front: Optional[str] = None
    check_back: Optional[str] = None
    cash_image: Optional[str] = None


class AtmDepositImages(APIModel):
    transaction_id: str
    atm_id: str
    deposit_date: str
    available: bool
    envelope_id: Optional[str] = None
    deposit_time: Optional[str] = None
    atm_location: Optional[str] = None
    check: Optional[AtmDepositCheck] = None
    cash: Optional[AtmDepositCash] = None
    imaged_amount: Optional[float] = None
    recorded_amount: Optional[float] = None
    discrepancy_amount: Optional[float] = None
    image_quality: AtmImageQuality
    unavailable_reason: Optional[str] = None
    verification_notes: Optional[str] = None


class RecurringBlockReceipt(APIModel):
    card_id: str
    recurring_payments_blocked: bool
    effective_within_hours: int
    one_time_purchases_affected: bool


class CreditReceipt(APIModel):
    transaction_id: str
    account_id: str
    amount: float
    credit_type: str
    balance: float
    status: Literal["posted"]


class AccountTransferReceipt(APIModel):
    source_account_id: str
    destination_account_id: str
    amount: float
    source_balance: float
    destination_balance: float
    status: Literal["completed"]


class AccountClosureReceipt(APIModel):
    account_id: str
    status: Literal["closed"]
    closed_on: str
    reason: Optional[str] = None
    early_closure_fee_waived: Optional[bool] = None


class CreditCardMutationReceipt(APIModel):
    account_id: str
    status: str
    effective_on: Optional[str] = None
    card_type: Optional[str] = None
    transaction_id: Optional[str] = None
    amount: Optional[float] = None
    balance: Optional[float] = None
    flag_id: Optional[str] = None
    reason: Optional[str] = None
    notices: list[str] = Field(default_factory=list)


class CreditCardPaymentReceipt(APIModel):
    account_id: str
    checking_account_id: str
    amount: float
    credit_card_balance: float
    checking_account_balance: float
    status: Literal["completed"]


class DebitCardOrderReceipt(APIModel):
    order_id: str
    card_id: str
    account_id: str
    status: str
    delivery_option: str
    card_design: str
    shipping_address: str
    expected_delivery: str
    total_fee: float
    balance: float


class DebitCardMutationReceipt(APIModel):
    card_id: str
    status: str
    effective_on: Optional[str] = None
    issue_reason: Optional[str] = None
    deactivated_card_ids: list[str] = Field(default_factory=list)
    grace_period_card_ids: list[str] = Field(default_factory=list)
    notices: list[str] = Field(default_factory=list)


class TemporaryLimitIncreaseReceipt(APIModel):
    card_id: str
    limit_type: str
    previous_limit: float
    new_limit: float
    expires_in_hours: int
    notices: list[str] = Field(default_factory=list)


class InterestReportReceipt(APIModel):
    report_id: str
    account_id: str
    status: str
    expected_apy: float
    actual_apy: float
    amount_difference: float


class BankAccountCreationReceipt(APIModel):
    account: BankAccount


def _request_model(
    name: str,
    required: dict[str, type],
    optional: Optional[dict[str, type]] = None,
) -> type[APIModel]:
    """Create one strict request model for a private discovered operation."""

    fields: dict[str, tuple[Any, Any]] = {
        field_name: (annotation, ...) for field_name, annotation in required.items()
    }
    fields.update(
        {
            field_name: (Optional[annotation], None)
            for field_name, annotation in (optional or {}).items()
        }
    )
    return create_model(name, __base__=APIModel, **fields)


RewardsUpdateRequest = _request_model(
    "RewardsUpdateRequest", {"new_rewards_earned": str}
)
CreditCardDisputeRequest = _request_model(
    "CreditCardDisputeRequest",
    {
        "card_action": str,
        "card_last_4_digits": str,
        "full_name": str,
        "user_id": str,
        "phone": str,
        "email": str,
        "address": str,
        "contacted_merchant": bool,
        "purchase_date": str,
        "issue_noticed_date": str,
        "dispute_reason": str,
        "resolution_requested": str,
        "eligible_for_provisional_credit": bool,
    },
    {"partial_refund_amount": float},
)
DebitCardDisputeRequest = _request_model(
    "DebitCardDisputeRequest",
    {
        "account_id": str,
        "card_id": str,
        "user_id": str,
        "dispute_category": str,
        "transaction_date": str,
        "discovery_date": str,
        "disputed_amount": float,
        "transaction_type": str,
        "card_in_possession": bool,
        "pin_compromised": str,
        "contacted_merchant": bool,
        "police_report_filed": bool,
        "written_statement_provided": bool,
        "provisional_credit_eligible": bool,
        "customer_max_liability_amount": float,
        "card_action": str,
    },
)
RecurringBlockRequest = _request_model(
    "RecurringBlockRequest", {"block_recurring": bool}
)
ReplacementCreditCardRequest = _request_model(
    "ReplacementCreditCardRequest",
    {"user_id": str, "shipping_address": str, "reason": str},
    {"expedited_shipping": bool},
)
ClosureReasonRequest = _request_model(
    "ClosureReasonRequest", {"user_id": str, "closure_reason": str}
)
StatementCreditRequest = _request_model(
    "StatementCreditRequest", {"user_id": str, "amount": float, "reason": str}
)
CreditCardFlagRequest = _request_model(
    "CreditCardFlagRequest",
    {"user_id": str, "flag_type": str, "expiration_date": str, "reason": str},
)
CreditCardDowngradeRequest = _request_model(
    "CreditCardDowngradeRequest", {"user_id": str, "target_card_type": str}
)
CustomerIdRequest = _request_model("CustomerIdRequest", {"user_id": str})
CreditCardPaymentRequest = _request_model(
    "CreditCardPaymentRequest",
    {"user_id": str, "checking_account_id": str, "amount": float},
)
CreditLimitIncreaseRequest = _request_model(
    "CreditLimitIncreaseRequest",
    {"user_id": str, "requested_increase_amount": int},
)
CreditLimitApprovalRequest = _request_model(
    "CreditLimitApprovalRequest", {"user_id": str, "new_credit_limit": int}
)
CreditLimitDenialRequest = _request_model(
    "CreditLimitDenialRequest", {"user_id": str, "denial_reason": str}
)
BankAccountRequest = _request_model(
    "BankAccountRequest", {"account_type": str, "account_class": str}
)
BankAccountClosureRequest = _request_model(
    "BankAccountClosureRequest",
    {},
    {"reason": str, "waive_early_closure_fee": bool},
)
BankTransferRequest = _request_model(
    "BankTransferRequest",
    {"source_account_id": str, "destination_account_id": str, "amount": float},
)
AccountCreditRequest = _request_model(
    "AccountCreditRequest", {"amount": float, "credit_type": str}
)
InterestDiscrepancyRequest = _request_model(
    "InterestDiscrepancyRequest",
    {
        "user_id": str,
        "expected_apy": float,
        "actual_apy": float,
        "amount_difference": float,
    },
)
DebitCardOrderRequest = _request_model(
    "DebitCardOrderRequest",
    {
        "user_id": str,
        "delivery_option": str,
        "delivery_fee": float,
        "card_design": str,
        "design_fee": float,
        "shipping_address": str,
    },
    {"excess_replacement_fee": float},
)
ReasonRequest = _request_model("ReasonRequest", {"reason": str})
FraudAlertClearRequest = _request_model("FraudAlertClearRequest", {"reason": str})
PinResetRequest = _request_model(
    "PinResetRequest", {"last_4_digits": str, "new_pin": str}
)
PinChangeRequest = _request_model(
    "PinChangeRequest", {"current_pin": str, "new_pin": str}
)
TemporaryLimitIncreaseRequest = _request_model(
    "TemporaryLimitIncreaseRequest", {"limit_type": str, "new_limit": int}
)


def _money(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value).replace("$", "").replace(",", "").strip())


def _banking_db(environment: Any) -> Any:
    tools = getattr(environment, "tools", None)
    db = getattr(tools, "db", None)
    if db is None:
        raise ValueError("Banking response projection requires transactional state")
    return db


def _records(db: Any, table: str) -> list[tuple[str, dict[str, Any]]]:
    value = getattr(db, table, None)
    return list(getattr(value, "data", {}).items())


def _matches(record: dict[str, Any], **values: Any) -> bool:
    return all(
        value is None or record.get(field) == value for field, value in values.items()
    )


def _legacy_error(result: Any) -> None:
    if not isinstance(result, str):
        return
    message = result.strip()
    if message.startswith(("Error:", "Failed to ", "Failed ")):
        raise ClientOperationBusinessError(message)


def _customer(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "customer_id": record["user_id"],
        "name": record["name"],
        "address": record["address"],
        "email": record["email"],
        "phone_number": record["phone_number"],
        "date_of_birth": record["date_of_birth"],
        "rho_bank_plus_subscription": record.get("rho_bank_plus_subscription"),
    }


def _referral(record_id: str, record: dict[str, Any]) -> dict[str, Any]:
    return {
        "referral_id": record.get("referral_id", record_id),
        "customer_id": record["referrer_id"],
        "account_type": record["referred_account_type"],
        "status": record["referral_status"],
        "referred_on": record["date"],
    }


def _credit_card_transaction(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "transaction_id": record["transaction_id"],
        "customer_id": record["user_id"],
        "account_id": record.get("credit_card_account_id"),
        "card_type": record.get("credit_card_type", "Unknown"),
        "merchant": record.get("merchant_name", "Unknown"),
        "amount": _money(record.get("transaction_amount")),
        "transaction_date": record.get("transaction_date", ""),
        "category": record.get("category", ""),
        "status": record.get("status", "UNKNOWN"),
        "rewards_earned": record.get("rewards_earned", "0 points"),
    }


def _credit_card_account(record: dict[str, Any]) -> dict[str, Any]:
    status = record.get("status", "ACTIVE")
    standing = record.get("account_status")
    return {
        "account_id": record["account_id"],
        "customer_id": record["user_id"],
        "card_type": record["card_type"],
        "status": status,
        "standing": standing,
        "opened_on": record.get("date_of_account_open", ""),
        "balance": _money(record.get("current_balance")),
        "credit_limit": (
            _money(record["credit_limit"])
            if record.get("credit_limit") is not None
            else None
        ),
        "past_due_amount": (
            _money(record["past_due_amount"])
            if record.get("past_due_amount") is not None
            else None
        ),
        "reward_points": record.get("reward_points", "0 points"),
    }


def _bank_account(record: dict[str, Any]) -> dict[str, Any]:
    account_type = record.get("account_type", record.get("class", ""))
    if account_type == "saving":
        account_type = "savings"
    return {
        "account_id": record["account_id"],
        "customer_id": record["user_id"],
        "account_type": account_type,
        "account_class": record.get("account_class", record.get("level", "")),
        "status": record.get("status", "UNKNOWN"),
        "opened_on": record.get("date_opened", ""),
        "balance": _money(record.get("current_holdings", record.get("balance", 0))),
        "closed_on": record.get("date_closed"),
    }


def _bank_transaction(record_id: str, record: dict[str, Any]) -> dict[str, Any]:
    return {
        "transaction_id": record.get("transaction_id", record_id),
        "account_id": record["account_id"],
        "transaction_type": record.get("type", "unknown"),
        "amount": _money(record.get("amount")),
        "description": record.get("description", ""),
        "transaction_date": record.get("date", ""),
        "status": record.get("status", "unknown"),
    }


def _debit_card(record_id: str, record: dict[str, Any]) -> dict[str, Any]:
    return {
        "card_id": record.get("card_id", record_id),
        "account_id": record["account_id"],
        "last_four": record.get("last_4_digits", record.get("card_number_last_4", "")),
        "expiration_date": record.get("expiration_date", ""),
        "status": record.get("status", "UNKNOWN"),
        "issue_reason": record.get("issue_reason", "unknown"),
        "issued_on": record.get("issue_date", record.get("created_date", "")),
        "card_design": record.get("card_design"),
    }


def _credit_card_dispute(record_id: str, record: dict[str, Any]) -> dict[str, Any]:
    eligible = bool(record.get("eligible_for_provisional_credit", False))
    return {
        "dispute_id": record.get("dispute_id", record_id),
        "transaction_id": record["transaction_id"],
        "customer_id": record["user_id"],
        "status": record.get("status", "UNKNOWN"),
        "dispute_reason": record.get("dispute_reason", ""),
        "resolution_requested": record.get("resolution_requested", ""),
        "partial_refund_amount": record.get("partial_refund_amount"),
        "provisional_credit_eligible": eligible,
        "provisional_credit_issued": bool(
            record.get("provisional_credit_given", eligible)
        ),
        "submitted_on": record.get("submitted_at", ""),
        "card_action": record.get("card_action", ""),
    }


def _debit_card_dispute(record_id: str, record: dict[str, Any]) -> dict[str, Any]:
    eligible = bool(record.get("provisional_credit_eligible", False))
    return {
        "dispute_id": record.get("dispute_id", record_id),
        "transaction_id": record["transaction_id"],
        "account_id": record["account_id"],
        "card_id": record["card_id"],
        "customer_id": record["user_id"],
        "status": record.get("status", "UNKNOWN"),
        "category": record.get("dispute_category", ""),
        "disputed_amount": _money(record.get("disputed_amount")),
        "provisional_credit_eligible": eligible,
        "provisional_credit_issued": bool(
            record.get("provisional_credit_issued", eligible)
        ),
        "provisional_credit_amount": record.get("provisional_credit_amount"),
        "maximum_liability_amount": _money(record.get("customer_max_liability_amount")),
        "submitted_on": record.get("submitted_at", ""),
        "card_action": record.get("card_action", ""),
    }


def _replacement_order(record_id: str, record: dict[str, Any]) -> dict[str, Any]:
    return {
        "order_id": record.get("order_id", record_id),
        "account_id": record["credit_card_account_id"],
        "customer_id": record["user_id"],
        "status": record.get("status", "UNKNOWN"),
        "reason": record.get("reason", ""),
        "shipping_address": record.get("shipping_address", ""),
        "expedited": bool(record.get("expedited_shipping", False)),
        "ordered_on": record.get("order_date", ""),
        "expected_delivery": record.get("expected_delivery", ""),
    }


def _closure_reason(record_id: str, record: dict[str, Any]) -> dict[str, Any]:
    return {
        "closure_reason_id": record.get("record_id", record_id),
        "account_id": record["credit_card_account_id"],
        "customer_id": record["user_id"],
        "reason": record["closure_reason"],
        "status": record.get("status", "LOGGED"),
        "logged_on": record.get("logged_at", ""),
    }


def _credit_limit_request(record_id: str, record: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_id": record.get("request_id", record_id),
        "account_id": record["credit_card_account_id"],
        "customer_id": record["user_id"],
        "status": record.get("status", "UNKNOWN"),
        "requested_amount": (
            _money(record["requested_increase_amount"])
            if record.get("requested_increase_amount") is not None
            else None
        ),
        "previous_limit": (
            _money(record["previous_limit"])
            if record.get("previous_limit") is not None
            else None
        ),
        "new_limit": _money(record["new_limit"])
        if record.get("new_limit") is not None
        else None,
        "increase_amount": (
            _money(record["increase_amount"])
            if record.get("increase_amount") is not None
            else None
        ),
        "denial_reason": record.get("denial_reason"),
        "submitted_on": record.get("submitted_at"),
        "decided_on": record.get("decision_date"),
    }


def _find_one(
    db: Any,
    table: str,
    **values: Any,
) -> tuple[str, dict[str, Any]]:
    matches = [item for item in _records(db, table) if _matches(item[1], **values)]
    if not matches:
        raise ClientOperationBusinessError("Resource not found")
    return matches[-1]


def _label(result: str, name: str) -> Optional[str]:
    match = re.search(
        rf"^\s*(?:-\s*)?{re.escape(name)}:\s*(.+?)\s*$",
        result,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def _notices(result: Any) -> list[str]:
    if not isinstance(result, str):
        return []
    prefixes = (
        "note:",
        "important:",
        "reminder:",
        "any pending",
        "any recurring",
        "the customer will",
        "after 24 hours",
        "for security",
        "please review",
        "report any",
    )
    return [
        line.strip(" -")
        for line in result.splitlines()
        if line.strip().lower().startswith(prefixes)
    ]


def _payload(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, BaseModel):
        return value.model_dump(exclude_none=True)
    return dict(value)


def _invoke(
    tool_name: str,
    *,
    path_arguments: Optional[dict[str, str]] = None,
    discoverable: bool = False,
    transform: Optional[Callable[[dict[str, str], Any, Any], dict[str, Any]]] = None,
) -> Callable[[dict[str, str], Any, Any], OperationInvocation]:
    """Build a private adapter for a resource-shaped Client operation."""

    def invoke(path: dict[str, str], query: Any, body: Any) -> OperationInvocation:
        if transform is not None:
            arguments = transform(path, query, body)
        else:
            arguments = {
                target: path[source]
                for source, target in (path_arguments or {}).items()
            }
            arguments.update(_payload(query))
            arguments.update(_payload(body))
        return OperationInvocation(
            tool_name=tool_name,
            arguments=arguments,
            discoverable=discoverable,
        )

    return invoke


def _operation(
    method: str,
    path: str,
    operation_id: str,
    description: str,
    tool_name: str,
    *,
    body_type: Any = None,
    query_type: Any = None,
    path_arguments: Optional[dict[str, str]] = None,
    mutates_state: bool = False,
    advertised: bool = True,
    discoverable: bool = False,
    transform: Optional[Callable[[dict[str, str], Any, Any], dict[str, Any]]] = None,
    response_type: Any = None,
) -> ClientOperation:
    return ClientOperation(
        method=method,
        path=path,
        operation_id=operation_id,
        summary=description,
        description=description,
        response_type=(
            response_type if response_type is not None else _RESPONSE_TYPES[tool_name]
        ),
        body_type=body_type,
        query_type=query_type,
        invoke=_invoke(
            tool_name,
            path_arguments=path_arguments,
            discoverable=discoverable,
            transform=transform,
        ),
        mutates_state=mutates_state,
        idempotency="not_guaranteed" if mutates_state else "safe",
        automatic_retries="forbidden" if mutates_state else "allowed",
        advertised=advertised,
        reference_tool_names=(tool_name,),
        environment_response_adapter=_adapt_banking_response,
    )


def _discovered(
    method: str,
    path: str,
    operation_id: str,
    description: str,
    tool_name: str,
    **kwargs: Any,
) -> ClientOperation:
    return _operation(
        method,
        path,
        operation_id,
        description,
        tool_name,
        advertised=False,
        discoverable=True,
        **kwargs,
    )


def _customer_search(
    _path: dict[str, str], _query: Any, body: BankingCustomerSearchRequest
) -> OperationInvocation:
    if body.customer_id is not None:
        return OperationInvocation(
            "get_user_information_by_id", {"user_id": body.customer_id}
        )
    if body.customer_name is not None:
        return OperationInvocation(
            "get_user_information_by_name",
            {"customer_name": body.customer_name},
        )
    return OperationInvocation("get_user_information_by_email", {"email": body.email})


def _self_service_arguments(
    _path: dict[str, str], _query: Any, body: SelfServiceActionRequest
) -> dict[str, Any]:
    return {
        "discoverable_tool_name": body.action_name,
        "arguments": json.dumps(body.arguments),
    }


def _customer_email_arguments(
    path: dict[str, str], _query: Any, body: CustomerEmailRequest
) -> dict[str, Any]:
    return {"user_id": path["customer_id"], "new_email": body.email}


def _activation(
    path: dict[str, str], _query: Any, body: ActivationRequest
) -> OperationInvocation:
    names = {
        "new": "activate_debit_card_8291",
        "replacement": "activate_debit_card_8292",
        "reissued": "activate_debit_card_8293",
    }
    arguments = body.model_dump(exclude={"activation_kind"})
    arguments["card_id"] = path["card_id"]
    return OperationInvocation(
        names[body.activation_kind], arguments, discoverable=True
    )


def _frozen_state(
    path: dict[str, str], _query: Any, body: FrozenStateRequest
) -> OperationInvocation:
    return OperationInvocation(
        "freeze_debit_card_3892" if body.frozen else "unfreeze_debit_card_3893",
        {"card_id": path["card_id"]},
        discoverable=True,
    )


_RESPONSE_TYPES: dict[str, Any] = {
    "get_user_information_by_id": BankingCustomer,
    "change_user_email": CustomerEmail,
    "get_referrals_by_user": list[Referral],
    "get_credit_card_transactions_by_user": list[CreditCardTransaction],
    "get_credit_card_accounts_by_user": list[CreditCardAccount],
    "log_verification": VerificationReceipt,
    "get_current_time": ServerTime,
    "give_discoverable_user_tool": SelfServiceActionReceipt,
    "update_transaction_rewards_3847": RewardsUpdateReceipt,
    "file_credit_card_transaction_dispute_4829": CreditCardDispute,
    "file_debit_card_transaction_dispute_6281": DebitCardDispute,
    "set_debit_card_recurring_block_7382": RecurringBlockReceipt,
    "get_debit_dispute_status_7483": list[DebitCardDispute],
    "get_atm_deposit_images_8473": AtmDepositImages,
    "order_replacement_credit_card_7291": ReplacementOrder,
    "get_user_dispute_history_7291": list[CreditCardDispute],
    "get_pending_replacement_orders_5765": list[ReplacementOrder],
    "log_credit_card_closure_reason_4521": ClosureReason,
    "get_closure_reason_history_8293": list[ClosureReason],
    "apply_statement_credit_8472": CreditCardMutationReceipt,
    "apply_credit_card_account_flag_6147": CreditCardMutationReceipt,
    "downgrade_credit_card_3847": CreditCardMutationReceipt,
    "close_credit_card_account_7834": CreditCardMutationReceipt,
    "pay_credit_card_from_checking_9182": CreditCardPaymentReceipt,
    "submit_credit_limit_increase_request_7392": CreditLimitRequest,
    "get_credit_limit_increase_history_4829": list[CreditLimitRequest],
    "get_payment_history_6183": PaymentHistory,
    "approve_credit_limit_increase_5847": CreditLimitRequest,
    "deny_credit_limit_increase_5848": CreditLimitRequest,
    "open_bank_account_4821": BankAccountCreationReceipt,
    "close_bank_account_7392": AccountClosureReceipt,
    "get_all_user_accounts_by_user_id_3847": CustomerAccounts,
    "transfer_funds_between_bank_accounts_7291": AccountTransferReceipt,
    "apply_checking_account_credit_5829": CreditReceipt,
    "apply_savings_account_credit_6831": CreditReceipt,
    "submit_interest_discrepancy_report_7294": InterestReportReceipt,
    "get_bank_account_transactions_9173": list[BankAccountTransaction],
    "order_debit_card_5739": DebitCardOrderReceipt,
    "activate_debit_card_8291": DebitCardMutationReceipt,
    "activate_debit_card_8292": DebitCardMutationReceipt,
    "activate_debit_card_8293": DebitCardMutationReceipt,
    "close_debit_card_4721": DebitCardMutationReceipt,
    "freeze_debit_card_3892": DebitCardMutationReceipt,
    "unfreeze_debit_card_3893": DebitCardMutationReceipt,
    "clear_debit_card_fraud_alert_4892": DebitCardMutationReceipt,
    "reset_debit_card_pin_6284": DebitCardMutationReceipt,
    "change_debit_card_pin_6285": DebitCardMutationReceipt,
    "get_debit_cards_by_account_id_7823": list[DebitCard],
    "request_temporary_debit_card_limit_increase_8374": TemporaryLimitIncreaseReceipt,
}


def _adapt_customer_search_response(
    invocation: OperationInvocation, result: Any, environment: Any
) -> list[dict[str, Any]]:
    _legacy_error(result)
    db = _banking_db(environment)
    selector = next(iter(invocation.arguments.items()))
    field = {"user_id": "user_id", "customer_name": "name", "email": "email"}[
        selector[0]
    ]
    return [
        {"customer_id": record["user_id"], "name": record["name"]}
        for _, record in _records(db, "users")
        if record.get(field) == selector[1]
    ]


def _card_mutation(
    db: Any, invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    card_id = invocation.arguments["card_id"]
    _, card = _find_one(db, "debit_cards", card_id=card_id)
    account_id = card.get("account_id")
    deactivated = []
    grace = []
    if account_id:
        for other_id, other in _records(db, "debit_cards"):
            if other_id == card_id or other.get("account_id") != account_id:
                continue
            if other.get("status") == "DEACTIVATED":
                deactivated.append(other_id)
            elif other.get("status") == "GRACE_PERIOD":
                grace.append(other_id)
    effective_on = next(
        (
            card.get(field)
            for field in (
                "activated_date",
                "closed_date",
                "frozen_date",
                "unfrozen_date",
            )
            if card.get(field)
        ),
        None,
    )
    return {
        "card_id": card_id,
        "status": card.get("status", "updated").lower(),
        "effective_on": effective_on,
        "issue_reason": card.get("issue_reason"),
        "deactivated_card_ids": deactivated,
        "grace_period_card_ids": grace,
        "notices": _notices(result),
    }


def _adapt_atm_images(invocation: OperationInvocation, result: str) -> dict[str, Any]:
    transaction_id = invocation.arguments["transaction_id"]
    available = "IMAGES NOT AVAILABLE" not in result
    notes_marker = "--- VERIFICATION NOTES ---"
    notes = result.split(notes_marker, 1)[1].strip() if notes_marker in result else None
    recorded = _label(result, "Amount Recorded by ATM") or _label(
        result, "Amount Recorded"
    )
    check = None
    if "Item 1: Personal Check" in result:
        check_amount = _label(result, "Amount")
        check = {
            "check_number": _label(result, "Check Number"),
            "drawn_on": _label(result, "Drawn On"),
            "payee": _label(result, "Payee"),
            "amount": _money(check_amount),
            "memo": (_label(result, "Memo") or "").strip('"') or None,
            "signature_status": _label(result, "Signature"),
            "date_on_check": _label(result, "Date on Check"),
        }
    denominations = [
        {
            "count": int(match.group(1)),
            "denomination": _money(match.group(2)),
            "total": _money(match.group(3)),
        }
        for match in re.finditer(
            r"^\s*\*\s*(\d+)\s*x\s*\$([\d,.]+)\s+bills?\s*=\s*\$([\d,.]+)",
            result,
            flags=re.MULTILINE | re.IGNORECASE,
        )
    ]
    cash_total = _label(result, "Cash Total")
    cash = (
        {"amount": _money(cash_total), "denominations": denominations}
        if cash_total is not None
        else None
    )
    quality = {
        "envelope_scan": _label(result, "Envelope scan"),
        "check_front": _label(result, "Check front"),
        "check_back": _label(result, "Check back (endorsement)"),
        "cash_image": _label(result, "Cash image"),
    }
    discrepancy_match = re.search(
        r"DISCREPANCY DETECTED:\s*\$([\d,.]+)", result, flags=re.IGNORECASE
    )
    return {
        "transaction_id": transaction_id,
        "atm_id": _label(result, "ATM") or "Unknown",
        "deposit_date": _label(result, "Deposit Date") or "Unknown",
        "available": available,
        "envelope_id": _label(result, "Envelope ID"),
        "deposit_time": _label(result, "Deposit Time"),
        "atm_location": _label(result, "ATM Location"),
        "check": check,
        "cash": cash,
        "imaged_amount": (_money(_label(result, "GRAND TOTAL")) if available else None),
        "recorded_amount": _money(recorded) if recorded is not None else None,
        "discrepancy_amount": (
            _money(discrepancy_match.group(1)) if discrepancy_match else None
        ),
        "image_quality": quality,
        "unavailable_reason": _label(result, "Reason") if not available else None,
        "verification_notes": notes,
    }


def _adapt_banking_response(
    invocation: OperationInvocation, result: Any, environment: Any
) -> Any:
    _legacy_error(result)
    db = _banking_db(environment)
    name = invocation.tool_name
    args = invocation.arguments

    if name == "get_user_information_by_id":
        _, record = _find_one(db, "users", user_id=args["user_id"])
        return _customer(record)
    if name == "change_user_email":
        return {"customer_id": args["user_id"], "email": args["new_email"]}
    if name == "get_referrals_by_user":
        return [
            _referral(record_id, record)
            for record_id, record in _records(db, "referrals")
            if record.get("referrer_id") == args["user_id"]
        ]
    if name == "get_credit_card_transactions_by_user":
        return [
            _credit_card_transaction(record)
            for _, record in _records(db, "credit_card_transaction_history")
            if record.get("user_id") == args["user_id"]
        ]
    if name == "get_credit_card_accounts_by_user":
        return [
            _credit_card_account(record)
            for _, record in _records(db, "credit_card_accounts")
            if record.get("user_id") == args["user_id"]
        ]
    if name == "log_verification":
        record_id, record = _find_one(
            db,
            "verification_history",
            user_id=args["user_id"],
            time_verified=args["time_verified"],
        )
        return {
            "verification_id": record_id,
            "customer_id": record["user_id"],
            "status": "logged",
            "verified_at": record["time_verified"],
        }
    if name == "get_current_time":
        timestamp = str(result).removeprefix("The current time is ").removesuffix(".")
        return {"timestamp": timestamp}
    if name == "give_discoverable_user_tool":
        return {"action_name": args["discoverable_tool_name"], "status": "offered"}
    if name == "update_transaction_rewards_3847":
        return {
            "transaction_id": args["transaction_id"],
            "rewards_earned": args["new_rewards_earned"],
        }
    if name == "file_credit_card_transaction_dispute_4829":
        record_id, record = _find_one(
            db,
            "transaction_disputes",
            transaction_id=args["transaction_id"],
            user_id=args["user_id"],
        )
        return _credit_card_dispute(record_id, record)
    if name == "file_debit_card_transaction_dispute_6281":
        record_id, record = _find_one(
            db,
            "debit_card_disputes",
            transaction_id=args["transaction_id"],
            user_id=args["user_id"],
        )
        return _debit_card_dispute(record_id, record)
    if name == "set_debit_card_recurring_block_7382":
        return {
            "card_id": args["card_id"],
            "recurring_payments_blocked": args["block_recurring"],
            "effective_within_hours": 24,
            "one_time_purchases_affected": False,
        }
    if name == "get_debit_dispute_status_7483":
        return [
            _debit_card_dispute(record_id, record)
            for record_id, record in _records(db, "debit_card_disputes")
            if record.get("user_id") == args["user_id"]
        ]
    if name == "get_atm_deposit_images_8473":
        return _adapt_atm_images(invocation, str(result))
    if name == "order_replacement_credit_card_7291":
        record_id, record = _find_one(
            db,
            "credit_card_orders",
            credit_card_account_id=args["credit_card_account_id"],
            user_id=args["user_id"],
            reason=args["reason"],
        )
        return _replacement_order(record_id, record)
    if name == "get_user_dispute_history_7291":
        return [
            _credit_card_dispute(record_id, record)
            for record_id, record in _records(db, "transaction_disputes")
            if record.get("user_id") == args["user_id"]
        ]
    if name == "get_pending_replacement_orders_5765":
        return [
            _replacement_order(record_id, record)
            for record_id, record in _records(db, "credit_card_orders")
            if record.get("credit_card_account_id") == args["credit_card_account_id"]
        ]
    if name == "log_credit_card_closure_reason_4521":
        record_id, record = _find_one(
            db,
            "credit_card_closure_reasons",
            credit_card_account_id=args["credit_card_account_id"],
            user_id=args["user_id"],
        )
        return _closure_reason(record_id, record)
    if name == "get_closure_reason_history_8293":
        return [
            _closure_reason(record_id, record)
            for record_id, record in _records(db, "credit_card_closure_reasons")
            if record.get("credit_card_account_id") == args["credit_card_account_id"]
        ]
    if name == "apply_statement_credit_8472":
        transaction_id = _label(str(result), "Transaction ID")
        balance = _find_one(
            db, "credit_card_accounts", account_id=args["credit_card_account_id"]
        )[1].get("current_balance", 0)
        return {
            "account_id": args["credit_card_account_id"],
            "status": "posted",
            "effective_on": _label(str(result), "Date"),
            "transaction_id": transaction_id,
            "amount": args["amount"],
            "balance": _money(balance),
            "reason": args["reason"],
        }
    if name == "apply_credit_card_account_flag_6147":
        return {
            "account_id": args["credit_card_account_id"],
            "status": "active",
            "effective_on": _label(str(result), "Effective Date"),
            "flag_id": _label(str(result), "Flag ID"),
            "reason": args["reason"],
        }
    if name == "downgrade_credit_card_3847":
        return {
            "account_id": args["credit_card_account_id"],
            "status": "active",
            "card_type": args["target_card_type"],
        }
    if name == "close_credit_card_account_7834":
        _, account = _find_one(
            db, "credit_card_accounts", account_id=args["credit_card_account_id"]
        )
        return {
            "account_id": args["credit_card_account_id"],
            "status": "closed",
            "effective_on": account.get("closed_date"),
        }
    if name == "pay_credit_card_from_checking_9182":
        _, checking = _find_one(db, "accounts", account_id=args["checking_account_id"])
        _, credit = _find_one(
            db, "credit_card_accounts", account_id=args["credit_card_account_id"]
        )
        return {
            "account_id": args["credit_card_account_id"],
            "checking_account_id": args["checking_account_id"],
            "amount": args["amount"],
            "credit_card_balance": _money(credit.get("current_balance")),
            "checking_account_balance": _money(checking.get("current_holdings")),
            "status": "completed",
        }
    if name in {
        "submit_credit_limit_increase_request_7392",
        "approve_credit_limit_increase_5847",
        "deny_credit_limit_increase_5848",
    }:
        desired_status = {
            "submit_credit_limit_increase_request_7392": "PENDING",
            "approve_credit_limit_increase_5847": "APPROVED",
            "deny_credit_limit_increase_5848": "DENIED",
        }[name]
        record_id, record = _find_one(
            db,
            "credit_limit_increase_requests",
            credit_card_account_id=args["credit_card_account_id"],
            status=desired_status,
        )
        return _credit_limit_request(record_id, record)
    if name == "get_credit_limit_increase_history_4829":
        return [
            _credit_limit_request(record_id, record)
            for record_id, record in _records(db, "credit_limit_increase_requests")
            if record.get("credit_card_account_id") == args["credit_card_account_id"]
        ]
    if name == "get_payment_history_6183":
        payments = [
            record
            for _, record in _records(db, "payment_history")
            if record.get("credit_card_account_id") == args["credit_card_account_id"]
        ]
        payments.sort(key=lambda record: record.get("payment_date", ""), reverse=True)
        payments = payments[: args["months"]]
        consecutive = 0
        for payment in payments:
            if payment.get("status") != "ON_TIME":
                break
            consecutive += 1
        return {
            "account_id": args["credit_card_account_id"],
            "requested_months": args["months"],
            "consecutive_on_time_payments": consecutive,
            "payments": [
                {
                    "payment_id": payment.get("payment_id"),
                    "payment_date": payment.get("payment_date", ""),
                    "amount": _money(payment.get("amount")),
                    "status": payment.get("status", "UNKNOWN"),
                }
                for payment in payments
            ],
        }
    if name == "open_bank_account_4821":
        _, account = _find_one(
            db,
            "accounts",
            user_id=args["user_id"],
            account_type=args["account_type"],
            account_class=args["account_class"],
        )
        return {"account": _bank_account(account)}
    if name == "close_bank_account_7392":
        _, account = _find_one(db, "accounts", account_id=args["account_id"])
        return {
            "account_id": args["account_id"],
            "status": "closed",
            "closed_on": account.get("date_closed", ""),
            "reason": account.get("closure_reason"),
            "early_closure_fee_waived": account.get("early_closure_fee_waived"),
        }
    if name == "get_all_user_accounts_by_user_id_3847":
        return {
            "bank_accounts": [
                _bank_account(record)
                for _, record in _records(db, "accounts")
                if record.get("user_id") == args["user_id"]
            ],
            "credit_card_accounts": [
                _credit_card_account(record)
                for _, record in _records(db, "credit_card_accounts")
                if record.get("user_id") == args["user_id"]
            ],
        }
    if name == "transfer_funds_between_bank_accounts_7291":
        _, source = _find_one(db, "accounts", account_id=args["source_account_id"])
        _, destination = _find_one(
            db, "accounts", account_id=args["destination_account_id"]
        )
        return {
            "source_account_id": args["source_account_id"],
            "destination_account_id": args["destination_account_id"],
            "amount": args["amount"],
            "source_balance": _money(source.get("current_holdings")),
            "destination_balance": _money(destination.get("current_holdings")),
            "status": "completed",
        }
    if name in {
        "apply_checking_account_credit_5829",
        "apply_savings_account_credit_6831",
    }:
        _, account = _find_one(db, "accounts", account_id=args["account_id"])
        return {
            "transaction_id": _label(str(result), "Transaction ID") or "unknown",
            "account_id": args["account_id"],
            "amount": args["amount"],
            "credit_type": args["credit_type"],
            "balance": _money(account.get("current_holdings")),
            "status": "posted",
        }
    if name == "submit_interest_discrepancy_report_7294":
        return {
            "report_id": _label(str(result), "Report ID") or "unknown",
            "account_id": args["account_id"],
            "status": "pending_review",
            "expected_apy": args["expected_apy"],
            "actual_apy": args["actual_apy"],
            "amount_difference": args["amount_difference"],
        }
    if name == "get_bank_account_transactions_9173":
        transactions = [
            (record_id, record)
            for record_id, record in _records(db, "bank_account_transaction_history")
            if record.get("account_id") == args["account_id"]
        ]

        def sort_key(item: tuple[str, dict[str, Any]]) -> datetime:
            for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y"):
                try:
                    return datetime.strptime(str(item[1].get("date", "")), fmt)
                except ValueError:
                    continue
            return datetime.min

        transactions.sort(key=sort_key, reverse=True)
        return [
            _bank_transaction(record_id, record) for record_id, record in transactions
        ]
    if name == "order_debit_card_5739":
        order_id, order = _find_one(
            db,
            "debit_card_orders",
            account_id=args["account_id"],
            user_id=args["user_id"],
            status="PENDING",
        )
        card_id, _ = _find_one(
            db, "debit_cards", account_id=args["account_id"], status="PENDING"
        )
        _, account = _find_one(db, "accounts", account_id=args["account_id"])
        return {
            "order_id": order.get("order_id", order_id),
            "card_id": card_id,
            "account_id": args["account_id"],
            "status": order.get("status", "PENDING").lower(),
            "delivery_option": order["delivery_option"],
            "card_design": order["card_design"],
            "shipping_address": order["shipping_address"],
            "expected_delivery": order["expected_delivery"],
            "total_fee": _money(order.get("total_fee")),
            "balance": _money(account.get("current_holdings")),
        }
    if name in {
        "activate_debit_card_8291",
        "activate_debit_card_8292",
        "activate_debit_card_8293",
        "close_debit_card_4721",
        "freeze_debit_card_3892",
        "unfreeze_debit_card_3893",
        "clear_debit_card_fraud_alert_4892",
        "reset_debit_card_pin_6284",
        "change_debit_card_pin_6285",
    }:
        return _card_mutation(db, invocation, result)
    if name == "get_debit_cards_by_account_id_7823":
        cards = [
            (record_id, record)
            for record_id, record in _records(db, "debit_cards")
            if record.get("account_id") == args["account_id"]
        ]
        cards.sort(
            key=lambda item: item[1].get("issue_date", item[1].get("created_date", "")),
            reverse=True,
        )
        return [_debit_card(record_id, record) for record_id, record in cards]
    if name == "request_temporary_debit_card_limit_increase_8374":
        _, card = _find_one(db, "debit_cards", card_id=args["card_id"])
        previous = card.get(f"original_{args['limit_type']}_limit")
        return {
            "card_id": args["card_id"],
            "limit_type": args["limit_type"],
            "previous_limit": _money(previous),
            "new_limit": _money(card.get(f"daily_{args['limit_type']}_limit")),
            "expires_in_hours": 24,
            "notices": _notices(result),
        }
    raise ValueError(f"No Banking response projection for {name}")


def operations() -> tuple[ClientOperation, ...]:
    """Return initial and knowledge-discovered Banking Client operations."""

    initial = (
        ClientOperation(
            method="POST",
            path="/v1/customers/search",
            operation_id="searchBankingCustomers",
            summary="Find a banking customer",
            description="Find a banking customer using one supported identifier.",
            response_type=list[CustomerSearchResult],
            body_type=BankingCustomerSearchRequest,
            invoke=_customer_search,
            reference_tool_names=(
                "get_user_information_by_id",
                "get_user_information_by_name",
                "get_user_information_by_email",
            ),
            environment_response_adapter=_adapt_customer_search_response,
        ),
        _operation(
            "GET",
            "/v1/customers/{customer_id}",
            "getBankingCustomer",
            "Retrieve a banking customer.",
            "get_user_information_by_id",
            path_arguments={"customer_id": "user_id"},
        ),
        _operation(
            "PUT",
            "/v1/customers/{customer_id}/email",
            "replaceBankingCustomerEmail",
            "Replace a banking customer's email address.",
            "change_user_email",
            body_type=CustomerEmailRequest,
            transform=_customer_email_arguments,
            mutates_state=True,
        ),
        _operation(
            "GET",
            "/v1/customers/{customer_id}/referrals",
            "listBankingCustomerReferrals",
            "List referrals made by a banking customer.",
            "get_referrals_by_user",
            path_arguments={"customer_id": "user_id"},
        ),
        _operation(
            "GET",
            "/v1/customers/{customer_id}/credit-card-transactions",
            "listBankingCustomerCreditCardTransactions",
            "List a customer's credit-card transactions.",
            "get_credit_card_transactions_by_user",
            path_arguments={"customer_id": "user_id"},
        ),
        _operation(
            "GET",
            "/v1/customers/{customer_id}/credit-card-accounts",
            "listBankingCustomerCreditCardAccounts",
            "List a customer's credit-card accounts.",
            "get_credit_card_accounts_by_user",
            path_arguments={"customer_id": "user_id"},
        ),
        _operation(
            "POST",
            "/v1/customers/{customer_id}/verifications",
            "recordBankingCustomerVerification",
            "Create a customer identity-verification record.",
            "log_verification",
            body_type=VerificationRequest,
            path_arguments={"customer_id": "user_id"},
            mutates_state=True,
        ),
        _operation(
            "GET",
            "/v1/time",
            "getServerTime",
            "Retrieve the current server timestamp.",
            "get_current_time",
        ),
        _operation(
            "POST",
            "/v1/customer-self-service-actions",
            "offerCustomerSelfServiceAction",
            "Create a customer self-service action resource.",
            "give_discoverable_user_tool",
            body_type=SelfServiceActionRequest,
            transform=_self_service_arguments,
            mutates_state=True,
        ),
        ClientOperation(
            method="POST",
            path="/v1/conversations/{conversation_id}/transfers",
            operation_id="createConversationTransfer",
            summary="Transfer a conversation to a human agent",
            description=(
                "Create a live transfer of one active banking conversation to "
                "a human support agent."
            ),
            response_type=ConversationTransferReceipt,
            body_type=ConversationTransferRequest,
            invoke=lambda _path, _query, body: OperationInvocation(
                "transfer_to_human_agents", {"summary": body.summary}
            ),
            success_status=201,
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            execution="conversation_transfer",
            reference_tool_names=("transfer_to_human_agents",),
        ),
    )

    discovered = (
        _discovered(
            "PATCH",
            "/v1/credit-card-transactions/{transaction_id}/rewards",
            "replaceCreditCardTransactionRewards",
            "Replace the rewards recorded for a credit-card transaction.",
            "update_transaction_rewards_3847",
            body_type=RewardsUpdateRequest,
            path_arguments={"transaction_id": "transaction_id"},
            mutates_state=True,
        ),
        _discovered(
            "POST",
            "/v1/credit-card-transactions/{transaction_id}/disputes",
            "fileCreditCardTransactionDispute",
            "File a credit-card transaction dispute.",
            "file_credit_card_transaction_dispute_4829",
            body_type=CreditCardDisputeRequest,
            path_arguments={"transaction_id": "transaction_id"},
            mutates_state=True,
        ),
        _discovered(
            "POST",
            "/v1/debit-card-transactions/{transaction_id}/disputes",
            "fileDebitCardTransactionDispute",
            "File a debit-card transaction dispute.",
            "file_debit_card_transaction_dispute_6281",
            body_type=DebitCardDisputeRequest,
            path_arguments={"transaction_id": "transaction_id"},
            mutates_state=True,
        ),
        _discovered(
            "PUT",
            "/v1/debit-cards/{card_id}/recurring-payment-block",
            "replaceDebitCardRecurringPaymentBlock",
            "Set whether a debit card blocks recurring payments.",
            "set_debit_card_recurring_block_7382",
            body_type=RecurringBlockRequest,
            path_arguments={"card_id": "card_id"},
            mutates_state=True,
        ),
        _discovered(
            "GET",
            "/v1/customers/{customer_id}/debit-card-disputes",
            "listCustomerDebitCardDisputes",
            "List a customer's debit-card disputes.",
            "get_debit_dispute_status_7483",
            path_arguments={"customer_id": "user_id"},
        ),
        _discovered(
            "GET",
            "/v1/atm-deposits/{transaction_id}/images",
            "getAtmDepositImages",
            "Retrieve images associated with an ATM deposit.",
            "get_atm_deposit_images_8473",
            path_arguments={"transaction_id": "transaction_id"},
        ),
        _discovered(
            "POST",
            "/v1/credit-card-accounts/{account_id}/replacement-orders",
            "createCreditCardReplacementOrder",
            "Create a replacement-card order for a credit-card account.",
            "order_replacement_credit_card_7291",
            body_type=ReplacementCreditCardRequest,
            path_arguments={"account_id": "credit_card_account_id"},
            mutates_state=True,
        ),
        _discovered(
            "GET",
            "/v1/customers/{customer_id}/credit-card-disputes",
            "listCustomerCreditCardDisputes",
            "List a customer's credit-card transaction disputes.",
            "get_user_dispute_history_7291",
            path_arguments={"customer_id": "user_id"},
        ),
        _discovered(
            "GET",
            "/v1/credit-card-accounts/{account_id}/pending-replacement-orders",
            "listPendingCreditCardReplacementOrders",
            "List pending replacement orders for a credit-card account.",
            "get_pending_replacement_orders_5765",
            path_arguments={"account_id": "credit_card_account_id"},
        ),
        _discovered(
            "POST",
            "/v1/credit-card-accounts/{account_id}/closure-reasons",
            "recordCreditCardClosureReason",
            "Record a customer's reason for closing a credit-card account.",
            "log_credit_card_closure_reason_4521",
            body_type=ClosureReasonRequest,
            path_arguments={"account_id": "credit_card_account_id"},
            mutates_state=True,
        ),
        _discovered(
            "GET",
            "/v1/credit-card-accounts/{account_id}/closure-reasons",
            "listCreditCardClosureReasons",
            "List recorded closure reasons for a credit-card account.",
            "get_closure_reason_history_8293",
            path_arguments={"account_id": "credit_card_account_id"},
        ),
        _discovered(
            "POST",
            "/v1/credit-card-accounts/{account_id}/statement-credits",
            "createCreditCardStatementCredit",
            "Apply a statement credit to a credit-card account.",
            "apply_statement_credit_8472",
            body_type=StatementCreditRequest,
            path_arguments={"account_id": "credit_card_account_id"},
            mutates_state=True,
        ),
        _discovered(
            "POST",
            "/v1/credit-card-accounts/{account_id}/flags",
            "createCreditCardAccountFlag",
            "Apply a dated account flag to a credit-card account.",
            "apply_credit_card_account_flag_6147",
            body_type=CreditCardFlagRequest,
            path_arguments={"account_id": "credit_card_account_id"},
            mutates_state=True,
        ),
        _discovered(
            "POST",
            "/v1/credit-card-accounts/{account_id}/downgrades",
            "createCreditCardDowngrade",
            "Downgrade a credit-card account to an eligible no-annual-fee card.",
            "downgrade_credit_card_3847",
            body_type=CreditCardDowngradeRequest,
            path_arguments={"account_id": "credit_card_account_id"},
            mutates_state=True,
        ),
        _discovered(
            "POST",
            "/v1/credit-card-accounts/{account_id}/closure",
            "closeCreditCardAccount",
            "Close a credit-card account.",
            "close_credit_card_account_7834",
            body_type=CustomerIdRequest,
            path_arguments={"account_id": "credit_card_account_id"},
            mutates_state=True,
        ),
        _discovered(
            "POST",
            "/v1/credit-card-accounts/{account_id}/payments",
            "createCreditCardPayment",
            "Pay a credit-card account from a checking account.",
            "pay_credit_card_from_checking_9182",
            body_type=CreditCardPaymentRequest,
            path_arguments={"account_id": "credit_card_account_id"},
            mutates_state=True,
        ),
        _discovered(
            "POST",
            "/v1/credit-card-accounts/{account_id}/credit-limit-increase-requests",
            "createCreditLimitIncreaseRequest",
            "Submit a credit-limit increase request.",
            "submit_credit_limit_increase_request_7392",
            body_type=CreditLimitIncreaseRequest,
            path_arguments={"account_id": "credit_card_account_id"},
            mutates_state=True,
        ),
        _discovered(
            "GET",
            "/v1/credit-card-accounts/{account_id}/credit-limit-increase-requests",
            "listCreditLimitIncreaseRequests",
            "List credit-limit increase requests for a credit-card account.",
            "get_credit_limit_increase_history_4829",
            path_arguments={"account_id": "credit_card_account_id"},
        ),
        _discovered(
            "GET",
            "/v1/credit-card-accounts/{account_id}/payment-history",
            "getCreditCardPaymentHistory",
            "Retrieve payment history for a credit-card account.",
            "get_payment_history_6183",
            query_type=PaymentHistoryQuery,
            path_arguments={"account_id": "credit_card_account_id"},
        ),
        _discovered(
            "POST",
            "/v1/credit-card-accounts/{account_id}/credit-limit-increase-approvals",
            "approveCreditLimitIncrease",
            "Approve and apply a credit-limit increase.",
            "approve_credit_limit_increase_5847",
            body_type=CreditLimitApprovalRequest,
            path_arguments={"account_id": "credit_card_account_id"},
            mutates_state=True,
        ),
        _discovered(
            "POST",
            "/v1/credit-card-accounts/{account_id}/credit-limit-increase-denials",
            "denyCreditLimitIncrease",
            "Deny a credit-limit increase request.",
            "deny_credit_limit_increase_5848",
            body_type=CreditLimitDenialRequest,
            path_arguments={"account_id": "credit_card_account_id"},
            mutates_state=True,
        ),
        _discovered(
            "POST",
            "/v1/customers/{customer_id}/bank-accounts",
            "createBankAccount",
            "Open a bank account for a customer.",
            "open_bank_account_4821",
            body_type=BankAccountRequest,
            path_arguments={"customer_id": "user_id"},
            mutates_state=True,
        ),
        _discovered(
            "POST",
            "/v1/bank-accounts/{account_id}/closure",
            "closeBankAccount",
            "Close a checking or savings account.",
            "close_bank_account_7392",
            body_type=BankAccountClosureRequest,
            path_arguments={"account_id": "account_id"},
            mutates_state=True,
        ),
        _discovered(
            "GET",
            "/v1/customers/{customer_id}/accounts",
            "listCustomerBankAccounts",
            "List all bank and credit-card accounts for a customer.",
            "get_all_user_accounts_by_user_id_3847",
            path_arguments={"customer_id": "user_id"},
        ),
        _discovered(
            "POST",
            "/v1/bank-account-transfers",
            "createBankAccountTransfer",
            "Transfer funds between bank accounts.",
            "transfer_funds_between_bank_accounts_7291",
            body_type=BankTransferRequest,
            mutates_state=True,
        ),
        _discovered(
            "POST",
            "/v1/checking-accounts/{account_id}/credits",
            "createCheckingAccountCredit",
            "Apply a credit to a checking account.",
            "apply_checking_account_credit_5829",
            body_type=AccountCreditRequest,
            path_arguments={"account_id": "account_id"},
            mutates_state=True,
        ),
        _discovered(
            "POST",
            "/v1/savings-accounts/{account_id}/credits",
            "createSavingsAccountCredit",
            "Apply a credit to a savings account.",
            "apply_savings_account_credit_6831",
            body_type=AccountCreditRequest,
            path_arguments={"account_id": "account_id"},
            mutates_state=True,
        ),
        _discovered(
            "POST",
            "/v1/savings-accounts/{account_id}/interest-discrepancy-reports",
            "createInterestDiscrepancyReport",
            "Submit an interest discrepancy report.",
            "submit_interest_discrepancy_report_7294",
            body_type=InterestDiscrepancyRequest,
            path_arguments={"account_id": "account_id"},
            mutates_state=True,
        ),
        _discovered(
            "GET",
            "/v1/bank-accounts/{account_id}/transactions",
            "listBankAccountTransactions",
            "List transactions for a bank account.",
            "get_bank_account_transactions_9173",
            path_arguments={"account_id": "account_id"},
        ),
        _discovered(
            "POST",
            "/v1/checking-accounts/{account_id}/debit-card-orders",
            "createDebitCardOrder",
            "Order a debit card for a checking account.",
            "order_debit_card_5739",
            body_type=DebitCardOrderRequest,
            path_arguments={"account_id": "account_id"},
            mutates_state=True,
        ),
        ClientOperation(
            method="POST",
            path="/v1/debit-cards/{card_id}/activation",
            operation_id="activateDebitCard",
            summary="Activate a debit card",
            description="Activate a new, replacement, or reissued debit card.",
            response_type=DebitCardMutationReceipt,
            body_type=ActivationRequest,
            invoke=_activation,
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            advertised=False,
            reference_tool_names=(
                "activate_debit_card_8291",
                "activate_debit_card_8292",
                "activate_debit_card_8293",
            ),
            environment_response_adapter=_adapt_banking_response,
        ),
        _discovered(
            "POST",
            "/v1/debit-cards/{card_id}/closure",
            "closeDebitCard",
            "Close a debit card permanently.",
            "close_debit_card_4721",
            body_type=ReasonRequest,
            path_arguments={"card_id": "card_id"},
            mutates_state=True,
        ),
        ClientOperation(
            method="PUT",
            path="/v1/debit-cards/{card_id}/frozen-state",
            operation_id="replaceDebitCardFrozenState",
            summary="Set debit-card frozen state",
            description="Freeze or unfreeze a debit card.",
            response_type=DebitCardMutationReceipt,
            body_type=FrozenStateRequest,
            invoke=_frozen_state,
            mutates_state=True,
            idempotency="safe",
            automatic_retries="allowed",
            advertised=False,
            reference_tool_names=(
                "freeze_debit_card_3892",
                "unfreeze_debit_card_3893",
            ),
            environment_response_adapter=_adapt_banking_response,
        ),
        _discovered(
            "POST",
            "/v1/debit-cards/{card_id}/fraud-alert-clearances",
            "clearDebitCardFraudAlert",
            "Clear a fraud alert on a debit card.",
            "clear_debit_card_fraud_alert_4892",
            body_type=FraudAlertClearRequest,
            path_arguments={"card_id": "card_id"},
            mutates_state=True,
        ),
        _discovered(
            "POST",
            "/v1/debit-cards/{card_id}/pin-resets",
            "resetDebitCardPin",
            "Reset a debit-card PIN.",
            "reset_debit_card_pin_6284",
            body_type=PinResetRequest,
            path_arguments={"card_id": "card_id"},
            mutates_state=True,
        ),
        _discovered(
            "POST",
            "/v1/debit-cards/{card_id}/pin-changes",
            "changeDebitCardPin",
            "Change a debit-card PIN using the current PIN.",
            "change_debit_card_pin_6285",
            body_type=PinChangeRequest,
            path_arguments={"card_id": "card_id"},
            mutates_state=True,
        ),
        _discovered(
            "GET",
            "/v1/checking-accounts/{account_id}/debit-cards",
            "listCheckingAccountDebitCards",
            "List debit cards associated with a checking account.",
            "get_debit_cards_by_account_id_7823",
            path_arguments={"account_id": "account_id"},
        ),
        _discovered(
            "POST",
            "/v1/debit-cards/{card_id}/temporary-limit-increases",
            "createTemporaryDebitCardLimitIncrease",
            "Request a temporary debit-card limit increase.",
            "request_temporary_debit_card_limit_increase_8374",
            body_type=TemporaryLimitIncreaseRequest,
            path_arguments={"card_id": "card_id"},
            mutates_state=True,
        ),
    )
    return (*initial, *discovered)
