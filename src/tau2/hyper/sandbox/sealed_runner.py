"""Host proxies for sealed construction-candidate execution.

Hidden tasks and canonical assistant tools remain in the host scorer. Submitted
Python runs in a network-disabled Docker container that receives only
candidate-visible state and messages. LLM requests are mediated by the host.
"""

from __future__ import annotations

import json
import queue
import stat
import subprocess
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import ConfigDict, TypeAdapter

from tau2.agent.base_agent import HalfDuplexAgent
from tau2.data_model.message import AssistantMessage, Message, ToolCall, ToolMessage
from tau2.data_model.tasks import EnvFunctionCall, InitializationData
from tau2.environment.environment import Environment
from tau2.environment.tool import BaseTool
from tau2.environment.toolkit import ToolKitBase, ToolType
from tau2.hyper.agent_context import ModelConfig, get_agent_context
from tau2.hyper.client_api.runtime import ClientAPIRuntime
from tau2.hyper.runtime_contract import DEFAULT_CONSTRUCTION_RUNTIME_IMAGE
from tau2.utils import get_dict_hash
from tau2.utils.utils import get_now

_RESPONSE_PREFIX = "__TAU2_CANDIDATE_RPC__"
_MODEL_REQUEST_PREFIX = "__TAU2_MODEL_REQUEST__"
_CLIENT_API_REQUEST_PREFIX = "__TAU2_CLIENT_API_REQUEST__"
_MESSAGE_ADAPTER = TypeAdapter(Message)
_SAFE_CANDIDATE_MODEL_KWARGS = frozenset(
    {
        "frequency_penalty",
        "max_completion_tokens",
        "max_tokens",
        "modalities",
        "presence_penalty",
        "reasoning_effort",
        "response_format",
        "seed",
        "stop",
        "temperature",
        "thinking",
        "top_p",
    }
)


def _candidate_visible_message(message: Message) -> dict[str, Any]:
    """Serialize a message without trusted-only semantic action metadata."""
    payload = message.model_dump(mode="json", exclude_none=True)
    payload.pop("semantic_tool_calls", None)
    for tool_message in payload.get("tool_messages", []):
        tool_message.pop("semantic_tool_calls", None)
    return payload


@dataclass(frozen=True)
class SealedRunnerConfig:
    """Container settings for candidate execution."""

    kit_path: Path
    # Trusted runtime wiring injected over the sealed pipe at session start.
    # The Developer-readable kit never carries the source domain on disk.
    domain: str
    image: str = DEFAULT_CONSTRUCTION_RUNTIME_IMAGE
    memory: Optional[str] = None
    cpus: Optional[str] = None
    request_timeout_seconds: float = 300.0
    max_model_calls_per_request: int = 32
    max_client_api_calls_per_request: int = 256
    client_api_mode: Optional[str] = None
    client_api_factory: Optional[Callable[..., ClientAPIRuntime]] = None
    client_api_mock: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.client_api_factory is not None and self.client_api_mock is not None:
            raise ValueError(
                "A sealed runner cannot use a real Client API runtime and a "
                "local Client API mock at the same time"
            )
        image_leaf = self.image.rsplit("/", 1)[-1]
        uses_implicit_latest = "@" not in image_leaf and ":" not in image_leaf
        if image_leaf.endswith(":latest") or uses_implicit_latest:
            raise ValueError(
                "Sealed scoring images must use a versioned/commit tag or digest, "
                f"not Docker's mutable latest tag: {self.image!r}"
            )


