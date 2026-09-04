"""Retail+ Client API schemas, operations, and response adapters."""

from __future__ import annotations

import json
from typing import Any, Literal, Optional

from pydantic import Field, model_validator

from tau2.hyper.client_api.catalog import (
    APIModel,
    ClientOperation,
    ConversationTransferReceipt,
    ConversationTransferRequest,
    OperationInvocation,
)


class RetailCustomerSearchRequest(APIModel):
    """Provide email alone or a complete name-and-postal-code combination."""

    email: Optional[str] = Field(default=None, min_length=1)
    first_name: Optional[str] = Field(default=None, min_length=1)
    last_name: Optional[str] = Field(default=None, min_length=1)
    postal_code: Optional[str] = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_selector(self) -> "RetailCustomerSearchRequest":
        """Require email alone or the complete name-and-postal-code tuple."""

        name_fields = (self.first_name, self.last_name, self.postal_code)
        has_any_name_field = any(value is not None for value in name_fields)
        has_all_name_fields = all(value is not None for value in name_fields)
        if self.email is not None:
            if has_any_name_field:
                raise ValueError(
                    "email cannot be combined with name or postal-code fields"
                )
            return self
        if not has_all_name_fields:
            raise ValueError(
                "provide email or the complete first_name, last_name, and "
                "postal_code combination"
            )
        return self


class CustomerLookupResult(APIModel):
    customer_id: str


class Address(APIModel):
    address_line_1: str = Field(min_length=1)
    address_line_2: Optional[str] = None
    city: str = Field(min_length=1)
    region: str = Field(min_length=1)
    country: str = Field(min_length=1)
    postal_code: str = Field(min_length=1)


class ProductSummary(APIModel):
    product_id: str
    name: str


class ProductCollection(APIModel):
    products: list[ProductSummary]


class PaymentMethodRequest(APIModel):
    payment_method_id: str = Field(min_length=1)


class CancellationRequest(APIModel):
    reason: str = Field(min_length=1)


class ItemReplacement(APIModel):
    existing_item_id: str = Field(min_length=1)
    replacement_item_id: str = Field(min_length=1)


class ItemReplacementRequest(APIModel):
    replacements: list[ItemReplacement] = Field(min_length=1)
    payment_method_id: str = Field(min_length=1)


class ReturnRequest(APIModel):
    item_ids: list[str] = Field(min_length=1)
    refund_payment_method_id: str = Field(min_length=1)


class CustomerName(APIModel):
    first_name: str
    last_name: str


class PaymentMethodBase(APIModel):
    source: str
    id: str


class CreditCard(PaymentMethodBase):
    source: Literal["credit_card"]
    brand: str
    last_four: str


class GiftCard(PaymentMethodBase):
    source: Literal["gift_card"]
    balance: float


class Paypal(PaymentMethodBase):
    source: Literal["paypal"]


PaymentMethod = CreditCard | GiftCard | Paypal


class Customer(APIModel):
    customer_id: str
    name: CustomerName
    default_shipping_address: Address
    email: str
    payment_methods: list[PaymentMethod]
    order_ids: list[str]


class CustomerDefaultShippingAddress(APIModel):
    customer_id: str
    default_shipping_address: Address


class CatalogItem(APIModel):
    item_id: str
    options: dict[str, str]
    available: bool
    price: float


class Product(APIModel):
    name: str
    product_id: str
    items: list[CatalogItem]


class OrderFulfillment(APIModel):
    tracking_id: list[str]
    item_ids: list[str]


class OrderItem(APIModel):
    name: str
    product_id: str
    item_id: str
    price: float
    options: dict[str, str]


class OrderPayment(APIModel):
    transaction_type: Literal["payment", "refund"]
    amount: float
    payment_method_id: str


OrderStatus = Literal[
    "processed",
    "pending",
    "pending (items modified)",
    "delivered",
    "cancelled",
    "exchange requested",
    "return requested",
]


class OrderCancellation(APIModel):
    reason: Literal["no longer needed", "ordered by mistake"]


class OrderExchange(APIModel):
    replacements: list[ItemReplacement]
    payment_method_id: str
    price_difference: float


class OrderReturn(APIModel):
    item_ids: list[str]
    refund_payment_method_id: str


