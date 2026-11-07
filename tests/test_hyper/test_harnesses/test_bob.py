"""Contract tests for the IBM Bob Shell harness configuration."""

import io
import json
import sqlite3
import tarfile
from pathlib import Path

from tau2.hyper.harnesses.bob import (
    BOB_SHELL_HARNESS_VERSION,
    BOB_SPANS_DIR,
    BOB_STORE_DIR,
    BOB_SUBMIT_GRACE_SECONDS,
    BobShellSandboxBuilder,
)
from tau2.hyper.sandbox.builder import SandboxBuilder
from tau2.hyper.sandbox.model_gateway import (
    _REQUEST_HEADERS,
    ModelGatewaySpec,
    _allowed_upstream_path,
    _pin_bob_profile_to_gateway,
)
from tau2.hyper.sandbox.native_runtime import NativeProcessEvent


def test_bob_builder_identity(monkeypatch):
    monkeypatch.delenv("BOB_TEAM_ID", raising=False)
    builder = BobShellSandboxBuilder("bob-default")

    assert isinstance(builder, SandboxBuilder)
    identity = builder.harness_identity().to_dict()
    assert identity["name"] == "bob"
    assert identity["version"] == BOB_SHELL_HARNESS_VERSION
    assert identity["config"]["mcp_servers"] == ["hyper_tau"]
    assert identity["config"]["team_id"] is False


def test_bob_command_runs_headless_with_the_prompt_as_an_argument(monkeypatch):
    monkeypatch.delenv("BOB_TEAM_ID", raising=False)
    builder = BobShellSandboxBuilder("bob-default")

    command = builder.harness_command()
    assert command[:4] == ["python", "-m", "tau2.hyper.harnesses.prompt_arg_driver", "bob"]
    assert "run" in command and "--format" in command
    assert command[command.index("--format") + 1] == "stream-json"
    assert "--accept-license" in command and "--trust" in command
    assert "--team-id" not in command

    monkeypatch.setenv("BOB_TEAM_ID", "team-1")
    assert BobShellSandboxBuilder("bob-default").harness_command()[-2:] == ["--team-id", "team-1"]


class _Broker:
    token = "cb-token"
    client_tool_enabled = True


def test_bob_runtime_files_stay_below_the_runtime_home():
    builder = BobShellSandboxBuilder("bob-default")
    files = builder.runtime_files(include_client_tool=True)

    assert all(path.startswith("/runtime-home/") for path in files)
    mcp = json.loads(files[builder.mcp_config_path])
    assert mcp["mcpServers"]["hyper_tau"]["args"] == ["-m", "tau2.hyper.sandbox.callback_mcp"]


def test_bob_mcp_entry_carries_the_callback_environment_by_value():
    # Bob starts an MCP server with an empty environment, so the entry names
    # the benchmark's package and the callback values the builder set.
    builder = BobShellSandboxBuilder("bob-default")
    environment = builder.runtime_environment(_Broker())
    assert environment["BOB_TELEMETRY_PROVIDER"] == "none"

    mcp = json.loads(builder.runtime_files(include_client_tool=True)[builder.mcp_config_path])
    env = mcp["mcpServers"]["hyper_tau"]["env"]
    assert env["PYTHONPATH"] == "/workspace:/opt/tau2/src"
    assert env["TAU2_CALLBACK_DIR"] == "/run/tau2-callback"
    assert env["TAU2_CALLBACK_TOKEN"] == "cb-token"
    assert env["TAU2_CLIENT_TOOL_ENABLED"] == "1"
    assert "BOB_LOG_LEVEL" not in env


def test_bob_model_gateway_environment_points_at_the_sidecar():
    builder = BobShellSandboxBuilder("bob-default")
    spec = ModelGatewaySpec(
        provider="bob",
        model="bob-default",
        token="tok",
        upstream_api_key="real",
        expires_at=1.0,
        upstream_origin="https://bob.example/api",
        wire="bob",
    )
    env = builder.model_gateway_environment(spec)
    assert env["BOB_API_KEY"] == "tok"
    # Bob appends /admin/v1/profile and /inference/v1/... to this URL, and the
    # sidecar scopes requests below /<provider>/v1/.
    assert env["BOB_GATEWAY_URL"] == f"{spec.base_url}/v1"
    assert env["BOB_GATEWAY_URL"].endswith("/bob/v1")
    assert spec.metadata()["allowed_api_families"] == ["admin/v1/profile", "inference/v1"]


def test_bob_wire_relays_the_profile_without_a_region_and_with_bobs_headers():
    assert {"x-instance-id", "x-team-id"} <= _REQUEST_HEADERS
    profile = {
        "user_id": "u",
        "instances": [
            {"instance_id": "i-1", "region_domain": "us-east.bob.example", "teams": []},
            {"instance_id": "i-2"},
        ],
    }
    pinned = json.loads(_pin_bob_profile_to_gateway(json.dumps(profile).encode()))
    assert [i.get("region_domain") for i in pinned["instances"]] == [None, None]
    assert pinned["instances"][0]["instance_id"] == "i-1"
    assert _pin_bob_profile_to_gateway(b"not json") == b"not json"


