"""Provider-neutral process supervision for native coding harnesses.

The benchmark owns the outer Docker lifecycle. Codex and Claude Code run as
ordinary processes inside that container and retain their native file, edit,
search, and shell loops. This module deliberately knows nothing about either
provider protocol; adapters translate the streamed lines into BuildSteps.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from loguru import logger

from tau2.hyper.runtime_contract import (
    CONSTRUCTION_RUNTIME_CONTRACT_VERSION,
    DEFAULT_CONSTRUCTION_RUNTIME_IMAGE,
)
from tau2.hyper.sandbox.model_gateway import (
    MODEL_GATEWAY_HOST,
    MODEL_GATEWAY_PORT,
    ModelGatewaySpec,
)

NATIVE_NETWORK_PROFILE = "provider-only"


class WallClockDeadlineExpired(BaseException):
    """Raised to unwind a builder immediately at its wall-clock deadline."""


class WallClockDeadline:
    """Cross-thread wall-clock deadline with Unix main-thread interruption.

    CLI runs use ``SIGALRM`` so blocking Python I/O is interrupted. Worker
    threads use a timer callback, which is expected to stop their outer Docker
    container; the builder also checks :attr:`expired` between operations.
    """

    def __init__(
        self,
        timeout_seconds: float,
        *,
        on_expire: Optional[Callable[[], None]] = None,
    ):
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.timeout_seconds = timeout_seconds
        self.on_expire = on_expire
        self.started_at = 0.0
        self.expired = False
        self._timer: Optional[threading.Timer] = None
        self._uses_signal = False
        self._previous_handler = None

    @property
    def elapsed_seconds(self) -> float:
        """Elapsed monotonic seconds since entering the deadline."""
        if self.started_at == 0:
            return 0.0
        return time.monotonic() - self.started_at

    @property
    def remaining_seconds(self) -> float:
        """Non-negative seconds remaining."""
        return max(0.0, self.timeout_seconds - self.elapsed_seconds)

    def _timer_expired(self) -> None:
        self.expired = True
        if self.on_expire is not None:
            try:
                self.on_expire()
            except Exception as exc:  # noqa: BLE001 - deadline remains expired
                logger.warning(f"Wall-clock expiry callback failed: {exc}")

    def _signal_expired(self, signum, frame) -> None:
        self.expired = True
        raise WallClockDeadlineExpired

    def __enter__(self) -> WallClockDeadline:
        self.started_at = time.monotonic()
        self._uses_signal = (
            threading.current_thread() is threading.main_thread()
            and hasattr(signal, "SIGALRM")
            and hasattr(signal, "setitimer")
        )
        if self._uses_signal:
            self._previous_handler = signal.getsignal(signal.SIGALRM)
            signal.signal(signal.SIGALRM, self._signal_expired)
            signal.setitimer(signal.ITIMER_REAL, self.timeout_seconds)
        else:
            self._timer = threading.Timer(self.timeout_seconds, self._timer_expired)
            self._timer.daemon = True
            self._timer.start()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._timer is not None:
            self._timer.cancel()
        if self._uses_signal:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, self._previous_handler)


@dataclass(frozen=True)
class NativeProcessEvent:
    """One timestamped line emitted by a native harness process."""

    sequence: int
    channel: str
    text: str
    elapsed_seconds: float


@dataclass
class NativeProcessResult:
    """Terminal state and captured output for a supervised process."""

    command: list[str]
    events: list[NativeProcessEvent] = field(default_factory=list)
    exit_code: Optional[int] = None
    timed_out: bool = False
    cancelled: bool = False
    elapsed_seconds: float = 0.0

    @property
    def stdout(self) -> str:
        """Return stdout events joined for diagnostic metadata."""
        return "\n".join(e.text for e in self.events if e.channel == "stdout")

    @property
    def stderr(self) -> str:
        """Return stderr events joined for diagnostic metadata."""
        return "\n".join(e.text for e in self.events if e.channel == "stderr")


def _terminate_process_group(process: subprocess.Popen) -> None:
    """Terminate a process and every descendant in its process group."""
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=1)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    except OSError:
        process.kill()


def run_supervised_process(
    command: list[str],
    *,
    timeout_seconds: float,
    cwd: Optional[Path] = None,
    env: Optional[dict[str, str]] = None,
    stdin_text: Optional[str] = None,
    on_event: Optional[Callable[[NativeProcessEvent], None]] = None,
    on_timeout: Optional[Callable[[], None]] = None,
    cancel_event: Optional[threading.Event] = None,
    on_cancel: Optional[Callable[[], None]] = None,
) -> NativeProcessResult:
    """Run a process with line streaming and hard process-tree termination."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    started = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=str(cwd) if cwd is not None else None,
        env=env,
        stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        start_new_session=True,
    )
    if stdin_text is not None:
        assert process.stdin is not None
        process.stdin.write(stdin_text)
        process.stdin.close()

    events: list[NativeProcessEvent] = []
    event_lock = threading.Lock()

    def read_channel(channel: str, stream) -> None:
        for raw_line in iter(stream.readline, ""):
            with event_lock:
                event = NativeProcessEvent(
                    sequence=len(events),
                    channel=channel,
                    text=raw_line.rstrip("\r\n"),
                    elapsed_seconds=time.monotonic() - started,
                )
                events.append(event)
            if on_event is not None:
                on_event(event)
        stream.close()

    assert process.stdout is not None
    assert process.stderr is not None
    readers = [
        threading.Thread(
            target=read_channel,
            args=("stdout", process.stdout),
            daemon=True,
        ),
        threading.Thread(
            target=read_channel,
            args=("stderr", process.stderr),
            daemon=True,
        ),
    ]
    for reader in readers:
        reader.start()

    timed_out = False
    cancelled = False
    deadline = started + timeout_seconds
    while process.poll() is None:
        if cancel_event is not None and cancel_event.is_set():
            cancelled = True
            if on_cancel is not None:
                try:
                    on_cancel()
                except Exception as exc:  # noqa: BLE001 - still kill process
                    logger.warning(f"Native runtime cancel callback failed: {exc}")
            _terminate_process_group(process)
            break
        if time.monotonic() >= deadline:
            timed_out = True
            if on_timeout is not None:
                try:
                    on_timeout()
                except Exception as exc:  # noqa: BLE001 - still kill process
                    logger.warning(f"Native runtime timeout callback failed: {exc}")
            _terminate_process_group(process)
            break
        time.sleep(0.05)
    process.wait()

    for reader in readers:
        reader.join(timeout=2)

    return NativeProcessResult(
        command=list(command),
        events=events,
        exit_code=process.returncode,
        timed_out=timed_out,
        cancelled=cancelled,
        elapsed_seconds=time.monotonic() - started,
    )


