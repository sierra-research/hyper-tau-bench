"""Discoverable-call grounding check: equivalence with the reference grading.

The reference banking domain grades discoverable-tool usage via name-keyed
audit rows in ``agent_discoverable_tools`` compared under whole-DB equality;
construction scoring strips that table. These tests pin the trace-level
predicate in ``tau2.hyper.grounding`` to the exact row-set semantics of the
reference mechanism.
"""

import itertools
import json
from pathlib import Path

from tau2.data_model.message import AssistantMessage, ToolCall, ToolMessage
from tau2.data_model.tasks import EvaluationCriteria, RewardType, Task
from tau2.hyper._inner import _apply_discoverable_grounding
from tau2.hyper.data_model import EvaluationResult
from tau2.hyper.grounding import (
    check_discoverable_grounding,
    golden_discoverable_call_names,
    grounding_check_for_simulation,
    observed_discoverable_calls,
)
from tau2.utils.utils import DATA_DIR

BANKING_TASKS_PATH = (
    Path(DATA_DIR) / "tau2" / "domains" / "banking_knowledge" / "tasks.json"
)

READS = frozenset({"get_payment_history_6183", "get_debit_dispute_status_7483"})
WRITES = frozenset({"freeze_debit_card_3892", "order_debit_card_5739"})
DISCOVERABLE = READS | WRITES


def _task(actions: list[dict], reward_basis=None) -> Task:
    return Task(
        id="grounding_test",
        user_scenario={"instructions": "n/a"},
        evaluation_criteria=EvaluationCriteria(
            actions=[
                {
                    "action_id": f"a{i}",
                    "requestor": "assistant",
                    "name": a["name"],
                    "arguments": a.get("arguments", {}),
                }
                for i, a in enumerate(actions)
            ],
            reward_basis=reward_basis or [RewardType.DB],
        ),
    )


def _meta_call(tool_name: str) -> dict:
    return {
        "name": "call_discoverable_agent_tool",
        "arguments": {"agent_tool_name": tool_name, "arguments": "{}"},
    }


def _tool_message(names: list[str], requestor: str = "assistant") -> ToolMessage:
    return ToolMessage(
        id="tm1",
        role="tool",
        requestor="assistant",
        semantic_tool_calls=[
            ToolCall(id=f"sc{i}", name=n, arguments={}, requestor=requestor)
            for i, n in enumerate(names)
        ],
    )


def _reference_row_set(
    golden_names: frozenset[str],
    observed_calls: list[str],
    mutating: frozenset[str],
) -> frozenset[str]:
    """The reference bookkeeping, restated literally.

    ``call_discoverable_agent_tool`` upserts a name-keyed row when the
    underlying tool mutates state or its name is in the allowlist, and the
    runner derives the allowlist as the set of golden discoverable-call
    names (``_derive_read_log_allowlist``).
    """
    allowlist = golden_names
    rows: set[str] = set()
    for name in observed_calls:
        if name in mutating or name in allowlist:
            rows.add(name)
    return frozenset(rows)


def test_required_set_matches_reference_allowlist_derivation():
    """The predicate's required set must equal the runner's allowlist."""
    from tau2.runner.build import _derive_read_log_allowlist

    raw = json.loads(BANKING_TASKS_PATH.read_text())
    tasks = [Task.model_validate(item) for item in raw]
    assert tasks, "banking tasks file must not be empty"
    checked = 0
    for task in tasks:
        expected = frozenset(_derive_read_log_allowlist(task))
        assert golden_discoverable_call_names(task) == expected
        checked += bool(expected)
    assert checked > 0, "expected at least one task with discoverable calls"


def test_predicate_equals_reference_row_grading_on_all_small_cases():
    """Exhaustive parity: predicate == row-set equality for every call mix.

    Enumerates every golden subset and every observed call combination over
    a 4-tool universe (2 reads, 2 writes) and asserts the trace predicate
    agrees with literal row-set comparison in each case.
    """
    universe = sorted(DISCOVERABLE)
    for golden_size in range(len(universe) + 1):
        for golden in itertools.combinations(universe, golden_size):
            golden_set = frozenset(golden)
            for observed_size in range(len(universe) + 1):
                for observed in itertools.combinations(universe, observed_size):
                    observed_calls = list(observed)
                    gold_rows = _reference_row_set(
                        golden_set, sorted(golden_set), WRITES
                    )
                    candidate_rows = _reference_row_set(
                        golden_set, observed_calls, WRITES
                    )
                    check = check_discoverable_grounding(
                        required=golden_set,
                        observed=frozenset(observed_calls),
                        mutating_names=WRITES,
                    )
                    assert check.passed == (candidate_rows == gold_rows), (
                        f"golden={sorted(golden_set)} observed={observed_calls}"
                    )


