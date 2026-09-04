"""Contract tests for the native Codex harness configuration."""

import json
import threading
from io import StringIO
from types import SimpleNamespace

from tau2.hyper.harnesses.codex import (
    CODEX_HARNESS_VERSION,
    CodexSandboxBuilder,
)
from tau2.hyper.harnesses.codex_driver import (
    _thread_start_params,
    _wait_for_response,
    _wait_for_turn_completion,
)
from tau2.hyper.live_experiment import LiveExperimentContext
from tau2.hyper.sandbox import native_builder as native_builder_module
from tau2.hyper.sandbox.builder import SandboxBuilder
from tau2.hyper.sandbox.native_runtime import NativeProcessEvent, NativeProcessResult


def test_codex_builder_identity_is_harness_plus_model():
    builder = CodexSandboxBuilder(
        "gpt-5.4",
        llm_args={"reasoning_effort": "high"},
        docker_image="runtime@sha256:abc",
    )

    assert isinstance(builder, SandboxBuilder)
    assert builder.harness_identity().to_dict() == {
        "name": "codex",
        "version": CODEX_HARNESS_VERSION,
        "config": {
            "interface": "app-server-stdio",
            "approval_policy": "never",
            "inner_sandbox": "danger-full-access",
            "web_search": "disabled",
            "apps": False,
            "multi_agent": False,
            "memory": False,
            "history_persistence": "none",
            "model_gateway": "provider-only/per-run/model-scoped",
            "gateway_token_inherited_by_shell": False,
            "mcp_servers": ["hyper_tau"],
        },
    }
    assert builder.model_identity().to_dict() == {
        "model": "gpt-5.4",
        "reasoning_effort": "high",
    }


def test_codex_builder_honors_preexisting_cancellation(tmp_path):
    cancel_event = threading.Event()
    cancel_event.set()

    result = CodexSandboxBuilder("gpt-5.4").build(
        tmp_path,
        "brief",
        native_builder_module.BuildBudget(max_steps=10),
        cancel_event=cancel_event,
    )

    assert result.done_reason == "cancelled"
    assert result.total_steps == 0


def test_codex_config_disables_non_benchmark_capabilities():
    builder = CodexSandboxBuilder("gpt-5.4", llm_args={"reasoning_effort": "medium"})

    config = builder.render_runtime_config(include_client_tool=False)

    assert 'web_search = "disabled"' in config
    assert 'approval_policy = "never"' in config
    assert 'sandbox_mode = "danger-full-access"' in config
    assert 'model_provider = "tau2_gateway"' in config
    assert 'base_url = "http://tau2-model-gateway:8143/openai/v1"' in config
    assert 'env_key = "TAU2_MODEL_GATEWAY_TOKEN"' in config
    assert 'wire_api = "responses"' in config
    assert "ignore_default_excludes = false" in config
    assert 'exclude = ["TAU2_MODEL_GATEWAY_TOKEN"]' in config
    assert "allow_login_shell = false" in config
    assert "apps = false" in config
    assert "multi_agent = false" in config
    assert 'persistence = "none"' in config
    assert "required = true" in config
    assert 'enabled_tools = ["run_local_test", "submit"]' in config
    assert 'command = "/opt/tau2/.venv/bin/python"' in config
    assert '"PATH", "PYTHONPATH", "TAU2_DATA_DIR"' in config
    assert "talk_to_client" not in config
    assert "run_live_experiment" not in config
    assert "[agents]" not in config


def test_codex_config_enables_one_shot_live_experiment():
    builder = CodexSandboxBuilder("gpt-5.4")
    builder.set_live_experiment_context(LiveExperimentContext(lambda: "result"))

    config = builder.render_runtime_config(
        include_client_tool=False,
        include_live_experiment_tool=True,
    )

    assert (
        'enabled_tools = ["run_local_test", "run_live_experiment", "submit"]' in config
    )
    assert '"TAU2_LIVE_EXPERIMENT_TOOL_ENABLED"' in config


def test_codex_thread_start_uses_protocol_sandbox_mode():
    assert _thread_start_params("gpt-5.4")["sandbox"] == "danger-full-access"


def test_codex_preserves_turn_completion_seen_before_start_response():
    process = SimpleNamespace(
        stdout=StringIO(
            "\n".join(
                [
                    json.dumps(
                        {
                            "method": "turn/completed",
                            "params": {"turn": {"status": "completed"}},
                        }
                    ),
                    json.dumps({"id": 2, "result": {"turn": {"id": "turn-1"}}}),
                ]
            )
            + "\n"
        )
    )
    pending_messages = []

    result = _wait_for_response(process, 2, pending_messages=pending_messages)

    assert result == {"turn": {"id": "turn-1"}}
    assert _wait_for_turn_completion(process, pending_messages) == 0


def test_native_builder_enforces_positive_step_limit(tmp_path, monkeypatch):
    class FakeBroker:
        def __init__(self, kit_path, **kwargs):
            self.callback_dir = tmp_path
            self.client_tool_enabled = False
            self.submitted = threading.Event()
            self.token = "callback-token"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def metadata(self):
            return {}

    class FakeRuntime:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

        def start_model_gateway(self, spec):
            pass

        def write_runtime_file(self, path, contents):
            pass

        def runtime_metadata(self):
            return {"backend": "fake"}

        def run(self, command, *, on_event, cancel_event, **kwargs):
            for sequence in range(3):
                on_event(
                    NativeProcessEvent(
                        sequence=sequence,
                        channel="stdout",
                        elapsed_seconds=float(sequence),
                        text=json.dumps(
                            {
                                "method": "item/completed",
                                "params": {
                                    "item": {
                                        "type": "agentMessage",
                                        "text": f"step {sequence + 1}",
                                    }
                                },
                            }
                        ),
                    )
                )
            return NativeProcessResult(
                command=command,
                exit_code=-15,
                cancelled=cancel_event.is_set(),
            )

        def close(self):
            pass

    monkeypatch.setattr(native_builder_module, "CallbackBroker", FakeBroker)
    monkeypatch.setattr(native_builder_module, "NativeSandboxRuntime", FakeRuntime)
    monkeypatch.setattr(
        native_builder_module,
        "ModelGatewaySpec",
        SimpleNamespace(
            from_host_environment=lambda *args, **kwargs: SimpleNamespace(
                token="gateway-token",
                base_url="http://gateway",
            )
        ),
    )

    result = CodexSandboxBuilder("gpt-5.4").build(
        tmp_path,
        "brief",
        native_builder_module.BuildBudget(max_steps=2, max_time_seconds=10),
    )

    assert result.done_reason == "max_steps"
    assert result.total_steps == 2
    assert [step.content for step in result.steps] == ["step 1", "step 2"]
