"""Typed representations of Rho-Bank Client API resources.

These models mirror the documented request and response shapes described
across ``client_api/openapi.yaml`` and the knowledge-base procedures that
extend it (see sop.md, Section 4, "Knowledge-discovered API operations").
``workspace/tools.py`` uses them to build outgoing request bodies and to
parse incoming response bodies into a consistent, typed shape before handing
data back to the agent.

Every model here is defensive on purpose. Fields that are not confirmed to
appear on every record (either because a knowledge-base procedure only
mentions them in some cases, or because the full published schema was not
available while this module was written) are declared ``Optional`` with a
default of ``None``. Every model also allows unrecognized extra fields to
pass through untouched rather than raising, since the live API may return
additional fields beyond what any single knowledge-base procedure documents.

Enumerated (``Literal``) fields are only used where a knowledge-base
procedure or the handbook states the full, exhaustive set of allowed values.
Everywhere else, string fields are left as plain ``str`` so that an
unanticipated value from the real API does not fail validation.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict
from typing_extensions import Literal


class APIModel(BaseModel):
    """Base class for all Client API resource models."""

    model_config = ConfigDict(extra="allow")


# ---------------------------------------------------------------------------
# Generic / shared
# ---------------------------------------------------------------------------


class TimeResponse(APIModel):
    """Response body of GET /v1/time."""

    timestamp: str


class APIErrorDetail(APIModel):
    code: Optional[str] = None
    message: str


class APIError(APIModel):
    """Shared error envelope used by every documented Client API error."""

    error: APIErrorDetail


# ---------------------------------------------------------------------------
# Customer identity, profile, search, and verification
# ---------------------------------------------------------------------------


class CustomerProfile(APIModel):
    """A customer's core profile and top-level product references.

    Mirrors the shape used by client_api/development_seed.json test cases;
    a brand-new customer (no products yet) legitimately has most fields
    unset, so only ``customer_id`` is required.
    """

    customer_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    checking_account_id: Optional[str] = None
    savings_account_id: Optional[str] = None
    active_debit_card_id: Optional[str] = None
    pending_debit_card_id: Optional[str] = None
    credit_card_account_ids: Optional[List[str]] = None
    credit_card_transaction_id: Optional[str] = None
    bank_transaction_id: Optional[str] = None
    payment_history_id: Optional[str] = None
    referral_id: Optional[str] = None


class CustomerSearchResult(APIModel):
    """One candidate profile returned by POST /v1/customers/search."""

    customer_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None


class VerificationRecord(APIModel):
    """A logged identity-verification event for a customer."""

    customer_id: str
    verified: bool
    factors_used: Optional[List[str]] = None
    verified_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Bank accounts (personal and business checking / savings)
# ---------------------------------------------------------------------------


class BankAccount(APIModel):
    """One checking or savings account, personal or business."""

    account_id: str
    account_type: Optional[Literal["checking", "savings"]] = None
    account_class: Optional[str] = None  # product name, e.g. "Green Account"
    status: Optional[str] = None  # e.g. OPEN, CLOSED
    balance: Optional[float] = None
    date_opened: Optional[str] = None
    is_business: Optional[bool] = None


class CreditCardAccount(APIModel):
    """One credit-card account (personal or business)."""

    account_id: str
    product_name: Optional[str] = None  # e.g. "Platinum Rewards Card"
    tier: Optional[str] = None  # e.g. entry, mid, premium, invitation
    status: Optional[str] = None
    credit_limit: Optional[float] = None
    outstanding_balance: Optional[float] = None
    past_due_amount: Optional[float] = None
    open_date: Optional[str] = None
    is_business: Optional[bool] = None


class CustomerAccountsResponse(APIModel):
    """Response body of GET /v1/customers/{customer_id}/accounts."""

    bank_accounts: List[BankAccount] = []
    credit_card_accounts: List[CreditCardAccount] = []


class BankTransaction(APIModel):
    """One posted transaction on a checking or savings account."""

    transaction_id: str
    account_id: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    posted_at: Optional[str] = None
    type: Optional[str] = None


# ---------------------------------------------------------------------------
# Debit cards
# ---------------------------------------------------------------------------

DebitCardClosureReason = Literal[
    "lost",
    "stolen",
    "fraud_suspected",
    "damaged",
    "no_longer_needed",
    "account_closing",
]

DebitCardReissueIssueReason = Literal[
    "expired",
    "damaged",
    "upgrade",
    "bank_reissue",
]

DebitCardFraudAlertClearanceReason = Literal["customer_verified", "velocity_clear"]

DebitCardLimitType = Literal["atm", "purchase"]


class DebitCard(APIModel):
    """One debit card linked to a checking account."""

    card_id: str
    account_id: Optional[str] = None
    user_id: Optional[str] = None
    status: Optional[str] = None  # e.g. ACTIVE, PENDING, CLOSED, FROZEN
    issue_reason: Optional[str] = None
    last4: Optional[str] = None
    expiration_date: Optional[str] = None


class CheckingAccountDebitCardsResponse(APIModel):
    """Response body of GET /v1/checking-accounts/{account_id}/debit-cards."""

    debit_cards: List[DebitCard] = []


class DebitCardClosureRequest(APIModel):
    """Request body for POST /v1/debit-cards/{card_id}/closure."""

    card_id: str
    reason: DebitCardClosureReason


class DebitCardActivationRequest(APIModel):
    """Request body for POST /v1/debit-cards/{card_id}/activation."""

    card_id: str


class DebitCardTemporaryLimitIncreaseRequest(APIModel):
    """Request body for POST /v1/debit-cards/{card_id}/temporary-limit-increases."""

    card_id: str
    limit_type: DebitCardLimitType
    new_limit: float


class DebitCardFraudAlertClearanceRequest(APIModel):
    """Request body for POST /v1/debit-cards/{card_id}/fraud-alert-clearances."""

    card_id: str
    reason: DebitCardFraudAlertClearanceReason


# ---------------------------------------------------------------------------
# Credit card servicing: payments, disputes, replacements, limit increases
# ---------------------------------------------------------------------------


class CreditCardPaymentRequest(APIModel):
    """Request body for POST /v1/credit-card-accounts/{account_id}/payments."""

    source_account_id: str
    amount: float


class CreditLimitIncreaseRequest(APIModel):
    """Request body for POST /v1/credit-card-accounts/{account_id}/credit-limit-increase-requests."""

    credit_card_account_id: str
    user_id: str
    requested_increase_amount: float


CreditLimitDenialReason = Literal[
    "insufficient_account_age",
    "cooldown_period_active",
    "pending_disputes",
    "pending_replacement_card",
    "past_due_balance",
    "high_utilization",
    "insufficient_payment_history",
    "requested_amount_exceeds_limit",
    "other",
]


class CreditLimitIncreaseDenialRequest(APIModel):
    """Request body for POST /v1/credit-card-accounts/{account_id}/credit-limit-increase-denials."""

    credit_card_account_id: str
    user_id: str
    denial_reason: CreditLimitDenialReason


CreditCardReplacementReason = Literal[
    "fraud_suspected",
    "lost",
    "stolen",
    "damaged",
    "expired",
    "other",
]


class ReplacementOrder(APIModel):
    """One entry from GET /v1/credit-card-accounts/{account_id}/pending-replacement-orders."""

    order_id: str
    status: Optional[str] = None  # e.g. pending, shipped, delivered, cancelled
    created_at: Optional[str] = None
    latest_event_at: Optional[str] = None
    notes: Optional[str] = None


class PendingReplacementOrdersResponse(APIModel):
    orders: List[ReplacementOrder] = []


class CreditCardDispute(APIModel):
    """One record from a credit-card dispute filing or history listing."""

    dispute_id: str
    credit_card_account_id: Optional[str] = None
    transaction_id: Optional[str] = None
    reason: Optional[str] = None
    amount: Optional[float] = None
    status: Optional[str] = None
    provisional_credit_issued: Optional[bool] = None
    filed_at: Optional[str] = None


class CreditCardDisputesResponse(APIModel):
    """Response body of GET /v1/customers/{customer_id}/credit-card-disputes."""

    disputes: List[CreditCardDispute] = []


class PaymentHistoryEntry(APIModel):
    """One statement-period payment record for a credit card account."""

    payment_history_id: str
    credit_card_account_id: Optional[str] = None
    period: Optional[str] = None
    amount_paid: Optional[float] = None
    paid_on_time: Optional[bool] = None
    due_date: Optional[str] = None


class CreditCardTransaction(APIModel):
    """One posted transaction on a credit card account."""

    transaction_id: str
    credit_card_account_id: Optional[str] = None
    amount: Optional[float] = None
    merchant: Optional[str] = None
    posted_at: Optional[str] = None
    status: Optional[str] = None


# ---------------------------------------------------------------------------
# Referrals and applications
# ---------------------------------------------------------------------------


class Referral(APIModel):
    referral_id: str
    product_name: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[str] = None


class Application(APIModel):
    application_id: str
    product_name: Optional[str] = None
    status: Optional[str] = None
    submitted_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Human transfer
# ---------------------------------------------------------------------------


class TransferRequest(APIModel):
    """Request body for POST /v1/conversations/{conversation_id}/transfers."""

    summary: str


class TransferResult(APIModel):
    """Response body of POST /v1/conversations/{conversation_id}/transfers."""

    transfer_id: str
    status: str


# ---------------------------------------------------------------------------
# Customer self-service actions
# ---------------------------------------------------------------------------


class CustomerSelfServiceActionRequest(APIModel):
    """Request body for POST /v1/customer-self-service-actions.

    Used when a knowledge-base procedure instructs the customer to complete
    an action in their own app (for example, mobile check deposit) rather
    than having the agent perform it directly.
    """

    action_name: str
    parameters: Optional[dict] = None


class CustomerSelfServiceActionResult(APIModel):
    action_name: Optional[str] = None
    status: Optional[str] = None
    instructions: Optional[str] = None
