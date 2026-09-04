"""Tests for the architecture-neutral custom-agent factory context."""

from pathlib import Path

import pytest

from tau2.data_model.message import AssistantMessage, UserMessage
from tau2.environment.tool import as_tool
from tau2.hyper import agent_context
from tau2.hyper._inner import _instantiate_custom_agent
from tau2.hyper.agent_context import build_agent_context, get_agent_context

RESOURCE_ROOT = Path(__file__).parent


def test_build_agent_context_keeps_inputs_separate():
    context = build_agent_context(
        domain="telecom",
        tools=[],
        resource_root=RESOURCE_ROOT,
        model_configs=[
            {"model": "gpt-5.5", "constraints": {"reasoning_effort": "minimal"}}
        ],
    )

    assert context.action_interface.available == ()
    assert context.resources.root == RESOURCE_ROOT.resolve()
    assert "test_agent_context.py" in context.resources.files
    assert context.model_gateway.available_models == ("gpt-5.5",)
    assert context.model_gateway.models[0].constrained_args == {
        "reasoning_effort": "minimal",
    }
    assert context.runtime_config == {"domain": "telecom"}


def test_kit_resources_read_any_kit_artifact(tmp_path):
    (tmp_path / "rules").mkdir()
    (tmp_path / "rules" / "returns.md").write_text("Return policy")
    context = build_agent_context(
        domain="retail",
        tools=[],
        resource_root=tmp_path,
        model_configs=[{"model": "gpt-5.5", "constraints": {}}],
    )

    assert context.resources.files == ("rules/returns.md",)
    assert context.resources.read_text("rules/returns.md") == "Return policy"
    with pytest.raises(ValueError, match="escapes the kit root"):
        context.resources.path("../hidden.txt")


def test_action_catalog_exposes_metadata_and_runtime_handler():
    def lookup_account(account_id: str) -> str:
        """Look up an account.

        Args:
            account_id: Account to retrieve.
        """
        return f"account:{account_id}"

    context = build_agent_context(
        domain="telecom",
        tools=[as_tool(lookup_account)],
        resource_root=RESOURCE_ROOT,
        model_configs=[{"model": "gpt-5.5", "constraints": {}}],
    )

    assert context.action_interface.catalog.names == ("lookup_account",)
    definition = context.action_interface.definitions[0]
    assert definition.name == "lookup_account"
    assert definition.description == "Look up an account."
    assert definition.input_schema["required"] == ["account_id"]
    assert definition.return_schema["required"] == ["returns"]
    assert context.action_interface.available[0](account_id="abc") == "account:abc"
    assert context.action_interface.select(["lookup_account"])[0].name == (
        "lookup_account"
    )


def test_action_catalog_rejects_duplicate_names():
    def lookup() -> str:
        """Look up data."""
        return "data"

    with pytest.raises(ValueError, match="Action names must be unique"):
        build_agent_context(
            domain="telecom",
            tools=[as_tool(lookup), as_tool(lookup)],
            resource_root=RESOURCE_ROOT,
            model_configs=[{"model": "gpt-5.5", "constraints": {}}],
        )


def test_model_gateway_enforces_constraints_without_selecting_actions(monkeypatch):
    captured = {}

    def fake_generate(**kwargs):
        captured.update(kwargs)
        return UserMessage(role="user", content="response")

    monkeypatch.setattr(agent_context, "generate", fake_generate)
    context = build_agent_context(
        domain="telecom",
        tools=[],
        resource_root=RESOURCE_ROOT,
        model_configs=[
            {
                "model": "gpt-5.5",
                "constraints": {"reasoning_effort": "minimal", "temperature": 0.0},
            }
        ],
    )

    response = context.model_gateway.generate(
        model="gpt-5.5",
        messages=[],
        call_name="agent_component",
        seed=7,
    )

    assert response.content == "response"
    assert captured == {
        "model": "gpt-5.5",
        "messages": [],
        "tools": None,
        "tool_choice": None,
        "call_name": "agent_component",
        "reasoning_effort": "minimal",
        "temperature": 0.0,
        "seed": 7,
    }


def test_model_gateway_rejects_conflicting_constraint(monkeypatch):
    def fail_generate(**_kwargs):
        raise AssertionError("provider must not be called")

    monkeypatch.setattr(agent_context, "generate", fail_generate)
    context = build_agent_context(
        domain="telecom",
        tools=[],
        resource_root=RESOURCE_ROOT,
        model_configs=[
            {"model": "gpt-5.5", "constraints": {"reasoning_effort": "minimal"}}
        ],
    )

    with pytest.raises(
        ValueError,
        match="reasoning_effort must be 'minimal', got 'high'",
    ):
        context.model_gateway.generate(
            model="gpt-5.5",
            messages=[],
            reasoning_effort="high",
        )


