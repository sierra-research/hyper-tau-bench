"""Tests for the run_sample_scenarios developer surface."""

import json
from types import SimpleNamespace

import pytest

from tau2.hyper.live_experiment import (
    SampleScenariosContext,
    format_sample_scenario_results,
)
from tau2.hyper.sandbox.callback_broker import (
    CallbackBroker,
    CallbackBrokerError,
    CallbackQuotaError,
)
from tau2.hyper.sandbox.callback_mcp import _tool_definitions
from tau2.hyper.sandbox.kit import _build_construction_readme


def test_sample_scenarios_context_quota():
    calls = []

    def runner() -> str:
        calls.append(1)
        return "results"

    ctx = SampleScenariosContext(runner, max_runs=2)
    assert ctx.max_runs == 2
    first = ctx.run()
    assert first.startswith("results")
    assert "Sample-scenario runs remaining: 1" in first
    assert "Sample-scenario runs remaining: 0" in ctx.run()
    assert ctx.runs_used == 2
    with pytest.raises(RuntimeError, match="quota"):
        ctx.run()
    assert len(calls) == 2


def test_sample_scenarios_context_consumes_run_on_failure():
    def runner() -> str:
        raise ValueError("candidate failed to load")

    ctx = SampleScenariosContext(runner, max_runs=1)
    with pytest.raises(ValueError):
        ctx.run()
    assert ctx.runs_used == 1
    with pytest.raises(RuntimeError, match="quota"):
        ctx.run()


def test_formatted_feedback_never_leaks_message_metadata():
    # Regression: litellm's raw_data echoes the request back, including the
    # user simulator's system prompt with the hidden <scenario> instructions.
    # Both developer-visible formatters must whitelist message fields.
    from tau2.data_model.message import AssistantMessage, ToolCall, UserMessage
    from tau2.hyper.live_experiment import format_live_experiment_results

    secret = "HIDDEN SCENARIO: book a one-way flight"
    messages = [
        UserMessage(
            role="user",
            content="Hi, I need help with a booking.",
            cost=0.01,
            usage={"prompt_tokens": 10},
            raw_data={"instructions": secret, "billing": {"payer": "developer"}},
        ),
        AssistantMessage(
            role="assistant",
            content="Sure, let me look that up.",
            tool_calls=[ToolCall(id="c1", name="lookup", arguments={"q": "res"})],
            raw_data={"instructions": secret},
        ),
    ]
    results = [
        SimpleNamespace(
            reward=1.0,
            messages=messages,
            reward_breakdown=None,
            nl_assertion_details=None,
            response_assertion_details=None,
            grounding_details=None,
        )
    ]
    # Both developer-visible surfaces share the sealed contract: each
    # conversation plus the client's score, no provider metadata and no
    # grading rationale of any kind.
    for formatter in (format_sample_scenario_results, format_live_experiment_results):
        rendered = formatter(results)
        assert secret not in rendered
        for banned in ("raw_data", "usage", "cost", "billing", "timestamp"):
            assert f'"{banned}"' not in rendered
        for banned in (
            "reward_breakdown",
            "nl_assertion",
            "response_assertion",
            "grounding",
            "assertion",
            "justification",
            '"met"',
            '"passed"',
            "mean_reward",
        ):
            assert banned not in rendered
        case = json.loads(rendered)["cases"][0]
        assert sorted(case.keys()) == [
            "case_id",
            "client_review_score",
            "conversation",
        ]
        transcript = case["conversation"]
        assert transcript[0]["content"] == "Hi, I need help with a booking."
        assert transcript[1]["tool_calls"][0]["name"] == "lookup"


def test_format_sample_scenario_results_stable_anonymous_ids():
    results = [SimpleNamespace(reward=reward, messages=[]) for reward in (1.0, 0.0)]
    payload = json.loads(format_sample_scenario_results(results))
    assert payload["scenario_count"] == 2
    assert [case["case_id"] for case in payload["cases"]] == [
        "sample_01",
        "sample_02",
    ]
    assert [case["client_review_score"] for case in payload["cases"]] == [1.0, 0.0]
    assert "client's quality review" in payload["score_note"]


def test_broker_dispatches_run_sample_scenarios(tmp_path):
    ctx = SampleScenariosContext(lambda: "sample output", max_runs=1)
    broker = CallbackBroker(tmp_path, sample_scenarios_context=ctx)
    try:
        assert broker.sample_scenarios_tool_enabled
        result = broker.dispatch(
            token=broker.token, tool="run_sample_scenarios", arguments={}
        )
        assert result.startswith("sample output")
        with pytest.raises(CallbackQuotaError):
            broker.dispatch(
                token=broker.token, tool="run_sample_scenarios", arguments={}
            )
        metadata = broker.metadata()
        assert metadata["sample_scenarios_tool_enabled"] is True
        assert metadata["sample_scenario_runs_used"] == 1
    finally:
        broker.close()


def test_broker_rejects_run_sample_scenarios_without_context(tmp_path):
    broker = CallbackBroker(tmp_path)
    try:
        assert not broker.sample_scenarios_tool_enabled
        with pytest.raises(CallbackBrokerError):
            broker.dispatch(
                token=broker.token, tool="run_sample_scenarios", arguments={}
            )
    finally:
        broker.close()


def test_tool_schema_gated_on_sample_scenarios_flag():
    names_off = {
        schema["name"]
        for schema in _tool_definitions(
            include_client=True,
            include_live_experiment=False,
            include_sample_scenarios=False,
        )
    }
    names_on = {
        schema["name"]
        for schema in _tool_definitions(
            include_client=True,
            include_live_experiment=False,
            include_sample_scenarios=True,
        )
    }
    assert "run_sample_scenarios" not in names_off
    assert "run_sample_scenarios" in names_on


def test_construction_readme_presents_sample_scenarios():
    with_samples = _build_construction_readme(
        "banking_knowledge",
        sample_scenario_count=8,
    )
    assert "8 sample customer scenarios" in with_samples
    assert "run_sample_scenarios" in with_samples
    assert "No sample scenarios are provided" not in with_samples

    without_samples = _build_construction_readme("banking_knowledge")
    assert "No sample scenarios are provided" in without_samples
    assert "run_sample_scenarios" not in without_samples
