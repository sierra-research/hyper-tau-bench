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
