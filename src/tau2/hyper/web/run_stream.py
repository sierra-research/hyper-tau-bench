"""Write-through trajectory streaming for sandbox builder runs.

The builder holds its trajectory in memory until the run ends, which makes
detached runs (nohup scripts, orphaned server threads) invisible while they
work. ``TrajectoryStreamer`` writes every step to disk as it happens and
registers the run in a shared registry directory, so any process — notably
the construction workbench — can discover live runs and tail their action
stream.

Files written:

- ``<registry>/<run_id>.trajectory.jsonl`` — one JSON event per line, in the
  same shape as the WebDisplay ``sandbox_step`` events so UIs can reuse their
  existing renderers.
- ``<registry>/<run_id>.json`` — the run manifest (pid, kit path, status,
  step counters), rewritten atomically on every update. The registry directory
  is ``TAU2_RUN_REGISTRY_DIR`` when set, otherwise
  ``<tempdir>/hyper_tau_run_registry``.

Streaming is strictly best-effort: a failure to write the stream must never
kill or slow the run it observes.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional

from loguru import logger

from tau2.hyper.result_serialization import bounded_tool_result

# Tool results in the stream are capped like WebDisplay caps them for SSE;
# the full text still reaches the end-of-run trajectory dump.
_STREAM_RESULT_CHARS = 3000


def run_registry_dir() -> Path:
    """Directory where live-run manifests are registered."""
    override = os.environ.get("TAU2_RUN_REGISTRY_DIR")
    if override:
        return Path(override)
    return Path(tempfile.gettempdir()) / "hyper_tau_run_registry"


def trajectory_path_for_run(run_id: str) -> Optional[Path]:
    """Return the trusted registry-owned trajectory path for a run id."""
    if not _valid_run_id(run_id):
        return None
    registry = run_registry_dir().resolve()
    path = registry / f"{run_id}.trajectory.jsonl"
    try:
        resolved = path.resolve()
    except OSError:
        return None
    if resolved != path:
        # Do not follow a registry symlink to another file.
        return None
    return resolved


class TrajectoryStreamer:
    """Streams builder steps to disk and maintains a run manifest."""

    def __init__(self, run_id: str, jsonl_path: Path, manifest: dict):
        self.run_id = run_id
        self.jsonl_path = jsonl_path
        self.manifest = manifest
        self._registry_path = run_registry_dir() / f"{run_id}.json"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def start(
        cls, kit_path: Path, llm: str, max_steps: int
    ) -> Optional["TrajectoryStreamer"]:
        """Open the stream and register the run. Returns None on failure."""
        try:
            kit_path = Path(kit_path)
            started_at = time.time()
            run_id = f"{int(started_at)}-{os.getpid()}-{uuid.uuid4().hex[:8]}"
            run_registry_dir().mkdir(parents=True, exist_ok=True)
            jsonl_path = trajectory_path_for_run(run_id)
            if jsonl_path is None:
                raise RuntimeError("Could not create a safe trajectory path")
            manifest = {
                "run_id": run_id,
                "pid": os.getpid(),
                "kit_path": str(kit_path),
                "trajectory_path": str(jsonl_path),
                "llm": llm,
                "max_steps": max_steps,
                "steps": 0,
                "tool_calls": 0,
                "status": "running",
                "done_reason": None,
                "started_at": started_at,
                "updated_at": started_at,
            }
            jsonl_path.write_text("")
            streamer = cls(run_id, jsonl_path, manifest)
            streamer._write_manifest()
            return streamer
        except Exception as exc:  # noqa: BLE001 — observability must not kill runs
            logger.debug(f"Trajectory streaming unavailable: {exc}")
            return None

    def step(self, build_step, max_steps: int) -> None:
        """Append one builder step to the stream."""
        try:
            tool_results = [
                {
                    "name": tr.get("name", ""),
                    "result": bounded_tool_result(
                        tr.get("result"), _STREAM_RESULT_CHARS
                    ),
                }
                for tr in (build_step.tool_results or [])
            ]
            self._append(
                {
                    "type": "sandbox_step",
                    "step": build_step.step_idx,
                    "max_steps": max_steps,
                    "thinking": build_step.content,
                    "reasoning_summary": build_step.reasoning_summary,
                    "tool_calls": build_step.tool_calls,
                    "tool_results": tool_results,
                    "elapsed_seconds": build_step.timestamp,
                }
            )
            self.manifest["steps"] = build_step.step_idx
            self.manifest["tool_calls"] += len(build_step.tool_calls or [])
            self.manifest["updated_at"] = time.time()
            self._write_manifest()
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"Trajectory stream step write failed: {exc}")

    def finish(
        self,
        done_reason: str,
        status: str = "finished",
        *,
        total_steps: int | None = None,
        total_tool_calls: int | None = None,
    ) -> None:
        """Mark the run terminal and append the closing event."""
        try:
            if total_steps is not None:
                self.manifest["steps"] = total_steps
            if total_tool_calls is not None:
                self.manifest["tool_calls"] = total_tool_calls
            self._append(
                {
                    "type": "sandbox_done",
                    "reason": done_reason,
                    "steps": self.manifest["steps"],
                    "tool_calls": self.manifest["tool_calls"],
                }
            )
            self.manifest["status"] = status
            self.manifest["done_reason"] = done_reason
            self.manifest["updated_at"] = time.time()
            self._write_manifest()
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"Trajectory stream finish write failed: {exc}")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _append(self, event: dict) -> None:
        with self.jsonl_path.open("a") as handle:
            handle.write(json.dumps(event, default=str) + "\n")

    def _write_manifest(self) -> None:
        """Atomic rewrite so pollers never see a torn manifest."""
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._registry_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(self.manifest, indent=2, default=str))
        tmp_path.replace(self._registry_path)


def load_run_manifests() -> list[dict]:
    """Load all registered run manifests, newest first, liveness-annotated."""
    registry = run_registry_dir()
    if not registry.is_dir():
        return []
    manifests = []
    for path in registry.glob("*.json"):
        try:
            manifest = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if (
            not isinstance(manifest, dict)
            or manifest.get("run_id") != path.stem
            or not _valid_run_id(manifest["run_id"])
        ):
            continue
        manifest["alive"] = _pid_alive(manifest.get("pid"))
        if manifest.get("status") == "running" and not manifest["alive"]:
            # The producing process died without closing the stream.
            manifest["status"] = "abandoned"
        manifests.append(manifest)
    manifests.sort(key=lambda m: m.get("started_at") or 0, reverse=True)
    return manifests


def load_run_manifest(run_id: str) -> Optional[dict]:
    """Load a single manifest by run id (registry filenames are run ids)."""
    if not _valid_run_id(run_id):
        return None
    path = run_registry_dir() / f"{run_id}.json"
    if not path.is_file():
        return None
    try:
        manifest = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(manifest, dict) or manifest.get("run_id") != run_id:
        return None
    manifest["alive"] = _pid_alive(manifest.get("pid"))
    if manifest.get("status") == "running" and not manifest["alive"]:
        manifest["status"] = "abandoned"
    return manifest


def _valid_run_id(run_id: object) -> bool:
    return (
        isinstance(run_id, str)
        and bool(run_id)
        and len(run_id) <= 128
        and all(ch.isascii() and (ch.isalnum() or ch in "-_") for ch in run_id)
    )


def _pid_alive(pid) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True
