"""Stable public and persisted serialization for Hyper-τ results."""

from __future__ import annotations

import json
from typing import Any

from tau2.hyper.data_model import OuterLoopResult

_SUMMARY_FIELDS = frozenset(
    {
        "final_test_reward",
        "final_quality_reward",
        "performance_reward",
        "performance_penalty",
        "performance_details",
        "total_outer_steps",
        "client_turns_used",
    }
)
_DETAIL_FIELDS = _SUMMARY_FIELDS | {"domain", "test_details", "steps"}
_COMPACT_STEP_FIELDS = frozenset({"step_idx", "action", "result_summary"})


def bounded_tool_result(value: object, max_chars: int) -> str:
    """Return a JSON-safe, bounded text representation of a tool result."""
    if value is None:
        return ""
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text[:max_chars]


def serialize_result_summary(result: OuterLoopResult) -> dict[str, Any]:
    """Serialize the compact result persisted in completed recordings."""
    return result.model_dump(mode="json", include=_SUMMARY_FIELDS)


def serialize_result_detail(result: OuterLoopResult) -> dict[str, Any]:
    """Serialize the detailed result exposed by the run API."""
    return result.model_dump(mode="json", include=_DETAIL_FIELDS)


def serialize_result_event(result: OuterLoopResult) -> dict[str, Any]:
    """Serialize a compact result event for recording and live display."""
    payload = result.model_dump(
        mode="json",
        include=_SUMMARY_FIELDS | {"domain", "test_details"},
    )
    payload["steps"] = [
        step.model_dump(mode="json", include=_COMPACT_STEP_FIELDS)
        for step in result.steps
    ]
    return {"type": "result", "result": payload}


def compact_run_result(
    *,
    task,
    result: OuterLoopResult,
    config: dict[str, Any],
    recording_path,
) -> dict[str, Any]:
    """One run as a small record another system reads: identity, rewards, tasks.

    The full event stream stays in the recording at ``recording_path``.
    """
    builder = (result.run_metadata or {}).get("builder") or {}
    return {
        "task_id": task.id,
        "source_domain": task.source_domain,
        "developer_harness": config.get("developer_harness"),
        "developer_llm": config.get("developer_llm"),
        "developer_llm_args": config.get("developer_llm_args") or {},
        "developer_skills": list(config.get("developer_skills") or []),
        "harness": builder.get("harness"),
        "agent_llm": config.get("agent_llm"),
        "user_llm": config.get("user_llm"),
        "test_task_limit": config.get("test_task_limit", 0),
        "final_test_reward": result.final_test_reward,
        "final_quality_reward": result.final_quality_reward,
        "performance_reward": result.performance_reward,
        "performance_penalty": result.performance_penalty,
        "build_result": (result.run_metadata or {}).get("build_result"),
        "scoring": (result.run_metadata or {}).get("scoring"),
        "test_details": [
            {
                "task_id": d.get("task_id"),
                "reward": d.get("reward"),
                "error": d.get("error"),
                "agent_credit_usage": d.get("agent_credit_usage"),
            }
            for d in (result.test_details or [])
        ],
        "total_outer_steps": result.total_outer_steps,
        "recording_path": str(recording_path),
    }
