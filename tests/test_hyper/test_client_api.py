"""Tests for the Hyper-τ client-owned REST API boundary."""

import json
import os
import re
import textwrap
from email import policy
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import quote

import pytest
from pydantic import BaseModel

from tau2.data_model.message import AssistantMessage, ToolCall, ToolMessage
from tau2.data_model.tasks import EnvFunctionCall, InitializationData
from tau2.environment.db import DB
from tau2.environment.environment import Environment
from tau2.environment.toolkit import (
    ToolKitBase,
    ToolType,
    is_discoverable_tool,
    is_tool,
)
from tau2.evaluator.evaluator_action import ActionEvaluator
from tau2.hyper.client_api import (
    CLIENT_API_MAX_REQUEST_BYTES,
    CLIENT_API_MAX_RESPONSE_BYTES,
    ClientAPI,
    ClientAPIContext,
)
from tau2.hyper.client_api.runtime import ClientAPIRuntime, build_openapi_contract


class Account(BaseModel):
    balance: int


class AccountDB(DB):
    account: Account


class AccountTools(ToolKitBase):
    @is_tool(ToolType.READ)
    def get_balance(self) -> int:
        """Return the current account balance."""
        return self.db.account.balance

    @is_tool(ToolType.WRITE)
    def add_credit(self, amount: int) -> Account:
        """Add credit to the account.

        Args:
            amount: Positive number of credits to add.
        """
        self.db.account.balance += amount
        return self.db.account

    @is_tool(ToolType.READ)
    def echo(self, value: str) -> str:
        """Return a supplied string.

        Args:
            value: String to return.
        """
        return value

    @is_tool(ToolType.READ)
    def large_response(self, size: int) -> str:
        """Return a string of the requested size.

        Args:
            size: Number of characters to return.
        """
        return "x" * size


class BankingCatalogTools(ToolKitBase):
    """Minimal toolkit covering one initial and one discovered Banking API."""

    @is_tool(ToolType.READ)
    def get_user_information_by_id(self, user_id: str) -> str:
        """Return a stable fake customer record."""
        return f"customer:{user_id}"

    @is_tool(ToolType.WRITE)
    def change_user_email(self, user_id: str, new_email: str) -> str:
        """Replace a fake customer's email address."""
        return f"email:{user_id}:{new_email}"

    @is_discoverable_tool(ToolType.WRITE)
    def update_transaction_rewards_3847(
        self,
        transaction_id: str,
        new_rewards_earned: str,
    ) -> str:
        """Update a fake transaction reward value."""
        self.db.account.balance = int(new_rewards_earned)
        return f"updated:{transaction_id}:{new_rewards_earned}"


def _runtime() -> ClientAPIRuntime:
    environment = Environment(
        domain_name="accounts",
        policy="",
        tools=AccountTools(AccountDB(account=Account(balance=10))),
    )
    return ClientAPIRuntime(environment)


def _banking_catalog_runtime() -> ClientAPIRuntime:
    environment = Environment(
        domain_name="banking_knowledge",
        policy="",
        tools=BankingCatalogTools(AccountDB(account=Account(balance=10))),
    )
    return ClientAPIRuntime(environment)


def test_openapi_contract_exposes_rest_operations_without_database_schema():
    contract = build_openapi_contract(_runtime().environment)

    assert contract["openapi"] == "3.1.0"
    assert (
        contract["jsonSchemaDialect"] == "https://json-schema.org/draft/2020-12/schema"
    )
    assert contract["info"]["version"] == "3.1.0"
    operation = contract["paths"]["/v1/tools/add_credit"]["post"]
    assert operation["operationId"] == "add_credit"
    assert operation["description"].startswith("Add credit to the account")
    assert operation["x-api-mutates-state"] is True
    assert operation["x-api-idempotency"] == "not_guaranteed"
    assert operation["x-api-automatic-retries"] == "forbidden"
    read_operation = contract["paths"]["/v1/tools/get_balance"]["post"]
    assert read_operation["x-api-mutates-state"] is False
    assert read_operation["x-api-idempotency"] == "safe"
    assert read_operation["x-api-automatic-retries"] == "allowed"
    request_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    assert request_schema["type"] == "object"
    assert request_schema["required"] == ["amount"]
    assert request_schema["properties"]["amount"]["type"] == "integer"
    response_schema = operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    assert response_schema["$ref"] == "#/components/schemas/add_credit_response_Account"
    assert (
        contract["components"]["schemas"]["add_credit_response_Account"]["properties"][
            "balance"
        ]["type"]
        == "integer"
    )
    assert "returns" not in response_schema.get("properties", {})
    assert operation["x-api-request-body-max-bytes"] == 1_048_576
    assert operation["x-api-response-body-max-bytes"] == 4_194_304
    for status in ("400", "404", "405", "413", "422", "502"):
        error_schema = operation["responses"][status]["content"]["application/json"][
            "schema"
        ]
        assert error_schema == {"$ref": "#/components/schemas/APIError"}
    assert contract["components"]["schemas"]["APIError"]["required"] == ["error"]
    assert (
        "type"
        not in contract["components"]["schemas"]["APIError"]["properties"]["error"][
            "properties"
        ]
    )
    assert "database" not in str(contract).lower()

    all_refs: list[str] = []

    def collect_refs(value):
        if isinstance(value, dict):
            if "$ref" in value:
                all_refs.append(value["$ref"])
            for nested in value.values():
                collect_refs(nested)
        elif isinstance(value, list):
            for nested in value:
                collect_refs(nested)

    collect_refs(contract)
    assert not any(ref.startswith("#/$defs/") for ref in all_refs)
    for ref in all_refs:
        if ref.startswith("#/components/schemas/"):
            assert ref.rsplit("/", 1)[-1] in contract["components"]["schemas"]


def test_client_api_exposes_only_explicit_trusted_conversation_context():
    client_api = ClientAPI(
        lambda _request: {"status_code": 200},
        context=ClientAPIContext(conversation_id="conv_test"),
    )

    assert client_api.context.conversation_id == "conv_test"
    assert client_api.context.model_dump() == {"conversation_id": "conv_test"}

    unbound = ClientAPI(lambda _request: {"status_code": 200})
    with pytest.raises(RuntimeError, match="context has not been initialized"):
        _ = unbound.context


@pytest.mark.parametrize("domain", ["retail_plus", "airline_plus", "telecom"])
def test_conversation_transfer_is_scoped_recorded_and_terminal(domain):
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    runtime = create_domain_client_api_runtime(
        domain,
        conversation_id="conv_current",
    )
    before = runtime.snapshot()

    missing = runtime.request(
        method="POST",
        path="/v1/conversations/conv_other/transfers",
        body={"summary": "Customer requested a person"},
    )
    accepted = runtime.request(
        method="POST",
        path="/v1/conversations/conv_current/transfers",
        body={"summary": "Customer requested a person"},
    )
    duplicate = runtime.request(
        method="POST",
        path="/v1/conversations/conv_current/transfers",
        body={"summary": "Retry the transfer"},
    )

    assert missing.status_code == 404
    assert missing.body["error"]["code"] == "conversation_not_found"
    assert accepted.status_code == 201
    assert accepted.body["status"] == "accepted"
    assert accepted.body["transfer_id"].startswith("tr_")
    assert runtime.conversation_transfer is not None
    assert runtime.conversation_transfer.model_dump() == accepted.body
    assert runtime.snapshot() == before
    assert [call.model_dump() for call in runtime.operation_calls] == [
        {
            "operation_id": "transfer_to_human_agents",
            "arguments": {"summary": "Customer requested a person"},
        }
    ]
    assert duplicate.status_code == 409
    assert duplicate.body["error"]["code"] == "conversation_transferred"


@pytest.mark.parametrize("domain", ["retail_plus", "airline_plus", "telecom"])
def test_conversation_transfer_receipt_is_deterministic_across_replay(domain):
    """Grading replays recorded tool calls against a fresh runtime with a
    fresh conversation_id; the transfer receipt is a WRITE output compared
    strictly against the transcript, so it must be a deterministic function
    of the request rather than a random id (a random id erred every eval
    task whose conversation ended in a live transfer)."""
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    body = {"summary": "Customer requested a person"}
    receipts = []
    for conversation_id in ("conv_live", "conv_replay"):
        runtime = create_domain_client_api_runtime(
            domain,
            conversation_id=conversation_id,
        )
        response = runtime.request(
            method="POST",
            path=f"/v1/conversations/{conversation_id}/transfers",
            body=body,
        )
        assert response.status_code == 201
        receipts.append(response.body)
    assert receipts[0] == receipts[1]

    other = create_domain_client_api_runtime(domain, conversation_id="conv_live")
    different = other.request(
        method="POST",
        path="/v1/conversations/conv_live/transfers",
        body={"summary": "A different escalation summary"},
    )
    assert different.body["transfer_id"] != receipts[0]["transfer_id"]


