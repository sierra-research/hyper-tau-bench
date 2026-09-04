"""
FastAPI web application for the Hyper-τ construction workbench.

The browser UI focuses on construction tasks:
- assemble a starter construction kit,
- run the builder construction step,
- run validation/scoring against the same kit as a separate step,

Usage:
    tau2 hyper-tau-app                     # start on default port
    tau2 hyper-tau-app --port 8765         # custom port
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import threading
import time
import uuid
from pathlib import Path
from queue import Empty, Queue
from threading import Event
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse
from loguru import logger
from pydantic import BaseModel

from tau2.hyper.runtime_contract import DEFAULT_CONSTRUCTION_RUNTIME_IMAGE
from tau2.hyper.task_loader import (
    LegacyHyperTauDomainError,
    load_active_hyper_tau_task,
    load_active_hyper_tau_tasks,
)
from tau2.hyper.web.web_display import WebDisplay

app = FastAPI(title="Hyper-τ Construction Workbench")

_construction_sessions: dict[str, dict[str, Any]] = {}
_construction_jobs: dict[str, dict[str, Any]] = {}

_DEFAULT_CONSTRUCTION_STATE_DIR = "/private/tmp/hyper_tau_construction_workbench"
CONSTRUCTION_STATE_DIR = Path(
    os.getenv("HYPER_TAU_CONSTRUCTION_STATE_DIR", _DEFAULT_CONSTRUCTION_STATE_DIR)
)

# ---------------------------------------------------------------------------
# Data models for API
# ---------------------------------------------------------------------------


class ConstructionKitRequest(BaseModel):
    task_id: str
    agent_llm: str = "gpt-5.5"
    user_llm: str = "gpt-5.5"


class ConstructionRunRequest(BaseModel):
    developer_llm: str = "gpt-5.5"
    developer_reasoning_effort: str | None = "high"
    developer_thinking_budget: int | None = None
    agent_llm: str = "gpt-5.5"
    user_llm: str = "gpt-5.5"
    agent_reasoning_effort: str | None = "none"
    user_reasoning_effort: str | None = "none"
    sandbox_steps: int = 0


class ConstructionValidationRequest(BaseModel):
    agent_llm: str = "gpt-5.5"
    user_llm: str = "gpt-5.5"
    agent_reasoning_effort: str | None = "none"
    user_reasoning_effort: str | None = "none"
    max_tasks: int | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main HTML page."""
    html_path = Path(__file__).parent / "index.html"
    return HTMLResponse(content=html_path.read_text())


@app.get("/api/tasks")
async def list_tasks():
    """List all available Hyper-τ tasks."""
    tasks = load_active_hyper_tau_tasks()
    return [
        {
            "id": t.id,
            "source_domain": t.source_domain,
            "task_description": t.task_description,
            "num_training_tasks": len(t.training_task_ids),
            "num_test_tasks": len(t.test_task_ids),
            "agent_llm": t.agent_llm,
            "agent_reasoning_effort": t.agent_reasoning_effort,
            "user_llm": t.user_llm,
            "user_reasoning_effort": t.user_reasoning_effort,
            "client_llm": t.client_llm,
            "client_reasoning_effort": t.client_reasoning_effort,
            "client_enabled": t.client_enabled,
        }
        for t in tasks
    ]


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """Get details of a specific task."""
    try:
        task = load_active_hyper_tau_task(task_id)
    except (FileNotFoundError, LegacyHyperTauDomainError) as error:
        return {"error": str(error)}
    return {
        "id": task.id,
        "source_domain": task.source_domain,
        "task_description": task.task_description,
        "client_instructions": task.client_instructions,
        "training_task_ids": task.training_task_ids,
        "test_task_ids": task.test_task_ids,
    }


