"""Airline+ Client API schemas, operations, and response adapters."""

from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import Field

from tau2.hyper.client_api.catalog import (
    APIModel,
    ClientOperation,
    ConversationTransferReceipt,
    ConversationTransferRequest,
    OperationInvocation,
)

FlightType = Literal["round_trip", "one_way"]
CabinClass = Literal["business", "economy", "basic_economy"]
Insurance = Literal["yes", "no"]


class AirportCode(APIModel):
    iata: str
    city: str


class AirportCollection(APIModel):
    airports: list[AirportCode]


class ItinerarySearchQuery(APIModel):
    origin: str = Field(min_length=3, max_length=3)
    destination: str = Field(min_length=3, max_length=3)
    departure_date: str = Field(min_length=1)
    stops: Literal[0, 1]


class CabinOffer(APIModel):
    cabin: CabinClass
    available_seats: int
    price: int


class FlightSegment(APIModel):
    flight_number: str
    origin: str
    destination: str
    status: Literal["available"]
    scheduled_departure_time_est: str
    scheduled_arrival_time_est: str
    departure_date: str
    cabin_offers: list[CabinOffer]


class Itinerary(APIModel):
    segments: list[FlightSegment] = Field(min_length=1)


class ItineraryCollection(APIModel):
    itineraries: list[Itinerary]


class FlightInstanceStatus(APIModel):
    flight_number: str
    date: str
    status: Literal["available", "on time", "flying", "landed", "cancelled", "delayed"]


class FlightInfo(APIModel):
    flight_number: str
    date: str = Field(min_length=1)


class Passenger(APIModel):
    first_name: str
    last_name: str
    dob: str


class Payment(APIModel):
    payment_id: str
    amount: int


class TripRequest(APIModel):
    origin: str = Field(min_length=3, max_length=3)
    destination: str = Field(min_length=3, max_length=3)
    trip_type: FlightType
    cabin: CabinClass
    segments: list[FlightInfo] = Field(min_length=1)


class BaggageSelection(APIModel):
    total_bags: int = Field(ge=0)
    paid_bags: int = Field(ge=0)


class ReservationRequest(APIModel):
    customer_id: str = Field(min_length=1)
    trip: TripRequest
    passengers: list[Passenger] = Field(min_length=1)
    payment_methods: list[Payment]
    baggage: BaggageSelection
    insurance: Insurance


class BaggageUpdateRequest(BaggageSelection):
    payment_method_id: str = Field(min_length=1)


class ItineraryUpdateRequest(APIModel):
    cabin: CabinClass
    segments: list[FlightInfo] = Field(min_length=1)
    payment_method_id: str = Field(min_length=1)


class PassengerUpdateRequest(APIModel):
    passengers: list[Passenger] = Field(min_length=1)


class Name(APIModel):
    first_name: str
    last_name: str


class Address(APIModel):
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    country: str
    region: str
    postal_code: str


class PaymentMethodBase(APIModel):
    source: str
    id: str


class CreditCard(PaymentMethodBase):
    source: Literal["credit_card"]
    brand: str
    last_four: str


class GiftCard(PaymentMethodBase):
    source: Literal["gift_card"]
    amount: float


class Certificate(PaymentMethodBase):
    source: Literal["certificate"]
    amount: float


PaymentMethod = CreditCard | GiftCard | Certificate


class Customer(APIModel):
    customer_id: str
    name: Name
    address: Address
    email: str
    dob: str
    payment_methods: list[PaymentMethod]
    saved_passengers: list[Passenger]
    membership: Literal["gold", "silver", "regular"]
    reservation_ids: list[str]


class ReservationSegment(APIModel):
    flight_number: str
    origin: str
    destination: str
    date: str
    price: int


class ReservationTrip(APIModel):
    origin: str
    destination: str
    trip_type: FlightType
    cabin: CabinClass
    segments: list[ReservationSegment]


class Reservation(APIModel):
    reservation_id: str
    customer_id: str
    trip: ReservationTrip
    passengers: list[Passenger]
    payments: list[Payment]
    created_at: str
    baggage: BaggageSelection
    insurance: Insurance
    status: Optional[Literal["cancelled"]] = None


class ReservationCancellationResult(APIModel):
    reservation_id: str
    status: Literal["cancelled"]
    payments: list[Payment]


class ReservationBaggageResult(APIModel):
    reservation_id: str
    baggage: BaggageSelection
    payments: list[Payment]


