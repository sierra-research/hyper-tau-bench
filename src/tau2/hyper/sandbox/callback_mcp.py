"""Minimal stdio MCP server for native Hyper-τ callback tools."""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path

_PROTOCOL_VERSION = "2024-11-05"


def _tool_definitions(
    *,
    include_client: bool,
    include_live_experiment: bool,
    include_sample_scenarios: bool,
) -> list[dict]:
    tools = [
        {
            "name": "run_local_test",
            "description": (
                "Run developer-authored customer scenario JSON against the "
                "submitted candidate runtime."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_path": {"type": "string"},
                    "verbose": {"type": "boolean", "default": False},
                    "max_steps": {"type": "integer", "default": 100},
                },
                "required": ["task_path"],
            },
        },
        {
            "name": "submit",
            "description": (
                "Submit the current workspace for evaluation and end construction."
            ),
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]
    if include_sample_scenarios:
        tools.insert(
            1,
            {
                "name": "run_sample_scenarios",
                "description": (
                    "Run the current candidate against the client-supplied "
                    "sample scenarios. The scenario set is fixed and case ids "
                    "are stable across runs. Runs are quota-limited and a run "
                    "is consumed even if the candidate fails to load or "
                    "execute."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
        )
    if include_live_experiment:
        tools.insert(
            1,
            {
                "name": "run_live_experiment",
                "description": (
                    "Run the current candidate once against a small hidden "
                    "sample of representative traffic. The attempt is consumed "
                    "even if the candidate fails to load or execute. The "
                    "report is also saved to a timestamped "
                    "simulations/live_experiment_*.json artifact, so it can "
                    "be re-read from disk if this tool result is lost."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
        )
    if include_client:
        tools.insert(
            1,
            {
                "name": "talk_to_client",
                "description": (
                    "Ask the business Client a requirements question. This is "
                    "quota limited and not available on construction-only tasks."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {"message": {"type": "string"}},
                    "required": ["message"],
                },
            },
        )
    return tools


def _call_broker(tool: str, arguments: dict) -> dict:
    callback_dir = Path(os.environ["TAU2_CALLBACK_DIR"])
    token = os.environ["TAU2_CALLBACK_TOKEN"]
    timeout = float(os.environ.get("TAU2_CALLBACK_TIMEOUT_SECONDS", "28800"))
    request_id = uuid.uuid4().hex
    request_path = callback_dir / f"request-{request_id}.json"
    temporary_path = callback_dir / f".request-{request_id}.tmp"
    response_path = callback_dir / f"response-{request_id}.json"
    temporary_path.write_text(
        json.dumps(
            {
                "token": token,
                "tool": tool,
                "arguments": arguments,
            }
        )
    )
    temporary_path.replace(request_path)

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if response_path.exists():
            response = json.loads(response_path.read_text())
            response_path.unlink(missing_ok=True)
            return response
        time.sleep(0.05)
    request_path.unlink(missing_ok=True)
    raise TimeoutError(f"Hyper-tau callback timed out after {timeout:g}s")


def _result(message_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _error(message_id, code: int, message: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": {"code": code, "message": message},
    }


def _handle(message: dict) -> dict | None:
    method = message.get("method")
    message_id = message.get("id")
    if method == "initialize":
        return _result(
            message_id,
            {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "hyper-tau", "version": "1"},
            },
        )
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return _result(message_id, {})
    if method == "tools/list":
        include_client = os.environ.get("TAU2_CLIENT_TOOL_ENABLED") == "1"
        include_live_experiment = (
            os.environ.get("TAU2_LIVE_EXPERIMENT_TOOL_ENABLED") == "1"
        )
        include_sample_scenarios = (
            os.environ.get("TAU2_SAMPLE_SCENARIOS_TOOL_ENABLED") == "1"
        )
        return _result(
            message_id,
            {
                "tools": _tool_definitions(
                    include_client=include_client,
                    include_live_experiment=include_live_experiment,
                    include_sample_scenarios=include_sample_scenarios,
                )
            },
        )
    if method == "tools/call":
        params = message.get("params", {})
        try:
            response = _call_broker(
                str(params.get("name", "")),
                params.get("arguments", {}),
            )
        except Exception as exc:  # noqa: BLE001 - rendered as MCP tool error
            response = {"ok": False, "error": {"message": str(exc)}}
        if response.get("ok"):
            text = str(response.get("result", ""))
            return _result(
                message_id,
                {"content": [{"type": "text", "text": text}]},
            )
        error = response.get("error", {})
        return _result(
            message_id,
            {
                "content": [
                    {"type": "text", "text": str(error.get("message", "error"))}
                ],
                "isError": True,
            },
        )
    if message_id is None:
        return None
    return _error(message_id, -32601, f"Method not found: {method}")


def main() -> None:
    """Serve newline-delimited JSON-RPC over stdin/stdout."""
    for line in sys.stdin:
        try:
            message = json.loads(line)
            response = _handle(message)
        except Exception as exc:  # noqa: BLE001 - keep MCP process alive
            response = _error(None, -32603, str(exc))
        if response is not None:
            sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
