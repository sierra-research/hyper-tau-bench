from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Customer(StrictModel):
    id: Optional[str] = None
    customer_id: Optional[str] = None
    name: Optional[str] = None
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    verified_email: Optional[str] = None
    primary_phone_number: Optional[str] = None
    account_status: Optional[str] = None
    lines: Optional[List[Any]] = None


class CustomerSearchResult(StrictModel):
    customer: Optional[Customer] = None
    customer_id: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    match_type: Optional[str] = None


class Line(StrictModel):
    id: Optional[str] = None
    line_id: Optional[str] = None
    customer_id: Optional[str] = None
    phone_number: Optional[str] = None
    status: Optional[str] = None
    lifecycle_status: Optional[str] = None
    device_id: Optional[str] = None
    plan_id: Optional[str] = None
    plan: Optional[Any] = None
    data_allowance_gb: Optional[float] = None
    base_allowance_gb: Optional[float] = None
    used_data_gb: Optional[float] = None
    available_data_gb: Optional[float] = None
    refueled_data_gb: Optional[float] = None
    current_cycle_refuel_gb: Optional[float] = None
    refuel_limit_gb: Optional[float] = None
    remaining_refuel_gb: Optional[float] = None
    bills: Optional[List[Any]] = None


class Device(StrictModel):
    id: Optional[str] = None
    device_id: Optional[str] = None
    line_id: Optional[str] = None
    customer_id: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    operating_system: Optional[str] = None
    status: Optional[str] = None
    phone_number: Optional[str] = None


class Plan(StrictModel):
    id: Optional[str] = None
    plan_id: Optional[str] = None
    name: Optional[str] = None
    display_name: Optional[str] = None
    data_allowance_gb: Optional[float] = None
    data_gb: Optional[float] = None
    hotspot_allowance_gb: Optional[float] = None
    monthly_price: Optional[float] = None
    price: Optional[float] = None
    eligible: Optional[bool] = None
    description: Optional[str] = None


class PlanQuote(StrictModel):
    id: Optional[str] = None
    quote_id: Optional[str] = None
    line_id: Optional[str] = None
    plan_id: Optional[str] = None
    plan: Optional[Plan] = None
    monthly_price: Optional[float] = None
    calculated_monthly_price: Optional[float] = None
    status: Optional[str] = None
    expires_at: Optional[str] = None
    created_at: Optional[str] = None


class Bill(StrictModel):
    id: Optional[str] = None
    bill_id: Optional[str] = None
    customer_id: Optional[str] = None
    line_id: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[float] = None
    balance: Optional[float] = None
    due_date: Optional[str] = None
    issued_at: Optional[str] = None
    paid_at: Optional[str] = None


class Refuel(StrictModel):
    id: Optional[str] = None
    refuel_id: Optional[str] = None
    receipt_id: Optional[str] = None
    line_id: Optional[str] = None
    customer_id: Optional[str] = None
    amount_gb: Optional[float] = None
    data_gb: Optional[float] = None
    price: Optional[float] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class RefuelQuote(StrictModel):
    id: Optional[str] = None
    quote_id: Optional[str] = None
    line_id: Optional[str] = None
    amount_gb: Optional[float] = None
    data_gb: Optional[float] = None
    price: Optional[float] = None
    status: Optional[str] = None
    expires_at: Optional[str] = None
    created_at: Optional[str] = None


class ServiceRecovery(StrictModel):
    id: Optional[str] = None
    recovery_id: Optional[str] = None
    line_id: Optional[str] = None
    device_id: Optional[str] = None
    status: Optional[str] = None
    issue: Optional[str] = None
    resolution: Optional[str] = None
    created_at: Optional[str] = None


class RoamingStatus(StrictModel):
    line_id: Optional[str] = None
    enabled: Optional[bool] = None
    country: Optional[str] = None
    status: Optional[str] = None
    incident_id: Optional[str] = None


class ApiErrorDetail(StrictModel):
    code: Optional[str] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ApiError(StrictModel):
    error: Optional[ApiErrorDetail] = None


class ApiResponse(StrictModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    status_code: Optional[int] = None
    body: Optional[Any] = None
    headers: Optional[Dict[str, str]] = None
    elapsed_seconds: Optional[float] = None


class CustomerCollection(StrictModel):
    customers: List[CustomerSearchResult] = Field(default_factory=list)


class LineCollection(StrictModel):
    lines: List[Line] = Field(default_factory=list)


class PlanCollection(StrictModel):
    plans: List[Plan] = Field(default_factory=list)


class BillCollection(StrictModel):
    bills: List[Bill] = Field(default_factory=list)


class RefuelCollection(StrictModel):
    refuels: List[Refuel] = Field(default_factory=list)
