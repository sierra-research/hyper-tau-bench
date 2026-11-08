"""IBM Bob Shell integration for the Hyper-τ construction sandbox.

Bob Shell (``bob``, the ``@ibm/bob`` package; ``bobshell`` before 2.0.9) runs one task headless with
``bob run --format stream-json``: one JSON object per line, of type
``message`` (a user or assistant text), ``tool_use`` (``tool_name``,
``tool_id``, ``parameters``), ``tool_result`` (``tool_id``, ``status``,
``output``) and a closing ``result`` (``status``, ``stats``). The prompt is a
positional argument, so the supervised runtime's stdin prompt reaches it
through ``prompt_arg_driver``.

Bob reaches its own model gateway (IBM's, behind an API key) rather than an
Anthropic or OpenAI endpoint: the run's sidecar speaks the ``bob`` wire
(``Authorization: apikey …`` with ``x-instance-id`` and ``x-team-id``,
``GET /admin/v1/profile``, then ``/inference/v1/model/info`` and
``/inference/v1/chat/completions``), and ``BOB_GATEWAY_URL`` points the
harness at the sidecar's ``/bob/v1`` prefix, below which Bob appends those
paths. The sidecar drops ``region_domain`` from the profile it relays, since
Bob would otherwise move its inference calls to ``api.<region_domain>``. The
model is Bob's own choice; ``--developer-llm`` names the run for the record.

The package is not on public npm: the construction image installs it from a
tarball dropped in ``docker/hyper-construction/vendor/`` (``npm pack`` of an
installed Bob Shell), and a run on an image without it fails at startup.

Bob's Developer traffic rides no gateway Strata can read, so the record of a
Bob build is Bob's own task store, ``/runtime-home/.bob/db/bob.db``, written
turn by turn below the private runtime home (a tmpfs), plus the OpenTelemetry
spans Bob exports when its telemetry is on. With an artifacts directory
(``--developer-artifacts-dir``) the build keeps both: the harness runs under
``otlp_sink_driver`` with a sink on the container's loopback, Bob's own
telemetry variables point at it (``BOB_TELEMETRY_PROVIDER=langfuse`` with
``BOB_TELEMETRY_URL``, the two Langfuse keys the Shell insists on, any value,
and ``BOB_TELEMETRY_AGENT_OPS_ENABLED`` for the generation spans; on the
standard ``OTEL_EXPORTER_OTLP_ENDPOINT`` Shell 2.0.9 filters a span's
attributes to an allowlist with no token counts and no first-token time,
measured 2026-11-07), the store and
the sink's file are copied out while the container is still there
(``collect_artifacts``), and the submit gets a grace (``submit_grace_seconds``)
in which Bob ends its turn on its own, so the ``submit`` row and the turn's
end are in the store instead of being cut by the host's kill.

Skills reach Bob the way they reach Claude Code, below the private runtime
home and never in the kit: each ``<name>/SKILL.md`` of the run's skills
directory is written to ``/runtime-home/.bob/skills/<name>/SKILL.md``, Bob's
global skills location (Shell 2.0.9 reads ``~/.bob/skills``, lists each skill's
name and description in its system prompt under ``available_skills`` and loads
one with its ``use_skill`` tool when the request matches the description), and
a global rules file ``/runtime-home/.bob/rules/strata-skills.md`` (rendered
into every mode's prompt under ``global_rules``) tells Bob to activate each
handed skill before it reads the kit and to keep working until ``submit``, as
the Claude driver's CLAUDE.md does. The ``use_skill`` frames are the record of
which skills Bob read (``build_result.skills_read``).
"""

from __future__ import annotations

import io
import json
import os
import sqlite3
import tarfile
from pathlib import Path
from typing import Any

from tau2.hyper.harnesses.claude import load_skills_dir
from tau2.hyper.sandbox.builder import BuildStep
from tau2.hyper.sandbox.model_gateway import ModelGatewaySpec
from tau2.hyper.sandbox.native_builder import NativeSandboxBuilder
from tau2.hyper.sandbox.native_runtime import NativeProcessEvent, NativeSandboxRuntime

