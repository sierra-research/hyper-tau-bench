"""Agent tools backed by the client-owned REST API.

This toolkit wraps the small set of operations documented directly in the
base OpenAPI surface and in the knowledge-base procedures that ship with
strong, consistent evidence of their exact HTTP shape (method, path, and
body fields). For the long tail of "knowledge-discovered" operations that
only ever surface once the applicable knowledge-base procedure has been
retrieved, ``call_documented_api_operation`` lets the agent invoke that
documented operation directly, exactly as the SOP describes, without a
bespoke wrapper for every one of the ~700 procedures.
"""

from typing import Any, Dict, List, Optional
from urllib.parse import quote

from tau2.environment.toolkit import ToolType, is_tool
from tau2.hyper.client_api import ClientAPIToolKitBase


class Tools(ClientAPIToolKitBase):
    """Client-API-backed tools for Rho-Bank customer service."""

    # ------------------------------------------------------------------
    # General / time
    # ------------------------------------------------------------------

    @is_tool(ToolType.READ)
    def get_current_time(self) -> dict:
        """Get the current server date/time. Always use this instead of assuming or guessing the current date."""
        response = self.client_api.request("GET", "/v1/time")
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Customer lookup and identity verification
    # ------------------------------------------------------------------

    @is_tool(ToolType.READ)
    def search_customers(
        self,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        name: Optional[str] = None,
        address: Optional[str] = None,
    ) -> list:
        """Find a banking customer profile using exactly one identifier.

        Provide exactly one of ``email``, ``phone``, ``name``, or ``address``.
        Use this to locate a customer's profile when they do not know their
        user ID, before checking the two verification factors against it.
        Do not disclose any account information based on this search alone;
        it only locates a candidate profile.
        """
        provided = {
            key: value
            for key, value in {
                "email": email,
                "phone": phone,
                "name": name,
                "address": address,
            }.items()
            if value
        }
        if len(provided) != 1:
            raise ValueError(
                "Provide exactly one identifier: email, phone, name, or address."
            )
        response = self.client_api.request("POST", "/v1/customers/search", body=provided)
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def get_customer_profile(self, customer_id: str) -> dict:
        """Retrieve a customer's profile record.

        Includes the contact and identity details (date of birth, email,
        phone, home address) needed to check the two verification factors
        against what the customer provides. Do not disclose any of these
        fields to the customer before they are verified; use them only to
        check the match.
        """
        response = self.client_api.request(
            "GET", f"/v1/customers/{quote(customer_id, safe='')}"
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------

    @is_tool(ToolType.READ)
    def get_customer_accounts(self, customer_id: str) -> dict:
        """List all bank accounts and credit-card accounts for a customer.

        Returns bank_accounts and credit_card_accounts, each with account
        id, type, class, status, balance, and date opened. Use this for
        eligibility checks (tenure, balance, account count) before opening
        or closing accounts, and for general account-detail inquiries.
        """
        response = self.client_api.request(
            "GET", f"/v1/customers/{quote(customer_id, safe='')}/accounts"
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def get_checking_account_debit_cards(self, account_id: str) -> dict:
        """List the debit cards linked to a checking account.

        Use this before any debit-card action (closure, activation, freeze,
        limit change) to confirm the current card_id and status.
        """
        response = self.client_api.request(
            "GET", f"/v1/checking-accounts/{quote(account_id, safe='')}/debit-cards"
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Debit cards
    # ------------------------------------------------------------------

    @is_tool(ToolType.WRITE)
    def close_debit_card(
        self,
        card_id: str,
        reason: str,
    ) -> dict:
        """Permanently close a debit card.

        ``reason`` must be one of: "lost", "stolen", "fraud_suspected",
        "damaged", "no_longer_needed", "account_closing". Closure is
        immediate and irreversible; confirm with the customer before
        calling this. Pending transactions still process, and refunds to a
        closed card are credited to the linked checking account.
        """
        allowed_reasons = {
            "lost",
            "stolen",
            "fraud_suspected",
            "damaged",
            "no_longer_needed",
            "account_closing",
        }
        if reason not in allowed_reasons:
            raise ValueError(f"reason must be one of {sorted(allowed_reasons)}")
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/closure",
            body={"card_id": card_id, "reason": reason},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def activate_debit_card(self, card_id: str, pin: Optional[str] = None) -> dict:
        """Activate a new or reissued debit card.

        Provide ``pin`` (a 4-digit PIN) only when the applicable procedure
        requires selecting one as part of activation (e.g. a reissued
        card). Confirm activation with the customer before calling this.
        """
        body: Dict[str, Any] = {"card_id": card_id}
        if pin is not None:
            body["pin"] = pin
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/activation",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def request_debit_card_temporary_limit_increase(
        self,
        card_id: str,
        limit_type: str,
        new_limit: float,
    ) -> dict:
        """Request a temporary debit-card limit increase.

        ``limit_type`` must be "atm" or "purchase". The temporary increase
        lasts 24 hours and automatically reverts; only one is allowed per
        24-hour period per card, and it cannot exceed the card's documented
        maximum boost. Confirm the exact amount with the customer before
        calling this.
        """
        if limit_type not in ("atm", "purchase"):
            raise ValueError("limit_type must be 'atm' or 'purchase'")
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/temporary-limit-increases",
            body={"card_id": card_id, "limit_type": limit_type, "new_limit": new_limit},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def clear_debit_card_fraud_alert(self, card_id: str, reason: str) -> dict:
        """Clear a debit-card fraud alert or velocity block.

        ``reason`` must be "customer_verified" (customer-initiated fraud
        alert cleared after identity verification and a reasonable
        explanation) or "velocity_clear" (automatic velocity block cleared
        early). This operation cannot clear a bank-initiated fraud alert;
        those require a transfer to the security team.
        """
        if reason not in ("customer_verified", "velocity_clear"):
            raise ValueError("reason must be 'customer_verified' or 'velocity_clear'")
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/fraud-alert-clearances",
            body={"card_id": card_id, "reason": reason},
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Credit cards
    # ------------------------------------------------------------------

    @is_tool(ToolType.READ)
    def get_credit_card_pending_replacement_orders(self, account_id: str) -> dict:
        """List pending replacement-card orders for a credit-card account.

        Always check this immediately before closing a credit-card account:
        an account with a pending replacement order (status pending or
        shipped) cannot be closed until the replacement is delivered or the
        order is cancelled.
        """
        response = self.client_api.request(
            "GET",
            f"/v1/credit-card-accounts/{quote(account_id, safe='')}/pending-replacement-orders",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def submit_credit_limit_increase_request(
        self,
        account_id: str,
        user_id: str,
        requested_increase_amount: float,
    ) -> dict:
        """Submit a credit-limit increase request for review.

        This creates a formal record before eligibility checks run. Follow
        with eligibility review (basic standing, payment history) and then
        call ``approve_credit_limit_increase`` or
        ``deny_credit_limit_increase`` to record the decision. Never tell
        the customer the request is approved before the approval call
        succeeds.
        """
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(account_id, safe='')}/credit-limit-increase-requests",
            body={
                "credit_card_account_id": account_id,
                "user_id": user_id,
                "requested_increase_amount": requested_increase_amount,
            },
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def approve_credit_limit_increase(
        self,
        account_id: str,
        user_id: str,
        approved_amount: float,
    ) -> dict:
        """Record approval of a submitted credit-limit increase request.

        Only call this after all eligibility requirements are confirmed
        met. Do not tell the customer the request is approved until this
        call succeeds.
        """
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(account_id, safe='')}/credit-limit-increase-approvals",
            body={
                "credit_card_account_id": account_id,
                "user_id": user_id,
                "approved_amount": approved_amount,
            },
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def deny_credit_limit_increase(
        self,
        account_id: str,
        user_id: str,
        denial_reason: str,
    ) -> dict:
        """Record denial of a submitted credit-limit increase request.

        ``denial_reason`` must be exactly one of: "insufficient_account_age",
        "cooldown_period_active", "pending_disputes",
        "pending_replacement_card", "past_due_balance", "high_utilization",
        "insufficient_payment_history", "requested_amount_exceeds_limit",
        or "other".
        """
        allowed_reasons = {
            "insufficient_account_age",
            "cooldown_period_active",
            "pending_disputes",
            "pending_replacement_card",
            "past_due_balance",
            "high_utilization",
            "insufficient_payment_history",
            "requested_amount_exceeds_limit",
            "other",
        }
        if denial_reason not in allowed_reasons:
            raise ValueError(f"denial_reason must be one of {sorted(allowed_reasons)}")
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(account_id, safe='')}/credit-limit-increase-denials",
            body={
                "credit_card_account_id": account_id,
                "user_id": user_id,
                "denial_reason": denial_reason,
            },
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.WRITE)
    def pay_credit_card_from_checking(
        self,
        credit_card_account_id: str,
        checking_account_id: str,
        user_id: str,
        amount: float,
    ) -> dict:
        """Pay a credit-card balance from a Rho-Bank checking account.

        Before calling this, confirm the checking account has sufficient
        funds and the amount does not exceed the credit card's outstanding
        balance, and get explicit customer authorization for the exact
        amount.
        """
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/payments",
            body={
                "credit_card_account_id": credit_card_account_id,
                "from_account_id": checking_account_id,
                "user_id": user_id,
                "amount": amount,
            },
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Disputes
    # ------------------------------------------------------------------

    @is_tool(ToolType.READ)
    def get_customer_credit_card_disputes(self, customer_id: str) -> dict:
        """List all credit-card disputes on file for a customer.

        Use this when checking dispute history, verifying the count of
        disputes filed in the past 12 months, or confirming whether an
        open dispute exists (for example, before a credit-limit-increase
        eligibility check).
        """
        response = self.client_api.request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/credit-card-disputes",
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Customer self-service actions (app-side actions the customer performs)
    # ------------------------------------------------------------------

    @is_tool(ToolType.WRITE)
    def create_customer_self_service_action(
        self,
        action_type: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """Register a self-service action the customer completes in their own app.

        Only call this for an ``action_type`` that the applicable retrieved
        procedure actually documents as a customer self-service action
        (for example, mobile check deposit). Never perform the action on
        the customer's behalf; explain how to use it in the app afterward.
        """
        body: Dict[str, Any] = {"action_type": action_type}
        if details:
            body["details"] = details
        response = self.client_api.request(
            "POST", "/v1/customer-self-service-actions", body=body
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Human transfer
    # ------------------------------------------------------------------

    @is_tool(ToolType.GENERIC)
    def transfer_to_human_agent(self, summary: str) -> dict:
        """Transfer the active conversation to a human agent.

        Only call this after confirming a human transfer is warranted per
        policy (explicit customer request after being offered help,
        out-of-scope request, or a procedure that directs a transfer). Tell
        the customer "YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE
        HOLD ON." A successful transfer cannot be retried and ends further
        Client operations for this conversation.
        """
        conversation_id = quote(self.client_api.context.conversation_id, safe="")
        response = self.client_api.request(
            "POST",
            f"/v1/conversations/{conversation_id}/transfers",
            body={"summary": summary},
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Generic pass-through for knowledge-discovered operations
    # ------------------------------------------------------------------

    @is_tool(ToolType.GENERIC)
    def call_documented_api_operation(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        query: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """Call a REST operation documented by a retrieved knowledge-base procedure.

        Use this only for operations not already covered by one of the
        dedicated tools above, and only with the exact HTTP method, path,
        and request fields the applicable procedure documents. Resource
        identifiers embedded in ``path`` must already be URL-encoded (for
        example, a leading "#" as "%23"). Never invent a method, path, or
        field that a procedure does not document, and never use this for
        an operation that has no supporting procedure.
        """
        http_method = method.upper()
        response = self.client_api.request(http_method, path, body=body, query=query)
        response.raise_for_status()
        return response.body
