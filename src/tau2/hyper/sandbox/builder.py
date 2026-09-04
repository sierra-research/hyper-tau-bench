"""Shared protocol and result models for sandbox builders.

A builder takes a kit directory and a brief, modifies the kit to produce a
working agent, and returns a recorded :class:`BuildResult`. Native coding-agent
adapters implement the :class:`SandboxBuilder` protocol in sibling modules.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from tau2.hyper.client import ClientContext
from tau2.hyper.live_experiment import LiveExperimentContext, SampleScenariosContext

DEFAULT_BUILD_TIME_SECONDS = 8 * 60 * 60


# ---------------------------------------------------------------------------
# Budget model
# ---------------------------------------------------------------------------


@dataclass
class BuildBudget:
    """Budget constraints for a sandbox builder session.

    Attributes:
        max_steps: Optional build-step limit. Zero disables the step limit.
        max_time_seconds: Hard wall-clock limit. Legacy zero values resolve to
            the eight-hour benchmark default.
    """

    max_steps: int = 0
    max_time_seconds: int = DEFAULT_BUILD_TIME_SECONDS

    def __post_init__(self) -> None:
        if self.max_steps < 0:
            raise ValueError("max_steps cannot be negative")
        if self.max_time_seconds == 0:
            self.max_time_seconds = DEFAULT_BUILD_TIME_SECONDS
        if self.max_time_seconds < 0:
            raise ValueError("max_time_seconds must be positive")


@dataclass(frozen=True)
class HarnessIdentity:
    """Versioned coding harness plus the configuration that affects behavior."""

    name: str
    version: str
    config: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Return the stable result-record representation."""
        return {
            "name": self.name,
            "version": self.version,
            "config": dict(self.config),
        }


@dataclass(frozen=True)
class ModelIdentity:
    """Model identity separated from the harness that invokes it."""

    model: str
    reasoning_effort: Optional[str] = None
    config: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Return the stable result-record representation."""
        result = {"model": self.model}
        if self.reasoning_effort is not None:
            result["reasoning_effort"] = self.reasoning_effort
        if self.config:
            result["config"] = dict(self.config)
        return result


# ---------------------------------------------------------------------------
# Trajectory recording
# ---------------------------------------------------------------------------


@dataclass
class BuildStep:
    """One step in the builder's trajectory."""

    step_idx: int
    role: str  # "assistant" or "tool"
    content: Optional[str] = None
    reasoning_summary: Optional[str] = None
    tool_calls: Optional[list[dict]] = None
    tool_results: Optional[list[dict]] = None
    timestamp: float = 0.0


@dataclass
class BuildResult:
    """Result of a builder session."""

    kit_path: Path
    steps: list[BuildStep] = field(default_factory=list)
    total_steps: int = 0
    total_tool_calls: int = 0
    client_turns_used: int = 0
    submitted: bool = False
    done_reason: str = ""
    elapsed_seconds: float = 0.0
    builder_type: str = ""
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class SandboxBuilder(Protocol):
    """Protocol for sandbox builders.

    A builder receives a kit directory path and a brief (instructions),
    modifies the kit in-place, and returns a BuildResult.
    """

    def set_client_context(self, ctx: ClientContext) -> None:
        """Provide the Client simulator so ``talk_to_client`` works.

        Called by the orchestrator after the Client produces its opening
        brief and before :meth:`build` is invoked.
        """
        ...

    def set_live_experiment_context(self, ctx: LiveExperimentContext) -> None:
        """Provide the host-owned one-shot live experiment runner."""
        ...

    def set_sample_scenarios_context(self, ctx: SampleScenariosContext) -> None:
        """Provide the host-owned quota-limited sample-scenario runner."""
        ...

    def build(
        self,
        kit_path: Path,
        brief: str,
        budget: BuildBudget,
        display=None,
        cancel_event: Optional[threading.Event] = None,
    ) -> BuildResult:
        """Build an agent in the kit directory.

        Args:
            kit_path: Path to the developer kit directory.
            brief: Instructions/brief from the Client describing what
                needs to be built or fixed.
            budget: Budget constraints for this session.
            display: Optional display adapter for live visualization.
            cancel_event: Optional cooperative cancellation signal.

        Returns:
            BuildResult with trajectory and metadata.
        """
        ...