BOB_SHELL_HARNESS_VERSION = "2.0.5"
# Bob starts an MCP server with an empty environment (HOME and nothing else),
# so the callback server's entry carries what it needs by value.
_MCP_SERVER_ENVIRONMENT_KEYS = (
    "TAU2_CALLBACK_DIR",
    "TAU2_CALLBACK_TOKEN",
    "TAU2_CALLBACK_TIMEOUT_SECONDS",
    "TAU2_CLIENT_TOOL_ENABLED",
    "TAU2_LIVE_EXPERIMENT_TOOL_ENABLED",
    "TAU2_SAMPLE_SCENARIOS_TOOL_ENABLED",
)
_RUNTIME_PYTHONPATH = "/workspace:/opt/tau2/src"
# Bob's task store below the runtime home, and where the sink writes the spans.
BOB_STORE_DIR = "/runtime-home/.bob/db"
BOB_SPANS_DIR = "/runtime-home/otlp"
BOB_SPANS_FILE = "spans.ndjson"
OTLP_SINK_PORT = 4318
# After submit, Bob answers the tool result with its closing message and ends
# the task; the store's last rows (the submit call, the turn's end) are written
# then. Measured at under a minute on the second run's tail; capped here.
BOB_SUBMIT_GRACE_SECONDS = 120.0
# Bob's global skills and rules below the runtime home (Shell 2.0.9 reads
# ``~/.bob/skills/<name>/SKILL.md`` and every ``~/.bob/rules/*.md``).
BOB_SKILLS_DIR = "/runtime-home/.bob/skills"
BOB_SKILLS_DIRECTIVE_PATH = "/runtime-home/.bob/rules/strata-skills.md"


def render_bob_skills_directive(skills: list[dict[str, str]]) -> str:
    """The global rule that tells Bob to activate the run's skills first."""
    count = "One skill was" if len(skills) == 1 else f"{len(skills)} skills were"
    lines = [
        "# Skills for this build",
        "",
        f"{count} handed to you for this build. Before you read the kit, activate each "
        "one with the use_skill tool and follow what it says:",
        "",
    ]
    for skill in skills:
        description = skill.get("description") or ""
        lines.append(
            f"- `{skill['name']}`" + (f" — {description}" if description else "")
        )
    lines += [
        "",
        "Keep working until you have called `hyper_tau.submit`: a session that ends "
        "without it is scored as the workspace stands, and the time left in your "
        "budget is lost.",
        "",
    ]
    return "\n".join(lines)


