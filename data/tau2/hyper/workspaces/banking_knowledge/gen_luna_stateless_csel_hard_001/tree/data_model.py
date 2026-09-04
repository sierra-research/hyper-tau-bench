from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelBase(BaseModel):
    model_config = ConfigDict(extra="allow")


class Customer(ModelBase):
    id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    full_name: Optional[str] = None
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    dob: Optional[date] = None
    home_address: Optional[str] = None
    address: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BankAccount(ModelBase):
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
    current_holdings: Optional[Decimal] = None
    date_opened: Optional[date] = None
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class CreditCardAccount(ModelBase):
    id: Optional[str] = None
    account_id: Optional[str] = None
    credit_card_account_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    account_type: Optional[str] = None
    account_class: Optional[str] = None
    product: Optional[str] = None
    product_name: Optional[str] = None
    tier: Optional[str] = None
    status: Optional[str] = None
    credit_limit: Optional[Decimal] = None
    available_credit: Optional[Decimal] = None
    outstanding_balance: Optional[Decimal] = None
    balance: Optional[Decimal] = None
    annual_fee: Optional[Decimal] = None
    apr: Optional[Decimal] = None
    date_opened: Optional[date] = None
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class DebitCard(ModelBase):
    id: Optional[str] = None
    card_id: Optional[str] = None
    account_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    last_four: Optional[str] = None
    last4: Optional[str] = None
    status: Optional[str] = None
    issue_reason: Optional[str] = None
    card_type: Optional[str] = None
    expiration_date: Optional[str] = None
    daily_atm_limit: Optional[Decimal] = None
    daily_purchase_limit: Optional[Decimal] = None
    created_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class CreditCard(ModelBase):
    id: Optional[str] = None
    card_id: Optional[str] = None
    account_id: Optional[str] = None
    credit_card_account_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    last_four: Optional[str] = None
    last4: Optional[str] = None
    status: Optional[str] = None
    product: Optional[str] = None
    product_name: Optional[str] = None
    expiration_date: Optional[str] = None
    created_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class Transaction(ModelBase):
    id: Optional[str] = None
    transaction_id: Optional[str] = None
    account_id: Optional[str] = None
    credit_card_account_id: Optional[str] = None
    card_id: Optional[str] = None
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


class Application(ModelBase):
    id: Optional[str] = None
    application_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    product: Optional[str] = None
    product_name: Optional[str] = None
    application_type: Optional[str] = None
    status: Optional[str] = None
    decision: Optional[str] = None
    requested_amount: Optional[Decimal] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Dispute(ModelBase):
    id: Optional[str] = None
    dispute_id: Optional[str] = None
    transaction_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    account_id: Optional[str] = None
    credit_card_account_id: Optional[str] = None
    card_id: Optional[str] = None
    dispute_type: Optional[str] = None
    reason: Optional[str] = None
    amount: Optional[Decimal] = None
    status: Optional[str] = None
    provisional_credit: Optional[Decimal] = None
    provisional_credit_status: Optional[str] = None
    merchant_contacted: Optional[bool] = None
    purchase_date: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class Referral(ModelBase):
    id: Optional[str] = None
    referral_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    product: Optional[str] = None
    product_name: Optional[str] = None
    referral_code: Optional[str] = None
    referral_link: Optional[str] = None
    status: Optional[str] = None
    reward_type: Optional[str] = None
    reward_amount: Optional[Decimal] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class VerificationRecord(ModelBase):
    id: Optional[str] = None
    verification_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    factors: Optional[List[str]] = None
    status: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class Payment(ModelBase):
    id: Optional[str] = None
    payment_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    credit_card_account_id: Optional[str] = None
    from_account_id: Optional[str] = None
    amount: Optional[Decimal] = None
    status: Optional[str] = None
    payment_type: Optional[str] = None
    created_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None


class ReplacementOrder(ModelBase):
    id: Optional[str] = None
    order_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    card_id: Optional[str] = None
    credit_card_account_id: Optional[str] = None
    reason: Optional[str] = None
    shipping_method: Optional[str] = None
    shipping_address: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    latest_event_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    notes: Optional[str] = None


class AccountCollection(ModelBase):
    bank_accounts: List[BankAccount] = Field(default_factory=list)
    credit_card_accounts: List[CreditCardAccount] = Field(default_factory=list)


class CustomerSearchResult(ModelBase):
    customer: Optional[Customer] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    email: Optional[str] = None
    match_type: Optional[str] = None
    matches: Optional[List[Customer]] = None


class ApiError(ModelBase):
    code: Optional[str] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ApiResponse(ModelBase):
    status_code: Optional[int] = None
    body: Optional[Any] = None
    headers: Optional[Dict[str, str]] = None
    elapsed_seconds: Optional[float] = None


class TimeResponse(ModelBase):
    timestamp: str


class VerificationHistory(ModelBase):
    records: List[VerificationRecord] = Field(default_factory=list)


class DisputeCollection(ModelBase):
    disputes: List[Dispute] = Field(default_factory=list)


class ReplacementOrderCollection(ModelBase):
    orders: List[ReplacementOrder] = Field(default_factory=list)


class ReferralCollection(ModelBase):
    referrals: List[Referral] = Field(default_factory=list)


class TransactionCollection(ModelBase):
    transactions: List[Transaction] = Field(default_factory=list)
