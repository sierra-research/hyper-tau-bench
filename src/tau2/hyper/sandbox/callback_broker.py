"""Authenticated host callbacks for native Hyper-τ coding harnesses."""

from __future__ import annotations

import json
import secrets
import tempfile
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from tau2.hyper.sandbox.local_test import LocalTestService

if TYPE_CHECKING:
    from tau2.hyper.client import ClientContext
    from tau2.hyper.live_experiment import (
        LiveExperimentContext,
        SampleScenariosContext,
    )


class CallbackBrokerError(RuntimeError):
    """Base error returned by the callback broker."""


class CallbackAuthenticationError(CallbackBrokerError):
    """The per-run callback token was missing or incorrect."""


class CallbackQuotaError(CallbackBrokerError):
    """A callback quota was exhausted."""


class CallbackBroker:
    """Dispatch MCP callbacks while hidden state remains in the host process.

    The container sees a private request directory and a random token. It does
    not receive the Client object, reference evaluator implementation, or raw
    provider credentials. Closing the broker expires the token immediately.
    """

    def __init__(
        self,
        kit_path: Path,
        *,
        toolkit: Optional[Any] = None,
        client_context: Optional[ClientContext] = None,
        live_experiment_context: Optional[LiveExperimentContext] = None,
        sample_scenarios_context: Optional[SampleScenariosContext] = None,
        response_phrasing_pack: Optional[Any] = None,
        local_test_wiring: Optional[Any] = None,
        max_local_tests: int = 50,
    ):
        self.kit_path = Path(kit_path).resolve()
        self.token = secrets.token_urlsafe(32)
        self.client_context = client_context
        self.live_experiment_context = live_experiment_context
        self.sample_scenarios_context = sample_scenarios_context
        self.max_local_tests = max_local_tests
        self.local_tests_used = 0
        self.submitted = threading.Event()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._temp_dir = tempfile.TemporaryDirectory(prefix="tau2_callback_")
        self.callback_dir = Path(self._temp_dir.name)
        self._toolkit = toolkit or LocalTestService(
            self.kit_path,
            response_phrasing_pack=response_phrasing_pack,
            local_test_wiring=local_test_wiring,
        )

    @property
    def client_tool_enabled(self) -> bool:
        """Whether the native harness should be offered ``talk_to_client``."""
        ctx = self.client_context
        return bool(ctx and ctx.client and ctx.client_state is not None)

    @property
    def live_experiment_tool_enabled(self) -> bool:
        """Whether the native harness should be offered the live experiment."""
        return self.live_experiment_context is not None

    @property
    def sample_scenarios_tool_enabled(self) -> bool:
        """Whether the native harness should be offered the sample scenarios."""
        return self.sample_scenarios_context is not None

    def dispatch(self, *, token: str, tool: str, arguments: dict) -> str:
        """Authenticate and dispatch one callback tool invocation."""
        if not secrets.compare_digest(token, self.token):
            raise CallbackAuthenticationError("Invalid or expired callback token")
        if not isinstance(arguments, dict):
            raise CallbackBrokerError("Tool arguments must be an object")

        with self._lock:
            if tool == "run_local_test":
                if self.local_tests_used >= self.max_local_tests:
                    raise CallbackQuotaError("Local-test callback quota exhausted")
                task_path = arguments.get("task_path")
                if not isinstance(task_path, str) or not task_path:
                    raise CallbackBrokerError("run_local_test requires task_path")
                self.local_tests_used += 1
                return self._toolkit.run_local_test(
                    task_path,
                    verbose=bool(arguments.get("verbose", False)),
                    max_steps=int(arguments.get("max_steps", 100)),
                )

            if tool == "talk_to_client":
                ctx = self.client_context
                if not self.client_tool_enabled or ctx is None:
                    raise CallbackBrokerError("No Client is available for this task")
                message = arguments.get("message")
                if not isinstance(message, str) or not message:
                    raise CallbackBrokerError("talk_to_client requires message")
                return ctx.talk(message)

            if tool == "run_live_experiment":
                ctx = self.live_experiment_context
                if ctx is None:
                    raise CallbackBrokerError(
                        "No live experiment is available for this task"
                    )
                if ctx.used:
                    # Names the saved report so a Developer whose MCP client
                    # timed out on the original call can read it from disk.
                    raise CallbackQuotaError(ctx.already_run_message())
                try:
                    return ctx.run()
                except RuntimeError as exc:
                    if "already been run" in str(exc):
                        raise CallbackQuotaError(str(exc)) from exc
                    raise

            if tool == "run_sample_scenarios":
                ctx = self.sample_scenarios_context
                if ctx is None:
                    raise CallbackBrokerError(
                        "No sample scenarios are available for this task"
                    )
                try:
                    return ctx.run()
                except RuntimeError as exc:
                    if "quota" in str(exc):
                        raise CallbackQuotaError(str(exc)) from exc
                    raise

            if tool == "submit":
                if self.submitted.is_set():
                    return "Submission already received."
                self.submitted.set()
                return "Submission received. The current workspace will be evaluated."

            raise CallbackBrokerError(f"Unknown callback tool: {tool}")

    def start(self) -> None:
        """Start processing atomic request files from the mounted directory."""
        if self._thread is not None:
            return
        self.callback_dir.chmod(0o700)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        while not self._stop.wait(0.05):
            for request_path in sorted(self.callback_dir.glob("request-*.json")):
                request_id = request_path.stem.removeprefix("request-")
                if not request_id.isalnum() or len(request_id) > 64:
                    request_path.unlink(missing_ok=True)
                    continue
                claimed_path = self.callback_dir / f"processing-{request_id}.json"
                try:
                    request_path.replace(claimed_path)
                    if claimed_path.is_symlink():
                        raise CallbackBrokerError("Symlinked callback request rejected")
                    if claimed_path.stat().st_size > 1024 * 1024:
                        raise CallbackBrokerError("Callback request is too large")
                    request = json.loads(claimed_path.read_text())
                    output = self.dispatch(
                        token=str(request.get("token", "")),
                        tool=str(request.get("tool", "")),
                        arguments=request.get("arguments", {}),
                    )
                    response = {"ok": True, "result": output}
                except Exception as exc:  # noqa: BLE001 - serialized to MCP client
                    response = {
                        "ok": False,
                        "error": {
                            "type": type(exc).__name__,
                            "message": str(exc),
                        },
                    }
                finally:
                    claimed_path.unlink(missing_ok=True)

                response_path = self.callback_dir / f"response-{request_id}.json"
                temporary_path = self.callback_dir / f".response-{request_id}.tmp"
                temporary_path.write_text(json.dumps(response))
                temporary_path.replace(response_path)

    def metadata(self) -> dict:
        """Return callback configuration without its bearer token."""
        return {
            "transport": "authenticated-file-broker",
            "client_tool_enabled": self.client_tool_enabled,
            "live_experiment_tool_enabled": self.live_experiment_tool_enabled,
            "live_experiment_used": bool(
                self.live_experiment_context and self.live_experiment_context.used
            ),
            "sample_scenarios_tool_enabled": self.sample_scenarios_tool_enabled,
            "sample_scenario_runs_used": (
                self.sample_scenarios_context.runs_used
                if self.sample_scenarios_context is not None
                else 0
            ),
            "max_local_tests": self.max_local_tests,
            "local_tests_used": self.local_tests_used,
            "submitted": self.submitted.is_set(),
        }

    def close(self) -> None:
        """Expire the token, stop request processing, and remove broker files."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        self.token = secrets.token_urlsafe(32)
        self._temp_dir.cleanup()

    def __enter__(self) -> CallbackBroker:
        self.start()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
