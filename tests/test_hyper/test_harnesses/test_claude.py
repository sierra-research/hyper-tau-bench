"""Contract tests for the native Claude Code harness configuration."""

import json
from pathlib import Path
from types import SimpleNamespace

from tau2.hyper.harnesses.claude import (
    CLAUDE_CODE_HARNESS_VERSION,
    ClaudeCodeSandboxBuilder,
)
from tau2.hyper.live_experiment import LiveExperimentContext, SampleScenariosContext
from tau2.hyper.sandbox.builder import SandboxBuilder
from tau2.hyper.sandbox.native_runtime import NativeProcessEvent


def test_claude_builder_identity_is_harness_plus_model():
    builder = ClaudeCodeSandboxBuilder(
        "claude-opus-4-6",
        llm_args={"reasoning_effort": "high"},
        docker_image="runtime@sha256:abc",
    )

    assert isinstance(builder, SandboxBuilder)
    assert builder.harness_identity().to_dict() == {
        "name": "claude-code",
        "version": CLAUDE_CODE_HARNESS_VERSION,
        "config": {
            "interface": "print-stream-json",
            "permission_mode": "dontAsk-with-explicit-allowlist",
            "bare_mode": True,
            "web_tools": "removed",
            "browser": False,
            "background_tasks": False,
            "built_in_agents": False,
            "memory": False,
            "session_persistence": False,
            "nonessential_traffic": False,
            "model_gateway": "provider-only/per-run/model-scoped",
            "gateway_token_inherited_by_shell": True,
            "inner_bash_sandbox": "disabled/container-is-boundary",
            "mcp_servers": ["hyper_tau"],
        },
    }
    assert builder.model_identity().to_dict() == {
        "model": "claude-opus-4-6",
        "reasoning_effort": "high",
    }


def test_claude_command_removes_web_and_uses_only_private_mcp():
    builder = ClaudeCodeSandboxBuilder(
        "claude-opus-4-6", llm_args={"reasoning_effort": "medium"}
    )

    command = builder.harness_command()
    files = builder.runtime_files(include_client_tool=False)
    settings = json.loads(files[builder.runtime_config_path])
    mcp = json.loads(files[builder.mcp_config_path])

    assert command[:2] == ["claude", "--print"]
    assert "--bare" in command
    assert command[command.index("--effort") + 1] == "medium"
    assert command[command.index("--permission-mode") + 1] == "dontAsk"
    assert (
        command[command.index("--allowedTools") + 1]
        == command[command.index("--tools") + 1]
    )
    assert command[command.index("--disallowedTools") + 1] == "WebSearch,WebFetch"
    assert "--strict-mcp-config" in command
    assert "--no-session-persistence" in command
    assert "--no-chrome" in command
    assert settings["includeGitInstructions"] is True
    assert settings["disableClaudeAiConnectors"] is True
    assert settings["permissions"]["defaultMode"] == "dontAsk"
    assert settings["permissions"]["deny"] == ["WebSearch", "WebFetch"]
    assert list(mcp["mcpServers"]) == ["hyper_tau"]
    assert "talk_to_client" not in command[command.index("--tools") + 1]


def test_claude_enables_one_shot_live_experiment():
    builder = ClaudeCodeSandboxBuilder("claude-opus-4-6")
    builder.set_live_experiment_context(LiveExperimentContext(lambda: "result"))

    command = builder.harness_command()
    files = builder.runtime_files(
        include_client_tool=False,
        include_live_experiment_tool=True,
    )
    settings = json.loads(files[builder.runtime_config_path])

    assert "mcp__hyper_tau__run_live_experiment" in settings["permissions"]["allow"]
    assert (
        "mcp__hyper_tau__run_live_experiment" in command[command.index("--tools") + 1]
    )


def test_claude_enables_sample_scenarios_tool():
    # Regression: runtime_files() must accept the full kwarg set the native
    # build loop passes (a missing include_sample_scenarios_tool crashed
    # every claude-code run once the caller started sending it).
    builder = ClaudeCodeSandboxBuilder("claude-opus-4-6")
    builder.set_sample_scenarios_context(SampleScenariosContext(lambda: "result"))

    command = builder.harness_command()
    files = builder.runtime_files(
        include_client_tool=False,
        include_live_experiment_tool=False,
        include_sample_scenarios_tool=True,
    )
    settings = json.loads(files[builder.runtime_config_path])
    mcp = json.loads(files[builder.mcp_config_path])

    assert "mcp__hyper_tau__run_sample_scenarios" in settings["permissions"]["allow"]
    assert (
        "mcp__hyper_tau__run_sample_scenarios" in command[command.index("--tools") + 1]
    )
    assert (
        mcp["mcpServers"]["hyper_tau"]["env"]["TAU2_SAMPLE_SCENARIOS_TOOL_ENABLED"]
        == "${TAU2_SAMPLE_SCENARIOS_TOOL_ENABLED}"
    )


def test_claude_disables_nested_bash_sandbox():
    builder = ClaudeCodeSandboxBuilder("claude-opus-4-6")
    broker = SimpleNamespace(
        token="callback-token",
        client_tool_enabled=False,
    )

    environment = builder.runtime_environment(broker)

    # The construction container is the isolation boundary, so Claude Code's
    # inner Bash sandbox (a nested bubblewrap user namespace the container's
    # default security context forbids) is disabled; otherwise every Bash call
    # fails preflight. Env scrubbing also requires bubblewrap and is disabled;
    # the per-run gateway token is model-scoped and unexfiltratable (no egress).
    assert environment["CLAUDE_CODE_SANDBOXED"] == "1"
    assert environment["IS_SANDBOX"] == "1"
    assert environment["CLAUDE_CODE_SUBPROCESS_ENV_SCRUB"] == "0"
    assert environment["MCP_TIMEOUT"] == "28800000"


def test_construction_image_installs_bash_sandbox_binaries():
    dockerfile = (
        Path(__file__).resolve().parents[3]
        / "docker"
        / "hyper-construction"
        / "Dockerfile"
    ).read_text()

    # bubblewrap + socat are the Linux Bash-sandbox binaries; socat's absence
    # was what surfaced the nested-sandbox failure ("socat not installed").
    assert "        bubblewrap \\\n" in dockerfile
    assert "        socat \\\n" in dockerfile


def test_claude_stream_normalizes_text_tool_calls_and_results():
    builder = ClaudeCodeSandboxBuilder("claude-opus-4-6")
    assistant = NativeProcessEvent(
        sequence=0,
        channel="stdout",
        elapsed_seconds=1.0,
        text=json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "Inspecting the kit."},
                        {
                            "type": "tool_use",
                            "id": "tool-1",
                            "name": "Read",
                            "input": {"file_path": "/workspace/README.md"},
                        },
                    ]
                },
            }
        ),
    )
    user = NativeProcessEvent(
        sequence=1,
        channel="stdout",
        elapsed_seconds=2.0,
        text=json.dumps(
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "tool-1",
                            "content": "kit contents",
                            "is_error": False,
                        }
                    ]
                },
            }
        ),
    )

    assistant_step = builder.normalize_event(assistant)[0]
    result_step = builder.normalize_event(user)[0]

    assert assistant_step.content == "Inspecting the kit."
    assert assistant_step.tool_calls == [
        {
            "id": "tool-1",
            "name": "Read",
            "arguments": {"file_path": "/workspace/README.md"},
        }
    ]
    assert result_step.tool_results == [
        {
            "id": "tool-1",
            "name": "tool_result",
            "result": "kit contents",
            "is_error": False,
        }
    ]