@app.get("/api/tasks/{task_id}/full")
async def get_task_full(task_id: str):
    """Get full details of a specific construction task."""
    try:
        task = load_active_hyper_tau_task(task_id)
    except (FileNotFoundError, LegacyHyperTauDomainError) as error:
        return {"error": str(error)}
    return {
        "id": task.id,
        "source_domain": task.source_domain,
        "task_description": task.task_description,
        "client_instructions": task.client_instructions,
        "training_task_ids": task.training_task_ids,
        "test_task_ids": task.test_task_ids,
        "agent_llm": task.agent_llm,
        "agent_reasoning_effort": task.agent_reasoning_effort,
        "user_llm": task.user_llm,
        "user_reasoning_effort": task.user_reasoning_effort,
        "client_llm": task.client_llm,
        "client_reasoning_effort": task.client_reasoning_effort,
    }


# ---------------------------------------------------------------------------
# Construction workbench
# ---------------------------------------------------------------------------


@app.get("/api/construction/sessions")
async def list_construction_sessions():
    """Return construction sessions created by this app process."""
    return [
        _construction_session_payload(session)
        for session in sorted(
            _construction_sessions.values(),
            key=lambda item: item["created_at"],
            reverse=True,
        )
    ]


@app.post("/api/construction/sessions")
async def create_construction_session(request: ConstructionKitRequest):
    """Assemble a construction kit and create a persistent workbench session."""
    try:
        task = load_active_hyper_tau_task(request.task_id)
    except (FileNotFoundError, LegacyHyperTauDomainError) as error:
        return {"error": str(error)}

    from tau2.hyper.sandbox.kit import build_kit

    CONSTRUCTION_STATE_DIR.mkdir(parents=True, exist_ok=True)
    session_id = f"{task.source_domain}-{uuid.uuid4().hex[:8]}"
    session_dir = CONSTRUCTION_STATE_DIR / "sessions" / session_id
    kit_path = session_dir / "kit"
    session_dir.mkdir(parents=True, exist_ok=True)

    try:
        build_kit(
            task,
            kit_path,
        )
    except (FileNotFoundError, ValueError) as error:
        shutil.rmtree(session_dir, ignore_errors=True)
        logger.warning(f"Could not assemble kit for {task.id}: {error}")
        raise HTTPException(
            status_code=422,
            detail=f"Could not assemble kit for {task.id}: {error}",
        ) from error
    except Exception as error:
        shutil.rmtree(session_dir, ignore_errors=True)
        logger.exception(f"Could not assemble kit for {task.id}")
        raise HTTPException(
            status_code=500,
            detail=f"Could not assemble kit for {task.id}: {error}",
        ) from error

    session = {
        "id": session_id,
        "task_id": task.id,
        "domain": task.source_domain,
        "task_description": task.task_description,
        "kit_path": str(kit_path),
        "created_at": time.time(),
        "status": "kit_ready",
        "kit_agent_llm": request.agent_llm,
        "kit_user_llm": request.user_llm,
        "construction_result": None,
        "validation_result": None,
        "last_job_id": None,
    }
    _construction_sessions[session_id] = session
    return _construction_session_payload(session)


@app.get("/api/construction/sessions/{session_id}")
async def get_construction_session(session_id: str):
    """Return metadata for a construction session."""
    return _construction_session_payload(_require_construction_session(session_id))


@app.get("/api/construction/sessions/{session_id}/files")
async def list_construction_files(session_id: str):
    """List files in a construction kit."""
    session = _require_construction_session(session_id)
    kit_path = Path(session["kit_path"])
    return {"session_id": session_id, "files": _list_kit_files(kit_path)}


@app.get(
    "/api/construction/sessions/{session_id}/file",
    response_class=PlainTextResponse,
)
async def get_construction_file(session_id: str, path: str):
    """Read a text file from a construction kit."""
    session = _require_construction_session(session_id)
    kit_path = Path(session["kit_path"])
    file_path = _safe_kit_file(kit_path, path)
    try:
        text = file_path.read_text(errors="replace")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if len(text) > 400_000:
        return text[:400_000] + "\n\n[truncated after 400000 characters]"
    return text


