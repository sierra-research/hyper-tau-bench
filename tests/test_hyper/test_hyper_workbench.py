"""Tests for the Hyper-τ web construction workbench."""

from queue import Queue
from types import SimpleNamespace

from tau2.data_model.tasks import NLAssertion
from tau2.hyper.response_phrasing import (
    load_selected_response_phrasing_rule_pack_for_task,
)
from tau2.hyper.task_loader import load_hyper_tau_task
from tau2.hyper.web.app import _load_validation_tasks
from tau2.hyper.web.web_display import WebDisplay

RETAIL_PLUS_HARD_TASK_ID = (
    "009_retail_plus_construction_core_evidence_hard_seeded_live_experiment"
    "_performance_medium"
)


def _nl_assertion_key(assertion: str | NLAssertion) -> str:
    if isinstance(assertion, NLAssertion):
        return assertion.id
    return assertion


def test_workbench_validation_uses_composed_response_phrasing_pack():
    task = load_hyper_tau_task(
        "006_airline_plus_construction_core_evidence"
        "_response_phrasing_performance_medium"
    )
    pack = load_selected_response_phrasing_rule_pack_for_task(task)

    scoring_tasks = _load_validation_tasks(task)

    assert pack is not None
    assert scoring_tasks
    first_criteria = scoring_tasks[0].evaluation_criteria
    assert first_criteria.response_assertions is not None
    assert [assertion.id for assertion in first_criteria.response_assertions] == [
        assertion.id for assertion in pack.response_assertions
    ]
    assert first_criteria.nl_assertions is not None
    assert {
        _nl_assertion_key(assertion) for assertion in first_criteria.nl_assertions
    } >= {_nl_assertion_key(assertion) for assertion in pack.nl_assertions}


def test_workbench_serves_only_benchmark_runner_ui():
    """The runner does not import or mount experimenter-only authoring tools."""
    from starlette.testclient import TestClient

    from tau2.hyper.web.app import app

    client = TestClient(app)

    workbench_page = client.get("/")
    assert workbench_page.status_code == 200
    assert "Construction workbench" in workbench_page.text
    assert "Reasoning summary" in workbench_page.text
    assert 'id="stopBtn"' in workbench_page.text
    assert "Transformation Studio" not in workbench_page.text
    assert client.get("/studio/").status_code == 404


def test_workbench_does_not_load_removed_legacy_tasks():
    from starlette.testclient import TestClient

    from tau2.hyper.web.app import app

    client = TestClient(app)
    task_id = "retail_construction_001"

    detail = client.get(f"/api/tasks/{task_id}").json()
    assert "not found" in detail["error"]

    assert client.post("/api/runs", json={"task_id": task_id}).status_code == 404


def test_workbench_assembles_retail_plus_hard_bundle(monkeypatch, tmp_path):
    from starlette.testclient import TestClient

    import tau2.hyper.web.app as app_module

    monkeypatch.setattr(app_module, "CONSTRUCTION_STATE_DIR", tmp_path)
    monkeypatch.setattr(app_module, "_construction_sessions", {})

    response = TestClient(app_module.app).post(
        "/api/construction/sessions",
        json={"task_id": RETAIL_PLUS_HARD_TASK_ID},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "kit_ready"
    assert payload["task_id"] == RETAIL_PLUS_HARD_TASK_ID


def test_workbench_returns_structured_kit_assembly_errors(monkeypatch, tmp_path):
    from starlette.testclient import TestClient

    import tau2.hyper.sandbox.kit as kit_module
    import tau2.hyper.web.app as app_module

    monkeypatch.setattr(app_module, "CONSTRUCTION_STATE_DIR", tmp_path)
    monkeypatch.setattr(app_module, "_construction_sessions", {})

    def fail_build(*args, **kwargs):
        del args, kwargs
        raise ValueError("unknown transformation bundle 'missing_bundle'")

    monkeypatch.setattr(kit_module, "build_kit", fail_build)

    response = TestClient(app_module.app).post(
        "/api/construction/sessions",
        json={"task_id": RETAIL_PLUS_HARD_TASK_ID},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            f"Could not assemble kit for {RETAIL_PLUS_HARD_TASK_ID}: "
            "unknown transformation bundle 'missing_bundle'"
        )
    }
    assert list((tmp_path / "sessions").iterdir()) == []


