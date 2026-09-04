"""Tests for durable Hyper-tau run recordings."""

from __future__ import annotations

import json
import re
from types import SimpleNamespace

from tau2.hyper._inner import run_inner_simulations
from tau2.hyper.data_model import EvaluationResult, HyperTauTask, OuterLoopResult
from tau2.hyper.recording import RecordingDisplay
from tau2.hyper.result_serialization import serialize_result_summary


def _task() -> HyperTauTask:
    return HyperTauTask(
        id="checkpoint_task",
        source_domain="mock",
        task_description="Build the mock domain.",
        client_instructions="",
        training_task_ids=[],
        test_task_ids=["task_1", "task_2"],
    )


def test_eval_results_are_checkpointed_after_every_completion(tmp_path):
    task = _task()
    recorder = RecordingDisplay(
        task=task,
        config={"developer_harness": "codex", "developer_llm": "gpt-5.4"},
        checkpoint_dir=tmp_path,
    )

    recorder.show_task_info(task, "mock", max_steps=0)
    recorder.show_eval_task_start("task_1", "test", 0, 2)
    recorder.show_eval_task_start("task_2", "test", 1, 2)
    recorder.show_eval_task_complete("task_1", "test", 1.0, True)

    checkpoint_path = recorder.checkpoint_path
    assert checkpoint_path is not None
    assert checkpoint_path.name.endswith(".in_progress.json")
    first = json.loads(checkpoint_path.read_text())
    assert first["status"] == "in_progress"
    assert first["task_id"] == task.id
    assert first["config"]["developer_harness"] == "codex"
    assert first["progress"]["test"] == {
        "total": 2,
        "completed": 1,
        "passed": 1,
        "pass_rate": 1.0,
        "mean_reward": 1.0,
        "results": [
            {
                "task_id": "task_1",
                "reward": 1.0,
                "passed": True,
            }
        ],
    }

    recorder.show_eval_task_complete("task_2", "test", 0.25, False)

    second = json.loads(checkpoint_path.read_text())
    assert second["progress"]["test"]["completed"] == 2
    assert second["progress"]["test"]["passed"] == 1
    assert second["progress"]["test"]["pass_rate"] == 0.5
    assert second["progress"]["test"]["mean_reward"] == 0.625
    assert not list(tmp_path.glob("*.tmp"))


def test_final_save_replaces_in_progress_checkpoint(tmp_path):
    task = _task()
    config = {"developer_harness": "codex", "developer_llm": "gpt-5.4"}
    recorder = RecordingDisplay(
        task=task,
        config=config,
        checkpoint_dir=tmp_path,
    )
    recorder.show_task_info(task, "mock", max_steps=0)
    recorder.show_eval_task_start("task_1", "test", 0, 1)
    recorder.show_eval_task_complete("task_1", "test", 1.0, True)
    checkpoint_path = recorder.checkpoint_path
    assert checkpoint_path is not None and checkpoint_path.exists()

    result = OuterLoopResult(
        domain="mock",
        final_test_reward=1.0,
        total_outer_steps=1,
        client_turns_used=0,
    )
    final_path = recorder.save(task=task, result=result, config=config)

    assert final_path.exists()
    assert final_path.name.startswith(f"{task.id}_")
    assert not final_path.name.endswith(".in_progress.json")
    assert not checkpoint_path.exists()
    saved = json.loads(final_path.read_text())
    assert saved["status"] == "complete"
    assert saved["result"] == serialize_result_summary(result)
    assert {
        "base_policy",
        "solution_policy",
        "initial_test_reward",
        "recovery_ratio",
        "evaluate_calls",
    }.isdisjoint(saved["result"])
    assert saved["progress"]["test"]["pass_rate"] == 1.0


