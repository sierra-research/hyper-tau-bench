"""Gates for the airline_plus domain.

airline_plus was originally derived from canonical airline according to
data/tau2/domains/airline_plus/delta_spec.yaml. Since the 2026-08-04
standalone cutover the committed files are
edited directly. These tests enforce:

1. Leakage: canonical ids, emails, name tokens, and retired policy phrases
   must not appear in the committed files. The canonical token universe is
   read off the committed canonical corpus (see tests/plus_support/) and the
   retired phrases are pinned literals; nothing is regenerated or diffed.
2. Solvability: every gold write action replays cleanly against the environment.
3. Discrimination (canonical ghost): for every value the spec changes, the
   committed gold amounts must equal what the new value produces and differ
   from what the canonical value would produce, on at least one task.
4. No canonical leakage: canonical fee/limit phrases must not survive in the
   policy, and communicate_info strings must not collide with other numeric
   tokens in the same task.
"""

import json
import re
from pathlib import Path

import pytest
import yaml
from plus_support import airline_plus as expectations

from tau2.domains.airline_plus.environment import get_environment, get_tasks
from tau2.domains.airline_plus.tools import AirlinePlusTools
from tau2.registry import registry
from tau2.utils.utils import DATA_DIR

REPO_ROOT = Path(__file__).resolve().parents[3]
PLUS_DIR = Path(DATA_DIR) / "tau2" / "domains" / "airline_plus"

READ_ONLY_TOOLS = {
    "get_user_details",
    "get_reservation_details",
    "get_flight_status",
    "search_direct_flight",
    "search_onestop_flight",
    "list_all_airports",
    "calculate",
    "transfer_to_human_agents",
}


@pytest.fixture(scope="module")
def spec():
    return yaml.safe_load((PLUS_DIR / "delta_spec.yaml").read_text())


@pytest.fixture(scope="module")
def committed_tasks():
    return json.loads((PLUS_DIR / "tasks.json").read_text())


@pytest.fixture(scope="module")
def committed_db():
    return json.loads((PLUS_DIR / "db.json").read_text())


def _gold_actions(task: dict) -> list:
    return (task.get("evaluation_criteria") or {}).get("actions") or []


def _write_actions(task: dict) -> list:
    return [a for a in _gold_actions(task) if a["name"] not in READ_ONLY_TOOLS]


def _matrix(spec: dict, side: str) -> dict:
    """The free-checked-bag matrix on one side of the delta spec."""
    return {
        tier: cells[side] for tier, cells in spec["baggage_allowance"].items()
    }


def _gold_bookings(committed_tasks: list):
    """(task id, book_reservation arguments, total charged by the gold)."""
    for task in committed_tasks:
        for action in _gold_actions(task):
            if action["name"] != "book_reservation":
                continue
            args = action["arguments"]
            yield (
                task["id"],
                args,
                sum(method["amount"] for method in args["payment_methods"]),
            )


# ---------------------------------------------------------------------------
# 1. Leakage + spec consistency
# ---------------------------------------------------------------------------


def test_committed_outputs_carry_no_canonical_tokens():
    """Canonical ids, emails, name tokens, and retired policy phrases must not
    appear in the committed files. Standalone replacement for the retired
    freshness pin: airline_plus is edited directly, so the scan targets the
    committed files themselves."""
    tokens = expectations.canonical_identifier_tokens()
    # Guard the guard: an empty token family would make the scan below pass
    # for the wrong reason.
    assert set(tokens) == {
        "user_id",
        "reservation_id",
        "payment_id",
        "email",
        "flight",
        "dob",
    }
    for label, family in tokens.items():
        assert family, f"no canonical {label} tokens to scan for"
    assert expectations.RETIRED_POLICY_PHRASES
    assert expectations.collect_committed_leakage() == []


def test_tools_match_spec(spec):
    assert AirlinePlusTools.EXTRA_BAGGAGE_FEE == spec["fees"]["extra_baggage_fee"]["new"]
    assert (
        AirlinePlusTools.INSURANCE_FEE_PER_PASSENGER
        == spec["fees"]["insurance_fee_per_passenger"]["new"]
    )
    ids = spec["identifiers"]
    assert AirlinePlusTools.NEW_RESERVATION_IDS == ids["new_reservation_ids"]["new"]
    assert AirlinePlusTools.NEW_PAYMENT_IDS == ids["new_payment_ids"]["new"]