def test_retail_openapi_contract_is_client_resource_shaped():
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    contract = build_openapi_contract(
        create_domain_client_api_runtime("retail_plus").environment
    )
    expected_methods = {
        "/v1/customers/search": "post",
        "/v1/customers/{customer_id}": "get",
        "/v1/customers/{customer_id}/default-shipping-address": "put",
        "/v1/catalog/products": "get",
        "/v1/catalog/products/{product_id}": "get",
        "/v1/catalog/items/{item_id}": "get",
        "/v1/orders/{order_id}": "get",
        "/v1/orders/{order_id}/shipping-address": "put",
        "/v1/orders/{order_id}/payment-method": "put",
        "/v1/orders/{order_id}/cancellations": "post",
        "/v1/orders/{order_id}/item-modifications": "post",
        "/v1/orders/{order_id}/returns": "post",
        "/v1/orders/{order_id}/exchanges": "post",
        "/v1/conversations/{conversation_id}/transfers": "post",
    }

    assert set(contract["paths"]) == set(expected_methods)
    for path, method in expected_methods.items():
        assert set(contract["paths"][path]) == {method}
        operation = contract["paths"][path][method]
        assert operation["operationId"]
        assert operation["description"]
        assert "tool" not in operation["description"].lower()
    assert all("calculate" not in path for path in contract["paths"])
    search_schema = contract["paths"]["/v1/customers/search"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"]
    assert set(search_schema["properties"]) == {
        "email",
        "first_name",
        "last_name",
        "postal_code",
    }
    assert "type" not in search_schema["properties"]
    transfer = contract["paths"]["/v1/conversations/{conversation_id}/transfers"][
        "post"
    ]
    assert transfer["operationId"] == "createConversationTransfer"
    assert transfer["x-api-mutates-state"] is True
    assert transfer["x-api-idempotency"] == "not_guaranteed"
    assert transfer["x-api-automatic-retries"] == "forbidden"
    assert set(transfer["responses"]) >= {"201", "404", "409", "422"}

    customer_schema = contract["paths"]["/v1/customers/{customer_id}"]["get"][
        "responses"
    ]["200"]["content"]["application/json"]["schema"]
    assert set(customer_schema["properties"]) == {
        "customer_id",
        "name",
        "default_shipping_address",
        "email",
        "payment_methods",
        "order_ids",
    }
    order_schema = contract["paths"]["/v1/orders/{order_id}"]["get"]["responses"][
        "200"
    ]["content"]["application/json"]["schema"]
    assert set(order_schema["properties"]) == {
        "order_id",
        "customer_id",
        "shipping_address",
        "items",
        "status",
        "fulfillments",
        "payments",
        "cancellation",
        "exchange",
        "return_request",
    }


@pytest.mark.parametrize(
    ("domain", "policy_patterns"),
    [
        (
            "retail_plus",
            (
                r"\bpending[- ]order\b",
                r"\bdelivered[- ]order\b",
                r"\bsame product\b",
                r"\brefund transaction",
            ),
        ),
        (
            "airline_plus",
            (
                r"\bdirect or one[- ]stop\b",
                r"\bwithout changing its size\b",
                r"\brefund transaction",
            ),
        ),
        (
            "telecom",
            (
                r"\bactive line owned by\b",
                r"\bsuspended or pending[- ]activation\b",
                r"\bno other bill is awaiting payment\b",
                r"\bresulting charge\b",
            ),
        ),
        (
            "banking_knowledge",
            (
                r"\bcompleted customer identity verification\b",
                r"\bdocumented self[- ]service action\b",
            ),
        ),
    ],
)
def test_public_client_api_descriptions_do_not_encode_policy_rules(
    domain, policy_patterns
):
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    environment = (
        _banking_catalog_runtime().environment
        if domain == "banking_knowledge"
        else create_domain_client_api_runtime(domain).environment
    )
    contract = build_openapi_contract(environment)
    public_descriptions = "\n".join(
        value
        for path_item in contract["paths"].values()
        for operation in path_item.values()
        for key in ("summary", "description")
        if (value := operation.get(key))
    ).lower()

    for pattern in policy_patterns:
        assert re.search(pattern, public_descriptions) is None


@pytest.mark.parametrize(
    "domain", ["retail_plus", "airline_plus", "telecom", "banking_knowledge"]
)
def test_openapi_contract_never_names_the_evaluation_harness(domain):
    # The contract ships inside construction kits styled as a business-owned
    # artifact; nothing in it may name the benchmark or its harness roles.
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    environment = (
        _banking_catalog_runtime().environment
        if domain == "banking_knowledge"
        else create_domain_client_api_runtime(domain).environment
    )
    document = json.dumps(build_openapi_contract(environment))

    assert "τ" not in document
    assert "Client" not in document
    lowered = document.lower()
    for term in (
        "tau",
        "tau2",
        "hyper",
        "developer",
        "broker",
        "sealed",
        "benchmark",
        "simulator",
        "simulation",
        "sandbox",
        "grader",
    ):
        assert re.search(rf"\b{re.escape(term)}\b", lowered) is None, term


def test_retail_client_api_adapts_lookup_address_and_evaluation_actions():
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    runtime = create_domain_client_api_runtime("retail_plus")
    state = runtime.snapshot()
    customer_id, customer = next(iter(state["users"].items()))

    lookup = runtime.request(
        method="POST",
        path="/v1/customers/search",
        body={"email": customer["email"]},
    )
    lookup_by_name = runtime.request(
        method="POST",
        path="/v1/customers/search",
        body={
            "first_name": customer["name"]["first_name"],
            "last_name": customer["name"]["last_name"],
            "postal_code": customer["address"]["zip"],
        },
    )
    invalid = runtime.request(
        method="POST",
        path="/v1/customers/search",
        body={"first_name": "Incomplete"},
    )
    mixed = runtime.request(
        method="POST",
        path="/v1/customers/search",
        body={
            "email": customer["email"],
            "first_name": customer["name"]["first_name"],
            "last_name": customer["name"]["last_name"],
            "postal_code": customer["address"]["zip"],
        },
    )
    changed = runtime.request(
        method="PUT",
        path=(f"/v1/customers/{quote(customer_id, safe='')}/default-shipping-address"),
        body={
            "address_line_1": "42 API Boundary Way",
            "address_line_2": None,
            "city": "Broker City",
            "region": "CA",
            "country": "USA",
            "postal_code": "94107",
        },
    )

    assert lookup.status_code == 200
    assert lookup.body == {"customer_id": customer_id}
    assert lookup_by_name.status_code == 200
    assert lookup_by_name.body == {"customer_id": customer_id}
    assert invalid.status_code == 400
    assert invalid.body["error"]["code"] == "invalid_request"
    assert mixed.status_code == 400
    assert mixed.body["error"]["code"] == "invalid_request"
    assert changed.status_code == 200
    assert changed.body == {
        "customer_id": customer_id,
        "default_shipping_address": {
            "address_line_1": "42 API Boundary Way",
            "address_line_2": "",
            "city": "Broker City",
            "region": "CA",
            "country": "USA",
            "postal_code": "94107",
        },
    }
    assert runtime.snapshot()["users"][customer_id]["address"]["address2"] == ""
    assert [call.operation_id for call in runtime.operation_calls] == [
        "find_user_id_by_email",
        "find_user_id_by_name_zip",
        "modify_user_address",
    ]
    assert runtime.operation_calls[2].arguments == {
        "user_id": customer_id,
        "address1": "42 API Boundary Way",
        "address2": "",
        "city": "Broker City",
        "state": "CA",
        "country": "USA",
        "zip": "94107",
    }


def test_retail_client_api_normalizes_collections_and_decodes_order_ids():
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    runtime = create_domain_client_api_runtime("retail_plus")
    state = runtime.snapshot()
    customer_id = next(iter(state["users"]))
    product_id = next(iter(state["products"]))
    order_id = next(iter(state["orders"]))

    products = runtime.request(method="GET", path="/v1/catalog/products")
    product = runtime.request(
        method="GET",
        path=f"/v1/catalog/products/{product_id}",
    )
    customer = runtime.request(
        method="GET",
        path=f"/v1/customers/{customer_id}",
    )
    order = runtime.request(
        method="GET",
        path=f"/v1/orders/{quote(order_id, safe='')}",
    )
    calculate = runtime.request(
        method="POST",
        path="/v1/tools/calculate",
        body={"expression": "2 + 2"},
    )

    assert products.status_code == 200
    assert products.body["products"]
    assert set(products.body["products"][0]) == {"product_id", "name"}
    assert product.status_code == 200
    assert product.body["items"]
    assert "variants" not in product.body
    assert customer.status_code == 200
    assert customer.body["customer_id"] == customer_id
    assert isinstance(customer.body["payment_methods"], list)
    assert "user_id" not in customer.body
    assert "orders" not in customer.body
    assert set(customer.body["default_shipping_address"]) == {
        "address_line_1",
        "address_line_2",
        "city",
        "region",
        "country",
        "postal_code",
    }
    assert order.status_code == 200
    assert order.body["order_id"] == order_id
    assert order.body["customer_id"] == state["orders"][order_id]["user_id"]
    assert "user_id" not in order.body
    assert "payment_history" not in order.body
    assert "exchange_items" not in order.body
    assert calculate.status_code == 404


def test_airline_openapi_contract_is_client_resource_shaped():
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    contract = build_openapi_contract(
        create_domain_client_api_runtime("airline_plus").environment
    )
    expected_methods = {
        "/v1/customers/{customer_id}": "get",
        "/v1/customers/{customer_id}/certificates": "post",
        "/v1/airports": "get",
        "/v1/flight-itineraries": "get",
        "/v1/flights/{flight_number}/instances/{date}": "get",
        "/v1/reservations": "post",
        "/v1/reservations/{reservation_id}": "get",
        "/v1/reservations/{reservation_id}/cancellations": "post",
        "/v1/reservations/{reservation_id}/baggage": "put",
        "/v1/reservations/{reservation_id}/itinerary": "put",
        "/v1/reservations/{reservation_id}/passengers": "put",
        "/v1/conversations/{conversation_id}/transfers": "post",
    }

    assert set(contract["paths"]) == set(expected_methods)
    for path, method in expected_methods.items():
        assert set(contract["paths"][path]) == {method}
    assert all("calculate" not in path for path in contract["paths"])

    customer_schema = contract["paths"]["/v1/customers/{customer_id}"]["get"][
        "responses"
    ]["200"]["content"]["application/json"]["schema"]
    assert set(customer_schema["properties"]) == {
        "customer_id",
        "name",
        "address",
        "email",
        "dob",
        "payment_methods",
        "saved_passengers",
        "membership",
        "reservation_ids",
    }
    reservation_schema = contract["paths"]["/v1/reservations/{reservation_id}"]["get"][
        "responses"
    ]["200"]["content"]["application/json"]["schema"]
    assert set(reservation_schema["properties"]) == {
        "reservation_id",
        "customer_id",
        "trip",
        "passengers",
        "payments",
        "created_at",
        "baggage",
        "insurance",
        "status",
    }


def test_airline_client_api_consolidates_search_and_normalizes_responses():
    from tau2.domains.airline_plus.environment import get_tasks
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    direct_action = next(
        action
        for task in get_tasks()
        for action in task.evaluation_criteria.actions
        if action.name == "search_direct_flight"
    )
    runtime = create_domain_client_api_runtime("airline_plus")
    query = {
        "origin": direct_action.arguments["origin"],
        "destination": direct_action.arguments["destination"],
        "departure_date": direct_action.arguments["date"],
        "stops": 0,
    }

    airports = runtime.request(method="GET", path="/v1/airports")
    itineraries = runtime.request(
        method="GET",
        path="/v1/flight-itineraries",
        query=query,
    )
    one_stop = runtime.request(
        method="GET",
        path="/v1/flight-itineraries",
        query={**query, "stops": 1},
    )

    assert airports.status_code == 200
    assert airports.body["airports"][0].keys() == {"iata", "city"}
    assert itineraries.status_code == 200
    assert itineraries.body["itineraries"]
    assert len(itineraries.body["itineraries"][0]["segments"]) == 1
    segment = itineraries.body["itineraries"][0]["segments"][0]
    assert "departure_date" in segment
    assert "date" not in segment
    assert segment["cabin_offers"]
    assert set(segment["cabin_offers"][0]) == {
        "cabin",
        "available_seats",
        "price",
    }
    assert "available_seats" not in segment
    assert "prices" not in segment
    assert one_stop.status_code == 200
    assert all(
        len(itinerary["segments"]) == 2 for itinerary in one_stop.body["itineraries"]
    )
    assert [call.operation_id for call in runtime.operation_calls] == [
        "list_all_airports",
        "search_direct_flight",
        "search_onestop_flight",
    ]
    assert runtime.operation_calls[-2].arguments == direct_action.arguments
    assert runtime.operation_calls[-1].arguments == direct_action.arguments


def test_airline_client_api_projects_customer_and_reservation_resources():
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    runtime = create_domain_client_api_runtime("airline_plus")
    state = runtime.snapshot()
    customer_id = next(iter(state["users"]))
    reservation_id = next(iter(state["reservations"]))

    customer = runtime.request(
        method="GET",
        path=f"/v1/customers/{customer_id}",
    )
    reservation = runtime.request(
        method="GET",
        path=f"/v1/reservations/{reservation_id}",
    )

    assert customer.status_code == 200
    assert customer.body["customer_id"] == customer_id
    assert isinstance(customer.body["payment_methods"], list)
    assert (
        customer.body["reservation_ids"] == state["users"][customer_id]["reservations"]
    )
    assert "user_id" not in customer.body
    assert "reservations" not in customer.body
    assert set(customer.body["address"]) == {
        "address_line_1",
        "address_line_2",
        "city",
        "country",
        "region",
        "postal_code",
    }

    assert reservation.status_code == 200
    assert (
        reservation.body["customer_id"]
        == state["reservations"][reservation_id]["user_id"]
    )
    assert set(reservation.body["trip"]) == {
        "origin",
        "destination",
        "trip_type",
        "cabin",
        "segments",
    }
    assert set(reservation.body["baggage"]) == {"total_bags", "paid_bags"}
    assert "flights" not in reservation.body
    assert "payment_history" not in reservation.body
    assert "total_baggages" not in reservation.body


def test_explicit_client_api_distinguishes_methods_resources_and_state_conflicts():
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    runtime = create_domain_client_api_runtime("retail_plus")
    state = runtime.snapshot()
    non_pending_order_id = next(
        order_id
        for order_id, order in state["orders"].items()
        if order["status"] != "pending"
    )

    wrong_method = runtime.request(method="POST", path="/v1/catalog/products")
    wrong_search_method = runtime.request(method="GET", path="/v1/customers/search")
    missing = runtime.request(method="GET", path="/v1/orders/%23NOT-REAL")
    conflict = runtime.request(
        method="POST",
        path=f"/v1/orders/{quote(non_pending_order_id, safe='')}/cancellations",
        body={"reason": "ordered by mistake"},
    )

    assert wrong_method.status_code == 405
    assert wrong_method.headers["allow"] == "GET"
    assert wrong_search_method.status_code == 405
    assert wrong_search_method.headers["allow"] == "POST"
    assert missing.status_code == 404
    assert missing.body["error"]["code"] == "resource_not_found"
    assert conflict.status_code == 409
    assert conflict.body["error"]["code"] == "resource_conflict"
    assert conflict.body["error"]["message"] == (
        "The resource's current state prevents the operation"
    )
    assert "pending" not in conflict.body["error"]["message"].lower()


@pytest.mark.parametrize(
    ("private_message", "expected_status", "expected_code", "public_message"),
    [
        (
            "Order secret-404 not found for an internal customer",
            404,
            "resource_not_found",
            "The requested resource was not found",
        ),
        (
            "Order is not pending because of secret-409 eligibility",
            409,
            "resource_conflict",
            "The resource's current state prevents the operation",
        ),
        (
            "Refunds require the secret-422 payment workflow",
            422,
            "business_rule_violation",
            "The request violates a business constraint",
        ),
    ],
)
def test_explicit_client_api_redacts_private_business_errors(
    monkeypatch,
    private_message: str,
    expected_status: int,
    expected_code: str,
    public_message: str,
):
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    runtime = create_domain_client_api_runtime("retail_plus")
    order_id = next(iter(runtime.snapshot()["orders"]))

    def reject_operation(*_args, **_kwargs):
        raise ValueError(private_message)

    monkeypatch.setattr(runtime.environment, "make_tool_call", reject_operation)

    response = runtime.request(method="GET", path=f"/v1/orders/{order_id}")

    assert response.status_code == expected_status
    assert response.body == {
        "error": {"code": expected_code, "message": public_message}
    }
    assert private_message not in json.dumps(response.body)


def test_client_api_redacts_private_legacy_tool_errors(monkeypatch):
    runtime = _runtime()

    def reject_operation(*_args, **_kwargs):
        raise RuntimeError("secret legacy eligibility rule")

    monkeypatch.setattr(runtime.environment, "make_tool_call", reject_operation)

    response = runtime.request(method="POST", path="/v1/tools/get_balance")

    assert response.status_code == 422
    assert response.body == {
        "error": {
            "code": "operation_rejected",
            "message": "The operation rejected the request",
        }
    }
    assert "type" not in response.body["error"]


def test_client_api_redacts_private_response_adapter_errors(monkeypatch):
    from tau2.hyper.client_api import catalog as catalog_module
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    runtime = create_domain_client_api_runtime("retail_plus")
    order_id = next(iter(runtime.snapshot()["orders"]))

    def reject_response(*_args, **_kwargs):
        raise RuntimeError("secret response adapter detail")

    monkeypatch.setattr(
        catalog_module,
        "adapt_operation_response",
        reject_response,
    )

    response = runtime.request(method="GET", path=f"/v1/orders/{order_id}")

    assert response.status_code == 502
    assert response.body == {
        "error": {
            "code": "invalid_response_body",
            "message": "The operation could not normalize its response",
        }
    }


def test_executed_write_is_recorded_when_response_normalization_fails(monkeypatch):
    # client_api resolves adapt_operation_response lazily from the catalog
    # (the construction image has no tau2.domains), so patch the catalog.
    from tau2.hyper.client_api import catalog as catalog_module
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    runtime = create_domain_client_api_runtime("retail_plus")
    state = runtime.snapshot()
    customer_id = next(iter(state["users"]))
    monkeypatch.setattr(
        catalog_module,
        "adapt_operation_response",
        lambda _operation, _invocation, _result: {"invalid": "user"},
    )

    response = runtime.request(
        method="PUT",
        path=f"/v1/customers/{customer_id}/default-shipping-address",
        body={
            "address_line_1": "42 Recorded Write Way",
            "address_line_2": None,
            "city": "Broker City",
            "region": "CA",
            "country": "USA",
            "postal_code": "94107",
        },
    )

    assert response.status_code == 502
    assert response.body["error"]["code"] == "invalid_response_body"
    assert runtime.snapshot()["users"][customer_id]["address"]["address1"] == (
        "42 Recorded Write Way"
    )
    assert [call.operation_id for call in runtime.operation_calls] == [
        "modify_user_address"
    ]


def test_airline_client_api_normalizes_status_and_certificate():
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    runtime = create_domain_client_api_runtime("airline_plus")
    state = runtime.snapshot()
    customer_id = next(iter(state["users"]))
    flight_number, flight = next(iter(state["flights"].items()))
    date = next(iter(flight["dates"]))

    status = runtime.request(
        method="GET",
        path=f"/v1/flights/{flight_number}/instances/{date}",
    )
    certificate = runtime.request(
        method="POST",
        path=f"/v1/customers/{customer_id}/certificates",
        body={"amount": 85},
    )

    assert status.status_code == 200
    assert status.body == {
        "flight_number": flight_number,
        "date": date,
        "status": flight["dates"][date]["status"],
    }
    assert certificate.status_code == 201
    assert certificate.body["customer_id"] == customer_id
    assert certificate.body["amount"] == 85
    assert certificate.body["certificate_id"].startswith("certificate_")
    assert [call.operation_id for call in runtime.operation_calls] == [
        "get_flight_status",
        "send_certificate",
    ]


def test_telecom_openapi_contract_is_client_resource_shaped():
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    contract = build_openapi_contract(
        create_domain_client_api_runtime("telecom").environment
    )
    expected_methods = {
        "/v1/customers/search": "post",
        "/v1/customers/{customer_id}": "get",
        "/v1/lines/{line_id}": "get",
        "/v1/devices/{device_id}": "get",
        "/v1/bills/{bill_id}": "get",
        "/v1/plans/{plan_id}": "get",
        "/v1/customers/{customer_id}/lines/{line_id}/suspensions": "post",
        "/v1/customers/{customer_id}/lines/{line_id}/resumptions": "post",
        "/v1/customers/{customer_id}/bills": "get",
        "/v1/customers/{customer_id}/bills/{bill_id}/payment-requests": "post",
        "/v1/customers/{customer_id}/lines/{line_id}/data-usage": "get",
        "/v1/customers/{customer_id}/lines/{line_id}/roaming": "put",
        "/v1/customers/{customer_id}/lines/{line_id}/data-refuels": "post",
        "/v1/conversations/{conversation_id}/transfers": "post",
    }

    assert set(contract["paths"]) == set(expected_methods)
    for path, method in expected_methods.items():
        assert set(contract["paths"][path]) == {method}
        operation = contract["paths"][path][method]
        assert operation["operationId"]
        assert operation["description"]
        assert "tool" not in operation["description"].lower()

    search_schema = contract["paths"]["/v1/customers/search"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"]
    assert set(search_schema["properties"]) == {
        "phone_number",
        "full_name",
        "date_of_birth",
    }
    assert "type" not in search_schema["properties"]


def test_banking_openapi_advertises_initial_operations_without_platform_wrappers():
    contract = build_openapi_contract(_banking_catalog_runtime().environment)

    assert "/v1/customers/search" in contract["paths"]
    assert "/v1/customers/{customer_id}" in contract["paths"]
    assert "/v1/customers/{customer_id}/credit-card-accounts" in contract["paths"]
    assert "/v1/customers/{customer_id}/credit-card-transactions" in contract["paths"]
    assert "/v1/customers/{customer_id}/referrals" in contract["paths"]
    assert "/v1/customers/{customer_id}/verifications" in contract["paths"]
    assert "/v1/conversations/{conversation_id}/transfers" in contract["paths"]

    serialized = json.dumps(contract)
    assert "unlock_discoverable_agent_tool" not in serialized
    assert "call_discoverable_agent_tool" not in serialized
    assert "list_discoverable_agent_tools" not in serialized
    assert (
        "/v1/credit-card-transactions/{transaction_id}/rewards" not in contract["paths"]
    )


def test_banking_discovered_endpoint_is_directly_routable_without_unlock():
    runtime = _banking_catalog_runtime()

    missing_field = runtime.request(
        method="PATCH",
        path="/v1/credit-card-transactions/txn_1/rewards",
        body={},
    )
    response = runtime.request(
        method="PATCH",
        path="/v1/credit-card-transactions/txn_1/rewards",
        body={"new_rewards_earned": "42"},
    )

    assert missing_field.status_code == 400
    assert response.status_code == 200
    assert response.body == {
        "transaction_id": "txn_1",
        "rewards_earned": "42",
    }
    assert runtime.snapshot()["account"]["balance"] == 42
    assert [call.operation_id for call in runtime.operation_calls] == [
        "update_transaction_rewards_3847"
    ]


def test_banking_customer_email_resource_maps_public_field_to_reference_argument():
    runtime = _banking_catalog_runtime()

    response = runtime.request(
        method="PUT",
        path="/v1/customers/customer_1/email",
        body={"email": "new@example.com"},
    )

    assert response.status_code == 200
    assert response.body == {
        "customer_id": "customer_1",
        "email": "new@example.com",
    }
    assert runtime.operation_calls[0].arguments == {
        "user_id": "customer_1",
        "new_email": "new@example.com",
    }


def test_banking_discovered_endpoint_state_resets_between_trials():
    runtime = _banking_catalog_runtime()
    initialization = InitializationData(agent_data={"account": {"balance": 10}})
    runtime.set_state(initialization, None, [])

    response = runtime.request(
        method="PATCH",
        path="/v1/credit-card-transactions/txn_1/rewards",
        body={"new_rewards_earned": "99"},
    )
    assert response.status_code == 200
    assert runtime.snapshot()["account"]["balance"] == 99

    runtime.set_state(initialization, None, [])

    assert runtime.snapshot()["account"]["balance"] == 10
    assert runtime.operation_calls == ()


def test_banking_document_adapter_replaces_wrapper_protocol_with_http_contract():
    from tau2.hyper.client_api.banking_docs import rewrite_banking_client_api_text

    source = (
        "Use unlock_discoverable_agent_tool to unlock "
        "update_transaction_rewards_3847. Then use "
        "call_discoverable_agent_tool with transaction_id and "
        "new_rewards_earned. Use downgrade_credit_card_3847 with "
        "credit_card_account_id, user_id, and target_card_type."
    )

    rewritten = rewrite_banking_client_api_text(source)

    assert "unlock_discoverable_agent_tool" not in rewritten
    assert "call_discoverable_agent_tool" not in rewritten
    assert "update_transaction_rewards_3847" not in rewritten
    assert "PATCH /v1/credit-card-transactions/{transaction_id}/rewards" in rewritten
    assert "Request body" in rewritten
    assert "new_rewards_earned" in rewritten
    assert "POST /v1/credit-card-accounts/{account_id}/downgrades" in rewritten
    assert "target_card_type" in rewritten
    assert "Response" in rewritten
    assert "Errors" in rewritten


def test_banking_document_adapter_preserves_email_encoding():
    from tau2.hyper.client_api.banking_docs import (
        rewrite_banking_client_api_document,
    )

    source = (
        b"From: ops@example.com\r\n"
        b"To: support@example.com\r\n"
        b"Subject: Rewards correction\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"Content-Transfer-Encoding: quoted-printable\r\n"
        b"MIME-Version: 1.0\r\n\r\n"
        b"Call update_transaction_rewards_3847 for the customer.=\r\n"
    )

    rewritten = rewrite_banking_client_api_document(source, ".eml")
    message = BytesParser(policy=policy.default).parsebytes(rewritten.content)
    body = message.get_content()

    assert message["Content-Transfer-Encoding"] == "quoted-printable"
    assert "update_transaction_rewards_3847" not in body
    assert "PATCH /v1/credit-card-transactions/{transaction_id}/rewards" in body
    assert "Referenced API contracts" in body


def test_telecom_client_api_validates_flat_search_and_splits_resource_reads():
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    runtime = create_domain_client_api_runtime("telecom")
    state = runtime.snapshot()
    customer = state["customers"][0]
    line_id = customer["line_ids"][0]
    line = next(item for item in state["lines"] if item["line_id"] == line_id)

    by_phone = runtime.request(
        method="POST",
        path="/v1/customers/search",
        body={"phone_number": line["phone_number"]},
    )
    by_name = runtime.request(
        method="POST",
        path="/v1/customers/search",
        body={
            "full_name": customer["full_name"],
            "date_of_birth": customer["date_of_birth"],
        },
    )
    incomplete = runtime.request(
        method="POST",
        path="/v1/customers/search",
        body={"full_name": customer["full_name"]},
    )
    mixed = runtime.request(
        method="POST",
        path="/v1/customers/search",
        body={
            "phone_number": line["phone_number"],
            "full_name": customer["full_name"],
            "date_of_birth": customer["date_of_birth"],
        },
    )
    line_response = runtime.request(
        method="GET",
        path=f"/v1/lines/{quote(line_id, safe='')}",
    )
    customer_response = runtime.request(
        method="GET",
        path=f"/v1/customers/{quote(customer['customer_id'], safe='')}",
    )
    device_response = runtime.request(
        method="GET",
        path=f"/v1/devices/{quote(line['device_id'], safe='')}",
    )
    bill_response = runtime.request(
        method="GET",
        path=f"/v1/bills/{quote(customer['bill_ids'][0], safe='')}",
    )
    plan_response = runtime.request(
        method="GET",
        path=f"/v1/plans/{quote(line['plan_id'], safe='')}",
    )
    wrong_resource = runtime.request(
        method="GET",
        path=f"/v1/lines/{quote(line['plan_id'], safe='')}",
    )

    assert by_phone.status_code == 200
    assert [item["customer_id"] for item in by_phone.body["customers"]] == [
        customer["customer_id"]
    ]
    assert set(by_phone.body["customers"][0]) == {
        "customer_id",
        "full_name",
        "phone_number",
    }
    assert by_name.status_code == 200
    assert [item["customer_id"] for item in by_name.body["customers"]] == [
        customer["customer_id"]
    ]
    assert incomplete.status_code == 400
    assert mixed.status_code == 400
    assert line_response.body["line_id"] == line["line_id"]
    assert line_response.body["phone_number"] == line["phone_number"]
    assert customer_response.body["customer_id"] == customer["customer_id"]
    assert set(customer_response.body) == {
        "customer_id",
        "full_name",
        "phone_number",
        "account_status",
        "line_ids",
    }
    assert not {
        "created_at",
        "last_extension_date",
        "goodwill_credit_used_this_year",
        "bill_ids",
        "payment_methods",
    } & set(customer_response.body)
    assert not {"last_plan_change_date", "last_sim_replacement_date"} & set(
        line_response.body
    )
    assert device_response.body["device_id"] == line["device_id"]
    assert not {"imei", "activation_date", "last_esim_transfer_date"} & set(
        device_response.body
    )
    assert bill_response.body["bill_id"] == customer["bill_ids"][0]
    assert "customer_id" not in bill_response.body
    assert all("item_type" not in item for item in bill_response.body["line_items"])
    assert plan_response.body["plan_id"] == line["plan_id"]
    assert wrong_resource.status_code == 404
    assert wrong_resource.body["error"]["code"] == "resource_not_found"
    assert [call.operation_id for call in runtime.operation_calls] == [
        "get_customer_by_phone",
        "get_customer_by_name",
        "get_details_by_id",
        "get_customer_by_id",
        "get_details_by_id",
        "get_details_by_id",
        "get_details_by_id",
    ]


def test_telecom_client_api_normalizes_line_billing_and_roaming_operations():
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    runtime = create_domain_client_api_runtime("telecom")
    state = runtime.snapshot()
    customer = next(item for item in state["customers"] if item["line_ids"])
    customer_id = customer["customer_id"]
    line_id = customer["line_ids"][0]
    line = next(item for item in state["lines"] if item["line_id"] == line_id)
    encoded_customer = quote(customer_id, safe="")
    encoded_line = quote(line_id, safe="")

    usage = runtime.request(
        method="GET",
        path=(f"/v1/customers/{encoded_customer}/lines/{encoded_line}/data-usage"),
    )
    roaming = runtime.request(
        method="PUT",
        path=f"/v1/customers/{encoded_customer}/lines/{encoded_line}/roaming",
        body={"enabled": not line["roaming_enabled"]},
    )
    bills = runtime.request(
        method="GET",
        path=f"/v1/customers/{encoded_customer}/bills",
        query={"limit": 2},
    )

    assert usage.status_code == 200
    assert usage.body["line_id"] == line_id
    assert roaming.status_code == 200
    assert roaming.body == {
        "line_id": line_id,
        "roaming_enabled": not line["roaming_enabled"],
    }
    assert bills.status_code == 200
    assert len(bills.body["bills"]) <= 2
    assert all(
        set(bill)
        == {
            "bill_id",
            "period_start",
            "period_end",
            "total_due",
            "due_date",
            "status",
        }
        for bill in bills.body["bills"]
    )
    assert [call.operation_id for call in runtime.operation_calls] == [
        "get_data_usage",
        "enable_roaming" if not line["roaming_enabled"] else "disable_roaming",
        "get_bills_for_customer",
    ]


def test_telecom_client_api_write_responses_are_resource_scoped():
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    runtime = create_domain_client_api_runtime("telecom")
    state = runtime.snapshot()
    line = next(item for item in state["lines"] if item["status"] == "Active")
    customer = next(
        item for item in state["customers"] if line["line_id"] in item["line_ids"]
    )
    line_path = (
        f"/v1/customers/{quote(customer['customer_id'], safe='')}/lines/"
        f"{quote(line['line_id'], safe='')}"
    )

    suspension = runtime.request(
        method="POST",
        path=f"{line_path}/suspensions",
        body={"reason": "Customer requested a temporary suspension"},
    )
    resumption = runtime.request(
        method="POST",
        path=f"{line_path}/resumptions",
    )
    refuel = runtime.request(
        method="POST",
        path=f"{line_path}/data-refuels",
        body={"amount_gb": 0.5},
    )

    assert suspension.body == {
        "line_id": line["line_id"],
        "status": "Suspended",
        "suspension_start_date": suspension.body["suspension_start_date"],
        "holding_fee_per_month": 5.0,
    }
    assert resumption.body == {"line_id": line["line_id"], "status": "Active"}
    assert refuel.body == {
        "line_id": line["line_id"],
        "added_gb": 0.5,
        "total_refueled_gb": line["data_refueling_gb"] + 0.5,
        "charge": refuel.body["charge"],
    }

    payment_runtime = create_domain_client_api_runtime("telecom")
    payment_state = payment_runtime.snapshot()
    payment_customer = next(
        customer
        for customer in payment_state["customers"]
        if any(
            bill["status"] == "Overdue" and bill["bill_id"] in customer["bill_ids"]
            for bill in payment_state["bills"]
        )
        and not any(
            bill["status"] == "Awaiting Payment"
            and bill["bill_id"] in customer["bill_ids"]
            for bill in payment_state["bills"]
        )
    )
    overdue_bill = next(
        bill
        for bill in payment_state["bills"]
        if bill["status"] == "Overdue"
        and bill["bill_id"] in payment_customer["bill_ids"]
    )
    payment = payment_runtime.request(
        method="POST",
        path=(
            f"/v1/customers/{quote(payment_customer['customer_id'], safe='')}/bills/"
            f"{quote(overdue_bill['bill_id'], safe='')}/payment-requests"
        ),
    )

    assert payment.body == {
        "bill_id": overdue_bill["bill_id"],
        "status": "awaiting_payment",
    }


def _initialize_runtime_for_task(runtime, task):
    initial_state = task.initial_state
    runtime.set_state(
        initial_state.initialization_data if initial_state else None,
        initial_state.initialization_actions if initial_state else None,
        (initial_state.message_history or []) if initial_state else [],
    )


def _retail_request_for_reference_action(runtime, action):
    arguments = action.arguments

    def encoded(value):
        return quote(value, safe="")

    if action.name == "find_user_id_by_email":
        return runtime.request(
            method="POST",
            path="/v1/customers/search",
            body={"email": arguments["email"]},
        )
    if action.name == "find_user_id_by_name_zip":
        return runtime.request(
            method="POST",
            path="/v1/customers/search",
            body={
                "first_name": arguments["first_name"],
                "last_name": arguments["last_name"],
                "postal_code": arguments["zip"],
            },
        )
    paths = {
        "get_user_details": (
            "GET",
            f"/v1/customers/{encoded(arguments.get('user_id', ''))}",
        ),
        "get_order_details": (
            "GET",
            f"/v1/orders/{encoded(arguments.get('order_id', ''))}",
        ),
        "get_product_details": (
            "GET",
            f"/v1/catalog/products/{encoded(arguments.get('product_id', ''))}",
        ),
        "get_item_details": (
            "GET",
            f"/v1/catalog/items/{encoded(arguments.get('item_id', ''))}",
        ),
    }
    if action.name in paths:
        method, path = paths[action.name]
        return runtime.request(method=method, path=path)
    order_id = encoded(arguments.get("order_id", ""))
    if action.name in {"modify_pending_order_address", "modify_user_address"}:
        id_value = (
            encoded(arguments["user_id"])
            if action.name == "modify_user_address"
            else order_id
        )
        path = (
            f"/v1/customers/{id_value}/default-shipping-address"
            if action.name == "modify_user_address"
            else f"/v1/orders/{id_value}/shipping-address"
        )
        return runtime.request(
            method="PUT",
            path=path,
            body={
                "address_line_1": arguments["address1"],
                "address_line_2": arguments["address2"],
                "city": arguments["city"],
                "region": arguments["state"],
                "country": arguments["country"],
                "postal_code": arguments["zip"],
            },
        )
    if action.name == "modify_pending_order_payment":
        return runtime.request(
            method="PUT",
            path=f"/v1/orders/{order_id}/payment-method",
            body={"payment_method_id": arguments["payment_method_id"]},
        )
    if action.name == "cancel_pending_order":
        return runtime.request(
            method="POST",
            path=f"/v1/orders/{order_id}/cancellations",
            body={"reason": arguments["reason"]},
        )
    if action.name in {
        "modify_pending_order_items",
        "exchange_delivered_order_items",
    }:
        suffix = (
            "item-modifications"
            if action.name == "modify_pending_order_items"
            else "exchanges"
        )
        return runtime.request(
            method="POST",
            path=f"/v1/orders/{order_id}/{suffix}",
            body={
                "replacements": [
                    {
                        "existing_item_id": existing,
                        "replacement_item_id": replacement,
                    }
                    for existing, replacement in zip(
                        arguments["item_ids"], arguments["new_item_ids"]
                    )
                ],
                "payment_method_id": arguments["payment_method_id"],
            },
        )
    if action.name == "return_delivered_order_items":
        return runtime.request(
            method="POST",
            path=f"/v1/orders/{order_id}/returns",
            body={
                "item_ids": arguments["item_ids"],
                "refund_payment_method_id": arguments["payment_method_id"],
            },
        )
    raise AssertionError(f"No Retail+ request mapping for {action.name}")


def _airline_request_for_reference_action(runtime, action):
    arguments = action.arguments

    def encoded(value):
        return quote(value, safe="")

    if action.name == "get_user_details":
        return runtime.request(
            method="GET",
            path=f"/v1/customers/{encoded(arguments['user_id'])}",
        )
    if action.name == "get_reservation_details":
        return runtime.request(
            method="GET",
            path=f"/v1/reservations/{encoded(arguments['reservation_id'])}",
        )
    if action.name == "search_direct_flight":
        return runtime.request(
            method="GET",
            path="/v1/flight-itineraries",
            query={
                "origin": arguments["origin"],
                "destination": arguments["destination"],
                "departure_date": arguments["date"],
                "stops": 0,
            },
        )
    if action.name == "book_reservation":
        return runtime.request(
            method="POST",
            path="/v1/reservations",
            body={
                "customer_id": arguments["user_id"],
                "trip": {
                    "origin": arguments["origin"],
                    "destination": arguments["destination"],
                    "trip_type": arguments["flight_type"],
                    "cabin": arguments["cabin"],
                    "segments": arguments["flights"],
                },
                "passengers": arguments["passengers"],
                "payment_methods": arguments["payment_methods"],
                "baggage": {
                    "total_bags": arguments["total_baggages"],
                    "paid_bags": arguments["nonfree_baggages"],
                },
                "insurance": arguments["insurance"],
            },
        )
    reservation_id = encoded(arguments.get("reservation_id", ""))
    if action.name == "cancel_reservation":
        return runtime.request(
            method="POST",
            path=f"/v1/reservations/{reservation_id}/cancellations",
        )
    if action.name == "update_reservation_baggages":
        return runtime.request(
            method="PUT",
            path=f"/v1/reservations/{reservation_id}/baggage",
            body={
                "total_bags": arguments["total_baggages"],
                "paid_bags": arguments["nonfree_baggages"],
                "payment_method_id": arguments["payment_id"],
            },
        )
    if action.name == "update_reservation_flights":
        return runtime.request(
            method="PUT",
            path=f"/v1/reservations/{reservation_id}/itinerary",
            body={
                "cabin": arguments["cabin"],
                "segments": arguments["flights"],
                "payment_method_id": arguments["payment_id"],
            },
        )
    if action.name == "update_reservation_passengers":
        return runtime.request(
            method="PUT",
            path=f"/v1/reservations/{reservation_id}/passengers",
            body={"passengers": arguments["passengers"]},
        )
    if action.name == "send_certificate":
        return runtime.request(
            method="POST",
            path=f"/v1/customers/{encoded(arguments['user_id'])}/certificates",
            body={"amount": arguments["amount"]},
        )
    raise AssertionError(f"No Airline+ request mapping for {action.name}")


def _telecom_request_for_reference_action(runtime, action):
    arguments = action.arguments

    def encoded(value):
        return quote(value, safe="")

    customer_id = encoded(arguments.get("customer_id", ""))
    line_id = encoded(arguments.get("line_id", ""))
    line_path = f"/v1/customers/{customer_id}/lines/{line_id}"
    if action.name == "resume_line":
        return runtime.request(method="POST", path=f"{line_path}/resumptions")
    if action.name == "suspend_line":
        return runtime.request(
            method="POST",
            path=f"{line_path}/suspensions",
            body={"reason": arguments["reason"]},
        )
    if action.name == "enable_roaming":
        return runtime.request(
            method="PUT",
            path=f"{line_path}/roaming",
            body={"enabled": True},
        )
    if action.name == "disable_roaming":
        return runtime.request(
            method="PUT",
            path=f"{line_path}/roaming",
            body={"enabled": False},
        )
    if action.name == "refuel_data":
        return runtime.request(
            method="POST",
            path=f"{line_path}/data-refuels",
            body={"amount_gb": arguments["gb_amount"]},
        )
    if action.name == "send_payment_request":
        return runtime.request(
            method="POST",
            path=(
                f"/v1/customers/{customer_id}/bills/"
                f"{encoded(arguments['bill_id'])}/payment-requests"
            ),
        )
    raise AssertionError(f"No Telecom request mapping for {action.name}")


@pytest.mark.parametrize("domain", ["retail_plus", "airline_plus", "telecom"])
def test_all_task_backed_client_operations_preserve_reference_semantics(domain):
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    if domain == "retail_plus":
        from tau2.domains.retail_plus.environment import get_tasks

        request_for_action = _retail_request_for_reference_action
    elif domain == "airline_plus":
        from tau2.domains.airline_plus.environment import get_tasks

        request_for_action = _airline_request_for_reference_action
    else:
        from tau2.domains.telecom.environment import get_tasks

        request_for_action = _telecom_request_for_reference_action
    excluded = {"calculate", "transfer_to_human_agents"}
    task_actions = {
        action.name: (task, action)
        for task in get_tasks()
        for action in task.evaluation_criteria.actions
        if action.requestor == "assistant" and action.name not in excluded
    }

    for action_name, (task, action) in task_actions.items():
        runtime = create_domain_client_api_runtime(domain)
        _initialize_runtime_for_task(runtime, task)
        response = request_for_action(runtime, action)

        assert 200 <= response.status_code < 300, (
            action_name,
            response.model_dump(),
        )
        assert runtime.operation_calls[-1].operation_id == action_name
        assert runtime.operation_calls[-1].arguments == action.arguments


def test_airline_client_api_write_responses_are_resource_scoped():
    from tau2.domains.airline_plus.environment import get_tasks
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    expected_fields = {
        "cancel_reservation": {"reservation_id", "status", "payments"},
        "update_reservation_baggages": {
            "reservation_id",
            "baggage",
            "payments",
        },
        "update_reservation_flights": {"reservation_id", "trip", "payments"},
        "update_reservation_passengers": {"reservation_id", "passengers"},
    }
    task_actions = {
        action.name: (task, action)
        for task in get_tasks()
        for action in task.evaluation_criteria.actions
        if action.name in expected_fields
    }

    assert set(task_actions) == set(expected_fields)
    for action_name, (task, action) in task_actions.items():
        runtime = create_domain_client_api_runtime("airline_plus")
        _initialize_runtime_for_task(runtime, task)

        response = _airline_request_for_reference_action(runtime, action)

        assert 200 <= response.status_code < 300
        assert set(response.body) == expected_fields[action_name]


def test_retail_client_api_write_responses_are_resource_scoped():
    from tau2.domains.retail_plus.environment import get_tasks
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    expected_fields = {
        "modify_pending_order_address": {"order_id", "shipping_address"},
        "modify_pending_order_payment": {"order_id", "payments"},
        "cancel_pending_order": {
            "order_id",
            "status",
            "cancellation",
            "payments",
        },
        "modify_pending_order_items": {"order_id", "status", "items", "payments"},
        "return_delivered_order_items": {
            "order_id",
            "status",
            "return_request",
        },
        "exchange_delivered_order_items": {"order_id", "status", "exchange"},
    }
    task_actions = {
        action.name: (task, action)
        for task in get_tasks()
        for action in task.evaluation_criteria.actions
        if action.name in expected_fields
    }

    assert set(task_actions) == set(expected_fields)
    for action_name, (task, action) in task_actions.items():
        runtime = create_domain_client_api_runtime("retail_plus")
        _initialize_runtime_for_task(runtime, task)

        response = _retail_request_for_reference_action(runtime, action)

        assert 200 <= response.status_code < 300
        assert set(response.body) == expected_fields[action_name]


def test_client_api_runtime_is_the_authoritative_state_owner():
    runtime = _runtime()
    runtime.set_state(
        InitializationData(agent_data={"account": {"balance": 40}}),
        initialization_actions=None,
        message_history=[],
    )

    response = runtime.request(
        method="POST",
        path="/v1/tools/add_credit",
        body={"amount": 2},
    )

    assert response.status_code == 200
    assert response.body == {"balance": 42}
    assert runtime.snapshot() == {"account": {"balance": 42}}


def test_client_api_runtimes_reset_and_isolate_trial_state():
    first = _runtime()
    second = _runtime()
    first.set_state(
        InitializationData(agent_data={"account": {"balance": 1}}),
        initialization_actions=None,
        message_history=[],
    )
    second.set_state(
        InitializationData(agent_data={"account": {"balance": 100}}),
        initialization_actions=None,
        message_history=[],
    )

    first.request(
        method="POST",
        path="/v1/tools/add_credit",
        body={"amount": 4},
    )

    assert first.snapshot() == {"account": {"balance": 5}}
    assert second.snapshot() == {"account": {"balance": 100}}


def test_client_api_runtime_applies_private_initialization_actions():
    runtime = _runtime()

    runtime.set_state(
        InitializationData(agent_data={"account": {"balance": 8}}),
        initialization_actions=[
            EnvFunctionCall(
                env_type="assistant",
                func_name="add_credit",
                arguments={"amount": 3},
            )
        ],
        message_history=[],
    )

    assert runtime.snapshot() == {"account": {"balance": 11}}


def test_developer_setup_actions_run_through_candidate_tools_after_client_reset():
    from tau2.hyper.sandbox.sealed_runner import (
        SealedCandidateEnvironment,
        SealedRunnerConfig,
    )

    class FakeRunner:
        def __init__(self):
            self.calls = []

        def request(self, method, payload=None):
            self.calls.append((method, payload or {}))
            if method == "tool_call":
                return {"prepared": payload["arguments"]["case_id"]}
            return {"ok": True}

        def close(self):
            pass

    runner = FakeRunner()
    runtime = _runtime()
    metadata = {
        "domain": "accounts",
        "policy": "",
        "tools": {
            "prepare_developer_case": {
                "schema": {
                    "type": "function",
                    "function": {
                        "name": "prepare_developer_case",
                        "description": "Prepare one public development case.",
                        "parameters": {
                            "type": "object",
                            "properties": {"case_id": {"type": "string"}},
                            "required": ["case_id"],
                        },
                    },
                },
                "return_schema": {"type": "object"},
                "info": {"tool_type": "write", "mutates_state": True},
                "mutates_state": True,
                "discoverable": False,
            }
        },
    }
    environment = SealedCandidateEnvironment(
        SealedRunnerConfig(
            kit_path=Path.cwd(),
            domain="accounts",
            image="tau2-construction-runtime:contract-v7",
            client_api_mode="rest",
        ),
        metadata=metadata,
        runner=runner,
        client_api_runtime=runtime,
    )
    environment.configure_developer_setup_actions(
        [
            EnvFunctionCall(
                env_type="assistant",
                func_name="prepare_developer_case",
                arguments={"case_id": "known-case"},
            )
        ]
    )

    environment.set_state(None, None, [])

    assert [call for call in runner.calls if call[0] != "sync"] == [
        (
            "reset",
            {
                "agent_data": None,
                "solo_mode": False,
                "client_api_context": {
                    "conversation_id": runtime.context.conversation_id
                },
            },
        ),
        (
            "tool_call",
            {
                "name": "prepare_developer_case",
                "arguments": {"case_id": "known-case"},
            },
        ),
    ]


@pytest.mark.parametrize(
    ("domain", "expected_version", "expected_case_ids"),
    [
        ("retail_plus", 2, {"pending_order", "delivered_order"}),
        (
            "airline_plus",
            2,
            {
                "economy_reservation",
                "basic_economy_reservation",
                "insured_round_trip",
            },
        ),
        ("telecom", 3, {"service_account"}),
        ("banking_knowledge", 2, {"servicing_customer", "application_customer"}),
    ],
)
def test_client_api_development_seed_manifests_are_public_and_stable(
    domain,
    expected_version,
    expected_case_ids,
):
    from tau2.hyper.client_api.development import development_seed_manifest

    manifest = development_seed_manifest(domain)

    assert manifest["version"] == expected_version
    # The source-domain registry name is host runtime wiring; the
    # Developer-facing seed must not carry it anywhere.
    assert "domain" not in manifest
    assert {case["id"] for case in manifest["cases"]} == expected_case_ids
    serialized = json.dumps(manifest).lower()
    assert domain not in serialized
    assert "initialization_data" not in serialized
    assert "initialization_actions" not in serialized
    assert "database" not in serialized


def test_client_api_development_seed_identifiers_match_domain_conventions():
    from tau2.hyper.client_api.development import development_seed_manifest

    retail = development_seed_manifest("retail_plus")
    for case in retail["cases"]:
        assert re.fullmatch(r"[a-z]+_[a-z]+_\d{4}", case["customer_id"])
        assert re.fullmatch(r"#W\d{7}", case["order_id"])
        for kind, identifier in case["payment_method_ids"].items():
            assert re.fullmatch(rf"{kind}_\d{{7}}", identifier)

    airline = development_seed_manifest("airline_plus")
    for case in airline["cases"]:
        assert re.fullmatch(r"[a-z]+_[a-z]+_\d{4}", case["customer_id"])
        assert re.fullmatch(r"[A-Z0-9]{6}", case["reservation_id"])
        assert re.fullmatch(r"credit_card_\d{7}", case["credit_card_id"])
        assert re.fullmatch(r"gift_card_\d{7}", case["gift_card_id"])
        assert re.fullmatch(r"certificate_\d{7}", case["certificate_id"])

    telecom = development_seed_manifest("telecom")
    case = telecom["cases"][0]
    for field, prefix in (
        ("customer_id", "C"),
        ("active_line_id", "L"),
        ("suspended_line_id", "L"),
        ("active_device_id", "D"),
        ("suspended_device_id", "D"),
        ("paid_bill_id", "B"),
        ("issued_bill_id", "B"),
        ("overdue_bill_id", "B"),
    ):
        assert re.fullmatch(rf"{prefix}\d{{4}}", case[field])

    banking = development_seed_manifest("banking_knowledge")
    servicing = banking["cases"][0]
    assert re.fullmatch(r"[a-z0-9]{10}", servicing["customer_id"])
    assert servicing["checking_account_id"] == f"chk_{servicing['customer_id']}"
    assert servicing["savings_account_id"] == f"sav_{servicing['customer_id']}"
    assert servicing["active_debit_card_id"].startswith("dbc_")
    assert servicing["pending_debit_card_id"].startswith("dbc_")
    assert all(
        value.startswith("cc_") for value in servicing["credit_card_account_ids"]
    )
    assert servicing["credit_card_transaction_id"].startswith("txn_")
    assert servicing["bank_transaction_id"].startswith("btxn_")


def test_retail_development_seed_is_publicly_addressable_and_isolated():
    from tau2.hyper.client_api.development import development_seed_manifest
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    manifest = development_seed_manifest("retail_plus")
    first = create_domain_client_api_runtime("retail_plus", development_seed=True)
    second = create_domain_client_api_runtime("retail_plus", development_seed=True)
    evaluation = create_domain_client_api_runtime("retail_plus")
    first.set_state(None, None, [])
    second.set_state(None, None, [])
    pending = next(case for case in manifest["cases"] if case["id"] == "pending_order")
    customer_id = pending["customer_id"]
    order_id = pending["order_id"]

    customer = first.request(method="GET", path=f"/v1/customers/{customer_id}")
    order = first.request(
        method="GET",
        path=f"/v1/orders/{quote(order_id, safe='')}",
    )
    cancelled = first.request(
        method="POST",
        path=f"/v1/orders/{quote(order_id, safe='')}/cancellations",
        body={"reason": "no longer needed"},
    )

    assert customer.status_code == 200
    assert pending["email"] == customer.body["email"]
    assert order.status_code == 200
    assert order.body["status"] == "pending"
    assert cancelled.status_code == 200
    assert first.snapshot()["orders"][order_id]["status"] == "cancelled"
    assert second.snapshot()["orders"][order_id]["status"] == "pending"
    assert (
        evaluation.request(
            method="GET",
            path=f"/v1/orders/{quote(order_id, safe='')}",
        ).status_code
        == 404
    )


def test_retail_development_seed_supports_major_order_workflows():
    from tau2.hyper.client_api.development import development_seed_manifest
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    cases = {
        case["id"]: case for case in development_seed_manifest("retail_plus")["cases"]
    }
    address = {
        "address_line_1": "42 Public API Way",
        "address_line_2": None,
        "city": "Testville",
        "region": "CA",
        "country": "USA",
        "postal_code": "94000",
    }

    def fresh():
        return create_domain_client_api_runtime("retail_plus", development_seed=True)

    pending = cases["pending_order"]
    pending_path = f"/v1/orders/{quote(pending['order_id'], safe='')}"
    runtime = fresh()
    order = runtime.request(method="GET", path=pending_path).body
    item = order["items"][0]
    product = runtime.request(
        method="GET", path=f"/v1/catalog/products/{item['product_id']}"
    ).body
    replacement = next(
        candidate
        for candidate in product["items"]
        if candidate["available"] and candidate["item_id"] != item["item_id"]
    )

    requests = [
        (
            "PUT",
            f"/v1/customers/{pending['customer_id']}/default-shipping-address",
            address,
        ),
        ("PUT", f"{pending_path}/shipping-address", address),
        (
            "PUT",
            f"{pending_path}/payment-method",
            {
                "payment_method_id": pending["payment_method_ids"]["paypal"],
            },
        ),
        (
            "POST",
            f"{pending_path}/cancellations",
            {"reason": "no longer needed"},
        ),
        (
            "POST",
            f"{pending_path}/item-modifications",
            {
                "replacements": [
                    {
                        "existing_item_id": item["item_id"],
                        "replacement_item_id": replacement["item_id"],
                    }
                ],
                "payment_method_id": pending["payment_method_ids"]["credit_card"],
            },
        ),
    ]
    for method, path, body in requests:
        response = fresh().request(method=method, path=path, body=body)
        assert 200 <= response.status_code < 300, response.model_dump()

    delivered = cases["delivered_order"]
    delivered_path = f"/v1/orders/{quote(delivered['order_id'], safe='')}"
    runtime = fresh()
    delivered_order = runtime.request(method="GET", path=delivered_path).body
    delivered_item = delivered_order["items"][0]
    product = runtime.request(
        method="GET", path=f"/v1/catalog/products/{delivered_item['product_id']}"
    ).body
    replacement = next(
        candidate
        for candidate in product["items"]
        if candidate["available"] and candidate["item_id"] != delivered_item["item_id"]
    )
    return_response = fresh().request(
        method="POST",
        path=f"{delivered_path}/returns",
        body={
            "item_ids": [delivered_item["item_id"]],
            "refund_payment_method_id": delivered["payment_method_ids"]["credit_card"],
        },
    )
    exchange_response = fresh().request(
        method="POST",
        path=f"{delivered_path}/exchanges",
        body={
            "replacements": [
                {
                    "existing_item_id": delivered_item["item_id"],
                    "replacement_item_id": replacement["item_id"],
                }
            ],
            "payment_method_id": delivered["payment_method_ids"]["credit_card"],
        },
    )
    assert return_response.status_code == 200
    assert exchange_response.status_code == 200


@pytest.mark.parametrize(
    ("domain", "case_id", "request_spec"),
    [
        (
            "airline_plus",
            "economy_reservation",
            lambda case: {
                "method": "GET",
                "path": f"/v1/reservations/{case['reservation_id']}",
            },
        ),
        (
            "telecom",
            "service_account",
            lambda case: {
                "method": "POST",
                "path": "/v1/customers/search",
                "body": {"phone_number": case["phone_number"]},
            },
        ),
    ],
)
def test_service_domain_development_seeds_are_reachable(domain, case_id, request_spec):
    from tau2.hyper.client_api.development import development_seed_manifest
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    case = next(
        item
        for item in development_seed_manifest(domain)["cases"]
        if item["id"] == case_id
    )
    runtime = create_domain_client_api_runtime(domain, development_seed=True)

    response = runtime.request(**request_spec(case))

    assert response.status_code == 200


def test_airline_development_seed_supports_booking_and_service_workflows():
    from tau2.hyper.client_api.development import development_seed_manifest
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    manifest = development_seed_manifest("airline_plus")
    cases = {case["id"]: case for case in manifest["cases"]}

    def fresh():
        return create_domain_client_api_runtime("airline_plus", development_seed=True)

    expected_shapes = {
        "economy_reservation": ("economy", "one_way", "no"),
        "basic_economy_reservation": ("basic_economy", "one_way", "no"),
        "insured_round_trip": ("economy", "round_trip", "yes"),
    }
    for case_id, expected in expected_shapes.items():
        case = cases[case_id]
        response = fresh().request(
            method="GET", path=f"/v1/reservations/{case['reservation_id']}"
        )
        assert response.status_code == 200
        assert (
            response.body["trip"]["cabin"],
            response.body["trip"]["trip_type"],
            response.body["insurance"],
        ) == expected

    case = cases["economy_reservation"]
    reservation_path = f"/v1/reservations/{case['reservation_id']}"
    baggage = fresh().request(
        method="PUT",
        path=f"{reservation_path}/baggage",
        body={
            "total_bags": 1,
            "paid_bags": 1,
            "payment_method_id": case["credit_card_id"],
        },
    )
    passengers = fresh().request(
        method="PUT",
        path=f"{reservation_path}/passengers",
        body={
            "passengers": [
                {
                    "first_name": "Updated",
                    "last_name": "Traveler",
                    "dob": "1990-01-01",
                }
            ]
        },
    )
    cancellation = fresh().request(
        method="POST", path=f"{reservation_path}/cancellations"
    )
    certificate = fresh().request(
        method="POST",
        path=f"/v1/customers/{case['customer_id']}/certificates",
        body={"amount": 75},
    )
    for response in (baggage, passengers, cancellation, certificate):
        assert 200 <= response.status_code < 300, response.model_dump()

    runtime = fresh()
    existing = runtime.request(method="GET", path=reservation_path).body
    booking_search = manifest["booking_search"]
    itinerary_response = runtime.request(
        method="GET",
        path="/v1/flight-itineraries",
        query={key: value for key, value in booking_search.items() if key != "cabin"},
    )
    itinerary = itinerary_response.body["itineraries"][0]
    selected_segments = []
    total = 0
    for segment in itinerary["segments"]:
        offer = next(
            item
            for item in segment["cabin_offers"]
            if item["cabin"] == booking_search["cabin"]
        )
        selected_segments.append(
            {
                "flight_number": segment["flight_number"],
                "date": segment["departure_date"],
            }
        )
        total += offer["price"]
    booking = runtime.request(
        method="POST",
        path="/v1/reservations",
        body={
            "customer_id": case["customer_id"],
            "trip": {
                "origin": booking_search["origin"],
                "destination": booking_search["destination"],
                "trip_type": "one_way",
                "cabin": booking_search["cabin"],
                "segments": selected_segments,
            },
            "passengers": existing["passengers"],
            "payment_methods": [
                {"payment_id": case["credit_card_id"], "amount": total}
            ],
            "baggage": {"total_bags": 0, "paid_bags": 0},
            "insurance": "no",
        },
    )
    assert itinerary_response.status_code == 200
    assert booking.status_code == 201, booking.model_dump()


def test_telecom_development_seed_supports_service_workflows():
    from tau2.hyper.client_api.development import development_seed_manifest
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    case = development_seed_manifest("telecom")["cases"][0]

    def fresh():
        return create_domain_client_api_runtime("telecom", development_seed=True)

    customer = case["customer_id"]
    active = case["active_line_id"]
    suspended = case["suspended_line_id"]
    requests = [
        (
            "POST",
            f"/v1/customers/{customer}/lines/{active}/suspensions",
            {"reason": "lost device"},
        ),
        (
            "POST",
            f"/v1/customers/{customer}/lines/{suspended}/resumptions",
            None,
        ),
        (
            "POST",
            f"/v1/customers/{customer}/bills/{case['issued_bill_id']}/payment-requests",
            None,
        ),
        (
            "PUT",
            f"/v1/customers/{customer}/lines/{active}/roaming",
            {"enabled": True},
        ),
        (
            "POST",
            f"/v1/customers/{customer}/lines/{active}/data-refuels",
            {"amount_gb": 1},
        ),
    ]
    for method, path, body in requests:
        response = fresh().request(method=method, path=path, body=body)
        assert response.status_code == 200, response.model_dump()


def test_telecom_development_fixtures_cover_customer_device_states():
    from tau2.hyper.client_api.development import (
        apply_development_fixture,
        development_seed_manifest,
    )
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    fixture_ids = {
        item["id"] for item in development_seed_manifest("telecom").get("fixtures", [])
    }
    assert fixture_ids == {
        "connected",
        "airplane_mode",
        "mobile_data_off",
        "roaming_abroad",
        "data_limit_reached",
        "slow_network_mode",
        "broken_apn",
        "broken_mms",
        "missing_sim",
        "data_saver",
        "slow_vpn",
        "missing_app_permission",
        "missing_app_storage_permission",
        "sim_pin_locked",
        "wifi_calling_on",
        "abroad",
        "roaming_on",
        "roaming_off",
        "line_roaming_enabled",
        "line_roaming_disabled",
        "overdue_bill_suspension",
        "contract_end_suspension",
    }

    case = development_seed_manifest("telecom")["cases"][0]
    for fixture_id in fixture_ids:
        runtime = create_domain_client_api_runtime("telecom", development_seed=True)
        apply_development_fixture(runtime.environment, fixture_id)
        user_db = runtime.environment.user_tools.db
        device = user_db.device
        active_line = runtime.environment.tools._get_line_by_id(case["active_line_id"])
        if fixture_id == "connected":
            assert device.data_enabled is True
        elif fixture_id == "airplane_mode":
            assert device.airplane_mode is True
        elif fixture_id == "mobile_data_off":
            assert device.data_enabled is False
        elif fixture_id == "roaming_abroad":
            assert user_db.surroundings.is_abroad is True
            assert device.roaming_enabled is False
        elif fixture_id == "data_limit_reached":
            assert user_db.surroundings.mobile_data_usage_exceeded is True
        elif fixture_id == "slow_network_mode":
            assert device.network_mode_preference.value == "2g_only"
        elif fixture_id == "broken_apn":
            assert device.active_apn_settings.apn_name.value == "broken"
        elif fixture_id == "broken_mms":
            assert device.active_apn_settings.mmsc_url is None
        elif fixture_id == "missing_sim":
            assert device.sim_card_missing is True
        elif fixture_id == "data_saver":
            assert device.data_saver_mode is True
        elif fixture_id == "slow_vpn":
            assert device.vpn_connected is True
            assert device.vpn_details.server_performance.value == "poor"
        elif fixture_id == "missing_app_permission":
            assert device.app_statuses["messaging"].permissions.sms is False
        elif fixture_id == "missing_app_storage_permission":
            assert device.app_statuses["messaging"].permissions.storage is False
        elif fixture_id == "sim_pin_locked":
            assert device.sim_card_status.value == "locked_pin"
        elif fixture_id == "wifi_calling_on":
            assert device.wifi_calling_enabled is True
            assert device.wifi_calling_mms_over_wifi is True
        elif fixture_id == "abroad":
            assert user_db.surroundings.is_abroad is True
            assert device.roaming_enabled is False
        elif fixture_id == "roaming_on":
            assert device.roaming_enabled is True
        elif fixture_id == "roaming_off":
            assert device.roaming_enabled is False
        elif fixture_id == "line_roaming_enabled":
            assert active_line.roaming_enabled is True
        elif fixture_id == "line_roaming_disabled":
            assert active_line.roaming_enabled is False
        elif fixture_id == "overdue_bill_suspension":
            assert active_line.status.value == "Suspended"
            assert active_line.suspension_start_date is not None
            assert active_line.contract_end_date is None
            assert user_db.surroundings.line_active is False
            assert device.network_connection_status.value == "no_service"
        elif fixture_id == "contract_end_suspension":
            assert active_line.status.value == "Suspended"
            assert active_line.contract_end_date is not None
            assert user_db.surroundings.line_active is False
            assert device.network_connection_status.value == "no_service"

    runtime = create_domain_client_api_runtime("telecom", development_seed=True)
    with pytest.raises(ValueError, match="Unknown development fixture"):
        apply_development_fixture(runtime.environment, "private_state_guess")


def test_telecom_development_fixtures_compose_in_listed_order():
    from tau2.hyper.client_api.development import apply_development_fixtures
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    runtime = create_domain_client_api_runtime("telecom", development_seed=True)
    apply_development_fixtures(
        runtime.environment, ["airplane_mode", "broken_apn", "mobile_data_off"]
    )
    user_db = runtime.environment.user_tools.db
    assert user_db.device.airplane_mode is True
    assert user_db.device.active_apn_settings.apn_name.value == "broken"
    assert user_db.device.data_enabled is False

    # Later fixtures win where two touch the same setting.
    runtime = create_domain_client_api_runtime("telecom", development_seed=True)
    apply_development_fixtures(runtime.environment, ["roaming_on", "roaming_abroad"])
    user_db = runtime.environment.user_tools.db
    assert user_db.surroundings.is_abroad is True
    assert user_db.device.roaming_enabled is False

    runtime = create_domain_client_api_runtime("telecom", development_seed=True)
    apply_development_fixtures(runtime.environment, ["roaming_abroad", "roaming_on"])
    user_db = runtime.environment.user_tools.db
    assert user_db.surroundings.is_abroad is True
    assert user_db.device.roaming_enabled is True

    runtime = create_domain_client_api_runtime("telecom", development_seed=True)
    with pytest.raises(ValueError, match="Duplicate development fixtures"):
        apply_development_fixtures(
            runtime.environment, ["airplane_mode", "airplane_mode"]
        )
    with pytest.raises(ValueError, match="Unknown development fixture"):
        apply_development_fixtures(
            runtime.environment, ["airplane_mode", "private_state_guess"]
        )


def test_banking_development_seed_is_reachable_without_private_setup_contract():
    from tau2.domains.banking_knowledge.environment import get_environment
    from tau2.hyper.client_api.development import (
        apply_development_seed,
        development_seed_manifest,
    )

    environment = get_environment(retrieval_variant="no_knowledge")
    apply_development_seed(environment)
    runtime = ClientAPIRuntime(environment)
    case = development_seed_manifest("banking_knowledge")["cases"][0]

    response = runtime.request(
        method="POST",
        path="/v1/customers/search",
        body={"email": case["email"]},
    )

    assert response.status_code == 200
    assert response.body == [
        {
            "customer_id": case["customer_id"],
            "name": "Developer Customer",
        }
    ]
    assert (
        runtime.request(
            method="GET",
            path=f"/v1/customers/{case['customer_id']}/credit-card-accounts",
        ).status_code
        == 200
    )
    assert (
        runtime.request(
            method="GET",
            path=f"/v1/customers/{case['customer_id']}/credit-card-transactions",
        ).status_code
        == 200
    )


def test_banking_development_seed_supports_servicing_workflows():
    from tau2.domains.banking_knowledge.environment import get_environment
    from tau2.hyper.client_api.development import (
        apply_development_seed,
        development_seed_manifest,
    )

    case = development_seed_manifest("banking_knowledge")["cases"][0]

    def fresh():
        environment = get_environment(retrieval_variant="no_knowledge")
        apply_development_seed(environment)
        return ClientAPIRuntime(environment)

    responses = [
        fresh().request(
            method="PUT",
            path=f"/v1/customers/{case['customer_id']}/email",
            body={"email": "updated.customer@example.test"},
        ),
        fresh().request(
            method="PUT",
            path=f"/v1/debit-cards/{case['active_debit_card_id']}/frozen-state",
            body={"frozen": True},
        ),
        fresh().request(
            method="POST",
            path=f"/v1/debit-cards/{case['pending_debit_card_id']}/activation",
            body={
                "activation_kind": "replacement",
                "last_4_digits": "9002",
                "expiration_date": "11/30/2030",
                "cvv": "456",
                "pin": "7290",
            },
        ),
        fresh().request(
            method="POST",
            path=f"/v1/credit-card-accounts/{case['credit_card_account_ids'][0]}/payments",
            body={
                "user_id": case["customer_id"],
                "checking_account_id": case["checking_account_id"],
                "amount": 25,
            },
        ),
        fresh().request(
            method="POST",
            path="/v1/bank-account-transfers",
            body={
                "source_account_id": case["checking_account_id"],
                "destination_account_id": case["savings_account_id"],
                "amount": 25,
            },
        ),
    ]
    for response in responses:
        assert response.status_code == 200, response.model_dump()


def test_client_api_runtime_records_successful_semantic_operations():
    runtime = _runtime()

    runtime.request(
        method="POST",
        path="/v1/tools/add_credit",
        body={"amount": 2},
    )
    runtime.request(
        method="POST",
        path="/v1/tools/add_credit",
        body={"amount": "not-an-integer"},
    )

    assert [call.model_dump() for call in runtime.operation_calls] == [
        {
            "operation_id": "add_credit",
            "arguments": {"amount": 2},
        }
    ]


def test_action_evaluator_includes_client_api_semantic_tool_calls():
    semantic_call = ToolCall(
        id="outer-1:client-api:0",
        name="transfer_to_human_agents",
        arguments={"summary": "Change is unsupported"},
        requestor="assistant",
    )
    trajectory = [
        AssistantMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="outer-1",
                    name="escalate_case",
                    arguments={"reason": "unsupported"},
                    requestor="assistant",
                )
            ],
        ),
        ToolMessage(
            id="outer-1",
            role="tool",
            content="Transfer successful",
            semantic_tool_calls=[semantic_call],
        ),
    ]

    extracted = ActionEvaluator.extract_tool_calls(trajectory)

    assert [call.name for call in extracted] == [
        "escalate_case",
        "transfer_to_human_agents",
    ]