class ReservationItineraryResult(APIModel):
    reservation_id: str
    trip: ReservationTrip
    payments: list[Payment]


class ReservationPassengersResult(APIModel):
    reservation_id: str
    passengers: list[Passenger]


class CertificateRequest(APIModel):
    amount: int = Field(gt=0)


class CertificateResult(APIModel):
    certificate_id: str
    customer_id: str
    amount: int


def _data(value: Any) -> dict[str, Any]:
    """Return a JSON-shaped mapping from a private reference model."""

    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value)


def _passenger(value: Any) -> dict[str, Any]:
    item = _data(value)
    return {
        "first_name": item["first_name"],
        "last_name": item["last_name"],
        "dob": item["dob"],
    }


def _available_segment(value: Any, departure_date: str) -> dict[str, Any]:
    item = _data(value)
    return {
        "flight_number": item["flight_number"],
        "origin": item["origin"],
        "destination": item["destination"],
        "status": item["status"],
        "scheduled_departure_time_est": item["scheduled_departure_time_est"],
        "scheduled_arrival_time_est": item["scheduled_arrival_time_est"],
        "departure_date": item.get("date") or departure_date,
        "cabin_offers": [
            {
                "cabin": cabin,
                "available_seats": available_seats,
                "price": item["prices"][cabin],
            }
            for cabin, available_seats in item["available_seats"].items()
        ],
    }


def _adapt_customer_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    customer = _data(result)
    return {
        "customer_id": customer["user_id"],
        "name": {
            "first_name": customer["name"]["first_name"],
            "last_name": customer["name"]["last_name"],
        },
        "address": {
            "address_line_1": customer["address"]["address1"],
            "address_line_2": customer["address"].get("address2"),
            "city": customer["address"]["city"],
            "country": customer["address"]["country"],
            "region": customer["address"]["state"],
            "postal_code": customer["address"]["zip"],
        },
        "email": customer["email"],
        "dob": customer["dob"],
        "payment_methods": [
            {
                field: payment_method[field]
                for field in ("source", "id", "brand", "last_four", "amount")
                if field in payment_method
            }
            for payment_method in customer["payment_methods"].values()
        ],
        "saved_passengers": [
            _passenger(passenger) for passenger in customer["saved_passengers"]
        ],
        "membership": customer["membership"],
        "reservation_ids": customer["reservations"],
    }


def _adapt_reservation_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    reservation = _data(result)
    return {
        "reservation_id": reservation["reservation_id"],
        "customer_id": reservation["user_id"],
        "trip": _reservation_trip(reservation),
        "passengers": [
            _passenger(passenger) for passenger in reservation["passengers"]
        ],
        "payments": _reservation_payments(reservation),
        "created_at": reservation["created_at"],
        "baggage": _reservation_baggage(reservation),
        "insurance": reservation["insurance"],
        "status": reservation.get("status"),
    }


def _reservation_trip(reservation: dict[str, Any]) -> dict[str, Any]:
    return {
        "origin": reservation["origin"],
        "destination": reservation["destination"],
        "trip_type": reservation["flight_type"],
        "cabin": reservation["cabin"],
        "segments": [
            {
                "flight_number": segment["flight_number"],
                "origin": segment["origin"],
                "destination": segment["destination"],
                "date": segment["date"],
                "price": segment["price"],
            }
            for segment in reservation["flights"]
        ],
    }


def _reservation_payments(reservation: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "payment_id": payment["payment_id"],
            "amount": payment["amount"],
        }
        for payment in reservation["payment_history"]
    ]


def _reservation_baggage(reservation: dict[str, Any]) -> dict[str, int]:
    return {
        "total_bags": reservation["total_baggages"],
        "paid_bags": reservation["nonfree_baggages"],
    }


def _adapt_reservation_cancellation_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    reservation = _data(result)
    return {
        "reservation_id": reservation["reservation_id"],
        "status": reservation["status"],
        "payments": _reservation_payments(reservation),
    }


def _adapt_reservation_baggage_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    reservation = _data(result)
    return {
        "reservation_id": reservation["reservation_id"],
        "baggage": _reservation_baggage(reservation),
        "payments": _reservation_payments(reservation),
    }


def _adapt_reservation_itinerary_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    reservation = _data(result)
    return {
        "reservation_id": reservation["reservation_id"],
        "trip": _reservation_trip(reservation),
        "payments": _reservation_payments(reservation),
    }