class BobShellSandboxBuilder(NativeSandboxBuilder):
    """Run IBM Bob Shell headless as a JSON-lines process."""

    harness_name = "bob"
    harness_version = BOB_SHELL_HARNESS_VERSION
    model_gateway_provider = "bob"
    # Bob reads its global settings below $HOME/.bob/settings; HOME is the
    # private runtime home, so these never touch the kit.
    runtime_config_path = "/runtime-home/.bob/settings/settings.json"
    mcp_config_path = "/runtime-home/.bob/settings/mcp.json"
    submit_grace_seconds = BOB_SUBMIT_GRACE_SECONDS

    def __init__(self, llm: str, *, skills_dir: str | Path | None = None, **kwargs):
        super().__init__(llm, **kwargs)
        self.skills = load_skills_dir(skills_dir) if skills_dir is not None else []
        self._mcp_server_environment: dict[str, str] = {}
        self._pending_text: list[str] = []

    def harness_config_metadata(self) -> dict:
        metadata = {
            "interface": "run-stream-json",
            "permission_mode": "headless-auto-approve",
            "license": "accepted-by-flag",
            "subagents": False,
            "mcp_servers": ["hyper_tau"],
            "model_gateway": "provider-only/per-run/bob-wire",
            "model_choice": "bob's own",
            "team_id": bool(os.environ.get("BOB_TEAM_ID")),
            "telemetry": "otlp-to-sink" if self.keeps_artifacts else "off",
            "submit_grace_seconds": self.submit_grace_seconds,
        }
        if self.skills:
            metadata["skills"] = [skill["name"] for skill in self.skills]
            metadata["skills_location"] = BOB_SKILLS_DIR
            metadata["skills_directive"] = "global-rule"
        return metadata

    @property
    def keeps_artifacts(self) -> bool:
        """Whether the build copies Bob's store and spans out (an artifacts directory was given)."""
        return self.artifacts_dir is not None

    def runtime_environment(self, broker) -> dict[str, str]:
        environment = super().runtime_environment(broker)
        # The builder asks for the environment before the runtime files, so
        # the MCP entry written next carries these values.
        self._mcp_server_environment = {
            key: environment[key]
            for key in _MCP_SERVER_ENVIRONMENT_KEYS
            if key in environment
        }
        environment["BOB_LOG_LEVEL"] = "warn"
        if self.keeps_artifacts:
            # Telemetry on (settings.json), exported as OTLP/JSON to the sink the
            # driver starts on the container's loopback, through Bob's own
            # provider variables: the standard OTEL variable makes the Shell
            # filter a span to an allowlist with no usage split and no
            # first-token time, the Langfuse provider sends the whole span
            # (the keys are required, their value is not checked by a sink
            # that forwards nothing), and the agent-ops switch is what exports
            # the ``LLM Generation`` spans on that path. Nothing leaves the
            # container (its network is internal, and the sidecar serves the
            # model gateway's two families only).
            environment.update(
                {
                    "BOB_TELEMETRY_PROVIDER": "langfuse",
                    "BOB_TELEMETRY_URL": f"http://127.0.0.1:{OTLP_SINK_PORT}",
                    "BOB_TELEMETRY_LF_PUBLIC_KEY": "sink",
                    "BOB_TELEMETRY_LF_SECRET_KEY": "sink",
                    "BOB_TELEMETRY_AGENT_OPS_ENABLED": "true",
                }
            )
        else:
            environment["BOB_TELEMETRY_PROVIDER"] = "none"
        return environment

    def model_gateway_environment(self, spec: ModelGatewaySpec) -> dict[str, str]:
        return {
            "BOB_API_KEY": spec.token,
            "BOB_GATEWAY_URL": f"{spec.base_url}/v1",
        }

    def render_runtime_config(
        self,
        *,
        include_client_tool: bool,
        include_live_experiment_tool: bool = False,
        include_sample_scenarios_tool: bool = False,
    ) -> str:
        # `telemetry.enabled` is the Shell's own switch (its settings reference);
        # the payload (prompts, replies, tool text) stays out of the spans: the
        # split, the latency and the ids are what the trace reads.
        return json.dumps(
            {
                "autoApprove": True,
                "telemetry": {"enabled": self.keeps_artifacts, "excludePayload": True},
            },
            indent=2,
            sort_keys=True,
        )

    def runtime_files(
        self,
        *,
        include_client_tool: bool,
        include_live_experiment_tool: bool = False,
        include_sample_scenarios_tool: bool = False,
    ) -> dict[str, str]:
        # Bob gives an MCP server an empty environment: the callback server
        # reads TAU2_CALLBACK_* and finds the benchmark's package through the
        # entry's own ``env``.
        files = {
            self.runtime_config_path: self.render_runtime_config(
                include_client_tool=include_client_tool,
                include_live_experiment_tool=include_live_experiment_tool,
                include_sample_scenarios_tool=include_sample_scenarios_tool,
            ),
            self.mcp_config_path: json.dumps(
                {
                    "mcpServers": {
                        "hyper_tau": {
                            "command": "python",
                            "args": ["-m", "tau2.hyper.sandbox.callback_mcp"],
                            "env": {
                                "PYTHONPATH": _RUNTIME_PYTHONPATH,
                                **self._mcp_server_environment,
                            },
                        }
                    }
                },
                indent=2,
                sort_keys=True,
            ),
        }
        files.update(self.skills_files())
        return files

    def skills_files(self) -> dict[str, str]:
        """The run's skills below Bob's global skills directory, and the rule that says to activate them."""
        if not self.skills:
            return {}
        files = {BOB_SKILLS_DIRECTIVE_PATH: render_bob_skills_directive(self.skills)}
        for skill in self.skills:
            files[f"{BOB_SKILLS_DIR}/{skill['name']}/SKILL.md"] = skill["content"]
        return files

    def skills_read(self, steps) -> list[str] | None:
        """The run's skills Bob activated with ``use_skill``, in order of first activation."""
        if not self.skills:
            return None
        wanted = {skill["name"] for skill in self.skills}
        read: list[str] = []
        for step in steps:
            for call in getattr(step, "tool_calls", None) or []:
                if not isinstance(call, dict) or call.get("name") != "use_skill":
                    continue
                arguments = call.get("arguments")
                name = (
                    arguments.get("skill_name") if isinstance(arguments, dict) else None
                )
                if name in wanted and name not in read:
                    read.append(name)
        return read

    def harness_command(self) -> list[str]:
        driver = (
            [
                "tau2.hyper.harnesses.otlp_sink_driver",
                "--out",
                f"{BOB_SPANS_DIR}/{BOB_SPANS_FILE}",
                "--port",
                str(OTLP_SINK_PORT),
                "--endpoint-env",
                "BOB_TELEMETRY_URL",
                "--",
            ]
            if self.keeps_artifacts
            else ["tau2.hyper.harnesses.prompt_arg_driver"]
        )
        command = [
            "python",
            "-m",
            *driver,
            "bob",
            "run",
            "--format",
            "stream-json",
            "--workspace",
            "/workspace",
            "--trust",
            "--accept-license",
            "--disable-subagents",
        ]
        team_id = os.environ.get("BOB_TEAM_ID")
        if team_id:
            command.extend(["--team-id", team_id])
        return command

    def collect_artifacts(
        self, runtime: NativeSandboxRuntime, into: Path
    ) -> dict | None:
        """Bob's task store (its write-ahead log folded in) and the sink's spans, copied out."""
        store_dir = into / "bob-store"
        store_dir.mkdir(parents=True, exist_ok=True)
        _extract(runtime.read_runtime_tree(BOB_STORE_DIR), store_dir)
        store = store_dir / "bob.db"
        artifacts: dict[str, Any] = {"store": str(store), **_fold_wal(store)}
        spans = into / BOB_SPANS_FILE
        try:
            spans_dir = into / ".otlp"
            spans_dir.mkdir(exist_ok=True)
            _extract(runtime.read_runtime_tree(BOB_SPANS_DIR), spans_dir)
            exported = spans_dir / BOB_SPANS_FILE
            if exported.is_file():
                exported.replace(spans)
            for leftover in spans_dir.iterdir():
                leftover.unlink()
            spans_dir.rmdir()
        except RuntimeError as exc:
            # No directory: Bob exported nothing (or the driver never ran).
            artifacts["spans_error"] = str(exc)[:300]
        if spans.is_file():
            with spans.open("rb") as handle:
                requests = sum(1 for line in handle if line.strip())
            artifacts.update({"spans": str(spans), "span_requests": requests})
        else:
            artifacts.update({"spans": None, "span_requests": 0})
        return artifacts

    def normalize_event(self, event: NativeProcessEvent) -> list[BuildStep]:
        if event.channel != "stdout":
            return []
        try:
            frame = json.loads(event.text)
        except json.JSONDecodeError:
            return []
        if not isinstance(frame, dict):
            return []
        kind = frame.get("type")
        # Bob streams an assistant message as one ``message`` frame per text
        # delta, so the deltas are held and become one step at the next tool
        # call, tool result or the closing ``result``.
        if kind == "message" and frame.get("role") == "assistant":
            content = _text(frame.get("content"))
            if content:
                self._pending_text.append(content)
            return []
        if kind == "message":
            return []
        return self._flush_text() + self._normalize_frame(kind, frame)

    def _flush_text(self) -> list[BuildStep]:
        if not self._pending_text:
            return []
        content = "".join(self._pending_text)
        self._pending_text = []
        return [BuildStep(step_idx=0, role="assistant", content=content)]

    def _normalize_frame(self, kind: str | None, frame: dict) -> list[BuildStep]:
        if kind == "tool_use":
            return [
                BuildStep(
                    step_idx=0,
                    role="assistant",
                    tool_calls=[
                        {
                            "id": str(frame.get("tool_id", "")),
                            "name": str(frame.get("tool_name", "")),
                            "arguments": frame.get("parameters") or {},
                        }
                    ],
                )
            ]
        if kind == "tool_result":
            return [
                BuildStep(
                    step_idx=0,
                    role="tool",
                    tool_results=[
                        {
                            "id": str(frame.get("tool_id", "")),
                            "name": "tool_result",
                            "result": _text(frame.get("output")),
                            "is_error": frame.get("status") not in (None, "success"),
                        }
                    ],
                )
            ]
        return []