def test_client_api_runtime_returns_rest_errors_instead_of_raising_tool_errors():
    runtime = _runtime()

    missing = runtime.request(method="GET", path="/v1/tools/get_balance")
    unknown = runtime.request(method="POST", path="/v1/tools/not_real", body={})

    assert missing.status_code == 405
    assert missing.body["error"]["code"] == "method_not_allowed"
    assert unknown.status_code == 404
    assert unknown.body["error"]["code"] == "operation_not_found"


def test_client_api_request_body_limit_accepts_boundary_and_rejects_one_byte_over():
    runtime = _runtime()
    empty_body_size = len(json.dumps({"value": ""}, separators=(",", ":")).encode())
    boundary_value = "x" * (CLIENT_API_MAX_REQUEST_BYTES - empty_body_size)

    accepted = runtime.request(
        method="POST",
        path="/v1/tools/echo",
        body={"value": boundary_value},
    )
    rejected = runtime.request(
        method="POST",
        path="/v1/tools/echo",
        body={"value": boundary_value + "x"},
    )

    assert accepted.status_code == 200
    assert accepted.body == boundary_value
    assert rejected.status_code == 413
    assert rejected.body["error"]["code"] == "request_too_large"


def test_client_api_request_limit_counts_query_parameters():
    runtime = _runtime()

    rejected = runtime.request(
        method="POST",
        path="/v1/tools/echo",
        query={"value": "x" * CLIENT_API_MAX_REQUEST_BYTES},
        body=None,
    )

    assert rejected.status_code == 413
    assert rejected.body["error"]["code"] == "request_too_large"