class Order(APIModel):
    order_id: str
    customer_id: str
    shipping_address: Address
    items: list[OrderItem]
    status: OrderStatus
    fulfillments: list[OrderFulfillment]
    payments: list[OrderPayment]
    cancellation: Optional[OrderCancellation] = None
    exchange: Optional[OrderExchange] = None
    return_request: Optional[OrderReturn] = None


class OrderShippingAddressResult(APIModel):
    order_id: str
    shipping_address: Address


class OrderPaymentMethodResult(APIModel):
    order_id: str
    payments: list[OrderPayment]


class OrderCancellationResult(APIModel):
    order_id: str
    status: Literal["cancelled"]
    cancellation: OrderCancellation
    payments: list[OrderPayment]


class OrderItemModificationResult(APIModel):
    order_id: str
    status: Literal["pending (items modified)"]
    items: list[OrderItem]
    payments: list[OrderPayment]


class OrderReturnResult(APIModel):
    order_id: str
    status: Literal["return requested"]
    return_request: OrderReturn


class OrderExchangeResult(APIModel):
    order_id: str
    status: Literal["exchange requested"]
    exchange: OrderExchange


def _data(value: Any) -> dict[str, Any]:
    """Return a JSON-shaped mapping from a private reference model."""

    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value)


def _address(value: Any) -> dict[str, Any]:
    address = _data(value)
    return {
        "address_line_1": address["address1"],
        "address_line_2": address["address2"],
        "city": address["city"],
        "country": address["country"],
        "region": address["state"],
        "postal_code": address["zip"],
    }


def _catalog_item(value: Any) -> dict[str, Any]:
    item = _data(value)
    return {
        "item_id": item["item_id"],
        "options": item["options"],
        "available": item["available"],
        "price": item["price"],
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
        "default_shipping_address": _address(customer["address"]),
        "email": customer["email"],
        "payment_methods": [
            {
                field: payment_method[field]
                for field in ("source", "id", "brand", "last_four", "balance")
                if field in payment_method
            }
            for payment_method in customer["payment_methods"].values()
        ],
        "order_ids": customer["orders"],
    }


def _adapt_customer_address_response(
    invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    customer = _data(result)
    return {
        "customer_id": invocation.arguments["user_id"],
        "default_shipping_address": _address(customer["address"]),
    }


def _adapt_product_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    product = _data(result)
    return {
        "product_id": product["product_id"],
        "name": product["name"],
        "items": [_catalog_item(item) for item in product["variants"].values()],
    }


def _adapt_item_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    return _catalog_item(result)


def _adapt_order_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    order = _data(result)
    return {
        "order_id": order["order_id"],
        "customer_id": order["user_id"],
        "shipping_address": _address(order["address"]),
        "items": _order_items(order),
        "status": order["status"],
        "fulfillments": _order_fulfillments(order),
        "payments": _order_payments(order),
        "cancellation": _order_cancellation(order),
        "exchange": _order_exchange(order),
        "return_request": _order_return(order),
    }


def _order_items(order: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            field: item[field]
            for field in ("name", "product_id", "item_id", "price", "options")
        }
        for item in order["items"]
    ]


def _order_fulfillments(order: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "tracking_id": fulfillment["tracking_id"],
            "item_ids": fulfillment["item_ids"],
        }
        for fulfillment in order["fulfillments"]
    ]


def _order_payments(order: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "transaction_type": payment["transaction_type"],
            "amount": payment["amount"],
            "payment_method_id": payment["payment_method_id"],
        }
        for payment in order["payment_history"]
    ]


def _order_cancellation(order: dict[str, Any]) -> Optional[dict[str, Any]]:
    reason = order.get("cancel_reason")
    return None if reason is None else {"reason": reason}


def _order_exchange(order: dict[str, Any]) -> Optional[dict[str, Any]]:
    existing_items = order.get("exchange_items")
    replacement_items = order.get("exchange_new_items")
    if existing_items is None or replacement_items is None:
        return None
    return {
        "replacements": [
            {
                "existing_item_id": existing_item_id,
                "replacement_item_id": replacement_item_id,
            }
            for existing_item_id, replacement_item_id in zip(
                existing_items, replacement_items
            )
        ],
        "payment_method_id": order["exchange_payment_method_id"],
        "price_difference": order["exchange_price_difference"],
    }


def _order_return(order: dict[str, Any]) -> Optional[dict[str, Any]]:
    item_ids = order.get("return_items")
    if item_ids is None:
        return None
    return {
        "item_ids": item_ids,
        "refund_payment_method_id": order["return_payment_method_id"],
    }


