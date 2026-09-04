from typing import Any, Dict, List, Optional
from urllib.parse import quote

from tau2.environment.toolkit import ToolType, is_tool
from tau2.hyper.client_api import ClientAPIToolKitBase


class Tools(ClientAPIToolKitBase):
    """Customer-service operations backed by the Client REST API."""

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        query: Optional[Dict[str, Any]] = None,
    ) -> Any:
        response = self.client_api.request(
            method,
            path,
            body=body,
            query=query,
        )
        if 200 <= response.status_code < 300:
            return response.body
        return {
            "ok": False,
            "status_code": response.status_code,
            "error": response.body,
        }

    @is_tool(ToolType.READ)
    def search_customer(
        self,
        email: Optional[str] = None,
        name: Optional[str] = None,
        postal_code: Optional[str] = None,
    ) -> Any:
        """Find a customer by email or by complete name and postal code."""
        if email:
            body = {"email": email}
        elif name and postal_code:
            body = {"name": name, "postal_code": postal_code}
        else:
            return {
                "ok": False,
                "error": {
                    "code": "invalid_verification_input",
                    "message": "Provide an email or both name and postal code.",
                },
            }
        return self._request("POST", "/v1/customers/search", body=body)

    @is_tool(ToolType.READ)
    def get_customer(self, customer_id: str) -> Any:
        """Read a verified customer profile."""
        if not customer_id:
            return {"ok": False, "error": "customer_id is required"}
        return self._request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}",
        )

    @is_tool(ToolType.READ)
    def get_order(self, order_id: str) -> Any:
        """Read an order and its current status and details."""
        if not order_id:
            return {"ok": False, "error": "order_id is required"}
        return self._request(
            "GET",
            f"/v1/orders/{quote(order_id, safe='')}",
        )

    @is_tool(ToolType.READ)
    def list_customer_orders(self, customer_id: str) -> Any:
        """List orders belonging to a verified customer."""
        if not customer_id:
            return {"ok": False, "error": "customer_id is required"}
        return self._request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/orders",
        )

    @is_tool(ToolType.READ)
    def list_payment_methods(self, customer_id: str) -> Any:
        """List saved payment methods for a verified customer."""
        if not customer_id:
            return {"ok": False, "error": "customer_id is required"}
        return self._request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/payment-methods",
        )

    @is_tool(ToolType.READ)
    def get_order_messages(self, order_id: str) -> Any:
        """Read customer messages associated with an order."""
        if not order_id:
            return {"ok": False, "error": "order_id is required"}
        return self._request(
            "GET",
            f"/v1/orders/{quote(order_id, safe='')}/messages",
        )

    @is_tool(ToolType.WRITE)
    def submit_return(
        self,
        order_id: str,
        items: List[Dict[str, Any]],
        payment_method_id: str,
    ) -> Any:
        """Submit a confirmed return for a delivered order."""
        if not order_id or not items or not payment_method_id:
            return {
                "ok": False,
                "error": "order_id, items, and payment_method_id are required",
            }
        return self._request(
            "POST",
            f"/v1/orders/{quote(order_id, safe='')}/returns",
            body={
                "items": items,
                "payment_method_id": payment_method_id,
            },
        )

    @is_tool(ToolType.WRITE)
    def submit_exchange(
        self,
        order_id: str,
        items: List[Dict[str, Any]],
        payment_method_id: Optional[str] = None,
    ) -> Any:
        """Submit a confirmed same-product exchange for a delivered order."""
        if not order_id or not items:
            return {
                "ok": False,
                "error": "order_id and items are required",
            }
        body: Dict[str, Any] = {"items": items}
        if payment_method_id:
            body["payment_method_id"] = payment_method_id
        return self._request(
            "POST",
            f"/v1/orders/{quote(order_id, safe='')}/exchanges",
            body=body,
        )

    @is_tool(ToolType.WRITE)
    def cancel_order(self, order_id: str) -> Any:
        """Cancel an eligible order before delivery."""
        if not order_id:
            return {"ok": False, "error": "order_id is required"}
        return self._request(
            "POST",
            f"/v1/orders/{quote(order_id, safe='')}/cancel",
        )

    @is_tool(ToolType.WRITE)
    def update_customer_address(
        self,
        customer_id: str,
        address_id: str,
        address: Dict[str, Any],
    ) -> Any:
        """Update a saved customer address."""
        if not customer_id or not address_id or not address:
            return {
                "ok": False,
                "error": "customer_id, address_id, and address are required",
            }
        return self._request(
            "PATCH",
            f"/v1/customers/{quote(customer_id, safe='')}/addresses/"
            f"{quote(address_id, safe='')}",
            body=address,
        )

    @is_tool(ToolType.WRITE)
    def add_delivery_instructions(
        self,
        customer_id: str,
        address_id: str,
        instructions: str,
    ) -> Any:
        """Save delivery instructions on a customer address."""
        if not customer_id or not address_id or not instructions:
            return {
                "ok": False,
                "error": "customer_id, address_id, and instructions are required",
            }
        return self._request(
            "PATCH",
            f"/v1/customers/{quote(customer_id, safe='')}/addresses/"
            f"{quote(address_id, safe='')}",
            body={"delivery_instructions": instructions},
        )

    @is_tool(ToolType.WRITE)
    def transfer_to_human_agents(self, summary: str) -> Any:
        """Transfer the conversation to a human support agent."""
        if not summary:
            return {"ok": False, "error": "summary is required"}
        conversation_id = quote(
            self.client_api.context.conversation_id,
            safe="",
        )
        return self._request(
            "POST",
            f"/v1/conversations/{conversation_id}/transfers",
            body={"summary": summary},
        )
