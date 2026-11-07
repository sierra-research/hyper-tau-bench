"""Run a harness with an OTLP/HTTP sink beside it, in the same container.

A harness that exports OpenTelemetry spans (IBM Bob, with telemetry on and
``OTEL_EXPORTER_OTLP_ENDPOINT`` set) needs somewhere to post them. The
construction container's network is internal, so the sink runs here, on the
container's loopback, started before the harness: every export request it
receives is appended as one JSON line to ``--out`` (the shape
``scripts/bob/otlp-sink.mjs`` of Strata writes: ``received_at``, ``path``,
``body``), and nothing is forwarded. The harness is then started with the
developer prompt (read from stdin, as the supervised runtime delivers it)
appended as its last argument, like ``prompt_arg_driver``, and the driver
exits with the harness's exit code.

    python -m tau2.hyper.harnesses.otlp_sink_driver --out <file> [--port 4318] -- <command>…

The driver is not told when the harness is stopped from outside (the host
removes the container): a line is written as each request arrives, so what
the harness exported is on disk whenever the file is read.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import json
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

DEFAULT_PORT = 4318
_MAX_BODY = 64 * 1024 * 1024


class OtlpSink(ThreadingHTTPServer):
    """An HTTP server that appends every POST it receives to one NDJSON file."""

    daemon_threads = True

    def __init__(self, out: Path, host: str = "127.0.0.1", port: int = DEFAULT_PORT):
        self.out = Path(out)
        self.out.parent.mkdir(parents=True, exist_ok=True)
        self.received = 0
        self._write_lock = threading.Lock()
        super().__init__((host, port), _Handler)

    @property
    def endpoint(self) -> str:
        host, port = self.server_address[:2]
        return f"http://{host}:{port}"

    def record(self, path: str, headers: dict[str, str], body: bytes) -> None:
        line: dict[str, Any] = {
            "received_at": datetime.now(timezone.utc).isoformat(),
            "path": path,
            "content_type": headers.get("content-type", ""),
            "bytes": len(body),
        }
        try:
            line["body"] = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            # protobuf, or anything else: kept whole for a reader that knows it
            line["raw"] = base64.b64encode(body).decode("ascii")
        with self._write_lock:
            with self.out.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(line, separators=(",", ":")) + "\n")
            self.received += 1


class _Handler(BaseHTTPRequestHandler):
    server: OtlpSink

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - BaseHTTPRequestHandler API
        return

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        length = int(self.headers.get("content-length") or 0)
        if length < 0 or length > _MAX_BODY:
            self.send_error(413)
            return
        body = self.rfile.read(length)
        if self.headers.get("content-encoding", "").lower() == "gzip":
            try:
                body = gzip.decompress(body)
            except OSError:
                self.send_error(400)
                return
        headers = {key.lower(): value for key, value in self.headers.items()}
        self.server.record(self.path, headers, body)
        payload = b"{}"
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        payload = json.dumps({"received": self.server.received}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def start_sink(out: Path, *, port: int = DEFAULT_PORT) -> OtlpSink:
    """The sink serving on the loopback, in a daemon thread."""
    sink = OtlpSink(out, port=port)
    threading.Thread(target=sink.serve_forever, kwargs={"poll_interval": 0.2}, daemon=True).start()
    return sink


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="otlp_sink_driver", description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", required=True, help="the NDJSON file the export requests are appended to")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("command", nargs=argparse.REMAINDER, help="the harness command; the prompt on stdin is appended")
    args = parser.parse_args(argv)
    command = [part for part in args.command if part != "--"] if args.command[:1] == ["--"] else list(args.command)
    if not command:
        sys.stderr.write("otlp_sink_driver: no harness command given\n")
        return 2
    prompt = sys.stdin.read().strip()
    if not prompt:
        sys.stderr.write("otlp_sink_driver: empty developer prompt on stdin\n")
        return 2
    sink = start_sink(Path(args.out), port=args.port)
    environment = dict(os.environ)
    environment.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", sink.endpoint)
    try:
        completed = subprocess.run([*command, prompt], stdin=subprocess.DEVNULL, env=environment, check=False)
    finally:
        sink.shutdown()
        sink.server_close()
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
