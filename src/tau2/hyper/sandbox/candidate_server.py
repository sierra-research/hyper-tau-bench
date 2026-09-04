"""Trusted RPC shim for executing a construction submission in Docker.

The server has no task-loading or registry dependency. It receives only
candidate-visible database state and conversation messages. Model calls are
brokered back to the host, so the candidate gets no provider credentials or
network access.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from tau2.data_model.message import Message
from tau2.data_model.tasks import InitializationData
from tau2.environment.db import DB
from tau2.environment.environment import Environment
from tau2.environment.tool import BaseTool, as_tool
from tau2.environment.toolkit import ToolKitBase
from tau2.hyper.client_api import ClientAPI, ClientAPIContext, ClientAPIToolKitBase

_RESPONSE_PREFIX = "__TAU2_CANDIDATE_RPC__"
_MODEL_REQUEST_PREFIX = "__TAU2_MODEL_REQUEST__"
_CLIENT_API_REQUEST_PREFIX = "__TAU2_CLIENT_API_REQUEST__"
_MESSAGE_ADAPTER = TypeAdapter(Message)


def _json_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


def _brokered_generate(*, model, tools, messages, call_name="llm_call", **kwargs):
    """Replace direct provider access with a host-mediated model call."""
    request_id = uuid.uuid4().hex
    payload = {
        "id": request_id,
        "model": model,
        "tools": [tool.openai_schema for tool in (tools or [])],
        "messages": [_json_value(message) for message in messages],
        "call_name": call_name,
        "kwargs": _json_value(kwargs),
    }
    sys.stdout.write(_MODEL_REQUEST_PREFIX + json.dumps(payload) + "\n")
    sys.stdout.flush()
    response = json.loads(sys.stdin.readline())
    if response.get("id") != request_id:
        raise RuntimeError("Model broker returned a mismatched response")
    if not response.get("ok"):
        error = response.get("error") or {}
        raise RuntimeError(error.get("message", "Model broker call failed"))
    return _MESSAGE_ADAPTER.validate_python(response["result"])


def _install_model_broker() -> None:
    import tau2.utils.llm_utils as llm_utils
    from tau2.hyper import agent_context

    llm_utils.generate = _brokered_generate
    agent_context.generate = _brokered_generate
    # LLMAgent imports generate into its module namespace. Patch it too if an
    # eager import happened before the submitted agent module was loaded.
    module = sys.modules.get("tau2.agent.llm_agent")
    if module is not None:
        module.generate = _brokered_generate


def _brokered_client_api_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Send one Client API request to the trusted host runtime."""
    request_id = uuid.uuid4().hex
    request = {"id": request_id, **payload}
    sys.stdout.write(_CLIENT_API_REQUEST_PREFIX + json.dumps(request) + "\n")
    sys.stdout.flush()
    response = json.loads(sys.stdin.readline())
    if response.get("id") != request_id:
        raise RuntimeError("Client API broker returned a mismatched response")
    if not response.get("ok"):
        error = response.get("error") or {}
        raise RuntimeError(error.get("message", "Client API broker call failed"))
    return response["result"]


def _resolve_mock_module_path(path: str) -> Path:
    """Resolve a Developer mock module while keeping it inside workspace/."""
    candidate = Path(path)
    if candidate.is_absolute() or candidate.suffix != ".py":
        raise ValueError("Client API mock module must be a relative .py file")
    workspace = Path("workspace").resolve()
    resolved = candidate.resolve()
    if not resolved.is_relative_to(workspace):
        raise ValueError("Client API mock module must be inside workspace/")
    if not resolved.is_file():
        raise FileNotFoundError(f"Client API mock module not found: {path}")
    return resolved


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    with contextlib.redirect_stdout(sys.stderr):
        spec.loader.exec_module(module)
    return module


def _find_subclass(module, base_class):
    if module is None:
        return None
    for attr in dir(module):
        value = getattr(module, attr)
        if (
            isinstance(value, type)
            and issubclass(value, base_class)
            and value is not base_class
        ):
            return value
    return None


def _find_database_file(name: str) -> Path | None:
    for extension in (".json", ".toml", ".yaml", ".yml"):
        candidate = Path("database") / f"{name}{extension}"
        if candidate.is_file():
            return candidate
    return None


