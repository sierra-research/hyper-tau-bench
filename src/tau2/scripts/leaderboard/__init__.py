"""Voice interaction-metrics computation for leaderboard submissions.

The old τ-bench submission tooling (Leaderboard, Submission models,
prepare/verify flows) is not part of the τ^τ-bench release. What remains is
``compute_interaction_metrics`` — the offline interaction-quality panel for
full-duplex voice runs, exposed as ``tau2 submit interaction-metrics``.
"""

from .compute_interaction_metrics import (
    InteractionMetrics,
    InteractionMetricsCounts,
    InteractionMetricsPanel,
    compute_interaction_metrics,
)

__all__ = [
    "InteractionMetrics",
    "InteractionMetricsCounts",
    "InteractionMetricsPanel",
    "compute_interaction_metrics",
]