@app.post("/api/construction/sessions/{session_id}/construct")
async def start_construction_step(
    session_id: str,
    request: ConstructionRunRequest,
):
    """Run the builder construction step against an assembled kit."""
    session = _require_construction_session(session_id)
    if session["status"].endswith(("_running", "_cancelling")):
        raise HTTPException(status_code=409, detail="A workbench job is already active")
    job = _create_construction_job(session_id, "construction")
    session["status"] = "construction_running"
    session["last_job_id"] = job["id"]

    thread = threading.Thread(
        target=_run_construction_step_in_thread,
        args=(job["id"], session_id, request),
        daemon=True,
    )
    thread.start()
    return {"job_id": job["id"], "session_id": session_id}


@app.post("/api/construction/sessions/{session_id}/validate")
async def start_validation_step(
    session_id: str,
    request: ConstructionValidationRequest,
):
    """Run validation/scoring against the current construction kit."""
    session = _require_construction_session(session_id)
    if session["status"].endswith(("_running", "_cancelling")):
        raise HTTPException(status_code=409, detail="A workbench job is already active")
    job = _create_construction_job(session_id, "validation")
    session["status"] = "validation_running"
    session["last_job_id"] = job["id"]

    thread = threading.Thread(
        target=_run_validation_step_in_thread,
        args=(job["id"], session_id, request),
        daemon=True,
    )
    thread.start()
    return {"job_id": job["id"], "session_id": session_id}


@app.get("/api/construction/jobs/{job_id}/events")
async def stream_construction_job_events(job_id: str):
    """Stream construction workbench job events via SSE."""
    if job_id not in _construction_jobs:
        return {"error": "Job not found"}

    queue = _construction_jobs[job_id]["queue"]

    async def event_generator():
        while True:
            try:
                event = queue.get_nowait()
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") == "done":
                    break
            except Empty:
                yield ": keepalive\n\n"
                await asyncio.sleep(0.3)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/construction/jobs/{job_id}/stop")
async def stop_construction_job(job_id: str):
    """Cooperatively stop an active construction or validation job."""
    job = _construction_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Construction job not found")
    if job["status"] in {"complete", "error", "cancelled"}:
        return {"job_id": job_id, "status": job["status"]}
    if job["status"] == "cancelling":
        return {"job_id": job_id, "status": "stop_requested"}

    job["status"] = "cancelling"
    job["cancel_event"].set()
    session = _construction_sessions.get(job["session_id"])
    if session is not None:
        session["status"] = f"{job['kind']}_cancelling"
    job["queue"].put({"type": "stop_requested", "kind": job["kind"]})
    logger.info(f"Stop requested for construction job {job_id}")
    return {"job_id": job_id, "status": "stop_requested"}


@app.get("/api/live-runs")
async def list_live_runs():
    """Discover builder runs on this machine via the shared run registry.

    Includes runs launched outside this server process (detached scripts,
    other workbench instances) — anything whose builder streamed a
    trajectory through TrajectoryStreamer.
    """
    from tau2.hyper.web.run_stream import load_run_manifests

    return load_run_manifests()


def _read_trajectory_chunk(
    trajectory_path: Path,
    position: int,
    file_identity: tuple[int, int] | None,
) -> tuple[str, int, tuple[int, int] | None, bool]:
    """Read appended data, resetting after trajectory replacement or truncation."""
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    if not no_follow and trajectory_path.is_symlink():
        return "", position, file_identity, False
    try:
        descriptor = os.open(trajectory_path, os.O_RDONLY | no_follow)
    except OSError:
        return "", position, file_identity, False
    with os.fdopen(descriptor) as handle:
        stat = os.fstat(handle.fileno())
        current_identity = (stat.st_dev, stat.st_ino)
        reset = file_identity is not None and (
            current_identity != file_identity or stat.st_size < position
        )
        if reset:
            position = 0
        handle.seek(position)
        chunk = handle.read()
        return chunk, handle.tell(), current_identity, reset


