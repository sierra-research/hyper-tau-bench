from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class APIErrorDetail(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: Optional[str] = None
    message: Optional[str] = None
    details: Optional[Any] = None


class APIError(BaseModel):
    model_config = ConfigDict(extra="allow")

    error: Optional[APIErrorDetail] = None


class Customer(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    full_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    verified_email: Optional[str] = None
    primary_phone_number: Optional[str] = None
    address: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class CustomerSearchResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    customer: Optional[Customer] = None
    id: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    matched_by: Optional[str] = None


class CustomerCollection(BaseModel):
    model_config = ConfigDict(extra="allow")

    customers: List[CustomerSearchResult] = Field(default_factory=list)


class Line(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    customer_id: Optional[str] = None
    phone_number: Optional[str] = None
    status: Optional[str] = None
    lifecycle_state: Optional[str] = None
    plan_id: Optional[str] = None
    plan_name: Optional[str] = None
    device_id: Optional[str] = None
    data_allowance_gb: Optional[Decimal] = None
    data_used_gb: Optional[Decimal] = None
    refueled_data_gb: Optional[Decimal] = None
    available_data_gb: Optional[Decimal] = None
    billing_cycle_start: Optional[date] = None
    billing_cycle_end: Optional[date] = None


class LineCollection(BaseModel):
    model_config = ConfigDict(extra="allow")

    lines: List[Line] = Field(default_factory=list)


class Device(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    line_id: Optional[str] = None
    customer_id: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    operating_system: Optional[str] = None
    phone_number: Optional[str] = None
    status: Optional[str] = None
    imei: Optional[str] = None
    esim: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None


class DeviceCollection(BaseModel):
    model_config = ConfigDict(extra="allow")

    devices: List[Device] = Field(default_factory=list)


class Bill(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    customer_id: Optional[str] = None
    line_id: Optional[str] = None
    invoice_number: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[Decimal] = None
    balance: Optional[Decimal] = None
    due_date: Optional[date] = None
    issued_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    currency: Optional[str] = None


class BillCollection(BaseModel):
    model_config = ConfigDict(extra="allow")

    bills: List[Bill] = Field(default_factory=list)


class Plan(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    monthly_price: Optional[Decimal] = None
    price: Optional[Decimal] = None
    currency: Optional[str] = None
    data_allowance_gb: Optional[Decimal] = None
    hotspot_allowance_gb: Optional[Decimal] = None
    unlimited_data: Optional[bool] = None
    eligible: Optional[bool] = None
    features: Optional[List[str]] = None


class PlanCollection(BaseModel):
    model_config = ConfigDict(extra="allow")

    plans: List[Plan] = Field(default_factory=list)


class PlanQuote(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    customer_id: Optional[str] = None
    line_id: Optional[str] = None
    plan_id: Optional[str] = None
    plan_name: Optional[str] = None
    current_plan_id: Optional[str] = None
    monthly_price: Optional[Decimal] = None
    new_monthly_price: Optional[Decimal] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class Refuel(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    customer_id: Optional[str] = None
    line_id: Optional[str] = None
    receipt_number: Optional[str] = None
    status: Optional[str] = None
    amount_gb: Optional[Decimal] = None
    data_gb: Optional[Decimal] = None
    price: Optional[Decimal] = None
    currency: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class RefuelCollection(BaseModel):
    model_config = ConfigDict(extra="allow")

    refuels: List[Refuel] = Field(default_factory=list)


class Usage(BaseModel):
    model_config = ConfigDict(extra="allow")

    line_id: str
    data_allowance_gb: Optional[Decimal] = None
    base_allowance_gb: Optional[Decimal] = None
    refueled_data_gb: Optional[Decimal] = None
    total_available_gb: Optional[Decimal] = None
    used_data_gb: Optional[Decimal] = None
    remaining_data_gb: Optional[Decimal] = None
    cycle_start: Optional[date] = None
    cycle_end: Optional[date] = None
    unit: Optional[str] = None


class Account(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    customer_id: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    customers: Optional[List[Customer]] = None
    lines: Optional[List[Line]] = None
    devices: Optional[List[Device]] = None
    bills: Optional[List[Bill]] = None


class Quote(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    customer_id: Optional[str] = None
    line_id: Optional[str] = None
    kind: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class Transfer(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    conversation_id: Optional[str] = None
    status: Optional[str] = None
    summary: Optional[str] = None
    created_at: Optional[datetime] = None


class GenericResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    detail: Optional[str] = None
    data: Optional[Any] = None


class APIResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    status_code: int
    body: Any = None
    headers: Dict[str, str] = Field(default_factory=dict)
    elapsed_seconds: Optional[float] = None
