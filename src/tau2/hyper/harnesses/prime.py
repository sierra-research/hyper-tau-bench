"""Prime Agent integration for the Hyper-τ construction sandbox.

Config shape and event stream follow the Prime Agent docs
(PrimeIntellect-ai/prime-agent, ``--mode json``, settings.json mcpServers)
and were verified on 2026-08-25 against the pinned binary inside the
construction runtime. Two behaviors found only by running it:

- Prime's model registry pins a per-model baseUrl and ignores
  ``OPENAI_BASE_URL``, so the gateway reroute must go through a
  provider-level override in ``~/.prime/agent/models.json``.
- Every tool (ipython, filesystem, shell, MCP) runs through a Python kernel
  that Prime bootstraps by downloading Python 3.11 + PyPI packages on first
  use. The construction network is internal-only, so the runtime image
  pre-provisions the kernel venv and ``PRIME_AGENT_KERNEL_PYTHON`` skips the
  bootstrap.
"""

from __future__ import annotations

import json
from typing import Any

from tau2.hyper.sandbox.builder import BuildStep
from tau2.hyper.sandbox.callback_broker import CallbackBroker
from tau2.hyper.sandbox.model_gateway import ModelGatewaySpec
from tau2.hyper.sandbox.native_builder import NativeSandboxBuilder
from tau2.hyper.sandbox.native_runtime import NativeProcessEvent

# Version of the @earendil-works/pi-coding-agent engine the pinned
# prime-agent release ships; recorded per run in the harness identity.
PRIME_AGENT_HARNESS_VERSION = "0.8.0"

# Prime's model registry pins a baseUrl per catalog model, so the standard
# OPENAI_BASE_URL environment override is ignored; the only supported reroute
# is a provider-level baseUrl override in ~/.prime/agent/models.json.
_GATEWAY_BASE_URL = "http://tau2-model-gateway:8143/openai/v1"

_CALLBACK_ENV_VARS = (
    "TAU2_CALLBACK_DIR",
    "TAU2_CALLBACK_TOKEN",
    "TAU2_CALLBACK_TIMEOUT_SECONDS",
    "TAU2_CLIENT_TOOL_ENABLED",
    "TAU2_LIVE_EXPERIMENT_TOOL_ENABLED",
    "TAU2_SAMPLE_SCENARIOS_TOOL_ENABLED",
)

# Prime thinking levels: off, low, medium, high, xhigh, max.
_THINKING_LEVELS = {"off", "low", "medium", "high", "xhigh", "max"}