def test_client_api_proxy_rejects_oversized_query_before_transport():
    from tau2.hyper.client_api import ClientAPI

    calls: list[dict] = []
    client_api = ClientAPI(
        lambda request: calls.append(request) or {"status_code": 200}
    )

    rejected = client_api.request(
        "POST",
        "/v1/tools/echo",
        query={"value": "x" * CLIENT_API_MAX_REQUEST_BYTES},
    )

    assert rejected.status_code == 413
    assert rejected.body["error"]["code"] == "request_too_large"
    assert calls == []


def test_client_api_response_body_limit_replaces_oversized_result():
    runtime = _runtime()

    accepted = runtime.request(
        method="POST",
        path="/v1/tools/large_response",
        body={"size": CLIENT_API_MAX_RESPONSE_BYTES - 2},
    )
    rejected = runtime.request(
        method="POST",
        path="/v1/tools/large_response",
        body={"size": CLIENT_API_MAX_RESPONSE_BYTES - 1},
    )

    assert accepted.status_code == 200
    assert len(accepted.body) == CLIENT_API_MAX_RESPONSE_BYTES - 2
    assert rejected.status_code == 502
    assert rejected.body["error"]["code"] == "response_too_large"


def test_client_api_toolkit_has_no_developer_database():
    from tau2.hyper.client_api import ClientAPI, ClientAPIToolKitBase

    calls = []
    client_api = ClientAPI(
        lambda request: calls.append(request)
        or {
            "status_code": 200,
            "body": {"balance": 7},
            "headers": {},
            "elapsed_seconds": 0.01,
        }
    )

    class DeveloperTools(ClientAPIToolKitBase):
        @is_tool(ToolType.READ)
        def get_balance(self) -> int:
            response = self.client_api.request("POST", "/v1/tools/get_balance")
            response.raise_for_status()
            return response.body["balance"]

    toolkit = DeveloperTools(client_api)

    assert toolkit.db is None
    assert toolkit.get_balance() == 7
    assert calls == [
        {
            "method": "POST",
            "path": "/v1/tools/get_balance",
            "query": {},
            "body": None,
            "headers": {},
        }
    ]