def terminal_reason(
    result: NativeProcessResult,
    *,
    explicitly_submitted: bool,
    step_limit_reached: bool = False,
) -> str:
    """Normalize native process outcomes into benchmark terminal reasons."""
    if result.timed_out:
        return "time_budget"
    if explicitly_submitted:
        return "submitted"
    if step_limit_reached:
        return "max_steps"
    if result.exit_code == 0:
        return "completed"
    return "harness_error"


@dataclass(frozen=True)
class NativeMount:
    """One non-workspace bind mount exposed to the native runtime."""

    source: Path
    target: str
    read_only: bool = False


@dataclass(frozen=True)
class NativeRuntimeConfig:
    """Immutable Docker boundary shared by native coding harnesses."""

    image: str = DEFAULT_CONSTRUCTION_RUNTIME_IMAGE
    required_contract_version: int = CONSTRUCTION_RUNTIME_CONTRACT_VERSION
    memory: Optional[str] = None
    cpus: Optional[str] = None
    name_prefix: str = "tau2-native"

    def __post_init__(self) -> None:
        """Reject mutable image names at the native runtime boundary."""
        image_leaf = self.image.rsplit("/", 1)[-1]
        uses_implicit_latest = "@" not in image_leaf and ":" not in image_leaf
        if image_leaf.endswith(":latest") or uses_implicit_latest:
            raise ValueError(
                "Construction runtime images must use a versioned/commit tag or "
                f"digest, not Docker's mutable latest tag: {self.image!r}"
            )

    def container_command(
        self,
        *,
        kit_dir: Path,
        container_name: str,
        network_name: str,
        env: Optional[dict[str, str]] = None,
        extra_mounts: tuple[NativeMount, ...] = (),
    ) -> list[str]:
        """Render the detached container command without executing it."""
        command = [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            container_name,
            "--workdir",
            "/workspace",
            "--mount",
            f"type=bind,source={Path(kit_dir).resolve()},target=/workspace",
            "--tmpfs",
            "/runtime-home:rw,nosuid,nodev,exec,mode=0700",
            "--network",
            network_name,
            "-e",
            "HOME=/runtime-home",
            "-e",
            "XDG_CONFIG_HOME=/runtime-home/.config",
            "-e",
            "XDG_CACHE_HOME=/runtime-home/.cache",
            "-e",
            "PYTHONPATH=/workspace:/opt/tau2/src",
        ]
        if self.memory:
            command.extend(["--memory", str(self.memory)])
        if self.cpus:
            command.extend(["--cpus", str(self.cpus)])
        for mount in extra_mounts:
            mount_spec = (
                f"type=bind,source={Path(mount.source).resolve()},target={mount.target}"
            )
            if mount.read_only:
                mount_spec += ",readonly"
            command.extend(["--mount", mount_spec])
        for key, value in sorted((env or {}).items()):
            command.extend(["-e", f"{key}={value}"])
        command.extend([self.image, "sleep", "infinity"])
        return command


