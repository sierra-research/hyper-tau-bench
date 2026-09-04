"""Shared SandboxBuilder lifecycle for native coding-agent harnesses."""

from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from loguru import logger

from tau2.hyper.client import ClientContext
from tau2.hyper.live_experiment import LiveExperimentContext, SampleScenariosContext
from tau2.hyper.runtime_contract import (
    DEFAULT_CONSTRUCTION_RUNTIME_IMAGE,
    runtime_contract_version_for_image,
)
from tau2.hyper.sandbox.builder import (
    BuildBudget,
    BuildResult,
    BuildStep,
    HarnessIdentity,
    ModelIdentity,
)
from tau2.hyper.sandbox.callback_broker import CallbackBroker
from tau2.hyper.sandbox.model_gateway import ModelGatewaySpec
from tau2.hyper.sandbox.native_runtime import (
    NativeMount,
    NativeProcessEvent,
    NativeRuntimeConfig,
    NativeSandboxRuntime,
    terminal_reason,
)
from tau2.hyper.web.run_stream import TrajectoryStreamer


class _AnyEvent:
    """Event-like view that is set when any source event is set."""

    def __init__(self, *events: threading.Event):
        self.events = events

    def is_set(self) -> bool:
        return any(event.is_set() for event in self.events)


class NativeSandboxBuilder(ABC):
    """Common outer lifecycle while each harness retains its native loop."""

    harness_name: str
    harness_version: str
    model_gateway_provider: str
    runtime_config_path: str

    def __init__(
        self,
        llm: str,
        *,
        llm_args: Optional[dict] = None,
        docker_image: Optional[str] = None,
        docker_memory: Optional[str] = None,
        docker_cpus: Optional[str] = None,
    ):
        self.llm = llm
        self.llm_args = dict(llm_args or {})
        self.docker_image = docker_image
        self.docker_memory = docker_memory
        self.docker_cpus = docker_cpus
        self.response_phrasing_pack = None
        # Harness-supplied candidate-runtime wiring for run_local_test
        # callbacks, including any Client API defect profile; deliberately
        # never written into the kit.
        self.local_test_wiring = None
        self._client_ctx: Optional[ClientContext] = None
        self._live_experiment_ctx: Optional[LiveExperimentContext] = None
        self._sample_scenarios_ctx: Optional[SampleScenariosContext] = None

    @property
    def gateway_model(self) -> str:
        """Model id scoped at the gateway and sent upstream (default: as given)."""
        return self.llm

    def set_client_context(self, ctx: ClientContext) -> None:
        """Provide the host-side Client simulator to the callback broker."""
        self._client_ctx = ctx

    def set_live_experiment_context(self, ctx: LiveExperimentContext) -> None:
        """Provide the host-owned live experiment to the callback broker."""
        self._live_experiment_ctx = ctx

    def set_sample_scenarios_context(self, ctx: SampleScenariosContext) -> None:
        """Provide the host-owned sample-scenario runner to the callback broker."""
        self._sample_scenarios_ctx = ctx

    def model_identity(self) -> ModelIdentity:
        """Identify model and reasoning separately from the coding harness."""
        model_config = dict(self.llm_args)
        reasoning_effort = model_config.pop("reasoning_effort", None)
        return ModelIdentity(
            model=self.llm,
            reasoning_effort=reasoning_effort,
            config=model_config,
        )

    def harness_identity(self) -> HarnessIdentity:
        """Return exact native binary version and benchmark-relevant config."""
        return HarnessIdentity(
            name=self.harness_name,
            version=self.harness_version,
            config=self.harness_config_metadata(),
        )

    @abstractmethod
    def harness_config_metadata(self) -> dict:
        """Return non-secret configuration that affects harness behavior."""

    @abstractmethod
    def render_runtime_config(
        self,
        *,
        include_client_tool: bool,
        include_live_experiment_tool: bool = False,
        include_sample_scenarios_tool: bool = False,
    ) -> str:
        """Render the harness's private runtime configuration file."""

    def runtime_files(
        self,
        *,
        include_client_tool: bool,
        include_live_experiment_tool: bool = False,
        include_sample_scenarios_tool: bool = False,
    ) -> dict[str, str]:
        """Return private files written below the ephemeral runtime home."""
        return {
            self.runtime_config_path: self.render_runtime_config(
                include_client_tool=include_client_tool,
                include_live_experiment_tool=include_live_experiment_tool,
                include_sample_scenarios_tool=include_sample_scenarios_tool,
            )
        }

    @abstractmethod
    def harness_command(self) -> list[str]:
        """Command that drives one native coding-agent session."""

    @abstractmethod
    def normalize_event(self, event: NativeProcessEvent) -> list[BuildStep]:
        """Translate one native process event into benchmark trajectory steps."""

    def runtime_environment(self, broker: CallbackBroker) -> dict[str, str]:
        """Environment inherited by the harness and callback MCP server."""
        return {
            "TAU2_CALLBACK_DIR": "/run/tau2-callback",
            "TAU2_CALLBACK_TOKEN": broker.token,
            "TAU2_CALLBACK_TIMEOUT_SECONDS": "28800",
            "TAU2_CLIENT_TOOL_ENABLED": "1" if broker.client_tool_enabled else "0",
            "TAU2_LIVE_EXPERIMENT_TOOL_ENABLED": (
                "1" if getattr(broker, "live_experiment_tool_enabled", False) else "0"
            ),
            "TAU2_SAMPLE_SCENARIOS_TOOL_ENABLED": (
                "1" if getattr(broker, "sample_scenarios_tool_enabled", False) else "0"
            ),
        }

    def model_gateway_environment(self, spec: ModelGatewaySpec) -> dict[str, str]:
        """Environment injected only into the native harness process."""
        return {"TAU2_MODEL_GATEWAY_TOKEN": spec.token}

    @staticmethod
    def _developer_prompt(brief: str, budget: BuildBudget) -> str:
        step_budget = (
            f" You have at most {budget.max_steps} recorded build steps."
            if budget.max_steps > 0
            else ""
        )
        return (
            "Work autonomously as the Developer for this Hyper-tau benchmark. "
            "Read README.md and the developer-visible kit, then build the best "
            "working submission in this repository. Use your native file, edit, "
            "search, shell, and Git tools. The hyper_tau MCP server provides "
            "run_local_test and submit; it provides talk_to_client only when "
            "the task has a Client, run_live_experiment only when the task "
            "has a one-shot live traffic sample, and run_sample_scenarios only "
            "when the client supplied sample scenarios. General web search and arbitrary internet "
            "research are prohibited. "
            f"You have {budget.max_time_seconds} seconds of wall-clock time."
            f"{step_budget} Call hyper_tau.submit when finished.\n\n"
            f"{brief}"
        )

    def build(
        self,
        kit_path: Path,
        brief: str,
        budget: BuildBudget,
        display=None,
        cancel_event: Optional[threading.Event] = None,
    ) -> BuildResult:
        """Run one native harness inside the supervised construction runtime."""
        kit_path = Path(kit_path).resolve()
        if cancel_event is not None and cancel_event.is_set():
            return BuildResult(
                kit_path=kit_path,
                builder_type=self.harness_name,
                done_reason="cancelled",
            )

        started = time.monotonic()
        result = BuildResult(
            kit_path=kit_path,
            builder_type=self.harness_name,
            metadata={
                "harness": self.harness_identity().to_dict(),
                "model": self.model_identity().to_dict(),
                "budget": {
                    "max_time_seconds": budget.max_time_seconds,
                    "max_steps": budget.max_steps,
                },
            },
        )
        streamer = TrajectoryStreamer.start(
            kit_path,
            llm=self.llm,
            max_steps=budget.max_steps,
        )
        runtime: Optional[NativeSandboxRuntime] = None
        broker = CallbackBroker(
            kit_path,
            client_context=self._client_ctx,
            live_experiment_context=self._live_experiment_ctx,
            sample_scenarios_context=self._sample_scenarios_ctx,
            response_phrasing_pack=self.response_phrasing_pack,
            local_test_wiring=self.local_test_wiring,
        )
        step_limit_reached = threading.Event()

        def record_event(event: NativeProcessEvent) -> None:
            for build_step in self.normalize_event(event):
                if budget.max_steps > 0 and len(result.steps) >= budget.max_steps:
                    step_limit_reached.set()
                    break
                build_step.step_idx = len(result.steps) + 1
                build_step.timestamp = event.elapsed_seconds
                result.steps.append(build_step)
                result.total_tool_calls += len(build_step.tool_calls or [])
                if streamer:
                    streamer.step(build_step, budget.max_steps)
                if display and hasattr(display, "show_sandbox_step"):
                    display.show_sandbox_step(
                        step=build_step.step_idx,
                        max_steps=budget.max_steps,
                        thinking=build_step.content,
                        tool_calls=build_step.tool_calls,
                        tool_results=build_step.tool_results,
                    )
                if budget.max_steps > 0 and len(result.steps) >= budget.max_steps:
                    step_limit_reached.set()

        try:
            with broker:
                gateway_spec = ModelGatewaySpec.from_host_environment(
                    self.model_gateway_provider,
                    model=self.gateway_model,
                    lifetime_seconds=budget.max_time_seconds + 60,
                )
                runtime_image = self.docker_image or DEFAULT_CONSTRUCTION_RUNTIME_IMAGE
                runtime = NativeSandboxRuntime(
                    kit_path,
                    config=NativeRuntimeConfig(
                        image=runtime_image,
                        required_contract_version=runtime_contract_version_for_image(
                            runtime_image
                        ),
                        memory=self.docker_memory,
                        cpus=self.docker_cpus,
                        name_prefix=f"tau2-{self.harness_name}",
                    ),
                    env=self.runtime_environment(broker),
                    extra_mounts=(
                        NativeMount(broker.callback_dir, "/run/tau2-callback"),
                    ),
                )
                runtime.start()
                runtime.start_model_gateway(gateway_spec)
                for path, contents in self.runtime_files(
                    include_client_tool=broker.client_tool_enabled,
                    include_live_experiment_tool=(
                        getattr(broker, "live_experiment_tool_enabled", False)
                    ),
                    include_sample_scenarios_tool=(
                        getattr(broker, "sample_scenarios_tool_enabled", False)
                    ),
                ).items():
                    runtime.write_runtime_file(path, contents)
                result.metadata["sandbox"] = runtime.runtime_metadata()
                if display and hasattr(display, "show_sandbox_phase"):
                    display.show_sandbox_phase(
                        "builder_start",
                        f"{self.harness_name} + {self.llm}, "
                        f"{budget.max_time_seconds}s wall clock",
                    )

                remaining = max(
                    0.001,
                    budget.max_time_seconds - (time.monotonic() - started),
                )
                cancellation_events = [broker.submitted, step_limit_reached]
                if cancel_event is not None:
                    cancellation_events.append(cancel_event)
                process_result = runtime.run(
                    self.harness_command(),
                    timeout_seconds=remaining,
                    stdin_text=self._developer_prompt(brief, budget),
                    on_event=record_event,
                    cancel_event=_AnyEvent(*cancellation_events),
                    env=self.model_gateway_environment(gateway_spec),
                )
                explicitly_submitted = broker.submitted.is_set()
                if cancel_event is not None and cancel_event.is_set():
                    result.done_reason = "cancelled"
                else:
                    result.done_reason = terminal_reason(
                        process_result,
                        explicitly_submitted=explicitly_submitted,
                        step_limit_reached=step_limit_reached.is_set(),
                    )
                result.submitted = explicitly_submitted
                result.metadata["process"] = {
                    "exit_code": process_result.exit_code,
                    "timed_out": process_result.timed_out,
                    "cancelled": process_result.cancelled,
                    "event_count": len(process_result.events),
                    "stderr_tail": process_result.stderr[-4000:],
                }
                result.metadata["callback"] = broker.metadata()
                if result.done_reason == "harness_error":
                    # Surface the harness's own last words: normalize_event
                    # drops error frames, so without this the only record of
                    # a startup failure is an unexplained zero-step build.
                    error_frames = [
                        e.text[:800]
                        for e in process_result.events
                        if '"type":"error"' in e.text or '"error"' in e.text[:80]
                    ]
                    logger.error(
                        f"Native {self.harness_name} harness error: "
                        f"exit_code={process_result.exit_code} "
                        f"stderr_tail={process_result.stderr[-2000:]!r} "
                        f"error_frames={error_frames[-3:]} "
                        f"last_events="
                        f"{[e.text[:400] for e in process_result.events[-2:]]}"
                    )
        except Exception as exc:  # noqa: BLE001 - current workspace is scored
            if cancel_event is not None and cancel_event.is_set():
                result.done_reason = "cancelled"
            else:
                logger.exception(f"Native {self.harness_name} harness failed: {exc}")
                result.done_reason = "harness_error"
                result.metadata["harness_error"] = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            result.metadata["callback"] = broker.metadata()
        finally:
            if runtime is not None:
                runtime.close()

        result.total_steps = len(result.steps)
        result.client_turns_used = (
            self._client_ctx.turns_used if self._client_ctx is not None else 0
        )
        result.elapsed_seconds = time.monotonic() - started
        if streamer:
            streamer.finish(
                result.done_reason,
                total_steps=result.total_steps,
                total_tool_calls=result.total_tool_calls,
            )
        if display and hasattr(display, "show_sandbox_done"):
            display.show_sandbox_done(
                result.done_reason,
                result.total_steps,
                result.total_tool_calls,
            )
        return result
