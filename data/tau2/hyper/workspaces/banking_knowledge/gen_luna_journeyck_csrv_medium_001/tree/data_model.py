from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class BankingModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class Customer(BankingModel):
    customer_id: str
    user_id: Optional[str] = None
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    home_address: Optional[str] = None
    address: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BankAccount(BankingModel):
    account_id: str
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    account_type: Optional[str] = None
    account_class: Optional[str] = None
    product_name: Optional[str] = None
    status: Optional[str] = None
    balance: Optional[Decimal] = None
    available_balance: Optional[Decimal] = None
    current_balance: Optional[Decimal] = None
    current_holdings: Optional[Decimal] = None
    date_opened: Optional[date] = None
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    currency: Optional[str] = None
    routing_number: Optional[str] = None
    account_number: Optional[str] = None
    interest_rate: Optional[Decimal] = None
    apy: Optional[Decimal] = None
    monthly_maintenance_fee: Optional[Decimal] = None
    overdraft_fee: Optional[Decimal] = None
    daily_atm_limit: Optional[Decimal] = None
    daily_mobile_check_deposit_limit: Optional[Decimal] = None
    daily_outbound_transfer_limit: Optional[Decimal] = None
    monthly_withdrawal_limit: Optional[int] = None
    early_closure_fee: Optional[Decimal] = None
    notice_period_days: Optional[int] = None
    manager_approval_required: Optional[bool] = None


class CreditCardAccount(BankingModel):
    account_id: str
    credit_card_account_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    account_class: Optional[str] = None
    product_name: Optional[str] = None
    card_type: Optional[str] = None
    tier: Optional[str] = None
    status: Optional[str] = None
    balance: Optional[Decimal] = None
    outstanding_balance: Optional[Decimal] = None
    available_credit: Optional[Decimal] = None
    credit_limit: Optional[Decimal] = None
    purchase_apr: Optional[Decimal] = None
    annual_fee: Optional[Decimal] = None
    foreign_transaction_fee: Optional[Decimal] = None
    date_opened: Optional[date] = None
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    autopay_status: Optional[str] = None
    rewards_balance: Optional[Decimal] = None
    reward_type: Optional[str] = None


class DebitCard(BankingModel):
    card_id: str
    account_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    card_number: Optional[str] = None
    last_four: Optional[str] = None
    status: Optional[str] = None
    issue_reason: Optional[str] = None
    expiration_date: Optional[str] = None
    daily_atm_limit: Optional[Decimal] = None
    daily_purchase_limit: Optional[Decimal] = None
    pin_status: Optional[str] = None
    fraud_alert_type: Optional[str] = None
    created_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class CreditCard(BankingModel):
    card_id: str
    account_id: Optional[str] = None
    credit_card_account_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    card_number: Optional[str] = None
    last_four: Optional[str] = None
    status: Optional[str] = None
    issue_reason: Optional[str] = None
    expiration_date: Optional[str] = None
    created_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class Transaction(BankingModel):
    transaction_id: str
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    account_id: Optional[str] = None
    credit_card_account_id: Optional[str] = None
    card_id: Optional[str] = None
    merchant_name: Optional[str] = None
    description: Optional[str] = None
    transaction_type: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    transaction_date: Optional[date] = None
    posted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    is_pending: Optional[bool] = None
    is_recurring: Optional[bool] = None


class Dispute(BankingModel):
    dispute_id: str
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    account_id: Optional[str] = None
    credit_card_account_id: Optional[str] = None
    card_id: Optional[str] = None
    transaction_id: Optional[str] = None
    dispute_reason: Optional[str] = None
    reason: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[Decimal] = None
    provisional_credit: Optional[Decimal] = None
    provisional_credit_eligible: Optional[bool] = None
    merchant_contacted: Optional[bool] = None
    filed_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None


