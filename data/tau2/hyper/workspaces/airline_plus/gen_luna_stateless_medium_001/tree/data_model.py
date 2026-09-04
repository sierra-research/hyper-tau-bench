from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class Address(BaseModel):
    model_config = ConfigDict(extra="allow")

    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


class Name(BaseModel):
    model_config = ConfigDict(extra="allow")

    first: Optional[str] = None
    middle: Optional[str] = None
    last: Optional[str] = None


class PaymentMethod(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    type: Optional[str] = None
    last_four: Optional[str] = None
    balance: Optional[float] = None
    available_balance: Optional[float] = None
    currency: Optional[str] = None


class Customer(BaseModel):
    model_config = ConfigDict(extra="allow")

    customer_id: str
    name: Optional[Name] = None
    address: Optional[Address] = None
    email: Optional[str] = None
    dob: Optional[str] = None
    payment_methods: List[PaymentMethod] = []
    reservations: List[Dict[str, Any]] = []


class Flight(BaseModel):
    model_config = ConfigDict(extra="allow")

    flight_id: Optional[str] = None
    flight_number: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    departure_date: Optional[str] = None
    departure_time: Optional[str] = None
    arrival_date: Optional[str] = None
    arrival_time: Optional[str] = None
    status: Optional[str] = None
    cabin: Optional[str] = None
    price: Optional[float] = None
    available_seats: Optional[int] = None


class Passenger(BaseModel):
    model_config = ConfigDict(extra="allow")

    passenger_id: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    seat: Optional[str] = None


class Reservation(BaseModel):
    model_config = ConfigDict(extra="allow")

    reservation_id: str
    customer_id: Optional[str] = None
    flights: List[Flight] = []
    passengers: List[Passenger] = []
    cabin: Optional[str] = None
    status: Optional[str] = None
    total_price: Optional[float] = None
    original_total: Optional[float] = None
    travel_insurance: Optional[bool] = None
    checked_bags: Optional[Dict[str, int]] = None
    payment_methods: List[PaymentMethod] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SearchResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    flights: List[Flight] = []
    origin: Optional[str] = None
    destination: Optional[str] = None
    departure_date: Optional[str] = None
    return_date: Optional[str] = None
    cabin: Optional[str] = None
    passenger_count: Optional[int] = None


class PricingPreview(BaseModel):
    model_config = ConfigDict(extra="allow")

    reservation_id: Optional[str] = None
    old_total: Optional[float] = None
    new_total: Optional[float] = None
    difference: Optional[float] = None
    currency: Optional[str] = None
    details: List[Dict[str, Any]] = []


class APIError(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: Optional[str] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class APIResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    status_code: Optional[int] = None
    body: Optional[Any] = None
    headers: Dict[str, str] = {}
    elapsed_seconds: Optional[float] = None
