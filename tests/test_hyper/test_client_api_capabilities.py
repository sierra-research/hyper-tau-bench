"""Client-deployed API capability-plane tests."""

import json

import pytest

from tau2.data_model.message import AssistantMessage, ToolCall
from tau2.hyper.client import (
    ClientCapabilityIntent,
    ClientContext,
    ClientSimulator,
    client_capability_control_tools,
)
from tau2.hyper.client_api.capabilities import (
    CapabilityDeploymentSession,
    EnableCapabilityAction,
    OfferCapabilityAction,
)
from tau2.hyper.client_api.defects import load_defect_profile
from tau2.hyper.client_api.runtime import (
    build_openapi_contract,
    create_domain_client_api_runtime,
)
from tau2.hyper.sandbox.kit import build_kit
from tau2.hyper.sandbox.orchestrator import SandboxOrchestrator
from tau2.hyper.task_loader import load_hyper_tau_task


class StubClient:
    def __init__(self, intents=()):
        self.intents = iter(intents)
        self.intent = None

    def generate_response(self, message, state):
        self.intent = next(self.intents, None)
        response = (
            self.intent.response if self.intent else "I can check with the API team."
        )
        return response, state

    def take_capability_intent(self):
        intent = self.intent
        self.intent = None
        return intent


def _profile():
    return load_defect_profile(
        "retail_plus/all_defects_v1", expected_domain="retail_plus"
    )


def _return_request(runtime):
    return runtime.request(
        method="POST",
        path="/v1/orders/does-not-matter/returns",
        body={
            "item_ids": ["item-1"],
            "refund_payment_method_id": "card-1",
        },
    )


def test_missing_capability_is_neither_advertised_nor_routable_initially():
    profile = _profile()
    session = CapabilityDeploymentSession(profile)
    snapshot = session.freeze()
    runtime = create_domain_client_api_runtime(
        "retail_plus",
        development_seed=True,
        defect_profile=profile,
        deployment_snapshot=snapshot,
    )
    contract = build_openapi_contract(
        runtime.environment,
        defect_profile=profile,
    )

    assert "/v1/orders/{order_id}/returns" not in contract["paths"]
    assert _return_request(runtime).status_code == 404


def test_semantic_client_offer_requires_acceptance_before_deployment():
    profile = _profile()
    session = CapabilityDeploymentSession(profile)
    client = StubClient(
        intents=(
            None,
            ClientCapabilityIntent(
                action="offer",
                capability_id="retail_partial_return_v1",
                response=(
                    "I can enable support for sending back only chosen products. "
                    "Would you like me to enable it?"
                ),
            ),
            ClientCapabilityIntent(
                action="enable",
                capability_id="retail_partial_return_v1",
                response="Yes, I'll enable that capability now.",
            ),
        )
    )
    context = ClientContext(
        client=client,
        client_state=object(),
        capability_session=session,
    )
    vague = context.talk("Can you add whatever API is missing?")
    assert vague == "I can check with the API team."
    assert session.freeze().enabled_capability_ids == ()

    offer = context.talk(
        "The interface has no way to send back just the products a customer chose "
        "from a delivered purchase while leaving the other products alone."
    )
    assert "Would you like me to enable it?" in offer
    assert session.freeze().enabled_capability_ids == ()
    assert context.discussions[-1]["capability_offers"] == [
        {
            "type": "offer_capability",
            "capability_id": "retail_partial_return_v1",
        }
    ]

    response = context.talk("Yes, please enable what you just offered.")
    snapshot = session.freeze()
    assert snapshot.enabled_capability_ids == ("retail_partial_return_v1",)
    assert "POST /v1/orders/{order_id}/returns" in response
    assert '"operationId": "createOrderReturn"' in response
    assert context.discussions[-1]["deployment_actions"] == [
        {
            "type": "enable_capability",
            "capability_id": "retail_partial_return_v1",
        }
    ]


def test_capability_cannot_be_enabled_before_client_offer():
    session = CapabilityDeploymentSession(_profile())

    with pytest.raises(ValueError, match="must be offered"):
        session.enable_offered(
            EnableCapabilityAction(capability_id="retail_partial_return_v1")
        )