def test_candidate_server_loads_api_toolkit_without_loading_database_modules(
    tmp_path: Path, monkeypatch
):
    from tau2.hyper.sandbox.candidate_server import CandidateServer

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "policy.md").write_text("API policy")
    for filename in (
        "data_model.py",
        "user_data_model.py",
        "user_tools.py",
        "environment.py",
    ):
        (workspace / filename).write_text(
            'raise RuntimeError("REST mode must not load database modules")\n'
        )
    (workspace / "tools.py").write_text(
        """
from tau2.environment.toolkit import ToolType, is_tool
from tau2.hyper.client_api import ClientAPIToolKitBase


class Tools(ClientAPIToolKitBase):
    @is_tool(ToolType.READ)
    def ping(self) -> str:
        \"\"\"Return a health check.\"\"\"
        return \"pong\"
"""
    )
    monkeypatch.chdir(tmp_path)

    server = CandidateServer("demo", client_api_mode="rest")
    environment = server.environment

    assert environment.policy == "API policy"
    assert environment.tools.db is None
    assert [tool.name for tool in environment.get_tools()] == ["ping"]
    with pytest.raises(RuntimeError, match="context has not been initialized"):
        _ = environment.tools.client_api.context

    server.dispatch(
        "reset",
        {"client_api_context": {"conversation_id": "conv_candidate"}},
    )

    assert (
        server.environment.tools.client_api.context.conversation_id == "conv_candidate"
    )