def _adapt_order_shipping_address_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    order = _data(result)
    return {
        "order_id": order["order_id"],
        "shipping_address": _address(order["address"]),
    }


def _adapt_order_payment_method_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    order = _data(result)
    return {"order_id": order["order_id"], "payments": _order_payments(order)}


def _adapt_order_cancellation_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    order = _data(result)
    return {
        "order_id": order["order_id"],
        "status": order["status"],
        "cancellation": _order_cancellation(order),
        "payments": _order_payments(order),
    }


def _adapt_order_item_modification_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    order = _data(result)
    return {
        "order_id": order["order_id"],
        "status": order["status"],
        "items": _order_items(order),
        "payments": _order_payments(order),
    }


def _adapt_order_return_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    order = _data(result)
    return {
        "order_id": order["order_id"],
        "status": order["status"],
        "return_request": _order_return(order),
    }


def _adapt_order_exchange_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, Any]:
    order = _data(result)
    return {
        "order_id": order["order_id"],
        "status": order["status"],
        "exchange": _order_exchange(order),
    }


def _address_arguments(id_name: str, id_value: str, body: Address) -> dict[str, Any]:
    return {
        id_name: id_value,
        "address1": body.address_line_1,
        "address2": body.address_line_2 or "",
        "city": body.city,
        "state": body.region,
        "country": body.country,
        "zip": body.postal_code,
    }


def _replacement_arguments(
    order_id: str, body: ItemReplacementRequest
) -> dict[str, Any]:
    return {
        "order_id": order_id,
        "item_ids": [item.existing_item_id for item in body.replacements],
        "new_item_ids": [item.replacement_item_id for item in body.replacements],
        "payment_method_id": body.payment_method_id,
    }


def _adapt_customer_search_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, str]:
    return {"customer_id": result}


def _adapt_product_collection_response(
    _invocation: OperationInvocation, result: Any
) -> dict[str, list[dict[str, str]]]:
    # The verified reference operation returns a JSON-encoded name-to-ID map.
    products = json.loads(result)
    return {
        "products": [
            {"product_id": product_id, "name": name}
            for name, product_id in products.items()
        ]
    }