class Referral(BankingModel):
    referral_id: str
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    card_id: Optional[str] = None
    product_name: Optional[str] = None
    status: Optional[str] = None
    referral_code: Optional[str] = None
    referral_link: Optional[str] = None
    reward_type: Optional[str] = None
    reward_amount: Optional[Decimal] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class Application(BankingModel):
    application_id: str
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    product_name: Optional[str] = None
    application_type: Optional[str] = None
    status: Optional[str] = None
    decision: Optional[str] = None
    requested_amount: Optional[Decimal] = None
    requested_increase_amount: Optional[Decimal] = None
    reference: Optional[str] = None
    submitted_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None
    denial_reason: Optional[str] = None


class VerificationRecord(BankingModel):
    verification_id: str
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    factors: List[str] = Field(default_factory=list)
    verified: bool = False
    verified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ReplacementOrder(BankingModel):
    order_id: str
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    account_id: Optional[str] = None
    credit_card_account_id: Optional[str] = None
    card_id: Optional[str] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    shipping_method: Optional[str] = None
    shipping_address: Optional[str] = None
    created_at: Optional[datetime] = None
    latest_event_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    notes: Optional[str] = None


class Payment(BankingModel):
    payment_id: str
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    credit_card_account_id: Optional[str] = None
    source_account_id: Optional[str] = None
    amount: Optional[Decimal] = None
    status: Optional[str] = None
    payment_type: Optional[str] = None
    submitted_at: Optional[datetime] = None
    posted_at: Optional[datetime] = None
    reference: Optional[str] = None


class Promotion(BankingModel):
    promotion_id: str
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    product_name: Optional[str] = None
    promotion_type: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[Decimal] = None
    description: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class CreditLimitIncreaseRequest(BankingModel):
    request_id: str
    credit_card_account_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    requested_increase_amount: Optional[Decimal] = None
    status: Optional[str] = None
    decision: Optional[str] = None
    denial_reason: Optional[str] = None
    reference: Optional[str] = None
    submitted_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None


class TimeResponse(BankingModel):
    timestamp: str


class CustomerSearchResult(BankingModel):
    customer_id: str
    user_id: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    home_address: Optional[str] = None


class CustomerAccounts(BankingModel):
    bank_accounts: List[BankAccount] = Field(default_factory=list)
    credit_card_accounts: List[CreditCardAccount] = Field(default_factory=list)


class APIErrorDetail(BankingModel):
    code: Optional[str] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class APIError(BankingModel):
    error: Optional[APIErrorDetail] = None
    code: Optional[str] = None
    message: Optional[str] = None


class TransferResponse(BankingModel):
    transfer_id: str
    status: str


class OperationResult(BankingModel):
    success: bool = False
    status: Optional[str] = None
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    reference: Optional[str] = None


class AccountInventory(BankingModel):
    bank_accounts: List[BankAccount] = Field(default_factory=list)
    credit_card_accounts: List[CreditCardAccount] = Field(default_factory=list)


class DatabaseSnapshot(BankingModel):
    customers: List[Customer] = Field(default_factory=list)
    bank_accounts: List[BankAccount] = Field(default_factory=list)
    credit_card_accounts: List[CreditCardAccount] = Field(default_factory=list)
    debit_cards: List[DebitCard] = Field(default_factory=list)
    credit_cards: List[CreditCard] = Field(default_factory=list)
    transactions: List[Transaction] = Field(default_factory=list)
    disputes: List[Dispute] = Field(default_factory=list)
    referrals: List[Referral] = Field(default_factory=list)
    applications: List[Application] = Field(default_factory=list)
    verification_records: List[VerificationRecord] = Field(default_factory=list)
    replacement_orders: List[ReplacementOrder] = Field(default_factory=list)
    payments: List[Payment] = Field(default_factory=list)
    promotions: List[Promotion] = Field(default_factory=list)
    credit_limit_increase_requests: List[CreditLimitIncreaseRequest] = Field(
        default_factory=list
    )
