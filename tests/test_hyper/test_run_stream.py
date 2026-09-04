"""Tests for live-run trajectory streaming and workbench discovery."""

import json
import os

import pytest

from tau2.hyper.sandbox.builder import BuildStep
from tau2.hyper.web.run_stream import (
    TrajectoryStreamer,
    load_run_manifest,
    load_run_manifests,
    run_registry_dir,
    trajectory_path_for_run,
)


@pytest.fixture()
def registry(tmp_path, monkeypatch):
    registry_dir = tmp_path / "registry"
    monkeypatch.setenv("TAU2_RUN_REGISTRY_DIR", str(registry_dir))
    return registry_dir


def _make_step(step_idx: int) -> BuildStep:
    return BuildStep(
        step_idx=step_idx,
        role="assistant",
        content=f"thinking about step {step_idx}",
        reasoning_summary=f"summary for step {step_idx}",
        tool_calls=[{"id": "c1", "name": "read_file", "arguments": "{}"}],
        tool_results=[{"id": "c1", "name": "read_file", "result": "x" * 5000}],
        timestamp=1.5,
    )


def test_streamer_writes_jsonl_manifest_and_registry(registry, tmp_path):
    kit = tmp_path / "kit"
    kit.mkdir()

    streamer = TrajectoryStreamer.start(kit, llm="gpt-5.5", max_steps=200)
    assert streamer is not None
    streamer.step(_make_step(1), 200)
    streamer.step(_make_step(2), 200)
    streamer.finish("submitted")

    jsonl_path = registry / f"{streamer.run_id}.trajectory.jsonl"
    events = [json.loads(line) for line in jsonl_path.read_text().splitlines() if line]
    assert [event["type"] for event in events] == [
        "sandbox_step",
        "sandbox_step",
        "sandbox_done",
    ]
    # Step events use the WebDisplay sandbox_step shape, with results capped.
    assert events[0]["step"] == 1
    assert events[0]["max_steps"] == 200
    assert events[0]["thinking"] == "thinking about step 1"
    assert events[0]["reasoning_summary"] == "summary for step 1"
    assert len(events[0]["tool_results"][0]["result"]) == 3000
    assert events[2]["reason"] == "submitted"
    assert events[2]["steps"] == 2

    assert run_registry_dir() == registry
    manifest = json.loads((registry / f"{streamer.run_id}.json").read_text())
    assert manifest["status"] == "finished"
    assert manifest["done_reason"] == "submitted"
    assert manifest["steps"] == 2
    assert manifest["tool_calls"] == 2
    assert manifest["kit_path"] == str(kit)
    assert manifest["trajectory_path"] == str(jsonl_path)


def test_streamer_serializes_structured_tool_results(registry, tmp_path):
    kit = tmp_path / "kit"
    kit.mkdir()
    step = _make_step(1)
    step.tool_results = [
        {"id": "c1", "name": "read_file", "result": {"path": "agent.py"}}
    ]

    streamer = TrajectoryStreamer.start(kit, llm="gpt-5.5", max_steps=0)
    assert streamer is not None
    streamer.step(step, 0)

    event = json.loads(streamer.jsonl_path.read_text())
    assert event["tool_results"] == [
        {"name": "read_file", "result": '{"path": "agent.py"}'}
    ]


def test_repeated_kit_runs_keep_independent_trajectories(registry, tmp_path):
    kit = tmp_path / "kit"
    kit.mkdir()

    first = TrajectoryStreamer.start(kit, llm="gpt-5.5", max_steps=50)
    assert first is not None
    first.step(_make_step(1), 50)
    first.finish("submitted")
    first_contents = first.jsonl_path.read_text()

    second = TrajectoryStreamer.start(kit, llm="gpt-5.5", max_steps=50)
    assert second is not None
    second.step(_make_step(2), 50)
    second.finish("max_steps")

    assert first.run_id != second.run_id
    assert first.jsonl_path != second.jsonl_path
    assert first.jsonl_path.read_text() == first_contents
    assert '"step": 2' in second.jsonl_path.read_text()
    assert len(load_run_manifests()) == 2


