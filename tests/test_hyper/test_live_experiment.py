"""Tests for one-shot live experiment task partitions and feedback."""

import json
from types import SimpleNamespace

import pytest

from tau2.hyper.data_model import HyperTask
from tau2.hyper.live_experiment import (
    LiveExperimentContext,
    format_live_experiment_results,
)
from tau2.hyper.sandbox.orchestrator import SandboxOrchestrator
from tau2.hyper.task_loader import load_all_hyper_tau_tasks


def test_live_experiment_samples_are_clustered_tenths_of_the_scored_suite():
    # Release tasks carry their live-experiment sample inline instead of
    # partitioning it out into a separate variant bundle: the sample stays
    # inside the scored suite, is drawn at ~10% of it, and is clustered
    # rather than uniformly spread.
    live_tasks = {
        task.id: task
        for task in load_all_hyper_tau_tasks()
        if task.live_experiment_task_ids
    }

    assert set(live_tasks) == {
        "001_airline_plus_construction_core_evidence_all_defects_live_experiment_performance_medium",
        "009_retail_plus_construction_core_evidence_hard_seeded_live_experiment_performance_medium",
        "017_telecom_construction_core_evidence_hard_client_live_experiment_performance_hard",
        "019_banking_knowledge_construction_evidence_corpus_hard_live_experiment",
        "029_banking_knowledge_construction_client_api_deposits_business_super_live_experiment_performance_hard",
    }

    for task_id, task in live_tasks.items():
        selected = task.live_experiment_task_ids
        assert len(set(selected)) == len(selected), task_id
        assert set(selected) <= set(task.test_task_ids), task_id
        assert abs(len(selected) / len(task.test_task_ids) - 0.1) <= 0.01, task_id
        positions = sorted(task.test_task_ids.index(t_id) for t_id in selected)
        assert any(
            right == left + 1
            for left, right in zip(positions, positions[1:], strict=False)
        ), task_id


def test_live_experiment_context_consumes_failed_first_attempt():
    def fail():
        raise RuntimeError("candidate does not load")

    context = LiveExperimentContext(fail)

    with pytest.raises(RuntimeError, match="candidate does not load"):
        context.run()
    with pytest.raises(RuntimeError, match="already been run"):
        context.run()


def test_live_experiment_report_is_persisted_for_recovery(tmp_path):
    # Mirrors the run_local_test artifact: native MCP clients with short
    # timeouts can drop the tool result after the one-shot spend is consumed,
    # so the report must also be recoverable from simulations/ on disk.
    report = json.dumps({"conversation_count": 1, "cases": []})
    context = LiveExperimentContext(lambda: report, workspace_root=tmp_path)

    result = context.run()

    artifact = next((tmp_path / "simulations").glob("live_experiment_*.json"))
    assert artifact.read_text() == report
    relative = artifact.relative_to(tmp_path).as_posix()
    assert result.startswith(report)
    assert f"Saved artifact: {relative}" in result
    assert context.report_path == relative

    # A retry after a client-side timeout points back at the saved report.
    with pytest.raises(RuntimeError, match="already been run") as excinfo:
        context.run()
    assert relative in str(excinfo.value)


def test_live_experiment_failed_attempt_saves_no_artifact(tmp_path):
    def fail():
        raise RuntimeError("candidate does not load")

    context = LiveExperimentContext(fail, workspace_root=tmp_path)

    with pytest.raises(RuntimeError, match="candidate does not load"):
        context.run()

    assert context.report_path is None
    assert not list(tmp_path.rglob("live_experiment_*.json"))
    with pytest.raises(RuntimeError, match="already been run") as excinfo:
        context.run()
    assert "simulations" not in str(excinfo.value)


def test_hyper_task_allows_live_overlap_with_final_partition():
    # Ben, 2026-08-29: the live-experiment sample stays in the scored suite
    # (no guarantee the Developer gets those conversations right, so they
    # still count). Overlap with test_task_ids is allowed.
    task = HyperTask(
        id="overlap",
        source_domain="telecom",
        task_description="test",
        live_experiment_task_ids=["1"],
        test_task_ids=["1", "2"],
    )
    assert task.live_experiment_task_ids == ["1"]

    # Training and live splits stay disjoint: the same conversation cannot be
    # both a repeatable QA sample and one-shot pilot traffic.
    with pytest.raises(ValueError, match="disjoint"):
        HyperTask(
            id="overlap2",
            source_domain="telecom",
            task_description="test",
            training_task_ids=["1"],
            live_experiment_task_ids=["1"],
            test_task_ids=["1", "2"],
        )


def test_live_feedback_uses_opaque_case_ids():
    class Result:
        task_id = "hidden-task-id"
        reward = 1.0
        messages = []
        reward_breakdown = {"DB": 1.0}
        nl_assertion_details = None
        response_assertion_details = None
        grounding_details = None

    feedback = json.loads(format_live_experiment_results([Result()]))

    assert feedback["conversation_count"] == 1
    case = feedback["cases"][0]
    assert case["case_id"] == "live_001"
    assert case["client_review_score"] == 1.0
    assert sorted(case.keys()) == ["case_id", "client_review_score", "conversation"]
    assert "hidden-task-id" not in json.dumps(feedback)
    # Sealed contract: no grading rationale of any kind.
    assert "reward_breakdown" not in json.dumps(feedback)


def test_orchestrator_runs_live_partition_through_sealed_candidate(
    tmp_path, monkeypatch
):
    task = HyperTask(
        id="live_bundle",
        source_domain="telecom",
        task_description="test",
        client_enabled=False,
        live_experiment_task_ids=["live-task"],
        test_task_ids=["final-task"],
    )
    orchestrator = SandboxOrchestrator(task, SimpleNamespace())
    hidden_task = object()
    monkeypatch.setattr(orchestrator, "_load_inner_tasks", lambda ids: [hidden_task])

    environment = SimpleNamespace(close=lambda: None)
    monkeypatch.setattr(
        "tau2.hyper.sandbox.orchestrator.SealedCandidateEnvironment",
        SimpleNamespace(template=lambda config: environment),
    )
    observed = {}

    def fake_run(tasks, **kwargs):
        observed.update({"tasks": tasks, **kwargs})
        return [
            SimpleNamespace(
                task_id="live-task",
                reward=0.5,
                messages=[],
                reward_breakdown=None,
                nl_assertion_details=None,
                response_assertion_details=None,
                grounding_details=None,
            )
        ]

    monkeypatch.setattr(
        "tau2.hyper.sandbox.orchestrator.run_inner_simulations", fake_run
    )

    feedback = json.loads(orchestrator._run_live_experiment(tmp_path))

    assert observed["tasks"] == [hidden_task]
    assert observed["custom_environment"] is environment
    assert observed["eval_kind"] == "live"
    assert observed["use_reference_gold_environment"] is True
    assert feedback["conversation_count"] == 1
    assert feedback["cases"][0]["client_review_score"] == 0.5