def operations() -> tuple[ClientOperation, ...]:
    return (
        ClientOperation(
            "POST",
            "/v1/customers/search",
            "searchCustomers",
            "Search for a customer",
            "Find one customer using either an email address or the complete name-and-postal-code selector.",
            CustomerLookupResult,
            lambda _path, _query, body: OperationInvocation(
                "find_user_id_by_email",
                {"email": body.email},
            )
            if body.email is not None
            else OperationInvocation(
                "find_user_id_by_name_zip",
                {
                    "first_name": body.first_name,
                    "last_name": body.last_name,
                    "zip": body.postal_code,
                },
            ),
            body_type=RetailCustomerSearchRequest,
            response_adapter=_adapt_customer_search_response,
        ),
        ClientOperation(
            "GET",
            "/v1/customers/{customer_id}",
            "getCustomer",
            "Get a customer",
            "Return the customer identified by their customer ID.",
            Customer,
            lambda path, _query, _body: OperationInvocation(
                "get_user_details", {"user_id": path["customer_id"]}
            ),
            response_adapter=_adapt_customer_response,
        ),
        ClientOperation(
            "PUT",
            "/v1/customers/{customer_id}/default-shipping-address",
            "replaceCustomerDefaultShippingAddress",
            "Replace a customer's default shipping address",
            "Replace the complete default shipping address for one customer.",
            CustomerDefaultShippingAddress,
            lambda path, _query, body: OperationInvocation(
                "modify_user_address",
                _address_arguments("user_id", path["customer_id"], body),
            ),
            body_type=Address,
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            response_adapter=_adapt_customer_address_response,
        ),
        ClientOperation(
            "GET",
            "/v1/catalog/products",
            "listProducts",
            "List products",
            "Return product identifiers and names from the product catalog.",
            ProductCollection,
            lambda _path, _query, _body: OperationInvocation(
                "list_all_product_types", {}
            ),
            response_adapter=_adapt_product_collection_response,
        ),
        ClientOperation(
            "GET",
            "/v1/catalog/products/{product_id}",
            "getProduct",
            "Get a product",
            "Return one catalog product and its purchasable items.",
            Product,
            lambda path, _query, _body: OperationInvocation(
                "get_product_details", {"product_id": path["product_id"]}
            ),
            response_adapter=_adapt_product_response,
        ),
        ClientOperation(
            "GET",
            "/v1/catalog/items/{item_id}",
            "getCatalogItem",
            "Get a catalog item",
            "Return one purchasable catalog item.",
            CatalogItem,
            lambda path, _query, _body: OperationInvocation(
                "get_item_details", {"item_id": path["item_id"]}
            ),
            response_adapter=_adapt_item_response,
        ),
        ClientOperation(
            "GET",
            "/v1/orders/{order_id}",
            "getOrder",
            "Get an order",
            "Return one order, including its items, fulfillment, and payments.",
            Order,
            lambda path, _query, _body: OperationInvocation(
                "get_order_details", {"order_id": path["order_id"]}
            ),
            response_adapter=_adapt_order_response,
        ),
        ClientOperation(
            "PUT",
            "/v1/orders/{order_id}/shipping-address",
            "replaceOrderShippingAddress",
            "Replace an order shipping address",
            "Replace the complete shipping address associated with one order.",
            OrderShippingAddressResult,
            lambda path, _query, body: OperationInvocation(
                "modify_pending_order_address",
                _address_arguments("order_id", path["order_id"], body),
            ),
            body_type=Address,
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            response_adapter=_adapt_order_shipping_address_response,
            reference_tool_names=("modify_pending_order_address",),
        ),
        ClientOperation(
            "PUT",
            "/v1/orders/{order_id}/payment-method",
            "replaceOrderPaymentMethod",
            "Replace an order payment method",
            "Replace the payment method associated with one order.",
            OrderPaymentMethodResult,
            lambda path, _query, body: OperationInvocation(
                "modify_pending_order_payment",
                {
                    "order_id": path["order_id"],
                    "payment_method_id": body.payment_method_id,
                },
            ),
            body_type=PaymentMethodRequest,
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            response_adapter=_adapt_order_payment_method_response,
            reference_tool_names=("modify_pending_order_payment",),
        ),
        ClientOperation(
            "POST",
            "/v1/orders/{order_id}/cancellations",
            "createOrderCancellation",
            "Cancel an order",
            "Create a cancellation for one order.",
            OrderCancellationResult,
            lambda path, _query, body: OperationInvocation(
                "cancel_pending_order",
                {"order_id": path["order_id"], "reason": body.reason},
            ),
            body_type=CancellationRequest,
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            response_adapter=_adapt_order_cancellation_response,
            reference_tool_names=("cancel_pending_order",),
        ),
        ClientOperation(
            "POST",
            "/v1/orders/{order_id}/item-modifications",
            "createOrderItemModification",
            "Modify order items",
            "Replace selected items in one order.",
            OrderItemModificationResult,
            lambda path, _query, body: OperationInvocation(
                "modify_pending_order_items",
                _replacement_arguments(path["order_id"], body),
            ),
            body_type=ItemReplacementRequest,
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            response_adapter=_adapt_order_item_modification_response,
            reference_tool_names=("modify_pending_order_items",),
        ),
        ClientOperation(
            "POST",
            "/v1/orders/{order_id}/returns",
            "createOrderReturn",
            "Return order items",
            "Create a return request for selected items in one order.",
            OrderReturnResult,
            lambda path, _query, body: OperationInvocation(
                "return_delivered_order_items",
                {
                    "order_id": path["order_id"],
                    "item_ids": body.item_ids,
                    "payment_method_id": body.refund_payment_method_id,
                },
            ),
            body_type=ReturnRequest,
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            response_adapter=_adapt_order_return_response,
            reference_tool_names=("return_delivered_order_items",),
        ),
        ClientOperation(
            "POST",
            "/v1/orders/{order_id}/exchanges",
            "createOrderExchange",
            "Exchange order items",
            "Create an exchange request with replacements for selected items in one order.",
            OrderExchangeResult,
            lambda path, _query, body: OperationInvocation(
                "exchange_delivered_order_items",
                _replacement_arguments(path["order_id"], body),
            ),
            body_type=ItemReplacementRequest,
            mutates_state=True,
            idempotency="not_guaranteed",
            automatic_retries="forbidden",
            response_adapter=_adapt_order_exchange_response,
            reference_tool_names=("exchange_delivered_order_items",),
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
