"""Contract tests for the native OpenCode harness configuration."""

import json

from tau2.hyper.harnesses.opencode import (
    OPENCODE_HARNESS_VERSION,
    OpenCodeSandboxBuilder,
)
from tau2.hyper.sandbox.builder import SandboxBuilder
from tau2.hyper.sandbox.native_runtime import NativeProcessEvent


def test_opencode_builder_identity_is_harness_plus_model():
    builder = OpenCodeSandboxBuilder(
        "gpt-5.6-sol",
        llm_args={"reasoning_effort": "xhigh"},
    )

    assert isinstance(builder, SandboxBuilder)
    identity = builder.harness_identity().to_dict()
    assert identity["name"] == "opencode"
    assert identity["version"] == OPENCODE_HARNESS_VERSION
    assert identity["config"]["mcp_servers"] == ["hyper_tau"]
    assert identity["config"]["share"] == "disabled"
    assert builder.model_identity().to_dict() == {
        "model": "gpt-5.6-sol",
        "reasoning_effort": "xhigh",
    }


def test_opencode_config_targets_gateway_without_literal_secrets():
    builder = OpenCodeSandboxBuilder(
        "gpt-5.6-sol", llm_args={"reasoning_effort": "high"}
    )

    config = json.loads(builder.render_runtime_config(include_client_tool=False))
    provider = config["provider"]["tau2_gateway"]

    assert provider["options"]["baseURL"] == (
        "http://tau2-model-gateway:8143/openai/v1"
    )
    # The credential must be an env interpolation, never a literal token.
    assert provider["options"]["apiKey"] == "{env:TAU2_MODEL_GATEWAY_TOKEN}"
    assert config["model"] == "tau2_gateway/gpt-5.6-sol"
    assert provider["models"]["gpt-5.6-sol"]["options"] == {"reasoningEffort": "high"}
    assert config["share"] == "disabled"
    assert config["autoupdate"] is False
    assert config["permission"]["webfetch"] == "deny"
    assert config["tools"]["webfetch"] is False
    mcp = config["mcp"]["hyper_tau"]
    assert mcp["type"] == "local"
    assert mcp["command"][1:] == ["-m", "tau2.hyper.sandbox.callback_mcp"]


def test_opencode_config_omits_reasoning_when_none():
    builder = OpenCodeSandboxBuilder("gpt-5.6-luna", llm_args={})
    config = json.loads(builder.render_runtime_config(include_client_tool=True))
    model_entry = config["provider"]["tau2_gateway"]["models"]["gpt-5.6-luna"]
    assert "options" not in model_entry


def test_opencode_command_runs_headless_json_via_turn_loop_driver():
    builder = OpenCodeSandboxBuilder("gpt-5.6-sol")

    command = builder.harness_command()

    assert command[:3] == ["python", "-m", "tau2.hyper.harnesses.turn_loop_driver"]
    assert command[3:5] == ["opencode", "run"]
    assert "--format" in command and "json" in command
    assert command[-1] == "tau2_gateway/gpt-5.6-sol"


def _stdout_event(payload: dict) -> NativeProcessEvent:
    return NativeProcessEvent(
        sequence=1, channel="stdout", text=json.dumps(payload), elapsed_seconds=1.0
    )


