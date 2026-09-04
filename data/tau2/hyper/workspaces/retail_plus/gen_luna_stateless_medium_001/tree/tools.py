"""Agent tools backed by the client-owned REST API."""

from typing import Any, Dict, Optional
from urllib.parse import quote

from tau2.environment.toolkit import ToolType, is_tool
from tau2.hyper.client_api import ClientAPIToolKitBase


class Tools(ClientAPIToolKitBase):
    """Customer-support operations exposed to the agent."""

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        response = self.client_api.request(method, path, body=body)
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def search_customer(
        self,
        email: Optional[str] = None,
        name: Optional[str] = None,
        postal_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Find a customer using an email or complete name and postal code."""
        payload: Dict[str, Any] = {}
        if email is not None:
            payload["email"] = email
        else:
            if name is None or postal_code is None:
                raise ValueError(
                    "Provide either email or both name and postal_code."
                )
            payload["name"] = name
            payload["postal_code"] = postal_code
        return self._request("POST", "/v1/customers/search", payload)

    @is_tool(ToolType.READ)
    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Retrieve a verified customer profile."""
        identifier = quote(customer_id, safe="")
        return self._request("GET", f"/v1/customers/{identifier}")

    @is_tool(ToolType.READ)
    def get_order(self, order_id: str) -> Dict[str, Any]:
        """Retrieve an order by its customer-facing identifier."""
        identifier = quote(order_id, safe="")
        return self._request("GET", f"/v1/orders/{identifier}")

    @is_tool(ToolType.READ)
    def get_receipt(self, order_id: str) -> Dict[str, Any]:
        """Retrieve the receipt and purchase totals for an order."""
        identifier = quote(order_id, safe="")
        return self._request("GET", f"/v1/orders/{identifier}/receipt")

    @is_tool(ToolType.READ)
    def get_messages(self, order_id: str) -> Dict[str, Any]:
        """Retrieve customer messages associated with an order."""
        identifier = quote(order_id, safe="")
        return self._request("GET", f"/v1/orders/{identifier}/messages")

    @is_tool(ToolType.READ)
    def get_payment_methods(self, customer_id: str) -> Dict[str, Any]:
        """Retrieve saved payment methods for a customer."""
        identifier = quote(customer_id, safe="")
        return self._request(
            "GET",
            f"/v1/customers/{identifier}/payment-methods",
        )

    @is_tool(ToolType.READ)
    def get_addresses(self, customer_id: str) -> Dict[str, Any]:
        """Retrieve saved addresses for a customer."""
        identifier = quote(customer_id, safe="")
        return self._request(
            "GET",
            f"/v1/customers/{identifier}/addresses",
        )

    @is_tool(ToolType.WRITE)
    def update_default_address(
        self,
        customer_id: str,
        address: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Replace the customer's default delivery address."""
        identifier = quote(customer_id, safe="")
        return self._request(
            "PATCH",
            f"/v1/customers/{identifier}/addresses/default",
            {"address": address},
        )

    @is_tool(ToolType.WRITE)
    def create_return_request(
        self,
        order_id: str,
        items: list[Dict[str, Any]],
        refund_payment_method_id: str,
    ) -> Dict[str, Any]:
        """Submit a confirmed return request for a delivered order."""
        identifier = quote(order_id, safe="")
        return self._request(
            "POST",
            f"/v1/orders/{identifier}/returns",
            {
                "items": items,
                "refund_payment_method_id": refund_payment_method_id,
            },
        )

    @is_tool(ToolType.WRITE)
    def create_exchange_request(
        self,
        order_id: str,
        items: list[Dict[str, Any]],
        payment_method_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit a confirmed same-product exchange request."""
        identifier = quote(order_id, safe="")
        payload: Dict[str, Any] = {"items": items}
        if payment_method_id is not None:
            payload["payment_method_id"] = payment_method_id
        return self._request(
            "POST",
            f"/v1/orders/{identifier}/exchanges",
            payload,
        )

    @is_tool(ToolType.GENERIC)
    def transfer_to_human_agents(self, summary: str) -> Dict[str, Any]:
        """Transfer the conversation to a human support representative."""
        conversation_id = quote(
            self.client_api.context.conversation_id,
            safe="",
        )
        return self._request(
            "POST",
            f"/v1/conversations/{conversation_id}/transfers",
            {"summary": summary},
        )
