"""Airline customer-service operations backed by the Client REST API."""

from typing import Any, Dict, Optional
from urllib.parse import quote

from tau2.environment.toolkit import ToolType, is_tool
from tau2.hyper.client_api import ClientAPIToolKitBase


class Tools(ClientAPIToolKitBase):
    """Operations exposed to the customer-service agent."""

    def _request(
        self,
        method: str,
        path: str,
        query: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        kwargs: Dict[str, Any] = {}
        if query is not None:
            kwargs["query"] = query
        if body is not None:
            kwargs["body"] = body
        response = self.client_api.request(method, path, **kwargs)
        response.raise_for_status()
        return response.body

    @staticmethod
    def _identifier(value: str) -> str:
        return quote(value, safe="")

    @is_tool(ToolType.READ)
    def get_customer(self, customer_id: str) -> dict:
        """Retrieve a customer profile, including reservations and saved payment methods."""
        return self._request(
            "GET",
            f"/v1/customers/{self._identifier(customer_id)}",
        )

    @is_tool(ToolType.READ)
    def get_reservation(self, reservation_id: str) -> dict:
        """Retrieve a reservation by its customer-facing confirmation identifier."""
        return self._request(
            "GET",
            f"/v1/reservations/{self._identifier(reservation_id)}",
        )

    @is_tool(ToolType.READ)
    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        cabin: str,
        passengers: int = 1,
        return_date: Optional[str] = None,
        stops: Optional[int] = None,
    ) -> dict:
        """Search currently available flights for a specified itinerary."""
        query: Dict[str, Any] = {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "cabin": cabin,
            "passengers": passengers,
        }
        if return_date is not None:
            query["return_date"] = return_date
        if stops is not None:
            query["stops"] = stops
        return self._request("GET", "/v1/flights", query=query)

    @is_tool(ToolType.READ)
    def get_flight_status(self, flight_number: str, departure_date: str) -> dict:
        """Check the operational status of a flight on a specified date."""
        return self._request(
            "GET",
            f"/v1/flights/{self._identifier(flight_number)}/status",
            query={"departure_date": departure_date},
        )

    @is_tool(ToolType.READ)
    def price_reservation_change(
        self,
        reservation_id: str,
        flight_number: str,
        departure_date: str,
    ) -> dict:
        """Preview the price of changing one flight in an existing reservation."""
        return self._request(
            "POST",
            f"/v1/reservations/{self._identifier(reservation_id)}/changes/price",
            body={
                "flight_number": flight_number,
                "departure_date": departure_date,
            },
        )

    @is_tool(ToolType.WRITE)
    def change_reservation_flight(
        self,
        reservation_id: str,
        current_flight_number: str,
        new_flight_number: str,
        new_departure_date: str,
        payment_method_id: Optional[str] = None,
        confirmation: bool = False,
    ) -> dict:
        """Change a flight after an explicit customer confirmation."""
        if not confirmation:
            return {
                "success": False,
                "error": "explicit_confirmation_required",
                "message": "The customer must explicitly confirm the quoted change before it is submitted.",
            }
        body: Dict[str, Any] = {
            "current_flight_number": current_flight_number,
            "new_flight_number": new_flight_number,
            "new_departure_date": new_departure_date,
        }
        if payment_method_id is not None:
            body["payment_method_id"] = payment_method_id
        return self._request(
            "POST",
            f"/v1/reservations/{self._identifier(reservation_id)}/changes",
            body=body,
        )

    @is_tool(ToolType.WRITE)
    def cancel_reservation(
        self,
        reservation_id: str,
        confirmation: bool = False,
    ) -> dict:
        """Cancel a reservation after explicit customer confirmation."""
        if not confirmation:
            return {
                "success": False,
                "error": "explicit_confirmation_required",
                "message": "The customer must explicitly confirm cancellation before it is submitted.",
            }
        return self._request(
            "POST",
            f"/v1/reservations/{self._identifier(reservation_id)}/cancel",
            body={"confirmation": True},
        )

    @is_tool(ToolType.WRITE)
    def check_in(self, reservation_id: str) -> dict:
        """Check eligible passengers into a reservation and obtain boarding-pass data."""
        return self._request(
            "POST",
            f"/v1/reservations/{self._identifier(reservation_id)}/check-in",
            body={},
        )

    @is_tool(ToolType.WRITE)
    def add_feedback(
        self,
        reservation_id: str,
        flight_number: str,
        category: str,
        description: str,
    ) -> dict:
        """Record service or onboard feedback against a completed or disrupted flight."""
        return self._request(
            "POST",
            f"/v1/reservations/{self._identifier(reservation_id)}/feedback",
            body={
                "flight_number": flight_number,
                "category": category,
                "description": description,
            },
        )

    @is_tool(ToolType.READ)
    def review_compensation(
        self,
        reservation_id: str,
        flight_number: str,
        reason: str,
    ) -> dict:
        """Review compensation eligibility for a documented flight disruption."""
        return self._request(
            "POST",
            f"/v1/reservations/{self._identifier(reservation_id)}/compensation",
            body={
                "flight_number": flight_number,
                "reason": reason,
            },
        )

    @is_tool(ToolType.GENERIC)
    def transfer_to_human_agents(self, summary: str) -> dict:
        """Transfer the conversation to the appropriate specialist queue."""
        conversation_id = self._identifier(
            self.client_api.context.conversation_id
        )
        return self._request(
            "POST",
            f"/v1/conversations/{conversation_id}/transfers",
            body={"summary": summary},
        )