def test_workbench_stop_signals_the_active_job(monkeypatch):
    from threading import Event

    from starlette.testclient import TestClient

    import tau2.hyper.web.app as app_module

    cancel_event = Event()
    queue = Queue()
    session = {
        "id": "retail-plus-session",
        "status": "construction_running",
        "last_job_id": "construction-test",
    }
    job = {
        "id": "construction-test",
        "session_id": session["id"],
        "kind": "construction",
        "status": "running",
        "queue": queue,
        "cancel_event": cancel_event,
    }
    monkeypatch.setattr(app_module, "_construction_sessions", {session["id"]: session})
    monkeypatch.setattr(app_module, "_construction_jobs", {job["id"]: job})

    response = TestClient(app_module.app).post(
        "/api/construction/jobs/construction-test/stop"
    )

    assert response.status_code == 200
    assert response.json() == {
        "job_id": "construction-test",
        "status": "stop_requested",
    }
    assert cancel_event.is_set()
    assert job["status"] == "cancelling"
    assert session["status"] == "construction_cancelling"
    assert queue.get_nowait() == {
        "type": "stop_requested",
        "kind": "construction",
    }


def test_validation_stop_wins_over_sealed_runtime_load_failure(monkeypatch, tmp_path):
    from threading import Event

    import tau2.hyper.sandbox.sealed_runner as sealed_runner_module
    import tau2.hyper.web.app as app_module

    cancel_event = Event()
    queue = Queue()
    session = {
        "id": "retail-plus-session",
        "task_id": "retail-plus-task",
        "kit_path": str(tmp_path),
        "status": "validation_running",
        "last_job_id": "validation-test",
    }
    job = {
        "id": "validation-test",
        "session_id": session["id"],
        "kind": "validation",
        "status": "starting",
        "queue": queue,
        "cancel_event": cancel_event,
    }

    def cancel_during_load(cls, config):
        del cls, config
        cancel_event.set()
        raise RuntimeError("load failed")

    monkeypatch.setattr(app_module, "_construction_sessions", {session["id"]: session})
    monkeypatch.setattr(app_module, "_construction_jobs", {job["id"]: job})
    monkeypatch.setattr(
        app_module,
        "load_active_hyper_tau_task",
        lambda task_id: SimpleNamespace(
            source_domain="retail_plus",
            client_api_mode=None,
            hyper=SimpleNamespace(allowed_agent_models=[], sandbox_config={}),
        ),
    )
    monkeypatch.setattr(app_module, "_load_validation_tasks", lambda task: [])
    monkeypatch.setattr(
        sealed_runner_module.SealedCandidateEnvironment,
        "template",
        classmethod(cancel_during_load),
    )

    app_module._run_validation_step_in_thread(
        job["id"],
        session["id"],
        app_module.ConstructionValidationRequest(),
    )

    assert job["status"] == "cancelled"
    assert session["status"] == "validation_cancelled"
    assert job["result"] == {"cancelled": True}
    assert [queue.get_nowait()["type"] for _ in range(3)] == [
        "job_started",
        "cancelled",
        "done",
    ]


def test_workbench_streams_reasoning_summary_separately():
    queue = Queue()
    display = WebDisplay(queue)

    display.show_sandbox_step(
        step=1,
        max_steps=10,
        thinking="Visible builder message",
        tool_calls=None,
        tool_results=None,
        reasoning_summary="Model-generated reasoning summary",
    )

    event = queue.get_nowait()
    assert event["thinking"] == "Visible builder message"
    assert event["reasoning_summary"] == "Model-generated reasoning summary"
