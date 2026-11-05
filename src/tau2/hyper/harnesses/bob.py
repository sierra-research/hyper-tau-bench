"""IBM Bob Shell integration for the Hyper-τ construction sandbox.

Bob Shell (``bob``, the ``bobshell`` package) runs one task headless with
``bob run --format stream-json``: one JSON object per line, of type
``message`` (a user or assistant text), ``tool_use`` (``tool_name``,
``tool_id``, ``parameters``), ``tool_result`` (``tool_id``, ``status``,
``output``) and a closing ``result`` (``status``, ``stats``). The prompt is a
positional argument, so the supervised runtime's stdin prompt reaches it
through ``prompt_arg_driver``.

Bob reaches its own model gateway (IBM's, behind an API key) rather than an
Anthropic or OpenAI endpoint: the run's sidecar speaks the ``bob`` wire
(``Authorization: apikey …``, ``/admin/v1/profile`` and ``/inference/v1/…``),
and ``BOB_GATEWAY_URL`` points the harness at it. The model is Bob's own
choice; ``--developer-llm`` names the run for the record.

The package is not on public npm: the construction image installs it from a
tarball dropped in ``docker/hyper-construction/vendor/`` (``npm pack`` of an
installed Bob Shell), and a run on an image without it fails at startup.
"""

from __future__ import annotations

import json
import os
from typing import Any

from tau2.hyper.sandbox.builder import BuildStep
from tau2.hyper.sandbox.model_gateway import ModelGatewaySpec
from tau2.hyper.sandbox.native_builder import NativeSandboxBuilder
from tau2.hyper.sandbox.native_runtime import NativeProcessEvent

BOB_SHELL_HARNESS_VERSION = "2.0.5"


class BobShellSandboxBuilder(NativeSandboxBuilder):
    """Run IBM Bob Shell headless as a JSON-lines process."""

    harness_name = "bob"
    harness_version = BOB_SHELL_HARNESS_VERSION
    model_gateway_provider = "bob"
    # Bob reads its global settings below $HOME/.bob/settings; HOME is the
    # private runtime home, so these never touch the kit.
    runtime_config_path = "/runtime-home/.bob/settings/settings.json"
    mcp_config_path = "/runtime-home/.bob/settings/mcp.json"

    def harness_config_metadata(self) -> dict:
        return {
            "interface": "run-stream-json",
            "permission_mode": "headless-auto-approve",
            "license": "accepted-by-flag",
            "subagents": False,
            "mcp_servers": ["hyper_tau"],
            "model_gateway": "provider-only/per-run/bob-wire",
            "model_choice": "bob's own",
            "team_id": bool(os.environ.get("BOB_TEAM_ID")),
        }

    def runtime_environment(self, broker) -> dict[str, str]:
        environment = super().runtime_environment(broker)
        environment.update(
            {
                "BOB_LOG_LEVEL": "warn",
                "BOB_TELEMETRY_PROVIDER": "none",
            }
        )
        return environment

    def model_gateway_environment(self, spec: ModelGatewaySpec) -> dict[str, str]:
        return {
            "BOB_API_KEY": spec.token,
            "BOB_GATEWAY_URL": spec.base_url,
        }

    def render_runtime_config(
        self,
        *,
        include_client_tool: bool,
        include_live_experiment_tool: bool = False,
        include_sample_scenarios_tool: bool = False,
    ) -> str:
        return json.dumps({"autoApprove": True}, indent=2, sort_keys=True)

    def runtime_files(
        self,
        *,
        include_client_tool: bool,
        include_live_experiment_tool: bool = False,
        include_sample_scenarios_tool: bool = False,
    ) -> dict[str, str]:
        # The callback MCP server reads TAU2_CALLBACK_* from the container's
        # environment, which every process Bob spawns inherits.
        return {
            self.runtime_config_path: self.render_runtime_config(
                include_client_tool=include_client_tool,
                include_live_experiment_tool=include_live_experiment_tool,
                include_sample_scenarios_tool=include_sample_scenarios_tool,
            ),
            self.mcp_config_path: json.dumps(
                {
                    "mcpServers": {
                        "hyper_tau": {
                            "command": "python",
                            "args": ["-m", "tau2.hyper.sandbox.callback_mcp"],
                        }
                    }
                },
                indent=2,
                sort_keys=True,
            ),
        }

    def harness_command(self) -> list[str]:
        command = [
            "python",
            "-m",
            "tau2.hyper.harnesses.prompt_arg_driver",
            "bob",
            "run",
            "--format",
            "stream-json",
            "--workspace",
            "/workspace",
            "--trust",
            "--accept-license",
            "--disable-subagents",
        ]
        team_id = os.environ.get("BOB_TEAM_ID")
        if team_id:
            command.extend(["--team-id", team_id])
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
        kind = frame.get("type")
        if kind == "message" and frame.get("role") == "assistant":
            content = _text(frame.get("content"))
            return [BuildStep(step_idx=0, role="assistant", content=content)] if content else []
        if kind == "tool_use":
            return [
                BuildStep(
                    step_idx=0,
                    role="assistant",
                    tool_calls=[
                        {
                            "id": str(frame.get("tool_id", "")),
                            "name": str(frame.get("tool_name", "")),
                            "arguments": frame.get("parameters") or {},
                        }
                    ],
                )
            ]
        if kind == "tool_result":
            return [
                BuildStep(
                    step_idx=0,
                    role="tool",
                    tool_results=[
                        {
                            "id": str(frame.get("tool_id", "")),
                            "name": "tool_result",
                            "result": _text(frame.get("output")),
                            "is_error": frame.get("status") not in (None, "success"),
                        }
                    ],
                )
            ]
        return []


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, default=str)
