"""Agent tools backed by the Rho-Bank client-owned REST API.

Each tool below wraps one or more calls to the Client API described in
client_api/openapi.yaml, the "Agent Discoverable Operation" documented in
knowledge_base/doc_bank_accounts_bank_accounts_(general)_010.json, and the
operation signatures evidenced repeatedly across approved support-case
records for debit cards, credit cards, disputes, and credit-limit reviews.
Field names and enum values are taken directly from those sources; nothing
here invents a field that wasn't named in the underlying procedure.
"""

from urllib.parse import quote
from typing import Any, Dict, Optional

from tau2.environment.toolkit import ToolType, is_tool
from tau2.hyper.client_api import ClientAPIToolKitBase

from data_model import (
    CreditCardDisputeReason,
    CreditCardReplacementReason,
    CreditLimitIncreaseDenialReason,
    DebitCardClosureReason,
    FraudAlertClearanceReason,
    TemporaryLimitType,
)


def _clean(body: Dict[str, Any]) -> Dict[str, Any]:
    """Drop unset optional fields rather than sending JSON null for them."""
    return {key: value for key, value in body.items() if value is not None}


def _enum_value(enum_cls, value: str, field_name: str) -> str:
    """Validate a caller-supplied string against a documented enum before
    it goes over the wire, so a typo fails fast with a clear message
    instead of burning a round trip on a 422."""
    try:
        return enum_cls(value).value
    except ValueError as exc:
        allowed = ", ".join(member.value for member in enum_cls)
        raise ValueError(
            f"Invalid value {value!r} for {field_name}. Allowed values: {allowed}."
        ) from exc


