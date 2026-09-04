"""Host-owned developer feedback runners: live experiments and sample scenarios."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from loguru import logger


class LiveExperimentContext:
    """Thread-safe one-shot access to a host-owned live experiment runner.

    When ``workspace_root`` is provided, a successful run's report is also
    persisted under ``simulations/`` in the workspace, mirroring the
    ``local_run_*.json`` artifacts of ``run_local_test``. The report reaches
    native harnesses only through an MCP tool result, and an MCP client with
    a short timeout can drop that result after the experiment completed
    host-side — consuming the one-shot spend with nothing to show for it.
    The on-disk copy lets the Developer recover the report after such a
    client-side timeout.
    """

    def __init__(
        self,
        runner: Callable[[], str],
        *,
        workspace_root: Optional[Path] = None,
    ):
        self._runner = runner
        self._workspace_root = (
            Path(workspace_root) if workspace_root is not None else None
        )
        self._report_path: Optional[str] = None
        self._used = False
        self._lock = threading.Lock()

    @property
    def used(self) -> bool:
        """Whether the single attempt has been consumed."""
        with self._lock:
            return self._used

    @property
    def report_path(self) -> Optional[str]:
        """Workspace-relative path of the persisted report, if one was saved."""
        with self._lock:
            return self._report_path

    def already_run_message(self) -> str:
        """Retry error text; names the saved report so it can be re-read."""
        with self._lock:
            return self._already_run_message_locked()

    def _already_run_message_locked(self) -> str:
        if self._report_path is not None:
            return (
                "The live experiment has already been run. Its report was "
                f"saved to {self._report_path}; read that file to recover "
                "the results."
            )
        return "The live experiment has already been run"

    def run(self) -> str:
        """Run the experiment once, consuming the attempt even on failure."""
        with self._lock:
            if self._used:
                raise RuntimeError(self._already_run_message_locked())
            self._used = True
        report = self._runner()
        artifact_path = self._persist_report(report)
        if artifact_path is None:
            return report
        return f"{report}\n\nSaved artifact: {artifact_path}"

    def _persist_report(self, report: str) -> Optional[str]:
        """Save the report under ``simulations/``; losing the copy is non-fatal."""
        if self._workspace_root is None:
            return None
        try:
            simulations_dir = self._workspace_root / "simulations"
            simulations_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            candidate = simulations_dir / f"live_experiment_{timestamp}.json"
            suffix = 1
            while candidate.exists():
                candidate = (
                    simulations_dir / f"live_experiment_{timestamp}_{suffix}.json"
                )
                suffix += 1
            candidate.write_text(report)
        except OSError as error:
            logger.warning(f"Could not persist the live-experiment report: {error}")
            return None
        relative = candidate.relative_to(self._workspace_root).as_posix()
        with self._lock:
            self._report_path = relative
        return relative


class SampleScenariosContext:
    """Thread-safe quota-limited access to a host-owned sample-scenario runner.

    Unlike the one-shot live experiment, sample scenarios are meant for
    iteration: the Developer may re-run the same fixed scenario set until the
    run quota is exhausted. A failed run still consumes a quota slot.
    """

    def __init__(self, runner: Callable[[], str], *, max_runs: int = 10):
        self._runner = runner
        self._max_runs = max_runs
        self._runs_used = 0
        self._lock = threading.Lock()

    @property
    def runs_used(self) -> int:
        with self._lock:
            return self._runs_used

    @property
    def max_runs(self) -> int:
        return self._max_runs

    def run(self) -> str:
        """Run the scenario set once, consuming a quota slot even on failure."""
        with self._lock:
            if self._runs_used >= self._max_runs:
                raise RuntimeError("The sample-scenario run quota has been exhausted")
            self._runs_used += 1
            remaining = self._max_runs - self._runs_used
        output = self._runner()
        return f"{output}\n\nSample-scenario runs remaining: {remaining}"


# Only conversation-surface fields may reach the Developer. Anything else on
# a message is provider or simulator metadata: litellm's ``raw_data`` echoes
# the request back verbatim, including the user simulator's system prompt
# with the hidden <scenario> instructions, so dumping messages wholesale
# hands the sampled task definitions to the sandbox.
_PARTICIPANT_MESSAGE_FIELDS = ("role", "content", "tool_calls", "turn_idx")
_TOOL_MESSAGE_FIELDS = ("id", "role", "content", "requestor")
_TOOL_CALL_FIELDS = ("id", "name", "arguments", "requestor")


def developer_visible_message_json(message: Any) -> Any:
    """Project one trajectory message onto the developer-visible allowlist.

    This is the canonical message seal for every sandbox-readable surface
    (sample scenarios, live experiments, and local-run artifacts alike);
    persist trajectory messages through it rather than dumping them whole.
    """
    if not hasattr(message, "model_dump"):
        return message
    dump = message.model_dump(mode="json")
    fields = (
        _TOOL_MESSAGE_FIELDS
        if dump.get("role") == "tool"
        else _PARTICIPANT_MESSAGE_FIELDS
    )
    visible = {key: dump[key] for key in fields if key in dump}
    if visible.get("tool_calls"):
        visible["tool_calls"] = [
            {key: call[key] for key in _TOOL_CALL_FIELDS if key in call}
            for call in visible["tool_calls"]
        ]
    return visible


def format_sample_scenario_results(results: Sequence[Any]) -> str:
    """Render developer-visible sample-scenario feedback with stable case ids.

    The Developer sees each recorded conversation plus the client's quality
    score for it — nothing else. No grading rationale, assertion text, or
    reward breakdown may appear here: those describe the hidden evaluation,
    and the sample must read as client-supplied conversation reviews the
    Developer diagnoses unaided. Case ids follow the fixed scenario order so
    a specific case stays trackable across runs; canonical task IDs never
    appear.
    """
    payload = {
        "scenario_count": len(results),
        "score_note": (
            "client_review_score is the client's quality review of how the "
            "conversation was handled: 0 = mishandled, 1 = handled correctly."
        ),
        "cases": [
            {
                "case_id": f"sample_{index:02d}",
                "client_review_score": float(result.reward),
                "conversation": [
                    developer_visible_message_json(message)
                    for message in result.messages
                ],
            }
            for index, result in enumerate(results, start=1)
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def format_live_experiment_results(results: Sequence[Any]) -> str:
    """Render developer-visible live-experiment feedback.

    Sealed to the same contract as sample scenarios: each conversation from
    the one-shot hidden traffic sample plus the client's quality score for
    it — no grading rationale, assertion text, or reward breakdown, and
    canonical task IDs never appear.
    """
    payload = {
        "conversation_count": len(results),
        "score_note": (
            "client_review_score is the client's quality review of how the "
            "conversation was handled: 0 = mishandled, 1 = handled correctly."
        ),
        "cases": [
            {
                "case_id": f"live_{index:03d}",
                "client_review_score": float(result.reward),
                "conversation": [
                    developer_visible_message_json(message)
                    for message in result.messages
                ],
            }
            for index, result in enumerate(results, start=1)
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True)
