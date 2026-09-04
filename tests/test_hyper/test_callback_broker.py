"""Focused tests for authenticated native-harness callbacks."""

import os

import pytest

from tau2.hyper.client import ClientContext
from tau2.hyper.live_experiment import LiveExperimentContext
from tau2.hyper.sandbox.callback_broker import (
    CallbackAuthenticationError,
    CallbackBroker,
    CallbackQuotaError,
)
from tau2.hyper.sandbox.callback_mcp import _call_broker


class FakeLocalToolkit:
    def __init__(self):
        self.calls = []

    def run_local_test(self, task_path, *, verbose=False, max_steps=100):
        self.calls.append((task_path, verbose, max_steps))
        return "local result"

    def close(self):
        pass


class FakeClient:
    def generate_response(self, message, state):
        return f"answer to {message}", {"next": state}


def test_broker_authenticates_and_dispatches_local_test(tmp_path):
    toolkit = FakeLocalToolkit()
    broker = CallbackBroker(tmp_path, toolkit=toolkit)

    result = broker.dispatch(
        token=broker.token,
        tool="run_local_test",
        arguments={"task_path": "scenarios/a.json", "verbose": True},
    )

    assert result == "local result"
    assert toolkit.calls == [("scenarios/a.json", True, 100)]
    assert broker.local_tests_used == 1

    with pytest.raises(CallbackAuthenticationError):
        broker.dispatch(
            token="wrong",
            tool="run_local_test",
            arguments={"task_path": "scenarios/a.json"},
        )


def test_broker_enforces_local_test_quota_and_relays_client(tmp_path):
    client_context = ClientContext(
        client=FakeClient(),
        client_state={"turn": 0},
    )
    broker = CallbackBroker(
        tmp_path,
        toolkit=FakeLocalToolkit(),
        client_context=client_context,
        max_local_tests=1,
    )

    broker.dispatch(
        token=broker.token,
        tool="run_local_test",
        arguments={"task_path": "scenario.json"},
    )
    with pytest.raises(CallbackQuotaError):
        broker.dispatch(
            token=broker.token,
            tool="run_local_test",
            arguments={"task_path": "scenario.json"},
        )

    answer = broker.dispatch(
        token=broker.token,
        tool="talk_to_client",
        arguments={"message": "question"},
    )
    assert "answer to question" in answer

    # Client exchanges are uncapped: a second call succeeds.
    answer2 = broker.dispatch(
        token=broker.token,
        tool="talk_to_client",
        arguments={"message": "again"},
    )
    assert "answer to again" in answer2
    assert client_context.turns_used == 2
    assert client_context.discussions == [
        {
            "turn": 1,
            "developer_message": "question",
            "client_response": "answer to question",
        },
        {
            "turn": 2,
            "developer_message": "again",
            "client_response": "answer to again",
        },
    ]


def test_broker_runs_live_experiment_only_once(tmp_path):
    live_experiment = LiveExperimentContext(lambda: "live result")
    broker = CallbackBroker(
        tmp_path,
        toolkit=FakeLocalToolkit(),
        live_experiment_context=live_experiment,
    )

    result = broker.dispatch(
        token=broker.token,
        tool="run_live_experiment",
        arguments={},
    )

    assert result == "live result"
    assert broker.live_experiment_tool_enabled is True
    assert broker.metadata()["live_experiment_used"] is True
    with pytest.raises(CallbackQuotaError, match="already been run"):
        broker.dispatch(
            token=broker.token,
            tool="run_live_experiment",
            arguments={},
        )


def test_broker_retry_error_names_saved_live_experiment_report(tmp_path):
    # A native MCP client can time out waiting for the tool result while the
    # experiment completes host-side. The report is persisted under
    # simulations/, and the retry error names the file so the Developer can
    # recover the results from disk.
    live_experiment = LiveExperimentContext(
        lambda: '{"cases": []}', workspace_root=tmp_path
    )
    broker = CallbackBroker(
        tmp_path,
        toolkit=FakeLocalToolkit(),
        live_experiment_context=live_experiment,
    )

    result = broker.dispatch(
        token=broker.token,
        tool="run_live_experiment",
        arguments={},
    )

    assert "Saved artifact: simulations/live_experiment_" in result
    report_path = live_experiment.report_path
    assert report_path is not None
    assert (tmp_path / report_path).read_text() == '{"cases": []}'

    with pytest.raises(CallbackQuotaError, match="already been run") as excinfo:
        broker.dispatch(
            token=broker.token,
            tool="run_live_experiment",
            arguments={},
        )
    assert report_path in str(excinfo.value)


def test_submit_sets_idempotent_cancellation_signal(tmp_path):
    broker = CallbackBroker(tmp_path, toolkit=FakeLocalToolkit())

    first = broker.dispatch(token=broker.token, tool="submit", arguments={})
    second = broker.dispatch(token=broker.token, tool="submit", arguments={})

    assert "Submission received" in first
    assert "already received" in second
    assert broker.submitted.is_set()


def test_mcp_file_transport_reaches_host_broker(tmp_path, monkeypatch):
    broker = CallbackBroker(tmp_path, toolkit=FakeLocalToolkit())
    monkeypatch.setenv("TAU2_CALLBACK_DIR", os.fspath(broker.callback_dir))
    monkeypatch.setenv("TAU2_CALLBACK_TOKEN", broker.token)
    monkeypatch.setenv("TAU2_CALLBACK_TIMEOUT_SECONDS", "5")

    with broker:
        response = _call_broker("submit", {})

    assert response == {
        "ok": True,
        "result": "Submission received. The current workspace will be evaluated.",
    }
