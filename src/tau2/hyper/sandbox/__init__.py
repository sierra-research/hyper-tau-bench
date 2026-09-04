"""
Sandbox mode for Hyper-τ.

This module provides a sandboxed filesystem workspace where a coding
agent (or LLM with file/shell tools) can build and iterate on a τ-bench
agent using standard development workflows: reading files, writing code,
running tests, analyzing traces, and editing policy.

The sandbox is a "developer kit" directory containing domain artifacts
(policy, API spec, dev DB, sample tasks, agent stub) but *never* eval
artifacts — structural anti-cheating by omission.

Key components:

- :mod:`~tau2.hyper.sandbox.kit` — Kit directory builder and format.
- :mod:`~tau2.hyper.sandbox.local_test` — Host-side execution of
  Developer-authored local simulation scenarios.
- :mod:`~tau2.hyper.sandbox.builder` — Shared builder protocol and result
  models used by the coding-agent adapters in :mod:`tau2.hyper.harnesses`.
- :mod:`~tau2.hyper.sandbox.orchestrator` — SandboxOrchestrator managing
  the kit lifecycle, builder invocation, and scoring.
"""
