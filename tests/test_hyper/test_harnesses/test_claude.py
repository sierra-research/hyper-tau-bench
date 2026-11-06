"""Contract tests for the native Claude Code harness configuration."""

import json
from pathlib import Path
from types import SimpleNamespace

from tau2.hyper.harnesses.claude import (
    CLAUDE_CODE_HARNESS_VERSION,
    SKILLS_DIRECTIVE_PATH,
    ClaudeCodeSandboxBuilder,
    render_skills_directive,
    skill_name_of_call,
)
from tau2.hyper.sandbox.builder import BuildResult, BuildStep
from tau2.hyper.sandbox.orchestrator import _build_end_record
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
            "session_persistence": "runtime-home-only",
            "turn_loop": True,
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

    assert command[:3] == ["python", "-m", "tau2.hyper.harnesses.turn_loop_driver"]
    assert command[3:5] == ["claude", "--print"]
    assert "--bare" in command
    assert command[command.index("--effort") + 1] == "medium"
    assert command[command.index("--permission-mode") + 1] == "dontAsk"
    assert (
        command[command.index("--allowedTools") + 1]
        == command[command.index("--tools") + 1]
    )
    assert command[command.index("--disallowedTools") + 1] == "WebSearch,WebFetch"
    assert "--strict-mcp-config" in command
    # The turn loop's `--continue` needs the session kept (below the private runtime home).
    assert "--no-session-persistence" not in command
    assert "--input-format" not in command, "the driver hands the prompt as an argument"
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


def test_claude_skills_dir_rides_as_a_session_plugin(tmp_path):
    skills = tmp_path / "skills"
    (skills / "build-the-agent").mkdir(parents=True)
    (skills / "build-the-agent" / "SKILL.md").write_text("---\nname: build-the-agent\n---\nbody\n")
    (skills / "notes.txt").write_text("not a skill")

    builder = ClaudeCodeSandboxBuilder("claude-sonnet-4-5", skills_dir=skills)
    command = builder.harness_command()
    files = builder.runtime_files(include_client_tool=False)
    settings = json.loads(files[builder.runtime_config_path])

    assert builder.harness_identity().config["skills"] == ["build-the-agent"]
    assert builder.harness_identity().config["bare_mode"] is False
    assert builder.harness_identity().config["skills_directive"] == "claude-md"
    assert "--bare" not in command
    assert "--disable-slash-commands" not in command
    assert command[command.index("--plugin-dir") + 1] == "/runtime-home/plugins/strata-skills"
    assert "Skill" in command[command.index("--tools") + 1].split(",")
    assert "Skill" in settings["permissions"]["allow"]
    manifest = json.loads(files["/runtime-home/plugins/strata-skills/.claude-plugin/plugin.json"])
    assert manifest["name"] == "strata-skills"
    assert files["/runtime-home/plugins/strata-skills/skills/build-the-agent/SKILL.md"].endswith("body\n")
    # The CLAUDE.md Claude Code loads into every session's system prompt names the
    # skill and says to load it with the Skill tool first, then to keep going to submit.
    directive = files[SKILLS_DIRECTIVE_PATH]
    assert SKILLS_DIRECTIVE_PATH == "/runtime-home/.claude/CLAUDE.md"
    assert "`strata-skills:build-the-agent`" in directive
    assert "Skill tool" in directive
    assert "hyper_tau.submit" in directive
    # Every file stays below the private runtime home, never in the kit.
    assert all(path.startswith("/runtime-home/") for path in files)


def test_claude_without_skills_is_the_shipped_contract():
    builder = ClaudeCodeSandboxBuilder("claude-sonnet-4-5")
    command = builder.harness_command()

    assert "--disable-slash-commands" in command
    assert "--bare" in command
    assert "--plugin-dir" not in command
    assert "skills" not in builder.harness_identity().config
    assert "skills_directive" not in builder.harness_identity().config
    assert all(not path.endswith("CLAUDE.md") for path in builder.runtime_files(include_client_tool=False))
    assert builder.skills_read([]) is None, "no skills, nothing to read"
    assert "Skill" not in command[command.index("--tools") + 1].split(",")


