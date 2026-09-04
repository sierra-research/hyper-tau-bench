"""
Typed helper models for Client API resources used by tools.py.

This domain's persistent state lives entirely behind the Client REST API
(see client_api/openapi.yaml); there is no local database file shipped
with this kit. These models exist purely to give tools.py a small amount
of structure and validation around the JSON payloads it sends and
receives, without pretending to fully re-specify the wire schema. Fields
that are not confirmed by the documented contracts are treated
permissively (extra="allow") so an unexpected or additional field from
the backend never breaks a tool call.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class LenientModel(BaseModel):
    """Base class that tolerates additional fields from the backend."""

    model_config = ConfigDict(extra="allow")


class TimeResponse(LenientModel):
    timestamp: str


class BankAccount(LenientModel):
    account_id: str
    account_type: str
    account_class: Optional[str] = None
    status: Optional[str] = None
    balance: Optional[float] = None
    date_opened: Optional[str] = None


class CreditCardAccountSummary(LenientModel):
    account_id: Optional[str] = None
    status: Optional[str] = None


class AccountsResponse(LenientModel):
    bank_accounts: List[dict] = []
    credit_card_accounts: List[dict] = []


class TransferResult(LenientModel):
    transfer_id: str
    status: str


class ReplacementOrder(LenientModel):
    order_id: str
    status: str
    created_at: Optional[str] = None
    latest_event_at: Optional[str] = None
    notes: Optional[str] = None


class PendingReplacementOrdersResponse(LenientModel):
    orders: List[dict] = []


class APIErrorDetail(LenientModel):
    code: Optional[str] = None
    message: Optional[str] = None


class APIError(LenientModel):
    error: Optional[APIErrorDetail] = None
