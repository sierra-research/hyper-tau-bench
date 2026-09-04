"""Customer-care operations backed by the Client REST API."""

from typing import Any, Dict, Optional
from urllib.parse import quote

from tau2.environment.toolkit import ToolType, is_tool
from tau2.hyper.client_api import ClientAPIToolKitBase


class Tools(ClientAPIToolKitBase):
    """Validated wrappers for customer, line, billing, data, and plan operations."""

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        query: Optional[Dict[str, Any]] = None,
    ) -> Any:
        kwargs: Dict[str, Any] = {}
        if body is not None:
            kwargs["body"] = body
        if query is not None:
            kwargs["query"] = query
        response = self.client_api.request(method, path, **kwargs)
        response.raise_for_status()
        return response.body

    @staticmethod
    def _segment(value: str) -> str:
        return quote(str(value), safe="")

    @is_tool(ToolType.READ)
    def search_customers(
        self,
        phone_number: Optional[str] = None,
        full_name: Optional[str] = None,
        date_of_birth: Optional[str] = None,
        customer_id: Optional[str] = None,
    ) -> Any:
        """Find a customer using a phone number, customer ID, or full name with date of birth."""
        body: Dict[str, Any] = {}
        if phone_number is not None:
            body["phone_number"] = phone_number
        if full_name is not None:
            body["full_name"] = full_name
        if date_of_birth is not None:
            body["date_of_birth"] = date_of_birth
        if customer_id is not None:
            body["customer_id"] = customer_id
        return self._request("POST", "/v1/customers/search", body=body)

    @is_tool(ToolType.READ)
    def get_customer(self, customer_id: str) -> Any:
        """Retrieve a customer account by customer identifier."""
        return self._request("GET", f"/v1/customers/{self._segment(customer_id)}")

    @is_tool(ToolType.READ)
    def get_line(self, line_id: str) -> Any:
        """Retrieve a mobile line and its current service data."""
        return self._request("GET", f"/v1/lines/{self._segment(line_id)}")

    @is_tool(ToolType.READ)
    def get_device(self, device_id: str) -> Any:
        """Retrieve device information."""
        return self._request("GET", f"/v1/devices/{self._segment(device_id)}")

    @is_tool(ToolType.READ)
    def get_bill(self, bill_id: str) -> Any:
        """Retrieve a bill and its current payment status."""
        return self._request("GET", f"/v1/bills/{self._segment(bill_id)}")

    @is_tool(ToolType.READ)
    def list_line_bills(self, line_id: str) -> Any:
        """List billing records associated with a line."""
        return self._request("GET", f"/v1/lines/{self._segment(line_id)}/bills")

    @is_tool(ToolType.READ)
    def get_line_usage(self, line_id: str) -> Any:
        """Check the line's plan allowance, usage, and remaining data."""
        return self._request("GET", f"/v1/lines/{self._segment(line_id)}/usage")

    @is_tool(ToolType.READ)
    def list_available_plans(self, line_id: str) -> Any:
        """List monthly plans currently eligible for a line."""
        return self._request(
            "GET",
            f"/v1/lines/{self._segment(line_id)}/available-plans",
        )

    @is_tool(ToolType.READ)
    def create_plan_quote(self, line_id: str, plan_id: str) -> Any:
        """Create an information-only quote for changing a line to an eligible plan."""
        return self._request(
            "POST",
            f"/v1/lines/{self._segment(line_id)}/plan-quotes",
            body={"plan_id": plan_id},
        )

    @is_tool(ToolType.WRITE)
    def change_plan(
        self,
        line_id: str,
        plan_id: str,
        quote_id: str,
        confirmation: str,
    ) -> Any:
        """Apply a quoted plan change after the customer confirms the plan and price."""
        return self._request(
            "POST",
            f"/v1/lines/{self._segment(line_id)}/plan-changes",
            body={
                "plan_id": plan_id,
                "quote_id": quote_id,
                "confirmation": confirmation,
            },
        )

    @is_tool(ToolType.READ)
    def list_refuels(self, line_id: str) -> Any:
        """List completed and pending data refuels for a line."""
        return self._request("GET", f"/v1/lines/{self._segment(line_id)}/refuels")

    @is_tool(ToolType.READ)
    def create_refuel_quote(self, line_id: str, amount_gb: float) -> Any:
        """Create an information-only quote for an eligible data refuel amount."""
        return self._request(
            "POST",
            f"/v1/lines/{self._segment(line_id)}/refuel-quotes",
            body={"amount_gb": amount_gb},
        )

    @is_tool(ToolType.WRITE)
    def purchase_refuel(
        self,
        line_id: str,
        quote_id: str,
        confirmation: str,
    ) -> Any:
        """Purchase a quoted data refuel after the customer confirms the amount and price."""
        return self._request(
            "POST",
            f"/v1/lines/{self._segment(line_id)}/refuels",
            body={"quote_id": quote_id, "confirmation": confirmation},
        )

    @is_tool(ToolType.READ)
    def get_roaming_status(self, line_id: str) -> Any:
        """Check roaming and international mobile-data status for a line."""
        return self._request(
            "GET",
            f"/v1/lines/{self._segment(line_id)}/roaming",
        )

    @is_tool(ToolType.WRITE)
    def restore_roaming(self, line_id: str, confirmation: str) -> Any:
        """Restore eligible mobile-data roaming after explicit confirmation."""
        return self._request(
            "POST",
            f"/v1/lines/{self._segment(line_id)}/roaming",
            body={"confirmation": confirmation},
        )

    @is_tool(ToolType.READ)
    def get_service_status(self, line_id: str) -> Any:
        """Check the current cellular service state for a line."""
        return self._request(
            "GET",
            f"/v1/lines/{self._segment(line_id)}/service-status",
        )

    @is_tool(ToolType.WRITE)
    def record_service_recovery(self, line_id: str, resolution: str) -> Any:
        """Record a completed supported service-recovery resolution."""
        return self._request(
            "POST",
            f"/v1/lines/{self._segment(line_id)}/service-recovery",
            body={"resolution": resolution},
        )

    @is_tool(ToolType.GENERIC)
    def transfer_to_human_agents(self, summary: str) -> Any:
        """Transfer the conversation to a human care specialist."""
        conversation_id = self._segment(self.client_api.context.conversation_id)
        return self._request(
            "POST",
            f"/v1/conversations/{conversation_id}/transfers",
            body={"summary": summary},
        )