@app.get("/api/live-runs/{run_id}/events")
async def stream_live_run_events(run_id: str):
    """Tail a run's trajectory jsonl as SSE: replay history, then follow.

    Works for in-flight and finished runs alike; the stream ends once the
    manifest reports a terminal status and the file is drained.
    """
    from tau2.hyper.web.run_stream import (
        load_run_manifest,
        trajectory_path_for_run,
    )

    manifest = load_run_manifest(run_id)
    if manifest is None:
        return {"error": "Run not found"}
    trajectory_path = trajectory_path_for_run(run_id)
    if trajectory_path is None:
        return {"error": "Run trajectory not found"}

    async def event_generator():
        yield f"data: {json.dumps({'type': 'run_manifest', 'final': False, **manifest})}\n\n"
        position = 0
        file_identity = None
        pending = ""

        def complete_lines(chunk: str) -> list[str]:
            nonlocal pending
            pending += chunk
            lines = pending.split("\n")
            pending = lines.pop()
            return [line for line in lines if line.strip()]

        while True:
            chunk, position, file_identity, reset = _read_trajectory_chunk(
                trajectory_path, position, file_identity
            )
            if reset:
                pending = ""
            if chunk:
                for line in complete_lines(chunk):
                    yield f"data: {line}\n\n"
                continue
            current = load_run_manifest(run_id)
            if current is None:
                current = {
                    **manifest,
                    "status": "unavailable",
                    "alive": False,
                    "done_reason": "manifest_unavailable",
                }
            if current.get("status") != "running":
                # finish() appends sandbox_done before marking the manifest
                # terminal. Drain once more after observing that state so a
                # write between the prior EOF read and manifest load is kept.
                chunk, position, file_identity, reset = _read_trajectory_chunk(
                    trajectory_path, position, file_identity
                )
                if reset:
                    pending = ""
                for line in complete_lines(chunk):
                    yield f"data: {line}\n\n"
                yield f"data: {json.dumps({'type': 'run_manifest', 'final': True, **current})}\n\n"
                break
            yield ": keepalive\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Construction workbench helpers
# ---------------------------------------------------------------------------


def _construction_session_payload(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": session["id"],
        "task_id": session["task_id"],
        "domain": session["domain"],
        "task_description": session["task_description"],
        "kit_path": session["kit_path"],
        "created_at": session["created_at"],
        "status": session["status"],
        "kit_agent_llm": session["kit_agent_llm"],
        "kit_user_llm": session["kit_user_llm"],
        "construction_result": session.get("construction_result"),
        "validation_result": session.get("validation_result"),
        "last_job_id": session.get("last_job_id"),
    }


def _require_construction_session(session_id: str) -> dict[str, Any]:
    session = _construction_sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Construction session not found")
    return session


def _create_construction_job(session_id: str, kind: str) -> dict[str, Any]:
    job_id = f"{kind}-{uuid.uuid4().hex[:8]}"
    job = {
        "id": job_id,
        "session_id": session_id,
        "kind": kind,
        "status": "starting",
        "queue": Queue(),
        "cancel_event": Event(),
        "created_at": time.time(),
        "result": None,
    }
    _construction_jobs[job_id] = job
    return job


def _finish_cancelled_construction_job(
    job: dict[str, Any], session: dict[str, Any], queue: Queue
) -> None:
    """Record a cooperative workbench cancellation and close its event stream."""
    result = {"cancelled": True}
    job["status"] = "cancelled"
    job["result"] = result
    session["status"] = f"{job['kind']}_cancelled"
    queue.put({"type": "cancelled", "kind": job["kind"]})
    queue.put({"type": "done"})