def _adapt_reservation_passengers_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    reservation = _data(result)
    return {
        "reservation_id": reservation["reservation_id"],
        "passengers": [
            _passenger(passenger) for passenger in reservation["passengers"]
        ],
    }


def _adapt_airports_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    return {
        "airports": [
            {"iata": airport["iata"], "city": airport["city"]}
            for value in result
            if (airport := _data(value))
        ]
    }


def _adapt_itineraries_response(
    invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    if invocation.tool_name == "search_direct_flight":
        return {
            "itineraries": [
                {"segments": [_available_segment(flight, invocation.arguments["date"])]}
                for flight in result
            ]
        }
    return {
        "itineraries": [
            {
                "segments": [
                    _available_segment(flight, invocation.arguments["date"])
                    for flight in pair
                ]
            }
            for pair in result
        ]
    }


def _adapt_flight_instance_response(
    invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    return {
        "flight_number": invocation.arguments["flight_number"],
        "date": invocation.arguments["date"],
        "status": result,
    }


def _adapt_certificate_response(
    invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    match = re.search(r"Certificate (\S+) added", result)
    if match is None:
        raise ValueError("Certificate response did not contain an identifier")
    return {
        "certificate_id": match.group(1),
        "customer_id": invocation.arguments["user_id"],
        "amount": invocation.arguments["amount"],
    }


def operations() -> tuple[ClientOperation, ...]:
    return (
        ClientOperation(
            "GET",
            "/v1/customers/{customer_id}",
            "getCustomer",
            "Get a customer",
            "Return one airline customer, including reservations and payment methods.",
            Customer,
            lambda path, _query, _body: OperationInvocation(
                "get_user_details", {"user_id": path["customer_id"]}
            ),
            response_adapter=_adapt_customer_response,
        ),
        ClientOperation(
            "POST",
            "/v1/customers/{customer_id}/certificates",
            "createCustomerCertificate",
            "Create a customer certificate",
            "Issue a travel certificate with a server-owned identifier to one customer.",
            CertificateResult,
            lambda path, _query, body: OperationInvocation(
                "send_certificate",
                {"user_id": path["customer_id"], "amount": body.amount},
            ),
            body_type=CertificateRequest,
            success_status=201,
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            response_adapter=_adapt_certificate_response,
            reference_tool_names=("send_certificate",),
        ),
        ClientOperation(
            "GET",
            "/v1/airports",
            "listAirports",
            "List airports",
            "Return the airports supported by the airline.",
            AirportCollection,
            lambda _path, _query, _body: OperationInvocation("list_all_airports", {}),
            response_adapter=_adapt_airports_response,
        ),
        ClientOperation(
            "GET",
            "/v1/flight-itineraries",
            "searchFlightItineraries",
            "Search flight itineraries",
            "Search itineraries for an origin, destination, departure date, and requested stop count.",
            ItineraryCollection,
            lambda _path, query, _body: OperationInvocation(
                "search_direct_flight" if query.stops == 0 else "search_onestop_flight",
                {
                    "origin": query.origin,
                    "destination": query.destination,
                    "date": query.departure_date,
                },
            ),
            query_type=ItinerarySearchQuery,
            response_adapter=_adapt_itineraries_response,
        ),
        ClientOperation(
            "GET",
            "/v1/flights/{flight_number}/instances/{date}",
            "getFlightInstance",
            "Get a flight instance",
            "Return the operating status of one flight on one date.",
            FlightInstanceStatus,
            lambda path, _query, _body: OperationInvocation(
                "get_flight_status",
                {"flight_number": path["flight_number"], "date": path["date"]},
            ),
            response_adapter=_adapt_flight_instance_response,
        ),
        ClientOperation(
            "POST",
            "/v1/reservations",
            "createReservation",
            "Create a reservation",
            "Create and pay for a reservation using the complete selected itinerary, passengers, baggage, and insurance.",
            Reservation,
            lambda _path, _query, body: OperationInvocation(
                "book_reservation",
                {
                    "user_id": body.customer_id,
                    "origin": body.trip.origin,
                    "destination": body.trip.destination,
                    "flight_type": body.trip.trip_type,
                    "cabin": body.trip.cabin,
                    "flights": [
                        {
                            "flight_number": item.flight_number,
                            "date": item.date,
                        }
                        for item in body.trip.segments
                    ],
                    "passengers": [
                        {
                            "first_name": item.first_name,
                            "last_name": item.last_name,
                            "dob": item.dob,
                        }
                        for item in body.passengers
                    ],
                    "payment_methods": [
                        {
                            "payment_id": item.payment_id,
                            "amount": item.amount,
                        }
                        for item in body.payment_methods
                    ],
                    "total_baggages": body.baggage.total_bags,
                    "nonfree_baggages": body.baggage.paid_bags,
                    "insurance": body.insurance,
                },
            ),
            body_type=ReservationRequest,
            success_status=201,
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            response_adapter=_adapt_reservation_response,
            reference_tool_names=("book_reservation",),
        ),
        ClientOperation(
            "GET",
            "/v1/reservations/{reservation_id}",
            "getReservation",
            "Get a reservation",
            "Return one reservation and its current itinerary, passengers, baggage, and payments.",
            Reservation,
            lambda path, _query, _body: OperationInvocation(
                "get_reservation_details",
                {"reservation_id": path["reservation_id"]},
            ),
            response_adapter=_adapt_reservation_response,
        ),
        ClientOperation(
            "POST",
            "/v1/reservations/{reservation_id}/cancellations",
            "createReservationCancellation",
            "Cancel a reservation",
            "Create a cancellation for one reservation.",
            ReservationCancellationResult,
            lambda path, _query, _body: OperationInvocation(
                "cancel_reservation", {"reservation_id": path["reservation_id"]}
            ),
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            response_adapter=_adapt_reservation_cancellation_response,
        ),
        ClientOperation(
            "PUT",
            "/v1/reservations/{reservation_id}/baggage",
            "replaceReservationBaggage",
            "Replace reservation baggage",
            "Replace the complete baggage selection for one reservation.",
            ReservationBaggageResult,
            lambda path, _query, body: OperationInvocation(
                "update_reservation_baggages",
                {
                    "reservation_id": path["reservation_id"],
                    "total_baggages": body.total_bags,
                    "nonfree_baggages": body.paid_bags,
                    "payment_id": body.payment_method_id,
                },
            ),
            body_type=BaggageUpdateRequest,
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            response_adapter=_adapt_reservation_baggage_response,
        ),
        ClientOperation(
            "PUT",
            "/v1/reservations/{reservation_id}/itinerary",
            "replaceReservationItinerary",
            "Replace a reservation itinerary",
            "Replace the complete itinerary and cabin for one reservation.",
            ReservationItineraryResult,
            lambda path, _query, body: OperationInvocation(
                "update_reservation_flights",
                {
                    "reservation_id": path["reservation_id"],
                    "cabin": body.cabin,
                    "flights": [
                        {
                            "flight_number": item.flight_number,
                            "date": item.date,
                        }
                        for item in body.segments
                    ],
                    "payment_id": body.payment_method_id,
                },
            ),
            body_type=ItineraryUpdateRequest,
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            response_adapter=_adapt_reservation_itinerary_response,
            reference_tool_names=("update_reservation_flights",),
        ),
        ClientOperation(
            "PUT",
            "/v1/reservations/{reservation_id}/passengers",
            "replaceReservationPassengers",
            "Replace reservation passengers",
            "Replace the complete passenger details for one reservation.",
            ReservationPassengersResult,
            lambda path, _query, body: OperationInvocation(
                "update_reservation_passengers",
                {
                    "reservation_id": path["reservation_id"],
                    "passengers": [
                        {
                            "first_name": item.first_name,
                            "last_name": item.last_name,
                            "dob": item.dob,
                        }
                        for item in body.passengers
                    ],
                },
            ),
            body_type=PassengerUpdateRequest,
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            response_adapter=_adapt_reservation_passengers_response,
        ),
        ClientOperation(
            "POST",
            "/v1/conversations/{conversation_id}/transfers",
            "createConversationTransfer",
            "Transfer a conversation to a human agent",
            "Create a live transfer of one active conversation to a human support agent. The conversation transcript and routing context are attached automatically.",
            ConversationTransferReceipt,
            lambda _path, _query, body: OperationInvocation(
                "transfer_to_human_agents", {"summary": body.summary}
            ),
            body_type=ConversationTransferRequest,
            success_status=201,
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            execution="conversation_transfer",
        ),
    )