def test_bob_wire_allows_the_profile_and_inference_surface_only():
    assert _allowed_upstream_path("bob", "GET", "admin/v1/profile")
    assert _allowed_upstream_path("bob", "GET", "inference/v1/model/info")
    assert _allowed_upstream_path("bob", "POST", "inference/v1/chat/completions")
    assert not _allowed_upstream_path("bob", "POST", "admin/v1/profile")
    assert not _allowed_upstream_path("bob", "GET", "inference/v1")
    assert not _allowed_upstream_path("bob", "POST", "telemetry/v1/events")


def test_bob_stream_normalizes_text_tool_calls_and_results():
    builder = BobShellSandboxBuilder("bob-default")
    lines = [
        '{"type":"message","timestamp":"t","role":"user","content":"Run it."}',
        '{"type":"message","timestamp":"t","role":"assistant","content":"Let me"}',
        '{"type":"message","timestamp":"t","role":"assistant","content":" run it:"}',
        '{"type":"tool_use","timestamp":"t","tool_name":"execute_command","tool_id":"tooluse_1","parameters":{"command":"echo ok"}}',
        '{"type":"tool_result","timestamp":"t","tool_id":"tooluse_1","status":"success","output":"ok"}',
        '{"type":"message","timestamp":"t","role":"assistant","content":"o"}',
        '{"type":"message","timestamp":"t","role":"assistant","content":"k"}',
        '{"type":"result","timestamp":"t","status":"success","stats":{"tool_calls":1}}',
        "not json",
    ]
    steps = [
        step
        for line in lines
        for step in builder.normalize_event(NativeProcessEvent(sequence=0, channel="stdout", text=line, elapsed_seconds=0.0))
    ]
    # Bob streams assistant text one delta per frame: the deltas become one
    # step at the next tool call or at the closing result.
    assert [s.role for s in steps] == ["assistant", "assistant", "tool", "assistant"]
    assert steps[0].content == "Let me run it:"
    assert steps[1].tool_calls == [{"id": "tooluse_1", "name": "execute_command", "arguments": {"command": "echo ok"}}]
    assert steps[2].tool_results[0]["result"] == "ok" and steps[2].tool_results[0]["is_error"] is False
    assert steps[3].content == "ok"


def test_bob_keeps_nothing_and_exports_nothing_without_an_artifacts_dir(monkeypatch):
    monkeypatch.delenv("BOB_TEAM_ID", raising=False)
    builder = BobShellSandboxBuilder("bob-default")
    assert builder.keeps_artifacts is False
    assert builder.harness_identity().to_dict()["config"]["telemetry"] == "off"
    environment = builder.runtime_environment(_Broker())
    assert environment["BOB_TELEMETRY_PROVIDER"] == "none"
    assert "OTEL_EXPORTER_OTLP_ENDPOINT" not in environment
    settings = json.loads(builder.runtime_files(include_client_tool=True)[builder.runtime_config_path])
    assert settings["telemetry"] == {"enabled": False, "excludePayload": True}
    assert builder.harness_command()[2] == "tau2.hyper.harnesses.prompt_arg_driver"


def test_bob_with_an_artifacts_dir_runs_under_the_sink_with_telemetry_on(monkeypatch, tmp_path):
    monkeypatch.delenv("BOB_TEAM_ID", raising=False)
    builder = BobShellSandboxBuilder("bob-default", artifacts_dir=tmp_path / "bob-a")
    assert builder.keeps_artifacts is True
    # The submit gets a grace in which Bob writes the submit row and ends its turn.
    assert builder.submit_grace_seconds == BOB_SUBMIT_GRACE_SECONDS > 0
    config = builder.harness_identity().to_dict()["config"]
    assert config["telemetry"] == "otlp-to-sink" and config["submit_grace_seconds"] == BOB_SUBMIT_GRACE_SECONDS

    environment = builder.runtime_environment(_Broker())
    # Bob's own provider variables, not the standard OTEL one: on that one the
    # Shell filters a span's attributes to an allowlist with no usage split.
    assert environment["BOB_TELEMETRY_PROVIDER"] == "langfuse"
    assert environment["BOB_TELEMETRY_URL"] == "http://127.0.0.1:4318"
    assert environment["BOB_TELEMETRY_LF_PUBLIC_KEY"] and environment["BOB_TELEMETRY_LF_SECRET_KEY"]
    assert environment["BOB_TELEMETRY_AGENT_OPS_ENABLED"] == "true"
    assert not any(key.startswith("OTEL_") for key in environment)
    settings = json.loads(builder.runtime_files(include_client_tool=True)[builder.runtime_config_path])
    assert settings["telemetry"] == {"enabled": True, "excludePayload": True}

    command = builder.harness_command()
    assert command[:3] == ["python", "-m", "tau2.hyper.harnesses.otlp_sink_driver"]
    assert command[command.index("--out") + 1] == f"{BOB_SPANS_DIR}/spans.ndjson"
    assert command[command.index("--endpoint-env") + 1] == "BOB_TELEMETRY_URL"
    assert command[command.index("--") + 1 :][:3] == ["bob", "run", "--format"]


