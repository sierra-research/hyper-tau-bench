"""Tests for resolving sandbox limits from CLI and task configuration."""

from types import SimpleNamespace

from tau2.cli import _resolve_hyper_sandbox_limits


def test_explicit_cli_timeout_overrides_task_default():
    args = SimpleNamespace(sandbox_steps=0, sandbox_timeout=10)
    task = SimpleNamespace(sandbox_config={"max_time_seconds": 8 * 60 * 60})

    assert _resolve_hyper_sandbox_limits(args, task) == (0, 10)


def test_task_timeout_applies_when_cli_omits_override():
    args = SimpleNamespace(sandbox_steps=0, sandbox_timeout=None)
    task = SimpleNamespace(sandbox_config={"max_time_seconds": 123, "max_steps": 7})

    assert _resolve_hyper_sandbox_limits(args, task) == (7, 123)


def test_benchmark_defaults_apply_without_task_limits():
    args = SimpleNamespace(sandbox_steps=0, sandbox_timeout=None)
    task = SimpleNamespace(sandbox_config={})

    assert _resolve_hyper_sandbox_limits(args, task) == (0, 8 * 60 * 60)


def test_test_task_limit_keeps_the_task_order():
    from tau2.hyper.sandbox.orchestrator import limit_test_task_ids

    assert limit_test_task_ids(["c", "a", "b"], 0) == ["c", "a", "b"]
    assert limit_test_task_ids(["c", "a", "b"], 2) == ["c", "a"]
    assert limit_test_task_ids(["c", "a", "b"], 9) == ["c", "a", "b"]


def test_agent_models_narrows_the_task_menu():
    from tau2.cli import _resolve_agent_models_override

    menu = [{"model": "a"}, {"model": "b", "constraints": {"x": 1}}, {"model": "b", "constraints": {"x": 2}}]
    task = SimpleNamespace(allowed_agent_models=menu)
    assert _resolve_agent_models_override(SimpleNamespace(agent_models=None), task) is None
    assert _resolve_agent_models_override(SimpleNamespace(agent_models="b"), task) == menu[1:]
    import pytest

    with pytest.raises(ValueError):
        _resolve_agent_models_override(SimpleNamespace(agent_models="zzz"), task)


def test_client_brief_retries_a_transient_error(monkeypatch):
    from tau2.hyper.sandbox.orchestrator import _with_transient_retries
    import litellm

    monkeypatch.setattr("time.sleep", lambda s: None)
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise litellm.ServiceUnavailableError("503", llm_provider="openai", model="gpt-5.5")
        return "brief"

    assert _with_transient_retries(flaky, what="brief") == "brief"
    assert len(calls) == 3


def test_score_only_run_skips_the_build(monkeypatch, tmp_path):
    """A score-only orchestrator never builds the kit nor runs the Developer."""
    from tau2.hyper.sandbox import orchestrator as mod

    class Builder:
        harness_name = "x"

        def build(self, *a, **k):
            raise AssertionError("the Developer must not run in a score-only run")

    monkeypatch.setattr(mod, "build_kit", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no kit build")))
    task = SimpleNamespace(source_domain="retail_plus", live_experiment_task_ids=[], training_task_ids=[])
    orch = mod.SandboxOrchestrator.__new__(mod.SandboxOrchestrator)
    orch.score_only = True
    assert orch.score_only
    assert mod._kit_baseline_commit(tmp_path) is None
