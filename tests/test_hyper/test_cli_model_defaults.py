"""Regression tests for Hyper-tau CLI task-model defaults."""

import sys

import pytest

from tau2 import cli

TELECOM_TASK_ID = (
    "013_telecom_construction_core_evidence_seeded_all_defects_performance_medium"
)


def test_hyper_tau_cli_does_not_override_task_models(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        sys,
        "argv",
        ["tau2", "hyper-tau", TELECOM_TASK_ID],
    )
    monkeypatch.setattr(cli, "run_hyper_tau", lambda args: captured.update(vars(args)))

    cli.main()

    assert captured["agent_llm"] is None
    assert captured["agent_reasoning_effort"] is None
    assert captured["primary_model_only"] is False
    assert captured["user_llm"] is None
    assert captured["user_reasoning_effort"] is None


def test_hyper_tau_cli_accepts_explicit_inner_model_override(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "tau2",
            "hyper-tau",
            TELECOM_TASK_ID,
            "--agent-llm",
            "gpt-5.6-sol",
            "--agent-reasoning-effort",
            "none",
        ],
    )
    monkeypatch.setattr(cli, "run_hyper_tau", lambda args: captured.update(vars(args)))

    cli.main()

    assert captured["agent_llm"] == "gpt-5.6-sol"
    assert captured["agent_reasoning_effort"] == "none"


def test_hyper_tau_cli_accepts_primary_model_only(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "tau2",
            "hyper-tau",
            TELECOM_TASK_ID,
            "--primary-model-only",
        ],
    )
    monkeypatch.setattr(cli, "run_hyper_tau", lambda args: captured.update(vars(args)))

    cli.main()

    assert captured["primary_model_only"] is True


def test_primary_model_only_rejects_explicit_agent_override():
    from types import SimpleNamespace

    from tau2.hyper.task_loader import load_hyper_tau_task

    task = load_hyper_tau_task(TELECOM_TASK_ID)
    args = SimpleNamespace(
        primary_model_only=True,
        agent_llm="gpt-5.6-luna",
        agent_reasoning_effort=None,
        agent_thinking_budget=None,
    )

    with pytest.raises(ValueError, match="cannot be combined with --agent-llm"):
        cli._resolve_primary_model_override(args, task)


def test_primary_model_only_rejects_a_custom_tier_profile():
    from types import SimpleNamespace

    from tau2.hyper.task_loader import load_hyper_tau_task

    task = load_hyper_tau_task(
        "022_banking_knowledge_construction_kb_performance_medium"
    )
    args = SimpleNamespace(
        primary_model_only=True,
        agent_llm=None,
        agent_reasoning_effort=None,
        agent_thinking_budget=None,
    )

    with pytest.raises(ValueError, match="requires one stock performance tier"):
        cli._resolve_primary_model_override(args, task)


def test_hyper_tau_llm_args_require_model_for_constraint_override():
    assert cli._build_hyper_tau_llm_args(None, None, None) is None

    with pytest.raises(ValueError, match="model must be selected"):
        cli._build_hyper_tau_llm_args(None, "medium", None)


def test_hyper_tau_cli_does_not_override_task_client_model(monkeypatch):
    """--client-llm must default to None so a task's client_llm pin wins."""
    captured = {}
    monkeypatch.setattr(
        sys,
        "argv",
        ["tau2", "hyper-tau", TELECOM_TASK_ID],
    )
    monkeypatch.setattr(cli, "run_hyper_tau", lambda args: captured.update(vars(args)))

    cli.main()

    assert captured["client_llm"] is None
    assert captured["client_reasoning_effort"] is None


def test_client_effort_flag_works_without_an_explicit_client_model():
    """`--client-reasoning-effort` must not require `--client-llm`.

    The effective Client model comes from the task pin or the seat default,
    so the CLI resolves it before validating the effort against the model
    family rather than rejecting the flag outright.
    """
    from tau2.hyper.run_defaults import DEFAULT_CLIENT_LLM

    assert cli._build_hyper_tau_llm_args(DEFAULT_CLIENT_LLM, "low", None) == {
        "reasoning_effort": "low"
    }


def test_hyper_tau_list_tasks_renders_every_task(monkeypatch):
    """The task table must only read fields the schema still defines.

    Regression guard: the table previously rendered a Tags column, which
    raised AttributeError once ``tags`` left the schema.
    """
    monkeypatch.setattr(sys, "argv", ["tau2", "hyper-tau", "--list-tasks"])

    cli.main()
