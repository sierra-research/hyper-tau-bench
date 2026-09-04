"""Agent tools backed by the airline customer-service REST API."""

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
        response = self.client_api.request(
            method,
            path,
            query=query,
            body=body,
        )
        response.raise_for_status()
        return response.body

    @is_tool(ToolType.READ)
    def get_customer(self, customer_id: str) -> Any:
        """Retrieve a customer profile, saved payment methods, and reservations."""
        return self._request("GET", f"/v1/customers/{quote(customer_id, safe='')}")

    @is_tool(ToolType.READ)
    def get_reservation(self, reservation_id: str) -> Any:
        """Retrieve a reservation by confirmation code."""
        return self._request("GET", f"/v1/reservations/{quote(reservation_id, safe='')}")

    @is_tool(ToolType.READ)
    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        cabin: str,
        passengers: int = 1,
        return_date: Optional[str] = None,
    ) -> Any:
        """Search available flights for a specified itinerary."""
        query: Dict[str, Any] = {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "cabin": cabin,
            "passengers": passengers,
        }
        if return_date is not None:
            query["return_date"] = return_date
        return self._request("GET", "/v1/flights", query=query)

    @is_tool(ToolType.READ)
    def get_flight_status(self, flight_number: str, travel_date: str) -> Any:
        """Retrieve the operational status of a flight on a date."""
        return self._request(
            "GET",
            f"/v1/flights/{quote(flight_number, safe='')}/status",
            query={"date": travel_date},
        )

    @is_tool(ToolType.READ)
    def price_reservation_change(
        self,
        reservation_id: str,
        changes: Dict[str, Any],
    ) -> Any:
        """Preview the price of a proposed reservation change."""
        return self._request(
            "POST",
            f"/v1/reservations/{quote(reservation_id, safe='')}/price-change",
            body={"changes": changes},
        )

    @is_tool(ToolType.WRITE)
    def change_reservation(
        self,
        reservation_id: str,
        changes: Dict[str, Any],
        payment_method_id: Optional[str] = None,
    ) -> Any:
        """Apply a confirmed reservation change."""
        body: Dict[str, Any] = {"changes": changes}
        if payment_method_id is not None:
            body["payment_method_id"] = payment_method_id
        return self._request(
            "POST",
            f"/v1/reservations/{quote(reservation_id, safe='')}/change",
            body=body,
        )

    @is_tool(ToolType.WRITE)
    def create_reservation(
        self,
        customer_id: str,
        itinerary: Dict[str, Any],
        passengers: list,
        payment: Dict[str, Any],
    ) -> Any:
        """Create a reservation from a selected itinerary and passenger data."""
        return self._request(
            "POST",
            "/v1/reservations",
            body={
                "customer_id": customer_id,
                "itinerary": itinerary,
                "passengers": passengers,
                "payment": payment,
            },
        )

    @is_tool(ToolType.WRITE)
    def add_checked_bags(self, reservation_id: str, bags: Dict[str, int]) -> Any:
        """Add explicitly requested checked bags to a reservation."""
        return self._request(
            "POST",
            f"/v1/reservations/{quote(reservation_id, safe='')}/bags",
            body={"bags": bags},
        )

    @is_tool(ToolType.WRITE)
    def select_seats(self, reservation_id: str, seats: Dict[str, str]) -> Any:
        """Assign selected seats to passengers on a reservation."""
        return self._request(
            "POST",
            f"/v1/reservations/{quote(reservation_id, safe='')}/seats",
            body={"seats": seats},
        )

    @is_tool(ToolType.WRITE)
    def review_compensation(self, reservation_id: str, reason: str) -> Any:
        """Review compensation eligibility for a disruption."""
        return self._request(
            "POST",
            f"/v1/reservations/{quote(reservation_id, safe='')}/compensation-review",
            body={"reason": reason},
        )

    @is_tool(ToolType.WRITE)
    def save_service_feedback(
        self,
        reservation_id: str,
        flight_number: str,
        category: str,
        description: str,
    ) -> Any:
        """Record customer feedback about a flight or service experience."""
        return self._request(
            "POST",
            f"/v1/reservations/{quote(reservation_id, safe='')}/feedback",
            body={
                "flight_number": flight_number,
                "category": category,
                "description": description,
            },
        )

    @is_tool(ToolType.GENERIC)
    def transfer_to_human_agents(self, summary: str) -> Any:
        """Transfer the conversation to a specialist or human support queue."""
        conversation_id = quote(
            self.client_api.context.conversation_id,
            safe="",
        )
        return self._request(
            "POST",
            f"/v1/conversations/{conversation_id}/transfers",
            body={"summary": summary},
        )