def test_api_mode_construction_kit_contains_contract_but_no_database(tmp_path: Path):
    from tau2.hyper.sandbox.kit import build_kit
    from tau2.hyper.task_loader import load_hyper_tau_task

    task = load_hyper_tau_task(
        "008_retail_plus_construction_core_evidence_performance_hard"
    )

    kit = build_kit(task, tmp_path / "kit")

    assert not (kit / "database").exists()
    assert not (kit / "workspace" / "data_model.py").exists()
    assert (kit / "client_api" / "openapi.yaml").exists()
    assert (kit / "client_api" / "development_seed.json").exists()
    assert (kit / "framework" / "client_api_contract.md").exists()
    assert not (kit / "framework" / "toolkit_contract.md").exists()
    assert "ClientAPIToolKitBase" in (kit / "workspace" / "tools.py").read_text()
    readme = (kit / "README.md").read_text()
    assert "client_api" in readme
    assert "framework/client_api_contract.md" in readme
    assert "framework/toolkit_contract.md" not in readme
    framework_readme = (kit / "framework" / "README.md").read_text()
    assert "client_api_contract.md" in framework_readme
    assert "toolkit_contract.md" not in framework_readme
    scenario_contract = (kit / "framework" / "scenario_contract.md").read_text()
    scenario_contract_words = " ".join(scenario_contract.split())
    assert "workspace/tools.py" in scenario_contract
    assert "workspace/data_model.py" not in scenario_contract
    assert (
        "sandbox service implementing `client_api/openapi.yaml`"
        in scenario_contract_words
    )
    assert "Only the documented REST interface" in scenario_contract_words
    assert "canonical assistant" not in scenario_contract.lower()
    assert "reference toolkit" not in scenario_contract.lower()
    assert "cannot use `initialization_data`" in scenario_contract
    assert "Developer's own assistant tools" in scenario_contract
    assert "`development_fixture`" in scenario_contract
    assert "Unknown fixture IDs are rejected" in scenario_contract
    development_seed = json.loads(
        (kit / "client_api" / "development_seed.json").read_text()
    )
    assert "domain" not in development_seed
    assert "retail_plus" not in json.dumps(development_seed)
    assert {case["id"] for case in development_seed["cases"]} == {
        "pending_order",
        "delivered_order",
    }
    contract = json.loads((kit / "client_api" / "openapi.yaml").read_text())
    manifest = json.loads((kit / "framework" / "deployment_manifest.json").read_text())
    # Runtime wiring (mode flags, contract digest, user simulator, source
    # domain) is host-injected; the kit carries only the developer-facing
    # manifest, and the contract version lives only in openapi.yaml.
    assert not (kit / "kit_config.json").exists()
    assert contract["info"]["version"] == "3.1.0"
    assert "client_api_contract_version" not in manifest
    assert "client_api_contract_sha256" not in manifest
    assert "client_api_mode" not in manifest
    assert "use_reference_user_tools" not in manifest
    assert "domain" not in manifest
    assert "user_llm" not in manifest


def test_airline_plus_api_mode_kit_contains_contract_but_no_database(tmp_path: Path):
    from tau2.hyper.sandbox.kit import build_kit
    from tau2.hyper.task_loader import load_hyper_tau_task

    task = load_hyper_tau_task(
        "006_airline_plus_construction_core_evidence_response_phrasing_performance_medium"
    )

    kit = build_kit(task, tmp_path / "kit")

    assert task.test_task_ids == [str(index) for index in range(67)]
    assert not (kit / "database").exists()
    assert not (kit / "workspace" / "data_model.py").exists()
    assert (kit / "framework" / "client_api_contract.md").exists()
    assert not (kit / "framework" / "toolkit_contract.md").exists()
    scenario_contract = (kit / "framework" / "scenario_contract.md").read_text()
    assert "workspace/tools.py" in scenario_contract
    assert "workspace/data_model.py" not in scenario_contract
    contract = json.loads((kit / "client_api" / "openapi.yaml").read_text())
    assert "/v1/reservations" in contract["paths"]
    assert "/v1/flight-itineraries" in contract["paths"]
    assert "/v1/conversations/{conversation_id}/transfers" in contract["paths"]
    assert "ClientAPIToolKitBase" in (kit / "workspace" / "tools.py").read_text()


