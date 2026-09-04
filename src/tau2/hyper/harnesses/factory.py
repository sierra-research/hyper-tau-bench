"""Select a coding-agent harness without coupling the CLI to adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tau2.hyper.sandbox.builder import SandboxBuilder

DEFAULT_DEVELOPER_HARNESS = "codex"
DEVELOPER_HARNESSES = ("codex", "claude-code", "opencode", "prime-agent")


def create_developer_builder(
    developer_harness: str,
    developer_llm: str,
    developer_llm_args: dict | None,
    developer_reasoning_effort: str | None,
) -> SandboxBuilder:
    """Build the selected coding-agent integration for a construction run."""
    native_llm_args = dict(developer_llm_args or {})
    if developer_reasoning_effort and developer_reasoning_effort != "none":
        native_llm_args["reasoning_effort"] = developer_reasoning_effort

    if developer_harness == "codex":
        from tau2.hyper.harnesses.codex import CodexSandboxBuilder

        return CodexSandboxBuilder(llm=developer_llm, llm_args=developer_llm_args or {})
    if developer_harness == "claude-code":
        from tau2.hyper.harnesses.claude import ClaudeCodeSandboxBuilder

        return ClaudeCodeSandboxBuilder(llm=developer_llm, llm_args=native_llm_args)
    if developer_harness == "opencode":
        from tau2.hyper.harnesses.opencode import OpenCodeSandboxBuilder

        return OpenCodeSandboxBuilder(llm=developer_llm, llm_args=native_llm_args)
    if developer_harness == "prime-agent":
        from tau2.hyper.harnesses.prime import PrimeAgentSandboxBuilder

        return PrimeAgentSandboxBuilder(llm=developer_llm, llm_args=native_llm_args)
    raise NotImplementedError(
        f"The {developer_harness!r} harness is selected but its native "
        "runtime adapter is not installed"
    )
