"""Contract tests for the native Prime Agent harness configuration."""

import json
from types import SimpleNamespace

from tau2.hyper.harnesses.prime import (
    PRIME_AGENT_HARNESS_VERSION,
    PrimeAgentSandboxBuilder,
)
from tau2.hyper.sandbox.builder import SandboxBuilder
from tau2.hyper.sandbox.native_runtime import NativeProcessEvent


def test_prime_builder_identity_is_harness_plus_model():
    builder = PrimeAgentSandboxBuilder(
        "gpt-5.6-sol",
        llm_args={"reasoning_effort": "xhigh"},
    )

    assert isinstance(builder, SandboxBuilder)
    identity = builder.harness_identity().to_dict()
    assert identity["name"] == "prime-agent"
    assert identity["version"] == PRIME_AGENT_HARNESS_VERSION
    assert identity["config"]["mcp_servers"] == ["hyper_tau"]
    assert builder.model_identity().to_dict() == {
        "model": "gpt-5.6-sol",
        "reasoning_effort": "xhigh",
    }


def test_prime_settings_wire_mcp_with_tagged_env_refs_only():
    builder = PrimeAgentSandboxBuilder(
        "gpt-5.6-sol", llm_args={"reasoning_effort": "high"}
    )

    settings = json.loads(builder.render_runtime_config(include_client_tool=True))

    assert settings["defaultProvider"] == "openai"
    assert settings["defaultModel"] == "gpt-5.6-sol"
    assert settings["defaultThinkingLevel"] == "high"
    assert settings["bundledSkills"] == {"websearch": False}
    server = settings["mcpServers"]["hyper_tau"]
    assert server["type"] == "stdio"
    assert server["args"] == ["-m", "tau2.hyper.sandbox.callback_mcp"]
    assert server["enabledTools"] == ["run_local_test", "talk_to_client", "submit"]
    # Env entries must be tagged references, never literal secrets.
    for value in server["env"].values():
        assert set(value) == {"env"}
    assert "TAU2_CALLBACK_TOKEN" in server["env"]
    # Prime whitelists only HOME/PATH/TMPDIR for stdio servers; without
    # PYTHONPATH the callback server dies on the tau2 import.
    assert server["env"]["PYTHONPATH"] == {"env": "PYTHONPATH"}


def test_prime_settings_without_client_tool_and_reasoning():
    builder = PrimeAgentSandboxBuilder("gpt-5.6-luna", llm_args={})
    settings = json.loads(builder.render_runtime_config(include_client_tool=False))
    server = settings["mcpServers"]["hyper_tau"]
    assert server["enabledTools"] == ["run_local_test", "submit"]
    assert "defaultThinkingLevel" not in settings


def test_prime_maps_none_reasoning_to_off():
    builder = PrimeAgentSandboxBuilder(
        "gpt-5.6-luna", llm_args={"reasoning_effort": "none"}
    )
    settings = json.loads(builder.render_runtime_config(include_client_tool=False))
    assert settings["defaultThinkingLevel"] == "off"


def test_prime_runtime_files_reroute_openai_provider_via_models_json():
    builder = PrimeAgentSandboxBuilder("gpt-5.6-sol")

    files = builder.runtime_files(include_client_tool=False)

    assert set(files) == {
        "/runtime-home/.prime/agent/settings.json",
        "/runtime-home/.prime/agent/models.json",
    }
    models = json.loads(files["/runtime-home/.prime/agent/models.json"])
    # Prime ignores OPENAI_BASE_URL; this override is the only reroute.
    assert models == {
        "providers": {"openai": {"baseUrl": "http://tau2-model-gateway:8143/openai/v1"}}
    }


