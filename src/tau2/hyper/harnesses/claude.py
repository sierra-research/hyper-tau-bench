"""Claude Code integration for the Hyper-τ construction sandbox."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from tau2.hyper.sandbox.builder import BuildStep
from tau2.hyper.sandbox.model_gateway import ModelGatewaySpec
from tau2.hyper.sandbox.native_builder import NativeSandboxBuilder
from tau2.hyper.sandbox.native_runtime import NativeProcessEvent

CLAUDE_CODE_HARNESS_VERSION = "2.1.219"

# Skills a run hands the Developer ride as one plugin below the private runtime
# home (never the kit): ``--plugin-dir`` loads it for the session, and the
# harness's skills switch stays on for that run only.
SKILLS_PLUGIN_NAME = "strata-skills"
SKILLS_PLUGIN_PATH = f"/runtime-home/plugins/{SKILLS_PLUGIN_NAME}"
_SKILL_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def load_skills_dir(skills_dir: str | Path) -> list[dict[str, str]]:
    """Read ``<dir>/<name>/SKILL.md`` files: ``[{"name", "content"}]``, by name.

    The directory name is the skill's name (a kebab-case slug); a child with no
    SKILL.md is skipped. An empty directory is an error: a skills arm with no
    skills is a misconfiguration, not the baseline.
    """
    root = Path(skills_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Skills directory not found: {root}")
    skills: list[dict[str, str]] = []
    for child in sorted(root.iterdir()):
        skill_md = child / "SKILL.md"
        if not child.is_dir() or not skill_md.is_file():
            continue
        if not _SKILL_NAME_RE.match(child.name):
            raise ValueError(
                f"Skill directory name must be a kebab-case slug: {child.name}"
            )
        skills.append({"name": child.name, "content": skill_md.read_text()})
    if not skills:
        raise ValueError(f"No <name>/SKILL.md below the skills directory: {root}")
    return skills


def _text_content(value: Any) -> str:
    """Normalize Claude's string-or-block tool output for trajectory storage."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or item))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    if value is None:
        return ""
    return str(value)


def _enabled_tools(
    *,
    include_client_tool: bool,
    include_live_experiment_tool: bool = False,
    include_sample_scenarios_tool: bool = False,
    include_skill_tool: bool = False,
) -> list[str]:
    """Return the complete native tool allowlist for one task shape."""
    tools = [
        "Bash",
        "Edit",
        "Glob",
        "Grep",
        "NotebookEdit",
        "Read",
        "Write",
        "mcp__hyper_tau__run_local_test",
        "mcp__hyper_tau__submit",
    ]
    if include_live_experiment_tool:
        tools.append("mcp__hyper_tau__run_live_experiment")
    if include_sample_scenarios_tool:
        tools.append("mcp__hyper_tau__run_sample_scenarios")
    if include_client_tool:
        tools.append("mcp__hyper_tau__talk_to_client")
    if include_skill_tool:
        tools.append("Skill")
    return tools


