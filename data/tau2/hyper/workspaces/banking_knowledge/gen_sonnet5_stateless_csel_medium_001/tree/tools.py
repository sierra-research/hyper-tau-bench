"""Agent tools backed by the Rho-Bank client REST API.

Each ``@is_tool`` method wraps one or more calls to ``self.client_api``.
Paths and payload shapes follow the operations documented in the client
API contract and the procedures surfaced through knowledge-base research
(see sop.md, Section 4: "Knowledge-discovered API operations" — once a
procedure documents a method, path, request fields, response shape, and
errors, we call it directly rather than inventing a wrapper).

Identity verification itself is not a Client resource: the handbook asks
us to confirm two of {date of birth, email, phone, home address} against
whatever the customer profile lookup returns, then keep a note of that for
the rest of the conversation. That bookkeeping is implemented as ordinary
in-memory toolkit session state (allowed per the client API contract) with
no backing REST call, since verification success is a local judgment the
agent makes from data it has already read, not a fact the bank's backend
tracks through this API surface.
"""

from typing import List, Optional
from urllib.parse import quote

from tau2.environment.toolkit import ToolType, is_tool
from tau2.hyper.client_api import ClientAPIToolKitBase

from data_model import (
    CheckingAccountDebitCardsResponse,
    CreditCardDisputesResponse,
    CustomerAccountsResponse,
    CustomerSearchResult,
    PendingReplacementOrdersResponse,
    TimeResponse,
)


def _body(**kwargs) -> dict:
    """Build a JSON body dict, dropping any keys whose value is None."""
    return {key: value for key, value in kwargs.items() if value is not None}


