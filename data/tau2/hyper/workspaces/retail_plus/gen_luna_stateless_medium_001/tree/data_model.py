from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Address(StrictModel):
    id: Optional[str] = None
    name: Optional[str] = None
    label: Optional[str] = None
    street: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    is_default: Optional[bool] = None
    delivery_instructions: Optional[str] = None


class Customer(StrictModel):
    id: Optional[str] = None
    customer_id: Optional[str] = None
    account_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    postal_code: Optional[str] = None
    zip_code: Optional[str] = None
    addresses: Optional[List[Address]] = None
    default_address_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PaymentMethod(StrictModel):
    id: Optional[str] = None
    payment_method_id: Optional[str] = None
    type: Optional[str] = None
    brand: Optional[str] = None
    last4: Optional[str] = None
    ending: Optional[str] = None
    balance: Optional[float] = None
    available_balance: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None


class Payment(StrictModel):
    id: Optional[str] = None
    payment_id: Optional[str] = None
    payment_method_id: Optional[str] = None
    method_id: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    refunded_amount: Optional[float] = None


class OrderItem(StrictModel):
    id: Optional[str] = None
    item_id: Optional[str] = None
    product_id: Optional[str] = None
    sku: Optional[str] = None
    product_name: Optional[str] = None
    name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    currency: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    variant: Optional[Dict[str, Any]] = None
    attributes: Optional[Dict[str, Any]] = None


class CarrierEvent(StrictModel):
    id: Optional[str] = None
    event: Optional[str] = None
    status: Optional[str] = None
    timestamp: Optional[str] = None
    location: Optional[str] = None
    location_note: Optional[str] = None
    description: Optional[str] = None
    photo_url: Optional[str] = None
    photo: Optional[str] = None
    signed_by: Optional[str] = None


class ReturnItem(StrictModel):
    item_id: Optional[str] = None
    order_item_id: Optional[str] = None
    quantity: Optional[int] = None
    reason: Optional[str] = None


class ExchangeItem(StrictModel):
    item_id: Optional[str] = None
    order_item_id: Optional[str] = None
    quantity: Optional[int] = None
    replacement: Optional[Dict[str, Any]] = None
    replacement_item: Optional[Dict[str, Any]] = None
    price_difference: Optional[float] = None


class Order(StrictModel):
    id: Optional[str] = None
    order_id: Optional[str] = None
    customer_id: Optional[str] = None
    number: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    purchase_date: Optional[str] = None
    delivered_at: Optional[str] = None
    total: Optional[float] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    shipping: Optional[float] = None
    currency: Optional[str] = None
    items: Optional[List[OrderItem]] = None
    order_items: Optional[List[OrderItem]] = None
    shipping_address: Optional[Address] = None
    billing_address: Optional[Address] = None
    payments: Optional[List[Payment]] = None
    payment_history: Optional[List[Payment]] = None
    carrier_events: Optional[List[CarrierEvent]] = None
    delivery_events: Optional[List[CarrierEvent]] = None
    gift_message: Optional[str] = None
    receipt_subject: Optional[str] = None
    return_request: Optional[Dict[str, Any]] = None
    exchange_request: Optional[Dict[str, Any]] = None
    return_items: Optional[List[ReturnItem]] = None
    exchange_items: Optional[List[ExchangeItem]] = None
    draft: Optional[Dict[str, Any]] = None
    message_events: Optional[List[Dict[str, Any]]] = None


class CustomerSearchResult(StrictModel):
    customer_id: str


class APIErrorDetail(StrictModel):
    code: Optional[str] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class APIError(StrictModel):
    error: Optional[APIErrorDetail] = None
    code: Optional[str] = None
    message: Optional[str] = None


class MessageEvent(StrictModel):
    id: Optional[str] = None
    subject: Optional[str] = None
    timestamp: Optional[str] = None
    body: Optional[str] = None
    order_id: Optional[str] = None
    event_type: Optional[str] = None


class Receipt(StrictModel):
    order_id: Optional[str] = None
    lines: Optional[List[OrderItem]] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    currency: Optional[str] = None
    subject: Optional[str] = None
    purchase_date: Optional[str] = None


class ReturnRequest(StrictModel):
    order_id: Optional[str] = None
    items: List[ReturnItem] = Field(default_factory=list)
    payment_method_id: Optional[str] = None
    refund_payment_method_id: Optional[str] = None
    status: Optional[str] = None
    confirmed: Optional[bool] = None


class ExchangeRequest(StrictModel):
    order_id: Optional[str] = None
    items: List[ExchangeItem] = Field(default_factory=list)
    payment_method_id: Optional[str] = None
    status: Optional[str] = None
    confirmed: Optional[bool] = None
    price_difference: Optional[float] = None


JSONValue = Union[
    None,
    bool,
    int,
    float,
    str,
    List["JSONValue"],
    Dict[str, "JSONValue"],
]
