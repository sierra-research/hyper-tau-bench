"""Default models for the four LLM seats in a Hyper-τ run.

A Hyper-τ run drives four independently-configured seats:

``developer_llm``
    The Developer agent that builds the domain.
``client_llm``
    The Client persona the Developer interviews.
``agent_llm``
    The built agent under evaluation. Normally supplied by the task's
    performance profile via ``allowed_agent_models`` rather than this default.
``user_llm``
    The inner-loop user simulator that plays the customer while the built
    agent is scored against the held-out test tasks.

The two *simulator* seats (``client_llm`` and ``user_llm``) are deliberately
not pinned to the newest available model. A stronger simulator is not a better
one: ``gpt-5.6-sol`` was measured to over-answer in the client seat,
volunteering adjacent held points (76% ``client_held`` in the telecom
battery), which inflates reward by handing the agent facts it should have had
to elicit. Frontier models belong in
the seats that do work — the Developer, and the ``allowed_agent_models`` of
the performance profiles in :mod:`tau2.hyper.performance_profiles`.

Changing any value here shifts results for every task that does not pin the
field explicitly, so treat edits as horizontal: they break comparability with
previously recorded results.
"""

from typing import Optional

# The Developer seat. Not task-configurable; set with
# `tau2 hyper-tau --developer-llm`.
DEFAULT_DEVELOPER_LLM = "gpt-5.4"

# Fallback for the built agent when a task supplies neither `agent_llm` nor a
# performance profile carrying `allowed_agent_models`.
DEFAULT_AGENT_LLM = "gpt-5.4"

# The two simulator seats. Both are task-configurable (`client_llm` /
# `user_llm`); these apply only when a task leaves the field unset.
DEFAULT_CLIENT_LLM = "gpt-5.5"
DEFAULT_USER_LLM = "gpt-5.5"

# Reasoning effort for the simulator seats, applied only when the task leaves
# the field unset. Every maintained bundle pins `user_reasoning_effort` to
# "none" explicitly and is unaffected.
DEFAULT_CLIENT_REASONING_EFFORT = "low"
DEFAULT_USER_REASONING_EFFORT = "low"


def supports_reasoning_effort(model: str) -> bool:
    """Whether ``reasoning_effort`` is a valid argument for ``model``.

    Mirrors the model-family split the CLI applies when building LLM args:
    the gpt-5 family takes ``reasoning_effort``, Anthropic models take a
    thinking budget instead, and older OpenAI models take neither. Guards the
    seat defaults above so they are never sent to a model that rejects them.
    """
    return model.startswith("gpt-5")


def resolve_simulator_llm_args(
    llm_args: Optional[dict],
    *,
    model: str,
    task_effort: Optional[str],
    default_effort: str,
) -> dict:
    """Merge the reasoning effort for a simulator seat into its LLM args.

    Precedence is explicit ``llm_args``, then the task's pin, then the seat
    default. The default is skipped for models that reject
    ``reasoning_effort`` so an unpinned task on a non-reasoning model keeps
    sending no effort at all.
    """
    resolved = dict(llm_args or {})
    if "reasoning_effort" in resolved:
        return resolved
    effort = task_effort
    if effort is None and supports_reasoning_effort(model):
        effort = default_effort
    if effort:
        resolved["reasoning_effort"] = effort
    return resolved


__all__ = [
    "DEFAULT_AGENT_LLM",
    "DEFAULT_CLIENT_LLM",
    "DEFAULT_CLIENT_REASONING_EFFORT",
    "DEFAULT_DEVELOPER_LLM",
    "DEFAULT_USER_LLM",
    "DEFAULT_USER_REASONING_EFFORT",
    "resolve_simulator_llm_args",
    "supports_reasoning_effort",
]
