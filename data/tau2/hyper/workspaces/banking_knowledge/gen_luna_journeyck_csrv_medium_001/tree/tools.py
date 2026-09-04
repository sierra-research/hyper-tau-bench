from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import quote

from tau2.environment.toolkit import ToolType, is_tool
from tau2.hyper.client_api import ClientAPIToolKitBase


class Tools(ClientAPIToolKitBase):
    """Customer-service operations backed by the documented banking API."""

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        response = self.client_api.request(
            method,
            path,
            query=query,
            body=body,
        )
        if response.status_code < 200 or response.status_code >= 300:
            raise RuntimeError(
                f"Client API request failed with HTTP {response.status_code}: "
                f"{response.body}"
            )
        return response.body

    @staticmethod
    def _encoded(value: str) -> str:
        return quote(value, safe="")

    @is_tool(ToolType.READ)
    def get_current_time(self) -> dict:
        """Get the current server date and time."""
        return self._request("GET", "/v1/time")

    @is_tool(ToolType.READ)
    def search_customer(
        self,
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        home_address: Optional[str] = None,
        date_of_birth: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> list:
        """Find customers using exactly one supported identifier."""
        provided = {
            "email": email,
            "phone_number": phone_number,
            "home_address": home_address,
            "date_of_birth": date_of_birth,
            "full_name": full_name,
        }
        values = {key: value for key, value in provided.items() if value is not None}
        if len(values) != 1:
            raise ValueError(
                "Exactly one supported customer-search identifier is required."
            )
        return self._request("POST", "/v1/customers/search", body=values)

    @is_tool(ToolType.READ)
    def get_customer_accounts(self, customer_id: str) -> dict:
        """List a customer's bank and credit-card accounts."""
        return self._request(
            "GET",
            f"/v1/customers/{self._encoded(customer_id)}/accounts",
        )

    @is_tool(ToolType.READ)
    def get_debit_cards(self, account_id: str) -> dict:
        """List debit cards linked to a checking account."""
        return self._request(
            "GET",
            f"/v1/checking-accounts/{self._encoded(account_id)}/debit-cards",
        )

    @is_tool(ToolType.READ)
    def get_account_transactions(self, account_id: str) -> dict:
        """List transactions for a bank or card account."""
        return self._request(
            "GET",
            f"/v1/accounts/{self._encoded(account_id)}/transactions",
        )

    @is_tool(ToolType.READ)
    def get_credit_card_transactions(self, account_id: str) -> dict:
        """List transactions for a credit-card account."""
        return self._request(
            "GET",
            f"/v1/credit-card-accounts/{self._encoded(account_id)}/transactions",
        )

    @is_tool(ToolType.READ)
    def get_credit_card_disputes(self, customer_id: str) -> dict:
        """List credit-card disputes for a customer."""
        return self._request(
            "GET",
            f"/v1/customers/{self._encoded(customer_id)}/credit-card-disputes",
        )

    @is_tool(ToolType.READ)
    def get_pending_replacement_orders(
        self,
        credit_card_account_id: str,
    ) -> dict:
        """List replacement orders for a credit-card account."""
        return self._request(
            "GET",
            f"/v1/credit-card-accounts/"
            f"{self._encoded(credit_card_account_id)}/pending-replacement-orders",
        )

    @is_tool(ToolType.WRITE)
    def close_debit_card(self, card_id: str, reason: str) -> dict:
        """Permanently close a debit card for a documented reason."""
        return self._request(
            "POST",
            f"/v1/debit-cards/{self._encoded(card_id)}/closure",
            body={"reason": reason},
        )

    @is_tool(ToolType.WRITE)
    def activate_debit_card(
        self,
        card_id: str,
        last_four: str,
        expiration_date: str,
        cvv: str,
        pin: str,
    ) -> dict:
        """Activate a reissued debit card after matching its details."""
        return self._request(
            "POST",
            f"/v1/debit-cards/{self._encoded(card_id)}/activation",
            body={
                "last_four": last_four,
                "expiration_date": expiration_date,
                "cvv": cvv,
                "pin": pin,
            },
        )

    @is_tool(ToolType.WRITE)
    def clear_debit_card_fraud_alert(
        self,
        card_id: str,
        reason: str,
    ) -> dict:
        """Clear a customer-service-clearable debit-card alert."""
        return self._request(
            "POST",
            f"/v1/debit-cards/{self._encoded(card_id)}/fraud-alert-clearances",
            body={"reason": reason},
        )

    @is_tool(ToolType.WRITE)
    def request_temporary_debit_card_limit(
        self,
        card_id: str,
        limit_type: str,
        new_limit: float,
    ) -> dict:
        """Request a temporary debit-card ATM or purchase limit."""
        return self._request(
            "POST",
            f"/v1/debit-cards/"
            f"{self._encoded(card_id)}/temporary-limit-increases",
            body={"limit_type": limit_type, "new_limit": new_limit},
        )

    @is_tool(ToolType.WRITE)
    def pay_credit_card_from_checking(
        self,
        credit_card_account_id: str,
        checking_account_id: str,
        user_id: str,
        amount: float,
    ) -> dict:
        """Make a credit-card payment from a Rho-Bank checking account."""
        return self._request(
            "POST",
            f"/v1/credit-card-accounts/"
            f"{self._encoded(credit_card_account_id)}/payments",
            body={
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
    ) -> dict:
        """Submit a credit-limit-increase request for review."""
        return self._request(
            "POST",
            f"/v1/credit-card-accounts/"
            f"{self._encoded(credit_card_account_id)}/"
            "credit-limit-increase-requests",
            body={
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
    ) -> dict:
        """Record a credit-limit-increase denial."""
        return self._request(
            "POST",
            f"/v1/credit-card-accounts/"
            f"{self._encoded(credit_card_account_id)}/"
            "credit-limit-increase-denials",
            body={"user_id": user_id, "denial_reason": denial_reason},
        )

    @is_tool(ToolType.WRITE)
    def file_credit_card_dispute(
        self,
        credit_card_account_id: str,
        transaction_id: str,
        user_id: str,
        dispute_reason: str,
        amount: float,
    ) -> dict:
        """File a credit-card transaction dispute."""
        return self._request(
            "POST",
            f"/v1/credit-card-accounts/"
            f"{self._encoded(credit_card_account_id)}/disputes",
            body={
                "transaction_id": transaction_id,
                "user_id": user_id,
                "dispute_reason": dispute_reason,
                "amount": amount,
            },
        )

    @is_tool(ToolType.WRITE)
    def order_credit_card_replacement(
        self,
        credit_card_account_id: str,
        user_id: str,
        reason: str,
        shipping_method: str,
        shipping_address: Optional[str] = None,
    ) -> dict:
        """Order a replacement credit card."""
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "reason": reason,
            "shipping_method": shipping_method,
        }
        if shipping_address is not None:
            payload["shipping_address"] = shipping_address
        return self._request(
            "POST",
            f"/v1/credit-card-accounts/"
            f"{self._encoded(credit_card_account_id)}/replacement-orders",
            body=payload,
        )

    @is_tool(ToolType.WRITE)
    def transfer_to_human(self, summary: str) -> dict:
        """Transfer the active conversation to a human support agent."""
        conversation_id = self._encoded(self.client_api.context.conversation_id)
        return self._request(
            "POST",
            f"/v1/conversations/{conversation_id}/transfers",
            body={"summary": summary},
        )

    @is_tool(ToolType.WRITE)
    def perform_customer_self_service_action(
        self,
        action_name: str,
        account_id: str,
        check_amount: float,
    ) -> dict:
        """Submit a customer-owned action required by a documented procedure."""
        if action_name != "deposit_check_3847":
            raise ValueError("Unsupported customer self-service action.")
        return self._request(
            "POST",
            "/v1/customer-self-service-actions",
            body={
                "action_name": action_name,
                "account_id": account_id,
                "check_amount": check_amount,
            },
        )