class NativeSandboxRuntime:
    """Long-lived construction container for one native harness invocation."""

    def __init__(
        self,
        kit_dir: Path,
        *,
        config: Optional[NativeRuntimeConfig] = None,
        env: Optional[dict[str, str]] = None,
        extra_mounts: tuple[NativeMount, ...] = (),
    ):
        self.kit_dir = Path(kit_dir).resolve()
        self.config = config or NativeRuntimeConfig()
        self.env = dict(env or {})
        self.extra_mounts = tuple(extra_mounts)
        self.container_name = f"{self.config.name_prefix}-{uuid.uuid4().hex[:12]}"
        self.network_name = f"{self.container_name}-network"
        self.gateway_container_name = f"{self.container_name}-model-gateway"
        self._started = False
        self._network_started = False
        self._gateway_started = False
        self._image_id: Optional[str] = None
        self._runtime_contract_version: Optional[int] = None
        self._runtime_source_revision: Optional[str] = None
        self._gateway_metadata: Optional[dict] = None

    @staticmethod
    def _docker_command(
        command: list[str],
        *,
        timeout: int = 30,
        env: Optional[dict[str, str]] = None,
    ):
        """Run one Docker control-plane command with normalized failures."""
        try:
            return subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=env,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("Docker CLI not found for native harness") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"Timed out running Docker command: {command[1]}"
            ) from exc

    def _start_internal_network(self) -> None:
        result = self._docker_command(
            [
                "docker",
                "network",
                "create",
                "--driver",
                "bridge",
                "--internal",
                "--label",
                "tau2.hyper.network-profile=provider-only",
                self.network_name,
            ]
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"Failed to create native sandbox network: {detail}")
        self._network_started = True

    def start_model_gateway(self, spec: ModelGatewaySpec) -> None:
        """Start the only container with both provider and internal egress."""
        if not self._started:
            raise RuntimeError("Native sandbox must start before its model gateway")
        if self._gateway_started:
            raise RuntimeError("Native model gateway is already running")

        sidecar_environment = spec.sidecar_environment()
        command = [
            "docker",
            "create",
            "--rm",
            "--name",
            self.gateway_container_name,
            "--network",
            self.network_name,
            "--network-alias",
            MODEL_GATEWAY_HOST,
            "--read-only",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,noexec,mode=0700",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
        ]
        for key in sorted(sidecar_environment):
            command.extend(["-e", key])
        command.extend(
            [
                self.config.image,
                "python",
                "-m",
                "tau2.hyper.sandbox.model_gateway",
            ]
        )
        control_environment = os.environ.copy()
        control_environment.update(sidecar_environment)
        try:
            result = self._docker_command(command, env=control_environment)
            if result.returncode != 0:
                detail = result.stderr.strip() or result.stdout.strip()
                raise RuntimeError(f"Failed to create native model gateway: {detail}")
            self._gateway_started = True

            # Attach egress before starting the gateway. Starting first creates a
            # race in which an early process exit enters Docker's auto-remove state
            # before `network connect` has a chance to run.
            connected = self._docker_command(
                [
                    "docker",
                    "network",
                    "connect",
                    "bridge",
                    self.gateway_container_name,
                ]
            )
            if connected.returncode != 0:
                detail = connected.stderr.strip() or connected.stdout.strip()
                raise RuntimeError(f"Failed to attach model gateway egress: {detail}")

            started = self._docker_command(
                ["docker", "start", self.gateway_container_name]
            )
            if started.returncode != 0:
                detail = started.stderr.strip() or started.stdout.strip()
                raise RuntimeError(f"Failed to start native model gateway: {detail}")

            health_environment = os.environ.copy()
            health_environment["TAU2_MODEL_GATEWAY_TOKEN"] = spec.token
            health_script = (
                "import os,urllib.request; "
                "r=urllib.request.Request("
                f"'http://{MODEL_GATEWAY_HOST}:{MODEL_GATEWAY_PORT}/health',"
                "headers={'Authorization':'Bearer '+"
                "os.environ['TAU2_MODEL_GATEWAY_TOKEN']}); "
                "urllib.request.urlopen(r,timeout=2).read()"
            )
            last_detail = "gateway did not become healthy"
            for _ in range(50):
                health = self._docker_command(
                    [
                        "docker",
                        "exec",
                        "-e",
                        "TAU2_MODEL_GATEWAY_TOKEN",
                        self.container_name,
                        "python",
                        "-c",
                        health_script,
                    ],
                    timeout=5,
                    env=health_environment,
                )
                if health.returncode == 0:
                    self._gateway_metadata = spec.metadata()
                    self._gateway_metadata.update(
                        {
                            "container_name": self.gateway_container_name,
                            "internal_host": MODEL_GATEWAY_HOST,
                            "internal_port": MODEL_GATEWAY_PORT,
                        }
                    )
                    return
                last_detail = (
                    health.stderr.strip() or health.stdout.strip() or last_detail
                )
                time.sleep(0.1)

            logs = self._docker_command(
                ["docker", "logs", "--tail", "50", self.gateway_container_name]
            )
            log_detail = logs.stderr.strip() or logs.stdout.strip()
            raise RuntimeError(
                "Native model gateway failed its health check: "
                f"{last_detail}; logs={log_detail[-2000:]}"
            )
        except BaseException:
            self._remove_gateway(force=True)
            raise

    def start(self) -> None:
        """Start the isolated outer construction container."""
        if not self.kit_dir.is_dir():
            raise ValueError(f"Kit directory does not exist: {self.kit_dir}")
        try:
            self._start_internal_network()
            command = self.config.container_command(
                kit_dir=self.kit_dir,
                container_name=self.container_name,
                network_name=self.network_name,
                env=self.env,
                extra_mounts=self.extra_mounts,
            )
            result = self._docker_command(command)
            if result.returncode != 0:
                detail = result.stderr.strip() or result.stdout.strip()
                raise RuntimeError(f"Failed to start native sandbox: {detail}")
            self._started = True
            self._verify_runtime_contract()
            inspect = self._docker_command(
                ["docker", "inspect", "--format", "{{.Image}}", self.container_name]
            )
            image_id = inspect.stdout.strip()
            if inspect.returncode != 0 or not image_id.startswith("sha256:"):
                detail = inspect.stderr.strip() or inspect.stdout.strip() or "no output"
                raise RuntimeError(
                    "Could not resolve the native construction runtime's immutable "
                    f"image ID: {detail}"
                )
            self._image_id = image_id
        except BaseException:
            self.close(force=True)
            raise

    def _verify_runtime_contract(self) -> None:
        """Fail before model startup when host and image APIs disagree."""
        probe = (
            "import json, os; "
            "from tau2.hyper.runtime_contract import "
            "CONSTRUCTION_RUNTIME_CONTRACT_VERSION as version; "
            "print(json.dumps({'contract_version': version, "
            "'source_revision': os.environ.get('TAU2_SOURCE_REVISION', 'unknown')}))"
        )
        result = self._docker_command(
            ["docker", "exec", self.container_name, "python", "-c", probe],
            timeout=15,
        )
        expected = self.config.required_contract_version
        try:
            metadata = json.loads(result.stdout.strip())
            actual = int(metadata["contract_version"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            actual = None
            metadata = {}

        if result.returncode != 0 or actual != expected:
            detail = result.stderr.strip() or result.stdout.strip() or "no output"
            actual_text = "unavailable" if actual is None else str(actual)
            raise RuntimeError(
                "Construction runtime contract mismatch: host requires "
                f"version {expected}, but image {self.config.image!r} reports "
                f"{actual_text}. Rebuild the image from this checkout. "
                f"Details: {detail}"
            )

        self._runtime_contract_version = actual
        self._runtime_source_revision = str(
            metadata.get("source_revision") or "unknown"
        )

    def run(
        self,
        command: list[str],
        *,
        timeout_seconds: float,
        stdin_text: Optional[str] = None,
        on_event: Optional[Callable[[NativeProcessEvent], None]] = None,
        cancel_event: Optional[threading.Event] = None,
        env: Optional[dict[str, str]] = None,
    ) -> NativeProcessResult:
        """Run the harness and remove the full container on timeout."""
        if not self._started:
            self.start()
        docker_exec = [
            "docker",
            "exec",
            "-i",
            "--workdir",
            "/workspace",
        ]
        for key in sorted((env or {})):
            docker_exec.extend(["-e", key])
        docker_exec.extend([self.container_name, *command])
        control_environment = os.environ.copy()
        control_environment.update(env or {})
        return run_supervised_process(
            docker_exec,
            timeout_seconds=timeout_seconds,
            env=control_environment,
            stdin_text=stdin_text,
            on_event=on_event,
            on_timeout=self.close,
            cancel_event=cancel_event,
            on_cancel=self.close,
        )

    def write_runtime_file(self, path: str, contents: str) -> None:
        """Write a harness config below `/runtime-home` without touching kit."""
        if not path.startswith("/runtime-home/") or ".." in Path(path).parts:
            raise ValueError("Runtime files must stay below /runtime-home")
        parent = str(Path(path).parent)
        result = run_supervised_process(
            [
                "docker",
                "exec",
                "-i",
                self.container_name,
                "bash",
                "-c",
                'umask 077; mkdir -p -- "$1"; cat > "$2"',
                "tau2-write-runtime-file",
                parent,
                path,
            ],
            timeout_seconds=30,
            stdin_text=contents,
        )
        if result.exit_code != 0:
            raise RuntimeError(f"Failed to write native runtime file: {result.stderr}")

    def runtime_metadata(self) -> dict:
        """Return non-secret, serializable runtime identity."""
        return {
            "backend": "docker-native",
            "image": self.config.image,
            "runtime_contract_version": self._runtime_contract_version,
            "runtime_source_revision": self._runtime_source_revision,
            "container_name": self.container_name,
            "kit_mount": str(self.kit_dir),
            "workdir": "/workspace",
            "runtime_home": "/runtime-home",
            "network_profile": NATIVE_NETWORK_PROFILE,
            "docker_network": self.network_name,
            "docker_network_internal": True,
            "image_id": self._image_id,
            "memory": self.config.memory,
            "cpus": self.config.cpus,
            "env_override_keys": sorted(self.env),
            "extra_mount_targets": [mount.target for mount in self.extra_mounts],
            "model_gateway": self._gateway_metadata,
        }

    def _remove_gateway(self, *, force: bool = False) -> None:
        if not force and not self._gateway_started:
            return
        try:
            self._docker_command(
                ["docker", "rm", "-f", self.gateway_container_name], timeout=15
            )
        except RuntimeError as exc:
            logger.warning(f"Failed to remove native model gateway: {exc}")
        self._gateway_started = False

    def close(self, *, force: bool = False) -> None:
        """Remove the container, terminating every process in its namespace."""
        self._remove_gateway(force=force)
        if force or self._started:
            try:
                self._docker_command(
                    ["docker", "rm", "-f", self.container_name], timeout=15
                )
            except RuntimeError as exc:
                logger.warning(f"Failed to remove native container: {exc}")
            self._started = False
        if force or self._network_started:
            try:
                self._docker_command(
                    ["docker", "network", "rm", self.network_name], timeout=15
                )
            except RuntimeError as exc:
                logger.warning(f"Failed to remove native network: {exc}")
            self._network_started = False

    def __enter__(self) -> NativeSandboxRuntime:
        self.start()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