def test_registered():
    assert "airline_plus" in registry.get_domains()
    assert "airline_plus" in registry.get_task_sets()


def test_splits_cover_all_tasks(committed_tasks):
    """base keeps canonical structure (all tasks); the 17 new tasks (50-62
    from the generator era, 63-66 added post-cutover in Phase C) live in both
    base and test, never train."""
    splits = json.loads((PLUS_DIR / "split_tasks.json").read_text())
    ids = {t["id"] for t in committed_tasks}
    new_ids = {str(i) for i in range(50, 67)}
    assert set(splits["base"]) == ids
    assert set(splits["test"]) <= ids
    assert new_ids <= set(splits["base"])
    assert new_ids <= set(splits["test"])
    assert not new_ids & set(splits["train"])


# ---------------------------------------------------------------------------
# 2. Solvability: gold actions replay against the environment
# ---------------------------------------------------------------------------


def test_gold_actions_replay(committed_tasks):
    failures = []
    for task in committed_tasks:
        env = get_environment()
        for action in _write_actions(task):
            try:
                env.make_tool_call(
                    action["name"],
                    requestor="assistant",
                    **(action.get("arguments") or {}),
                )
            except Exception as exc:  # noqa: BLE001 - collecting all failures
                failures.append(f"{task['id']}/{action['action_id']}: {exc}")
    assert not failures, "\n".join(failures)


def test_task_loader_returns_all_tasks():
    assert len(get_tasks(None)) == 67


# ---------------------------------------------------------------------------
# 3. Canonical-ghost discrimination
# ---------------------------------------------------------------------------


def test_ghost_extra_baggage_fee(spec, committed_tasks, committed_db):
    """Every gold booking total is the one the plus extra-bag fee produces,
    and at least one of them moves if the canonical fee is used instead.

    A memorized-fee agent quotes and charges the wrong amount on the
    witnessing tasks.
    """
    matrix = _matrix(spec, "new")
    insurance_fee = spec["fees"]["insurance_fee_per_passenger"]["new"]
    new_fee = spec["fees"]["extra_baggage_fee"]["new"]
    old_fee = spec["fees"]["extra_baggage_fee"]["old"]
    witnesses = []
    for task_id, args, gold_total in _gold_bookings(committed_tasks):
        true_total = expectations.booking_total(
            committed_db,
            args,
            bag_fee=new_fee,
            insurance_fee=insurance_fee,
            matrix=matrix,
        )
        ghost_total = expectations.booking_total(
            committed_db,
            args,
            bag_fee=old_fee,
            insurance_fee=insurance_fee,
            matrix=matrix,
        )
        assert gold_total == true_total, (
            f"task {task_id}: gold charges {gold_total}, plus values give"
            f" {true_total}"
        )
        if ghost_total != true_total:
            witnesses.append(task_id)
    assert witnesses, f"canonical ${old_fee} bag fee is not caught by any task"


def test_ghost_insurance_fee(spec, committed_tasks, committed_db):
    """Same shape as the bag-fee gate for the per-passenger insurance fee."""
    matrix = _matrix(spec, "new")
    bag_fee = spec["fees"]["extra_baggage_fee"]["new"]
    new_fee = spec["fees"]["insurance_fee_per_passenger"]["new"]
    old_fee = spec["fees"]["insurance_fee_per_passenger"]["old"]
    witnesses = []
    for task_id, args, gold_total in _gold_bookings(committed_tasks):
        true_total = expectations.booking_total(
            committed_db,
            args,
            bag_fee=bag_fee,
            insurance_fee=new_fee,
            matrix=matrix,
        )
        ghost_total = expectations.booking_total(
            committed_db,
            args,
            bag_fee=bag_fee,
            insurance_fee=old_fee,
            matrix=matrix,
        )
        assert gold_total == true_total, (
            f"task {task_id}: gold charges {gold_total}, plus values give"
            f" {true_total}"
        )
        if ghost_total != true_total:
            witnesses.append(task_id)
    assert witnesses, (
        f"canonical ${old_fee} insurance fee is not caught by any task"
    )