def test_model_gateway_selects_allowed_model_with_its_constraints(monkeypatch):
    captured = {}

    def fake_generate(**kwargs):
        captured.update(kwargs)
        return UserMessage(role="user", content="response")

    monkeypatch.setattr(agent_context, "generate", fake_generate)
    context = build_agent_context(
        domain="telecom",
        tools=[],
        resource_root=RESOURCE_ROOT,
        model_configs=[
            {"model": "gpt-5.5", "constraints": {"reasoning_effort": "none"}},
            {"model": "gpt-5.6", "constraints": {"reasoning_effort": "xhigh"}},
        ],
    )

    context.model_gateway.generate(model="gpt-5.6", messages=[], temperature=0.2)

    assert context.model_gateway.available_models == ("gpt-5.5", "gpt-5.6")
    assert captured["model"] == "gpt-5.6"
    assert captured["reasoning_effort"] == "xhigh"
    assert captured["temperature"] == 0.2


def test_model_gateway_accounts_for_every_priced_call(monkeypatch):
    responses = iter(
        [
            AssistantMessage(
                role="assistant",
                content="route",
                usage={"prompt_tokens": 1_000, "completion_tokens": 100},
            ),
            AssistantMessage(
                role="assistant",
                content="answer",
                usage={"prompt_tokens": 2_000, "completion_tokens": 200},
            ),
        ]
    )
    monkeypatch.setattr(agent_context, "generate", lambda **_kwargs: next(responses))
    context = build_agent_context(
        domain="telecom",
        tools=[],
        resource_root=RESOURCE_ROOT,
        model_configs=[
            {
                "model": "priced-model",
                "constraints": {},
                "credit_rates": {
                    "input_per_million": 2.0,
                    "output_per_million": 10.0,
                },
            }
        ],
    )

    context.model_gateway.generate(model="priced-model", messages=[])
    context.model_gateway.generate(model="priced-model", messages=[])

    usage = context.model_gateway.credit_usage
    assert usage is not None
    assert usage["calls"] == 2
    assert usage["prompt_tokens"] == 3_000
    assert usage["completion_tokens"] == 300
    assert usage["total_credits"] == pytest.approx(0.009)
    assert usage["by_model"]["priced-model"]["credits"] == pytest.approx(0.009)


def test_model_gateway_selects_one_of_multiple_configs_for_same_model(monkeypatch):
    captured = {}

    def fake_generate(**kwargs):
        captured.update(kwargs)
        return UserMessage(role="user", content="response")

    monkeypatch.setattr(agent_context, "generate", fake_generate)
    context = build_agent_context(
        domain="telecom",
        tools=[],
        resource_root=RESOURCE_ROOT,
        model_configs=[
            {"model": "gpt-5.5", "constraints": {"reasoning_effort": "none"}},
            {"model": "gpt-5.5", "constraints": {"reasoning_effort": "xhigh"}},
        ],
    )

    context.model_gateway.generate(
        model="gpt-5.5",
        messages=[],
        reasoning_effort="xhigh",
    )

    assert context.model_gateway.available_models == ("gpt-5.5",)
    assert captured["model"] == "gpt-5.5"
    assert captured["reasoning_effort"] == "xhigh"


def _choice_context(monkeypatch, captured):
    def fake_generate(**kwargs):
        captured.update(kwargs)
        return UserMessage(role="user", content="response")

    monkeypatch.setattr(agent_context, "generate", fake_generate)
    return build_agent_context(
        domain="telecom",
        tools=[],
        resource_root=RESOURCE_ROOT,
        model_configs=[
            {
                "model": "gpt-5.5",
                "constraints": {
                    "reasoning_effort": {"one_of": ["high", "medium"]},
                    "temperature": 0.0,
                },
            }
        ],
    )


@pytest.mark.parametrize("effort", ["high", "medium"])
def test_model_gateway_accepts_any_offered_choice(monkeypatch, effort):
    captured = {}
    context = _choice_context(monkeypatch, captured)

    context.model_gateway.generate(
        model="gpt-5.5", messages=[], reasoning_effort=effort
    )

    assert captured["reasoning_effort"] == effort
    # Pinned constraints still apply alongside an open choice.
    assert captured["temperature"] == 0.0


