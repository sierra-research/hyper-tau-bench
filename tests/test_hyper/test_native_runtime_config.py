"""Docker argv rendering tests for the native construction runtime."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tau2.hyper.runtime_contract import (
    CONSTRUCTION_RUNTIME_CONTRACT_VERSION,
    DEFAULT_CONSTRUCTION_RUNTIME_IMAGE,
)
from tau2.hyper.sandbox.model_gateway import ModelGatewaySpec
from tau2.hyper.sandbox.native_runtime import (
    NativeMount,
    NativeRuntimeConfig,
    NativeSandboxRuntime,
)


def test_container_uses_separate_ephemeral_home_and_no_raw_provider_keys(tmp_path):
    config = NativeRuntimeConfig(image="runtime@sha256:abc")

    command = config.container_command(
        kit_dir=tmp_path,
        container_name="tau2-native-test",
        network_name="tau2-test-internal",
        env={"TAU2_CALLBACK_DIR": "/run/tau2-callback"},
        extra_mounts=(NativeMount(tmp_path / "callbacks", "/run/tau2-callback"),),
    )

    joined = " ".join(command)
    assert "target=/workspace" in joined
    assert "--tmpfs /runtime-home:rw,nosuid,nodev,exec,mode=0700" in joined
    assert "HOME=/runtime-home" in joined
    assert "XDG_CONFIG_HOME=/runtime-home/.config" in joined
    assert "PYTHONPATH=/workspace:/opt/tau2/src" in joined
    assert "--network tau2-test-internal" in joined
    assert "target=/run/tau2-callback" in joined
    assert "OPENAI_API_KEY" not in joined
    assert "ANTHROPIC_API_KEY" not in joined


def test_native_runtime_default_image_is_versioned():
    assert NativeRuntimeConfig().image == DEFAULT_CONSTRUCTION_RUNTIME_IMAGE
    assert not NativeRuntimeConfig().image.endswith(":latest")


@pytest.mark.parametrize(
    "image",
    ["tau2-construction-runtime", "tau2-construction-runtime:latest"],
)
def test_native_runtime_rejects_mutable_latest_image(image):
    with pytest.raises(ValueError, match="mutable latest"):
        NativeRuntimeConfig(image=image)


def test_native_runtime_records_matching_contract(tmp_path, monkeypatch):
    runtime = NativeSandboxRuntime(tmp_path)

    def fake_docker(command, **kwargs):
        if command[:2] == ["docker", "network"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if command[:2] == ["docker", "run"]:
            return SimpleNamespace(returncode=0, stdout="container\n", stderr="")
        if command[:2] == ["docker", "exec"]:
            return SimpleNamespace(
                returncode=0,
                stdout=(
                    '{"contract_version": '
                    f"{CONSTRUCTION_RUNTIME_CONTRACT_VERSION}, "
                    '"source_revision": "abc123"}\n'
                ),
                stderr="",
            )
        if command[:2] == ["docker", "inspect"]:
            return SimpleNamespace(
                returncode=0,
                stdout="sha256:0123456789abcdef\n",
                stderr="",
            )
        raise AssertionError(command)

    monkeypatch.setattr(runtime, "_docker_command", fake_docker)
    runtime.start()

    metadata = runtime.runtime_metadata()
    assert metadata["runtime_contract_version"] == (
        CONSTRUCTION_RUNTIME_CONTRACT_VERSION
    )
    assert metadata["runtime_source_revision"] == "abc123"
    assert metadata["image_id"] == "sha256:0123456789abcdef"


def test_gateway_attaches_egress_before_process_start(tmp_path, monkeypatch):
    runtime = NativeSandboxRuntime(tmp_path)
    runtime._started = True
    calls = []

    def fake_docker(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(runtime, "_docker_command", fake_docker)
    spec = ModelGatewaySpec(
        provider="openai",
        model="gpt-5.4",
        token="scoped-token",
        upstream_api_key="raw-provider-key",
        expires_at=9999999999,
    )

    runtime.start_model_gateway(spec)

    assert calls[0][0][:2] == ["docker", "create"]
    assert calls[1][0] == [
        "docker",
        "network",
        "connect",
        "bridge",
        runtime.gateway_container_name,
    ]
    assert calls[2][0] == ["docker", "start", runtime.gateway_container_name]
    assert "raw-provider-key" not in " ".join(calls[0][0])
    assert calls[0][1]["env"]["TAU2_MODEL_GATEWAY_UPSTREAM_KEY"] == ("raw-provider-key")


def test_runtime_start_timeout_cleans_indeterminate_docker_resources(
    tmp_path, monkeypatch
):
    runtime = NativeSandboxRuntime(tmp_path)
    calls = []

    def fake_docker(command, **kwargs):
        calls.append(command)
        if command[:2] == ["docker", "run"]:
            raise RuntimeError("Timed out running Docker command: run")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(runtime, "_docker_command", fake_docker)

    with pytest.raises(RuntimeError, match="Timed out"):
        runtime.start()

    assert ["docker", "rm", "-f", runtime.container_name] in calls
    assert ["docker", "network", "rm", runtime.network_name] in calls


def test_gateway_create_timeout_cleans_indeterminate_container(tmp_path, monkeypatch):
    runtime = NativeSandboxRuntime(tmp_path)
    runtime._started = True
    calls = []

    def fake_docker(command, **kwargs):
        calls.append(command)
        if command[:2] == ["docker", "create"]:
            raise RuntimeError("Timed out running Docker command: create")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(runtime, "_docker_command", fake_docker)
    spec = ModelGatewaySpec(
        provider="openai",
        model="gpt-5.4",
        token="scoped-token",
        upstream_api_key="raw-provider-key",
        expires_at=9999999999,
    )

    with pytest.raises(RuntimeError, match="Timed out"):
        runtime.start_model_gateway(spec)

    assert ["docker", "rm", "-f", runtime.gateway_container_name] in calls


MAINTAINED_DOMAINS = ("airline_plus", "retail_plus", "banking_knowledge", "telecom")


def _maintained_task_files():
    """Every release task JSON for a maintained construction domain."""
    task_root = (
        Path(__file__).resolve().parents[2] / "data" / "tau2" / "hyper" / "tasks"
    )
    return [
        path
        for path in sorted(task_root.glob("*.json"))
        if json.loads(path.read_text()).get("source_domain") in MAINTAINED_DOMAINS
    ]


def test_maintained_tasks_do_not_request_ignored_docker_network():
    task_files = _maintained_task_files()

    assert task_files
    assert all('"docker_network"' not in path.read_text() for path in task_files)


def test_maintained_tasks_pin_the_construction_runtime_image():
    task_files = _maintained_task_files()

    assert task_files
    for path in task_files:
        task = json.loads(path.read_text())
        image = task.get("sandbox_config", {}).get("docker_image")
        if image is not None:
            assert not image.endswith(":latest"), path