def test_same_second_saves_for_same_task_produce_distinct_files(tmp_path):
    task = _task()
    first = RecordingDisplay(task=task, config={"run": "a"}, checkpoint_dir=tmp_path)
    second = RecordingDisplay(task=task, config={"run": "b"}, checkpoint_dir=tmp_path)
    # Worst case for concurrent runs of the same task: identical start instant.
    second.started_at = first.started_at

    first_path = first.save(task=task)
    second_path = second.save(task=task)

    assert first_path != second_path
    assert first_path.exists() and second_path.exists()
    assert json.loads(first_path.read_text())["config"] == {"run": "a"}
    assert json.loads(second_path.read_text())["config"] == {"run": "b"}


def test_final_filename_has_microsecond_resolution_and_resaves_reuse_it(tmp_path):
    task = _task()
    recorder = RecordingDisplay(task=task, checkpoint_dir=tmp_path)

    first_path = recorder.save(task=task)
    second_path = recorder.save(task=task)

    assert re.fullmatch(rf"{task.id}_\d{{8}}_\d{{6}}_\d{{6}}\.json", first_path.name), (
        first_path.name
    )
    assert second_path == first_path
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_none_sandbox_tool_result_is_recorded_as_empty_string(tmp_path):
    recorder = RecordingDisplay(checkpoint_dir=tmp_path)

    recorder.show_sandbox_step(
        step=1,
        max_steps=0,
        thinking=None,
        tool_calls=None,
        tool_results=[{"name": "submit", "result": None}],
    )

    assert recorder.events[-1]["tool_results"] == [{"name": "submit", "result": ""}]


def test_structured_sandbox_tool_result_is_recorded_as_json(tmp_path):
    recorder = RecordingDisplay(checkpoint_dir=tmp_path)

    recorder.show_sandbox_step(
        step=1,
        max_steps=0,
        thinking=None,
        tool_calls=None,
        tool_results=[{"name": "read_file", "result": {"path": "agent.py"}}],
    )

    assert recorder.events[-1]["tool_results"] == [
        {"name": "read_file", "result": '{"path": "agent.py"}'}
    ]


def test_inner_simulation_batch_persists_live_pass_rate(tmp_path, monkeypatch):
    task = _task()
    recorder = RecordingDisplay(task=task, checkpoint_dir=tmp_path)

    def fake_run_inner_simulation(*, task, **kwargs):
        reward = 1.0 if task.id == "task_1" else 0.0
        return EvaluationResult(task_id=task.id, reward=reward)

    monkeypatch.setattr(
        "tau2.hyper._inner.run_inner_simulation", fake_run_inner_simulation
    )

    results = run_inner_simulations(
        [SimpleNamespace(id="task_1"), SimpleNamespace(id="task_2")],
        domain="mock",
        policy="",
        agent_llm="mock-agent",
        user_llm="mock-user",
        display=recorder,
        eval_kind="test",
        max_workers=2,
    )

    assert [result.task_id for result in results] == ["task_1", "task_2"]
    checkpoint_path = recorder.checkpoint_path
    assert checkpoint_path is not None
    progress = json.loads(checkpoint_path.read_text())["progress"]["test"]
    assert progress["completed"] == 2
    assert progress["passed"] == 1
    assert progress["pass_rate"] == 0.5


def test_restarting_suite_immediately_resets_disk_checkpoint(tmp_path):
    task = _task()
    recorder = RecordingDisplay(task=task, checkpoint_dir=tmp_path)
    recorder.show_eval_task_start("task_1", "test", 0, 1)
    recorder.show_eval_task_complete("task_1", "test", 1.0, True)
    checkpoint_path = recorder.checkpoint_path
    assert checkpoint_path is not None

    recorder.show_eval_task_start("task_2", "test", 0, 1)

    progress = json.loads(checkpoint_path.read_text())["progress"]["test"]
    assert progress == {
        "total": 1,
        "completed": 0,
        "passed": 0,
        "pass_rate": 0.0,
        "mean_reward": 0.0,
        "results": [],
    }
