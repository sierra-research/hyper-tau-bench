from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


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
    amount: Optional[float] = None
    currency: Optional[str] = None
    expiration_month: Optional[int] = None
    expiration_year: Optional[int] = None
    name: Optional[str] = None


class Passenger(BaseModel):
    model_config = ConfigDict(extra="allow")

    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    passenger_id: Optional[str] = None
    seat: Optional[str] = None


class Flight(BaseModel):
    model_config = ConfigDict(extra="allow")

    flight_number: Optional[str] = None
    flight_id: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    departure_date: Optional[str] = None
    arrival_date: Optional[str] = None
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    status: Optional[str] = None
    cabin: Optional[str] = None
    price: Optional[float] = None
    available_seats: Optional[int] = None
    seat: Optional[str] = None
    terminal: Optional[str] = None
    gate: Optional[str] = None


class Reservation(BaseModel):
    model_config = ConfigDict(extra="allow")

    reservation_id: Optional[str] = None
    confirmation_code: Optional[str] = None
    customer_id: Optional[str] = None
    status: Optional[str] = None
    cabin: Optional[str] = None
    trip_type: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    total_price: Optional[float] = None
    original_total: Optional[float] = None
    currency: Optional[str] = None
    passengers: List[Passenger] = Field(default_factory=list)
    flights: List[Flight] = Field(default_factory=list)
    payment_methods: List[PaymentMethod] = Field(default_factory=list)
    travel_insurance: Optional[bool] = None
    checked_bags: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class Customer(BaseModel):
    model_config = ConfigDict(extra="allow")

    customer_id: Optional[str] = None
    account_identifier: Optional[str] = None
    name: Optional[Name] = None
    address: Optional[Address] = None
    email: Optional[str] = None
    dob: Optional[str] = None
    payment_methods: List[PaymentMethod] = Field(default_factory=list)
    reservations: List[Reservation] = Field(default_factory=list)
    loyalty_status: Optional[str] = None
    loyalty_number: Optional[str] = None


class BookingSearch(BaseModel):
    model_config = ConfigDict(extra="allow")

    origin: Optional[str] = None
    destination: Optional[str] = None
    departure_date: Optional[str] = None
    return_date: Optional[str] = None
    passengers: Optional[int] = None
    adults: Optional[int] = None
    children: Optional[int] = None
    cabin: Optional[str] = None
    stops: Optional[int] = None


class CaseRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    description: Optional[str] = None
    customer_id: Optional[str] = None
    email: Optional[str] = None
    reservation_id: Optional[str] = None
    credit_card_id: Optional[str] = None
    gift_card_id: Optional[str] = None
    certificate_id: Optional[str] = None


class APIError(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: Optional[str] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class APIResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    status_code: Optional[int] = None
    body: Optional[Any] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    elapsed_seconds: Optional[float] = None


class FlightSearchResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    flights: List[Flight] = Field(default_factory=list)
    results: List[Flight] = Field(default_factory=list)
    search: Optional[BookingSearch] = None


class PricePreview(BaseModel):
    model_config = ConfigDict(extra="allow")

    old_total: Optional[float] = None
    new_total: Optional[float] = None
    difference_due: Optional[float] = None
    currency: Optional[str] = None
    flights: List[Flight] = Field(default_factory=list)


class PaymentAllocation(BaseModel):
    model_config = ConfigDict(extra="allow")

    credit_card_id: Optional[str] = None
    gift_card_id: Optional[str] = None
    certificate_id: Optional[str] = None
    credit_card_amount: Optional[float] = None
    gift_card_amount: Optional[float] = None
    certificate_amount: Optional[float] = None


class Feedback(BaseModel):
    model_config = ConfigDict(extra="allow")

    reservation_id: Optional[str] = None
    flight_number: Optional[str] = None
    category: Optional[str] = None
    message: Optional[str] = None
    details: Optional[str] = None


class TransferRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    summary: str


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: Optional[bool] = None
    message: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[APIError] = None
