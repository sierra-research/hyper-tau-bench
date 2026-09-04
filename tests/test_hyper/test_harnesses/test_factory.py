"""Construction runs select supported native coding harnesses."""

from tau2.hyper.harnesses.factory import (
    DEFAULT_DEVELOPER_HARNESS,
    create_developer_builder,
)


def test_codex_is_the_default_developer_harness():
    assert DEFAULT_DEVELOPER_HARNESS == "codex"


def test_codex_selection_builds_the_native_adapter():
    from tau2.hyper.harnesses.codex import CodexSandboxBuilder

    builder = create_developer_builder(
        "codex", "gpt-5.6-sol", {"reasoning_effort": "xhigh"}, "xhigh"
    )
    assert isinstance(builder, CodexSandboxBuilder)
    assert builder.llm == "gpt-5.6-sol"


def test_claude_code_selection_builds_the_native_adapter():
    from tau2.hyper.harnesses.claude import ClaudeCodeSandboxBuilder

    builder = create_developer_builder("claude-code", "claude-opus-4-6", {}, "high")
    assert isinstance(builder, ClaudeCodeSandboxBuilder)
    assert builder.llm_args.get("reasoning_effort") == "high"


def test_workbench_launch_seams_use_the_default_harness_factory():
    """The web app shares the CLI's default harness selection."""
    from pathlib import Path

    import tau2.hyper.web.app as app_module

    source = Path(app_module.__file__).read_text()
    assert "create_developer_builder" in source
    assert "DEFAULT_DEVELOPER_HARNESS" in source
