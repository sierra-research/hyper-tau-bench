"""Security-boundary tests for sealed construction scoring."""

import io
import json
import os
from pathlib import Path

import pytest

from tau2.data_model.message import (
    AssistantMessage,
    MultiToolMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from tau2.hyper.agent_context import ModelConfig, ModelGateway
from tau2.hyper.sandbox.sealed_runner import (
    CandidateProcess,
    SealedCandidateAgent,
    SealedRunnerConfig,
    _ensure_kit_world_readable,
)


def _config(tmp_path: Path, **kwargs) -> SealedRunnerConfig:
    kwargs.setdefault("domain", "demo")
    return SealedRunnerConfig(
        kit_path=tmp_path,
        **kwargs,
    )


def test_candidate_command_mounts_only_kit_without_network_or_credentials(tmp_path):
    process = CandidateProcess.__new__(CandidateProcess)
    process.config = _config(tmp_path)

    command = process._build_command()
    rendered = " ".join(command)

    assert command[:4] == ["docker", "run", "--rm", "-i"]
    assert "--read-only" in command
    assert "--network none" in rendered
    assert "--cap-drop ALL" in rendered
    assert "no-new-privileges" in command
    assert "--user 65534:65534" in rendered
    assert "target=/workspace,readonly" in rendered
    assert str(tmp_path.resolve()) in rendered
    assert "OPENAI_API_KEY" not in rendered
    assert "ANTHROPIC_API_KEY" not in rendered
    assert "PYTHONPATH=" not in rendered


def test_candidate_cannot_shadow_trusted_tau2_at_process_start(tmp_path):
    process = CandidateProcess.__new__(CandidateProcess)
    process.config = _config(tmp_path)

    command = process._build_command()
    python_index = command.index("python")
    bootstrap = command[python_index + 3]

    assert command[python_index + 1 : python_index + 3] == ["-I", "-c"]
    assert bootstrap.index("/opt/tau2/src") < bootstrap.index("/workspace")
    assert "tau2.hyper.sandbox.candidate_server" in bootstrap


def test_model_broker_enforces_models_constraints_and_safe_arguments(
    tmp_path, monkeypatch
):
    process = CandidateProcess.__new__(CandidateProcess)
    process.config = _config(tmp_path)
    process.model_gateway = ModelGateway(
        models=(
            ModelConfig(
                model="trusted-model",
                constrained_args={"reasoning_effort": "high"},
            ),
        )
    )
    captured = {}

    def fake_generate(**kwargs):
        captured.update(kwargs)
        return AssistantMessage(role="assistant", content="safe")

    monkeypatch.setattr("tau2.hyper.agent_context.generate", fake_generate)
    response = process._model_response(
        {
            "id": "model-call",
            "model": "trusted-model",
            "kwargs": {"temperature": 0.2},
            "messages": [UserMessage(role="user", content="hello").model_dump()],
            "tools": [],
        }
    )

    assert response["ok"] is True
    assert captured["model"] == "trusted-model"
    assert captured["reasoning_effort"] == "high"
    assert captured["temperature"] == 0.2

    disallowed_model = process._model_response(
        {
            "id": "wrong-model",
            "model": "candidate-chosen-model",
            "kwargs": {},
            "messages": [],
            "tools": [],
        }
    )
    unsafe_transport = process._model_response(
        {
            "id": "unsafe-transport",
            "model": "trusted-model",
            "kwargs": {"api_key": "candidate-value"},
            "messages": [],
            "tools": [],
        }
    )

    assert disallowed_model["ok"] is False
    assert "not allowed" in disallowed_model["error"]["message"]
    assert unsafe_transport["ok"] is False
    assert "unsupported arguments: api_key" in unsafe_transport["error"]["message"]


def test_model_broker_accepts_pinned_extra_body_and_rejects_everything_else(
    tmp_path, monkeypatch
):
    pinned_extra_body = {"thinking": {"type": "disabled"}}
    process = CandidateProcess.__new__(CandidateProcess)
    process.config = _config(tmp_path)
    process.model_gateway = ModelGateway(
        models=(
            ModelConfig(
                model="pinned-model",
                constrained_args={"extra_body": pinned_extra_body},
            ),
            ModelConfig(
                model="plain-model",
                constrained_args={"reasoning_effort": "low"},
            ),
        )
    )
    captured = {}

    def fake_generate(**kwargs):
        captured.update(kwargs)
        return AssistantMessage(role="assistant", content="safe")

    monkeypatch.setattr("tau2.hyper.agent_context.generate", fake_generate)

    # The candidate-side gateway resolves the pin into every call's kwargs,
    # so a request carrying the exact pinned value must go through.
    pin_matching = process._model_response(
        {
            "id": "pin-matching",
            "model": "pinned-model",
            "kwargs": {"extra_body": {"thinking": {"type": "disabled"}}},
            "messages": [],
            "tools": [],
        }
    )

    assert pin_matching["ok"] is True
    assert captured["extra_body"] == pinned_extra_body

    divergent_value = process._model_response(
        {
            "id": "divergent-value",
            "model": "pinned-model",
            "kwargs": {"extra_body": {"thinking": {"type": "enabled"}}},
            "messages": [],
            "tools": [],
        }
    )
    unpinned_model = process._model_response(
        {
            "id": "unpinned-model",
            "model": "plain-model",
            "kwargs": {"extra_body": {"thinking": {"type": "disabled"}}},
            "messages": [],
            "tools": [],
        }
    )

    assert divergent_value["ok"] is False
    assert "violates configured constraints" in divergent_value["error"]["message"]
    assert unpinned_model["ok"] is False
    assert "unsupported arguments: extra_body" in unpinned_model["error"]["message"]


def test_client_api_broker_dispatches_only_to_host_owned_runtime(tmp_path):
    from tau2.hyper.client_api import ClientAPIResponse

    class Runtime:
        def __init__(self):
            self.requests = []

        def dispatch(self, request):
            self.requests.append(request)
            return ClientAPIResponse(status_code=200, body={"ok": True}).model_dump()

    runtime = Runtime()
    process = CandidateProcess.__new__(CandidateProcess)
    process.config = _config(tmp_path)
    process.client_api_runtime = runtime
    request = {
        "id": "api-1",
        "method": "POST",
        "path": "/v1/tools/ping",
        "body": {},
    }

    response = process._client_api_response(request)

    assert response["id"] == "api-1"
    assert response["ok"] is True
    assert response["result"]["body"] == {"ok": True}
    assert runtime.requests == [request]


def test_mock_client_api_reset_payload_stays_candidate_local(tmp_path):
    from tau2.hyper.sandbox.sealed_runner import SealedCandidateEnvironment

    class Runner:
        def __init__(self):
            self.calls = []

        def request(self, method, payload=None):
            self.calls.append((method, payload or {}))
            if method == "client_api_mock_report":
                return {"trace": [], "verification": {"status": "passed"}}
            return {"ok": True}

    runner = Runner()
    mock_spec = {
        "module": "workspace/mock_client_api.py",
        "config": {"account_id": "acct_test"},
    }
    environment = SealedCandidateEnvironment(
        _config(
            tmp_path,
            client_api_mode="rest",
            client_api_mock=mock_spec,
            max_client_api_calls_per_request=7,
        ),
        metadata={"domain": "demo", "policy": "", "tools": {}},
        runner=runner,
    )

    environment.set_state(None, None, [])

    reset = next(payload for method, payload in runner.calls if method == "reset")
    assert reset["client_api_mock"] == mock_spec
    assert reset["max_client_api_calls_per_request"] == 7
    assert reset["client_api_context"]["conversation_id"].startswith("conv_local_")
    assert environment.client_api_runtime is None
    assert environment.collect_client_api_mock_report() == {
        "trace": [],
        "verification": {"status": "passed"},
    }


def test_sealed_runner_rejects_real_and_mock_client_api_backends(tmp_path):
    with pytest.raises(ValueError, match="cannot use a real Client API runtime"):
        _config(
            tmp_path,
            client_api_factory=lambda **kwargs: None,
            client_api_mock={"module": "workspace/mock.py", "config": {}},
        )


@pytest.mark.skipif(
    os.getenv("TAU2_RUN_DOCKER_SMOKE") != "1",
    reason="requires the locally built contract-v7 Docker image",
)
def test_sealed_mock_client_api_runs_inside_candidate_container(tmp_path):
    from tau2.hyper.sandbox.sealed_runner import SealedCandidateEnvironment

    kit = tmp_path / "kit"
    workspace = kit / "workspace"
    workspace.mkdir(parents=True)
    (kit / "kit_config.json").write_text('{"domain":"demo","client_api_mode":"rest"}')
    (workspace / "tools.py").write_text(
        """
from tau2.environment.toolkit import ToolType, is_tool
from tau2.hyper.client_api import ClientAPIToolKitBase

class Tools(ClientAPIToolKitBase):
    @is_tool(ToolType.READ)
    def probe(self) -> dict:
        return self.client_api.request("GET", "/v1/probe").body
"""
    )
    (workspace / "mock_client_api.py").write_text(
        """
class Mock:
    def __init__(self, config):
        self.calls = 0

    def request(self, request):
        self.calls += 1
        return {"status_code": 200, "body": {"calls": self.calls}}

    def verify(self):
        assert self.calls == 2

def create_mock_client_api(config):
    return Mock(config)
"""
    )
    config = _config(
        kit,
        image="tau2-construction-runtime:contract-v7",
        client_api_mode="rest",
        client_api_mock={
            "module": "workspace/mock_client_api.py",
            "config": {},
        },
    )
    template = SealedCandidateEnvironment.template(config)
    environment = template.clone()
    try:
        environment.set_state(None, None, [])
        assert environment.make_tool_call("probe") == {"calls": 1}
        assert environment.make_tool_call("probe") == {"calls": 2}
        report = environment.collect_client_api_mock_report()
        assert report["module"] == "workspace/mock_client_api.py"
        assert len(report["trace"]) == 2
        assert report["verification"]["status"] == "passed"
    finally:
        environment.close()


class _RecordingRunner:
    def __init__(self):
        self.calls = []

    def request(self, method, payload=None):
        self.calls.append((method, payload or {}))
        if method == "agent_turn":
            return AssistantMessage(role="assistant", content="done").model_dump()
        if method == "agent_is_stop":
            return False
        return {"ok": True}


def test_candidate_agent_receives_messages_but_no_task_or_evaluator_state():
    runner = _RecordingRunner()
    agent = SealedCandidateAgent(
        runner,
        model_configs=[
            {
                "model": "trusted-model",
                "constraints": {"reasoning_effort": "none"},
            }
        ],
    )
    history = [UserMessage(role="user", content="visible history")]

    state = agent.get_init_state(message_history=history)
    output, _ = agent.generate_next_message(
        UserMessage(role="user", content="visible turn"), state
    )

    init_payload = runner.calls[0][1]
    turn_payload = runner.calls[1][1]
    assert set(init_payload) == {"model_configs", "message_history"}
    assert set(turn_payload) == {"message"}
    assert "visible history" in str(init_payload)
    assert "visible turn" in str(turn_payload)
    assert "task" not in str(runner.calls).lower()
    assert "evaluation" not in str(runner.calls).lower()
    assert output.content == "done"


def test_candidate_agent_never_receives_semantic_tool_calls():
    runner = _RecordingRunner()
    agent = SealedCandidateAgent(
        runner,
        model_configs=[{"model": "trusted-model", "constraints": {}}],
    )
    semantic_call = ToolCall(
        id="outer-1:client-api:0",
        name="private_reference_operation",
        arguments={"private_argument": "value"},
        requestor="assistant",
    )
    tool_message = ToolMessage(
        id="outer-1",
        role="tool",
        content="visible result",
        semantic_tool_calls=[semantic_call],
    )
    multi_tool_message = MultiToolMessage(
        role="tool",
        tool_messages=[tool_message],
    )

    agent.get_init_state(message_history=[tool_message])
    agent.generate_next_message(multi_tool_message, {"sealed": True})
    agent.is_stop(tool_message)
    agent.stop(tool_message, {"sealed": True})

    payloads = {method: payload for method, payload in runner.calls}
    assert (
        "semantic_tool_calls" not in payloads["initialize_agent"]["message_history"][0]
    )
    assert (
        "semantic_tool_calls"
        not in payloads["agent_turn"]["message"]["tool_messages"][0]
    )
    assert "semantic_tool_calls" not in payloads["agent_is_stop"]["message"]
    assert "semantic_tool_calls" not in payloads["agent_stop"]["message"]
    assert tool_message.semantic_tool_calls == [semantic_call]


def test_candidate_agent_outputs_receive_a_trusted_host_timestamp(monkeypatch):
    class ContainerClockRunner(_RecordingRunner):
        def request(self, method, payload=None):
            if method == "agent_turn":
                return AssistantMessage(
                    role="assistant",
                    content="done",
                    timestamp="2099-01-01T00:00:00",
                ).model_dump()
            return super().request(method, payload)

    monkeypatch.setattr(
        "tau2.hyper.sandbox.sealed_runner.get_now",
        lambda: "2026-08-20T15:48:28.000000",
    )
    agent = SealedCandidateAgent(
        ContainerClockRunner(),
        model_configs=[{"model": "trusted-model", "constraints": {}}],
    )

    output, _ = agent.generate_next_message(
        UserMessage(role="user", content="visible turn"), {"sealed": True}
    )

    assert output.timestamp == "2026-08-20T15:48:28.000000"


def test_candidate_agent_cannot_call_customer_runtime_tools():
    class UserToolRunner(_RecordingRunner):
        def request(self, method, payload=None):
            if method == "agent_turn":
                return AssistantMessage(
                    role="assistant",
                    tool_calls=[
                        ToolCall(
                            name="reference_user_probe",
                            arguments={},
                            requestor="user",
                        )
                    ],
                ).model_dump()
            return super().request(method, payload)

    agent = SealedCandidateAgent(
        UserToolRunner(),
        model_configs=[{"model": "trusted-model", "constraints": {}}],
    )

    with pytest.raises(ValueError, match="cannot issue customer/user"):
        agent.generate_next_message(
            UserMessage(role="user", content="hello"), {"sealed": True}
        )


def test_runtime_image_removes_canonical_domains_and_task_data():
    repo_root = Path(__file__).resolve().parents[2]
    dockerfile = (
        repo_root / "docker" / "hyper-construction" / "Dockerfile"
    ).read_text()

    # src/tau2/domains and everything under src/tau2/hyper outside the
    # fail-closed allowlist are removed by the strip script; the Dockerfile
    # must run it and drop the task data.
    assert "strip_runtime_src.py" in dockerfile
    assert "rm -rf data/tau2/domains" in dockerfile
    assert "COPY data/tau2/user_simulator" in dockerfile
    assert "COPY data/tau2/hyper" not in dockerfile


def _remote_toolkit(metadata_tools):
    from tau2.hyper.sandbox.sealed_runner import RemoteCandidateToolkit

    runner = CandidateProcess.__new__(CandidateProcess)
    return RemoteCandidateToolkit(runner, {"tools": metadata_tools}), runner


def test_remote_toolkit_reports_tool_types_from_rpc_metadata():
    from tau2.environment.toolkit import ToolType, get_tool_types

    toolkit, _ = _remote_toolkit(
        {
            "get_balance": {
                "schema": {"function": {"name": "get_balance"}},
                "info": {"tool_type": "read", "mutates_state": False},
                "mutates_state": False,
                "discoverable": False,
            },
            "post_adjustment": {
                "schema": {"function": {"name": "post_adjustment"}},
                "info": {"tool_type": "write", "mutates_state": True},
                "mutates_state": True,
                "discoverable": False,
            },
        }
    )

    assert get_tool_types(toolkit) == {
        "get_balance": ToolType.READ,
        "post_adjustment": ToolType.WRITE,
    }


def test_sealed_agent_factory_reaches_runner_behind_discoverable_only_surface():
    from types import SimpleNamespace

    from tau2.environment.tool import as_tool
    from tau2.hyper.sandbox.sealed_runner import _find_candidate_runner

    toolkit, runner = _remote_toolkit(
        {
            "hidden_lookup": {
                "schema": {"function": {"name": "hidden_lookup"}},
                "info": {"tool_type": "read", "mutates_state": False},
                "mutates_state": False,
                "discoverable": True,
            }
        }
    )
    assert toolkit.get_tools() == {}

    class Bridge:
        def __init__(self, assistant_environment):
            self.assistant_environment = assistant_environment

        def unlock_discoverable_agent_tool(self, tool_name: str) -> str:
            """Unlock a discoverable agent tool.

            Args:
                tool_name: The name of the tool to unlock.
            """
            return tool_name

    bridge = Bridge(SimpleNamespace(tools=toolkit))
    platform_tool = as_tool(bridge.unlock_discoverable_agent_tool)

    assert _find_candidate_runner([platform_tool]) is runner
    assert _find_candidate_runner([]) is None


def test_candidate_metadata_accepts_discoverable_basetool():
    from types import SimpleNamespace

    from tau2.environment.toolkit import ToolType
    from tau2.hyper.sandbox.candidate_server import CandidateServer
    from tau2.hyper.sandbox.sealed_runner import RemoteCandidateTool

    prebuilt = RemoteCandidateTool(
        name="hidden_lookup",
        schema_data={"function": {"name": "hidden_lookup", "parameters": {}}},
        return_schema_data={},
        info={},
        runner=None,
    )

    class PrebuiltToolkit:
        def get_tools(self):
            return {}

        def get_discoverable_tools(self):
            return {"hidden_lookup": prebuilt}

        def tool_type(self, name):
            return ToolType.READ

        def tool_mutates_state(self, name):
            return False

    server = CandidateServer.__new__(CandidateServer)
    server.environment = SimpleNamespace(
        tools=PrebuiltToolkit(), domain_name="demo", policy=""
    )

    entry = server._metadata()["tools"]["hidden_lookup"]
    assert entry["discoverable"] is True
    assert entry["schema"]["function"]["name"] == "hidden_lookup"


def test_candidate_client_api_mock_is_stateful_traced_verified_and_reset(
    tmp_path, monkeypatch
):
    from tau2.hyper.sandbox.candidate_server import CandidateServer

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "tools.py").write_text(
        """
from tau2.environment.toolkit import ToolType, is_tool
from tau2.hyper.client_api import ClientAPIToolKitBase

class Tools(ClientAPIToolKitBase):
    @is_tool(ToolType.READ)
    def probe(self, key: str) -> dict:
        response = self.client_api.request(
            "GET", "/v1/probe", query={"key": key}
        )
        return response.model_dump(mode="json")
"""
    )
    (workspace / "mock_client_api.py").write_text(
        """
class MockClientAPI:
    def __init__(self, config):
        self.calls = 0
        self.expected = config["expected"]

    def request(self, request):
        self.calls += 1
        if request["query"].get("key") == "explode":
            raise RuntimeError("developer mock exploded")
        return {
            "status_code": 200,
            "body": {"sequence": self.calls, "request": request},
        }

    def verify(self):
        assert self.calls == self.expected, f"expected {self.expected} calls"
        return {"calls": self.calls}

def create_mock_client_api(config):
    return MockClientAPI(config)
"""
    )
    monkeypatch.chdir(tmp_path)
    server = CandidateServer("demo", client_api_mode="rest")
    reset = {
        "client_api_context": {"conversation_id": "conv_mock"},
        "client_api_mock": {
            "module": "workspace/mock_client_api.py",
            "config": {"expected": 2},
        },
    }

    server.dispatch("reset", reset)
    first = server.dispatch("tool_call", {"name": "probe", "arguments": {"key": "x"}})
    second = server.dispatch("tool_call", {"name": "probe", "arguments": {"key": "x"}})
    report = server.dispatch("client_api_mock_report", {})

    assert first["body"]["sequence"] == 1
    assert second["body"]["sequence"] == 2
    assert report["verification"] == {
        "status": "passed",
        "result": {"calls": 2},
    }
    assert [entry["request"] for entry in report["trace"]] == [
        {
            "method": "GET",
            "path": "/v1/probe",
            "query": {"key": "x"},
            "body": None,
            "headers": {},
        },
        {
            "method": "GET",
            "path": "/v1/probe",
            "query": {"key": "x"},
            "body": None,
            "headers": {},
        },
    ]

    reset["client_api_mock"]["config"]["expected"] = 1
    server.dispatch("reset", reset)
    after_reset = server.dispatch(
        "tool_call", {"name": "probe", "arguments": {"key": "x"}}
    )
    assert after_reset["body"]["sequence"] == 1
    assert len(server.dispatch("client_api_mock_report", {})["trace"]) == 1

    reset["client_api_mock"]["config"]["expected"] = 1
    server.dispatch("reset", reset)
    with pytest.raises(RuntimeError, match="developer mock exploded"):
        server.dispatch("tool_call", {"name": "probe", "arguments": {"key": "explode"}})
    error_report = server.dispatch("client_api_mock_report", {})
    assert error_report["trace"][0]["error"] == {
        "type": "RuntimeError",
        "message": "developer mock exploded",
    }

    reset["client_api_mock"]["config"]["expected"] = 2
    server.dispatch("reset", reset)
    server.dispatch("tool_call", {"name": "probe", "arguments": {"key": "x"}})
    failed_verification = server.dispatch("client_api_mock_report", {})
    assert failed_verification["verification"] == {
        "status": "failed",
        "error": {
            "type": "AssertionError",
            "message": "expected 2 calls",
        },
    }
    assert server.dispatch("client_api_mock_report", {}) == failed_verification


