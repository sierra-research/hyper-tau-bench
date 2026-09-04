"""
Standalone Client-simulator tooling for the Hyper-τ outer loop.

The :class:`tau2.hyper.client.ClientSimulator` is driven entirely by a
``client_instructions`` system prompt. This package makes that prompt a
rendered, testable artifact instead of hand-authored JSON:

- :mod:`instructions` renders a Client system prompt from section fact
  schemas (persona + held/confirmable knowledge lists + point-back
  behavioral contract).
- :mod:`probes` derives a deterministic probe battery from the same
  schemas (plus an LLM corruption stage for wrong-hypothesis probes).
- :mod:`judge` grades one Client reply against a probe's expected
  behavior with a fixed judging prompt.
- :mod:`runner` runs the battery against a live Client and aggregates a
  per-section scorecard.

Everything is reachable through ``tau2 hyper-client {render,probe}``.
"""

from tau2.hyper.client_sim.instructions import (
    RenderedClientInstructions,
    SectionFacts,
    load_section_facts,
    render_client_instructions,
)

__all__ = [
    "RenderedClientInstructions",
    "SectionFacts",
    "load_section_facts",
    "render_client_instructions",
]
