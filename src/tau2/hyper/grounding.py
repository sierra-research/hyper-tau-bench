"""Discoverable-call grounding check for Client REST construction scoring.

The reference banking domain grades discoverable-tool usage through DB
bookkeeping: ``call_discoverable_agent_tool`` upserts a name-keyed
``{"tool_name": X, "status": "CALLED"}`` row for every state-mutating call
plus every read named by the task's allowlist, and whole-DB equality then
compares the row sets. Construction scoring strips that table from both
sides (``_drop_construction_agent_audit_tables``) because no kit artifact
communicates the logging convention — which also silently dropped the
"agent actually performed its required reads" assertion.

This module re-states the row-set comparison as a trace-level predicate so
Client REST construction tasks recover the original grading without any
Developer-side bookkeeping. The equivalence rests on three properties of
the reference mechanism:

1. Rows are keyed by tool name only, and upserted — call multiplicity and
   arguments never influenced the row set.
2. The read allowlist is derived from the task's own golden trajectory
   (``_derive_read_log_allowlist``), so "reads that get logged" is exactly
   "reads the gold trace calls".
3. A row is written only when the underlying method actually executed —
   rejected calls (unknown tool, bad arguments) never logged.

Therefore the original row-set equality reduces to::

    {observed mutating} | {observed & required}  ==  {required}

where ``required`` is the set of ``agent_tool_name`` values in golden
``call_discoverable_agent_tool`` actions and ``observed`` is the set of
canonical operations the trusted runtime executed (surfaced per tool
response as ``ToolMessage.semantic_tool_calls``). Extra reads outside the
golden set stay free, exactly as the allowlist intended.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Optional

from pydantic import BaseModel, Field

from tau2.data_model.message import Message, ToolMessage
from tau2.environment.toolkit import DISCOVERABLE_ATTR, MUTATES_STATE_ATTR

if TYPE_CHECKING:
    from tau2.data_model.tasks import Task

DISCOVERABLE_CALL_ACTION = "call_discoverable_agent_tool"


class GroundingCheck(BaseModel):
    """Outcome of the discoverable-call grounding predicate for one task."""

    passed: bool
    required: list[str] = Field(default_factory=list)
    observed: list[str] = Field(default_factory=list)
    missing: list[str] = Field(
        default_factory=list,
        description="Golden discoverable calls the agent never made.",
    )
    extra_mutating: list[str] = Field(
        default_factory=list,
        description="Mutating discoverable calls outside the golden set.",
    )


def golden_discoverable_call_names(task: "Task") -> frozenset[str]:
    """Tool names named by the task's golden discoverable-call actions.

    Mirrors ``tau2.runner.build._derive_read_log_allowlist`` (which the
    reference runner feeds to the banking toolkit); a parity test pins the
    two together.
    """
    names: set[str] = set()
    if task.evaluation_criteria is None:
        return frozenset()
    for action in task.evaluation_criteria.actions or []:
        if action.name == DISCOVERABLE_CALL_ACTION:
            name = (action.arguments or {}).get("agent_tool_name")
            if name:
                names.add(name)
    return frozenset(names)


def observed_discoverable_calls(
    messages: Iterable[Message],
    discoverable_names: frozenset[str],
) -> frozenset[str]:
    """Discoverable operations the trusted runtime executed for the assistant.

    Reads the ``semantic_tool_calls`` annotations the sealed Client REST
    environment attaches to each tool response — the host-owned record of
    canonical operations, which Developer code cannot forge.
    """
    observed: set[str] = set()
    for message in messages:
        if not isinstance(message, ToolMessage):
            continue
        for call in message.semantic_tool_calls or []:
            if call.requestor != "assistant":
                continue
            if call.name in discoverable_names:
                observed.add(call.name)
    return frozenset(observed)


def reference_discoverable_classification(
    domain: str,
) -> tuple[frozenset[str], frozenset[str]]:
    """(all discoverable tool names, the mutating subset) for a domain.

    Builds one reference environment through the registry; callers should
    invoke this once per scoring run, not per simulation.
    """
    from tau2.registry import registry

    constructor = registry.get_env_constructor(domain)
    try:
        # Discoverable tools live on the core toolkit; skip retrieval-layer
        # construction (embedding pipelines) where the domain supports it.
        environment = constructor(retrieval_variant="no_knowledge")
    except TypeError:
        environment = constructor()
    tools = environment.tools
    if tools is None:
        return frozenset(), frozenset()
    if not tools.has_tool(DISCOVERABLE_CALL_ACTION):
        # The row bookkeeping this check restates exists only in domains
        # with the discoverable-call meta-tool (banking). Domains without it
        # never graded discoverable usage through audit rows, so adding the
        # predicate there would tighten their grading, not restore it.
        return frozenset(), frozenset()
    discoverable = {}
    for name, method in tools.tools.items():
        if getattr(method, DISCOVERABLE_ATTR, False):
            discoverable[name] = bool(getattr(method, MUTATES_STATE_ATTR, False))
    return (
        frozenset(discoverable),
        frozenset(name for name, mutates in discoverable.items() if mutates),
    )


def check_discoverable_grounding(
    *,
    required: frozenset[str],
    observed: frozenset[str],
    mutating_names: frozenset[str],
) -> GroundingCheck:
    """Evaluate the row-set predicate the reference DB bookkeeping encoded.

    The candidate row set is mutating calls plus required reads actually
    made; the golden row set is every golden discoverable call (mutating
    calls always logged, golden reads allowlisted by construction).
    """
    candidate_rows = (observed & mutating_names) | (observed & required)
    return GroundingCheck(
        passed=candidate_rows == required,
        required=sorted(required),
        observed=sorted(observed),
        missing=sorted(required - candidate_rows),
        extra_mutating=sorted((observed & mutating_names) - required),
    )


def grounding_check_for_simulation(
    task: "Task",
    messages: Iterable[Message],
    *,
    discoverable_names: frozenset[str],
    mutating_names: frozenset[str],
) -> Optional[GroundingCheck]:
    """Run the grounding predicate for one simulated task.

    Returns ``None`` when the task's gold trace makes no discoverable calls
    and the agent triggered no mutating discoverable operations — the
    reference bookkeeping would have left the table empty on both sides.
    """
    required = golden_discoverable_call_names(task)
    observed = observed_discoverable_calls(messages, discoverable_names)
    check = check_discoverable_grounding(
        required=required,
        observed=observed,
        mutating_names=mutating_names,
    )
    if not required and not check.extra_mutating:
        return None
    return check