def test_dispatch_supplies_defaults_for_optional_agent_hooks():
    """Contract-minimal agents must survive the optional-hook RPCs.

    The agent contract only requires get_init_state and generate_next_message;
    is_stop/set_seed/stop are optional (observed 2026-08-21: a builder-authored
    agent without is_stop crashed every sealed simulation).
    """
    from tau2.hyper.sandbox.candidate_server import CandidateServer

    class MinimalAgent:
        def get_init_state(self, message_history=None):
            return {}

        def generate_next_message(self, message, state):
            raise NotImplementedError

    server = CandidateServer.__new__(CandidateServer)
    server.agent = MinimalAgent()
    server.agent_state = {}

    plain = {"role": "assistant", "content": "How can I help?"}
    assert server.dispatch("agent_is_stop", {"message": plain}) is False
    assert server.dispatch("agent_seed", {"seed": 7}) == {"ok": True}
    assert server.dispatch("agent_stop", {"message": plain}) == {"ok": True}

    class StoppingAgent(MinimalAgent):
        def is_stop(self, message):
            return True

    server.agent = StoppingAgent()
    assert server.dispatch("agent_is_stop", {"message": plain}) is True


def test_kit_tree_gains_other_read_bits_for_unprivileged_candidate_user(tmp_path):
    kit = tmp_path / "kit"
    kit.mkdir(mode=0o700)
    nested = kit / "sections"
    nested.mkdir(mode=0o700)
    config = kit / "sop.md"
    config.write_text("# SOP\n")
    config.chmod(0o600)
    artifact = nested / "notes.md"
    artifact.write_text("x")
    artifact.chmod(0o640)

    _ensure_kit_world_readable(kit)

    assert kit.stat().st_mode & 0o005 == 0o005
    assert nested.stat().st_mode & 0o005 == 0o005
    assert config.stat().st_mode & 0o004 == 0o004
    assert artifact.stat().st_mode & 0o004 == 0o004
    # Owner bits stay untouched.
    assert config.stat().st_mode & 0o600 == 0o600