def _load_environment(
    domain: str, *, client_api_mode: str | None = None
) -> Environment:
    workspace = Path("workspace")
    data_model_path = workspace / "data_model.py"
    tools_path = workspace / "tools.py"
    if not tools_path.is_file():
        raise RuntimeError("workspace/tools.py is required")
    if client_api_mode is None and not data_model_path.is_file():
        raise RuntimeError(
            "workspace/data_model.py and workspace/tools.py are required"
        )

    workspace_text = str(workspace.resolve())
    if workspace_text not in sys.path:
        # Keep the trusted tau2 runtime and installed dependencies ahead of
        # candidate-controlled modules. The workspace is needed only for
        # sibling imports such as ``from data_model import ExampleDB``.
        sys.path.append(workspace_text)

    data_model_module = (
        _load_module("data_model", data_model_path)
        if client_api_mode is None and data_model_path.is_file()
        else None
    )
    user_data_model_module = None
    if client_api_mode is None and (workspace / "user_data_model.py").is_file():
        user_data_model_module = _load_module(
            "user_data_model", workspace / "user_data_model.py"
        )
    tools_module = _load_module("tools", tools_path)
    user_tools_module = None
    if client_api_mode is None and (workspace / "user_tools.py").is_file():
        user_tools_module = _load_module("user_tools", workspace / "user_tools.py")

    if client_api_mode == "rest":
        toolkit_class = _find_subclass(tools_module, ClientAPIToolKitBase)
        if toolkit_class is None:
            raise RuntimeError(
                "REST client API submissions must define a "
                "ClientAPIToolKitBase subclass"
            )
        toolkit = toolkit_class(ClientAPI(_brokered_client_api_request))
    else:
        db_class = _find_subclass(data_model_module, DB)
        toolkit_class = _find_subclass(tools_module, ToolKitBase)
        if db_class is None or toolkit_class is None:
            raise RuntimeError("Submission must define DB and ToolKitBase subclasses")

        db_path = _find_database_file("db")
        if db_path is None:
            raise RuntimeError("database/db.{json,toml,yaml,yml} is required")
        toolkit = toolkit_class(db_class.load(str(db_path)))

    user_toolkit = None
    user_toolkit_class = _find_subclass(user_tools_module, ToolKitBase)
    if user_toolkit_class is not None:
        user_db_class = _find_subclass(user_data_model_module, DB)
        user_db_path = _find_database_file("user_db")
        if user_db_path is not None:
            if user_db_class is None:
                raise RuntimeError(
                    "workspace/user_data_model.py must define a DB subclass"
                )
            user_db = user_db_class.load(str(user_db_path))
        else:
            user_db = toolkit.db
        user_toolkit = user_toolkit_class(user_db)

    policy_path = workspace / "policy.md"
    policy = policy_path.read_text() if policy_path.is_file() else ""
    environment_module = None
    if client_api_mode is None and (workspace / "environment.py").is_file():
        environment_module = _load_module("environment", workspace / "environment.py")
    environment_factory = getattr(environment_module, "create_environment", None)
    if callable(environment_factory):
        environment = environment_factory(
            domain_name=domain,
            policy=policy,
            tools=toolkit,
            user_tools=user_toolkit,
        )
    else:
        environment = Environment(
            domain_name=domain,
            policy=policy,
            tools=toolkit,
            user_tools=user_toolkit,
        )
    if not isinstance(environment, Environment):
        raise RuntimeError("create_environment() must return an Environment")
    return environment


def _load_agent_factory():
    agent_path = Path("workspace/agent.py")
    if not agent_path.is_file():
        return None
    module = _load_module("kit_agent", agent_path)
    factory = getattr(module, "create_agent", None)
    return factory if callable(factory) else None