def test_missing_required_read_fails():
    check = check_discoverable_grounding(
        required=frozenset({"get_payment_history_6183", "freeze_debit_card_3892"}),
        observed=frozenset({"freeze_debit_card_3892"}),
        mutating_names=WRITES,
    )
    assert not check.passed
    assert check.missing == ["get_payment_history_6183"]


def test_extra_unrequired_read_stays_free():
    check = check_discoverable_grounding(
        required=frozenset({"freeze_debit_card_3892"}),
        observed=frozenset({"freeze_debit_card_3892", "get_debit_dispute_status_7483"}),
        mutating_names=WRITES,
    )
    assert check.passed


def test_extra_mutating_call_fails():
    check = check_discoverable_grounding(
        required=frozenset({"freeze_debit_card_3892"}),
        observed=frozenset({"freeze_debit_card_3892", "order_debit_card_5739"}),
        mutating_names=WRITES,
    )
    assert not check.passed
    assert check.extra_mutating == ["order_debit_card_5739"]


def test_observed_extraction_keeps_assistant_discoverable_calls_only():
    messages = [
        AssistantMessage(role="assistant", content="on it"),
        _tool_message(["get_payment_history_6183", "get_user_information_by_id"]),
        _tool_message(["get_debit_dispute_status_7483"], requestor="user"),
    ]
    observed = observed_discoverable_calls(messages, DISCOVERABLE)
    assert observed == frozenset({"get_payment_history_6183"})


def test_no_required_and_no_extra_mutating_is_exempt():
    task = _task([{"name": "log_verification", "arguments": {}}])
    check = grounding_check_for_simulation(
        task,
        [_tool_message(["get_payment_history_6183"])],
        discoverable_names=DISCOVERABLE,
        mutating_names=WRITES,
    )
    assert check is None


def test_apply_zeroes_reward_for_db_basis_tasks():
    task = _task([_meta_call("get_payment_history_6183")])
    result = EvaluationResult(
        task_id=task.id,
        reward=1.0,
        messages=[_tool_message([])],
        reward_breakdown={"DB": 1.0},
    )
    _apply_discoverable_grounding(result, task, (DISCOVERABLE, WRITES))
    assert result.reward == 0.0
    assert result.reward_breakdown["GROUNDING"] == 0.0
    assert result.grounding_details["missing"] == ["get_payment_history_6183"]


def test_apply_leaves_non_db_basis_rewards_alone():
    task = _task(
        [_meta_call("get_payment_history_6183")],
        reward_basis=[RewardType.ACTION],
    )
    result = EvaluationResult(
        task_id=task.id,
        reward=1.0,
        messages=[_tool_message([])],
    )
    _apply_discoverable_grounding(result, task, (DISCOVERABLE, WRITES))
    assert result.reward == 1.0
    assert result.grounding_details is not None


def test_domains_without_the_meta_tool_are_exempt():
    """Only domains that graded via audit rows get the restated check."""
    from tau2.hyper.grounding import reference_discoverable_classification

    for domain in ("airline_plus", "retail_plus", "telecom"):
        discoverable, mutating = reference_discoverable_classification(domain)
        assert discoverable == frozenset(), domain
        assert mutating == frozenset(), domain


def test_apply_records_pass_without_touching_reward():
    task = _task([_meta_call("freeze_debit_card_3892")])
    result = EvaluationResult(
        task_id=task.id,
        reward=1.0,
        messages=[_tool_message(["freeze_debit_card_3892"])],
        reward_breakdown={"DB": 1.0},
    )
    _apply_discoverable_grounding(result, task, (DISCOVERABLE, WRITES))
    assert result.reward == 1.0
    assert result.reward_breakdown["GROUNDING"] == 1.0
    assert result.grounding_details["passed"] is True