def test_ghost_baggage_matrix_cells(spec, committed_tasks, committed_db):
    """Every changed allowance cell must be witnessed by at least one task.

    A cell is witnessed when some gold priced against it (a booking's charged
    total, or a baggage update's chargeable-bag count) differs under the
    canonical allowance. Both sides also pin the committed gold to the plus
    matrix, so a cell cannot be "witnessed" by a stale value.

    silver/basic_economy is witnessed manually (see
    test_ghost_silver_basic_allowance): task 24's gold books 0 bags because the
    new allowance is 0, while the scenario tells the user to use their full
    free allowance, so a canonical-matrix agent books 1 bag.
    """
    new_matrix = _matrix(spec, "new")
    old_matrix = _matrix(spec, "old")
    bag_fee = spec["fees"]["extra_baggage_fee"]["new"]
    insurance_fee = spec["fees"]["insurance_fee_per_passenger"]["new"]
    witnessed = set()

    for task_id, args, gold_total in _gold_bookings(committed_tasks):
        cell = (committed_db["users"][args["user_id"]]["membership"], args["cabin"])
        totals = {
            side: expectations.booking_total(
                committed_db,
                args,
                bag_fee=bag_fee,
                insurance_fee=insurance_fee,
                matrix=matrix,
            )
            for side, matrix in (("new", new_matrix), ("old", old_matrix))
        }
        assert gold_total == totals["new"], task_id
        if totals["old"] != totals["new"]:
            witnessed.add(cell)

    for task in committed_tasks:
        for action in _gold_actions(task):
            if action["name"] != "update_reservation_baggages":
                continue
            membership, cabin, passengers = expectations.baggage_update_context(
                committed_db, task, action
            )
            bags = action["arguments"]["total_baggages"]
            counts = {
                side: max(
                    0,
                    bags
                    - expectations.allowance(matrix, membership, cabin) * passengers,
                )
                for side, matrix in (("new", new_matrix), ("old", old_matrix))
            }
            assert action["arguments"]["nonfree_baggages"] == counts["new"], (
                f"task {task['id']}: gold charges for"
                f" {action['arguments']['nonfree_baggages']} bags, the plus"
                f" matrix gives {counts['new']}"
            )
            if counts["old"] != counts["new"]:
                witnessed.add((membership, cabin))

    changed = {
        (membership, expectations.CABINS[index])
        for membership, cells in spec["baggage_allowance"].items()
        for index in range(len(expectations.CABINS))
        if cells["old"][index] != cells["new"][index]
    } - {("silver", "basic_economy")}
    assert changed, "delta spec changes no allowance cell"
    uncovered = sorted(f"{tier}/{cabin}" for tier, cabin in changed - witnessed)
    assert not uncovered, f"allowance cells with no witnessing task: {uncovered}"


def test_ghost_silver_basic_allowance(spec, committed_tasks):
    """Task 24: silver member on basic economy told to use their full free
    allowance. New allowance is 0 (gold books no bags); the canonical allowance
    is 1, so a ghost agent adds a bag and diverges on total_baggages."""
    assert spec["baggage_allowance"]["silver"]["new"][0] == 0
    assert spec["baggage_allowance"]["silver"]["old"][0] == 1
    task = next(t for t in committed_tasks if t["id"] == "24")
    book = next(a for a in _gold_actions(task) if a["name"] == "book_reservation")
    assert book["arguments"]["total_baggages"] == 0
    assert "free baggage allowance" in json.dumps(task["user_scenario"])


def test_ghost_compensation_amounts(spec, committed_tasks, committed_db):
    """send_certificate gold amounts must differ from what the canonical
    compensation rates would produce for the same passenger counts."""
    witnesses = {
        # task id -> (rate kind, host reservation pax count)
        "50": ("delayed_flight_per_passenger", 1),
        "51": ("cancelled_flight_per_passenger", 2),
        "62": ("delayed_flight_per_passenger", 4),
    }
    for tid, (kind, n_pax) in witnesses.items():
        task = next(t for t in committed_tasks if t["id"] == tid)
        cert = next(a for a in _gold_actions(task) if a["name"] == "send_certificate")
        new_amount = spec["compensation"][kind]["new"] * n_pax
        old_amount = spec["compensation"][kind]["old"] * n_pax
        assert cert["arguments"]["amount"] == new_amount
        assert cert["arguments"]["amount"] != old_amount