class CandidateServer:
    """Stateful executor for one candidate environment."""

    def __init__(self, domain: str, *, client_api_mode: str | None = None):
        _install_model_broker()
        self.domain = domain
        self.client_api_mode = client_api_mode
        self.environment = _load_environment(domain, client_api_mode=client_api_mode)
        self.agent_factory = _load_agent_factory()
        self.agent = None
        self.agent_state = None
        self._client_api_mock = None
        self._client_api_mock_request = None
        self._client_api_mock_module_path = None
        self._client_api_mock_trace: list[dict[str, Any]] = []
        self._client_api_mock_verification = None
        self._client_api_calls_in_dispatch = 0
        self._max_client_api_calls_per_request = 256

    def _configure_client_api_mock(self, specification: dict[str, Any]) -> None:
        """Load a fresh Developer-owned mock instance inside the candidate."""
        if self.client_api_mode != "rest":
            raise RuntimeError("Client API mocks require a REST construction kit")
        module_path = _resolve_mock_module_path(str(specification["module"]))
        module = _load_module(
            f"kit_client_api_mock_{uuid.uuid4().hex}",
            module_path,
        )
        factory = getattr(module, "create_mock_client_api", None)
        if not callable(factory):
            raise RuntimeError(
                "Client API mock module must define create_mock_client_api(config)"
            )
        with contextlib.redirect_stdout(sys.stderr):
            mock = factory(dict(specification.get("config") or {}))
        request = getattr(mock, "request", None)
        if not callable(request) and callable(mock):
            request = mock
        if not callable(request):
            raise RuntimeError(
                "create_mock_client_api(config) must return a callable or an "
                "object with request(payload)"
            )
        self._client_api_mock = mock
        self._client_api_mock_request = request
        self._client_api_mock_module_path = specification["module"]
        self._client_api_mock_trace = []
        self._client_api_mock_verification = None
        toolkit = self.environment.tools
        if not isinstance(toolkit, ClientAPIToolKitBase):
            raise RuntimeError(
                "Client API mock requires a ClientAPIToolKitBase toolkit"
            )
        toolkit.client_api._transport = self._mock_client_api_request

    def _mock_client_api_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Dispatch and trace one request without leaving the sealed candidate."""
        self._client_api_calls_in_dispatch += 1
        request = json.loads(json.dumps(payload))
        entry: dict[str, Any] = {
            "index": len(self._client_api_mock_trace) + 1,
            "request": request,
        }
        if self._client_api_calls_in_dispatch > self._max_client_api_calls_per_request:
            error = RuntimeError(
                "Candidate request exceeded the limit of "
                f"{self._max_client_api_calls_per_request} Client API calls"
            )
            entry["error"] = {
                "type": type(error).__name__,
                "message": str(error),
            }
            self._client_api_mock_trace.append(entry)
            raise error
        try:
            assert self._client_api_mock_request is not None
            with contextlib.redirect_stdout(sys.stderr):
                response = self._client_api_mock_request(request)
            entry["response"] = _json_value(response)
            return response
        except Exception as error:
            entry["error"] = {
                "type": type(error).__name__,
                "message": str(error),
            }
            raise
        finally:
            self._client_api_mock_trace.append(entry)

    def _client_api_mock_report(self) -> dict[str, Any]:
        if self._client_api_mock is None:
            raise RuntimeError("Client API mock is not initialized")
        if self._client_api_mock_verification is None:
            verify = getattr(self._client_api_mock, "verify", None)
            if not callable(verify):
                self._client_api_mock_verification = {"status": "not_configured"}
            else:
                try:
                    with contextlib.redirect_stdout(sys.stderr):
                        result = verify()
                    self._client_api_mock_verification = {
                        "status": "passed",
                        "result": _json_value(result),
                    }
                except Exception as error:
                    self._client_api_mock_verification = {
                        "status": "failed",
                        "error": {
                            "type": type(error).__name__,
                            "message": str(error),
                        },
                    }
        return {
            "module": self._client_api_mock_module_path,
            "trace": list(self._client_api_mock_trace),
            "verification": self._client_api_mock_verification,
        }

    def _metadata(self) -> dict[str, Any]:
        toolkit = self.environment.tools
        if toolkit is None:
            raise RuntimeError("Candidate assistant toolkit is missing")
        regular = toolkit.get_tools()
        discoverable = {
            name: function if isinstance(function, BaseTool) else as_tool(function)
            for name, function in toolkit.get_discoverable_tools().items()
        }
        return {
            "domain": self.environment.domain_name,
            "policy": self.environment.policy,
            "tools": {
                name: {
                    "schema": tool.openai_schema,
                    "return_schema": tool.returns.model_json_schema(),
                    "info": {
                        **tool.info,
                        "tool_type": toolkit.tool_type(name).value,
                        "mutates_state": toolkit.tool_mutates_state(name),
                    },
                    "mutates_state": toolkit.tool_mutates_state(name),
                    "discoverable": False,
                }
                for name, tool in regular.items()
            }
            | {
                name: {
                    "schema": tool.openai_schema,
                    "return_schema": tool.returns.model_json_schema(),
                    "info": {
                        **tool.info,
                        "tool_type": toolkit.tool_type(name).value,
                        "mutates_state": toolkit.tool_mutates_state(name),
                    },
                    "mutates_state": toolkit.tool_mutates_state(name),
                    "discoverable": True,
                }
                for name, tool in discoverable.items()
            },
        }

    def _reset(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.environment = _load_environment(
            self.domain, client_api_mode=self.client_api_mode
        )
        self.agent = None
        self.agent_state = None
        self._client_api_mock = None
        self._client_api_mock_request = None
        self._client_api_mock_module_path = None
        self._client_api_mock_trace = []
        self._client_api_mock_verification = None
        self._max_client_api_calls_per_request = int(
            payload.get("max_client_api_calls_per_request", 256)
        )
        self.environment.set_solo_mode(bool(payload.get("solo_mode", False)))
        client_api_context = payload.get("client_api_context")
        if client_api_context is not None:
            toolkit = self.environment.tools
            if not isinstance(toolkit, ClientAPIToolKitBase):
                raise RuntimeError(
                    "Client API context requires a ClientAPIToolKitBase toolkit"
                )
            toolkit.client_api._set_context(
                ClientAPIContext.model_validate(client_api_context)
            )
        client_api_mock = payload.get("client_api_mock")
        if client_api_mock is not None:
            self._configure_client_api_mock(client_api_mock)
        agent_data = payload.get("agent_data")
        if agent_data is not None:
            self.environment.set_state(
                initialization_data=InitializationData(
                    agent_data=agent_data,
                    user_data=None,
                ),
                initialization_actions=None,
                message_history=[],
            )
        return {"ok": True}

    def _initialize_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        from tau2.hyper.agent_context import (
            activate_agent_context,
            build_agent_context,
        )

        if self.agent_factory is not None:
            context = build_agent_context(
                domain=self.domain,
                tools=self.environment.get_tools(),
                resource_root=Path.cwd(),
                model_configs=payload["model_configs"],
            )
            with activate_agent_context(context):
                self.agent = self.agent_factory()
        else:
            from tau2.agent.llm_agent import LLMAgent

            model_config = payload["model_configs"][0]
            self.agent = LLMAgent(
                tools=self.environment.get_tools(),
                domain_policy=self.environment.policy,
                llm=model_config["model"],
                llm_args=dict(model_config.get("constraints") or {}),
            )
        history = [
            _MESSAGE_ADAPTER.validate_python(message)
            for message in payload.get("message_history", [])
        ]
        self.agent_state = self.agent.get_init_state(message_history=history)
        return {"ok": True}

    def dispatch(self, method: str, payload: dict[str, Any]) -> Any:
        self._client_api_calls_in_dispatch = 0
        if method == "metadata":
            return self._metadata()
        if method == "reset":
            return self._reset(payload)
        if method == "initialize_agent":
            return self._initialize_agent(payload)
        if method == "agent_turn":
            if self.agent is None:
                raise RuntimeError("Agent has not been initialized")
            message = _MESSAGE_ADAPTER.validate_python(payload["message"])
            output, self.agent_state = self.agent.generate_next_message(
                message, self.agent_state
            )
            return output.model_dump(mode="json", exclude_none=True)
        # The agent contract only requires get_init_state and
        # generate_next_message; is_stop/set_seed/stop are optional hooks, so
        # fall back to framework defaults when a candidate omits them.
        if method == "agent_is_stop":
            if self.agent is None:
                return False
            is_stop = getattr(self.agent, "is_stop", None)
            if is_stop is None:
                # BaseParticipant default: the participant never signals stop.
                return False
            message = _MESSAGE_ADAPTER.validate_python(payload["message"])
            return bool(is_stop(message))
        if method == "agent_seed":
            if self.agent is not None:
                set_seed = getattr(self.agent, "set_seed", None)
                if set_seed is not None:
                    set_seed(int(payload["seed"]))
            return {"ok": True}
        if method == "agent_stop":
            stop = getattr(self.agent, "stop", None) if self.agent else None
            if stop is not None:
                message = payload.get("message")
                parsed = (
                    _MESSAGE_ADAPTER.validate_python(message)
                    if message is not None
                    else None
                )
                stop(parsed, self.agent_state)
            return {"ok": True}
        if method == "tool_call":
            return self.environment.make_tool_call(
                payload["name"],
                requestor="assistant",
                **(payload.get("arguments") or {}),
            )
        if method == "update_db":
            if self.environment.tools is None:
                raise RuntimeError("Candidate assistant toolkit is missing")
            self.environment.tools.update_db(payload.get("data") or {})
            self.environment.sync_tools()
            return {"ok": True}
        if method == "snapshot":
            if self.environment.tools is None or self.environment.tools.db is None:
                return None
            return self.environment.tools.db.model_dump(mode="json", by_alias=True)
        if method == "sync":
            self.environment.sync_tools()
            return {"ok": True}
        if method == "client_api_mock_report":
            return self._client_api_mock_report()
        raise ValueError(f"Unknown candidate RPC method: {method}")


def main() -> None:
    server: CandidateServer | None = None
    for raw_line in sys.stdin:
        request = None
        try:
            request = json.loads(raw_line)
            method = str(request.get("method"))
            payload = request.get("payload") or {}
            if method == "configure":
                domain = payload.get("domain")
                if not domain:
                    raise ValueError("configure requires a domain")
                server = CandidateServer(
                    domain, client_api_mode=payload.get("client_api_mode")
                )
                result: Any = {"ok": True}
            else:
                if server is None:
                    raise RuntimeError(
                        "Candidate runtime wiring is not configured: the host must "
                        "send a 'configure' request first"
                    )
                result = server.dispatch(method, payload)
            response = {
                "id": request.get("id"),
                "ok": True,
                "result": _json_value(result),
            }
        except Exception as error:
            response = {
                "id": request.get("id") if request else None,
                "ok": False,
                "error": {
                    "type": type(error).__name__,
                    "message": str(error),
                },
            }
        sys.stdout.write(_RESPONSE_PREFIX + json.dumps(response, default=str) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
