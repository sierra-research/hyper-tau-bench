from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Address(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    name: Optional[str] = None
    label: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
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


class Customer(BaseModel):
    model_config = ConfigDict(extra="allow")

    customer_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    postal_code: Optional[str] = None
    zip_code: Optional[str] = None
    addresses: List[Address] = Field(default_factory=list)
    default_address_id: Optional[str] = None


class PaymentMethod(BaseModel):
    model_config = ConfigDict(extra="allow")

    payment_method_id: Optional[str] = None
    id: Optional[str] = None
    type: Optional[str] = None
    brand: Optional[str] = None
    last4: Optional[str] = None
    balance: Optional[float] = None
    available_balance: Optional[float] = None
    currency: Optional[str] = None


class OrderItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    item_id: Optional[str] = None
    line_id: Optional[str] = None
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    name: Optional[str] = None
    title: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    options: Dict[str, Any] = Field(default_factory=dict)
    variant: Optional[str] = None
    sku: Optional[str] = None
    selected: Optional[bool] = None


class CarrierEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: Optional[str] = None
    timestamp: Optional[str] = None
    location: Optional[str] = None
    location_note: Optional[str] = None
    photo_url: Optional[str] = None
    photo: Optional[str] = None
    signature: Optional[str] = None


class OrderMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    subject: Optional[str] = None
    body: Optional[str] = None
    timestamp: Optional[str] = None
    sent_at: Optional[str] = None
    event_type: Optional[str] = None


class Order(BaseModel):
    model_config = ConfigDict(extra="allow")

    order_id: str
    customer_id: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    purchase_date: Optional[str] = None
    updated_at: Optional[str] = None
    items: List[OrderItem] = Field(default_factory=list)
    shipping_address: Optional[Address] = None
    billing_address: Optional[Address] = None
    payments: List[PaymentMethod] = Field(default_factory=list)
    payment_methods: List[PaymentMethod] = Field(default_factory=list)
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    shipping: Optional[float] = None
    total: Optional[float] = None
    order_total: Optional[float] = None
    gift_message: Optional[str] = None
    carrier_events: List[CarrierEvent] = Field(default_factory=list)
    messages: List[OrderMessage] = Field(default_factory=list)
    return_request: Optional[Dict[str, Any]] = None
    exchange_request: Optional[Dict[str, Any]] = None
    return_draft: Optional[Dict[str, Any]] = None
    exchange_draft: Optional[Dict[str, Any]] = None


class ProductOption(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: Optional[str] = None
    value: Optional[str] = None
    price: Optional[float] = None


class Product(BaseModel):
    model_config = ConfigDict(extra="allow")

    product_id: Optional[str] = None
    name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    options: List[ProductOption] = Field(default_factory=list)
    variants: List[Dict[str, Any]] = Field(default_factory=list)


class APIErrorDetail(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: Optional[str] = None
    message: Optional[str] = None
    field: Optional[str] = None


class APIError(BaseModel):
    model_config = ConfigDict(extra="allow")

    error: Optional[APIErrorDetail] = None
    code: Optional[str] = None
    message: Optional[str] = None


class APIResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    status_code: int
    body: Any = None
    headers: Dict[str, str] = Field(default_factory=dict)
    elapsed_seconds: Optional[float] = None
