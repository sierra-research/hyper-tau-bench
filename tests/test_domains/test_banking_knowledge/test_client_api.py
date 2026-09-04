"""Banking Knowledge coverage for the direct Client API catalog."""

from tau2.domains.banking_knowledge.environment import get_environment
from tau2.domains.banking_knowledge.tools import KnowledgeTools
from tau2.environment.toolkit import DISCOVERABLE_ATTR, ToolType, is_tool
from tau2.hyper.client_api import ClientAPI, ClientAPIToolKitBase
from tau2.hyper.client_api.catalogs.banking import operations
from tau2.hyper.client_api.runtime import ClientAPIRuntime


def test_banking_catalog_routes_every_business_discoverable_operation():
    excluded = {
        "example_agent_tool_0000",
        "initial_transfer_to_human_agent_0218",
        "initial_transfer_to_human_agent_1822",
        "emergency_credit_bureau_incident_transfer_1114",
    }
    expected = {
        name
        for name, method in vars(KnowledgeTools).items()
        if getattr(method, DISCOVERABLE_ATTR, False)
    } - excluded
    catalog = operations()
    discovered = [operation for operation in catalog if not operation.advertised]
    routed = {
        name for operation in discovered for name in operation.reference_tool_names
    }

    assert routed == expected
    assert len({(operation.method, operation.path) for operation in catalog}) == len(
        catalog
    )


def test_banking_catalog_executes_discovered_write_and_isolates_fresh_runtime():
    runtime = ClientAPIRuntime(get_environment(retrieval_variant="no_knowledge"))
    state = runtime.snapshot()
    transaction_id, transaction = next(
        iter(state["credit_card_transaction_history"]["data"].items())
    )
    original_rewards = transaction["rewards_earned"]

    response = runtime.request(
        method="PATCH",
        path=f"/v1/credit-card-transactions/{transaction_id}/rewards",
        body={"new_rewards_earned": "smoke-reward"},
    )

    assert response.status_code == 200
    assert response.body == {
        "transaction_id": transaction_id,
        "rewards_earned": "smoke-reward",
    }
    assert (
        runtime.snapshot()["credit_card_transaction_history"]["data"][transaction_id][
            "rewards_earned"
        ]
        == "smoke-reward"
    )
    assert runtime.operation_calls[0].operation_id == "update_transaction_rewards_3847"

    fresh = ClientAPIRuntime(get_environment(retrieval_variant="no_knowledge"))
    assert (
        fresh.snapshot()["credit_card_transaction_history"]["data"][transaction_id][
            "rewards_earned"
        ]
        == original_rewards
    )


def test_banking_catalog_executes_documented_credit_card_downgrade():
    runtime = ClientAPIRuntime(get_environment(retrieval_variant="no_knowledge"))
    account_id, account = next(
        (
            account_id,
            account,
        )
        for account_id, account in runtime.snapshot()["credit_card_accounts"][
            "data"
        ].items()
        if not account["card_type"].startswith("Business ")
    )

    response = runtime.request(
        method="POST",
        path=f"/v1/credit-card-accounts/{account_id}/downgrades",
        body={
            "user_id": account["user_id"],
            "target_card_type": "Bronze Rewards Card",
        },
    )

    assert response.status_code == 200
    assert (
        runtime.snapshot()["credit_card_accounts"]["data"][account_id]["card_type"]
        == "Bronze Rewards Card"
    )
    assert runtime.operation_calls[0].operation_id == "downgrade_credit_card_3847"


def test_banking_developer_toolkit_runs_deterministic_direct_api_trial():
    runtime = ClientAPIRuntime(get_environment(retrieval_variant="no_knowledge"))
    transaction_id = next(
        iter(runtime.snapshot()["credit_card_transaction_history"]["data"])
    )

    def transport(request):
        return runtime.request(**request).model_dump(mode="json")

    class DeveloperTools(ClientAPIToolKitBase):
        @is_tool(ToolType.WRITE)
        def correct_rewards(self, transaction_id: str, rewards: str) -> str:
            """Correct the rewards recorded on a transaction."""

            response = self.client_api.request(
                "PATCH",
                f"/v1/credit-card-transactions/{transaction_id}/rewards",
                body={"new_rewards_earned": rewards},
            )
            response.raise_for_status()
            return response.body

    tools = DeveloperTools(ClientAPI(transport))
    result = tools.use_tool(
        "correct_rewards",
        transaction_id=transaction_id,
        rewards="deterministic-smoke-reward",
    )

    assert result == {
        "transaction_id": transaction_id,
        "rewards_earned": "deterministic-smoke-reward",
    }
    assert (
        runtime.snapshot()["credit_card_transaction_history"]["data"][transaction_id][
            "rewards_earned"
        ]
        == "deterministic-smoke-reward"
    )
    assert runtime.operation_calls[0].operation_id == "update_transaction_rewards_3847"


def test_banking_catalog_projects_public_customer_account_and_card_resources():
    runtime = ClientAPIRuntime(get_environment(retrieval_variant="no_knowledge"))
    state = runtime.snapshot()
    customer_id = next(iter(state["users"]["data"]))
    checking_account_id = next(
        account_id
        for account_id, account in state["accounts"]["data"].items()
        if account["user_id"] == customer_id and account.get("class") == "checking"
    )

    search = runtime.request(
        method="POST",
        path="/v1/customers/search",
        body={"customer_id": customer_id},
    )
    customer = runtime.request(
        method="GET",
        path=f"/v1/customers/{customer_id}",
    )
    accounts = runtime.request(
        method="GET",
        path=f"/v1/customers/{customer_id}/accounts",
    )
    cards = runtime.request(
        method="GET",
        path=f"/v1/checking-accounts/{checking_account_id}/debit-cards",
    )

    assert search.status_code == 200
    assert search.body == [
        {
            "customer_id": customer_id,
            "name": state["users"]["data"][customer_id]["name"],
        }
    ]
    assert customer.status_code == 200
    assert customer.body["customer_id"] == customer_id
    assert "user_id" not in customer.body
    assert accounts.status_code == 200
    assert set(accounts.body) == {"bank_accounts", "credit_card_accounts"}
    assert all(
        "current_holdings" not in account for account in accounts.body["bank_accounts"]
    )
    assert cards.status_code == 200
    assert all("cvv" not in card for card in cards.body)
    assert all("last_four" in card for card in cards.body)


def test_banking_catalog_normalizes_private_not_found_responses():
    runtime = ClientAPIRuntime(get_environment(retrieval_variant="no_knowledge"))

    response = runtime.request(method="GET", path="/v1/customers/not-a-customer")

    assert response.status_code == 404
    assert response.body == {
        "error": {
            "code": "resource_not_found",
            "message": "The requested resource was not found",
        }
    }


def test_banking_catalog_uses_typed_public_responses_for_every_operation():
    catalog = operations()

    assert len(catalog) == 48
    assert all(operation.response_type is not str for operation in catalog)