def test_model_gateway_requires_a_choice_to_be_named(monkeypatch):
    context = _choice_context(monkeypatch, {})

    with pytest.raises(ValueError, match="must choose one explicitly"):
        context.model_gateway.generate(model="gpt-5.5", messages=[])


def test_model_gateway_rejects_a_value_outside_the_choice(monkeypatch):
    context = _choice_context(monkeypatch, {})

    with pytest.raises(ValueError, match=r"must be one of \['high', 'medium'\]"):
        context.model_gateway.generate(
            model="gpt-5.5", messages=[], reasoning_effort="none"
        )


def test_validate_request_resolves_choices_without_leaking_the_wrapper(monkeypatch):
    context = _choice_context(monkeypatch, {})

    model, args = context.model_gateway.validate_request(
        "gpt-5.5", {"reasoning_effort": "medium"}
    )

    assert model == "gpt-5.5"
    assert args == {"reasoning_effort": "medium", "temperature": 0.0}


def test_resolve_stock_constraints_takes_the_first_offered_value():
    resolved = agent_context.resolve_stock_constraints(
        {
            "reasoning_effort": {"one_of": ["high", "medium"]},
            "temperature": 0.0,
        }
    )

    assert resolved == {"reasoning_effort": "high", "temperature": 0.0}


def test_model_gateway_rejects_ambiguous_same_model_request():
    context = build_agent_context(
        domain="telecom",
        tools=[],
        resource_root=RESOURCE_ROOT,
        model_configs=[
            {"model": "gpt-5.5", "constraints": {"reasoning_effort": "none"}},
            {"model": "gpt-5.5", "constraints": {"reasoning_effort": "xhigh"}},
        ],
    )

    with pytest.raises(ValueError, match="ambiguous across 2 allowed"):
        context.model_gateway.generate(model="gpt-5.5", messages=[])


def test_model_gateway_rejects_model_outside_allowed_list(monkeypatch):
    monkeypatch.setattr(
        agent_context,
        "generate",
        lambda **_kwargs: pytest.fail("provider must not be called"),
    )
    context = build_agent_context(
        domain="telecom",
        tools=[],
        resource_root=RESOURCE_ROOT,
        model_configs=[{"model": "gpt-5.5", "constraints": {}}],
    )

    with pytest.raises(ValueError, match="Model 'gpt-5.6' is not allowed"):
        context.model_gateway.generate(model="gpt-5.6", messages=[])


def test_custom_agent_factory_reads_run_context_without_arguments():
    captured = []

    class Agent:
        def get_init_state(self, message_history=None):
            return message_history

        def generate_next_message(self, message, state):
            return message, state

    def factory():
        context = get_agent_context()
        captured.append(context)
        return Agent()

    result, model_gateway = _instantiate_custom_agent(
        factory,
        domain="telecom",
        tools=[],
        resource_root=RESOURCE_ROOT,
        model_configs=[
            {"model": "gpt-5.5", "constraints": {"reasoning_effort": "minimal"}}
        ],
    )

    assert result.get_init_state(message_history=[]) == []
    assert model_gateway.credit_usage is None
    assert len(captured) == 1
    assert captured[0].runtime_config == {"domain": "telecom"}


def test_agent_context_is_only_active_during_factory():
    captured = []

    class Agent:
        def get_init_state(self, message_history=None):
            return message_history

        def generate_next_message(self, message, state):
            return message, state

    def factory():
        captured.append(get_agent_context())
        return Agent()

    _instantiate_custom_agent(
        factory,
        domain="telecom",
        tools=[],
        resource_root=RESOURCE_ROOT,
        model_configs=[
            {"model": "gpt-5.5", "constraints": {"reasoning_effort": "minimal"}}
        ],
    )

    assert len(captured) == 1
    with pytest.raises(RuntimeError, match=r"while create_agent\(\) is executing"):
        get_agent_context()


@pytest.mark.parametrize(
    "constraints",
    [
        {"extra_body": {"thinking": {"type": "disabled"}}},
        {"extra_body": {"reasoning": {"enabled": False}}},
        {"thinking": {"type": "disabled"}},
        {"reasoning_effort": "none"},
    ],
)
def test_reasoning_off_pin_recognizes_provider_spellings(constraints):
    assert agent_context.reasoning_off_pin(constraints) is not None


@pytest.mark.parametrize(
    "constraints",
    [
        {},
        {"reasoning_effort": "low"},
        {"extra_body": {"reasoning": {"effort": "low"}}},
        {"extra_body": {"thinking": {"type": "enabled"}}},
        {"reasoning_effort": {"one_of": ["none", "low"]}},
    ],
)
def test_reasoning_off_pin_skips_non_pins(constraints):
    assert agent_context.reasoning_off_pin(constraints) is None


