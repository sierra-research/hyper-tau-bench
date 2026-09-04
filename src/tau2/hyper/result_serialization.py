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