def _tar_of(directory: Path) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        for path in sorted(directory.rglob("*")):
            archive.add(path, arcname=str(path.relative_to(directory)))
    return buffer.getvalue()


class _Runtime:
    """What the Bob harness reads out of the container: tar streams of two directories."""

    def __init__(self, trees: dict[str, Path]):
        self.trees = trees
        self.read: list[str] = []

    def read_runtime_tree(self, path: str, *, timeout: int = 120) -> bytes:
        self.read.append(path)
        if path not in self.trees:
            raise RuntimeError(f"tar: {path}: Cannot open: No such file or directory")
        return _tar_of(self.trees[path])


def test_bob_collects_its_store_with_the_wal_folded_in_and_the_spans(tmp_path):
    # A store as Bob leaves it: WAL mode, with rows still in the write-ahead log.
    home = tmp_path / "home"
    store_dir = home / "db"
    store_dir.mkdir(parents=True)
    connection = sqlite3.connect(str(store_dir / "bob.db"))
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("CREATE TABLE tasks (id TEXT)")
    connection.execute("CREATE TABLE messages (id TEXT, data TEXT)")
    connection.execute("INSERT INTO tasks VALUES ('t1')")
    connection.executemany("INSERT INTO messages VALUES (?, ?)", [(f"m{i}", "{}") for i in range(5)])
    connection.commit()
    assert (store_dir / "bob.db-wal").stat().st_size > 0, "the rows are in the WAL, not yet in bob.db"
    spans_dir = home / "otlp"
    spans_dir.mkdir()
    (spans_dir / "spans.ndjson").write_text('{"body":{"resourceSpans":[]}}\n{"body":{"resourceSpans":[]}}\n')

    runtime = _Runtime({BOB_STORE_DIR: store_dir, BOB_SPANS_DIR: spans_dir})
    builder = BobShellSandboxBuilder("bob-default", artifacts_dir=tmp_path / "out")
    into = tmp_path / "out"
    into.mkdir()
    artifacts = builder.collect_artifacts(runtime, into)
    connection.close()

    assert runtime.read == [BOB_STORE_DIR, BOB_SPANS_DIR]
    assert artifacts["store"] == str(into / "bob-store" / "bob.db")
    assert artifacts["store_tasks"] == 1 and artifacts["store_messages"] == 5
    # whole in one file: a reader that opens bob.db alone sees every row
    assert not (into / "bob-store" / "bob.db-wal").exists() and not (into / "bob-store" / "bob.db-shm").exists()
    alone = sqlite3.connect(f"file:{into / 'bob-store' / 'bob.db'}?mode=ro", uri=True)
    assert alone.execute("SELECT count(*) FROM messages").fetchone()[0] == 5
    alone.close()
    assert artifacts["spans"] == str(into / "spans.ndjson") and artifacts["span_requests"] == 2
    assert not (into / ".otlp").exists()


def test_bob_collects_the_store_alone_when_nothing_was_exported(tmp_path):
    store_dir = tmp_path / "db"
    store_dir.mkdir()
    connection = sqlite3.connect(str(store_dir / "bob.db"))
    connection.execute("CREATE TABLE tasks (id TEXT)")
    connection.execute("CREATE TABLE messages (id TEXT)")
    connection.commit()
    connection.close()
    runtime = _Runtime({BOB_STORE_DIR: store_dir})
    into = tmp_path / "out"
    into.mkdir()
    artifacts = BobShellSandboxBuilder("bob-default", artifacts_dir=into).collect_artifacts(runtime, into)
    assert artifacts["store_messages"] == 0 and artifacts["spans"] is None and artifacts["span_requests"] == 0
    assert "No such file" in artifacts["spans_error"]


def test_the_result_file_carries_the_grace_and_the_artifacts(tmp_path):
    from tau2.hyper.sandbox.builder import BuildResult
    from tau2.hyper.sandbox.orchestrator import _build_end_record

    result = BuildResult(
        kit_path=tmp_path,
        metadata={
            "process": {
                "exit_code": 0,
                "cancelled": True,
                "submit_grace_seconds": 120.0,
                "exited_in_grace": True,
                "changed_after_submit": [],
            },
            "artifacts": {"collected": "exit", "store": "bob-store/bob.db", "tasks": 1, "messages": 187, "span_requests": 16},
        },
    )
    record = _build_end_record(result)
    assert record["process"]["exited_in_grace"] is True
    assert record["process"]["submit_grace_seconds"] == 120.0
    assert record["process"]["changed_after_submit"] == []
    assert record["artifacts"]["collected"] == "exit" and record["artifacts"]["messages"] == 187
