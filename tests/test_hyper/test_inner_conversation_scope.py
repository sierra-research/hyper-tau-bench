"""Each held-out conversation's model calls are named after it.

``run_inner_simulations`` scopes every simulated conversation as
``<prefix>-<eval_kind>-<task id>`` (``tau2.utils.model_routing.conversation_scope``)
and writes the id on the result, so a provider whose base_url carries
``{conversation}`` receives one conversation per task.
"""

from types import SimpleNamespace

from tau2.hyper import _inner
from tau2.hyper._inner import run_inner_simulations
from tau2.hyper.data_model import EvaluationResult
from tau2.utils import model_routing


def _task(task_id: str):
    return SimpleNamespace(id=task_id)


def _run(monkeypatch, *, prefix, env=None, tasks=("0", "1")):
    seen: dict[str, str | None] = {}

    def fake_run_inner_simulation(*, task, **_kwargs):
        seen[task.id] = model_routing.active_conversation()
        return EvaluationResult(task_id=task.id, reward=1.0, messages=[])

    monkeypatch.setattr(_inner, "run_inner_simulation", fake_run_inner_simulation)
    if env is None:
        monkeypatch.delenv("TAU2_CONVERSATION_PREFIX", raising=False)
    else:
        monkeypatch.setenv("TAU2_CONVERSATION_PREFIX", env)
    results = run_inner_simulations(
        [_task(t) for t in tasks],
        domain="retail_plus",
        policy="",
        agent_llm="gpt-5.6-sol",
        user_llm="gpt-5.5",
        eval_kind="test",
        max_workers=2,
        conversation_prefix=prefix,
    )
    return seen, results


def test_each_task_runs_under_its_own_conversation(monkeypatch):
    seen, results = _run(monkeypatch, prefix="hyper-007-run-arm-b")
    assert seen == {"0": "hyper-007-run-arm-b-test-0", "1": "hyper-007-run-arm-b-test-1"}
    assert [r.conversation_id for r in results] == [
        "hyper-007-run-arm-b-test-0",
        "hyper-007-run-arm-b-test-1",
    ]
    # the scope does not leak past the run
    assert model_routing.active_conversation() is None


def test_prefix_falls_back_to_the_environment(monkeypatch):
    seen, results = _run(monkeypatch, prefix=None, env="hyper-013-run-arm-a")
    assert seen["0"] == "hyper-013-run-arm-a-test-0"
    assert results[0].conversation_id == "hyper-013-run-arm-a-test-0"


def test_no_prefix_means_no_scope(monkeypatch):
    seen, results = _run(monkeypatch, prefix=None)
    assert seen == {"0": None, "1": None}
    assert [r.conversation_id for r in results] == [None, None]