def test_finish_uses_authoritative_build_totals(registry, tmp_path):
    kit = tmp_path / "kit"
    kit.mkdir()
    streamer = TrajectoryStreamer.start(kit, llm="gpt-5.5", max_steps=50)
    assert streamer is not None

    streamer.step(_make_step(1), 50)
    streamer.finish(
        "llm_error: unavailable",
        total_steps=2,
        total_tool_calls=3,
    )

    events = [json.loads(line) for line in streamer.jsonl_path.read_text().splitlines()]
    assert events[-1]["type"] == "sandbox_done"
    assert events[-1]["steps"] == 2
    assert events[-1]["tool_calls"] == 3
    manifest = load_run_manifest(streamer.run_id)
    assert manifest is not None
    assert manifest["steps"] == 2
    assert manifest["tool_calls"] == 3


def test_manifest_loading_flags_dead_runs_and_sorts(registry):
    registry.mkdir(parents=True)
    (registry / "old-run.json").write_text(
        json.dumps(
            {
                "run_id": "old-run",
                "pid": 2**22 + 12345,  # certainly not alive
                "status": "running",
                "started_at": 100.0,
            }
        )
    )
    (registry / "live-run.json").write_text(
        json.dumps(
            {
                "run_id": "live-run",
                "pid": os.getpid(),
                "status": "running",
                "started_at": 200.0,
            }
        )
    )
    (registry / "garbage.json").write_text("{not json")

    manifests = load_run_manifests()
    assert [m["run_id"] for m in manifests] == ["live-run", "old-run"]
    assert manifests[0]["status"] == "running" and manifests[0]["alive"]
    # Producer died without closing the stream → surfaced as abandoned.
    assert manifests[1]["status"] == "abandoned" and not manifests[1]["alive"]


def test_manifest_lookup_rejects_traversal(registry):
    registry.mkdir(parents=True)
    assert load_run_manifest("../etc/passwd") is None
    assert load_run_manifest("a/b") is None
    assert load_run_manifest("bad:name") is None
    assert load_run_manifest("missing") is None


def test_manifest_lookup_rejects_mismatched_run_id(registry):
    registry.mkdir(parents=True)
    (registry / "requested-run.json").write_text(
        json.dumps({"run_id": "different-run", "status": "finished"})
    )

    assert load_run_manifest("requested-run") is None


def test_trajectory_path_rejects_symlink_outside_registry(registry, tmp_path):
    registry.mkdir(parents=True)
    secret = tmp_path / "secret.txt"
    secret.write_text("must-not-be-streamed")
    (registry / "linked-run.trajectory.jsonl").symlink_to(secret)

    assert trajectory_path_for_run("linked-run") is None


def test_live_run_endpoints_list_and_replay(registry, tmp_path):
    from starlette.testclient import TestClient

    from tau2.hyper.web.app import app

    kit = tmp_path / "kit"
    kit.mkdir()
    streamer = TrajectoryStreamer.start(kit, llm="gpt-5.5", max_steps=50)
    streamer.step(_make_step(1), 50)
    streamer.finish("max_steps")

    client = TestClient(app)
    runs = client.get("/api/live-runs").json()
    assert [run["run_id"] for run in runs] == [streamer.run_id]
    assert runs[0]["status"] == "finished"

    with client.stream("GET", f"/api/live-runs/{streamer.run_id}/events") as response:
        assert response.status_code == 200
        payloads = [
            json.loads(line[len("data: ") :])
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]
    types = [payload["type"] for payload in payloads]
    assert types[0] == "run_manifest"
    assert "sandbox_step" in types
    assert "sandbox_done" in types
    assert types[-1] == "run_manifest"
    assert payloads[-1]["status"] == "finished"
    # Only the closing manifest is flagged final — clients replaying a
    # finished run must not hang up on the opening manifest.
    assert payloads[0]["final"] is False
    assert payloads[-1]["final"] is True

    missing = client.get("/api/live-runs/nope/events").json()
    assert missing == {"error": "Run not found"}