def _list_kit_files(kit_path: Path) -> list[dict[str, Any]]:
    if not kit_path.exists():
        return []

    files: list[dict[str, Any]] = []
    for path in sorted(p for p in kit_path.rglob("*") if p.is_file()):
        rel_parts = path.relative_to(kit_path).parts
        if "__pycache__" in rel_parts:
            continue
        rel = "/".join(rel_parts)
        try:
            stat = path.stat()
        except OSError:
            continue
        files.append(
            {
                "path": rel,
                "size_bytes": stat.st_size,
                "modified_at": stat.st_mtime,
            }
        )
    return files


def _safe_kit_file(kit_path: Path, relative_path: str) -> Path:
    root = kit_path.resolve()
    target = (kit_path / relative_path).resolve()
    if target != root and root not in target.parents:
        raise HTTPException(status_code=400, detail="Path escapes kit directory")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Kit file not found")
    return target


def _run_construction_step_in_thread(
    job_id: str,
    session_id: str,
    request: ConstructionRunRequest,
):
    job = _construction_jobs[job_id]
    queue: Queue = job["queue"]
    session = _construction_sessions[session_id]
    kit_path = Path(session["kit_path"])
    cancel_event: Event = job["cancel_event"]

    try:
        if cancel_event.is_set():
            _finish_cancelled_construction_job(job, session, queue)
            return
        job["status"] = "running"
        queue.put(
            {
                "type": "job_started",
                "kind": "construction",
                "session_id": session_id,
                "kit_path": str(kit_path),
            }
        )

        from tau2.hyper.harnesses.factory import (
            DEFAULT_DEVELOPER_HARNESS,
            create_developer_builder,
        )
        from tau2.hyper.sandbox.builder import BuildBudget
        from tau2.hyper.sandbox.orchestrator import (
            SandboxOrchestrator,
            _build_artifact_manifest,
        )

        task = load_active_hyper_tau_task(session["task_id"])
        developer_llm_args = _build_llm_args(
            request.developer_llm,
            request.developer_reasoning_effort,
            request.developer_thinking_budget,
        )
        agent_llm_args = _build_llm_args(
            request.agent_llm,
            request.agent_reasoning_effort,
            None,
        )
        user_llm_args = _build_llm_args(
            request.user_llm,
            request.user_reasoning_effort,
            None,
        )

        # The workbench pins the same default harness as the CLI.
        builder = create_developer_builder(
            DEFAULT_DEVELOPER_HARNESS,
            request.developer_llm,
            developer_llm_args,
            request.developer_reasoning_effort,
        )

        budget = BuildBudget(max_steps=request.sandbox_steps)
        orchestrator = SandboxOrchestrator.from_task(
            task=task,
            builder=builder,
            agent_llm=request.agent_llm,
            user_llm=request.user_llm,
            agent_llm_args=agent_llm_args,
            user_llm_args=user_llm_args,
            budget=budget,
            kit_dir=kit_path,
            keep_kit=True,
        )
        orchestrator._apply_sandbox_config_to_builder()

        display = WebDisplay(queue)
        brief = orchestrator._build_brief("")
        queue.put(
            {
                "type": "sandbox_phase",
                "phase": "construction",
                "detail": "Builder is working inside the assembled kit.",
            }
        )

        build_result = builder.build(
            kit_path,
            brief,
            budget,
            display=display,
            cancel_event=cancel_event,
        )
        if cancel_event.is_set() or build_result.done_reason == "cancelled":
            _finish_cancelled_construction_job(job, session, queue)
            return
        result = {
            "submitted": build_result.submitted,
            "done_reason": build_result.done_reason,
            "elapsed_seconds": build_result.elapsed_seconds,
            "total_steps": build_result.total_steps,
            "total_tool_calls": build_result.total_tool_calls,
            "artifact_count": len(_build_artifact_manifest(kit_path)),
        }
        session["status"] = "constructed"
        session["construction_result"] = result
        session["validation_result"] = None
        job["status"] = "complete"
        job["result"] = result
        queue.put({"type": "construction_result", "result": result})
        queue.put({"type": "done"})

    except Exception as exc:
        if cancel_event.is_set():
            logger.info(f"Construction job {job_id} cancelled")
            _finish_cancelled_construction_job(job, session, queue)
            return
        logger.exception(f"Construction job {job_id} failed")
        session["status"] = "construction_error"
        job["status"] = "error"
        job["result"] = {"error": str(exc)}
        queue.put({"type": "error", "message": str(exc)})
        queue.put({"type": "done"})


