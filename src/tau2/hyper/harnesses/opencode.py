"""OpenCode integration for the Hyper-τ construction sandbox.

Config shape and event stream follow the OpenCode docs
(https://opencode.ai/docs/config/, ``opencode run --format json``) and were
verified end-to-end on 2026-08-25 against the pinned binary inside the
construction runtime: gateway-routed model calls, hyper_tau MCP callbacks,
and a scored airline_plus construction smoke run (2/2 eval tasks passed).
"""

from __future__ import annotations

import json

from tau2.hyper.sandbox.builder import BuildStep
from tau2.hyper.sandbox.native_builder import NativeSandboxBuilder
from tau2.hyper.sandbox.native_runtime import NativeProcessEvent

OPENCODE_HARNESS_VERSION = "1.18.23"

_GATEWAY_PROVIDER_ID = "tau2_gateway"
_GATEWAY_BASE_URL_TEMPLATE = "http://tau2-model-gateway:8143/{provider}/v1"
_OPENROUTER_PREFIX = "openrouter/"


class OpenCodeSandboxBuilder(NativeSandboxBuilder):
    """Run the pinned OpenCode CLI as a non-interactive JSON-event process."""

    harness_name = "opencode"
    harness_version = OPENCODE_HARNESS_VERSION

    @property
    def model_gateway_provider(self) -> str:  # type: ignore[override]
        """Route litellm-style ``openrouter/...`` model ids to OpenRouter."""
        return "openrouter" if self.llm.startswith(_OPENROUTER_PREFIX) else "openai"

    @property
    def gateway_model(self) -> str:
        """Model id as sent upstream (litellm routing prefix stripped)."""
        return self.llm.removeprefix(_OPENROUTER_PREFIX)

    # Discovered via XDG_CONFIG_HOME=/runtime-home/.config set by the runtime.
    runtime_config_path = "/runtime-home/.config/opencode/opencode.json"

    def harness_config_metadata(self) -> dict:
        return {
            "interface": "run-json-events",
            "permission_mode": "allow-edit-bash/deny-webfetch",
            "web_tools": "removed",
            "share": "disabled",
            "autoupdate": False,
            "session_persistence": False,
            "model_gateway": "provider-only/per-run/model-scoped",
            "gateway_token_inherited_by_shell": False,
            "mcp_servers": ["hyper_tau"],
        }

    def render_runtime_config(
        self,
        *,
        include_client_tool: bool,
        include_live_experiment_tool: bool = False,
        include_sample_scenarios_tool: bool = False,
    ) -> str:
        # The hyper_tau callback server gates talk_to_client,
        # run_live_experiment, and run_sample_scenarios itself from the
        # runtime environment, so the kit-facing tool surface stays correct
        # even without a per-tool allowlist in OpenCode's MCP config.
        del (
            include_client_tool,
            include_live_experiment_tool,
            include_sample_scenarios_tool,
        )
        model_entry: dict = {"name": self.gateway_model}
        if self.model_gateway_provider == "openrouter":
            # Open-weight text-only builders: never attach image bytes; a
            # single image part poisons the session for chat-completions
            # providers.
            model_entry["attachment"] = False
        reasoning_effort = self.llm_args.get("reasoning_effort")
        if reasoning_effort and reasoning_effort != "none":
            model_entry["options"] = {"reasoningEffort": str(reasoning_effort)}
        # OpenAI models speak the Responses API natively; open-weight models
        # behind OpenRouter use the chat-completions SDK instead, because
        # OpenRouter's Responses->chat translation loses tool-call pairing
        # (dropped tool_call_id fields, order-dependent name resolution) and
        # strict open-model chat templates 400 on the result.
        sdk_npm = (
            "@ai-sdk/openai-compatible"
            if self.model_gateway_provider == "openrouter"
            else "@ai-sdk/openai"
        )
        return json.dumps(
            {
                "model": f"{_GATEWAY_PROVIDER_ID}/{self.gateway_model}",
                "provider": {
                    _GATEWAY_PROVIDER_ID: {
                        "npm": sdk_npm,
                        "name": "Hyper-tau model gateway",
                        "options": {
                            "baseURL": _GATEWAY_BASE_URL_TEMPLATE.format(
                                provider=self.model_gateway_provider
                            ),
                            "apiKey": "{env:TAU2_MODEL_GATEWAY_TOKEN}",
                        },
                        "models": {self.gateway_model: model_entry},
                    }
                },
                "mcp": {
                    "hyper_tau": {
                        "type": "local",
                        "command": [
                            "/opt/tau2/.venv/bin/python",
                            "-m",
                            "tau2.hyper.sandbox.callback_mcp",
                        ],
                        "enabled": True,
                    }
                },
                "permission": {
                    "edit": "allow",
                    "bash": "allow",
                    "webfetch": "deny",
                },
                "tools": {"webfetch": False},
                "share": "disabled",
                "autoupdate": False,
            },
            indent=2,
            sort_keys=True,
        )

    def harness_command(self) -> list[str]:
        return [
            "python",
            "-m",
            "tau2.hyper.harnesses.turn_loop_driver",
            "opencode",
            "run",
            "--format",
            "json",
            "--model",
            f"{_GATEWAY_PROVIDER_ID}/{self.gateway_model}",
        ]

    def normalize_event(self, event: NativeProcessEvent) -> list[BuildStep]:
        if event.channel != "stdout":
            return []
        try:
            frame = json.loads(event.text)
        except json.JSONDecodeError:
            return []
        if not isinstance(frame, dict):
            return []
        part = self._event_part(frame)
        if part is None:
            return []
        part_type = part.get("type")
        if part_type == "text":
            # Text parts stream repeatedly; record only the finished part.
            time_info = part.get("time") or {}
            if not time_info.get("end"):
                return []
            text = part.get("text")
            if not text:
                return []
            return [BuildStep(step_idx=0, role="assistant", content=str(text))]
        if part_type == "reasoning":
            time_info = part.get("time") or {}
            if not time_info.get("end"):
                return []
            text = part.get("text")
            if not text:
                return []
            return [
                BuildStep(step_idx=0, role="assistant", reasoning_summary=str(text))
            ]
        if part_type == "tool":
            state = part.get("state") or {}
            if state.get("status") not in {"completed", "error"}:
                return []
            tool_name = part.get("tool") or state.get("title") or "tool"
            call_id = part.get("callID") or part.get("id") or ""
            result = state.get("output")
            if result is None:
                result = state.get("error") or ""
            return [
                BuildStep(
                    step_idx=0,
                    role="tool",
                    tool_calls=[
                        {
                            "id": call_id,
                            "name": tool_name,
                            "arguments": state.get("input") or {},
                        }
                    ],
                    tool_results=[
                        {
                            "id": call_id,
                            "name": tool_name,
                            "result": result,
                            "status": state.get("status"),
                        }
                    ],
                )
            ]
        return []

    @staticmethod
    def _event_part(frame: dict) -> dict | None:
        """Return the message part carried by one OpenCode event.

        `opencode run --format json` (verified against 1.18.23) emits one
        JSON object per line shaped `{"type": "text"|"tool_use"|"step_start"
        |"step_finish", "part": {...}}` where `part.type` is the
        `text`/`tool`/`step-*` message-part schema. The server event-bus
        envelope (`message.part.updated` with `properties.part`) is kept as
        a fallback.
        """
        part = frame.get("part")
        if isinstance(part, dict):
            return part
        if frame.get("type") == "message.part.updated":
            part = (frame.get("properties") or {}).get("part")
            return part if isinstance(part, dict) else None
        return None
