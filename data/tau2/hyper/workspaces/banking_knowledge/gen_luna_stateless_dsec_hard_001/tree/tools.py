"""Customer-service tools backed by the documented banking REST API."""

from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import quote

from tau2.environment.toolkit import ToolType, is_tool
from tau2.hyper.client_api import ClientAPIToolKitBase


class Tools(ClientAPIToolKitBase):
    """Expose documented banking operations to the support agent."""

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        response = self.client_api.request(method, path, body=body)
        if hasattr(response, "raise_for_status"):
            response.raise_for_status()
            return response.body
        status = getattr(response, "status_code", 200)
        payload = getattr(response, "body", response)
        if status < 200 or status >= 300:
            raise RuntimeError(
                f"Client API request failed with status {status}: {payload}"
            )
        return payload

    @is_tool(ToolType.READ)
    def get_current_time(self) -> Any:
        """Retrieve the current server date and time."""
        return self._request("GET", "/v1/time")

    @is_tool(ToolType.READ)
    def search_customers(
        self,
        identifier_type: str,
        identifier_value: str,
    ) -> Any:
        """Find customer profiles using one supported identifier."""
        return self._request(
            "POST",
            "/v1/customers/search",
            {
                "identifier_type": identifier_type,
                "identifier_value": identifier_value,
            },
        )

    @is_tool(ToolType.READ)
    def get_customer_accounts(self, customer_id: str) -> Any:
        """List a customer's bank and credit-card accounts."""
        return self._request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/accounts",
        )

    @is_tool(ToolType.WRITE)
    def record_verification(
        self,
        customer_id: str,
        factors: Dict[str, str],
    ) -> Any:
        """Record a successful two-factor identity verification."""
        return self._request(
            "POST",
            "/v1/verifications",
            {"customer_id": customer_id, "factors": factors},
        )

    @is_tool(ToolType.READ)
    def get_debit_cards(self, account_id: str) -> Any:
        """List debit cards linked to a checking account."""
        return self._request(
            "GET",
            f"/v1/checking-accounts/{quote(account_id, safe='')}/debit-cards",
        )

    @is_tool(ToolType.WRITE)
    def activate_debit_card(
        self,
        card_id: str,
        last_four: str,
        expiration_date: str,
        cvv: str,
        pin: str,
    ) -> Any:
        """Activate a reissued debit card after validating printed details."""
        return self._request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/activation",
            {
                "last_four": last_four,
                "expiration_date": expiration_date,
                "cvv": cvv,
                "pin": pin,
            },
        )

    @is_tool(ToolType.WRITE)
    def close_debit_card(self, card_id: str, reason: str) -> Any:
        """Permanently close a debit card for a documented reason."""
        return self._request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/closure",
            {"reason": reason},
        )

    @is_tool(ToolType.WRITE)
    def clear_debit_card_fraud_alert(
        self,
        card_id: str,
        reason: str,
    ) -> Any:
        """Clear an eligible debit-card security alert."""
        return self._request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/fraud-alert-clearances",
            {"reason": reason},
        )

    @is_tool(ToolType.WRITE)
    def request_temporary_debit_card_limit(
        self,
        card_id: str,
        limit_type: str,
        new_limit: float,
    ) -> Any:
        """Request a temporary debit-card ATM or purchase limit."""
        return self._request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/temporary-limit-increases",
            {
                "limit_type": limit_type,
                "new_limit": new_limit,
            },
        )

    @is_tool(ToolType.READ)
    def get_credit_card_disputes(self, customer_id: str) -> Any:
        """List credit-card disputes for a customer."""
        return self._request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/credit-card-disputes",
        )

    @is_tool(ToolType.WRITE)
    def file_credit_card_dispute(
        self,
        credit_card_account_id: str,
        transaction_id: str,
        reason: str,
        amount: float,
        purchase_date: str,
        merchant_contacted: bool,
    ) -> Any:
        """File a documented credit-card transaction dispute."""
        return self._request(
            "POST",
            "/v1/credit-card-disputes",
            {
                "credit_card_account_id": credit_card_account_id,
                "transaction_id": transaction_id,
                "reason": reason,
                "amount": amount,
                "purchase_date": purchase_date,
                "merchant_contacted": merchant_contacted,
            },
        )

    @is_tool(ToolType.READ)
    def get_pending_replacement_orders(
        self,
        credit_card_account_id: str,
    ) -> Any:
        """Check replacement orders for a credit-card account."""
        return self._request(
            "GET",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/pending-replacement-orders",
        )

    @is_tool(ToolType.WRITE)
    def order_credit_card_replacement(
        self,
        credit_card_account_id: str,
        reason: str,
        shipping_method: str,
        shipping_address: Optional[str] = None,
    ) -> Any:
        """Order a replacement credit card."""
        body: Dict[str, Any] = {
            "credit_card_account_id": credit_card_account_id,
            "reason": reason,
            "shipping_method": shipping_method,
        }
        if shipping_address is not None:
            body["shipping_address"] = shipping_address
        return self._request("POST", "/v1/credit-card-replacements", body)

    @is_tool(ToolType.WRITE)
    def make_credit_card_payment(
        self,
        credit_card_account_id: str,
        checking_account_id: str,
        user_id: str,
        amount: float,
    ) -> Any:
        """Pay a credit card from a Rho-Bank checking account."""
        return self._request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/payments",
            {
                "checking_account_id": checking_account_id,
                "user_id": user_id,
                "amount": amount,
            },
        )

    @is_tool(ToolType.WRITE)
    def submit_credit_limit_increase(
        self,
        credit_card_account_id: str,
        user_id: str,
        requested_increase_amount: float,
    ) -> Any:
        """Submit a credit-limit-increase request for review."""
        return self._request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/credit-limit-increase-requests",
            {
                "credit_card_account_id": credit_card_account_id,
                "user_id": user_id,
                "requested_increase_amount": requested_increase_amount,
            },
        )

    @is_tool(ToolType.WRITE)
    def deny_credit_limit_increase(
        self,
        credit_card_account_id: str,
        user_id: str,
        denial_reason: str,
    ) -> Any:
        """Record a credit-limit-increase denial."""
        return self._request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/credit-limit-increase-denials",
            {
                "credit_card_account_id": credit_card_account_id,
                "user_id": user_id,
                "denial_reason": denial_reason,
            },
        )

    @is_tool(ToolType.WRITE)
    def approve_credit_limit_increase(
        self,
        credit_card_account_id: str,
        user_id: str,
        requested_increase_amount: float,
    ) -> Any:
        """Approve an eligible credit-limit-increase request."""
        return self._request(
            "POST",
            f"/v1/credit-card-accounts/{quote(credit_card_account_id, safe='')}/credit-limit-increase-approvals",
            {
                "credit_card_account_id": credit_card_account_id,
                "user_id": user_id,
                "requested_increase_amount": requested_increase_amount,
            },
        )

    @is_tool(ToolType.WRITE)
    def transfer_to_human_agents(self, summary: str) -> Any:
        """Transfer the active conversation to a human support agent."""
        conversation_id = quote(
            self.client_api.context.conversation_id,
            safe="",
        )
        return self._request(
            "POST",
            f"/v1/conversations/{conversation_id}/transfers",
            {"summary": summary},
        )
