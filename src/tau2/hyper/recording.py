"""
Recording and persistence for Hyper-τ simulation runs.

Provides:
- ``RecordingDisplay`` — wraps any display adapter and records all events.
- ``save_recording`` / ``load_recording`` / ``list_recordings`` — disk I/O.

Saved recordings live under ``data/simulations/hyper_tau/`` and are JSON
files containing the full event stream plus metadata, allowing faithful
replay in the web visualizer.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from loguru import logger

from tau2.hyper.data_model import HyperTauTask, OuterLoopResult
from tau2.hyper.result_serialization import (
    bounded_tool_result,
    serialize_result_event,
    serialize_result_summary,
)

# Default save directory (relative to project root)
_SIMULATIONS_DIR = Path("data/simulations/hyper_tau")


def _get_sim_dir() -> Path:
    """Get the simulations directory, creating it if needed."""
    # Walk up from this file to find the project root
    # (src/tau2/hyper/recording.py → 4 levels up)
    project_root = Path(__file__).resolve().parents[3]
    sim_dir = project_root / _SIMULATIONS_DIR
    sim_dir.mkdir(parents=True, exist_ok=True)
    return sim_dir


def _atomic_write_json(path: Path, payload: dict) -> None:
    """Durably replace *path* with a complete JSON document."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            json.dump(payload, temp_file, indent=2, default=str)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


# ---------------------------------------------------------------------------
# Recording display wrapper
# ---------------------------------------------------------------------------