def _text_content(value: Any) -> str:
    """Normalize string, block-list, or MCP-style result content to text."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # Tool results arrive as {"content": [blocks], "details": {...}}.
        if isinstance(value.get("content"), (list, str)):
            return _text_content(value["content"])
        return str(value.get("text") or value)
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("thinking") or item.get("content")
                parts.append(_text_content(text) if text else str(item))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    if value is None:
        return ""
    return str(value)


class PrimeAgentSandboxBuilder(NativeSandboxBuilder):
    """Run the pinned Prime Agent CLI as an autonomous JSON-event process."""

    harness_name = "prime-agent"
    harness_version = PRIME_AGENT_HARNESS_VERSION
    model_gateway_provider = "openai"
    runtime_config_path = "/runtime-home/.prime/agent/settings.json"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # tool_execution_end frames omit args; stash them from the paired
        # tool_execution_start, keyed by toolCallId.
        self._pending_tool_args: dict[str, Any] = {}

    def harness_config_metadata(self) -> dict:
        return {
            "interface": "mode-json",
            "web_tools": "removed",
            "bundled_skills": False,
            "session_persistence": "runtime-home-only",
            "model_gateway": "provider-only/per-run/model-scoped",
            "model_routing": "models.json provider baseUrl override",
            "gateway_token_inherited_by_shell": False,
            "mcp_servers": ["hyper_tau"],
        }

    def runtime_environment(self, broker: CallbackBroker) -> dict[str, str]:
        env = super().runtime_environment(broker)
        # Prime routes every tool (ipython, filesystem, shell, MCP) through a
        # Python kernel it bootstraps by downloading Python + PyPI packages on
        # first use — impossible on the internal sandbox network. The runtime
        # image pre-provisions the kernel venv; this documented override skips
        # the auto-bootstrap entirely.
        env["PRIME_AGENT_KERNEL_PYTHON"] = "/opt/prime-kernel/bin/python"
        return env

    def model_gateway_environment(self, spec: ModelGatewaySpec) -> dict[str, str]:
        # Auth comes from OPENAI_API_KEY (verified: Prime reports the key
        # source as "environment"). Routing does NOT come from
        # OPENAI_BASE_URL — Prime's registry pins per-model base URLs — so
        # models.json in runtime_files() carries the gateway reroute; the
        # variable stays set for any raw-SDK code path that does read it.
        return {
            "OPENAI_API_KEY": spec.token,
            "OPENAI_BASE_URL": f"{spec.base_url}/v1",
        }

    def render_runtime_config(
        self,
        *,
        include_client_tool: bool,
        include_live_experiment_tool: bool = False,
        include_sample_scenarios_tool: bool = False,
    ) -> str:
        enabled_tools = ["run_local_test", "submit"]
        if include_sample_scenarios_tool:
            enabled_tools.insert(1, "run_sample_scenarios")
        if include_live_experiment_tool:
            enabled_tools.insert(1, "run_live_experiment")
        if include_client_tool:
            enabled_tools.insert(1, "talk_to_client")
        settings: dict = {
            "defaultProvider": "openai",
            "defaultModel": self.llm,
            "enabledModels": [self.llm],
            "bundledSkills": {"websearch": False},
            "enableSkillCommands": False,
            "sessionDir": "/runtime-home/.prime/agent/sessions",
            "mcpServers": {
                "hyper_tau": {
                    "type": "stdio",
                    "command": "/opt/tau2/.venv/bin/python",
                    "args": ["-m", "tau2.hyper.sandbox.callback_mcp"],
                    # Prime spawns stdio servers with a minimal whitelist env
                    # (HOME/PATH/TMPDIR only), so PYTHONPATH must be declared
                    # explicitly or the tau2 import fails at startup. Tagged
                    # references keep literal values out of the config file.
                    "env": {
                        name: {"env": name}
                        for name in (*_CALLBACK_ENV_VARS, "PYTHONPATH")
                    },
                    "startupTimeoutMs": 30000,
                    "callTimeoutMs": 28800000,
                    "enabledTools": enabled_tools,
                }
            },
        }
        thinking_level = self._thinking_level()
        if thinking_level:
            settings["defaultThinkingLevel"] = thinking_level
        return json.dumps(settings, indent=2, sort_keys=True)

    def runtime_files(
        self,
        *,
        include_client_tool: bool,
        include_live_experiment_tool: bool = False,
        include_sample_scenarios_tool: bool = False,
    ) -> dict[str, str]:
        files = super().runtime_files(
            include_client_tool=include_client_tool,
            include_live_experiment_tool=include_live_experiment_tool,
            include_sample_scenarios_tool=include_sample_scenarios_tool,
        )
        # Reroute every built-in openai catalog model to the scoped gateway.
        files["/runtime-home/.prime/agent/models.json"] = json.dumps(
            {"providers": {"openai": {"baseUrl": _GATEWAY_BASE_URL}}},
            indent=2,
            sort_keys=True,
        )
        return files

    def _thinking_level(self) -> str | None:
        reasoning_effort = self.llm_args.get("reasoning_effort")
        if not reasoning_effort:
            return None
        level = str(reasoning_effort)
        if level == "none":
            return "off"
        return level if level in _THINKING_LEVELS else None

    def harness_command(self) -> list[str]:
        command = [
            "python",
            "-m",
            "tau2.hyper.harnesses.prompt_arg_driver",
            "prime-agent",
            "--mode",
            "json",
            # No startup network operations: the container has no internet
            # route beyond the scoped model gateway anyway.
            "--offline",
            "--provider",
            "openai",
            "--model",
            self.llm,
        ]
        thinking_level = self._thinking_level()
        if thinking_level:
            command.extend(["--thinking", thinking_level])
        # Everything the driver appends after `--` is the developer prompt.
        command.append("--")
        return command

    def normalize_event(self, event: NativeProcessEvent) -> list[BuildStep]:
        if event.channel != "stdout":
            return []
        try:
            frame = json.loads(event.text)
        except json.JSONDecodeError:
            return []
        if not isinstance(frame, dict):
            return []
        frame_type = frame.get("type")
        if frame_type == "message_end":
            return self._message_steps(frame)
        if frame_type == "tool_execution_start":
            call_id = frame.get("toolCallId")
            if call_id:
                self._pending_tool_args[call_id] = frame.get("args") or {}
            return []
        if frame_type == "tool_execution_end":
            return self._tool_steps(frame)
        return []

    @staticmethod
    def _message_steps(frame: dict) -> list[BuildStep]:
        message = frame.get("message") or {}
        if message.get("role") not in {None, "assistant"}:
            return []
        blocks = message.get("content")
        if isinstance(blocks, list):
            texts = [
                b for b in blocks if isinstance(b, dict) and b.get("type") == "text"
            ]
            thinks = [
                b for b in blocks if isinstance(b, dict) and b.get("type") == "thinking"
            ]
            content = "\n".join(_text_content(b.get("text")) for b in texts)
            reasoning = "\n".join(_text_content(b.get("thinking")) for b in thinks)
        else:
            content = _text_content(blocks)
            reasoning = ""
        if not content and not reasoning:
            return []
        return [
            BuildStep(
                step_idx=0,
                role="assistant",
                content=content or None,
                reasoning_summary=reasoning or None,
            )
        ]

    def _tool_steps(self, frame: dict) -> list[BuildStep]:
        tool_name = (
            frame.get("toolName") or frame.get("tool_name") or frame.get("tool") or ""
        )
        call_id = frame.get("toolCallId") or frame.get("id") or ""
        arguments = frame.get("args") or self._pending_tool_args.pop(call_id, {})
        result = frame.get("result")
        if result is None:
            result = frame.get("output", "")
        return [
            BuildStep(
                step_idx=0,
                role="tool",
                tool_calls=[{"id": call_id, "name": tool_name, "arguments": arguments}],
                tool_results=[
                    {
                        "id": call_id,
                        "name": tool_name,
                        "result": _text_content(result),
                        "is_error": bool(frame.get("isError", False)),
                    }
                ],
            )
        ]
