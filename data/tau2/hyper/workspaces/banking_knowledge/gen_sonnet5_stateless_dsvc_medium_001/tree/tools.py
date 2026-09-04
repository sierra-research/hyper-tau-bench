"""Agent tools backed by the client-owned REST API.

Each tool is a thin wrapper around one documented Client API operation.
Identifiers that appear in URL paths are percent-encoded; JSON bodies only
carry documented fields.
"""

from typing import Literal, Optional
from urllib.parse import quote

from tau2.environment.toolkit import ToolType, is_tool
from tau2.hyper.client_api import ClientAPIToolKitBase


_BANK_ACCOUNT_RESOURCE = {
    "personal_checking": "checking-accounts",
    "personal_savings": "savings-accounts",
    "business_checking": "business-checking-accounts",
    "business_savings": "business-savings-accounts",
}


class Tools(ClientAPIToolKitBase):
    """Client-API-backed tools for Rho-Bank customer service."""

    # ------------------------------------------------------------------
    # General / identity
    # ------------------------------------------------------------------

    @is_tool(ToolType.READ)
    def get_current_time(self) -> dict:
        """Get the current server date/time. Always use this instead of assuming or
        guessing today's date."""
        response = self.client_api.request("GET", "/v1/time")
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def search_customers(
        self,
        identifier_type: Literal["customer_id", "email", "phone", "name", "address"],
        identifier_value: str,
    ) -> dict:
        """Look up a banking customer profile using exactly one identifier (customer
        ID, email address, phone number, name, or home address). Use the returned
        profile fields to complete two-factor identity verification before
        disclosing or modifying any account-specific information."""
        response = self.client_api.request(
            "POST",
            "/v1/customers/search",
            body={identifier_type: identifier_value},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def get_customer_accounts(self, customer_id: str) -> dict:
        """List all bank accounts (checking and savings) and credit-card accounts
        for a verified customer."""
        response = self.client_api.request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/accounts",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.GENERIC)
    def transfer_to_human_agents(self, summary: str) -> dict:
        """Transfer the active conversation to a human agent. Only call this after
        confirming there is no procedure covering the customer's request, or once
        the customer's escalation to a human is warranted under policy."""
        conversation_id = quote(self.client_api.context.conversation_id, safe="")
        response = self.client_api.request(
            "POST",
            f"/v1/conversations/{conversation_id}/transfers",
            body={"summary": summary},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def create_customer_self_service_action(
        self, action_type: str, details: Optional[dict] = None
    ) -> dict:
        """Make a customer self-service action available in the customer's own app
        or device (for example, a mobile check deposit or a virtual-card generation
        flow). Only use this for actions that the applicable procedure says the
        customer must complete themselves; explain to the customer how to use it
        afterward."""
        body: dict = {"action_type": action_type}
        if details is not None:
            body["details"] = details
        response = self.client_api.request(
            "POST", "/v1/customer-self-service-actions", body=body
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Bank accounts (personal and business, checking and savings)
    # ------------------------------------------------------------------

    @is_tool(ToolType.WRITE)
    def open_bank_account(
        self,
        customer_id: str,
        account_category: Literal[
            "personal_checking",
            "personal_savings",
            "business_checking",
            "business_savings",
        ],
        product_class: str,
        initial_deposit_amount: float = 0.0,
    ) -> dict:
        """Open a new checking or savings account, personal or business, for a
        verified customer who has passed the eligibility checks for that product
        category."""
        resource = _BANK_ACCOUNT_RESOURCE[account_category]
        response = self.client_api.request(
            "POST",
            f"/v1/{resource}",
            body={
                "customer_id": customer_id,
                "product_class": product_class,
                "initial_deposit_amount": initial_deposit_amount,
            },
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def close_bank_account(
        self,
        account_id: str,
        account_category: Literal[
            "personal_checking",
            "personal_savings",
            "business_checking",
            "business_savings",
        ],
        reason: str,
    ) -> dict:
        """Close a checking or savings account, personal or business, after
        required pending-transaction and debit-card cleanup checks, and after the
        customer has explicitly confirmed the closure."""
        resource = _BANK_ACCOUNT_RESOURCE[account_category]
        response = self.client_api.request(
            "POST",
            f"/v1/{resource}/{quote(account_id, safe='')}/closure",
            body={"reason": reason},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def get_bank_account_transactions(
        self, account_id: str, account_category: Literal["checking", "savings"]
    ) -> dict:
        """List recent transactions for a checking or savings account. Use this to
        answer statement questions or to locate a transaction before filing a
        dispute."""
        resource = (
            "checking-accounts" if account_category == "checking" else "savings-accounts"
        )
        response = self.client_api.request(
            "GET",
            f"/v1/{resource}/{quote(account_id, safe='')}/transactions",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def file_bank_transaction_dispute(
        self,
        transaction_id: str,
        reason: Literal[
            "unauthorized_transaction",
            "duplicate_charge",
            "goods_services_not_received",
            "atm_dispense_error",
            "other",
        ],
        amount: float,
        description: Optional[str] = None,
    ) -> dict:
        """File a debit-card or bank-account transaction dispute (Regulation E)."""
        body: dict = {"reason": reason, "amount": amount}
        if description is not None:
            body["description"] = description
        response = self.client_api.request(
            "POST",
            f"/v1/bank-transactions/{quote(transaction_id, safe='')}/disputes",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def get_customer_bank_transaction_disputes(self, customer_id: str) -> dict:
        """Get the consolidated history of debit-card and bank-transaction disputes
        for a customer, including their current status."""
        response = self.client_api.request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/bank-transaction-disputes",
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Debit cards
    # ------------------------------------------------------------------

    @is_tool(ToolType.READ)
    def list_checking_account_debit_cards(self, checking_account_id: str) -> dict:
        """List the debit cards issued on a checking account, including each
        card's status."""
        response = self.client_api.request(
            "GET",
            f"/v1/checking-accounts/{quote(checking_account_id, safe='')}/debit-cards",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def activate_debit_card(self, card_id: str) -> dict:
        """Activate a new or reissued debit card."""
        response = self.client_api.request(
            "POST", f"/v1/debit-cards/{quote(card_id, safe='')}/activation", body={}
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def close_debit_card(
        self,
        card_id: str,
        reason: Literal[
            "lost",
            "stolen",
            "fraud_suspected",
            "damaged",
            "no_longer_needed",
            "account_closing",
        ],
    ) -> dict:
        """Permanently close a debit card. Lost, stolen, and fraud-suspected cards
        are closed immediately with no cooling-off period. Closure cannot be
        reversed, so confirm with the customer before calling this."""
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/closure",
            body={"reason": reason},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def freeze_debit_card(self, card_id: str) -> dict:
        """Temporarily freeze a debit card. A freeze is reversible, unlike
        closure."""
        response = self.client_api.request(
            "POST", f"/v1/debit-cards/{quote(card_id, safe='')}/freeze", body={}
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def unfreeze_debit_card(self, card_id: str) -> dict:
        """Remove a temporary freeze from a debit card."""
        response = self.client_api.request(
            "POST", f"/v1/debit-cards/{quote(card_id, safe='')}/unfreeze", body={}
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def change_debit_card_pin(self, card_id: str, new_pin: str) -> dict:
        """Set a new PIN on a debit card. Reject sequential PINs like 1234 and
        repeating PINs like 1111 before calling this."""
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/pin-changes",
            body={"new_pin": new_pin},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def order_debit_card_replacement(
        self,
        card_id: str,
        reason: Literal[
            "lost", "stolen", "fraud_suspected", "damaged", "expired", "no_longer_needed"
        ],
        expedited: bool = False,
    ) -> dict:
        """Order a replacement debit card."""
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/replacement-orders",
            body={"reason": reason, "expedited": expedited},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def block_recurring_transaction(self, card_id: str, merchant_name: str) -> dict:
        """Block future recurring transactions from a specific merchant on a debit
        card."""
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/recurring-transaction-blocks",
            body={"merchant_name": merchant_name},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def clear_debit_card_fraud_alert(
        self, card_id: str, reason: Literal["customer_verified", "velocity_clear"]
    ) -> dict:
        """Clear a customer-verified fraud alert or an automatic velocity block on
        a debit card. Bank-initiated fraud alerts cannot be cleared this way and
        require a security-team transfer instead."""
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/fraud-alert-clearances",
            body={"reason": reason},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def set_debit_card_temporary_limit(
        self, card_id: str, limit_type: Literal["atm", "purchase"], new_limit: float
    ) -> dict:
        """Set a temporary ATM or purchase limit on a debit card. The increase
        lasts 24 hours and then automatically reverts, and only one temporary
        increase is allowed per card in a 24-hour period."""
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/temporary-limit-increases",
            body={"limit_type": limit_type, "new_limit": new_limit},
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Credit cards
    # ------------------------------------------------------------------

    @is_tool(ToolType.READ)
    def get_credit_card_transactions(self, credit_card_account_id: str) -> dict:
        """List recent transactions on a credit-card account. Use this to locate a
        transaction before filing a dispute."""
        response = self.client_api.request(
            "GET",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/transactions",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def activate_credit_card(self, credit_card_account_id: str) -> dict:
        """Activate a new or reissued credit card."""
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/activation",
            body={},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def close_credit_card_account(self, credit_card_account_id: str, reason: str) -> dict:
        """Close a credit-card account. Accounts with a pending replacement-card
        order cannot be closed until the order is delivered or cancelled, so check
        pending replacement orders first."""
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/closure",
            body={"reason": reason},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def change_credit_card_product(
        self, credit_card_account_id: str, new_product_class: str
    ) -> dict:
        """Upgrade or downgrade a credit-card account to a different product while
        keeping the account open."""
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/product-changes",
            body={"new_product_class": new_product_class},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def get_credit_card_pending_replacement_orders(
        self, credit_card_account_id: str
    ) -> dict:
        """List pending, shipped, delivered, or cancelled replacement-card orders
        for a credit-card account. Check this before closing the account or
        starting a new replacement order."""
        response = self.client_api.request(
            "GET",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/pending-replacement-orders",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def order_credit_card_replacement(
        self,
        credit_card_account_id: str,
        reason: Literal[
            "fraud_suspected", "lost", "stolen", "damaged", "expired", "other"
        ],
        expedited: bool = False,
    ) -> dict:
        """Order a replacement credit card. Premium-tier and above products ship
        expedited replacements at no cost."""
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/replacement-orders",
            body={"reason": reason, "expedited": expedited},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def pay_credit_card_from_checking(
        self, credit_card_account_id: str, from_checking_account_id: str, amount: float
    ) -> dict:
        """Make a payment toward a credit-card balance from a Rho-Bank checking
        account. Confirm the checking account has sufficient funds and the amount
        does not exceed the outstanding balance before calling this."""
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/payments",
            body={
                "from_account_id": from_checking_account_id,
                "amount": amount,
            },
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def get_credit_card_payment_history(self, credit_card_account_id: str) -> dict:
        """List the payment history for a credit-card account."""
        response = self.client_api.request(
            "GET",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/payment-history",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def request_credit_limit_increase(
        self, credit_card_account_id: str, user_id: str, requested_increase_amount: float
    ) -> dict:
        """Submit a credit-limit increase request for review. This creates a
        formal record; eligibility must still be checked and the request approved
        or denied afterward."""
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
        """Approve a previously submitted credit-limit increase request. Only call
        this after every eligibility requirement has been verified as met."""
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
        self,
        credit_card_account_id: str,
        user_id: str,
        denial_reason: Literal[
            "insufficient_account_age",
            "cooldown_period_active",
            "pending_disputes",
            "pending_replacement_card",
            "past_due_balance",
            "high_utilization",
            "insufficient_payment_history",
            "requested_amount_exceeds_limit",
            "other",
        ],
    ) -> dict:
        """Deny a previously submitted credit-limit increase request with a
        specific denial reason."""
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
    def file_credit_card_transaction_dispute(
        self,
        transaction_id: str,
        reason: Literal[
            "unauthorized_fraudulent_charge",
            "duplicate_charge",
            "goods_services_not_received",
            "cashback_not_credited",
            "other",
        ],
        amount: float,
        merchant_contacted: Optional[bool] = None,
        description: Optional[str] = None,
    ) -> dict:
        """File a dispute on a credit-card transaction, including cash-back
        disputes. Non-fraud reasons generally require the customer to have
        contacted the merchant first."""
        body: dict = {"reason": reason, "amount": amount}
        if merchant_contacted is not None:
            body["merchant_contacted"] = merchant_contacted
        if description is not None:
            body["description"] = description
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-transactions/{quote(transaction_id, safe='')}/disputes",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def get_customer_credit_card_disputes(self, customer_id: str) -> dict:
        """Get the consolidated history of credit-card disputes for a customer,
        including their current status."""
        response = self.client_api.request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/credit-card-disputes",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def submit_credit_card_application(
        self, customer_id: str, product_class: str, annual_income: Optional[float] = None
    ) -> dict:
        """Submit a new credit-card application for a customer."""
        body: dict = {"customer_id": customer_id, "product_class": product_class}
        if annual_income is not None:
            body["annual_income"] = annual_income
        response = self.client_api.request(
            "POST", "/v1/credit-card-applications", body=body
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def get_customer_credit_card_applications(self, customer_id: str) -> dict:
        """List credit-card applications submitted by a customer along with their
        current status."""
        response = self.client_api.request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/credit-card-applications",
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Referrals
    # ------------------------------------------------------------------

    @is_tool(ToolType.READ)
    def get_customer_referrals(self, customer_id: str) -> dict:
        """List referral records and their status for a customer."""
        response = self.client_api.request(
            "GET", f"/v1/customers/{quote(customer_id, safe='')}/referrals"
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def create_referral_link(self, customer_id: str, product_class: str) -> dict:
        """Generate a referral link for a customer to share for a specific,
        participating product. Only call this for products with a documented,
        active referral program."""
        response = self.client_api.request(
            "POST",
            f"/v1/customers/{quote(customer_id, safe='')}/referrals",
            body={"product_class": product_class},
        )
        response.raise_for_status()
        return response.body