class Tools(ClientAPIToolKitBase):
    """Client-API-backed tools for Rho-Bank customer service."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Local-only bookkeeping: customer IDs verified so far this
        # conversation, and which factors were used. Not a Client resource.
        self._verified_customer_ids: set = set()
        self._verification_log: List[dict] = []

    # ------------------------------------------------------------------
    # General
    # ------------------------------------------------------------------

    @is_tool(ToolType.READ)
    def get_current_time(self) -> dict:
        """Get the current server date/time. Always use this instead of guessing."""
        response = self.client_api.request("GET", "/v1/time")
        response.raise_for_status()
        return TimeResponse.model_validate(response.body).model_dump()

    @is_tool(ToolType.READ)
    def search_customers(
        self,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        name: Optional[str] = None,
    ) -> List[dict]:
        """Find candidate customer profiles by one identifying detail.

        Provide exactly one of email, phone, address, or name. Use the
        returned profile(s) to compare the customer's stated verification
        factors (date of birth, email, phone, home address) against what
        is on file, and to obtain the customer_id needed for other tools.
        If this returns multiple candidates or none, ask the customer for
        another identifying detail rather than guessing.
        """
        body = _body(email=email, phone=phone, address=address, name=name)
        response = self.client_api.request("POST", "/v1/customers/search", body=body)
        response.raise_for_status()
        results = response.body if isinstance(response.body, list) else []
        return [CustomerSearchResult.model_validate(item).model_dump() for item in results]

    @is_tool(ToolType.READ)
    def get_customer_accounts(self, customer_id: str) -> dict:
        """List all bank accounts (checking/savings, personal/business) and credit-card accounts for a customer."""
        response = self.client_api.request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/accounts",
        )
        response.raise_for_status()
        return CustomerAccountsResponse.model_validate(response.body).model_dump()

    @is_tool(ToolType.READ)
    def get_bank_account_transactions(self, account_id: str) -> dict:
        """List recent transactions on a checking or savings account (for statement queries and closure/dispute checks)."""
        response = self.client_api.request(
            "GET",
            f"/v1/bank-accounts/{quote(account_id, safe='')}/transactions",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def get_credit_card_transactions(self, credit_card_account_id: str) -> dict:
        """List recent transactions posted to a credit-card account (for dispute or rewards lookups)."""
        response = self.client_api.request(
            "GET",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/transactions",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.GENERIC)
    def transfer_to_human_agents(self, summary: str) -> dict:
        """Transfer the active conversation to a human agent. Only call this after telling the customer they are being transferred."""
        conversation_id = quote(self.client_api.context.conversation_id, safe="")
        response = self.client_api.request(
            "POST",
            f"/v1/conversations/{conversation_id}/transfers",
            body={"summary": summary},
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Identity verification (local session bookkeeping, no REST call)
    # ------------------------------------------------------------------

    @is_tool(ToolType.WRITE)
    def record_identity_verification(self, customer_id: str, verified_factors: List[str]) -> dict:
        """Record that a customer's identity has been verified for this conversation.

        Call this only after confirming that at least two of the customer's
        stated factors (date_of_birth, email, phone, address) match the
        profile returned by search_customers. verified_factors should list
        which of those factor names were confirmed. Do not disclose or act
        on account-specific information before calling this.
        """
        if len(set(verified_factors)) < 2:
            raise ValueError(
                "At least two distinct matching factors are required to verify identity."
            )
        self._verified_customer_ids.add(customer_id)
        record = {
            "customer_id": customer_id,
            "verified": True,
            "factors_used": sorted(set(verified_factors)),
        }
        self._verification_log.append(record)
        return record

    @is_tool(ToolType.READ)
    def get_identity_verification_status(self, customer_id: str) -> dict:
        """Check whether a customer_id has already been verified earlier in this conversation."""
        return {
            "customer_id": customer_id,
            "verified": customer_id in self._verified_customer_ids,
        }

    # ------------------------------------------------------------------
    # Personal & business bank accounts: opening, closing, transfers
    # ------------------------------------------------------------------

    @is_tool(ToolType.WRITE)
    def open_checking_account(
        self,
        customer_id: str,
        product_class: str,
        initial_deposit_source_account_id: Optional[str] = None,
        initial_deposit_amount: Optional[float] = None,
    ) -> dict:
        """Open a new checking account (personal or business) for a verified, eligible customer.

        product_class is the exact product name (e.g. "Green Account",
        "Business Checking Account"). Only call this after confirming the
        customer is verified and meets the product's documented eligibility
        requirements, and after the customer has confirmed they want to
        proceed.
        """
        body = _body(
            product_class=product_class,
            initial_deposit_source_account_id=initial_deposit_source_account_id,
            initial_deposit_amount=initial_deposit_amount,
        )
        response = self.client_api.request(
            "POST",
            f"/v1/customers/{quote(customer_id, safe='')}/checking-accounts",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def open_savings_account(
        self,
        customer_id: str,
        product_class: str,
        initial_deposit_source_account_id: Optional[str] = None,
        initial_deposit_amount: Optional[float] = None,
    ) -> dict:
        """Open a new savings account (personal or business) for a verified, eligible customer.

        product_class is the exact product name (e.g. "Silver Account",
        "Emerald Saver Account"). Only call this after confirming the
        customer is verified and meets the product's documented eligibility
        requirements, and after the customer has confirmed they want to
        proceed.
        """
        body = _body(
            product_class=product_class,
            initial_deposit_source_account_id=initial_deposit_source_account_id,
            initial_deposit_amount=initial_deposit_amount,
        )
        response = self.client_api.request(
            "POST",
            f"/v1/customers/{quote(customer_id, safe='')}/savings-accounts",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def close_checking_account(self, account_id: str, reason: str) -> dict:
        """Close a checking account after confirming pre-closure requirements (no pending transactions, debit cards handled) and customer confirmation."""
        response = self.client_api.request(
            "POST",
            f"/v1/checking-accounts/{quote(account_id, safe='')}/closure",
            body={"reason": reason},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def close_savings_account(self, account_id: str, reason: str) -> dict:
        """Close a savings account after confirming pre-closure requirements (notice period, early-closure fee if applicable) and customer confirmation."""
        response = self.client_api.request(
            "POST",
            f"/v1/savings-accounts/{quote(account_id, safe='')}/closure",
            body={"reason": reason},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def transfer_between_bank_accounts(
        self, source_account_id: str, destination_account_id: str, amount: float
    ) -> dict:
        """Transfer funds between two of the customer's own bank accounts after explicit confirmation."""
        response = self.client_api.request(
            "POST",
            f"/v1/bank-accounts/{quote(source_account_id, safe='')}/transfers",
            body={"destination_account_id": destination_account_id, "amount": amount},
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Debit cards
    # ------------------------------------------------------------------

    @is_tool(ToolType.READ)
    def get_debit_cards(self, account_id: str) -> dict:
        """List debit cards linked to a checking account, including card_id, status, and issue_reason."""
        response = self.client_api.request(
            "GET",
            f"/v1/checking-accounts/{quote(account_id, safe='')}/debit-cards",
        )
        response.raise_for_status()
        return CheckingAccountDebitCardsResponse.model_validate(response.body).model_dump()

    @is_tool(ToolType.WRITE)
    def activate_debit_card(self, card_id: str) -> dict:
        """Activate a debit card (new issue or reissued for expired/damaged/upgrade/bank_reissue), after confirming card details and PIN selection with the customer."""
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/activation",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def freeze_debit_card(self, card_id: str) -> dict:
        """Freeze a debit card. Freezing is temporary and reversible, unlike closure."""
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/freeze",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def unfreeze_debit_card(self, card_id: str) -> dict:
        """Remove a freeze from a debit card."""
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/unfreeze",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def close_debit_card(self, card_id: str, reason: str) -> dict:
        """Permanently close a debit card. Use for lost, stolen, fraud_suspected, damaged (with replacement wanted), no_longer_needed, or account_closing. Closure is permanent and cannot be reversed."""
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/closure",
            body={"card_id": card_id, "reason": reason},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def change_debit_card_pin(self, card_id: str, new_pin: str) -> dict:
        """Set a new PIN for a debit card. new_pin must be a 4-digit string; avoid sequential or repeating digits."""
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/pin-changes",
            body={"new_pin": new_pin},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def request_debit_card_temporary_limit_increase(
        self, card_id: str, limit_type: str, new_limit: float
    ) -> dict:
        """Request a temporary debit-card limit increase. limit_type is "atm" or "purchase". Temporary increases last 24 hours and then automatically revert."""
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/temporary-limit-increases",
            body={"card_id": card_id, "limit_type": limit_type, "new_limit": new_limit},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def clear_debit_card_fraud_alert(self, card_id: str, reason: str) -> dict:
        """Clear a customer-service-clearable fraud alert or velocity block on a debit card. reason must be exactly "customer_verified" or "velocity_clear". Bank-initiated fraud alerts cannot be cleared this way and require a security-team transfer."""
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/fraud-alert-clearances",
            body={"card_id": card_id, "reason": reason},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def get_debit_card_pending_replacement_orders(self, card_id: str) -> dict:
        """List pending replacement orders for a debit card, to check whether a new order or closure can proceed."""
        response = self.client_api.request(
            "GET",
            f"/v1/debit-cards/{quote(card_id, safe='')}/pending-replacement-orders",
        )
        response.raise_for_status()
        return PendingReplacementOrdersResponse.model_validate(response.body).model_dump()

    @is_tool(ToolType.WRITE)
    def order_debit_card_replacement(
        self,
        card_id: str,
        reason: str,
        shipping_option: str,
        shipping_address: Optional[str] = None,
    ) -> dict:
        """Order a replacement debit card. reason is one of fraud_suspected, lost, stolen, damaged, expired, or other. shipping_option is "standard" or "expedited". shipping_address overrides the address on file when provided."""
        body = _body(reason=reason, shipping_option=shipping_option, shipping_address=shipping_address)
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/replacement-orders",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def cancel_debit_card_replacement_order(self, order_id: str) -> dict:
        """Cancel a pending debit-card replacement order."""
        response = self.client_api.request(
            "POST",
            f"/v1/replacement-orders/{quote(order_id, safe='')}/cancellation",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def block_recurring_transaction_on_debit_card(self, card_id: str, merchant_name: str) -> dict:
        """Block future recurring transactions from a specific merchant on a debit card."""
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/recurring-transaction-blocks",
            body={"merchant_name": merchant_name},
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Credit cards: replacements, payments, limit changes, closure
    # ------------------------------------------------------------------

    @is_tool(ToolType.READ)
    def get_credit_card_pending_replacement_orders(self, credit_card_account_id: str) -> dict:
        """List pending replacement orders for a credit-card account. Always check this before initiating a closure, since accounts with a pending replacement cannot be closed until it is delivered or cancelled."""
        response = self.client_api.request(
            "GET",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/pending-replacement-orders",
        )
        response.raise_for_status()
        return PendingReplacementOrdersResponse.model_validate(response.body).model_dump()

    @is_tool(ToolType.WRITE)
    def order_credit_card_replacement(
        self,
        credit_card_account_id: str,
        reason: str,
        shipping_option: str,
        shipping_address: Optional[str] = None,
    ) -> dict:
        """Order a replacement credit card. reason is one of fraud_suspected, lost, stolen, damaged, expired, or other. shipping_option is "standard" or "expedited". shipping_address overrides the address on file when provided."""
        body = _body(reason=reason, shipping_option=shipping_option, shipping_address=shipping_address)
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/replacement-orders",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def cancel_credit_card_replacement_order(self, order_id: str) -> dict:
        """Cancel a pending credit-card replacement order."""
        response = self.client_api.request(
            "POST",
            f"/v1/replacement-orders/{quote(order_id, safe='')}/cancellation",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def pay_credit_card_from_checking(
        self, credit_card_account_id: str, source_account_id: str, amount: float
    ) -> dict:
        """Pay down a credit-card balance from one of the customer's own Rho-Bank checking accounts, after confirming sufficient funds, the outstanding balance, and explicit customer authorization."""
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/payments",
            body={"source_account_id": source_account_id, "amount": amount},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def request_credit_limit_increase(
        self, credit_card_account_id: str, user_id: str, requested_increase_amount: float
    ) -> dict:
        """Submit a credit-limit increase request. Submitting creates the formal record; eligibility must still be checked and a decision (approval or denial) communicated afterward."""
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/credit-limit-increase-requests",
            body={
                "credit_card_account_id": credit_card_account_id,
                "user_id": user_id,
                "requested_increase_amount": requested_increase_amount,
            },
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def approve_credit_limit_increase(
        self, credit_card_account_id: str, user_id: str, approved_amount: float
    ) -> dict:
        """Record approval of a submitted credit-limit increase request. Only call after every eligibility requirement has been confirmed true."""
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/credit-limit-increase-approvals",
            body={
                "credit_card_account_id": credit_card_account_id,
                "user_id": user_id,
                "approved_amount": approved_amount,
            },
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def deny_credit_limit_increase(
        self, credit_card_account_id: str, user_id: str, denial_reason: str
    ) -> dict:
        """Record denial of a submitted credit-limit increase request. denial_reason must be exactly one of: insufficient_account_age, cooldown_period_active, pending_disputes, pending_replacement_card, past_due_balance, high_utilization, insufficient_payment_history, requested_amount_exceeds_limit, or other."""
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/credit-limit-increase-denials",
            body={
                "credit_card_account_id": credit_card_account_id,
                "user_id": user_id,
                "denial_reason": denial_reason,
            },
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def close_credit_card_account(self, credit_card_account_id: str, reason: str) -> dict:
        """Close a credit-card account after confirming there are no pending replacement orders and the customer has confirmed the closure."""
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/closure",
            body={"reason": reason},
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Disputes and rewards
    # ------------------------------------------------------------------

    @is_tool(ToolType.READ)
    def get_credit_card_disputes(self, customer_id: str) -> dict:
        """List all credit-card disputes for a customer, including status and whether provisional credit was issued. Use this to check active-dispute counts before other actions such as a credit-limit increase."""
        response = self.client_api.request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/credit-card-disputes",
        )
        response.raise_for_status()
        return CreditCardDisputesResponse.model_validate(response.body).model_dump()

    @is_tool(ToolType.WRITE)
    def file_credit_card_dispute(
        self,
        credit_card_account_id: str,
        transaction_id: str,
        reason: str,
        amount: float,
        merchant_contacted: Optional[bool] = None,
    ) -> dict:
        """File a credit-card transaction dispute. reason should describe the dispute type (e.g. unauthorized_fraudulent_charge, duplicate_charge, goods_services_not_received). merchant_contacted records whether the customer already tried to resolve it with the merchant, required for non-fraud reasons."""
        body = _body(
            transaction_id=transaction_id,
            reason=reason,
            amount=amount,
            merchant_contacted=merchant_contacted,
        )
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/disputes",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def get_debit_card_disputes(self, customer_id: str) -> dict:
        """List all debit-card transaction disputes for a customer."""
        response = self.client_api.request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/debit-card-disputes",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def file_debit_card_dispute(
        self,
        checking_account_id: str,
        transaction_id: str,
        reason: str,
        amount: float,
        merchant_contacted: Optional[bool] = None,
    ) -> dict:
        """File a debit-card transaction dispute (Regulation E) against a checking account."""
        body = _body(
            transaction_id=transaction_id,
            reason=reason,
            amount=amount,
            merchant_contacted=merchant_contacted,
        )
        response = self.client_api.request(
            "POST",
            f"/v1/checking-accounts/{quote(checking_account_id, safe='')}/disputes",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def get_cashback_disputes(self, customer_id: str) -> dict:
        """List all cash-back disputes for a customer."""
        response = self.client_api.request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/cashback-disputes",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def file_cashback_dispute(
        self,
        credit_card_account_id: str,
        transaction_id: str,
        reason: str,
        expected_amount: float,
        actual_amount: float,
    ) -> dict:
        """File a dispute over a cash-back or rewards calculation on a specific transaction."""
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/cashback-disputes",
            body={
                "transaction_id": transaction_id,
                "reason": reason,
                "expected_amount": expected_amount,
                "actual_amount": actual_amount,
            },
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def correct_resolved_dispute(self, dispute_id: str, correction_reason: str) -> dict:
        """Request a correction to a dispute that was already resolved (e.g. an incorrect outcome discovered later)."""
        response = self.client_api.request(
            "POST",
            f"/v1/disputes/{quote(dispute_id, safe='')}/corrections",
            body={"correction_reason": correction_reason},
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # ATM fee credits, savings bonuses, interest discrepancies
    # ------------------------------------------------------------------

    @is_tool(ToolType.WRITE)
    def request_atm_fee_credit(self, account_id: str, transaction_id: str, reason: str) -> dict:
        """Request a fee credit or rebate for an ATM fee charged to a checking account."""
        response = self.client_api.request(
            "POST",
            f"/v1/checking-accounts/{quote(account_id, safe='')}/atm-fee-credits",
            body={"transaction_id": transaction_id, "reason": reason},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def select_savings_bonus(self, account_id: str, bonus_id: str) -> dict:
        """Select an APY bonus or promotional offer for a savings account, when a procedure requires an explicit customer selection rather than automatic application."""
        response = self.client_api.request(
            "POST",
            f"/v1/savings-accounts/{quote(account_id, safe='')}/bonus-selections",
            body={"bonus_id": bonus_id},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def file_interest_discrepancy_report(
        self,
        account_id: str,
        description: str,
        expected_amount: float,
        actual_amount: float,
    ) -> dict:
        """File a report that the interest credited to a savings account does not match what the customer expected."""
        response = self.client_api.request(
            "POST",
            f"/v1/savings-accounts/{quote(account_id, safe='')}/interest-discrepancy-reports",
            body={
                "description": description,
                "expected_amount": expected_amount,
                "actual_amount": actual_amount,
            },
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Referrals and applications
    # ------------------------------------------------------------------

    @is_tool(ToolType.READ)
    def get_referrals(self, customer_id: str) -> dict:
        """List a customer's referral records and their statuses."""
        response = self.client_api.request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/referrals",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def create_referral(self, customer_id: str, product_type: str, product_name: str) -> dict:
        """Create a referral record and link for a documented referral program. Only call this for a product that has a documented, active referral program; otherwise explain that no referral offer exists."""
        response = self.client_api.request(
            "POST",
            f"/v1/customers/{quote(customer_id, safe='')}/referrals",
            body={"product_type": product_type, "product_name": product_name},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def get_credit_card_applications(self, customer_id: str) -> dict:
        """List a customer's credit-card application records and their statuses."""
        response = self.client_api.request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/credit-card-applications",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def submit_credit_card_application(self, customer_id: str, product_name: str) -> dict:
        """Submit a credit-card application after confirming the customer meets the product's documented eligibility requirements and wants to proceed."""
        response = self.client_api.request(
            "POST",
            f"/v1/customers/{quote(customer_id, safe='')}/credit-card-applications",
            body={"product_name": product_name},
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Customer self-service actions
    # ------------------------------------------------------------------

    @is_tool(ToolType.WRITE)
    def initiate_customer_self_service_action(
        self, action_name: str, parameters: Optional[dict] = None
    ) -> dict:
        """Make a customer-completed action available in the customer's own app (e.g. mobile check deposit) and record that it was offered.

        Only call this for an action a knowledge-base procedure actually
        requires the customer to complete themselves; the agent does not
        perform the action on the customer's behalf.
        """
        body = _body(action_name=action_name, parameters=parameters)
        response = self.client_api.request(
            "POST",
            "/v1/customer-self-service-actions",
            body=body,
        )
        response.raise_for_status()
        return response.body