class RecordingDisplay:
    """Wraps another display adapter and records all events.

    Events are stored as a list of dicts (same format as WebDisplay
    pushes to the SSE queue).  After the run completes, call
    ``save()`` to persist the recording to disk.

    Usage::

        display = HyperTauDisplay(...)       # or WebDisplay(...)
        recorder = RecordingDisplay(display)  # wrap it
        result = orchestrator.run(display=recorder, task=task)
        recorder.save(task=task)              # persist to disk
    """

    def __init__(
        self,
        inner_display=None,
        *,
        task: Optional[HyperTauTask] = None,
        config: Optional[dict] = None,
        checkpoint_dir: Optional[Path] = None,
    ):
        self.inner = inner_display
        self.events: list[dict] = []
        self.started_at = datetime.now(timezone.utc).isoformat()
        self._lock = threading.RLock()
        self._task = task
        self._config = dict(config or {})
        self._checkpoint_dir = checkpoint_dir
        self._checkpoint_path: Optional[Path] = None
        self._final_path: Optional[Path] = None
        self._eval_progress: dict[str, dict] = {}

    @property
    def checkpoint_path(self) -> Optional[Path]:
        """Path to the durable in-progress scoring snapshot, when created."""
        with self._lock:
            return self._checkpoint_path

    # ------------------------------------------------------------------
    # Recording helpers
    # ------------------------------------------------------------------

    def _record(self, event: dict) -> None:
        with self._lock:
            self.events.append(event)

    def _ensure_run_paths_locked(self) -> None:
        if self._checkpoint_path is not None:
            return

        task_id = self._task.id if self._task else "unknown"
        safe_task_id = str(task_id).replace("/", "_")
        started = datetime.fromisoformat(self.started_at).strftime("%Y%m%d_%H%M%S_%f")
        sim_dir = self._checkpoint_dir or _get_sim_dir()
        sim_dir.mkdir(parents=True, exist_ok=True)
        stem = f"{safe_task_id}_{started}"
        self._checkpoint_path = sim_dir / f"{stem}.in_progress.json"

    def _progress_snapshot_locked(self) -> dict[str, dict]:
        snapshot = {}
        for suite, progress in self._eval_progress.items():
            completed = progress["completed"]
            snapshot[suite] = {
                "total": progress["total"],
                "completed": completed,
                "passed": progress["passed"],
                "pass_rate": progress["passed"] / completed if completed else 0.0,
                "mean_reward": (
                    progress["reward_sum"] / completed if completed else 0.0
                ),
                "results": list(progress["results"]),
            }
        return snapshot

    def _task_metadata_locked(self) -> dict:
        if self._task is None:
            return {}
        return {
            "id": self._task.id,
            "source_domain": self._task.source_domain,
            "task_description": self._task.task_description,
        }

    def _save_checkpoint_locked(self) -> None:
        try:
            self._ensure_run_paths_locked()
            assert self._checkpoint_path is not None
            payload = {
                "status": "in_progress",
                "task_id": self._task.id if self._task else "unknown",
                "started_at": self.started_at,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "config": self._config,
                "task_metadata": self._task_metadata_locked(),
                "progress": self._progress_snapshot_locked(),
                "events": [
                    event
                    for event in self.events
                    if event.get("type") in {"eval_task_start", "eval_task_complete"}
                ],
            }
            _atomic_write_json(self._checkpoint_path, payload)
        except OSError as exc:
            # A persistence failure must not abort an otherwise valid benchmark run.
            logger.error(
                f"Failed to save Hyper-tau progress checkpoint "
                f"{self._checkpoint_path}: {exc}"
            )

    # ------------------------------------------------------------------
    # Display interface (mirrors HyperTauDisplay / WebDisplay)
    # ------------------------------------------------------------------

    def show_task_info(
        self,
        task: Optional[HyperTauTask],
        domain: str,
        max_steps: int,
    ) -> None:
        if task is not None:
            with self._lock:
                self._task = task
        event = {
            "type": "task_info",
            "domain": domain,
            "max_steps": max_steps,
            "task": (
                {
                    "id": task.id,
                    "source_domain": task.source_domain,
                    "task_description": task.task_description,
                }
                if task
                else None
            ),
        }
        self._record(event)
        if self.inner:
            self.inner.show_task_info(task, domain, max_steps)

    def show_client_message(self, content: str) -> None:
        event = {"type": "client_message", "content": content}
        self._record(event)
        if self.inner:
            self.inner.show_client_message(content)

    def show_final_eval_start(self) -> None:
        event = {"type": "final_eval_start"}
        self._record(event)
        if self.inner:
            self.inner.show_final_eval_start()

    def show_eval_task_start(
        self, task_id: str, suite: str, idx: int, total: int
    ) -> None:
        """Record and forward the start of an inner evaluation task."""
        event = {
            "type": "eval_task_start",
            "task_id": task_id,
            "suite": suite,
            "idx": idx,
            "total": total,
        }
        with self._lock:
            if idx == 0 and suite in self._eval_progress:
                self._eval_progress.pop(suite)
            self._eval_progress.setdefault(
                suite,
                {
                    "total": total,
                    "completed": 0,
                    "passed": 0,
                    "reward_sum": 0.0,
                    "results": [],
                },
            )["total"] = total
            self.events.append(event)
            if idx == 0:
                self._save_checkpoint_locked()
        if self.inner and hasattr(self.inner, "show_eval_task_start"):
            self.inner.show_eval_task_start(task_id, suite, idx, total)

    def show_eval_task_complete(
        self, task_id: str, suite: str, reward: float, passed: bool
    ) -> None:
        """Persist one completed inner evaluation before forwarding it."""
        event = {
            "type": "eval_task_complete",
            "task_id": task_id,
            "suite": suite,
            "reward": reward,
            "passed": passed,
        }
        with self._lock:
            progress = self._eval_progress.setdefault(
                suite,
                {
                    "total": 0,
                    "completed": 0,
                    "passed": 0,
                    "reward_sum": 0.0,
                    "results": [],
                },
            )
            progress["completed"] += 1
            progress["passed"] += int(passed)
            progress["reward_sum"] += reward
            progress["results"].append(
                {"task_id": task_id, "reward": reward, "passed": passed}
            )
            self.events.append(event)
            self._save_checkpoint_locked()
        if self.inner and hasattr(self.inner, "show_eval_task_complete"):
            self.inner.show_eval_task_complete(task_id, suite, reward, passed)

    def show_result(self, result: OuterLoopResult) -> None:
        self._record(serialize_result_event(result))
        if self.inner:
            self.inner.show_result(result)

    # ------------------------------------------------------------------
    # Sandbox mode events
    # ------------------------------------------------------------------

    def show_sandbox_phase(self, phase: str, detail: str = "") -> None:
        event = {"type": "sandbox_phase", "phase": phase, "detail": detail}
        self._record(event)
        if self.inner:
            self.inner.show_sandbox_phase(phase, detail)

    def show_sandbox_step(
        self,
        step: int,
        max_steps: int,
        thinking: str | None,
        tool_calls: list[dict] | None,
        tool_results: list[dict] | None,
        reasoning_summary: str | None = None,
    ) -> None:
        event = {
            "type": "sandbox_step",
            "step": step,
            "max_steps": max_steps,
            "thinking": thinking,
            "reasoning_summary": reasoning_summary,
            "tool_calls": tool_calls,
            "tool_results": [
                {
                    "name": tr.get("name", ""),
                    "result": bounded_tool_result(tr.get("result"), 2000),
                }
                for tr in (tool_results or [])
            ],
        }
        self._record(event)
        if self.inner:
            self.inner.show_sandbox_step(
                step,
                max_steps,
                thinking,
                tool_calls,
                tool_results,
                reasoning_summary=reasoning_summary,
            )

    def show_sandbox_done(self, reason: str, steps: int, tool_calls: int) -> None:
        event = {
            "type": "sandbox_done",
            "reason": reason,
            "steps": steps,
            "tool_calls": tool_calls,
        }
        self._record(event)
        if self.inner:
            self.inner.show_sandbox_done(reason, steps, tool_calls)

    # ------------------------------------------------------------------
    # Policy diff
    # ------------------------------------------------------------------

    def save(
        self,
        task: Optional[HyperTauTask] = None,
        result: Optional[OuterLoopResult] = None,
        config: Optional[dict] = None,
    ) -> Path:
        """Save the recorded simulation to disk.

        Args:
            task: The HyperTauTask that was run (for metadata).
            result: The OuterLoopResult (for summary data).
            config: Optional run configuration dict (LLMs, etc.).

        Returns:
            Path to the saved JSON file.
        """
        with self._lock:
            if task is not None:
                self._task = task
            if config is not None:
                self._config = dict(config)
            self._ensure_run_paths_locked()
            if self._final_path is None:
                assert self._checkpoint_path is not None
                # Reuse the in-progress stem (task id + microsecond start
                # timestamp): a second-resolution save timestamp lets two
                # concurrent runs of the same task finish in the same second
                # and silently overwrite each other's recording.
                stem = self._checkpoint_path.name.removesuffix(".in_progress.json")
                candidate = self._checkpoint_path.parent / f"{stem}.json"
                attempt = 0
                while candidate.exists():
                    attempt += 1
                    candidate = self._checkpoint_path.parent / f"{stem}_{attempt}.json"
                self._final_path = candidate

            recording = {
                "status": "complete",
                "task_id": self._task.id if self._task else "unknown",
                "started_at": self.started_at,
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "config": self._config,
                "events": list(self.events),
                "progress": self._progress_snapshot_locked(),
            }

            if self._task:
                recording["task_metadata"] = self._task_metadata_locked()

            if result:
                recording["result"] = serialize_result_summary(result)

            filepath = self._final_path
            _atomic_write_json(filepath, recording)
            if self._checkpoint_path and self._checkpoint_path.exists():
                self._checkpoint_path.unlink()

        logger.info(f"Saved Hyper-τ recording to {filepath}")
        return filepath


