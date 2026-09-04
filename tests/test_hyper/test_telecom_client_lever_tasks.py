"""Pins for the five authored telecom client-lever coverage tasks.

Authored (privately) from donors in tasks_full.json.
These pins guard against two specific regressions:

1. Re-running the telecom task generator (create_tasks.py) reshuffles its
   random sample and silently drops the appended [LEVER:] tasks — the
   presence pins fail loudly if that happens.
2. The lever content (communicate_info / nl_assertions / reward_basis /
   scenario text) is what makes the corresponding client-held facts
   reward-levered; the content pins keep them from being edited away.
"""

import json

import pytest

from tau2.data_model.tasks import Task
from tau2.utils import DATA_DIR

TELECOM_DIR = DATA_DIR / "tau2" / "domains" / "telecom"

TRANSFER_NOTICE = "YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON."

LEVER_IDS = {
    "transfer_notice": (
        "[service_issue]contract_end_suspension|lock_sim_card_pin"
        "[PERSONA:Hard][LEVER:transfer_notice_exact_text]"
    ),
    "carrier_confirmation": (
        "[mobile_data_issue]user_abroad_roaming_disabled_off"
        "[PERSONA:Hard][LEVER:carrier_change_confirmation]"
    ),
    "final_check": (
        "[mobile_data_issue]data_saver_mode_on|data_usage_exceeded"
        "[PERSONA:Easy][LEVER:close_case_final_check]"
    ),
    "identity": (
        "[service_issue]overdue_bill_suspension"
        "[PERSONA:Easy][LEVER:identity_name_dob_lookup]"
    ),
    "triage": (
        "[service_issue]airplane_mode_on[PERSONA:None][LEVER:multi_complaint_triage]"
    ),
}


@pytest.fixture(scope="module")
def tasks_by_id() -> dict[str, dict]:
    tasks = json.loads((TELECOM_DIR / "tasks.json").read_text())
    return {t["id"]: t for t in tasks}


@pytest.fixture(scope="module")
def lever_tasks(tasks_by_id) -> dict[str, dict]:
    missing = [tid for tid in LEVER_IDS.values() if tid not in tasks_by_id]
    assert not missing, (
        "authored [LEVER:] tasks missing from tasks.json — a generator rerun "
        f"dropped them; restore the committed [LEVER:] tasks: {missing}"
    )
    return {key: tasks_by_id[tid] for key, tid in LEVER_IDS.items()}


def test_lever_tasks_present_everywhere(lever_tasks):
    ids = set(LEVER_IDS.values())

    full_ids = {
        t["id"] for t in json.loads((TELECOM_DIR / "tasks_full.json").read_text())
    }
    assert ids <= full_ids

    splits = json.loads((TELECOM_DIR / "split_tasks.json").read_text())
    assert ids <= set(splits["base"]) and len(splits["base"]) == 119
    assert ids <= set(splits["full"])

    release_dir = DATA_DIR / "tau2" / "hyper" / "tasks"
    telecom_release_files = sorted(release_dir.glob("*_telecom_construction_*.json"))
    assert telecom_release_files
    for task_file in telecom_release_files:
        d = json.loads(task_file.read_text())
        suite = set(d["test_task_ids"]) | set(d.get("live_experiment_task_ids") or [])
        assert ids <= suite, task_file.name
        assert len(suite) == 119, task_file.name


def test_lever_tasks_are_valid_task_models(lever_tasks):
    for task in lever_tasks.values():
        Task(**task)


def test_transfer_notice_lever(lever_tasks):
    ec = lever_tasks["transfer_notice"]["evaluation_criteria"]
    assert ec["communicate_info"] == [TRANSFER_NOTICE]
    assert ec["reward_basis"] == ["ENV_ASSERTION", "ACTION", "COMMUNICATE"]
    # still the unfixable gold: exactly the transfer action
    assert [a["name"] for a in ec["actions"]] == ["transfer_to_human_agents"]


def test_carrier_confirmation_lever(lever_tasks):
    ec = lever_tasks["carrier_confirmation"]["evaluation_criteria"]
    assert ec["reward_basis"] == ["ENV_ASSERTION", "NL_ASSERTION"]
    (assertion,) = ec["nl_assertions"]
    assert "explicit" in assertion and "confirmation" in assertion
    assert any(a["name"] == "enable_roaming" for a in ec["actions"])


def test_final_check_lever(lever_tasks):
    task = lever_tasks["final_check"]
    instr = task["user_scenario"]["instructions"]["task_instructions"]
    # user is satisfied early; the excellent-speed threshold must be gone
    assert "web pages load" in instr
    assert "excellent internet speed and nothing else" not in instr
    # ...but the env assertion still demands excellent — that gap is the lever
    ec = task["evaluation_criteria"]
    assert ec["reward_basis"] == ["ENV_ASSERTION"]
    speed = next(
        a for a in ec["env_assertions"] if a["func_name"] == "assert_internet_speed"
    )
    assert speed["arguments"] == {"expected_speed": 200, "expected_desc": "excellent"}


def test_identity_lever(lever_tasks):
    task = lever_tasks["identity"]
    known = task["user_scenario"]["instructions"]["known_info"]
    assert "phone number 555-123-2002" not in known
    assert "born June 15, 1985" in known
    assert "date of birth" in task["ticket"]
    assert "555-123-2002" not in task["ticket"]
    # identification failure must strand real state: the suspended line + bill
    ec = task["evaluation_criteria"]
    assert ec["reward_basis"] == ["ENV_ASSERTION"]
    assert {a["func_name"] for a in ec["env_assertions"]} >= {
        "assert_service_status",
        "assert_no_overdue_bill",
    }


def test_triage_lever(lever_tasks):
    task = lever_tasks["triage"]
    instr = task["user_scenario"]["instructions"]
    assert "most recent bill" in instr["reason_for_call"]
    assert "do not steer" in instr["task_instructions"]
    ec = task["evaluation_criteria"]
    assert ec["reward_basis"] == ["ENV_ASSERTION", "NL_ASSERTION"]
    (assertion,) = ec["nl_assertions"]
    assert "before" in assertion and "billing" in assertion


def test_lever_tasks_replay_against_reference_env(lever_tasks):
    """Init + gold actions on a fresh env must satisfy every env assertion
    (the same check the authoring script runs)."""
    from tau2.registry import registry

    for task_dict in lever_tasks.values():
        task = Task(**task_dict)
        env = registry.get_env_constructor("telecom")()
        env.set_state(
            initialization_data=task.initial_state.initialization_data,
            initialization_actions=task.initial_state.initialization_actions,
            message_history=[],
        )
        for action in task.evaluation_criteria.actions or []:
            env.make_tool_call(
                action.name, requestor=action.requestor, **action.arguments
            )
            env.sync_tools()
        for assertion in task.evaluation_criteria.env_assertions or []:
            assert env.run_env_assertion(assertion, raise_assertion_error=False), (
                task.id,
                assertion,
            )
