from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class Customer(StrictModel):
    id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    full_name: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    dob: Optional[date] = None
    home_address: Optional[str] = None
    address: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CustomerSearchResult(StrictModel):
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    full_name: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    dob: Optional[date] = None
    home_address: Optional[str] = None
    address: Optional[str] = None


class VerificationRecord(StrictModel):
    id: Optional[str] = None
    verification_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    factors: Optional[List[str]] = None
    verified_factors: Optional[List[str]] = None
    status: Optional[str] = None
    result: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class Account(StrictModel):
    id: Optional[str] = None
    account_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    account_type: Optional[str] = None
    account_class: Optional[str] = None
    product_name: Optional[str] = None
    status: Optional[str] = None
    balance: Optional[Decimal] = None
    current_balance: Optional[Decimal] = None
    available_balance: Optional[Decimal] = None
    outstanding_balance: Optional[Decimal] = None
    current_holdings: Optional[Decimal] = None
    date_opened: Optional[date] = None
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    routing_number: Optional[str] = None
    account_number: Optional[str] = None


class BankAccountsResponse(StrictModel):
    bank_accounts: List[Account] = Field(default_factory=list)
    credit_card_accounts: List[Account] = Field(default_factory=list)


class Card(StrictModel):
    id: Optional[str] = None
    card_id: Optional[str] = None
    account_id: Optional[str] = None
    credit_card_account_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    card_type: Optional[str] = None
    product: Optional[str] = None
    last_four: Optional[str] = None
    status: Optional[str] = None
    issue_reason: Optional[str] = None
    expiration_date: Optional[str] = None
    linked_checking_account_id: Optional[str] = None
    created_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class Transaction(StrictModel):
    id: Optional[str] = None
    transaction_id: Optional[str] = None
    account_id: Optional[str] = None
    card_id: Optional[str] = None
    credit_card_account_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    merchant_name: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    transaction_type: Optional[str] = None
    status: Optional[str] = None
    transaction_date: Optional[date] = None
    posted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class Application(StrictModel):
    id: Optional[str] = None
    application_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    application_type: Optional[str] = None
    product_name: Optional[str] = None
    status: Optional[str] = None
    decision: Optional[str] = None
    reference: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Dispute(StrictModel):
    id: Optional[str] = None
    dispute_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    account_id: Optional[str] = None
    credit_card_account_id: Optional[str] = None
    card_id: Optional[str] = None
    transaction_id: Optional[str] = None
    reason: Optional[str] = None
    dispute_reason: Optional[str] = None
    amount: Optional[Decimal] = None
    status: Optional[str] = None
    provisional_credit: Optional[Decimal] = None
    provisional_credit_eligible: Optional[bool] = None
    merchant_contacted: Optional[bool] = None
    purchase_date: Optional[date] = None
    filed_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Referral(StrictModel):
    id: Optional[str] = None
    referral_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    product_name: Optional[str] = None
    status: Optional[str] = None
    referral_code: Optional[str] = None
    referral_link: Optional[str] = None
    referred_email: Optional[str] = None
    reward_type: Optional[str] = None
    reward_amount: Optional[Decimal] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ReplacementOrder(StrictModel):
    id: Optional[str] = None
    order_id: Optional[str] = None
    card_id: Optional[str] = None
    credit_card_account_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    reason: Optional[str] = None
    shipping_method: Optional[str] = None
    shipping_address: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    latest_event_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    notes: Optional[str] = None


class Payment(StrictModel):
    id: Optional[str] = None
    payment_id: Optional[str] = None
    payment_history_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    checking_account_id: Optional[str] = None
    credit_card_account_id: Optional[str] = None
    amount: Optional[Decimal] = None
    status: Optional[str] = None
    payment_type: Optional[str] = None
    scheduled_date: Optional[date] = None
    processed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class CreditLimitIncreaseRequest(StrictModel):
    id: Optional[str] = None
    request_id: Optional[str] = None
    reference: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    credit_card_account_id: Optional[str] = None
    requested_increase_amount: Optional[Decimal] = None
    status: Optional[str] = None
    decision: Optional[str] = None
    denial_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Transfer(StrictModel):
    id: Optional[str] = None
    transfer_id: Optional[str] = None
    conversation_id: Optional[str] = None
    status: Optional[str] = None
    reason_code: Optional[str] = None
    summary: Optional[str] = None
    created_at: Optional[datetime] = None


class TimeResponse(StrictModel):
    timestamp: str


class APIError(StrictModel):
    code: Optional[str] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class APIErrorResponse(StrictModel):
    error: Optional[APIError] = None


class AccountListResponse(StrictModel):
    bank_accounts: List[Account] = Field(default_factory=list)
    credit_card_accounts: List[Account] = Field(default_factory=list)


class CardListResponse(StrictModel):
    cards: List[Card] = Field(default_factory=list)


class TransactionListResponse(StrictModel):
    transactions: List[Transaction] = Field(default_factory=list)


class DisputeListResponse(StrictModel):
    disputes: List[Dispute] = Field(default_factory=list)


class ReferralListResponse(StrictModel):
    referrals: List[Referral] = Field(default_factory=list)


class ReplacementOrderListResponse(StrictModel):
    orders: List[ReplacementOrder] = Field(default_factory=list)


class ApplicationListResponse(StrictModel):
    applications: List[Application] = Field(default_factory=list)


class PaymentListResponse(StrictModel):
    payments: List[Payment] = Field(default_factory=list)
