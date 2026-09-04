"""
Agent tools backed by the client-owned REST API.

Each @is_tool method below implements exactly one operation whose HTTP
method, path, request fields, and response shape are documented in the
kit materials (client_api/openapi.yaml, the SOP's referenced API
contracts, and the knowledge-base procedures). Only documented fields are
sent; unrecognized or missing fields are treated as errors rather than
being guessed at the call site.
"""

from typing import Optional
from urllib.parse import quote

from tau2.environment.toolkit import ToolType, is_tool
from tau2.hyper.client_api import ClientAPIToolKitBase


class Tools(ClientAPIToolKitBase):
    """Client-API-backed tools for the Rho-Bank support agent."""

    # ------------------------------------------------------------------
    # General / time
    # ------------------------------------------------------------------

    @is_tool(ToolType.READ)
    def get_current_time(self) -> dict:
        """Get the current server date/time. Use this instead of guessing."""
        response = self.client_api.request("GET", "/v1/time")
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Customer lookup / verification support
    # ------------------------------------------------------------------

    @is_tool(ToolType.READ)
    def search_customer_profile(
        self,
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        date_of_birth: Optional[str] = None,
        home_address: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> list:
        """Locate a customer profile using exactly one identifying detail.

        Provide exactly one of email, phone_number, date_of_birth,
        home_address, or full_name. Use the returned profile only to
        check the two required verification factors; do not disclose any
        account information until verification succeeds.
        """
        identifiers = {
            "email": email,
            "phone_number": phone_number,
            "date_of_birth": date_of_birth,
            "home_address": home_address,
            "full_name": full_name,
        }
        provided = {key: value for key, value in identifiers.items() if value}
        if len(provided) != 1:
            raise ValueError(
                "search_customer_profile requires exactly one identifying "
                "detail (email, phone_number, date_of_birth, home_address, "
                "or full_name)."
            )
        response = self.client_api.request(
            "POST",
            "/v1/customers/search",
            body=provided,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def get_customer_accounts(self, customer_id: str) -> dict:
        """List a customer's bank accounts and credit-card accounts.

        Use this for opening-eligibility checks (existing account status,
        balances, tenure, and counts), pre-closure checks, and general
        account lookups.
        """
        response = self.client_api.request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/accounts",
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Bank account transfers
    # ------------------------------------------------------------------

    @is_tool(ToolType.GENERIC)
    def transfer_between_bank_accounts(
        self,
        source_account_id: str,
        destination_account_id: str,
        amount: float,
    ) -> dict:
        """Move funds between two of a customer's own bank accounts.

        Both accounts must be ACTIVE or OPEN, must belong to the same
        customer, and the source account must have sufficient available
        funds. Use this to fund a new savings account's opening deposit,
        move money between checking and savings at the customer's
        request, or consolidate balances before closing an account.
        """
        response = self.client_api.request(
            "POST",
            "/v1/bank-account-transfers",
            body={
                "source_account_id": source_account_id,
                "destination_account_id": destination_account_id,
                "amount": amount,
            },
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Debit cards
    # ------------------------------------------------------------------

    @is_tool(ToolType.READ)
    def get_debit_cards_for_account(self, account_id: str) -> dict:
        """List the debit cards linked to a checking account.

        Use this before closing, activating, or otherwise acting on a
        debit card to confirm the correct card_id and its current status.
        """
        response = self.client_api.request(
            "GET",
            f"/v1/checking-accounts/{quote(account_id, safe='')}/debit-cards",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.GENERIC)
    def close_debit_card(self, card_id: str, reason: str) -> dict:
        """Permanently close a debit card.

        reason must be exactly one of: lost, stolen, fraud_suspected,
        damaged, no_longer_needed, account_closing. Lost, stolen, and
        fraud_suspected closures happen immediately with no cooling-off
        period. Closure is permanent and cannot be reversed; confirm with
        the customer before calling this.
        """
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/closure",
            body={"reason": reason},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.GENERIC)
    def activate_debit_card(self, card_id: str, pin: Optional[str] = None) -> dict:
        """Activate a new or reissued debit card.

        Provide a 4-digit pin if the customer has chosen one as part of
        activation; omit it if the card does not require a PIN at this
        step.
        """
        body = {}
        if pin is not None:
            body["pin"] = pin
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/activation",
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.GENERIC)
    def increase_debit_card_temporary_limit(
        self,
        card_id: str,
        limit_type: str,
        new_limit: float,
    ) -> dict:
        """Request a temporary debit-card limit increase.

        limit_type must be exactly "atm" or "purchase". The increase is
        temporary and automatically reverts after 24 hours; only one
        temporary increase is allowed per card in a 24-hour period.
        """
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/temporary-limit-increases",
            body={"limit_type": limit_type, "new_limit": new_limit},
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.GENERIC)
    def clear_debit_card_fraud_alert(self, card_id: str, reason: str) -> dict:
        """Clear a customer-service-clearable debit-card fraud alert.

        reason must be exactly "customer_verified" or "velocity_clear".
        Bank-initiated fraud alerts cannot be cleared this way and
        require a transfer to the security team instead.
        """
        response = self.client_api.request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/fraud-alert-clearances",
            body={"reason": reason},
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Credit cards: disputes, limit increases, replacement orders
    # ------------------------------------------------------------------

    @is_tool(ToolType.READ)
    def get_credit_card_disputes(self, customer_id: str) -> dict:
        """List a customer's credit-card disputes across all cards.

        Use this to check dispute history and current status before
        deciding eligibility for actions such as a credit-limit increase.
        """
        response = self.client_api.request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/credit-card-disputes",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def get_pending_credit_card_replacement_orders(
        self,
        credit_card_account_id: str,
    ) -> dict:
        """List pending replacement-card orders for a credit-card account.

        Always check this immediately before initiating a credit-card
        account closure: an account with a pending replacement order
        cannot be closed until the replacement is delivered or cancelled.
        """
        response = self.client_api.request(
            "GET",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}"
            "/pending-replacement-orders",
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.GENERIC)
    def submit_credit_limit_increase_request(
        self,
        credit_card_account_id: str,
        user_id: str,
        requested_increase_amount: float,
    ) -> dict:
        """File a formal credit-limit increase request for review.

        This creates the review record; eligibility (account standing,
        payment history, past-due balance, disputes, etc.) is checked
        afterward and the outcome is communicated once a decision is
        reached. Do not tell the customer the increase is approved before
        an approval action actually succeeds.
        """
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}"
            "/credit-limit-increase-requests",
            body={
                "credit_card_account_id": credit_card_account_id,
                "user_id": user_id,
                "requested_increase_amount": requested_increase_amount,
            },
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.GENERIC)
    def deny_credit_limit_increase_request(
        self,
        credit_card_account_id: str,
        user_id: str,
        denial_reason: str,
    ) -> dict:
        """Record a denial decision for a pending credit-limit increase request.

        denial_reason must be exactly one of: insufficient_account_age,
        cooldown_period_active, pending_disputes, pending_replacement_card,
        past_due_balance, high_utilization, insufficient_payment_history,
        requested_amount_exceeds_limit, or other.
        """
        response = self.client_api.request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}"
            "/credit-limit-increase-denials",
            body={
                "credit_card_account_id": credit_card_account_id,
                "user_id": user_id,
                "denial_reason": denial_reason,
            },
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Customer self-service actions (app-completed steps)
    # ------------------------------------------------------------------

    @is_tool(ToolType.GENERIC)
    def create_customer_self_service_action(
        self,
        action_type: str,
        parameters: Optional[dict] = None,
    ) -> dict:
        """Make an in-app self-service action available to the customer.

        Use this only when the applicable procedure requires the customer
        to complete the action themselves in the Rho-Bank app (for
        example, mobile check deposit) rather than having the agent
        perform it directly. Explain to the customer how to use the
        action in the app after creating it.
        """
        body = {"action_type": action_type}
        if parameters is not None:
            body["parameters"] = parameters
        response = self.client_api.request(
            "POST",
            "/v1/customer-self-service-actions",
            body=body,
        )
        response.raise_for_status()
        return response.body

    # ------------------------------------------------------------------
    # Human escalation
    # ------------------------------------------------------------------

    @is_tool(ToolType.GENERIC)
    def transfer_to_human_agent(self, summary: str) -> dict:
        """Transfer the active conversation to a human support agent.

        Only call this after confirming there is no procedure covering
        the customer's request, when a retrieved procedure explicitly
        directs a transfer, or when the customer explicitly asks for a
        human. This is not safe to retry automatically, and no further
        actions can be taken on this conversation afterward.
        """
        conversation_id = quote(self.client_api.context.conversation_id, safe="")
        response = self.client_api.request(
            "POST",
            f"/v1/conversations/{conversation_id}/transfers",
            body={"summary": summary},
        )
        response.raise_for_status()
        return response.body