def test_candidate_process_sends_configure_wiring_at_session_start(tmp_path):
    """Runtime wiring reaches the container over the sealed pipe, not disk."""
    process = CandidateProcess.__new__(CandidateProcess)
    calls = []
    process.request = lambda method, payload=None: calls.append((method, payload))

    process.config = _config(tmp_path, domain="telecom", client_api_mode="rest")
    process._configure()
    assert calls == [("configure", {"domain": "telecom", "client_api_mode": "rest"})]


def _run_candidate_server_main(monkeypatch, capsys, requests):
    from tau2.hyper.sandbox import candidate_server

    created = []

    class FakeServer:
        def __init__(self, domain, *, client_api_mode=None):
            created.append((domain, client_api_mode))

        def dispatch(self, method, payload):
            return {"echo": method}

    monkeypatch.setattr(candidate_server, "CandidateServer", FakeServer)
    monkeypatch.setattr(
        candidate_server.sys,
        "stdin",
        io.StringIO("".join(json.dumps(request) + "\n" for request in requests)),
    )
    candidate_server.main()
    responses = [
        json.loads(line[len(candidate_server._RESPONSE_PREFIX) :])
        for line in capsys.readouterr().out.splitlines()
        if line.startswith(candidate_server._RESPONSE_PREFIX)
    ]
    return created, responses


