"""Contract tests for the IBM Bob Shell harness configuration."""

import json

from tau2.hyper.harnesses.bob import BOB_SHELL_HARNESS_VERSION, BobShellSandboxBuilder
from tau2.hyper.sandbox.builder import SandboxBuilder
from tau2.hyper.sandbox.model_gateway import ModelGatewaySpec, _allowed_upstream_path
from tau2.hyper.sandbox.native_runtime import NativeProcessEvent


def test_bob_builder_identity(monkeypatch):
    monkeypatch.delenv("BOB_TEAM_ID", raising=False)
    builder = BobShellSandboxBuilder("bob-default")

    assert isinstance(builder, SandboxBuilder)
    identity = builder.harness_identity().to_dict()
    assert identity["name"] == "bob"
    assert identity["version"] == BOB_SHELL_HARNESS_VERSION
    assert identity["config"]["mcp_servers"] == ["hyper_tau"]
    assert identity["config"]["team_id"] is False


def test_bob_command_runs_headless_with_the_prompt_as_an_argument(monkeypatch):
    monkeypatch.delenv("BOB_TEAM_ID", raising=False)
    builder = BobShellSandboxBuilder("bob-default")

    command = builder.harness_command()
    assert command[:4] == ["python", "-m", "tau2.hyper.harnesses.prompt_arg_driver", "bob"]
    assert "run" in command and "--format" in command
    assert command[command.index("--format") + 1] == "stream-json"
    assert "--accept-license" in command and "--trust" in command
    assert "--team-id" not in command

    monkeypatch.setenv("BOB_TEAM_ID", "team-1")
    assert BobShellSandboxBuilder("bob-default").harness_command()[-2:] == ["--team-id", "team-1"]


def test_bob_runtime_files_stay_below_the_runtime_home():
    builder = BobShellSandboxBuilder("bob-default")
    files = builder.runtime_files(include_client_tool=True)

    assert all(path.startswith("/runtime-home/") for path in files)
    mcp = json.loads(files[builder.mcp_config_path])
    assert mcp["mcpServers"]["hyper_tau"]["args"] == ["-m", "tau2.hyper.sandbox.callback_mcp"]


def test_bob_model_gateway_environment_points_at_the_sidecar():
    builder = BobShellSandboxBuilder("bob-default")
    spec = ModelGatewaySpec(
        provider="bob",
        model="bob-default",
        token="tok",
        upstream_api_key="real",
        expires_at=1.0,
        upstream_origin="https://bob.example/api",
        wire="bob",
    )
    env = builder.model_gateway_environment(spec)
    assert env["BOB_API_KEY"] == "tok"
    assert env["BOB_GATEWAY_URL"] == spec.base_url
    assert spec.base_url.endswith("/bob")


def test_bob_wire_allows_the_profile_and_inference_surface_only():
    assert _allowed_upstream_path("bob", "GET", "admin/v1/profile")
    assert _allowed_upstream_path("bob", "GET", "inference/v1/model/info")
    assert _allowed_upstream_path("bob", "POST", "inference/v1/chat/completions")
    assert not _allowed_upstream_path("bob", "POST", "admin/v1/profile")
    assert not _allowed_upstream_path("bob", "GET", "inference/v1")
    assert not _allowed_upstream_path("bob", "POST", "telemetry/v1/events")


def test_bob_stream_normalizes_text_tool_calls_and_results():
    builder = BobShellSandboxBuilder("bob-default")
    lines = [
        '{"type":"message","timestamp":"t","role":"user","content":"Run it."}',
        '{"type":"tool_use","timestamp":"t","tool_name":"execute_command","tool_id":"tooluse_1","parameters":{"command":"echo ok"}}',
        '{"type":"tool_result","timestamp":"t","tool_id":"tooluse_1","status":"success","output":"ok"}',
        '{"type":"message","timestamp":"t","role":"assistant","content":"ok"}',
        '{"type":"result","timestamp":"t","status":"success","stats":{"tool_calls":1}}',
        "not json",
    ]
    steps = [
        step
        for line in lines
        for step in builder.normalize_event(NativeProcessEvent(sequence=0, channel="stdout", text=line, elapsed_seconds=0.0))
    ]
    assert [s.role for s in steps] == ["assistant", "tool", "assistant"]
    assert steps[0].tool_calls == [{"id": "tooluse_1", "name": "execute_command", "arguments": {"command": "echo ok"}}]
    assert steps[1].tool_results[0]["result"] == "ok" and steps[1].tool_results[0]["is_error"] is False
    assert steps[2].content == "ok"
