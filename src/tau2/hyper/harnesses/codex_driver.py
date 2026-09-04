"""Stdio driver for one Codex app-server construction turn."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading


def _emit(message: dict) -> None:
    sys.stdout.write(json.dumps(message, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _forward_stderr(stream) -> None:
    for line in iter(stream.readline, ""):
        sys.stderr.write(line)
        sys.stderr.flush()


def _send(process: subprocess.Popen, message: dict) -> None:
    assert process.stdin is not None
    process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
    process.stdin.flush()


def _decline_unexpected_request(process: subprocess.Popen, message: dict) -> None:
    method = message.get("method")
    if method in {
        "item/commandExecution/requestApproval",
        "item/fileChange/requestApproval",
    }:
        result = {"decision": "decline"}
    elif method == "item/permissions/requestApproval":
        result = {"permissions": []}
    elif method == "mcpServer/elicitation/request":
        result = {"action": "decline", "content": None}
    elif method == "tool/requestUserInput":
        result = {"answers": {}}
    else:
        result = {"decision": "decline"}
    _send(process, {"id": message["id"], "result": result})


def _read_message(process: subprocess.Popen) -> dict:
    assert process.stdout is not None
    line = process.stdout.readline()
    if not line:
        raise RuntimeError("Codex app-server closed its stdout")
    message = json.loads(line)
    _emit(message)
    if "id" in message and "method" in message:
        _decline_unexpected_request(process, message)
    return message


def _wait_for_response(
    process: subprocess.Popen,
    request_id: int,
    *,
    pending_messages: list[dict] | None = None,
) -> dict:
    while True:
        message = _read_message(process)
        if message.get("id") == request_id and "method" not in message:
            if "error" in message:
                raise RuntimeError(
                    f"Codex app-server request {request_id} failed: {message['error']}"
                )
            return message["result"]
        if pending_messages is not None:
            pending_messages.append(message)


def _turn_exit_code(message: dict) -> int | None:
    """Return a terminal exit code for a turn completion notification."""
    if message.get("method") != "turn/completed":
        return None
    turn = message.get("params", {}).get("turn", {})
    return 0 if turn.get("status") == "completed" else 1


def _wait_for_turn_completion(
    process: subprocess.Popen, pending_messages: list[dict]
) -> int:
    """Observe buffered and future notifications until the turn completes."""
    for message in pending_messages:
        exit_code = _turn_exit_code(message)
        if exit_code is not None:
            return exit_code
    while True:
        exit_code = _turn_exit_code(_read_message(process))
        if exit_code is not None:
            return exit_code


def _thread_start_params(model: str) -> dict:
    """Build pinned app-server v2 thread parameters."""
    return {
        "model": model,
        "cwd": "/workspace",
        "approvalPolicy": "never",
        "sandbox": "danger-full-access",
        "serviceName": "hyper_tau",
    }


def main() -> int:
    """Initialize app-server, run one thread/turn, and stream every event."""
    prompt = sys.stdin.read()
    if not prompt:
        raise ValueError("Codex driver requires a prompt on stdin")

    process = subprocess.Popen(
        ["codex", "app-server", "--listen", "stdio://"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    assert process.stderr is not None
    stderr_thread = threading.Thread(
        target=_forward_stderr,
        args=(process.stderr,),
        daemon=True,
    )
    stderr_thread.start()
    try:
        _send(
            process,
            {
                "method": "initialize",
                "id": 0,
                "params": {
                    "clientInfo": {
                        "name": "hyper_tau",
                        "title": "Hyper-tau benchmark",
                        "version": "1",
                    }
                },
            },
        )
        _wait_for_response(process, 0)
        _send(process, {"method": "initialized", "params": {}})

        model = os.environ["TAU2_DEVELOPER_MODEL"]
        thread = _wait_for_response_after_send(
            process,
            {
                "method": "thread/start",
                "id": 1,
                "params": _thread_start_params(model),
            },
            1,
        )["thread"]

        turn_params = {
            "threadId": thread["id"],
            "input": [{"type": "text", "text": prompt}],
            "cwd": "/workspace",
            "approvalPolicy": "never",
            "sandboxPolicy": {"type": "dangerFullAccess"},
            "model": model,
        }
        effort = os.environ.get("TAU2_DEVELOPER_REASONING_EFFORT")
        if effort:
            turn_params["effort"] = effort
        pending_turn_messages: list[dict] = []
        _wait_for_response_after_send(
            process,
            {"method": "turn/start", "id": 2, "params": turn_params},
            2,
            pending_messages=pending_turn_messages,
        )
        return _wait_for_turn_completion(process, pending_turn_messages)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        stderr_thread.join(timeout=1)


def _wait_for_response_after_send(
    process: subprocess.Popen,
    message: dict,
    request_id: int,
    *,
    pending_messages: list[dict] | None = None,
) -> dict:
    _send(process, message)
    return _wait_for_response(
        process,
        request_id,
        pending_messages=pending_messages,
    )


if __name__ == "__main__":
    raise SystemExit(main())
