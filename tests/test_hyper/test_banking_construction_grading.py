"""Banking construction hashes must ignore wrapper logs in both DB views."""

from copy import deepcopy

import pytest

from tau2.data_model.tasks import EvaluationCriteria, RewardType, Task
from tau2.domains.banking_knowledge.data_model import DatabaseTable, TransactionalDB
from tau2.environment.environment import Environment
from tau2.environment.toolkit import ToolKitBase
from tau2.evaluator.evaluator_env import (
    EnvironmentEvaluator,
    FullDuplexEnvironmentEvaluator,
    _hashes_for_compare,
)


def _environment(*, audit=False, shared=True):
    db = TransactionalDB(
        accounts=DatabaseTable(
            data={"account_1": {"account_id": "account_1", "balance": 100.0}}
        ),
        agent_discoverable_tools=DatabaseTable(
            data={
                "audit_1": {"tool_name": "open_bank_account_4821", "status": "CALLED"}
            }
            if audit
            else {}
        ),
    )
    return Environment(
        domain_name="banking_knowledge",
        policy="",
        tools=ToolKitBase(db),
        user_tools=ToolKitBase(db if shared else deepcopy(db)),
    )


@pytest.mark.parametrize("shared", [True, False], ids=["shared-db", "separate-dbs"])
@pytest.mark.parametrize("predicted_audit,gold_audit", [(False, True), (True, False)])
def test_audit_only_difference_matches_both_views_without_mutation(
    shared, predicted_audit, gold_audit
):
    predicted = _environment(audit=predicted_audit, shared=shared)
    gold = _environment(audit=gold_audit, shared=shared)
    before = [
        toolkit.db.model_dump()
        for env in (predicted, gold)
        for toolkit in (env.tools, env.user_tools)
    ]

    agent, predicted_agent, user, predicted_user = _hashes_for_compare(
        predicted, gold, normalize=True
    )

    assert agent == predicted_agent
    assert user == predicted_user
    assert before == [
        toolkit.db.model_dump()
        for env in (predicted, gold)
        for toolkit in (env.tools, env.user_tools)
    ]
    assert (predicted.tools.db is predicted.user_tools.db) == shared
    assert (gold.tools.db is gold.user_tools.db) == shared


def test_standard_banking_grading_still_compares_audit_rows():
    agent, predicted_agent, user, predicted_user = _hashes_for_compare(
        _environment(), _environment(audit=True), normalize=False
    )
    assert agent != predicted_agent
    assert user != predicted_user


@pytest.mark.parametrize("view", ["tools", "user_tools"])
@pytest.mark.parametrize(
    "change", ["balance", "missing_account", "user_discoverable_tools"]
)
def test_real_state_differences_still_fail(view, change):
    predicted = _environment(shared=False)
    gold = _environment(audit=True, shared=False)
    db = getattr(predicted, view).db
    if change == "balance":
        db.accounts.data["account_1"]["balance"] = 99.0
    elif change == "missing_account":
        db.accounts.data.clear()
    else:
        db.user_discoverable_tools.data["user_tool_1"] = {"status": "AVAILABLE"}

    agent, predicted_agent, user, predicted_user = _hashes_for_compare(
        predicted, gold, normalize=True
    )
    if view == "tools":
        assert agent != predicted_agent
        assert user == predicted_user
    else:
        assert agent == predicted_agent
        assert user != predicted_user


@pytest.mark.parametrize(
    "evaluator", [EnvironmentEvaluator, FullDuplexEnvironmentEvaluator]
)
@pytest.mark.parametrize("wrong_balance", [False, True])
def test_evaluator_checks_shared_banking_db(evaluator, wrong_balance):
    # Explicit actions=[] exercises DB scoring; actions=None returns early.
    task = Task(
        id="shared_banking_db",
        user_scenario={"instructions": "Account state is already correct."},
        evaluation_criteria=EvaluationCriteria(
            actions=[], reward_basis=[RewardType.DB]
        ),
    )

    def predicted_constructor(**_kwargs):
        env = _environment()
        if wrong_balance:
            env.tools.db.accounts.data["account_1"]["balance"] = 99.0
        return env

    reward = evaluator.calculate_reward(
        environment_constructor=predicted_constructor,
        gold_environment_constructor=lambda **_kwargs: _environment(audit=True),
        task=task,
        full_trajectory=[],
    )
    assert reward.reward == (0.0 if wrong_balance else 1.0)
    assert reward.db_check.db_match == (not wrong_balance)


@pytest.fixture(scope="module")
def banking_base_environment():
    from tau2.domains.banking_knowledge.environment import get_db
    from tau2.domains.banking_knowledge.tools import KnowledgeTools, KnowledgeUserTools

    db = get_db()
    return Environment(
        domain_name="banking_knowledge",
        policy="",
        tools=KnowledgeTools(db),
        user_tools=KnowledgeUserTools(db),
    )


def _banking_tasks():
    from tau2.domains.banking_knowledge.environment import get_tasks

    tasks = get_tasks()
    assert len(tasks) == 144, "Review the corpus-wide regression when tasks change"
    return tasks


@pytest.mark.parametrize("task", _banking_tasks(), ids=lambda task: task.id)
def test_all_banking_gold_states_accept_absent_wrapper_logs(
    task, banking_base_environment
):
    """Isolate audit bookkeeping from every shipped reference final state.

    This is DB-comparison coverage, not a claim that all golden actions or
    natural-language assertions are correct. It requires no model/API calls.
    """
    gold = deepcopy(banking_base_environment)
    initial = task.initial_state
    if initial is not None:
        gold.set_state(
            initialization_data=initial.initialization_data,
            initialization_actions=initial.initialization_actions,
            message_history=list(initial.message_history or []),
        )
    for action in task.evaluation_criteria.actions or []:
        gold.make_tool_call(action.name, requestor=action.requestor, **action.arguments)

    predicted = deepcopy(gold)
    predicted.tools.db.agent_discoverable_tools.data.clear()
    assert predicted.tools.db is predicted.user_tools.db
    assert gold.tools.db is gold.user_tools.db
    agent, predicted_agent, user, predicted_user = _hashes_for_compare(
        predicted, gold, normalize=True
    )
    assert agent == predicted_agent
    assert user == predicted_user