def test_opencode_run_json_records_completed_text_and_tool_parts():
    # Envelope shapes captured from a real `opencode run --format json`
    # session against the pinned 1.18.23 binary: one JSON object per line,
    # the message part nested under "part".
    builder = OpenCodeSandboxBuilder("gpt-5.6-sol")

    finished_text = _stdout_event(
        {
            "type": "text",
            "sessionID": "ses_1",
            "part": {
                "type": "text",
                "text": "DONE",
                "time": {"start": 1, "end": 2},
            },
        }
    )
    streaming_text = _stdout_event(
        {
            "type": "text",
            "part": {"type": "text", "text": "DO", "time": {"start": 1}},
        }
    )
    completed_tool = _stdout_event(
        {
            "type": "tool_use",
            "part": {
                "type": "tool",
                "callID": "call_1",
                "tool": "bash",
                "state": {
                    "status": "completed",
                    "input": {"command": "echo hello-world"},
                    "output": "hello-world\n",
                    "title": "echo hello-world",
                },
            },
        }
    )
    running_tool = _stdout_event(
        {
            "type": "tool_use",
            "part": {"type": "tool", "state": {"status": "running"}},
        }
    )
    step_finish = _stdout_event(
        {
            "type": "step_finish",
            "part": {"type": "step-finish", "reason": "tool-calls"},
        }
    )

    text_steps = builder.normalize_event(finished_text)
    assert len(text_steps) == 1
    assert text_steps[0].role == "assistant"
    assert text_steps[0].content == "DONE"

    assert builder.normalize_event(streaming_text) == []
    assert builder.normalize_event(running_tool) == []
    assert builder.normalize_event(step_finish) == []

    tool_steps = builder.normalize_event(completed_tool)
    assert len(tool_steps) == 1
    assert tool_steps[0].tool_calls[0]["name"] == "bash"
    assert tool_steps[0].tool_calls[0]["arguments"] == {"command": "echo hello-world"}
    assert tool_steps[0].tool_results[0]["result"] == "hello-world\n"


def test_opencode_bus_envelope_still_accepted():
    builder = OpenCodeSandboxBuilder("gpt-5.6-sol")

    bus_text = _stdout_event(
        {
            "type": "message.part.updated",
            "properties": {
                "part": {
                    "type": "text",
                    "text": "Reading the kit README.",
                    "time": {"start": 1, "end": 2},
                }
            },
        }
    )

    steps = builder.normalize_event(bus_text)
    assert len(steps) == 1
    assert steps[0].content == "Reading the kit README."


def test_opencode_stream_ignores_noise():
    builder = OpenCodeSandboxBuilder("gpt-5.6-sol")

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
                sequence=1, channel="stdout", text="not json", elapsed_seconds=0.1
            )
        )
        == []
    )
    assert builder.normalize_event(_stdout_event({"type": "session.idle"})) == []


def test_opencode_runs_under_the_turn_loop_driver():
    # opencode's `run` is single-turn: without the loop driver, a model
    # that ends its turn early exits the harness with no submission.
    builder = OpenCodeSandboxBuilder("gpt-5.6-sol")
    command = builder.harness_command()
    assert command[:3] == ["python", "-m", "tau2.hyper.harnesses.turn_loop_driver"]
    assert command[3:5] == ["opencode", "run"]


def test_opencode_routes_openrouter_models_to_openrouter_gateway():
    builder = OpenCodeSandboxBuilder("openrouter/moonshotai/kimi-k3")

    assert builder.model_gateway_provider == "openrouter"
    assert builder.gateway_model == "moonshotai/kimi-k3"

    config = json.loads(builder.render_runtime_config(include_client_tool=False))
    provider = config["provider"]["tau2_gateway"]
    assert config["model"] == "tau2_gateway/moonshotai/kimi-k3"
    # chat-completions SDK: OpenRouter's Responses->chat translation loses
    # tool-call pairing, which strict open-model chat templates 400 on.
    assert provider["npm"] == "@ai-sdk/openai-compatible"
    assert provider["options"]["baseURL"] == (
        "http://tau2-model-gateway:8143/openrouter/v1"
    )
    assert list(provider["models"]) == ["moonshotai/kimi-k3"]
    # Text-only open-weight lane: image parts poison chat-completions
    # sessions, so attachments stay disabled for openrouter models.
    assert provider["models"]["moonshotai/kimi-k3"]["attachment"] is False

    command = builder.harness_command()
    assert command[command.index("--model") + 1] == "tau2_gateway/moonshotai/kimi-k3"


def test_opencode_keeps_openai_provider_for_plain_model_ids():
    builder = OpenCodeSandboxBuilder("gpt-5.6-sol")

    assert builder.model_gateway_provider == "openai"
    assert builder.gateway_model == "gpt-5.6-sol"
    config = json.loads(builder.render_runtime_config(include_client_tool=False))
    assert config["provider"]["tau2_gateway"]["options"]["baseURL"] == (
        "http://tau2-model-gateway:8143/openai/v1"
    )