def test_telecom_api_mode_kit_contains_resource_contract_but_no_database(
    tmp_path: Path,
):
    from tau2.hyper.sandbox.kit import build_kit
    from tau2.hyper.task_loader import load_hyper_tau_task

    task = load_hyper_tau_task(
        "015_telecom_construction_core_evidence_hard_all_defects_performance_medium"
    )

    kit = build_kit(task, tmp_path / "kit")

    assert len(task.test_task_ids) == 119
    assert not (kit / "database").exists()
    assert not (kit / "workspace" / "data_model.py").exists()
    development_seed = json.loads(
        (kit / "client_api" / "development_seed.json").read_text()
    )
    assert {fixture["id"] for fixture in development_seed["fixtures"]} >= {
        "connected",
        "airplane_mode",
        "data_limit_reached",
        "broken_apn",
        "missing_sim",
    }
    contract = json.loads((kit / "client_api" / "openapi.yaml").read_text())
    assert "/v1/customers/search" in contract["paths"]
    assert "/v1/lines/{line_id}" in contract["paths"]
    assert "/v1/customers/{customer_id}/lines/{line_id}/roaming" in contract["paths"]
    assert "ClientAPIToolKitBase" in (kit / "workspace" / "tools.py").read_text()


def test_banking_api_mode_kit_migrates_discovered_operation_documents(
    tmp_path: Path,
):
    from tau2.hyper.client_api.catalogs.banking import operations
    from tau2.hyper.sandbox.kit import build_kit
    from tau2.hyper.task_loader import load_hyper_tau_task

    task = load_hyper_tau_task(
        "027_banking_knowledge_construction_client_api_deposits_business_super"
    )

    # The content assertions below grep text renditions byte-for-byte, so this
    # build pins the text materialization explicitly; the task itself must NOT
    # pin a profile (None = harness default, text+image+video).
    kit = build_kit(task, tmp_path / "kit", modality_profile="text")

    # deposit_opening (19) + deposit_services (25) + business (20).
    assert len(task.test_task_ids) == 64
    assert task.client_api_mode == "rest"
    assert task.modality_profile is None
    default_kit = build_kit(task, tmp_path / "kit_default")
    assert any(
        path.suffix.lower() in {".png", ".mp4"}
        for path in default_kit.rglob("*")
        if path.is_file()
    )
    assert not (kit / "database").exists()
    assert not (kit / "workspace" / "data_model.py").exists()

    contract = json.loads((kit / "client_api" / "openapi.yaml").read_text())
    assert "/v1/customers/search" in contract["paths"]
    assert "/v1/customer-self-service-actions" in contract["paths"]
    assert (
        "/v1/credit-card-transactions/{transaction_id}/rewards" not in contract["paths"]
    )

    reference_names = {
        name for operation in operations() for name in operation.reference_tool_names
    }
    reference_names.update(
        {
            "unlock_discoverable_agent_tool",
            "call_discoverable_agent_tool",
            "initial_transfer_to_human_agent_0218",
            "initial_transfer_to_human_agent_1822",
            "emergency_credit_bureau_incident_transfer_1114",
            "downgrade_credit_card_3847",
        }
    )
    developer_documents = [
        path
        for root_name in ("knowledge_base", "uploaded_materials")
        for path in (kit / root_name).rglob("*")
        if path.is_file()
    ]
    developer_documents.append(kit / "sop.md")
    assert developer_documents
    assert all(
        path.suffix.lower()
        not in {".png", ".jpg", ".jpeg", ".mp4", ".webm", ".m4a", ".wav"}
        for path in developer_documents
    )
    corpus = "\n".join(path.read_text(errors="replace") for path in developer_documents)
    for name in reference_names:
        assert name not in corpus
    assert "database" not in corpus.lower()
    assert "discoverable wrapper" not in corpus.lower()
    assert not re.search(
        r"unlock\s+(?:GET|POST|PUT|PATCH|DELETE)\s+/v1/", corpus, re.IGNORECASE
    )
    assert "session unlock" not in corpus.lower()
    assert "without the unlock" not in corpus.lower()

    transfer_document = json.loads(
        (
            kit
            / "knowledge_base"
            / "doc_bank_accounts_bank_accounts_(general)_010.json"
        ).read_text()
    )["content"]
    assert "POST /v1/bank-account-transfers" in transfer_document
    assert "Request body" in transfer_document
    assert "Response" in transfer_document
    assert "Errors" in transfer_document

    downgrade_document = (kit / "uploaded_materials" / "screenshot_09.txt").read_text()
    assert "POST /v1/credit-card-accounts/{account_id}/downgrades" in downgrade_document
    assert "target_card_type" in downgrade_document
    assert "/transfers" not in downgrade_document

    uploaded_text = "\n".join(
        path.read_text(errors="replace")
        for path in (kit / "uploaded_materials").rglob("*")
        if path.is_file()
    )
    assert "API operation" in uploaded_text
    assert (
        "PATCH /v1/credit-card-transactions/{transaction_id}/rewards" in uploaded_text
    )
    assert "Response" in uploaded_text


def test_banking_api_mode_kit_scopes_knowledge_base_to_subdomain_documents(
    tmp_path: Path,
):
    from tau2.hyper.client_api.catalogs.banking import operations
    from tau2.hyper.sandbox.kit import _withheld_knowledge_base_documents, build_kit
    from tau2.hyper.task_loader import load_hyper_tau_task
    from tau2.utils.utils import DATA_DIR

    task = load_hyper_tau_task(
        "030_banking_knowledge_construction_client_api_card_selection"
    )

    kit = build_kit(task, tmp_path / "kit")

    manifest = json.loads(
        (
            DATA_DIR
            / "tau2"
            / "domains"
            / "banking_knowledge"
            / "subdomains"
            / "manifest.json"
        ).read_text()
    )
    subdomain = manifest["subdomains"]["card_selection"]

    assert task.client_api_mode == "rest"
    assert task.test_task_ids == subdomain["task_ids"]
    assert not (kit / "database").exists()
    assert not (kit / "workspace" / "data_model.py").exists()

    selected = set(task.knowledge_base_documents)
    assert selected == {f"{doc_id}.json" for doc_id in subdomain["doc_ids"]}

    shipped = {
        path.name
        for path in (kit / "knowledge_base").rglob("*")
        if path.is_file() and path.name != "INDEX.md"
    }
    assert shipped == selected - _withheld_knowledge_base_documents(task)
    assert shipped
    assert shipped < selected

    # The scoped kit keeps the full REST rewrite: no reference tool names,
    # wrapper vocabulary, or database language survive in the shipped docs.
    reference_names = {
        name for operation in operations() for name in operation.reference_tool_names
    }
    reference_names.update(
        {"unlock_discoverable_agent_tool", "call_discoverable_agent_tool"}
    )
    corpus = "\n".join(
        path.read_text(errors="replace")
        for path in (kit / "knowledge_base").rglob("*")
        if path.is_file()
    )
    corpus += "\n" + (kit / "sop.md").read_text()
    for name in reference_names:
        assert name not in corpus
    assert "database" not in corpus.lower()

    # Evidence materials pooled across the domain still ship in full; the
    # withheld card-selection documents' facts arrive via uploaded_materials.
    assert (kit / "uploaded_materials").is_dir()


def test_banking_api_mode_kit_builds_with_fully_withheld_knowledge_base(
    tmp_path: Path,
):
    """card_servicing ships zero knowledge-base documents by design.

    Every one of the subdomain's manifest documents is withheld by the core
    evidence bundle, so the scoped kit must still build, ship an empty
    knowledge base, and deliver the facts through uploaded_materials alone.
    The same holds for debit_security.
    """
    from tau2.hyper.sandbox.kit import _withheld_knowledge_base_documents, build_kit
    from tau2.hyper.task_loader import load_hyper_tau_task

    task = load_hyper_tau_task(
        "042_banking_knowledge_construction_client_api_card_servicing"
    )

    kit = build_kit(task, tmp_path / "kit")

    assert task.client_api_mode == "rest"
    # The three wrapper-action reward tasks are excluded from the 30-task
    # partition, matching the 93-task full rest bundle's exclusions.
    assert len(task.test_task_ids) == 27
    assert {"task_032", "task_033", "task_035"}.isdisjoint(task.test_task_ids)

    selected = set(task.knowledge_base_documents)
    assert selected <= _withheld_knowledge_base_documents(task)
    shipped = {
        path.name
        for path in (kit / "knowledge_base").rglob("*")
        if path.is_file() and path.name != "INDEX.md"
    }
    assert shipped == set()
    assert not (kit / "database").exists()
    assert (kit / "uploaded_materials").is_dir()
    assert (kit / "sop.md").is_file()


def test_knowledge_base_document_scoping_rejects_unknown_filenames(tmp_path: Path):
    from tau2.hyper.sandbox.kit import build_kit
    from tau2.hyper.task_loader import load_hyper_tau_task

    task = load_hyper_tau_task(
        "030_banking_knowledge_construction_client_api_card_selection"
    ).model_copy(deep=True)
    task.hyper.knowledge_base_documents.append("doc_missing_from_corpus_999.json")

    with pytest.raises(FileNotFoundError, match="knowledge_base_documents"):
        build_kit(task, tmp_path / "kit")


@pytest.mark.skipif(
    os.getenv("TAU2_RUN_DOCKER_SMOKE") != "1",
    reason="requires the locally built contract-v7 Docker image",
)
def test_sealed_retail_client_api_read_write_composition_and_reset(tmp_path: Path):
    """Exercise the real no-network container and host-owned Client state."""
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime
    from tau2.hyper.sandbox.kit import build_kit
    from tau2.hyper.sandbox.sealed_runner import (
        SealedCandidateEnvironment,
        SealedRunnerConfig,
    )
    from tau2.hyper.task_loader import load_hyper_tau_task

    task = load_hyper_tau_task(
        "008_retail_plus_construction_core_evidence_performance_hard"
    )
    kit = build_kit(task, tmp_path / "kit")
    (kit / "workspace" / "tools.py").write_text(
        textwrap.dedent(
            '''\
            """Minimal sealed smoke adapter for the Retail+ Client API."""

            from tau2.environment.toolkit import ToolType, is_tool
            from tau2.hyper.client_api import ClientAPIToolKitBase


            class Tools(ClientAPIToolKitBase):
                @is_tool(ToolType.READ)
                def lookup_customer(self, user_id: str) -> dict:
                    """Look up a customer.

                    Args:
                        user_id: Client customer identifier.
                    """
                    response = self.client_api.request(
                        "GET",
                        f"/v1/customers/{user_id}",
                    )
                    response.raise_for_status()
                    return response.body

                @is_tool(ToolType.WRITE)
                def change_customer_address(
                    self,
                    user_id: str,
                    address1: str,
                    address2: str,
                    city: str,
                    state: str,
                    country: str,
                    zip: str,
                ) -> dict:
                    """Change a customer's default address.

                    Args:
                        user_id: Client customer identifier.
                        address1: Primary address line.
                        address2: Secondary address line.
                        city: City.
                        state: State.
                        country: Country.
                        zip: Postal code.
                    """
                    response = self.client_api.request(
                        "PUT",
                        f"/v1/customers/{user_id}/default-shipping-address",
                        body={
                            "address_line_1": address1,
                            "address_line_2": address2,
                            "city": city,
                            "region": state,
                            "country": country,
                            "postal_code": zip,
                        },
                    )
                    response.raise_for_status()
                    return response.body

                @is_tool(ToolType.READ)
                def lookup_customer_with_first_order(self, user_id: str) -> dict:
                    """Compose customer and order API calls.

                    Args:
                        user_id: Client customer identifier.
                    """
                    user_response = self.client_api.request(
                        "GET",
                        f"/v1/customers/{user_id}",
                    )
                    user_response.raise_for_status()
                    user = user_response.body
                    order_response = self.client_api.request(
                        "GET",
                        f"/v1/orders/{user['order_ids'][0].replace('#', '%23')}",
                    )
                    order_response.raise_for_status()
                    return {"user": user, "order": order_response.body}
            '''
        )
    )
    config = SealedRunnerConfig(
        kit_path=kit,
        image="tau2-construction-runtime:contract-v7",
        domain="retail_plus",
        client_api_mode="rest",
        client_api_factory=(
            lambda *, solo_mode=False: create_domain_client_api_runtime(
                "retail_plus", solo_mode=solo_mode
            )
        ),
    )
    template = SealedCandidateEnvironment.template(config)
    assert set(template.metadata["tools"]) == {
        "lookup_customer",
        "change_customer_address",
        "lookup_customer_with_first_order",
    }

    first = template.clone()
    second = template.clone()
    try:
        first.set_state(None, None, [])
        second.set_state(None, None, [])
        user_id = next(iter(first.client_api_runtime.snapshot()["users"]))
        original = first.make_tool_call("lookup_customer", user_id=user_id)

        changed = first.make_tool_call(
            "change_customer_address",
            user_id=user_id,
            address1="42 API Boundary Way",
            address2="",
            city="Broker City",
            state="CA",
            country="USA",
            zip="94107",
        )
        composed = first.make_tool_call(
            "lookup_customer_with_first_order", user_id=user_id
        )
        untouched = second.make_tool_call("lookup_customer", user_id=user_id)

        assert changed["default_shipping_address"]["city"] == "Broker City"
        assert composed["user"]["default_shipping_address"]["city"] == "Broker City"
        assert composed["order"]["order_id"] == composed["user"]["order_ids"][0]
        assert (
            untouched["default_shipping_address"]
            == original["default_shipping_address"]
        )
        assert second.client_api_runtime.snapshot()["users"][user_id]["address"] == {
            "address1": original["default_shipping_address"]["address_line_1"],
            "address2": original["default_shipping_address"]["address_line_2"],
            "city": original["default_shipping_address"]["city"],
            "state": original["default_shipping_address"]["region"],
            "country": original["default_shipping_address"]["country"],
            "zip": original["default_shipping_address"]["postal_code"],
        }
        assert (
            first.tools.db.model_dump()["users"][user_id]["address"]["city"]
            == "Broker City"
        )
    finally:
        first.close()
        second.close()