def _run_validation_step_in_thread(
    job_id: str,
    session_id: str,
    request: ConstructionValidationRequest,
):
    job = _construction_jobs[job_id]
    queue: Queue = job["queue"]
    session = _construction_sessions[session_id]
    kit_path = Path(session["kit_path"])
    cancel_event: Event = job["cancel_event"]

    try:
        if cancel_event.is_set():
            _finish_cancelled_construction_job(job, session, queue)
            return
        job["status"] = "running"
        queue.put(
            {
                "type": "job_started",
                "kind": "validation",
                "session_id": session_id,
                "kit_path": str(kit_path),
            }
        )

        from tau2.hyper._inner import run_inner_simulations
        from tau2.hyper.sandbox.orchestrator import (
            _build_artifact_manifest,
            _build_contamination_report,
        )
        from tau2.hyper.sandbox.sealed_runner import (
            SealedCandidateEnvironment,
            SealedRunnerConfig,
            create_sealed_candidate_agent,
        )

        task = load_active_hyper_tau_task(session["task_id"])
        domain = task.source_domain
        tasks = _load_validation_tasks(task)
        if request.max_tasks and request.max_tasks > 0:
            tasks = tasks[: request.max_tasks]

        agent_llm_args = _build_llm_args(
            request.agent_llm,
            request.agent_reasoning_effort,
            None,
        )
        user_llm_args = _build_llm_args(
            request.user_llm,
            request.user_reasoning_effort,
            None,
        )
        requested_constraints = dict(agent_llm_args or {})
        matching_model_configs = [
            config
            for config in (task.hyper.allowed_agent_models or [])
            if config.get("model") == request.agent_llm
            and dict(config.get("constraints") or {}) == requested_constraints
        ]
        allowed_agent_models = matching_model_configs or [
            {
                "model": request.agent_llm,
                "constraints": requested_constraints,
            }
        ]
        sandbox_config = dict(task.hyper.sandbox_config or {})
        sealed_config = SealedRunnerConfig(
            kit_path=kit_path,
            image=(
                os.getenv("TAU2_SANDBOX_DOCKER_IMAGE")
                or sandbox_config.get("docker_image")
                or DEFAULT_CONSTRUCTION_RUNTIME_IMAGE
            ),
            memory=sandbox_config.get("docker_memory"),
            cpus=sandbox_config.get("docker_cpus"),
            domain=domain,
            client_api_mode=task.client_api_mode,
        )
        dev_env = None
        load_error = None
        try:
            dev_env = SealedCandidateEnvironment.template(sealed_config)
        except Exception as error:
            load_error = f"Could not load sealed candidate runtime: {error}"
        if cancel_event.is_set():
            _finish_cancelled_construction_job(job, session, queue)
            return
        if dev_env is None:
            result = {
                "total": len(tasks),
                "passed": 0,
                "failed": len(tasks),
                "avg_reward": 0.0,
                "load_error": load_error,
            }
            session["status"] = "validation_error"
            session["validation_result"] = result
            job["status"] = "error"
            job["result"] = result
            queue.put({"type": "validation_result", "result": result})
            queue.put({"type": "error", "message": load_error})
            queue.put({"type": "done"})
            return

        display = WebDisplay(queue)
        display.show_final_eval_start()
        final_results = run_inner_simulations(
            tasks,
            domain=domain,
            policy="",
            agent_llm=request.agent_llm,
            user_llm=request.user_llm,
            agent_llm_args=agent_llm_args,
            allowed_agent_models=allowed_agent_models,
            user_llm_args=user_llm_args,
            agent_factory=create_sealed_candidate_agent,
            custom_environment=dev_env,
            use_reference_gold_environment=True,
            display=display,
            eval_kind="test",
            stop_event=cancel_event,
        )
        if cancel_event.is_set():
            _finish_cancelled_construction_job(job, session, queue)
            return

        total = len(final_results)
        passed = sum(1 for result in final_results if result.reward == 1)
        avg_reward = (
            sum(result.reward for result in final_results) / total if total else 0.0
        )
        result = {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "avg_reward": avg_reward,
            "artifact_manifest": _build_artifact_manifest(kit_path),
            "contamination_report": _build_contamination_report(kit_path, domain),
            "details": [
                {
                    "task_id": item.task_id,
                    "reward": item.reward,
                    "passed": item.reward == 1,
                    "reward_breakdown": item.reward_breakdown,
                    "nl_assertion_details": item.nl_assertion_details,
                    "response_assertion_details": item.response_assertion_details,
                }
                for item in final_results
            ],
        }
        session["status"] = "validated"
        session["validation_result"] = result
        job["status"] = "complete"
        job["result"] = result
        queue.put({"type": "validation_result", "result": result})
        queue.put({"type": "done"})

    except Exception as exc:
        if cancel_event.is_set():
            logger.info(f"Validation job {job_id} cancelled")
            _finish_cancelled_construction_job(job, session, queue)
            return
        logger.exception(f"Validation job {job_id} failed")
        session["status"] = "validation_error"
        job["status"] = "error"
        job["result"] = {"error": str(exc)}
        queue.put({"type": "error", "message": str(exc)})
        queue.put({"type": "done"})


