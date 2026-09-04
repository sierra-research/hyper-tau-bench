"""Shared data structures for the Rho-Bank support agent.

This module centralizes the small set of enums and lightweight records that
both the tool layer (``tools.py``) and the agent layer (``agent.py``) need to
agree on: the identity-verification bookkeeping, the exhaustive reason/enum
values documented for specialized write operations discovered in the
knowledge base, and the shape of a knowledge-base document. Keeping these in
one place avoids the two files drifting out of sync on what a "verified"
customer looks like or what values a given field accepts.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class VerificationFactor(str, Enum):
    """The four identity factors a customer can use to verify, per Section 2
    of the handbook. Any two matching factors are sufficient."""

    DATE_OF_BIRTH = "date_of_birth"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"


class DebitCardClosureReason(str, Enum):
    """Exhaustive closure reasons for POST /v1/debit-cards/{card_id}/closure,
    as documented in approved closure case records."""

    LOST = "lost"
    STOLEN = "stolen"
    FRAUD_SUSPECTED = "fraud_suspected"
    DAMAGED = "damaged"
    NO_LONGER_NEEDED = "no_longer_needed"
    ACCOUNT_CLOSING = "account_closing"


class CreditCardReplacementReason(str, Enum):
    """Exhaustive replacement reasons for credit-card replacement ordering."""

    FRAUD_SUSPECTED = "fraud_suspected"
    LOST = "lost"
    STOLEN = "stolen"
    DAMAGED = "damaged"
    EXPIRED = "expired"
    OTHER = "other"


class DebitCardActivationIssueReason(str, Enum):
    """issue_reason values on a PENDING/reissued debit card that determine
    which activation operation applies (activation vs. reissue activation)."""

    EXPIRED = "expired"
    DAMAGED = "damaged"
    UPGRADE = "upgrade"
    BANK_REISSUE = "bank_reissue"


class FraudAlertClearanceReason(str, Enum):
    """Exhaustive reason values for
    POST /v1/debit-cards/{card_id}/fraud-alert-clearances. Bank-initiated
    fraud alerts are never clearable through this operation regardless of
    reason; only customer-initiated velocity blocks and customer-verified
    holds can be cleared this way."""

    CUSTOMER_VERIFIED = "customer_verified"
    VELOCITY_CLEAR = "velocity_clear"


class TemporaryLimitType(str, Enum):
    """limit_type values for
    POST /v1/debit-cards/{card_id}/temporary-limit-increases."""

    ATM = "atm"
    PURCHASE = "purchase"


class CreditLimitIncreaseDenialReason(str, Enum):
    """Exhaustive denial_reason values for
    POST /v1/credit-card-accounts/{account_id}/credit-limit-increase-denials."""

    INSUFFICIENT_ACCOUNT_AGE = "insufficient_account_age"
    COOLDOWN_PERIOD_ACTIVE = "cooldown_period_active"
    PENDING_DISPUTES = "pending_disputes"
    PENDING_REPLACEMENT_CARD = "pending_replacement_card"
    PAST_DUE_BALANCE = "past_due_balance"
    HIGH_UTILIZATION = "high_utilization"
    INSUFFICIENT_PAYMENT_HISTORY = "insufficient_payment_history"
    REQUESTED_AMOUNT_EXCEEDS_LIMIT = "requested_amount_exceeds_limit"
    OTHER = "other"


class CreditCardDisputeReason(str, Enum):
    """Dispute reasons evidenced across approved dispute case records.
    unauthorized_fraudulent_charge is the only reason that skips the
    merchant-contact requirement and is the only reason exempt from the
    30-day-since-purchase rule that applies to goods_services_not_received."""

    UNAUTHORIZED_FRAUDULENT_CHARGE = "unauthorized_fraudulent_charge"
    DUPLICATE_CHARGE = "duplicate_charge"
    GOODS_SERVICES_NOT_RECEIVED = "goods_services_not_received"
    OTHER = "other"


class HumanTransferReasonCode(str, Enum):
    """Internal categorization for human-agent transfers, organized into the
    four priority tiers described in approved escalation case records. This
    is bookkeeping for the agent's own reasoning and working notes; it is
    not a field accepted by POST /v1/conversations/{conversation_id}/transfers,
    which only takes a free-text summary."""

    # Tier 1: specific functional/operational reasons.
    THIRD_PARTY_INQUIRY = "third_party_inquiry"
    COMPLEX_BILLING_DISPUTE = "complex_billing_dispute"
    CUSTOMER_DEMANDS_AFTER_UNAVAILABLE_OFFER_REFUSAL = (
        "customer_demands_after_unavailable_offer_refusal"
    )
    SECURITY_TEAM_REVIEW_REQUIRED = "security_team_review_required"
    # Tier 2: knowledge/capability gap - no procedure covers the request.
    NO_DOCUMENTED_PROCEDURE = "no_documented_procedure"
    # Tier 3: customer disposition, not tied to a specific operational gap.
    CUSTOMER_REQUESTS_HUMAN_NO_SPECIFIC_REASON = (
        "customer_requests_human_no_specific_reason"
    )
    # Tier 4: fallback / repeated request threshold reached.
    REPEATED_TRANSFER_REQUEST = "repeated_transfer_request"


class VerificationRecord(BaseModel):
    """Tracks whether, and how, the current customer has been verified.

    Verification only needs to happen once per conversation (Section 2), so
    this record persists in the agent's working notes for the life of the
    conversation and is re-stated in every model call for reproducibility.
    """

    verified: bool = False
    factors_matched: List[VerificationFactor] = Field(default_factory=list)
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    profile_email: Optional[str] = None

    def summary(self) -> str:
        if not self.verified:
            return "not verified"
        factors = ", ".join(f.value for f in self.factors_matched) or "unknown factors"
        ids = []
        if self.customer_id:
            ids.append(f"customer_id={self.customer_id}")
        if self.user_id:
            ids.append(f"user_id={self.user_id}")
        id_text = f" ({', '.join(ids)})" if ids else ""
        return f"verified via {factors}{id_text}"


class WorkingNotes(BaseModel):
    """Durable per-conversation facts that must survive across turns.

    The agent re-serializes this object into the text of every model call so
    each call carries the operating policy, the conversation so far, and
    these working notes with no reliance on hidden process state. Nothing
    here is a substitute for re-reading the transcript; it exists so the
    agent doesn't have to re-derive verification status, gathered facts, or
    escalation counters from scratch on every turn.
    """

    verification: VerificationRecord = Field(default_factory=VerificationRecord)
    gathered_facts: Dict[str, str] = Field(default_factory=dict)
    pending_confirmation: Optional[str] = None
    human_transfer_request_count: int = 0
    transfer_reason_code: Optional[HumanTransferReasonCode] = None
    transferred: bool = False
    notes: List[str] = Field(default_factory=list)

    def record_fact(self, key: str, value: str) -> None:
        self.gathered_facts[key] = value

    def add_note(self, note: str) -> None:
        if note not in self.notes:
            self.notes.append(note)

    def render(self) -> str:
        """Render these notes as plain text for inclusion in a model call."""
        lines: List[str] = []
        lines.append(f"Identity verification: {self.verification.summary()}")
        if self.gathered_facts:
            fact_lines = ", ".join(
                f"{key}={value}" for key, value in self.gathered_facts.items()
            )
            lines.append(f"Facts gathered this conversation: {fact_lines}")
        if self.pending_confirmation:
            lines.append(
                f"Action awaiting explicit customer confirmation: {self.pending_confirmation}"
            )
        lines.append(
            f"Human-transfer requests so far this conversation: {self.human_transfer_request_count}"
        )
        if self.transferred:
            lines.append("This conversation has already been transferred to a human agent.")
        if self.notes:
            for note in self.notes:
                lines.append(f"Note: {note}")
        return "\n".join(lines)


class KnowledgeBaseDocument(BaseModel):
    """One markdown snippet from the internal knowledge base."""

    id: str
    title: str
    content: str
    category: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