def _reasoning_on_chat_response() -> AssistantMessage:
    return AssistantMessage(
        role="assistant",
        content="answer",
        raw_data={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "answer",
                        "reasoning_content": "Let me think about the policy...",
                    }
                }
            ]
        },
    )


def test_model_gateway_records_reasoning_constraint_violation(monkeypatch):
    monkeypatch.setattr(
        agent_context,
        "generate",
        lambda **_kwargs: _reasoning_on_chat_response(),
    )
    context = build_agent_context(
        domain="airline_plus",
        tools=[],
        resource_root=RESOURCE_ROOT,
        model_configs=[
            {
                "model": "moonshotai/kimi-k2.6",
                "constraints": {"extra_body": {"thinking": {"type": "disabled"}}},
            }
        ],
    )

    context.model_gateway.generate(
        model="moonshotai/kimi-k2.6",
        messages=[],
        call_name="agent_turn",
    )
    context.model_gateway.generate(
        model="moonshotai/kimi-k2.6",
        messages=[],
    )

    violations = context.model_gateway.constraint_violations
    assert violations is not None
    assert violations["violations"] == 2
    entry = violations["by_model"]["moonshotai/kimi-k2.6"]
    assert entry["violations"] == 2
    assert entry["constraint"] == "extra_body.thinking.type='disabled'"
    assert entry["evidence"] == "choices[].message.reasoning_content"
    assert entry["first_call_name"] == "agent_turn"


def test_model_gateway_stays_clean_when_response_honors_the_pin(monkeypatch):
    monkeypatch.setattr(
        agent_context,
        "generate",
        lambda **_kwargs: AssistantMessage(
            role="assistant",
            content="answer",
            raw_data={
                "choices": [{"message": {"role": "assistant", "content": "answer"}}]
            },
        ),
    )
    context = build_agent_context(
        domain="airline_plus",
        tools=[],
        resource_root=RESOURCE_ROOT,
        model_configs=[
            {
                "model": "qwen/qwen3.8-27b",
                "constraints": {"extra_body": {"reasoning": {"enabled": False}}},
            }
        ],
    )

    context.model_gateway.generate(model="qwen/qwen3.8-27b", messages=[])

    assert context.model_gateway.constraint_violations is None


def test_model_gateway_allows_reasoning_from_unconstrained_model(monkeypatch):
    monkeypatch.setattr(
        agent_context,
        "generate",
        lambda **_kwargs: _reasoning_on_chat_response(),
    )
    context = build_agent_context(
        domain="airline_plus",
        tools=[],
        resource_root=RESOURCE_ROOT,
        model_configs=[{"model": "moonshotai/kimi-k3", "constraints": {}}],
    )

    context.model_gateway.generate(model="moonshotai/kimi-k3", messages=[])

    assert context.model_gateway.constraint_violations is None


def test_reasoning_evidence_reads_provider_specific_fields():
    assert (
        agent_context.reasoning_evidence(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "answer",
                            "provider_specific_fields": {
                                "reasoning_content": "hidden thinking"
                            },
                        }
                    }
                ]
            }
        )
        == "choices[].message.provider_specific_fields.reasoning_content"
    )


def test_reasoning_evidence_reads_responses_api_output():
    assert (
        agent_context.reasoning_evidence(
            {
                "output": [
                    {
                        "type": "reasoning",
                        "summary": [{"type": "summary_text", "text": "step one"}],
                    }
                ]
            }
        )
        == "output[reasoning].summary"
    )
    # gpt-5.x with reasoning off still emits an empty reasoning item.
    assert (
        agent_context.reasoning_evidence(
            {"output": [{"type": "reasoning", "summary": [], "content": []}]}
        )
        is None
    )


def test_collect_message_constraint_violations_checks_stock_messages():
    config = {
        "model": "moonshotai/kimi-k2.6",
        "constraints": {"extra_body": {"thinking": {"type": "disabled"}}},
    }
    messages = [
        UserMessage(role="user", content="hi"),
        _reasoning_on_chat_response(),
    ]

    violations = agent_context.collect_message_constraint_violations(messages, config)

    assert violations is not None
    assert violations["violations"] == 1
    assert (
        violations["by_model"]["moonshotai/kimi-k2.6"]["evidence"]
        == "choices[].message.reasoning_content"
    )
    assert (
        agent_context.collect_message_constraint_violations(
            [AssistantMessage(role="assistant", content="clean")],
            config,
        )
        is None
    )