class ClaudeCodeSandboxBuilder(NativeSandboxBuilder):
    """Run the pinned Claude Code CLI as an autonomous JSONL process."""

    harness_name = "claude-code"
    harness_version = CLAUDE_CODE_HARNESS_VERSION
    model_gateway_provider = "anthropic"
    runtime_config_path = "/runtime-home/.claude/settings.json"
    mcp_config_path = "/runtime-home/claude-mcp.json"

    def __init__(self, llm: str, *, skills_dir: str | Path | None = None, **kwargs):
        super().__init__(llm, **kwargs)
        self.skills = load_skills_dir(skills_dir) if skills_dir is not None else []

    def harness_config_metadata(self) -> dict:
        metadata = {
            "interface": "print-stream-json",
            "permission_mode": "dontAsk-with-explicit-allowlist",
            "bare_mode": not self.skills,
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
        }
        if self.skills:
            metadata["skills"] = [skill["name"] for skill in self.skills]
            metadata["skills_plugin"] = SKILLS_PLUGIN_NAME
        return metadata

    def runtime_environment(self, broker) -> dict[str, str]:
        environment = super().runtime_environment(broker)
        callback_timeout_ms = str(
            int(float(environment["TAU2_CALLBACK_TIMEOUT_SECONDS"]) * 1000)
        )
        environment.update(
            {
                "CLAUDE_CODE_DISABLE_ARTIFACT": "1",
                "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
                "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",
                "CLAUDE_CODE_DISABLE_BUNDLED_SKILLS": "1",
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
                "CLAUDE_CODE_DISABLE_OFFICIAL_MARKETPLACE_AUTOINSTALL": "1",
                "CLAUDE_CODE_DISABLE_WORKFLOWS": "1",
                "CLAUDE_CODE_SKIP_PROMPT_HISTORY": "1",
                # The construction container is itself the isolation boundary
                # (internal-only network, no egress except the model gateway
                # sidecar, cap-scoped). Claude Code's inner Bash sandbox nests
                # a bubblewrap user namespace, which the container's default
                # security context forbids ("No permissions to create new
                # namespace"), so every Bash call failed preflight ("socat not
                # installed" / bwrap). Tell Claude Code it is already sandboxed
                # so Bash runs directly, matching the Codex lane's
                # danger-full-access model. Env scrubbing also requires
                # bubblewrap, so it is disabled; the per-run gateway token it
                # would scrub is model-scoped and unexfiltratable (no egress).
                "CLAUDE_CODE_SANDBOXED": "1",
                "IS_SANDBOX": "1",
                "CLAUDE_CODE_SUBPROCESS_ENV_SCRUB": "0",
                "CLAUDE_AGENT_SDK_DISABLE_BUILTIN_AGENTS": "1",
                "DISABLE_LOGIN_COMMAND": "1",
                "DISABLE_LOGOUT_COMMAND": "1",
                "DISABLE_UPDATES": "1",
                "DISABLE_UPGRADE_COMMAND": "1",
                "MCP_TIMEOUT": callback_timeout_ms,
            }
        )
        thinking = self.llm_args.get("thinking")
        if isinstance(thinking, dict) and thinking.get("budget_tokens"):
            environment["MAX_THINKING_TOKENS"] = str(thinking["budget_tokens"])
        return environment

    def model_gateway_environment(self, spec: ModelGatewaySpec) -> dict[str, str]:
        return {
            "ANTHROPIC_AUTH_TOKEN": spec.token,
            "ANTHROPIC_BASE_URL": spec.base_url,
        }

    def render_runtime_config(
        self,
        *,
        include_client_tool: bool,
        include_live_experiment_tool: bool = False,
        include_sample_scenarios_tool: bool = False,
    ) -> str:
        enabled_tools = _enabled_tools(
            include_client_tool=include_client_tool,
            include_live_experiment_tool=include_live_experiment_tool,
            include_sample_scenarios_tool=include_sample_scenarios_tool,
            include_skill_tool=bool(self.skills),
        )
        return json.dumps(
            {
                "autoMemoryEnabled": False,
                "disableAllHooks": True,
                "disableArtifact": True,
                "disableBundledSkills": True,
                "disableClaudeAiConnectors": True,
                "disableRemoteControl": True,
                "disableWorkflows": True,
                "enableAllProjectMcpServers": False,
                "includeGitInstructions": True,
                "permissions": {
                    "allow": enabled_tools,
                    "defaultMode": "dontAsk",
                    "deny": ["WebSearch", "WebFetch"],
                },
            },
            indent=2,
            sort_keys=True,
        )

    def runtime_files(
        self,
        *,
        include_client_tool: bool,
        include_live_experiment_tool: bool = False,
        include_sample_scenarios_tool: bool = False,
    ) -> dict[str, str]:
        files = {
            self.runtime_config_path: self.render_runtime_config(
                include_client_tool=include_client_tool,
                include_live_experiment_tool=include_live_experiment_tool,
                include_sample_scenarios_tool=include_sample_scenarios_tool,
            ),
            self.mcp_config_path: json.dumps(
                {
                    "mcpServers": {
                        "hyper_tau": {
                            "type": "stdio",
                            "command": "python",
                            "args": ["-m", "tau2.hyper.sandbox.callback_mcp"],
                            "env": {
                                "TAU2_CALLBACK_DIR": "${TAU2_CALLBACK_DIR}",
                                "TAU2_CALLBACK_TOKEN": "${TAU2_CALLBACK_TOKEN}",
                                "TAU2_CALLBACK_TIMEOUT_SECONDS": (
                                    "${TAU2_CALLBACK_TIMEOUT_SECONDS}"
                                ),
                                "TAU2_CLIENT_TOOL_ENABLED": (
                                    "${TAU2_CLIENT_TOOL_ENABLED}"
                                ),
                                "TAU2_LIVE_EXPERIMENT_TOOL_ENABLED": (
                                    "${TAU2_LIVE_EXPERIMENT_TOOL_ENABLED}"
                                ),
                                "TAU2_SAMPLE_SCENARIOS_TOOL_ENABLED": (
                                    "${TAU2_SAMPLE_SCENARIOS_TOOL_ENABLED}"
                                ),
                            },
                        }
                    }
                },
                indent=2,
                sort_keys=True,
            ),
        }
        files.update(self.skills_plugin_files())
        return files

    def skills_plugin_files(self) -> dict[str, str]:
        """The plugin that carries the run's skills: a manifest and one SKILL.md each."""
        if not self.skills:
            return {}
        files = {
            f"{SKILLS_PLUGIN_PATH}/.claude-plugin/plugin.json": json.dumps(
                {
                    "name": SKILLS_PLUGIN_NAME,
                    "description": "Skills handed to the Developer for this run",
                    "version": "0.0.0",
                },
                indent=2,
                sort_keys=True,
            )
        }
        for skill in self.skills:
            files[f"{SKILLS_PLUGIN_PATH}/skills/{skill['name']}/SKILL.md"] = skill[
                "content"
            ]
        return files

    def harness_command(self) -> list[str]:
        enabled_tools = _enabled_tools(
            include_client_tool=self._client_ctx is not None,
            include_live_experiment_tool=self._live_experiment_ctx is not None,
            include_sample_scenarios_tool=self._sample_scenarios_ctx is not None,
            include_skill_tool=bool(self.skills),
        )
        enabled_tool_list = ",".join(enabled_tools)

        # Claude Code 2.1.219 loads no skill under --bare, from a --plugin-dir or
        # the home's skills directory alike (checked in the image: the model
        # reports NONE with it and both skills without it). A skills run drops
        # bare mode; the settings file still disables hooks, and the env keeps
        # memory, updates and nonessential traffic off.
        command = [
            "claude",
            "--print",
            *([] if self.skills else ["--bare"]),
            "--output-format",
            "stream-json",
            "--verbose",
            "--input-format",
            "text",
            "--model",
            self.llm,
        ]
        reasoning_effort = self.llm_args.get("reasoning_effort")
        if reasoning_effort and reasoning_effort != "none":
            command.extend(["--effort", str(reasoning_effort)])
        command.extend(
            [
                "--permission-mode",
                "dontAsk",
                "--tools",
                enabled_tool_list,
                "--allowedTools",
                enabled_tool_list,
                "--disallowedTools",
                "WebSearch,WebFetch",
                "--mcp-config",
                self.mcp_config_path,
                "--strict-mcp-config",
                "--settings",
                self.runtime_config_path,
                "--no-session-persistence",
                "--no-chrome",
            ]
        )
        if self.skills:
            command.extend(["--plugin-dir", SKILLS_PLUGIN_PATH])
        else:
            command.append("--disable-slash-commands")
        return command

    def normalize_event(self, event: NativeProcessEvent) -> list[BuildStep]:
        if event.channel != "stdout":
            return []
        try:
            frame = json.loads(event.text)
        except json.JSONDecodeError:
            return []

        frame_type = frame.get("type")
        if frame_type == "assistant":
            return self._assistant_steps(frame)
        if frame_type == "user":
            return self._tool_result_steps(frame)
        if frame_type == "result":
            result_text = frame.get("result")
            if result_text:
                return [
                    BuildStep(
                        step_idx=0,
                        role="assistant",
                        content=_text_content(result_text),
                    )
                ]
        return []

    @staticmethod
    def _assistant_steps(frame: dict) -> list[BuildStep]:
        blocks = frame.get("message", {}).get("content", [])
        text_parts: list[str] = []
        calls: list[dict] = []
        for block in blocks if isinstance(blocks, list) else []:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")
            if block_type in {"text", "thinking"}:
                text = block.get("text") or block.get("thinking")
                if text:
                    text_parts.append(str(text))
            elif block_type == "tool_use":
                calls.append(
                    {
                        "id": block.get("id", ""),
                        "name": block.get("name", ""),
                        "arguments": block.get("input", {}),
                    }
                )
        if not text_parts and not calls:
            return []
        return [
            BuildStep(
                step_idx=0,
                role="assistant",
                content="\n".join(text_parts) or None,
                tool_calls=calls or None,
            )
        ]

    @staticmethod
    def _tool_result_steps(frame: dict) -> list[BuildStep]:
        blocks = frame.get("message", {}).get("content", [])
        results: list[dict] = []
        for block in blocks if isinstance(blocks, list) else []:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            results.append(
                {
                    "id": block.get("tool_use_id", ""),
                    "name": "tool_result",
                    "result": _text_content(block.get("content")),
                    "is_error": bool(block.get("is_error", False)),
                }
            )
        if not results:
            return []
        return [BuildStep(step_idx=0, role="tool", tool_results=results)]