class Tools(ClientAPIToolKitBase):
    """Agent-facing operations for Rho-Bank customer service."""

    # ------------------------------------------------------------------
    # General / identity
    # ------------------------------------------------------------------

    @is_tool(ToolType.READ)
    def get_current_time(self) -> dict:
        """Get the current server date/time. Use this instead of guessing
        or assuming today's date for any time-sensitive procedure."""
        response = self.client_api.request("GET", "/v1/time")
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def search_customers(
        self,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        name: Optional[str] = None,
        address: Optional[str] = None,
    ) -> dict:
        """Locate a customer profile using exactly one identifying detail
        the customer has given (email, phone, name, or home address).

        This only locates candidate profiles for verification purposes; it
        does not disclose account information and does not itself satisfy
        identity verification. Provide exactly one of the arguments.
        """
        provided = [value for value in (email, phone, name, address) if value is not None]
        if len(provided) != 1:
            raise ValueError(
                "search_customers requires exactly one identifying detail "
                "(email, phone, name, or address)."
            )
        body: Dict[str, Any] = _clean(
            {"email": email, "phone": phone, "name": name, "address": address}
        )
        response = self.client_api.request("POST", "/v1/customers/search", body=body)
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def get_customer_accounts(self, customer_id: str) -> dict:
        """List all bank accounts and credit-card accounts for a customer.
        Use this for eligibility checks (existing account counts, tenure,
        balances, status) and for looking up account IDs needed by other
        operations."""
        response = self.client_api.request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/accounts",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.GENERIC)
    def transfer_to_human_agent(self, summary: str) -> dict:
        """Create a live transfer of this conversation to a human agent.
        Only call this after confirming, per the handbook's escalation
        rules, that a human transfer is warranted. This cannot be
        retried automatically and ends the assistant's ability to act on
        this conversation."""
        conversation_id = quote(self.client_api.context.conversation_id, safe="")
        response = self.client_api.request(
            "POST",
            f"/v1/conversations/{conversation_id}/transfers",
            body={"summary": summary},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def enable_customer_self_service_action(
        self, action_type: str, details: Optional[Dict[str, Any]] = None
    ) -> dict:
        """Make a customer self-service action available in the customer's
        own banking app (for example, mobile check deposit). Use this only
        when the applicable procedure requires the customer to complete the
        action themselves in their own app rather than the agent performing
        it directly. Explain the app steps to the customer after calling
        this; the agent never performs the action on the customer's
        behalf."""
        body = _clean({"action_type": action_type, "details": details})
        response = self.client_api.request(
            "POST", "/v1/customer-self-service-actions", body=body
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Bank accounts (personal and business)
    # ------------------------------------------------------------------

    @is_tool(ToolType.WRITE)
    def transfer_between_bank_accounts(
        self, source_account_id: str, destination_account_id: str, amount: float
    ) -> dict:
        """Move funds between two of a customer's own bank accounts
        (checking or savings). Both accounts must be ACTIVE or OPEN and
        the source account must have sufficient available funds. Use this
        to fund a new savings account's opening deposit, to move money
        between a customer's checking and savings at their request, or to
        consolidate balances before closing an account."""
        body = {
            "source_account_id": source_account_id,
            "destination_account_id": destination_account_id,
            "amount": amount,
        }
        response = self.client_api.request(
            "POST", "/v1/bank-account-transfers", body=body
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def open_checking_account(
        self,
        customer_id: str,
        account_class: str,
        initial_deposit: Optional[float] = None,
    ) -> dict:
        """Open a new personal checking account for a verified, eligible
        customer. account_class is the product name (for example, "Blue
        Account", "Green Account", "Purple Account", "Light Blue Account",
        "Light Green Account", "Dark Green Account", "Gold Years Account").
        initial_deposit, if provided, is the USD opening deposit."""
        body = _clean(
            {
                "customer_id": customer_id,
                "account_class": account_class,
                "initial_deposit": initial_deposit,
            }
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
        account_class: str,
        initial_deposit: Optional[float] = None,
    ) -> dict:
        """Open a new personal savings account for a verified, eligible
        customer. account_class is the product name (for example, "Bronze
        Account", "Silver Account", "Silver Plus Account", "Gold Account",
        "Platinum Account", "Diamond Elite Account")."""
        body = _clean(
            {
                "customer_id": customer_id,
                "account_class": account_class,
                "initial_deposit": initial_deposit,
            }
        )
        response = self.client_api.request(
            "POST",
            f"/v1/customers/{quote(customer_id, safe='')}/savings-accounts",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def open_business_checking_account(
        self,
        customer_id: str,
        account_class: str,
        initial_deposit: Optional[float] = None,
    ) -> dict:
        """Open a new business checking account (for example, "Cobalt
        Blue", "True Blue")."""
        body = _clean(
            {
                "customer_id": customer_id,
                "account_class": account_class,
                "initial_deposit": initial_deposit,
            }
        )
        response = self.client_api.request(
            "POST",
            f"/v1/customers/{quote(customer_id, safe='')}/business-checking-accounts",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def open_business_savings_account(
        self,
        customer_id: str,
        account_class: str,
        initial_deposit: Optional[float] = None,
    ) -> dict:
        """Open a new business savings account (for example, "Silver
        Saver Account", "Silver Plus Saver Account", "Emerald Saver
        Account", "Platinum Reserve Account", "Diamond Vault Account")."""
        body = _clean(
            {
                "customer_id": customer_id,
                "account_class": account_class,
                "initial_deposit": initial_deposit,
            }
        )
        response = self.client_api.request(
            "POST",
            f"/v1/customers/{quote(customer_id, safe='')}/business-savings-accounts",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def close_checking_account(
        self, account_id: str, reason: Optional[str] = None
    ) -> dict:
        """Permanently close a checking account. Confirm outstanding
        transactions are settled and linked debit cards are handled per
        procedure before calling this."""
        body = _clean({"reason": reason})
        response = self.client_api.request(
            "POST",
            f"/v1/checking-accounts/{quote(account_id, safe='')}/closure",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def close_savings_account(
        self, account_id: str, reason: Optional[str] = None
    ) -> dict:
        """Permanently close a savings account. Any applicable early
        closure fee is deducted directly from the account balance by the
        backend; there is no alternative payment method for that fee."""
        body = _clean({"reason": reason})
        response = self.client_api.request(
            "POST",
            f"/v1/savings-accounts/{quote(account_id, safe='')}/closure",
            body=body,
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Debit cards
    # ------------------------------------------------------------------

    @is_tool(ToolType.READ)
    def get_checking_account_debit_cards(self, account_id: str) -> dict:
        """List the debit cards linked to a checking account, including
        each card's card_id and current status. Use this before any
        activation, freeze, unfreeze, closure, or limit-increase operation
        to confirm the correct card_id and that it belongs to the
        verified customer."""
        response = self.client_api.request(
            "GET",
            f"/v1/checking-accounts/{quote(account_id, safe='')}/debit-cards",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def activate_debit_card(self, card_id: str, pin: str) -> dict:
        """Activate a new or reissued debit card with the PIN the
        customer selected. For a reissued card, activation starts the
        24-hour grace period after which the old card is deactivated."""
        body = {"pin": pin}
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/activation",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def freeze_debit_card(self, card_id: str) -> dict:
        """Temporarily freeze a debit card. Freezing is reversible; use
        closure instead for a card confirmed lost or stolen."""
        response = self.client_api.request(
            "POST", f"/v1/debit-cards/{quote(card_id, safe='')}/freeze"
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def unfreeze_debit_card(self, card_id: str) -> dict:
        """Remove a temporary freeze from a debit card."""
        response = self.client_api.request(
            "POST", f"/v1/debit-cards/{quote(card_id, safe='')}/unfreeze"
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def close_debit_card(self, card_id: str, reason: str) -> dict:
        """Permanently close a debit card. Lost and stolen cards are
        closed immediately with no cooling-off period. reason must be one
        of: lost, stolen, fraud_suspected, damaged, no_longer_needed,
        account_closing. Closure is permanent and cannot be reversed;
        pending transactions still process, and any refunds routed to the
        closed card are credited to the linked checking account."""
        validated_reason = _enum_value(DebitCardClosureReason, reason, "reason")
        body = {"reason": validated_reason}
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/closure",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def clear_debit_card_fraud_alert(self, card_id: str, reason: str) -> dict:
        """Clear a customer-service-clearable fraud alert or velocity
        block on a debit card. reason must be exactly customer_verified
        (for a customer-initiated hold, after verification and a
        reasonable explanation) or velocity_clear (for an automatic
        velocity block). Bank-initiated fraud alerts cannot be cleared
        through this operation and require security-team review instead;
        expect a business-rule error in that case."""
        validated_reason = _enum_value(
            FraudAlertClearanceReason, reason, "reason"
        )
        body = {"reason": validated_reason}
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/fraud-alert-clearances",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def create_debit_card_temporary_limit_increase(
        self, card_id: str, limit_type: str, new_limit: float
    ) -> dict:
        """Request a temporary debit-card limit increase. limit_type must
        be exactly "atm" or "purchase". Only one temporary increase is
        allowed per 24-hour period per card, the new limit cannot exceed
        150% of the current limit, and the increase automatically reverts
        after 24 hours."""
        validated_limit_type = _enum_value(
            TemporaryLimitType, limit_type, "limit_type"
        )
        body = {"limit_type": validated_limit_type, "new_limit": new_limit}
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/temporary-limit-increases",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def block_debit_card_recurring_transaction(
        self, card_id: str, merchant_name: str
    ) -> dict:
        """Block future recurring transactions from a specific merchant on
        a debit card, for example to stop a subscription the customer no
        longer wants to be charged for."""
        body = {"merchant_name": merchant_name}
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/recurring-transaction-blocks",
            body=body,
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Credit cards
    # ------------------------------------------------------------------

    @is_tool(ToolType.WRITE)
    def activate_credit_card(self, credit_card_account_id: str) -> dict:
        """Activate a new or replacement credit card."""
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/activation",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def pay_credit_card_from_checking(
        self, credit_card_account_id: str, source_account_id: str, amount: float
    ) -> dict:
        """Pay down a credit-card balance using funds from one of the
        customer's own Rho-Bank checking accounts. Confirm the checking
        account has sufficient funds and the amount does not exceed the
        card's outstanding balance before calling this, and get explicit
        customer authorization first."""
        body = {"source_account_id": source_account_id, "amount": amount}
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/payments",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def get_credit_card_disputes(self, customer_id: str) -> dict:
        """Get the consolidated list of credit-card disputes for a
        customer, including current status, across all of their credit
        card accounts."""
        response = self.client_api.request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/credit-card-disputes",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def file_credit_card_dispute(
        self,
        credit_card_account_id: str,
        transaction_id: str,
        reason: str,
        amount: float,
        merchant_contacted: Optional[bool] = None,
    ) -> dict:
        """File a credit-card transaction dispute. reason must be exactly
        one of: unauthorized_fraudulent_charge, duplicate_charge,
        goods_services_not_received, other. merchant_contacted should be
        set for non-fraud reasons, where merchant resolution must
        generally be attempted first. The response reflects whether
        provisional credit was applied while the investigation is
        ongoing, based on account age, dispute amount versus the card
        tier's provisional-credit maximum, and the customer's dispute
        count over the trailing 12 months."""
        validated_reason = _enum_value(CreditCardDisputeReason, reason, "reason")
        body = _clean(
            {
                "transaction_id": transaction_id,
                "reason": validated_reason,
                "amount": amount,
                "merchant_contacted": merchant_contacted,
            }
        )
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/disputes",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def request_credit_limit_increase(
        self,
        credit_card_account_id: str,
        user_id: str,
        requested_increase_amount: float,
    ) -> dict:
        """Submit a credit-limit increase request. This creates a formal
        record before eligibility is checked; call
        approve_credit_limit_increase or deny_credit_limit_increase
        afterward once eligibility (account standing, payment history,
        requested amount) has been reviewed. Do not tell the customer the
        request was approved before the approval call succeeds."""
        body = {
            "credit_card_account_id": credit_card_account_id,
            "user_id": user_id,
            "requested_increase_amount": requested_increase_amount,
        }
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/credit-limit-increase-requests",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def approve_credit_limit_increase(
        self, credit_card_account_id: str, user_id: str, approved_amount: float
    ) -> dict:
        """Approve a previously submitted credit-limit increase request.
        Only call this after confirming every eligibility requirement is
        satisfied."""
        body = {
            "credit_card_account_id": credit_card_account_id,
            "user_id": user_id,
            "approved_amount": approved_amount,
        }
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/credit-limit-increase-approvals",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def deny_credit_limit_increase(
        self, credit_card_account_id: str, user_id: str, denial_reason: str
    ) -> dict:
        """Deny a previously submitted credit-limit increase request.
        denial_reason must be exactly one of: insufficient_account_age,
        cooldown_period_active, pending_disputes, pending_replacement_card,
        past_due_balance, high_utilization, insufficient_payment_history,
        requested_amount_exceeds_limit, other."""
        validated_reason = _enum_value(
            CreditLimitIncreaseDenialReason, denial_reason, "denial_reason"
        )
        body = {
            "credit_card_account_id": credit_card_account_id,
            "user_id": user_id,
            "denial_reason": validated_reason,
        }
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/credit-limit-increase-denials",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def get_pending_credit_card_replacement_orders(
        self, credit_card_account_id: str
    ) -> dict:
        """List pending, shipped, delivered, and cancelled replacement
        orders for a credit-card account. Always check this immediately
        before initiating a credit-card closure, since an account with a
        pending replacement order cannot be closed until that order is
        delivered or cancelled."""
        response = self.client_api.request(
            "GET",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/pending-replacement-orders",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def create_credit_card_replacement_order(
        self,
        credit_card_account_id: str,
        reason: str,
        shipping_method: str,
        shipping_address: Optional[str] = None,
    ) -> dict:
        """Order a replacement credit card. reason must be exactly one of:
        fraud_suspected, lost, stolen, damaged, expired, other.
        shipping_method must be exactly "standard" or "expedited".
        shipping_address, if provided, overrides the address on file for
        this shipment only and must be confirmed with the customer first."""
        validated_reason = _enum_value(
            CreditCardReplacementReason, reason, "reason"
        )
        if shipping_method not in ("standard", "expedited"):
            raise ValueError(
                "shipping_method must be exactly 'standard' or 'expedited'."
            )
        body = _clean(
            {
                "reason": validated_reason,
                "shipping_method": shipping_method,
                "shipping_address": shipping_address,
            }
        )
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/replacement-orders",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def close_credit_card_account(
        self, credit_card_account_id: str, reason: Optional[str] = None
    ) -> dict:
        """Permanently close a credit-card account. Always check
        get_pending_credit_card_replacement_orders first; an account with
        a pending replacement order cannot be closed until it is
        delivered or cancelled."""
        body = _clean({"reason": reason})
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/closure",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def submit_credit_card_application(
        self,
        customer_id: str,
        card_type: str,
        annual_income: Optional[float] = None,
        is_business: Optional[bool] = None,
    ) -> dict:
        """Submit a credit-card application for a customer. card_type is
        the product name (for example, "Bronze Rewards Card", "EcoCard",
        "Platinum Rewards Card", "Business Platinum Rewards Card").
        Confirm the customer meets the product's minimum credit-score
        requirement, if any, before submitting."""
        body = _clean(
            {
                "customer_id": customer_id,
                "card_type": card_type,
                "annual_income": annual_income,
                "is_business": is_business,
            }
        )
        response = self.client_api.request(
            "POST",
            f"/v1/customers/{quote(customer_id, safe='')}/credit-card-applications",
            body=body,
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Referrals
    # ------------------------------------------------------------------

    @is_tool(ToolType.READ)
    def get_referral_status(self, customer_id: str) -> dict:
        """Get a customer's referral history and status, including any
        active referral links and their outcomes."""
        response = self.client_api.request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/referrals",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def create_referral_link(self, customer_id: str, card_type: str) -> dict:
        """Generate a referral link for a customer to share for a specific
        card's referral program. Only call this for a card that has a
        documented, active referral program; participating cards vary in
        bonus amount, eligibility, and reward type."""
        body = {"card_type": card_type}
        response = self.client_api.request(
            "POST",
            f"/v1/customers/{quote(customer_id, safe='')}/referral-links",
            body=body,
        )
        response.raise_for_status()
        return response.body