class SchemaTool(BaseTool):
    """Host-only tool schema used by the trusted model broker."""

    schema_data: dict[str, Any]

    @property
    def openai_schema(self) -> dict[str, Any]:
        return self.schema_data

    def _call(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("SchemaTool is metadata-only")


def _ensure_kit_world_readable(kit_path: Path) -> None:
    """Grant other-read (and dir-traverse) bits across the kit tree.

    The candidate container runs as uid 65534, and on hosts that enforce
    real uids across bind mounts (Linux, unlike Docker Desktop on macOS)
    it cannot enter a kit rooted in a `mkdtemp` directory (mode 0700).
    Best-effort per path: entries owned by other uids are left as-is.
    """
    for path in (kit_path, *kit_path.rglob("*")):
        try:
            mode = path.stat().st_mode
            wanted = 0o005 if stat.S_ISDIR(mode) else 0o004
            if (mode & wanted) != wanted:
                path.chmod(stat.S_IMODE(mode) | wanted)
        except OSError:
            continue


class CandidateProcess:
    """Persistent RPC connection to one isolated candidate container."""

    def __init__(
        self,
        config: SealedRunnerConfig,
        *,
        client_api_runtime: Optional[ClientAPIRuntime] = None,
    ):
        self.config = config
        self.client_api_runtime = client_api_runtime
        self._request_id = 0
        self._lock = threading.Lock()
        self._stderr_tail: deque[str] = deque(maxlen=80)
        self._stdout_lines: queue.Queue[Optional[str]] = queue.Queue(maxsize=1024)
        self.model_gateway = None
        _ensure_kit_world_readable(self.config.kit_path.resolve())
        self._process = self._start()
        self._stdout_thread = threading.Thread(
            target=self._drain_stdout,
            name=f"candidate-stdout-{uuid.uuid4().hex[:8]}",
            daemon=True,
        )
        self._stdout_thread.start()
        self._stderr_thread = threading.Thread(
            target=self._drain_stderr,
            name=f"candidate-stderr-{uuid.uuid4().hex[:8]}",
            daemon=True,
        )
        self._stderr_thread.start()
        self._configure()

    def _configure(self) -> None:
        """Deliver runtime wiring over the sealed pipe at session start.

        The kit no longer carries runtime wiring on disk — anything in the
        kit is Developer-readable — so the trusted host injects the source
        domain here before any other request.
        """
        self.request(
            "configure",
            {
                "domain": self.config.domain,
                "client_api_mode": self.config.client_api_mode,
            },
        )

    def _build_command(self) -> list[str]:
        """Build a command that exposes only the kit and trusted runtime."""
        kit_path = self.config.kit_path.resolve()
        command = [
            "docker",
            "run",
            "--rm",
            "-i",
            "--read-only",
            "--network",
            "none",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "256",
            "--user",
            "65534:65534",
            "--workdir",
            "/workspace",
            "--mount",
            f"type=bind,source={kit_path},target=/workspace,readonly",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,size=512m",
            "-e",
            "HOME=/tmp",
        ]
        if self.config.memory:
            command.extend(["--memory", str(self.config.memory)])
        if self.config.cpus:
            command.extend(["--cpus", str(self.config.cpus)])
        command.extend(
            [
                self.config.image,
                "python",
                "-I",
                "-c",
                (
                    "import sys;"
                    "sys.path.insert(0, '/opt/tau2/src');"
                    "sys.path.append('/workspace');"
                    "from tau2.hyper.sandbox.candidate_server import main;"
                    "main()"
                ),
            ]
        )
        return command

    def _start(self) -> subprocess.Popen:
        try:
            return subprocess.Popen(
                self._build_command(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError as error:
            raise RuntimeError(
                "Sealed scoring requires Docker, but the docker CLI was not found"
            ) from error

    def _drain_stdout(self) -> None:
        process = self._process
        if process.stdout is None:
            self._stdout_lines.put(None)
            return
        for line in process.stdout:
            self._stdout_lines.put(line)
        self._stdout_lines.put(None)

    def _drain_stderr(self) -> None:
        process = self._process
        if process.stderr is None:
            return
        for line in process.stderr:
            self._stderr_tail.append(line.rstrip())

    def _model_response(self, request: dict[str, Any]) -> dict[str, Any]:
        try:
            if self.model_gateway is None:
                raise RuntimeError("Candidate model gateway is not initialized")
            tools = [
                SchemaTool(
                    name=schema.get("function", {}).get("name", "unknown"),
                    schema_data=schema,
                )
                for schema in request.get("tools", [])
            ]
            messages = [
                _MESSAGE_ADAPTER.validate_python(message)
                for message in request.get("messages", [])
            ]
            kwargs = dict(request.get("kwargs") or {})
            tool_choice = kwargs.pop("tool_choice", None)
            unsafe_args = sorted(set(kwargs) - _SAFE_CANDIDATE_MODEL_KWARGS)
            if unsafe_args:
                # Deployment manifests may pin a provider passthrough (an
                # extra_body thinking/reasoning toggle) that the candidate-side
                # gateway supplies on every call for that model. Such a value is
                # evaluation-supplied, not candidate-chosen, so it is accepted
                # only when it exactly equals the matched configuration's pin;
                # any other non-safe-listed argument stays rejected.
                pinned = self.model_gateway.pinned_constraints(request["model"], kwargs)
                unsafe_args = [
                    name
                    for name in unsafe_args
                    if name not in pinned or kwargs[name] != pinned[name]
                ]
            if unsafe_args:
                raise ValueError(
                    "Candidate model request contains unsupported arguments: "
                    + ", ".join(unsafe_args)
                )
            result = self.model_gateway.generate(
                model=request["model"],
                actions=tools or None,
                messages=messages,
                tool_choice=tool_choice,
                call_name=request.get("call_name") or "sealed_candidate_model",
                **kwargs,
            )
            return {
                "id": request.get("id"),
                "ok": True,
                "result": result.model_dump(mode="json", exclude_none=True),
            }
        except Exception as error:
            return {
                "id": request.get("id"),
                "ok": False,
                "error": {"type": type(error).__name__, "message": str(error)},
            }

    def _client_api_response(self, request: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a candidate request to the trusted client-owned runtime."""
        try:
            if self.client_api_runtime is None:
                raise RuntimeError("Client API runtime is not initialized")
            return {
                "id": request.get("id"),
                "ok": True,
                "result": self.client_api_runtime.dispatch(request),
            }
        except Exception as error:
            return {
                "id": request.get("id"),
                "ok": False,
                "error": {"type": type(error).__name__, "message": str(error)},
            }

    def request(self, method: str, payload: Optional[dict] = None) -> Any:
        with self._lock:
            if self._process is None:
                raise RuntimeError("Candidate runner is closed")
            if self._process.poll() is not None:
                details = "\n".join(self._stderr_tail)
                raise RuntimeError(
                    f"Candidate runner exited with {self._process.returncode}: {details}"
                )
            self._request_id += 1
            request_id = self._request_id
            request = {
                "id": request_id,
                "method": method,
                "payload": payload or {},
            }
            assert self._process.stdin is not None
            assert self._process.stdout is not None
            self._process.stdin.write(json.dumps(request) + "\n")
            self._process.stdin.flush()
            deadline = time.monotonic() + self.config.request_timeout_seconds
            model_calls = 0
            client_api_calls = 0
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self.close()
                    raise RuntimeError(
                        f"Candidate {method} request exceeded "
                        f"{self.config.request_timeout_seconds:g}s"
                    )
                try:
                    line = self._stdout_lines.get(timeout=remaining)
                except queue.Empty:
                    self.close()
                    raise RuntimeError(
                        f"Candidate {method} request exceeded "
                        f"{self.config.request_timeout_seconds:g}s"
                    ) from None
                if line is None:
                    details = "\n".join(self._stderr_tail)
                    raise RuntimeError(
                        "Candidate runner closed its response stream"
                        + (f": {details}" if details else "")
                    )
                if line.startswith(_MODEL_REQUEST_PREFIX):
                    model_calls += 1
                    if model_calls > self.config.max_model_calls_per_request:
                        self.close()
                        raise RuntimeError(
                            f"Candidate {method} request exceeded the limit of "
                            f"{self.config.max_model_calls_per_request} model calls"
                        )
                    model_request = json.loads(line[len(_MODEL_REQUEST_PREFIX) :])
                    self._process.stdin.write(
                        json.dumps(self._model_response(model_request)) + "\n"
                    )
                    self._process.stdin.flush()
                    continue
                if line.startswith(_CLIENT_API_REQUEST_PREFIX):
                    client_api_calls += 1
                    if client_api_calls > self.config.max_client_api_calls_per_request:
                        self.close()
                        raise RuntimeError(
                            f"Candidate {method} request exceeded the limit of "
                            f"{self.config.max_client_api_calls_per_request} Client "
                            "API calls"
                        )
                    api_request = json.loads(line[len(_CLIENT_API_REQUEST_PREFIX) :])
                    self._process.stdin.write(
                        json.dumps(self._client_api_response(api_request)) + "\n"
                    )
                    self._process.stdin.flush()
                    continue
                if not line.startswith(_RESPONSE_PREFIX):
                    continue
                response = json.loads(line[len(_RESPONSE_PREFIX) :])
                if response.get("id") != request_id:
                    continue
                if not response.get("ok"):
                    error = response.get("error") or {}
                    raise RuntimeError(
                        f"{error.get('type', 'CandidateError')}: "
                        f"{error.get('message', 'candidate operation failed')}"
                    )
                return response.get("result")

    def close(self) -> None:
        process = getattr(self, "_process", None)
        if process is None:
            return
        if process.stdin is not None:
            try:
                process.stdin.close()
            except OSError:
                pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        self._process = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


class RemoteDBView:
    """DB-shaped snapshot facade used by the private host evaluator."""

    def __init__(
        self,
        runner: CandidateProcess,
        client_api_runtime: Optional[ClientAPIRuntime] = None,
    ):
        self.runner = runner
        self.client_api_runtime = client_api_runtime

    def model_dump(self, **_kwargs) -> dict[str, Any]:
        if self.client_api_runtime is not None:
            return self.client_api_runtime.snapshot() or {}
        return self.runner.request("snapshot") or {}

    def get_hash(self) -> str:
        """Return a stable hash of the current authoritative snapshot."""
        return get_dict_hash(self.model_dump())


class RemoteCandidateTool(BaseTool):
    """Tool metadata facade; calls execute in the candidate container."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    schema_data: dict[str, Any]
    return_schema_data: dict[str, Any]
    info: dict[str, Any]
    runner: Any

    @property
    def returns(self):
        schema = self.return_schema_data

        class ReturnSchema:
            @classmethod
            def model_json_schema(cls):
                return schema

        return ReturnSchema

    @property
    def openai_schema(self) -> dict[str, Any]:
        return self.schema_data

    def _call(self, *args: Any, **kwargs: Any) -> Any:
        if args:
            raise TypeError("Remote candidate tools accept keyword arguments only")
        return self.runner.request(
            "tool_call", {"name": self.name, "arguments": kwargs}
        )

    def to_str(self) -> str:
        function = self.schema_data.get("function", {})
        return json.dumps(
            {
                "name": self.name,
                "description": function.get("description", ""),
                "parameters": function.get("parameters", {}),
            },
            sort_keys=True,
        )


class RemoteCandidateToolkit(ToolKitBase):
    """Toolkit facade backed by a sealed candidate process."""

    def __init__(
        self,
        runner: CandidateProcess,
        metadata: dict[str, Any],
        *,
        client_api_runtime: Optional[ClientAPIRuntime] = None,
    ):
        self.runner = runner
        self._metadata = metadata["tools"]
        self.client_api_runtime = client_api_runtime
        self.db = RemoteDBView(runner, client_api_runtime)
        self._tools = {
            name: RemoteCandidateTool(
                name=name,
                schema_data=definition["schema"],
                return_schema_data=definition.get("return_schema", {}),
                info=definition.get("info", {}),
                runner=runner,
            )
            for name, definition in self._metadata.items()
        }

    @property
    def tools(self):
        return self._tools

    def get_tools(self, include: Optional[list[str]] = None):
        tools = {
            name: tool
            for name, tool in self._tools.items()
            if not self._metadata[name].get("discoverable", False)
        }
        if include is not None:
            allowed = set(include)
            tools = {name: tool for name, tool in tools.items() if name in allowed}
        return tools

    def get_discoverable_tools(self):
        return {
            name: tool
            for name, tool in self._tools.items()
            if self._metadata[name].get("discoverable", False)
        }

    def use_tool(self, tool_name: str, /, **kwargs):
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        return self._tools[tool_name](**kwargs)

    def has_tool(self, tool_name: str) -> bool:
        return tool_name in self._tools

    def has_discoverable_tool(self, tool_name: str) -> bool:
        return tool_name in self.get_discoverable_tools()

    def tool_mutates_state(self, tool_name: str) -> bool:
        return bool(self._metadata[tool_name].get("mutates_state", True))

    def tool_type(self, tool_name: str) -> ToolType:
        value = self._metadata[tool_name].get("info", {}).get("tool_type")
        return ToolType(value) if value is not None else ToolType.GENERIC

    def update_db(self, update_data: Optional[dict[str, Any]] = None):
        if self.client_api_runtime is not None:
            tools = self.client_api_runtime.environment.tools
            if tools is None:
                raise RuntimeError("Client assistant toolkit is missing")
            tools.update_db(update_data or {})
            self.client_api_runtime.sync_environment()
            return
        self.runner.request("update_db", {"data": update_data or {}})


class SealedCandidateEnvironment(Environment):
    """Environment whose assistant side lives in a candidate-only container."""

    def __init__(
        self,
        config: SealedRunnerConfig,
        *,
        metadata: Optional[dict[str, Any]] = None,
        runner: Optional[CandidateProcess] = None,
        client_api_runtime: Optional[ClientAPIRuntime] = None,
    ):
        self.config = config
        self.runner = runner
        self.client_api_runtime = client_api_runtime
        self._developer_setup_actions: list[EnvFunctionCall] = []
        if metadata is None:
            if runner is None:
                runner = CandidateProcess(config)
                self.runner = runner
            metadata = runner.request("metadata")
        self.metadata = metadata
        toolkit = (
            RemoteCandidateToolkit(
                self.runner,
                metadata,
                client_api_runtime=client_api_runtime,
            )
            if self.runner is not None
            else None
        )
        super().__init__(
            domain_name=metadata["domain"],
            policy=metadata["policy"],
            tools=toolkit,
            user_tools=(
                client_api_runtime.environment.user_tools
                if client_api_runtime is not None
                else None
            ),
        )

    @classmethod
    def template(cls, config: SealedRunnerConfig) -> "SealedCandidateEnvironment":
        runner = CandidateProcess(config)
        try:
            metadata = runner.request("metadata")
        finally:
            runner.close()
        return cls(config, metadata=metadata, runner=None)

    def clone(self, *, solo_mode: bool = False) -> "SealedCandidateEnvironment":
        client_api_runtime = (
            self.config.client_api_factory(solo_mode=solo_mode)
            if self.config.client_api_factory is not None
            else None
        )
        runner = CandidateProcess(
            self.config,
            client_api_runtime=client_api_runtime,
        )
        environment = SealedCandidateEnvironment(
            self.config,
            metadata=self.metadata,
            runner=runner,
            client_api_runtime=client_api_runtime,
        )
        environment.set_solo_mode(solo_mode)
        return environment

    def sync_tools(self):
        if self.client_api_runtime is not None:
            self.client_api_runtime.sync_environment()
        if self.runner is not None:
            self.runner.request("sync")

    def get_response(self, message: ToolCall) -> ToolMessage:
        """Attach canonical Client operations executed by a wrapper tool."""
        runtime = self.client_api_runtime
        operation_offset = len(runtime.operation_calls) if runtime is not None else 0
        response = super().get_response(message)
        # Only assistant-side wrapper calls can execute Client operations;
        # user tools (e.g. telecom device tools) must not carry a trace, or
        # replay would refuse the conversation.
        if runtime is not None and message.requestor == "assistant":
            response.semantic_tool_calls = [
                ToolCall(
                    id=f"{message.id}:client-api:{index}",
                    name=call.operation_id,
                    arguments=call.arguments,
                    requestor=message.requestor,
                )
                for index, call in enumerate(runtime.operation_calls[operation_offset:])
            ]
        return response

    def _replay_trusted_tool_call(
        self,
        tool_call: ToolCall,
        expected_response: ToolMessage,
    ) -> bool:
        """Replay host-attached Client API operations instead of the wrapper."""

        runtime = self.client_api_runtime
        semantic_calls = expected_response.semantic_tool_calls
        if runtime is None or semantic_calls is None:
            return False
        if tool_call.requestor != "assistant":
            if semantic_calls:
                raise ValueError(
                    "Trusted Client API semantic traces must belong to assistant calls"
                )
            # Histories recorded before the requestor guard in get_response
            # carry an empty trace list on user-tool responses; replay those
            # through the normal (untrusted) path.
            return False
        for index, semantic_call in enumerate(semantic_calls):
            expected_id = f"{tool_call.id}:client-api:{index}"
            if semantic_call.id != expected_id:
                raise ValueError(
                    f"Semantic call {semantic_call.id!r} is not attributed to "
                    f"outer call {tool_call.id!r}; expected {expected_id!r}"
                )
            runtime.replay_operation(semantic_call)
        return True

    def set_solo_mode(self, solo_mode: bool):
        self.solo_mode = solo_mode
        if self.client_api_runtime is not None:
            self.client_api_runtime.environment.set_solo_mode(solo_mode)

    def configure_developer_setup_actions(self, actions: list[EnvFunctionCall]) -> None:
        """Configure local setup calls that run through candidate wrapper tools."""
        if any(action.env_type != "assistant" for action in actions):
            raise ValueError("Developer setup actions must target assistant tools")
        self._developer_setup_actions = list(actions)

    def configure_development_fixture(self, fixture_id: str | list[str]) -> None:
        """Apply named local fixtures in order inside the trusted Client runtime."""
        if self.client_api_runtime is None:
            raise RuntimeError("Development fixtures require a Client API runtime")
        from tau2.hyper.client_api.development import apply_development_fixtures

        apply_development_fixtures(
            self.client_api_runtime.environment,
            fixture_id,
        )

    def configure_client_api_trial_context(
        self,
        *,
        task_id: str,
        execution_mode: str = "final_evaluation",
        developer_test_scenario_id: Optional[str] = None,
    ) -> None:
        """Bind host-only task identity for deterministic defect activation."""

        if self.client_api_runtime is None:
            return
        from tau2.hyper.client_api.defects import ClientAPITrialContext

        self.client_api_runtime.set_trial_context(
            ClientAPITrialContext(
                task_id=task_id,
                execution_mode=execution_mode,
                developer_test_scenario_id=developer_test_scenario_id,
            )
        )

    def set_state(
        self,
        initialization_data: Optional[InitializationData],
        initialization_actions: Optional[list[EnvFunctionCall]],
        message_history: list[Message],
        strict: bool = True,
        validate_replay_responses: bool = True,
    ):
        if self.runner is None:
            raise RuntimeError("Cannot initialize a sealed environment template")
        if self.client_api_runtime is not None:
            self.client_api_runtime.set_state(
                initialization_data,
                initialization_actions,
                [],
            )
            agent_data = None
            initialization_actions = None
        else:
            agent_data = (
                initialization_data.agent_data
                if initialization_data is not None
                else None
            )
        reset_payload: dict[str, Any] = {
            "agent_data": agent_data,
            "solo_mode": self.solo_mode,
        }
        if self.client_api_runtime is not None:
            reset_payload["client_api_context"] = (
                self.client_api_runtime.context.model_dump(mode="json")
            )
        elif self.config.client_api_mock is not None:
            reset_payload.update(
                {
                    "client_api_context": {
                        "conversation_id": f"conv_local_{uuid.uuid4().hex}"
                    },
                    "client_api_mock": self.config.client_api_mock,
                    "max_client_api_calls_per_request": (
                        self.config.max_client_api_calls_per_request
                    ),
                }
            )
        self.runner.request("reset", reset_payload)
        for action in self._developer_setup_actions:
            self.make_tool_call(
                action.func_name,
                requestor="assistant",
                **action.arguments,
            )
        if initialization_actions:
            for action in initialization_actions:
                if action.env_type != "assistant":
                    continue
                self.make_tool_call(
                    action.func_name,
                    requestor="assistant",
                    **action.arguments,
                )
        super().set_state(
            initialization_data=None,
            initialization_actions=None,
            message_history=message_history,
            strict=strict,
            validate_replay_responses=validate_replay_responses,
        )

    @property
    def uses_client_api_mock(self) -> bool:
        """True when Client API dispatch is a Developer-owned local mock.

        A mock-backed candidate has no authoritative Client database, so
        host-side DB projections (reference user-tool syncs, DB grading)
        do not apply to it.
        """
        return self.config.client_api_mock is not None

    def collect_client_api_mock_report(self) -> Optional[dict[str, Any]]:
        """Return the local mock trace and run its optional verification hook."""
        if self.config.client_api_mock is None:
            return None
        if self.runner is None:
            raise RuntimeError("Cannot inspect a closed sealed candidate environment")
        return self.runner.request("client_api_mock_report")

    def collect_client_api_defect_report(self) -> Optional[dict[str, Any]]:
        """Return trusted deployed-defect telemetry for host-side grading."""

        if self.client_api_runtime is None:
            return None
        return self.client_api_runtime.defect_report()

    def close(self) -> None:
        if self.runner is not None:
            self.runner.close()
            self.runner = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


class SealedCandidateAgent(HalfDuplexAgent):
    """Agent proxy that reveals only visible conversation messages."""

    def __init__(
        self,
        runner: CandidateProcess,
        *,
        model_configs: list[dict[str, Any]],
    ):
        super().__init__(tools=[], domain_policy="")
        self.runner = runner
        self.model_configs = model_configs

    def get_init_state(self, message_history: Optional[list[Message]] = None):
        self.runner.request(
            "initialize_agent",
            {
                "model_configs": self.model_configs,
                "message_history": [
                    _candidate_visible_message(message)
                    for message in (message_history or [])
                ],
            },
        )
        return {"sealed": True}

    def generate_next_message(self, message: Message, state):
        result = self.runner.request(
            "agent_turn",
            {"message": _candidate_visible_message(message)},
        )
        output = _MESSAGE_ADAPTER.validate_python(result)
        if not isinstance(output, AssistantMessage):
            raise TypeError("Candidate agent must return an AssistantMessage")
        # Candidate containers may use a different local timezone. The host
        # owns trajectory ordering, so candidate-provided wall-clock values
        # must not be allowed to reorder a tool call after its result.
        output.timestamp = get_now()
        if output.tool_calls and any(
            tool_call.requestor != "assistant" for tool_call in output.tool_calls
        ):
            raise ValueError(
                "Candidate agents cannot issue customer/user runtime tool calls"
            )
        return output, state

    def is_stop(self, message: Message) -> bool:
        return bool(
            self.runner.request(
                "agent_is_stop",
                {"message": _candidate_visible_message(message)},
            )
        )

    def set_seed(self, seed: int):
        self.runner.request("agent_seed", {"seed": seed})

    def stop(self, message=None, state=None):
        del state
        self.runner.request(
            "agent_stop",
            {
                "message": (
                    _candidate_visible_message(message) if message is not None else None
                )
            },
        )


def _model_config_payload(config: ModelConfig) -> dict[str, Any]:
    payload = {
        "model": config.model,
        "constraints": dict(config.constrained_args),
    }
    if config.credit_rates is not None:
        payload["credit_rates"] = {
            "input_per_million": config.credit_rates.input_per_million,
            "output_per_million": config.credit_rates.output_per_million,
            "rate_card_date": config.credit_rates.rate_card_date,
            "pricing_basis": config.credit_rates.pricing_basis,
            "source_url": config.credit_rates.source_url,
        }
    return payload


def _find_candidate_runner(tools) -> Optional[CandidateProcess]:
    for tool in tools:
        if isinstance(tool, RemoteCandidateTool):
            return tool.runner
    # A submission whose assistant surface is entirely discoverable publishes
    # no RemoteCandidateTool: the reference-user bridge exposes only its
    # discoverable-platform wrappers. Reach the sealed toolkit through the
    # wrapper's bound environment instead.
    for tool in tools:
        bound = getattr(tool, "_func", None)
        owner = getattr(bound, "__self__", None)
        environment = getattr(owner, "assistant_environment", None)
        toolkit = getattr(environment, "tools", None)
        if isinstance(toolkit, RemoteCandidateToolkit):
            return toolkit.runner
    return None


def create_sealed_candidate_agent():
    """Build a proxy from the active host context without importing submission code."""
    context = get_agent_context()
    runner = _find_candidate_runner(context.action_interface.available)
    if runner is None:
        raise RuntimeError("Sealed candidate tools were not provided to agent factory")
    runner.model_gateway = context.model_gateway
    return SealedCandidateAgent(
        runner,
        model_configs=[
            _model_config_payload(config) for config in context.model_gateway.models
        ],
    )