def test_live_run_endpoint_ignores_manifest_trajectory_path(registry, tmp_path):
    from starlette.testclient import TestClient

    from tau2.hyper.web.app import app

    registry.mkdir(parents=True)
    secret = tmp_path / "secret.txt"
    secret.write_text("must-not-be-streamed")
    run_id = "forged-run"
    (registry / f"{run_id}.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "pid": os.getpid(),
                "status": "finished",
                "started_at": 100.0,
                "trajectory_path": str(secret),
            }
        )
    )
    safe_path = trajectory_path_for_run(run_id)
    assert safe_path is not None
    safe_path.write_text('{"type": "sandbox_done", "reason": "safe"}\n')

    response = TestClient(app).get(f"/api/live-runs/{run_id}/events")

    assert "must-not-be-streamed" not in response.text
    assert '"reason": "safe"' in response.text


def test_trajectory_reader_resets_after_file_replacement(tmp_path):
    from tau2.hyper.web import app as web_app

    trajectory = tmp_path / "run.trajectory.jsonl"
    trajectory.write_text('{"type": "old-event"}\n')
    old_chunk, old_position, old_identity, old_reset = web_app._read_trajectory_chunk(
        trajectory, 0, None
    )
    assert "old-event" in old_chunk
    assert old_reset is False

    replacement = tmp_path / "replacement.jsonl"
    replacement.write_text('{"type": "new-event"}\n')
    replacement.replace(trajectory)
    new_chunk, new_position, new_identity, new_reset = web_app._read_trajectory_chunk(
        trajectory, old_position, old_identity
    )

    assert "new-event" in new_chunk
    assert new_identity != old_identity
    assert new_reset is True

    trajectory.write_text("{}\n")
    truncated_chunk, _, truncated_identity, truncated_reset = (
        web_app._read_trajectory_chunk(trajectory, new_position, new_identity)
    )
    assert truncated_chunk == "{}\n"
    assert truncated_identity == new_identity
    assert truncated_reset is True


def test_live_run_endpoint_closes_if_manifest_disappears(
    registry, tmp_path, monkeypatch
):
    from starlette.testclient import TestClient

    from tau2.hyper.web import app as web_app

    kit = tmp_path / "kit"
    kit.mkdir()
    streamer = TrajectoryStreamer.start(kit, llm="gpt-5.5", max_steps=50)
    assert streamer is not None

    original_read = web_app._read_trajectory_chunk
    manifest_path = registry / f"{streamer.run_id}.json"
    read_count = 0

    def remove_manifest_after_first_eof(path, position, file_identity):
        nonlocal read_count
        result = original_read(path, position, file_identity)
        read_count += 1
        if read_count == 1:
            assert result[0] == ""
            manifest_path.unlink()
        return result

    monkeypatch.setattr(
        web_app,
        "_read_trajectory_chunk",
        remove_manifest_after_first_eof,
    )

    response = TestClient(web_app.app).get(f"/api/live-runs/{streamer.run_id}/events")

    payloads = [
        json.loads(line[len("data: ") :])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    assert [payload["type"] for payload in payloads] == [
        "run_manifest",
        "run_manifest",
    ]
    assert payloads[-1]["status"] == "unavailable"
    assert payloads[-1]["done_reason"] == "manifest_unavailable"
    assert payloads[-1]["final"] is True


def test_live_run_endpoint_drains_after_terminal_race(registry, tmp_path, monkeypatch):
    from starlette.testclient import TestClient

    from tau2.hyper.web import app as web_app

    kit = tmp_path / "kit"
    kit.mkdir()
    streamer = TrajectoryStreamer.start(kit, llm="gpt-5.5", max_steps=50)
    assert streamer is not None

    original_read = web_app._read_trajectory_chunk
    read_count = 0

    def finish_after_first_eof(path, position, file_identity):
        nonlocal read_count
        chunk, new_position, new_identity, reset = original_read(
            path, position, file_identity
        )
        read_count += 1
        if read_count == 1:
            assert chunk == ""
            streamer.finish("submitted")
        return chunk, new_position, new_identity, reset

    monkeypatch.setattr(web_app, "_read_trajectory_chunk", finish_after_first_eof)

    response = TestClient(web_app.app).get(f"/api/live-runs/{streamer.run_id}/events")

    payloads = [
        json.loads(line[len("data: ") :])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    assert [payload["type"] for payload in payloads] == [
        "run_manifest",
        "sandbox_done",
        "run_manifest",
    ]
    assert payloads[-1]["final"] is True