def _extract(tar_bytes: bytes, into: Path) -> None:
    """A tar stream read out of the container, into a directory of the run; nothing outside it."""
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:") as archive:
        members = [m for m in archive.getmembers() if m.isfile() or m.isdir()]
        for member in members:
            target = (into / member.name).resolve()
            if into.resolve() not in (target, *target.parents):
                raise RuntimeError(
                    f"the archive names a path outside the artifacts directory: {member.name}"
                )
        try:
            archive.extractall(into, members=members, filter="data")
        except TypeError:  # Python before 3.12: no filter argument
            archive.extractall(into, members=members)


def _fold_wal(store: Path) -> dict[str, Any]:
    """The store whole in one file: the write-ahead log folded in, with the counts it then holds."""
    if not store.is_file():
        raise RuntimeError(f"no bob.db in the store copied out ({store.parent})")
    connection = sqlite3.connect(str(store))
    try:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.execute("PRAGMA journal_mode=DELETE")
        tasks = connection.execute("SELECT count(*) FROM tasks").fetchone()[0]
        messages = connection.execute("SELECT count(*) FROM messages").fetchone()[0]
    finally:
        connection.close()
    for suffix in ("-wal", "-shm"):
        leftover = store.with_name(store.name + suffix)
        if leftover.exists():
            leftover.unlink()
    return {"store_tasks": int(tasks), "store_messages": int(messages)}


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, default=str)
