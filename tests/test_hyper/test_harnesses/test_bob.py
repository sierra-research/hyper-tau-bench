"""Contract tests for the IBM Bob Shell harness configuration."""

import json

from tau2.hyper.harnesses.bob import BOB_SHELL_HARNESS_VERSION, BobShellSandboxBuilder
from tau2.hyper.sandbox.builder import SandboxBuilder
from tau2.hyper.sandbox.model_gateway import (
    _REQUEST_HEADERS,
    ModelGatewaySpec,
    _allowed_upstream_path,
    _pin_bob_profile_to_gateway,
)
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


class _Broker:
    token = "cb-token"
    client_tool_enabled = True


def test_bob_runtime_files_stay_below_the_runtime_home():
    builder = BobShellSandboxBuilder("bob-default")
    files = builder.runtime_files(include_client_tool=True)

    assert all(path.startswith("/runtime-home/") for path in files)
    mcp = json.loads(files[builder.mcp_config_path])
    assert mcp["mcpServers"]["hyper_tau"]["args"] == ["-m", "tau2.hyper.sandbox.callback_mcp"]


def test_bob_mcp_entry_carries_the_callback_environment_by_value():
    # Bob starts an MCP server with an empty environment, so the entry names
    # the benchmark's package and the callback values the builder set.
    builder = BobShellSandboxBuilder("bob-default")
    environment = builder.runtime_environment(_Broker())
    assert environment["BOB_TELEMETRY_PROVIDER"] == "none"

    mcp = json.loads(builder.runtime_files(include_client_tool=True)[builder.mcp_config_path])
    env = mcp["mcpServers"]["hyper_tau"]["env"]
    assert env["PYTHONPATH"] == "/workspace:/opt/tau2/src"
    assert env["TAU2_CALLBACK_DIR"] == "/run/tau2-callback"
    assert env["TAU2_CALLBACK_TOKEN"] == "cb-token"
    assert env["TAU2_CLIENT_TOOL_ENABLED"] == "1"
    assert "BOB_LOG_LEVEL" not in env


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
    # Bob appends /admin/v1/profile and /inference/v1/... to this URL, and the
    # sidecar scopes requests below /<provider>/v1/.
    assert env["BOB_GATEWAY_URL"] == f"{spec.base_url}/v1"
    assert env["BOB_GATEWAY_URL"].endswith("/bob/v1")
    assert spec.metadata()["allowed_api_families"] == ["admin/v1/profile", "inference/v1"]


def test_bob_wire_relays_the_profile_without_a_region_and_with_bobs_headers():
    assert {"x-instance-id", "x-team-id"} <= _REQUEST_HEADERS
    profile = {
        "user_id": "u",
        "instances": [
            {"instance_id": "i-1", "region_domain": "us-east.bob.example", "teams": []},
            {"instance_id": "i-2"},
        ],
    }
    pinned = json.loads(_pin_bob_profile_to_gateway(json.dumps(profile).encode()))
    assert [i.get("region_domain") for i in pinned["instances"]] == [None, None]
    assert pinned["instances"][0]["instance_id"] == "i-1"
    assert _pin_bob_profile_to_gateway(b"not json") == b"not json"


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
        '{"type":"message","timestamp":"t","role":"assistant","content":"Let me"}',
        '{"type":"message","timestamp":"t","role":"assistant","content":" run it:"}',
        '{"type":"tool_use","timestamp":"t","tool_name":"execute_command","tool_id":"tooluse_1","parameters":{"command":"echo ok"}}',
        '{"type":"tool_result","timestamp":"t","tool_id":"tooluse_1","status":"success","output":"ok"}',
        '{"type":"message","timestamp":"t","role":"assistant","content":"o"}',
        '{"type":"message","timestamp":"t","role":"assistant","content":"k"}',
        '{"type":"result","timestamp":"t","status":"success","stats":{"tool_calls":1}}',
        "not json",
    ]
    steps = [
        step
        for line in lines
        for step in builder.normalize_event(NativeProcessEvent(sequence=0, channel="stdout", text=line, elapsed_seconds=0.0))
    ]
    # Bob streams assistant text one delta per frame: the deltas become one
    # step at the next tool call or at the closing result.
    assert [s.role for s in steps] == ["assistant", "assistant", "tool", "assistant"]
    assert steps[0].content == "Let me run it:"
    assert steps[1].tool_calls == [{"id": "tooluse_1", "name": "execute_command", "arguments": {"command": "echo ok"}}]
    assert steps[2].tool_results[0]["result"] == "ok" and steps[2].tool_results[0]["is_error"] is False
    assert steps[3].content == "ok"