# ---------------------------------------------------------------------------
# Loading / listing
# ---------------------------------------------------------------------------


def list_recordings() -> list[dict]:
    """List all saved Hyper-τ recordings.

    Returns:
        List of summary dicts sorted by timestamp (newest first),
        each containing: filename, task_id, started_at, result summary.
    """
    sim_dir = _get_sim_dir()
    recordings = []

    for path in sim_dir.glob("*.json"):
        try:
            with open(path) as f:
                data = json.load(f)
            summary = {
                "filename": path.name,
                "status": data.get("status", "complete"),
                "task_id": data.get("task_id", "unknown"),
                "started_at": data.get("started_at", ""),
                "updated_at": data.get("updated_at", ""),
                "saved_at": data.get("saved_at", ""),
                "config": data.get("config", {}),
                "task_metadata": data.get("task_metadata", {}),
                "result": data.get("result", {}),
                "progress": data.get("progress", {}),
                "num_events": len(data.get("events", [])),
            }
            recordings.append(summary)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Skipping invalid recording {path.name}: {e}")

    recordings.sort(
        key=lambda r: r.get("saved_at")
        or r.get("updated_at")
        or r.get("started_at", ""),
        reverse=True,
    )
    return recordings


def load_recording(filename: str) -> dict:
    """Load a saved Hyper-τ recording by filename.

    Args:
        filename: The JSON filename (e.g. "retail_scope_confusion_20260311_190700.json").

    Returns:
        The full recording dict with events, metadata, and result.

    Raises:
        FileNotFoundError: If the recording file doesn't exist.
    """
    sim_dir = _get_sim_dir()
    filepath = sim_dir / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Recording not found: {filename}")

    with open(filepath) as f:
        data = json.load(f)

    return data
