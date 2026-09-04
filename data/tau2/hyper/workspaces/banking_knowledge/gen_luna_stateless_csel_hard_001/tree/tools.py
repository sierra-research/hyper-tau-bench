"""Customer-service operations backed by the Client REST API."""

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
        if response.status_code < 200 or response.status_code >= 300:
            raise RuntimeError(
                f"Client API request failed with status "
                f"{response.status_code}: {response.body}"
            )
        return response.body

    @is_tool(ToolType.READ)
    def get_current_time(self) -> Any:
        """Retrieve the current server timestamp."""
        return self._request("GET", "/v1/time")

    @is_tool(ToolType.READ)
    def search_customer(
        self,
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        home_address: Optional[str] = None,
        date_of_birth: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> Any:
        """Find a customer using exactly one supported identifier."""
        supplied = {
            "email": email,
            "phone_number": phone_number,
            "home_address": home_address,
            "date_of_birth": date_of_birth,
            "full_name": full_name,
        }
        values = {key: value for key, value in supplied.items() if value is not None}
        if len(values) != 1:
            raise ValueError(
                "Provide exactly one supported customer-search identifier."
            )
        return self._request("POST", "/v1/customers/search", body=values)

    @is_tool(ToolType.READ)
    def get_customer_accounts(self, customer_id: str) -> Any:
        """List a customer's bank and credit-card accounts."""
        return self._request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/accounts",
        )

    @is_tool(ToolType.READ)
    def get_account_debit_cards(self, account_id: str) -> Any:
        """List debit cards linked to a checking account."""
        return self._request(
            "GET",
            f"/v1/checking-accounts/{quote(account_id, safe='')}/debit-cards",
        )

    @is_tool(ToolType.READ)
    def get_credit_card_transactions(
        self,
        credit_card_account_id: str,
    ) -> Any:
        """List transactions for a credit-card account."""
        return self._request(
            "GET",
            f"/v1/credit-card-accounts/"
            f"{quote(credit_card_account_id, safe='')}/transactions",
        )

    @is_tool(ToolType.READ)
    def get_debit_card_transactions(self, card_id: str) -> Any:
        """List transactions for a debit card."""
        return self._request(
            "GET",
            f"/v1/debit-cards/{quote(card_id, safe='')}/transactions",
        )

    @is_tool(ToolType.READ)
    def get_credit_card_account(self, account_id: str) -> Any:
        """Retrieve a credit-card account."""
        return self._request(
            "GET",
            f"/v1/credit-card-accounts/{quote(account_id, safe='')}",
        )

    @is_tool(ToolType.READ)
    def get_debit_card(self, card_id: str) -> Any:
        """Retrieve a debit card."""
        return self._request(
            "GET",
            f"/v1/debit-cards/{quote(card_id, safe='')}",
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
        """Activate an eligible debit card."""
        return self._request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/activation",
            body={
                "last_four": last_four,
                "expiration_date": expiration_date,
                "cvv": cvv,
                "pin": pin,
            },
        )

    @is_tool(ToolType.WRITE)
    def close_debit_card(self, card_id: str, reason: str) -> Any:
        """Permanently close a debit card."""
        return self._request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/closure",
            body={"reason": reason},
        )

    @is_tool(ToolType.WRITE)
    def clear_debit_card_fraud_alert(
        self,
        card_id: str,
        reason: str,
    ) -> Any:
        """Clear a customer-service-clearable debit-card alert."""
        return self._request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/fraud-alert-clearances",
            body={"reason": reason},
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
            f"/v1/debit-cards/"
            f"{quote(card_id, safe='')}/temporary-limit-increases",
            body={"limit_type": limit_type, "new_limit": new_limit},
        )

    @is_tool(ToolType.WRITE)
    def order_debit_card_replacement(
        self,
        card_id: str,
        reason: str,
        shipping_method: Optional[str] = None,
        shipping_address: Optional[str] = None,
    ) -> Any:
        """Order a replacement debit card."""
        body: Dict[str, Any] = {"reason": reason}
        if shipping_method is not None:
            body["shipping_method"] = shipping_method
        if shipping_address is not None:
            body["shipping_address"] = shipping_address
        return self._request(
            "POST",
            f"/v1/debit-cards/{quote(card_id, safe='')}/replacements",
            body=body,
        )

    @is_tool(ToolType.READ)
    def get_pending_replacement_orders(
        self,
        credit_card_account_id: str,
    ) -> Any:
        """List replacement orders for a credit-card account."""
        return self._request(
            "GET",
            f"/v1/credit-card-accounts/"
            f"{quote(credit_card_account_id, safe='')}/pending-replacement-orders",
        )

    @is_tool(ToolType.WRITE)
    def order_credit_card_replacement(
        self,
        credit_card_account_id: str,
        card_id: str,
        reason: str,
        shipping_method: str,
        shipping_address: Optional[str] = None,
    ) -> Any:
        """Order a replacement credit card."""
        body: Dict[str, Any] = {
            "card_id": card_id,
            "reason": reason,
            "shipping_method": shipping_method,
        }
        if shipping_address is not None:
            body["shipping_address"] = shipping_address
        return self._request(
            "POST",
            f"/v1/credit-card-accounts/"
            f"{quote(credit_card_account_id, safe='')}/replacement-orders",
            body=body,
        )

    @is_tool(ToolType.WRITE)
    def make_credit_card_payment(
        self,
        credit_card_account_id: str,
        checking_account_id: str,
        user_id: str,
        amount: float,
    ) -> Any:
        """Pay a credit-card account from a Rho-Bank checking account."""
        return self._request(
            "POST",
            f"/v1/credit-card-accounts/"
            f"{quote(credit_card_account_id, safe='')}/payments",
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
    ) -> Any:
        """Submit a credit-limit increase request."""
        return self._request(
            "POST",
            f"/v1/credit-card-accounts/"
            f"{quote(credit_card_account_id, safe='')}/"
            "credit-limit-increase-requests",
            body={
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
        """Record a credit-limit increase denial."""
        return self._request(
            "POST",
            f"/v1/credit-card-accounts/"
            f"{quote(credit_card_account_id, safe='')}/"
            "credit-limit-increase-denials",
            body={
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
        approved_increase_amount: float,
    ) -> Any:
        """Approve a credit-limit increase after eligibility review."""
        return self._request(
            "POST",
            f"/v1/credit-card-accounts/"
            f"{quote(credit_card_account_id, safe='')}/"
            "credit-limit-increase-approvals",
            body={
                "credit_card_account_id": credit_card_account_id,
                "user_id": user_id,
                "approved_increase_amount": approved_increase_amount,
            },
        )

    @is_tool(ToolType.WRITE)
    def submit_credit_card_dispute(
        self,
        credit_card_account_id: str,
        transaction_id: str,
        user_id: str,
        reason: str,
        amount: float,
        purchase_date: str,
        merchant_contacted: Optional[bool] = None,
    ) -> Any:
        """Submit a credit-card transaction dispute."""
        body: Dict[str, Any] = {
            "transaction_id": transaction_id,
            "user_id": user_id,
            "reason": reason,
            "amount": amount,
            "purchase_date": purchase_date,
        }
        if merchant_contacted is not None:
            body["merchant_contacted"] = merchant_contacted
        return self._request(
            "POST",
            f"/v1/credit-card-accounts/"
            f"{quote(credit_card_account_id, safe='')}/disputes",
            body=body,
        )

    @is_tool(ToolType.READ)
    def get_customer_credit_card_disputes(self, customer_id: str) -> Any:
        """List a customer's credit-card disputes."""
        return self._request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/credit-card-disputes",
        )

    @is_tool(ToolType.READ)
    def get_customer_referrals(self, customer_id: str) -> Any:
        """List a customer's referrals."""
        return self._request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/referrals",
        )

    @is_tool(ToolType.WRITE)
    def create_referral_link(self, customer_id: str, product: str) -> Any:
        """Create a referral link for a participating product."""
        return self._request(
            "POST",
            f"/v1/customers/{quote(customer_id, safe='')}/referrals",
            body={"product": product},
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
            body={"summary": summary},
        )

    @is_tool(ToolType.WRITE)
    def customer_self_service_action(
        self,
        action_name: str,
        account_id: str,
        check_amount: float,
    ) -> Any:
        """Submit a documented customer self-service action."""
        return self._request(
            "POST",
            "/v1/customer-self-service-actions",
            body={
                "action_name": action_name,
                "account_id": account_id,
                "check_amount": check_amount,
            },
        )