def test_claude_empty_skills_dir_is_refused(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        ClaudeCodeSandboxBuilder("claude-sonnet-4-5", skills_dir=tmp_path)


def test_skills_directive_names_each_skill_with_its_description(tmp_path):
    skills = tmp_path / "skills"
    (skills / "policy-from-evidence").mkdir(parents=True)
    (skills / "policy-from-evidence" / "SKILL.md").write_text(
        "---\nname: policy-from-evidence\ndescription: \"Use when the policy is spread across evidence files.\"\n---\nbody\n"
    )
    (skills / "tau-agent-construction").mkdir()
    (skills / "tau-agent-construction" / "SKILL.md").write_text("---\nname: tau-agent-construction\n---\nno description\n")

    builder = ClaudeCodeSandboxBuilder("claude-sonnet-4-5", skills_dir=skills)
    assert [s["description"] for s in builder.skills] == [
        "Use when the policy is spread across evidence files.",
        "",
    ]
    directive = render_skills_directive(builder.skills)
    assert directive.startswith("# Skills for this build\n")
    assert "2 skills were handed to you" in directive
    assert (
        "- `strata-skills:policy-from-evidence` — Use when the policy is spread across evidence files."
        in directive
    )
    assert "- `strata-skills:tau-agent-construction`\n" in directive


def _stdout(elapsed: float, frame: dict) -> NativeProcessEvent:
    return NativeProcessEvent(sequence=0, channel="stdout", elapsed_seconds=elapsed, text=json.dumps(frame))


def test_claude_counts_turns_and_the_skills_the_developer_read(tmp_path):
    skills = tmp_path / "skills"
    for name in ("build-the-agent", "policy-from-evidence"):
        (skills / name).mkdir(parents=True)
        (skills / name / "SKILL.md").write_text(f"---\nname: {name}\n---\nbody\n")
    builder = ClaudeCodeSandboxBuilder("claude-sonnet-4-5", skills_dir=skills)
    builder.reset_build_state()

    steps = []
    assert builder.normalize_event(_stdout(0.5, {"type": "system", "subtype": "init", "session_id": "s1"})) == []
    steps += builder.normalize_event(
        _stdout(
            3.0,
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "id": "t1", "name": "Skill", "input": {"skill": "strata-skills:build-the-agent"}},
                    ]
                },
            },
        )
    )
    # A turn that ended with no submit: the loop continues it, and a second turn ends later.
    assert builder.normalize_event(_stdout(126.4, {"type": "result", "subtype": "success", "is_error": False, "num_turns": 28})) == []
    assert builder.normalize_event(_stdout(127.0, {"type": "system", "subtype": "init", "session_id": "s1"})) == []
    steps += builder.normalize_event(
        _stdout(
            300.0,
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "id": "t2", "name": "Skill", "input": {"skill": "strata-skills:build-the-agent"}},
                        {"type": "tool_use", "id": "t3", "name": "Read", "input": {"file_path": "/workspace/README.md"}},
                    ]
                },
            },
        )
    )
    builder.normalize_event(_stdout(900.0, {"type": "result", "subtype": "success", "is_error": False, "num_turns": 61, "result": "Submitted."}))
    # A third turn started and was killed by the host on submit: it has no end.
    assert builder.normalize_event(_stdout(901.0, {"type": "system", "subtype": "init", "session_id": "s1"})) == []

    assert builder.turns_started() == 3
    assert builder.build_turns() == [
        {"ended_at": 126.4, "subtype": "success", "is_error": False, "num_turns": 28},
        {"ended_at": 900.0, "subtype": "success", "is_error": False, "num_turns": 61},
    ]
    # Read once, named once; the other skill was never loaded.
    assert builder.skills_read(steps) == ["build-the-agent"]
    # The names a Skill call carries: with the plugin prefix, as a slash command, or bare.
    assert skill_name_of_call({"skill": "strata-skills:build-the-agent"}) == "build-the-agent"
    assert skill_name_of_call({"command": "/build-the-agent some args"}) == "build-the-agent"
    assert skill_name_of_call({"skill": "build-the-agent"}) == "build-the-agent"
    assert skill_name_of_call("not a dict") is None

    # What the orchestrator writes into the result file's build_result from the build's metadata.
    result = BuildResult(
        kit_path=tmp_path,
        steps=steps,
        metadata={
            "process": {"exit_code": 0, "timed_out": False, "cancelled": True, "event_count": 9, "stderr_tail": "x" * 5000},
            "turns": builder.build_turns(),
            "turns_started": builder.turns_started(),
            "skills_read": builder.skills_read(steps),
        },
    )
    record = _build_end_record(result)
    assert record["process"] == {"exit_code": 0, "timed_out": False, "cancelled": True, "stderr_tail": "x" * 1000}
    assert record["turns"] == 3, "the turns started: the third ended with the kill on submit"
    assert record["turn_ends"][0]["ended_at"] == 126.4
    assert record["skills_read"] == ["build-the-agent"]
    # A harness that records none of it leaves the keys out.
    assert _build_end_record(BuildResult(kit_path=tmp_path)) == {}