@pytest.mark.skipif(
    os.getenv("TAU2_RUN_DOCKER_SMOKE") != "1",
    reason="requires the locally built contract-v7 Docker image",
)
def test_sealed_airline_plus_client_api_creation_and_transfer(tmp_path: Path):
    """Exercise server-owned IDs and semantic transfer through the API broker."""
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime
    from tau2.hyper.sandbox.kit import build_kit
    from tau2.hyper.sandbox.sealed_runner import (
        SealedCandidateEnvironment,
        SealedRunnerConfig,
    )
    from tau2.hyper.task_loader import load_hyper_tau_task

    task = load_hyper_tau_task(
        "006_airline_plus_construction_core_evidence_response_phrasing_performance_medium"
    )
    kit = build_kit(task, tmp_path / "kit")
    (kit / "workspace" / "tools.py").write_text(
        textwrap.dedent(
            '''\
            """Minimal sealed smoke adapter for the Airline+ Client API."""

            from urllib.parse import quote

            from tau2.environment.toolkit import ToolType, is_tool
            from tau2.hyper.client_api import ClientAPIToolKitBase


            class Tools(ClientAPIToolKitBase):
                @is_tool(ToolType.READ)
                def lookup_traveler(self, user_id: str) -> dict:
                    """Look up a traveler by client identifier."""
                    response = self.client_api.request(
                        "GET",
                        f"/v1/customers/{user_id}",
                    )
                    response.raise_for_status()
                    return response.body

                @is_tool(ToolType.WRITE)
                def issue_travel_credit(self, user_id: str, amount: int) -> dict:
                    """Issue a travel credit with a server-owned identifier."""
                    response = self.client_api.request(
                        "POST",
                        f"/v1/customers/{user_id}/certificates",
                        body={"amount": amount},
                    )
                    response.raise_for_status()
                    return response.body

                @is_tool(ToolType.GENERIC)
                def escalate_case(self, reason: str) -> dict:
                    """Escalate an unsupported request to a person."""
                    conversation_id = quote(
                        self.client_api.context.conversation_id,
                        safe="",
                    )
                    response = self.client_api.request(
                        "POST",
                        f"/v1/conversations/{conversation_id}/transfers",
                        body={"summary": reason},
                    )
                    response.raise_for_status()
                    return response.body
            '''
        )
    )
    config = SealedRunnerConfig(
        kit_path=kit,
        image="tau2-construction-runtime:contract-v7",
        domain="airline_plus",
        client_api_mode="rest",
        client_api_factory=(
            lambda *, solo_mode=False: create_domain_client_api_runtime(
                "airline_plus", solo_mode=solo_mode
            )
        ),
    )
    template = SealedCandidateEnvironment.template(config)
    environment = template.clone()
    try:
        environment.set_state(None, None, [])
        state = environment.client_api_runtime.snapshot()
        user_id = next(iter(state["users"]))
        before = set(state["users"][user_id]["payment_methods"])

        user = environment.make_tool_call("lookup_traveler", user_id=user_id)
        issued = environment.make_tool_call(
            "issue_travel_credit", user_id=user_id, amount=85
        )
        transfer = environment.get_response(
            ToolCall(
                id="transfer-smoke",
                name="escalate_case",
                arguments={"reason": "unsupported itinerary change"},
                requestor="assistant",
            )
        )

        after = environment.client_api_runtime.snapshot()
        new_payment_ids = set(after["users"][user_id]["payment_methods"]) - before
        assert user["customer_id"] == user_id
        assert issued == {
            "certificate_id": "certificate_8471205",
            "customer_id": user_id,
            "amount": 85,
        }
        assert new_payment_ids == {"certificate_8471205"}
        assert [call.name for call in transfer.semantic_tool_calls] == [
            "transfer_to_human_agents"
        ]
        assert transfer.semantic_tool_calls[0].arguments == {
            "summary": "unsupported itinerary change"
        }
    finally:
        environment.close()


@pytest.mark.skipif(
    os.getenv("TAU2_RUN_DOCKER_SMOKE") != "1",
    reason="requires the locally built contract-v7 Docker image",
)
def test_sealed_telecom_client_api_search_and_roaming(tmp_path: Path):
    """Exercise Telecom reads and a consolidated write through the API broker."""
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime
    from tau2.hyper.sandbox.kit import build_kit
    from tau2.hyper.sandbox.sealed_runner import (
        SealedCandidateEnvironment,
        SealedRunnerConfig,
    )
    from tau2.hyper.task_loader import load_hyper_tau_task

    task = load_hyper_tau_task(
        "015_telecom_construction_core_evidence_hard_all_defects_performance_medium"
    )
    kit = build_kit(task, tmp_path / "kit")
    (kit / "workspace" / "tools.py").write_text(
        textwrap.dedent(
            '''\
            """Minimal sealed smoke adapter for the Telecom Client API."""

            from tau2.environment.toolkit import ToolType, is_tool
            from tau2.hyper.client_api import ClientAPIToolKitBase


            class Tools(ClientAPIToolKitBase):
                @is_tool(ToolType.READ)
                def find_customer(self, phone_number: str) -> dict:
                    """Find a customer by a primary or service-line phone number."""
                    response = self.client_api.request(
                        "POST",
                        "/v1/customers/search",
                        body={"phone_number": phone_number},
                    )
                    response.raise_for_status()
                    return response.body

                @is_tool(ToolType.WRITE)
                def set_roaming(
                    self,
                    customer_id: str,
                    line_id: str,
                    enabled: bool,
                ) -> dict:
                    """Set international roaming for a customer line."""
                    response = self.client_api.request(
                        "PUT",
                        f"/v1/customers/{customer_id}/lines/{line_id}/roaming",
                        body={"enabled": enabled},
                    )
                    response.raise_for_status()
                    return response.body
            '''
        )
    )
    config = SealedRunnerConfig(
        kit_path=kit,
        image="tau2-construction-runtime:contract-v7",
        domain="telecom",
        client_api_mode="rest",
        client_api_factory=(
            lambda *, solo_mode=False: create_domain_client_api_runtime(
                "telecom", solo_mode=solo_mode
            )
        ),
    )
    template = SealedCandidateEnvironment.template(config)
    environment = template.clone()
    try:
        environment.set_state(None, None, [])
        state = environment.client_api_runtime.snapshot()
        customer = next(item for item in state["customers"] if item["line_ids"])
        line_id = customer["line_ids"][0]
        line = next(item for item in state["lines"] if item["line_id"] == line_id)

        found = environment.make_tool_call(
            "find_customer", phone_number=line["phone_number"]
        )
        changed = environment.get_response(
            ToolCall(
                id="telecom-roaming-smoke",
                name="set_roaming",
                arguments={
                    "customer_id": customer["customer_id"],
                    "line_id": line_id,
                    "enabled": not line["roaming_enabled"],
                },
                requestor="assistant",
            )
        )

        updated = environment.client_api_runtime.snapshot()
        updated_line = next(
            item for item in updated["lines"] if item["line_id"] == line_id
        )
        assert found["customers"][0]["customer_id"] == customer["customer_id"]
        assert updated_line["roaming_enabled"] is not line["roaming_enabled"]
        assert [call.name for call in changed.semantic_tool_calls] == [
            "enable_roaming" if not line["roaming_enabled"] else "disable_roaming"
        ]
    finally:
        environment.close()


@pytest.mark.skipif(
    os.getenv("TAU2_RUN_DOCKER_SMOKE") != "1",
    reason="requires the locally built contract-v7 Docker image",
)
def test_sealed_banking_subdomain_client_api_search_and_freeze(tmp_path: Path):
    """Exercise a journey-scoped Banking kit through the sealed API broker.

    Uses the debit_security bundle — one of the two whose knowledge base is
    empty after evidence-bundle withholding — so the sealed flow is proven on
    the scoped-kit shape, not just the full-domain bundle: a customer read
    plus a discovered (unadvertised) freeze write, with the semantic action
    mapping intact.
    """
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime
    from tau2.hyper.sandbox.kit import build_kit
    from tau2.hyper.sandbox.sealed_runner import (
        SealedCandidateEnvironment,
        SealedRunnerConfig,
    )
    from tau2.hyper.task_loader import load_hyper_tau_task

    task = load_hyper_tau_task(
        "050_banking_knowledge_construction_client_api_debit_security"
    )
    kit = build_kit(task, tmp_path / "kit")
    (kit / "workspace" / "tools.py").write_text(
        textwrap.dedent(
            '''\
            """Minimal sealed smoke adapter for a scoped Banking Client API kit."""

            from urllib.parse import quote

            from tau2.environment.toolkit import ToolType, is_tool
            from tau2.hyper.client_api import ClientAPIToolKitBase


            class Tools(ClientAPIToolKitBase):
                @is_tool(ToolType.READ)
                def find_customer(self, customer_id: str) -> dict:
                    """Find a banking customer by their customer id."""
                    response = self.client_api.request(
                        "POST",
                        "/v1/customers/search",
                        body={"customer_id": customer_id},
                    )
                    response.raise_for_status()
                    return response.body

                @is_tool(ToolType.WRITE)
                def set_card_frozen(self, card_id: str, frozen: bool) -> dict:
                    """Freeze or unfreeze a debit card."""
                    response = self.client_api.request(
                        "PUT",
                        f"/v1/debit-cards/{quote(card_id, safe='')}/frozen-state",
                        body={"frozen": frozen},
                    )
                    response.raise_for_status()
                    return response.body
            '''
        )
    )
    config = SealedRunnerConfig(
        kit_path=kit,
        image="tau2-construction-runtime:contract-v7",
        domain="banking_knowledge",
        client_api_mode="rest",
        client_api_factory=(
            lambda *, solo_mode=False: create_domain_client_api_runtime(
                "banking_knowledge", solo_mode=solo_mode
            )
        ),
    )
    template = SealedCandidateEnvironment.template(config)
    environment = template.clone()
    try:
        environment.set_state(None, None, [])
        state = environment.client_api_runtime.snapshot()
        card = next(
            item
            for item in state["debit_cards"]["data"].values()
            if item["status"] == "ACTIVE"
        )

        found = environment.make_tool_call("find_customer", customer_id=card["user_id"])
        frozen = environment.get_response(
            ToolCall(
                id="banking-freeze-smoke",
                name="set_card_frozen",
                arguments={"card_id": card["card_id"], "frozen": True},
                requestor="assistant",
            )
        )

        updated = environment.client_api_runtime.snapshot()
        updated_card = updated["debit_cards"]["data"][card["card_id"]]
        assert found[0]["customer_id"] == card["user_id"]
        assert updated_card["status"] != "ACTIVE"
        assert [call.name for call in frozen.semantic_tool_calls] == [
            "freeze_debit_card_3892"
        ]
    finally:
        environment.close()


@pytest.mark.skipif(
    os.getenv("TAU2_RUN_CLIENT_API_SIMULATION_SMOKE") != "1",
    reason="requires live user-simulator and assertion-judge model calls",
)
@pytest.mark.parametrize(
    ("domain", "hyper_task_id", "inner_task_id"),
    [
        (
            "retail_plus",
            "008_retail_plus_construction_core_evidence_performance_hard",
            "130",
        ),
        (
            "airline_plus",
            "006_airline_plus_construction_core_evidence_response_phrasing_performance_medium",
            "13",
        ),
    ],
)
def test_client_api_domain_simulation_smoke(
    tmp_path: Path,
    domain: str,
    hyper_task_id: str,
    inner_task_id: str,
):
    """Run one scored simulated conversation through each maintained API kit."""
    from tau2.hyper._inner import run_inner_simulation
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime
    from tau2.hyper.sandbox.kit import build_kit
    from tau2.hyper.sandbox.sealed_runner import (
        SealedCandidateEnvironment,
        SealedRunnerConfig,
        create_sealed_candidate_agent,
    )
    from tau2.hyper.task_loader import load_hyper_tau_task

    if domain == "retail_plus":
        from tau2.domains.retail_plus.environment import get_tasks
    else:
        from tau2.domains.airline_plus.environment import get_tasks

    hyper_task = load_hyper_tau_task(hyper_task_id)
    kit = build_kit(hyper_task, tmp_path / domain)
    (kit / "workspace" / "policy.md").write_text(
        "Honor direct transfer requests. Airline origins and destinations "
        "cannot be changed on an existing reservation."
    )
    (kit / "workspace" / "tools.py").write_text(
        textwrap.dedent(
            '''\
            """Transfer adapter for a scored Client API simulation smoke."""

            from urllib.parse import quote

            from tau2.environment.toolkit import ToolType, is_tool
            from tau2.hyper.client_api import ClientAPIToolKitBase


            class Tools(ClientAPIToolKitBase):
                @is_tool(ToolType.GENERIC)
                def escalate_case(self, reason: str) -> dict:
                    """Escalate a request that requires a person."""
                    conversation_id = quote(
                        self.client_api.context.conversation_id,
                        safe="",
                    )
                    response = self.client_api.request(
                        "POST",
                        f"/v1/conversations/{conversation_id}/transfers",
                        body={"summary": reason},
                    )
                    response.raise_for_status()
                    return response.body
            '''
        )
    )
    (kit / "workspace" / "agent.py").write_text(
        textwrap.dedent(
            f'''\
            """Deterministic agent for a scored Client API simulation smoke."""

            from tau2.agent.base_agent import HalfDuplexAgent
            from tau2.data_model.message import AssistantMessage, ToolCall, ToolMessage
            from tau2.hyper.agent_context import get_agent_context


            DOMAIN = {domain!r}
            TRANSFER_NOTICE = (
                "YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON."
            )


            class SmokeAgent(HalfDuplexAgent[dict]):
                def __init__(self, actions, policy):
                    super().__init__(tools=list(actions), domain_policy=policy)

                def get_init_state(self, message_history=None):
                    return {{"phase": 0}}

                def generate_next_message(self, message, state):
                    if isinstance(message, ToolMessage):
                        return (
                            AssistantMessage(role="assistant", content=TRANSFER_NOTICE),
                            state,
                        )
                    if DOMAIN == "airline_plus" and state["phase"] == 0:
                        state["phase"] = 1
                        return (
                            AssistantMessage(
                                role="assistant",
                                content=(
                                    "I cannot change an existing reservation's origin "
                                    "or destination, so I cannot change ATL-LAX to "
                                    "ATL-LAS. I can transfer you to a human agent if "
                                    "you would like."
                                ),
                            ),
                            state,
                        )
                    return (
                        AssistantMessage(
                            role="assistant",
                            tool_calls=[
                                ToolCall(
                                    id="semantic-transfer-smoke",
                                    name="escalate_case",
                                    arguments={{
                                        "reason": "Customer requested a human agent"
                                    }},
                                    requestor="assistant",
                                )
                            ],
                        ),
                        state,
                    )


            def create_agent():
                context = get_agent_context()
                return SmokeAgent(
                    context.action_interface.available,
                    "",
                )
            '''
        )
    )

    config = SealedRunnerConfig(
        kit_path=kit,
        image="tau2-construction-runtime:contract-v7",
        domain=domain,
        client_api_mode="rest",
        client_api_factory=(
            lambda *, solo_mode=False: create_domain_client_api_runtime(
                domain, solo_mode=solo_mode
            )
        ),
    )
    template = SealedCandidateEnvironment.template(config)
    inner_task = next(task for task in get_tasks() if str(task.id) == inner_task_id)

    result = run_inner_simulation(
        domain=domain,
        task=inner_task,
        policy=(kit / "workspace" / "policy.md").read_text(),
        agent_llm="gpt-5.6-sol",
        user_llm="gpt-5.5",
        agent_llm_args={"reasoning_effort": "xhigh"},
        user_llm_args={"reasoning_effort": "none"},
        max_steps=20,
        agent_factory=create_sealed_candidate_agent,
        custom_environment=template,
        use_reference_gold_environment=True,
    )

    assert result.reward == 1.0