def test_ghost_refund_window(committed_tasks):
    policy = (PLUS_DIR / "policy.md").read_text()
    assert "within 12 business days" in policy
    assert "5 to 7 business days" not in policy
    task = next(t for t in committed_tasks if t["id"] == "59")
    assert task["evaluation_criteria"]["communicate_info"] == ["12 business days"]


def test_ghost_gift_card_cap(committed_tasks, committed_db):
    """Task 53: the user asks to pay with both gift cards plus a credit card.
    Under the new 1-gift-card cap the gold uses 2 payment methods; a ghost
    agent applying the canonical 3-gift-card cap would use 3."""
    task = next(t for t in committed_tasks if t["id"] == "53")
    book = next(a for a in _gold_actions(task) if a["name"] == "book_reservation")
    gold_methods = book["arguments"]["payment_methods"]
    assert len(gold_methods) == 2

    user = committed_db["users"][book["arguments"]["user_id"]]
    gift_cards = [
        pid
        for pid, m in user["payment_methods"].items()
        if m["source"] == "gift_card"
    ]
    credit_card = gold_methods[-1]["payment_id"]
    total = sum(m["amount"] for m in gold_methods)
    ghost_plan = sorted(
        gift_cards, key=lambda pid: -user["payment_methods"][pid]["amount"]
    ) + [credit_card]
    ghost_methods = expectations.split_payment(
        committed_db, book["arguments"]["user_id"], ghost_plan, total
    )
    assert len(ghost_methods) == 3
    assert ghost_methods != gold_methods


def test_ghost_max_passengers(committed_tasks, committed_db):
    """Task 54: the user demands one reservation for five people and books
    nothing otherwise. A ghost agent applying the canonical 5-passenger limit
    can and would book (seats exist), diverging from the empty gold."""
    task = next(t for t in committed_tasks if t["id"] == "54")
    assert _gold_actions(task) == []
    seats = [
        day["available_seats"]["economy"]
        for flight in committed_db["flights"].values()
        if flight["origin"] == "PHX" and flight["destination"] == "LAS"
        for date, day in flight["dates"].items()
        if date == "2024-05-25" and day.get("status") == "available"
    ]
    assert any(s >= 5 for s in seats)


# ---------------------------------------------------------------------------
# 4. Leakage and collision scans
# ---------------------------------------------------------------------------


def test_no_canonical_value_phrases_in_policy():
    policy = (PLUS_DIR / "policy.md").read_text()
    for phrase in (
        "50 dollars",
        "30 dollars per passenger",
        "$100 times",
        "$50 times",
        "at most five passengers",
        "at most three gift cards",
        "5 to 7 business days",
        "3 free checked bags for each business passenger",
    ):
        assert phrase not in policy, f"canonical phrase leaked: {phrase!r}"


def test_no_canonical_flight_prefix(committed_tasks, committed_db):
    blob = json.dumps(committed_tasks) + json.dumps(committed_db)
    assert not re.search(r"\bHAT\d{3}\b", blob)


def test_communicate_info_collisions(committed_tasks):
    """A numeric communicate_info string must not appear as a substring of any
    other numeric token in the same task's gold arguments or scenario text
    (the evaluator does substring matching over the transcript)."""
    for task in committed_tasks:
        comm = (task.get("evaluation_criteria") or {}).get("communicate_info") or []
        numeric_comm = [c for c in comm if re.fullmatch(r"\d+", c)]
        if not numeric_comm:
            continue
        blob = json.dumps(_gold_actions(task)) + json.dumps(task["user_scenario"])
        tokens = set(re.findall(r"\d+(?:\.\d+)?", blob))
        for c in numeric_comm:
            hosts = [t for t in tokens if c in t and t != c]
            assert not hosts, (
                f"task {task['id']}: communicate value {c!r} is a substring of "
                f"other numeric tokens {hosts}"
            )