def _load_validation_tasks(task):
    from tau2.hyper.response_phrasing import (
        apply_response_phrasing_rule_pack_to_tasks,
        load_selected_response_phrasing_rule_pack_for_task,
    )
    from tau2.run import get_tasks as get_inner_loop_tasks
    from tau2.runner.build import load_tasks_from_file

    pack = load_selected_response_phrasing_rule_pack_for_task(task)
    if task.test_tasks_path:
        tasks = load_tasks_from_file(task.test_tasks_path, task.test_task_ids)
        return apply_response_phrasing_rule_pack_to_tasks(tasks, pack)

    all_tasks = get_inner_loop_tasks(task.source_domain)
    by_id = {inner_task.id: inner_task for inner_task in all_tasks}
    missing = [task_id for task_id in task.test_task_ids if task_id not in by_id]
    if missing:
        logger.warning(
            f"Test task IDs not found in domain {task.source_domain}: {missing}"
        )
    tasks = [by_id[task_id] for task_id in task.test_task_ids if task_id in by_id]
    return apply_response_phrasing_rule_pack_to_tasks(tasks, pack)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_llm_args(
    model: str,
    reasoning_effort: str | None,
    thinking_budget: int | None,
) -> dict | None:
    """Build LLM args dict from reasoning parameters.

    - OpenAI reasoning models (gpt-5.*): use ``reasoning_effort``.
    - Anthropic models (claude-*): use ``thinking`` with ``budget_tokens``.

    Returns None if no reasoning parameters are set.
    """
    args: dict = {}

    if reasoning_effort and model.startswith("gpt-5"):
        args["reasoning_effort"] = reasoning_effort

    if thinking_budget and "claude" in model:
        args["thinking"] = {
            "type": "enabled",
            "budget_tokens": thinking_budget,
        }

    return args if args else None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def start_app(host: str = "0.0.0.0", port: int = 8888):
    """Start the Hyper-τ visualizer web app."""
    import uvicorn

    logger.info(f"Starting Hyper-τ visualizer at http://localhost:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")
