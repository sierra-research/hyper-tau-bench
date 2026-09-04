"""Retry behavior of the inner-loop eval runner on transient provider errors.

Observed in the 2026-08-27 final-12 construction batch: litellm 503s during
final scoring hit ``_run_one``'s catch-all and were scored as task failures
with empty conversations (four tasks zeroed across runs 303/306/204). The
runner now retries transient provider errors with backoff before zeroing,
and tags every synthesized zero-reward result via ``EvaluationResult.error``
so infrastructure zeros stay distinguishable in ``test_details``.
"""

from types import SimpleNamespace

import pytest
from litellm.exceptions import (
    APIConnectionError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)

from tau2.data_model.message import AssistantMessage
from tau2.hyper import _inner
from tau2.hyper._inner import run_inner_simulations
from tau2.hyper.data_model import EvaluationResult


def _service_unavailable() -> ServiceUnavailableError:
    return ServiceUnavailableError(
        "Service Unavailable", llm_provider="openai", model="gpt-5"
    )


@pytest.fixture
def recorded_sleeps(monkeypatch):
    """Capture (and skip) retry backoff sleeps."""
    sleeps: list[float] = []
    monkeypatch.setattr(_inner.time, "sleep", lambda seconds: sleeps.append(seconds))
    return sleeps


def _run_single_task(monkeypatch, fake_run_inner_simulation) -> EvaluationResult:
    monkeypatch.setattr(
        "tau2.hyper._inner.run_inner_simulation", fake_run_inner_simulation
    )
    results = run_inner_simulations(
        [SimpleNamespace(id="task_1")],
        domain="mock",
        policy="",
        agent_llm="mock-agent",
        user_llm="mock-user",
        eval_kind="test",
        max_workers=1,
    )
    (result,) = results
    return result


def test_transient_provider_error_is_retried_to_a_real_result(
    recorded_sleeps, monkeypatch
):
    calls = {"n": 0}

    def fake_run_inner_simulation(*, task, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise _service_unavailable()
        return EvaluationResult(
            task_id=task.id,
            reward=1.0,
            messages=[AssistantMessage(role="assistant", content="resolved")],
        )

    result = _run_single_task(monkeypatch, fake_run_inner_simulation)

    assert calls["n"] == 2
    assert result.reward == 1.0
    assert result.error is None
    assert result.messages, "retry must surface the real conversation"
    assert recorded_sleeps == [_inner._TRANSIENT_ERROR_BACKOFF_SECONDS[0]]


def test_persistent_transient_failure_zeroes_with_infrastructure_tag(
    recorded_sleeps, monkeypatch
):
    calls = {"n": 0}

    def fake_run_inner_simulation(*, task, **kwargs):
        calls["n"] += 1
        raise _service_unavailable()

    result = _run_single_task(monkeypatch, fake_run_inner_simulation)

    assert calls["n"] == _inner._TRANSIENT_ERROR_MAX_ATTEMPTS
    assert result.reward == 0.0
    assert result.messages == []
    assert result.error is not None
    assert result.error.startswith("infrastructure_error: ServiceUnavailableError")
    assert len(recorded_sleeps) == _inner._TRANSIENT_ERROR_MAX_ATTEMPTS - 1


def test_task_execution_error_zeroes_immediately_with_task_tag(
    recorded_sleeps, monkeypatch
):
    calls = {"n": 0}

    def fake_run_inner_simulation(*, task, **kwargs):
        calls["n"] += 1
        raise ValueError("golden DB missing expected row")

    result = _run_single_task(monkeypatch, fake_run_inner_simulation)

    assert calls["n"] == 1, "genuine task-execution failures must not be retried"
    assert result.reward == 0.0
    assert result.error is not None
    assert result.error.startswith("task_error: ValueError")
    assert recorded_sleeps == []


def test_cancellation_during_backoff_returns_untagged_zero(monkeypatch):
    from threading import Event

    stop_event = Event()
    calls = {"n": 0}

    def fake_run_inner_simulation(*, task, **kwargs):
        calls["n"] += 1
        # Cancel the run, then fail transiently: the backoff wait must
        # return the plain cancelled shape, not an infrastructure zero.
        stop_event.set()
        raise _service_unavailable()

    monkeypatch.setattr(
        "tau2.hyper._inner.run_inner_simulation", fake_run_inner_simulation
    )
    (result,) = run_inner_simulations(
        [SimpleNamespace(id="task_1")],
        domain="mock",
        policy="",
        agent_llm="mock-agent",
        user_llm="mock-user",
        eval_kind="test",
        max_workers=1,
        stop_event=stop_event,
    )

    assert calls["n"] == 1
    assert result.reward == 0.0
    assert result.error is None, "cancellation must not be tagged as infra failure"


def test_transient_classifier_covers_provider_error_families():
    assert _inner._is_transient_provider_error(
        RateLimitError("quota", llm_provider="openai", model="gpt-5")
    )
    assert _inner._is_transient_provider_error(
        APIConnectionError("boom", llm_provider="openai", model="gpt-5")
    )
    assert _inner._is_transient_provider_error(
        Timeout("no response", model="gpt-5", llm_provider="openai")
    )
    # Provider text re-wrapped in a generic exception still classifies.
    assert _inner._is_transient_provider_error(RuntimeError("upstream 502 Bad Gateway"))
    assert not _inner._is_transient_provider_error(
        ValueError("db assertion mismatch on transfers table")
    )
