"""Select a coding-agent harness without coupling the CLI to adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tau2.hyper.sandbox.builder import SandboxBuilder

DEFAULT_DEVELOPER_HARNESS = "codex"
DEVELOPER_HARNESSES = ("codex", "claude-code", "opencode", "prime-agent", "bob")


def create_developer_builder(
    developer_harness: str,
    developer_llm: str,
    developer_llm_args: dict | None,
    developer_reasoning_effort: str | None,
    developer_skills_dir: str | None = None,
    developer_artifacts_dir: str | None = None,
) -> SandboxBuilder:
    """Build the selected coding-agent integration for a construction run.

    ``developer_skills_dir`` names a directory of skills (one ``SKILL.md`` per
    child directory) the harness loads for the run; only Claude Code takes one.
    ``developer_artifacts_dir`` is where what the harness kept below its private
    runtime home is copied after the build (Bob's task store and its spans);
    a harness that keeps nothing copies nothing.
    """
    native_llm_args = dict(developer_llm_args or {})
    if developer_reasoning_effort and developer_reasoning_effort != "none":
        native_llm_args["reasoning_effort"] = developer_reasoning_effort
    keep = {"artifacts_dir": developer_artifacts_dir} if developer_artifacts_dir else {}

    if developer_harness == "codex":
        from tau2.hyper.harnesses.codex import CodexSandboxBuilder

        return CodexSandboxBuilder(llm=developer_llm, llm_args=developer_llm_args or {}, **keep)
    if developer_harness == "claude-code":
        from tau2.hyper.harnesses.claude import ClaudeCodeSandboxBuilder

        return ClaudeCodeSandboxBuilder(
            llm=developer_llm,
            llm_args=native_llm_args,
            skills_dir=developer_skills_dir,
            **keep,
        )
    if developer_skills_dir is not None:
        raise NotImplementedError(
            f"The {developer_harness!r} harness does not take a skills directory"
        )
    if developer_harness == "bob":
        from tau2.hyper.harnesses.bob import BobShellSandboxBuilder

        return BobShellSandboxBuilder(llm=developer_llm, llm_args=native_llm_args, **keep)
    if developer_harness == "opencode":
        from tau2.hyper.harnesses.opencode import OpenCodeSandboxBuilder

        return OpenCodeSandboxBuilder(llm=developer_llm, llm_args=native_llm_args, **keep)
    if developer_harness == "prime-agent":
        from tau2.hyper.harnesses.prime import PrimeAgentSandboxBuilder

        return PrimeAgentSandboxBuilder(llm=developer_llm, llm_args=native_llm_args, **keep)
    raise NotImplementedError(
        f"The {developer_harness!r} harness is selected but its native "
        "runtime adapter is not installed"
    )