def test_client_llm_emits_structured_semantic_capability_intent(monkeypatch):
    def fake_generate(**kwargs):
        assert kwargs["tools"][0].name == "respond_about_deployable_capability"
        assert kwargs["tool_choice"] == "required"
        return AssistantMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    name="respond_about_deployable_capability",
                    arguments={
                        "action": "offer",
                        "capability_id": "retail_partial_return_v1",
                        "response": (
                            "I can enable support for returning only the chosen "
                            "products. Would you like me to?"
                        ),
                    },
                )
            ],
        )

    monkeypatch.setattr("tau2.hyper.client.generate", fake_generate)
    client = ClientSimulator(
        llm="fake-client",
        client_instructions="Private capability instructions",
        tools=client_capability_control_tools(),
    )
    state = client.get_init_state()

    response, state = client.generate_response(
        "Customers cannot send back only some products from a delivered purchase.",
        state,
    )

    assert "returning only the chosen products" in response
    assert state.messages[-1].tool_calls is None
    assert client.take_capability_intent() == ClientCapabilityIntent(
        action="offer",
        capability_id="retail_partial_return_v1",
        response=(
            "I can enable support for returning only the chosen products. "
            "Would you like me to?"
        ),
    )


def test_client_capability_normal_response_needs_no_capability_id():
    intent = ClientCapabilityIntent(
        action="respond",
        capability_id=None,
        response="I'm not sure. Can you be more specific?",
    )

    assert intent.capability_id is None


def test_enabled_snapshot_keeps_contract_static_and_updates_runtime_clones():
    profile = _profile()
    session = CapabilityDeploymentSession(profile)
    session.apply(EnableCapabilityAction(capability_id="retail_partial_return_v1"))
    snapshot = session.freeze()

    for _ in range(2):
        runtime = create_domain_client_api_runtime(
            "retail_plus",
            development_seed=True,
            defect_profile=profile,
            deployment_snapshot=snapshot,
        )
        contract = build_openapi_contract(
            runtime.environment,
            defect_profile=profile,
        )
        assert "/v1/orders/{order_id}/returns" not in contract["paths"]
        response = _return_request(runtime)
        assert response.status_code != 404

    with pytest.raises(ValueError, match="allowlisted"):
        session.apply(EnableCapabilityAction(capability_id="invented_endpoint"))
    session.seal()
    with pytest.raises(RuntimeError, match="sealed"):
        session.apply(EnableCapabilityAction(capability_id="retail_partial_return_v1"))


def test_enabled_capability_renders_contract_for_client_response():
    profile = _profile()
    session = CapabilityDeploymentSession(profile)
    session.offer(OfferCapabilityAction(capability_id="retail_partial_return_v1"))
    session.enable_offered(
        EnableCapabilityAction(capability_id="retail_partial_return_v1")
    )
    assert (
        json.loads(session.render_enabled_contract("retail_partial_return_v1"))[
            "operationId"
        ]
        == "createOrderReturn"
    )


def test_orchestrator_keeps_contract_static_and_freezes_enabled_clones(tmp_path):
    class Builder:
        local_test_wiring = None

    task = load_hyper_tau_task(
        "007_retail_plus_construction_core_evidence_seeded_all_defects_performance_easy"
    )
    builder = Builder()
    orchestrator = SandboxOrchestrator(task, builder=builder)
    build_kit(task, tmp_path)
    contract_path = tmp_path / "client_api/openapi.yaml"
    initial_bytes = contract_path.read_bytes()
    initial = json.loads(initial_bytes)
    assert "/v1/orders/{order_id}/returns" not in initial["paths"]

    profile = orchestrator._client_api_defect_profile()
    session = CapabilityDeploymentSession(profile)
    orchestrator._capability_session = session
    orchestrator._apply_sandbox_config_to_builder()
    session.apply(EnableCapabilityAction(capability_id="retail_partial_return_v1"))

    assert contract_path.read_bytes() == initial_bytes
    assert builder.local_test_wiring.capability_snapshot_provider() == session.freeze()

    orchestrator._deployment_snapshot = session.seal()
    config = orchestrator._sealed_runner_config(tmp_path)
    for _ in range(2):
        runtime = config.client_api_factory(solo_mode=False)
        assert _return_request(runtime).status_code != 404
