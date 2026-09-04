"""
Web display adapter for the Hyper-τ construction workbench.

Pushes the subset of sandbox and evaluation events consumed by the active
construction UI to a thread-safe queue. The FastAPI SSE endpoint reads from
this queue.
"""

from __future__ import annotations

from queue import Queue


class WebDisplay:
    """Push construction events to a queue for SSE streaming."""

    def __init__(self, queue: Queue):
        self.queue = queue

    def show_final_eval_start(self) -> None:
        self.queue.put({"type": "final_eval_start"})

    def show_eval_task_start(
        self, task_id: str, suite: str, idx: int, total: int
    ) -> None:
        """Announce a single eval task is starting.

        Args:
            task_id: The task being evaluated.
            suite: 'test' or 'regression'.
            idx: 0-based index within the suite.
            total: Total tasks in the suite.
        """
        self.queue.put(
            {
                "type": "eval_task_start",
                "task_id": task_id,
                "suite": suite,
                "idx": idx,
                "total": total,
            }
        )

    def show_eval_task_complete(
        self, task_id: str, suite: str, reward: float, passed: bool
    ) -> None:
        """Announce a single eval task has completed."""
        self.queue.put(
            {
                "type": "eval_task_complete",
                "task_id": task_id,
                "suite": suite,
                "reward": reward,
                "passed": passed,
            }
        )

    def show_sandbox_phase(self, phase: str, detail: str = "") -> None:
        self.queue.put({"type": "sandbox_phase", "phase": phase, "detail": detail})

    def show_sandbox_step(
        self,
        step: int,
        max_steps: int,
        thinking: str | None,
        tool_calls: list[dict] | None,
        tool_results: list[dict] | None,
        reasoning_summary: str | None = None,
    ) -> None:
        self.queue.put(
            {
                "type": "sandbox_step",
                "step": step,
                "max_steps": max_steps,
                "thinking": thinking,
                "reasoning_summary": reasoning_summary,
                "tool_calls": tool_calls,
                "tool_results": [
                    {
                        "name": tr.get("name", ""),
                        "result": (
                            tr.get("result", "")[:3000]
                            if len(tr.get("result", "")) > 3000
                            else tr.get("result", "")
                        ),
                    }
                    for tr in (tool_results or [])
                ],
            }
        )

    def show_sandbox_done(self, reason: str, steps: int, tool_calls: int) -> None:
        self.queue.put(
            {
                "type": "sandbox_done",
                "reason": reason,
                "steps": steps,
                "tool_calls": tool_calls,
            }
        )