def test_prime_gateway_env_targets_gateway_not_upstream():
    builder = PrimeAgentSandboxBuilder("gpt-5.6-sol")
    spec = SimpleNamespace(
        token="scoped-token",
        base_url="http://tau2-model-gateway:8143/openai",
    )

    env = builder.model_gateway_environment(spec)

    assert env["OPENAI_API_KEY"] == "scoped-token"
    assert env["OPENAI_BASE_URL"] == "http://tau2-model-gateway:8143/openai/v1"


def test_prime_command_runs_json_mode_via_prompt_driver():
    builder = PrimeAgentSandboxBuilder(
        "gpt-5.6-sol", llm_args={"reasoning_effort": "low"}
    )

    command = builder.harness_command()

    assert command[:3] == ["python", "-m", "tau2.hyper.harnesses.prompt_arg_driver"]
    assert command[3:6] == ["prime-agent", "--mode", "json"]
    assert "--offline" in command
    assert command[command.index("--provider") + 1] == "openai"
    assert command[command.index("--model") + 1] == "gpt-5.6-sol"
    assert command[command.index("--thinking") + 1] == "low"
    # The driver appends the prompt after the message separator.
    assert command[-1] == "--"


def _stdout_event(payload: dict) -> NativeProcessEvent:
    return NativeProcessEvent(
        sequence=1, channel="stdout", text=json.dumps(payload), elapsed_seconds=1.0
    )


def test_prime_stream_records_messages_with_thinking_blocks():
    builder = PrimeAgentSandboxBuilder("gpt-5.6-sol")

    message_end = _stdout_event(
        {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "Inspect the kit first."},
                    {"type": "text", "text": "Kit reviewed."},
                    {"type": "toolCall", "id": "call_1", "name": "ipython"},
                ],
            },
        }
    )

    steps = builder.normalize_event(message_end)
    assert len(steps) == 1
    assert steps[0].role == "assistant"
    assert steps[0].content == "Kit reviewed."
    assert steps[0].reasoning_summary == "Inspect the kit first."


def test_prime_stream_pairs_tool_end_with_args_from_tool_start():
    # Shapes captured from a real prime-agent 0.8.0 --mode json session:
    # args ride only on tool_execution_start; the end frame carries a
    # structured MCP-style result.
    builder = PrimeAgentSandboxBuilder("gpt-5.6-sol")

    assert (
        builder.normalize_event(
            _stdout_event(
                {
                    "type": "tool_execution_start",
                    "toolCallId": "call_9|fc_1",
                    "toolName": "ipython",
                    "args": {"code": "print(2+2)"},
                }
            )
        )
        == []
    )
    tool_steps = builder.normalize_event(
        _stdout_event(
            {
                "type": "tool_execution_end",
                "toolCallId": "call_9|fc_1",
                "toolName": "ipython",
                "result": {
                    "content": [{"type": "text", "text": "4\n"}],
                    "details": {"status": "ok"},
                    "isError": False,
                },
                "isError": False,
            }
        )
    )

    assert len(tool_steps) == 1
    assert tool_steps[0].tool_calls[0]["name"] == "ipython"
    assert tool_steps[0].tool_calls[0]["arguments"] == {"code": "print(2+2)"}
    assert tool_steps[0].tool_results[0]["result"] == "4\n"
    assert tool_steps[0].tool_results[0]["is_error"] is False


def test_prime_stream_ignores_noise_and_session_header():
    builder = PrimeAgentSandboxBuilder("gpt-5.6-sol")

    assert (
        builder.normalize_event(
            NativeProcessEvent(
                sequence=1, channel="stderr", text="{}", elapsed_seconds=0.1
            )
        )
        == []
    )
    assert (
        builder.normalize_event(
            NativeProcessEvent(
                sequence=1, channel="stdout", text="oops", elapsed_seconds=0.1
            )
        )
        == []
    )
    assert (
        builder.normalize_event(
            _stdout_event({"type": "session", "version": 3, "id": "uuid"})
        )
        == []
    )
    assert builder.normalize_event(_stdout_event({"type": "turn_start"})) == []