def test_candidate_server_main_configures_from_host_request(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.chdir(tmp_path)
    created, responses = _run_candidate_server_main(
        monkeypatch,
        capsys,
        [
            {
                "id": 1,
                "method": "configure",
                "payload": {"domain": "telecom", "client_api_mode": "rest"},
            },
            {"id": 2, "method": "metadata", "payload": {}},
        ],
    )
    assert created == [("telecom", "rest")]
    assert responses[0]["ok"] is True
    assert responses[1]["ok"] is True
    assert responses[1]["result"] == {"echo": "metadata"}


def test_candidate_server_main_ignores_legacy_kit_config(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "kit_config.json").write_text(
        json.dumps({"domain": "retail", "client_api_mode": None})
    )
    created, responses = _run_candidate_server_main(
        monkeypatch,
        capsys,
        [{"id": 1, "method": "metadata", "payload": {}}],
    )
    assert created == []
    assert responses[0]["ok"] is False
    assert "configure" in responses[0]["error"]["message"]


def test_candidate_server_main_requires_wiring_before_dispatch(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.chdir(tmp_path)
    created, responses = _run_candidate_server_main(
        monkeypatch,
        capsys,
        [{"id": 1, "method": "metadata", "payload": {}}],
    )
    assert created == []
    assert responses[0]["ok"] is False
    assert "configure" in responses[0]["error"]["message"]
