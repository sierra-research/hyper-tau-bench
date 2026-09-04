"""Tests for the sandbox builder protocol and Client runtime context."""

from pathlib import Path

from tau2.hyper.client import ClientContext
from tau2.hyper.sandbox.builder import (
    DEFAULT_BUILD_TIME_SECONDS,
    BuildBudget,
    BuildResult,
    HarnessIdentity,
    ModelIdentity,
    SandboxBuilder,
)


class MinimalBuilder:
    """Minimal SandboxBuilder that satisfies the Protocol without LLM deps."""

    def __init__(self):
        self._client_ctx: ClientContext | None = None

    def set_client_context(self, ctx: ClientContext) -> None:
        self._client_ctx = ctx

    def set_live_experiment_context(self, ctx) -> None:
        self._live_experiment_ctx = ctx

    def set_sample_scenarios_context(self, ctx) -> None:
        self._sample_scenarios_ctx = ctx

    def build(
        self,
        kit_path: Path,
        brief: str,
        budget: BuildBudget,
        display=None,
    ) -> BuildResult:
        return BuildResult(
            kit_path=kit_path,
            done_reason="submitted",
            builder_type="test:minimal",
        )


class TestSandboxBuilderProtocol:
    """Verify non-LLM builders satisfy the Protocol and receive client context."""

    def test_minimal_builder_is_sandbox_builder(self):
        builder = MinimalBuilder()
        assert isinstance(builder, SandboxBuilder)

    def test_set_client_context_stores_context(self):
        builder = MinimalBuilder()
        ctx = ClientContext(client="fake_client", client_state={"foo": 1})
        builder.set_client_context(ctx)
        assert builder._client_ctx is ctx
        assert builder._client_ctx.client == "fake_client"

    def test_build_returns_build_result(self, tmp_path):
        builder = MinimalBuilder()
        result = builder.build(
            kit_path=tmp_path,
            brief="test brief",
            budget=BuildBudget(max_steps=5),
        )
        assert isinstance(result, BuildResult)
        assert result.done_reason == "submitted"

    def test_client_context_defaults(self):
        ctx = ClientContext(client=None, client_state=None)
        assert ctx.turns_used == 0

    def test_client_context_turn_tracking(self):
        ctx = ClientContext(client="c", client_state="s")
        ctx.turns_used += 1
        assert ctx.turns_used == 1


class TestBenchmarkIdentity:
    """The comparable result identity is harness plus model."""

    def test_harness_identity_includes_version_and_config(self):
        identity = HarnessIdentity(
            name="codex",
            version="1.2.3",
            config={"web_search": "disabled"},
        )

        assert identity.to_dict() == {
            "name": "codex",
            "version": "1.2.3",
            "config": {"web_search": "disabled"},
        }

    def test_model_identity_includes_reasoning_effort(self):
        identity = ModelIdentity(model="gpt-5.4", reasoning_effort="high")

        assert identity.to_dict() == {
            "model": "gpt-5.4",
            "reasoning_effort": "high",
        }

    def test_default_budget_is_eight_hours_and_not_step_limited(self):
        budget = BuildBudget()

        assert budget.max_time_seconds == DEFAULT_BUILD_TIME_SECONDS == 8 * 60 * 60
        assert budget.max_steps == 0

    def test_legacy_zero_time_uses_eight_hour_default(self):
        budget = BuildBudget(max_time_seconds=0, max_steps=1000)

        assert budget.max_time_seconds == DEFAULT_BUILD_TIME_SECONDS
        assert budget.max_steps == 1000

    def test_zero_step_limit_is_rendered_as_telemetry(self):
        from io import StringIO

        from rich.console import Console

        from tau2.hyper.visualizer import HyperTauDisplay

        output = StringIO()
        display = HyperTauDisplay(
            console=Console(file=output, force_terminal=False, width=120)
        )

        display.show_sandbox_step(
            step=1,
            max_steps=0,
            thinking=None,
            tool_calls=None,
            tool_results=None,
        )

        rendered = output.getvalue()
        assert "Step 1" in rendered
        assert "telemetry only" in rendered

    def test_negative_step_budget_is_invalid(self):
        import pytest

        with pytest.raises(ValueError, match="max_steps cannot be negative"):
            BuildBudget(max_steps=-1)


def test_web_sandbox_default_has_no_step_limit():
    from tau2.hyper.web.app import ConstructionRunRequest

    assert ConstructionRunRequest().sandbox_steps == 0
