"""Agent tools backed by the client-owned REST API."""

from typing import Any, Dict, Optional
from urllib.parse import quote

from tau2.environment.toolkit import ToolType, is_tool
from tau2.hyper.client_api import ClientAPIToolKitBase


class Tools(ClientAPIToolKitBase):
    """Customer-care operations exposed to the service agent."""

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
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def search_customers(
        self,
        phone_number: Optional[str] = None,
        full_name: Optional[str] = None,
        date_of_birth: Optional[str] = None,
        customer_id: Optional[str] = None,
    ) -> Any:
        """Find a customer by exact phone number, customer ID, or full name and date of birth."""
        selectors = [
            phone_number is not None,
            customer_id is not None,
            full_name is not None or date_of_birth is not None,
        ]
        if sum(selectors) != 1:
            raise ValueError(
                "Provide exactly one selector: phone_number, customer_id, "
                "or full_name together with date_of_birth."
            )
        if full_name is not None and date_of_birth is None:
            raise ValueError("date_of_birth is required with full_name.")
        body: Dict[str, Any] = {}
        if phone_number is not None:
            body["phone_number"] = phone_number
        elif customer_id is not None:
            body["customer_id"] = customer_id
        else:
            body["full_name"] = full_name
            body["date_of_birth"] = date_of_birth
        return self._request("POST", "/v1/customers/search", body=body)

    @is_tool(ToolType.READ)
    def get_customer(self, customer_id: str) -> Any:
        """Retrieve a customer record by identifier."""
        return self._request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}",
        )

    @is_tool(ToolType.READ)
    def get_account(self, customer_id: str) -> Any:
        """Retrieve the account associated with a customer."""
        return self._request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/account",
        )

    @is_tool(ToolType.READ)
    def list_lines(self, customer_id: str) -> Any:
        """List the customer's mobile lines."""
        return self._request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/lines",
        )

    @is_tool(ToolType.READ)
    def get_line(self, line_id: str) -> Any:
        """Retrieve a mobile line by identifier."""
        return self._request(
            "GET",
            f"/v1/lines/{quote(line_id, safe='')}",
        )

    @is_tool(ToolType.READ)
    def get_usage(self, line_id: str) -> Any:
        """Retrieve current-cycle data usage and available allowance."""
        return self._request(
            "GET",
            f"/v1/lines/{quote(line_id, safe='')}/usage",
        )

    @is_tool(ToolType.READ)
    def list_bills(self, customer_id: str) -> Any:
        """List bills belonging to a customer."""
        return self._request(
            "GET",
            f"/v1/customers/{quote(customer_id, safe='')}/bills",
        )

    @is_tool(ToolType.READ)
    def get_bill(self, bill_id: str) -> Any:
        """Retrieve a bill by identifier."""
        return self._request(
            "GET",
            f"/v1/bills/{quote(bill_id, safe='')}",
        )

    @is_tool(ToolType.READ)
    def list_plans(self, line_id: str) -> Any:
        """List monthly plans currently available for a line."""
        return self._request(
            "GET",
            f"/v1/lines/{quote(line_id, safe='')}/plans",
        )

    @is_tool(ToolType.READ)
    def get_plan(self, plan_id: str) -> Any:
        """Retrieve a plan by identifier."""
        return self._request(
            "GET",
            f"/v1/plans/{quote(plan_id, safe='')}",
        )

    @is_tool(ToolType.READ)
    def create_plan_quote(self, line_id: str, plan_id: str) -> Any:
        """Create a calculated quote for changing a line to an eligible plan."""
        return self._request(
            "POST",
            f"/v1/lines/{quote(line_id, safe='')}/plan-quotes",
            body={"plan_id": plan_id},
        )

    @is_tool(ToolType.READ)
    def get_plan_quote(self, quote_id: str) -> Any:
        """Retrieve a saved plan quote and its status."""
        return self._request(
            "GET",
            f"/v1/plan-quotes/{quote(quote_id, safe='')}",
        )

    @is_tool(ToolType.WRITE)
    def change_plan(
        self,
        line_id: str,
        plan_id: str,
        quote_id: str,
        confirmed_plan_name: str,
        confirmed_new_monthly_price: float,
    ) -> Any:
        """Apply a plan change after explicit confirmation of plan and price."""
        return self._request(
            "POST",
            f"/v1/lines/{quote(line_id, safe='')}/plan-changes",
            body={
                "plan_id": plan_id,
                "quote_id": quote_id,
                "confirmed_plan_name": confirmed_plan_name,
                "confirmed_new_monthly_price": confirmed_new_monthly_price,
            },
        )

    @is_tool(ToolType.READ)
    def list_refuels(self, line_id: str) -> Any:
        """List data refuels for a line."""
        return self._request(
            "GET",
            f"/v1/lines/{quote(line_id, safe='')}/refuels",
        )

    @is_tool(ToolType.READ)
    def create_refuel_quote(self, line_id: str, amount_gb: float) -> Any:
        """Create a quote for an eligible current-cycle data refuel."""
        return self._request(
            "POST",
            f"/v1/lines/{quote(line_id, safe='')}/refuel-quotes",
            body={"amount_gb": amount_gb},
        )

    @is_tool(ToolType.READ)
    def get_refuel_quote(self, quote_id: str) -> Any:
        """Retrieve a saved data-refuel quote and its status."""
        return self._request(
            "GET",
            f"/v1/refuel-quotes/{quote(quote_id, safe='')}",
        )

    @is_tool(ToolType.WRITE)
    def purchase_refuel(
        self,
        line_id: str,
        amount_gb: float,
        quote_id: str,
        confirmed_amount_gb: float,
        confirmed_price: float,
    ) -> Any:
        """Purchase a quoted data refuel after explicit confirmation."""
        return self._request(
            "POST",
            f"/v1/lines/{quote(line_id, safe='')}/refuels",
            body={
                "amount_gb": amount_gb,
                "quote_id": quote_id,
                "confirmed_amount_gb": confirmed_amount_gb,
                "confirmed_price": confirmed_price,
            },
        )

    @is_tool(ToolType.READ)
    def get_device(self, device_id: str) -> Any:
        """Retrieve a device by identifier."""
        return self._request(
            "GET",
            f"/v1/devices/{quote(device_id, safe='')}",
        )

    @is_tool(ToolType.GENERIC)
    def transfer_to_human_agents(self, summary: str) -> Any:
        """Transfer the conversation to a human care specialist."""
        conversation_id = quote(
            self.client_api.context.conversation_id,
            safe="",
        )
        return self._request(
            "POST",
            f"/v1/conversations/{conversation_id}/transfers",
            body={"summary": summary},
        )
