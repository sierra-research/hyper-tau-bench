"""Focused tests for provider-neutral native process supervision."""

import sys
import threading
import time

from tau2.hyper.sandbox.native_runtime import (
    NativeProcessEvent,
    WallClockDeadline,
    WallClockDeadlineExpired,
    run_supervised_process,
    terminal_reason,
)


def test_wall_clock_deadline_interrupts_blocking_work():
    started = time.monotonic()

    try:
        with WallClockDeadline(0.05):
            time.sleep(30)
    except WallClockDeadlineExpired:
        pass
    else:
        raise AssertionError("expected hard wall-clock interruption")

    assert time.monotonic() - started < 5


def test_supervised_process_streams_both_channels():
    seen: list[NativeProcessEvent] = []

    result = run_supervised_process(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "print('hello', flush=True); "
                "print('warning', file=sys.stderr, flush=True)"
            ),
        ],
        timeout_seconds=5,
        on_event=seen.append,
    )

    assert result.exit_code == 0
    assert not result.timed_out
    assert {(event.channel, event.text) for event in seen} == {
        ("stdout", "hello"),
        ("stderr", "warning"),
    }


def test_supervised_process_hard_timeout_terminates_process():
    started = time.monotonic()

    result = run_supervised_process(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        timeout_seconds=0.1,
    )

    assert result.timed_out
    assert result.exit_code is not None
    assert time.monotonic() - started < 5
    assert terminal_reason(result, explicitly_submitted=False) == "time_budget"


def test_supervised_process_stops_on_explicit_submission_signal():
    submitted = threading.Event()
    timer = threading.Timer(0.05, submitted.set)
    timer.start()
    try:
        result = run_supervised_process(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            timeout_seconds=5,
            cancel_event=submitted,
        )
    finally:
        timer.cancel()

    assert result.cancelled
    assert not result.timed_out
    assert terminal_reason(result, explicitly_submitted=True) == "submitted"


def test_terminal_reason_normalizes_completion_and_failure():
    completed = run_supervised_process(
        [sys.executable, "-c", "pass"], timeout_seconds=5
    )
    failed = run_supervised_process(
        [sys.executable, "-c", "raise SystemExit(7)"], timeout_seconds=5
    )

    assert terminal_reason(completed, explicitly_submitted=True) == "submitted"
    assert terminal_reason(completed, explicitly_submitted=False) == "completed"
    assert terminal_reason(failed, explicitly_submitted=False) == "harness_error"


def test_terminal_reason_reports_explicit_step_limit():
    completed = run_supervised_process(
        [sys.executable, "-c", "pass"], timeout_seconds=5
    )

    assert (
        terminal_reason(
            completed,
            explicitly_submitted=False,
            step_limit_reached=True,
        )
        == "max_steps"
    )
