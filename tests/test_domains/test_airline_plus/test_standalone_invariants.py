"""Intrinsic committed-tree invariants for airline_plus (hardening plan PR B).

The standalone cutover dropped the
regenerate-and-compare pins, so the committed tree needs gates that hold on
its own. Each test here pins a property a confirmed audit defect violated:

- the payment-history component invariant (pre-rebuild: 332/2030 held,
  histories were floor(1.2 x canonical) with a divide-by-1.2 tell);
- task id grounding (pre-fix: task 35's truncated ``credit_card_907483``
  grounded nowhere);
- nl_assertion amount disjointness from canonical (pre-fix: ten tasks
  carried canonical dollar amounts verbatim);
- canonical-id disjointness and referential integrity (the de-memorization
  contract the domain exists for).

Canonical airline files are read ONLY as a frozen oracle; nothing here
re-derives the plus tree from them.
"""

import json
import re
from pathlib import Path

import pytest
import yaml

from tau2.utils.utils import DATA_DIR

PLUS_DIR = Path(DATA_DIR) / "tau2" / "domains" / "airline_plus"
AIRLINE_DIR = Path(DATA_DIR) / "tau2" / "domains" / "airline"


@pytest.fixture(scope="module")
def spec():
    return yaml.safe_load((PLUS_DIR / "delta_spec.yaml").read_text())


@pytest.fixture(scope="module")
def plus_db():
    return json.loads((PLUS_DIR / "db.json").read_text())


@pytest.fixture(scope="module")
def canonical_db():
    return json.loads((AIRLINE_DIR / "db.json").read_text())


@pytest.fixture(scope="module")
def plus_tasks():
    return json.loads((PLUS_DIR / "tasks.json").read_text())


@pytest.fixture(scope="module")
def canonical_tasks():
    return json.loads((AIRLINE_DIR / "tasks.json").read_text())


def _recompute(reservation, insurance_fee, bag_fee):
    pax = len(reservation.get("passengers", []))
    total = sum(f.get("price", 0) for f in reservation.get("flights", [])) * pax
    if reservation.get("insurance") == "yes":
        total += insurance_fee * pax
    total += bag_fee * reservation.get("nonfree_baggages", 0)
    return total


def test_payment_history_component_invariant(plus_db, spec):
    """Net paid == flights x pax + insurance + bag fees, under the PLUS fee
    schedule, for every reservation (full-refund pairs net to zero with each
    leg equal to the recompute). Canonical satisfies the same identity under
    canonical fees; the original 1.2-scaled histories satisfied it for only
    332/2030."""
    ins = spec["fees"]["insurance_fee_per_passenger"]["new"]
    bag = spec["fees"]["extra_baggage_fee"]["new"]
    violations = []
    for rid, res in plus_db["reservations"].items():
        expected = _recompute(res, ins, bag)
        history = res["payment_history"]
        net = sum(e["amount"] for e in history)
        full_refund = (
            len(history) == 2
            and history[0]["amount"] == -history[1]["amount"] == expected
        )
        if not (net == expected or full_refund):
            violations.append(f"{rid}: net {net} != {expected} {history}")
    assert not violations, "\n".join(violations[:10])


def test_flight_prefix_universality(plus_db):
    for flight_id, flight in plus_db["flights"].items():
        assert re.fullmatch(r"MER\d+", flight_id), flight_id
        assert flight["flight_number"] == flight_id, flight_id
    for rid, res in plus_db["reservations"].items():
        for leg in res["flights"]:
            assert re.fullmatch(r"MER\d+", leg["flight_number"]), (
                f"{rid}: {leg['flight_number']}"
            )


def test_referential_integrity(plus_db):
    users = plus_db["users"]
    reservations = plus_db["reservations"]
    problems = []
    for rid, res in reservations.items():
        user = users.get(res["user_id"])
        if user is None:
            problems.append(f"{rid}: user {res['user_id']} missing")
            continue
        if rid not in user.get("reservations", []):
            problems.append(f"{rid}: not listed on {res['user_id']}")
        for entry in res["payment_history"]:
            if entry["payment_id"] not in user.get("payment_methods", {}):
                problems.append(
                    f"{rid}: payment {entry['payment_id']} not a method of "
                    f"{res['user_id']}"
                )
        for leg in res["flights"]:
            if leg["flight_number"] not in plus_db["flights"]:
                problems.append(f"{rid}: unknown flight {leg['flight_number']}")
    for uid, user in users.items():
        for rid in user.get("reservations", []):
            if rid not in reservations:
                problems.append(f"{uid}: dangling reservation {rid}")
            elif reservations[rid]["user_id"] != uid:
                problems.append(f"{uid}: reservation {rid} owned by someone else")
    assert not problems, "\n".join(problems[:10])


def test_cabin_price_ordering(plus_db):
    for flight_id, flight in plus_db["flights"].items():
        for date, day in flight["dates"].items():
            prices = day.get("prices")
            if not prices:
                continue
            assert (
                prices["basic_economy"] <= prices["economy"] <= prices["business"]
            ), f"{flight_id} {date}: {prices}"


def test_ids_disjoint_from_canonical(plus_db, canonical_db):
    for key in ("reservations", "users"):
        overlap = set(plus_db[key]) & set(canonical_db[key])
        assert not overlap, f"{key} ids shared with canonical: {sorted(overlap)[:5]}"
    plus_emails = {u.get("email") for u in plus_db["users"].values()} - {None}
    canon_emails = {u.get("email") for u in canonical_db["users"].values()} - {None}
    overlap = plus_emails & canon_emails
    assert not overlap, f"emails shared with canonical: {sorted(overlap)[:5]}"


# ---------------------------------------------------------------------------
# Task <-> db grounding
# ---------------------------------------------------------------------------

ID_ARG_KEYS = {"reservation_id", "user_id", "payment_id", "flight_number"}

# 6-char uppercase alnum with at least one digit (reservation-id shaped);
# letters-only ids (e.g. JJAOMK) are covered by the canonical-equality check.
RES_TOKEN_RE = re.compile(r"\b(?=[A-Z0-9]{6}\b)(?=[A-Z]*\d)[A-Z0-9]{6}\b")
FLIGHT_TOKEN_RE = re.compile(r"\bMER\d{1,4}\b")
PAYMENT_TOKEN_RE = re.compile(r"\b(?:credit_card|gift_card|certificate)_\d+\b")


def _walk_id_args(node, found):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ID_ARG_KEYS and isinstance(value, str):
                found.append((key, value))
            _walk_id_args(value, found)
    elif isinstance(node, list):
        for item in node:
            _walk_id_args(item, found)


def _task_texts(task):
    instr = task["user_scenario"]["instructions"]
    ec = task.get("evaluation_criteria") or {}
    texts = [
        instr.get(k) or ""
        for k in ("task_instructions", "reason_for_call", "known_info", "unknown_info")
    ]
    texts += ec.get("nl_assertions") or []
    texts += ec.get("communicate_info") or []
    return "\n".join(texts)


def test_gold_arg_ids_ground_in_db(plus_db, plus_tasks):
    payment_ids = {
        pid for u in plus_db["users"].values() for pid in u.get("payment_methods", {})
    }
    problems = []
    for task in plus_tasks:
        found = []
        _walk_id_args((task.get("evaluation_criteria") or {}).get("actions") or [], found)
        for key, value in found:
            grounded = {
                "reservation_id": lambda v: v in plus_db["reservations"],
                "user_id": lambda v: v in plus_db["users"],
                "payment_id": lambda v: v in payment_ids,
                "flight_number": lambda v: v in plus_db["flights"],
            }[key](value)
            if not grounded:
                problems.append(f"task {task['id']}: {key}={value}")
    assert not problems, "\n".join(problems)


def test_task_text_ids_ground_in_db(plus_db, canonical_db, plus_tasks):
    """Reservation/flight/payment tokens quoted in task prose must exist in
    the plus db (the pre-fix truncated credit_card_907483 grounded nowhere),
    and no token may equal a canonical id (the de-memorization contract)."""
    payment_ids = {
        pid for u in plus_db["users"].values() for pid in u.get("payment_methods", {})
    }
    canonical_res = set(canonical_db["reservations"])
    problems = []
    for task in plus_tasks:
        text = _task_texts(task)
        for token in RES_TOKEN_RE.findall(text):
            if FLIGHT_TOKEN_RE.fullmatch(token):
                continue
            if token not in plus_db["reservations"]:
                problems.append(f"task {task['id']}: reservation-shaped {token}")
        for token in FLIGHT_TOKEN_RE.findall(text):
            if token not in plus_db["flights"]:
                problems.append(f"task {task['id']}: flight {token}")
        for token in PAYMENT_TOKEN_RE.findall(text):
            if token not in payment_ids:
                problems.append(f"task {task['id']}: payment {token}")
        for token in re.findall(r"\b[A-Z0-9]{6}\b", text):
            if token in canonical_res and token not in plus_db["reservations"]:
                problems.append(f"task {task['id']}: canonical reservation {token}")
    assert not problems, "\n".join(problems)


def test_nl_amounts_disjoint_from_canonical(plus_tasks, canonical_tasks):
    """No dollar literal in a plus task's nl_assertions may equal the same
    canonical task's literal (pre-fix: ten tasks carried canonical amounts).
    Additions that legitimately coincide belong in the allowlist with a
    reason."""
    allowlist: dict[str, set[str]] = {}
    canonical = {t["id"]: t for t in canonical_tasks}

    def amounts(task):
        nl = (task.get("evaluation_criteria") or {}).get("nl_assertions") or []
        return {
            m.replace(",", "")
            for a in nl
            for m in re.findall(r"\$([\d,]+(?:\.\d+)?)", a)
        }

    problems = []
    for task in plus_tasks:
        twin = canonical.get(task["id"])
        if twin is None:
            continue
        shared = amounts(task) & amounts(twin) - allowlist.get(task["id"], set())
        if shared:
            problems.append(f"task {task['id']}: canonical amounts {sorted(shared)}")
    assert not problems, "\n".join(problems)


def test_redrawn_values_disjoint_from_canonical(plus_db, canonical_db):
    """User street lines, unit numbers, card last-fours and zips share no
    value with EITHER canonical db (retail's included) — the PR C redraw
    drew from pools disjoint from the union, so exact set disjointness is
    the contract. Pre-redraw, every one of these families was carried over
    from canonical airline verbatim (the old delta_spec ``keep_last_four`` /
    ``keep_addresses`` policy, superseded by ``redrawn_value_families``)."""
    canonical_retail_db = json.loads(
        (Path(DATA_DIR) / "tau2" / "domains" / "retail" / "db.json").read_text()
    )

    def addresses(db, include_orders):
        ents = [u["address"] for u in db["users"].values() if "address" in u]
        if include_orders:
            ents += [o["address"] for o in db["orders"].values() if "address" in o]
        return ents

    def last_fours(db):
        return {
            m["last_four"]
            for u in db["users"].values()
            for m in u.get("payment_methods", {}).values()
            if "last_four" in m
        }

    canon = addresses(canonical_db, False) + addresses(canonical_retail_db, True)
    plus = addresses(plus_db, False)
    assert not {a["address1"] for a in plus} & {a["address1"] for a in canon}
    assert not {a["address2"] for a in plus if a.get("address2")} & {
        a["address2"] for a in canon if a.get("address2")
    }
    assert not {a["zip"] for a in plus} & {a["zip"] for a in canon}
    assert not last_fours(plus_db) & (
        last_fours(canonical_db) | last_fours(canonical_retail_db)
    )


def test_task_text_last_fours_ground_in_db(plus_db, plus_tasks):
    """Every context-bounded card last-four in task prose grounds in the
    plus db's last_four set (the redraw re-synced eight such references;
    a stale one would name a card no user holds)."""
    db_l4 = {
        m["last_four"]
        for u in plus_db["users"].values()
        for m in u.get("payment_methods", {}).values()
        if "last_four" in m
    }
    problems = []
    for task in plus_tasks:
        text = _task_texts(task)
        for pattern in (r"ending in (\d{4})\b", r"your (\d{4}) card\b"):
            for match in re.finditer(pattern, text):
                if match.group(1) not in db_l4:
                    problems.append(f"task {task['id']}: {match.group(0)}")
    assert not problems, "\n".join(problems)


# ---------------------------------------------------------------------------
# nl_assertions <-> gold consistency (Phase B audit gates)
# ---------------------------------------------------------------------------
# The dollar-amount disjointness gate above compares nl_assertions only
# against canonical amounts, so canonical-era ids and bag counts sailed
# through (pre-fix: task 21 named the wrong gift card; tasks 3/21/22/24
# asserted canonical baggage-matrix counts against plus golds).

BAG_WORD = r"(?:checked\s+)?(?:bags?|baggages?|suitcases?)"
BAG_COUNT = r"(\d+|no|one|two|three|four|five)"
FREE_BAG_RE = re.compile(rf"\b{BAG_COUNT}\s+free\s+{BAG_WORD}", re.IGNORECASE)
BAGS_FOR_FREE_RE = re.compile(
    rf"\b{BAG_COUNT}\s+{BAG_WORD}\s+for\s+free", re.IGNORECASE
)
TOTAL_BAG_RE = re.compile(rf"\b{BAG_COUNT}\s+total\s+{BAG_WORD}", re.IGNORECASE)
MEMBERSHIP_RE = re.compile(r"\b(regular|silver|gold)\s+member", re.IGNORECASE)
CABIN_RE = re.compile(r"\b(basic\s+economy|economy|business)\b", re.IGNORECASE)
CABIN_INDEX = {"basic_economy": 0, "economy": 1, "business": 2}
COUNT_WORDS = {"no": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5}


def test_nl_payment_ids_ground_in_gold_args(plus_tasks):
    """Every payment-method id named in a task's nl_assertions must appear
    among that task's gold action arguments. Every legitimate mention in the
    committed tasks satisfies this (the nl restates the scored payment);
    pre-fix, task 21 asserted gift_card_6506890 while the gold pinned
    gift_card_4787155."""
    problems = []
    for task in plus_tasks:
        ec = task.get("evaluation_criteria") or {}
        gold_ids = set(PAYMENT_TOKEN_RE.findall(json.dumps(ec.get("actions") or [])))
        for assertion in ec.get("nl_assertions") or []:
            for token in PAYMENT_TOKEN_RE.findall(assertion):
                if token not in gold_ids:
                    problems.append(
                        f"task {task['id']}: {token} not in gold action args"
                    )
    assert not problems, "\n".join(problems)


def _bag_claims(text):
    """Extract (kind, count) bag-count claims: kind 'free' for phrases like
    '2 free bags' / '2 checked bags for free', 'total' for '2 total
    baggages'."""
    claims = []
    for regex, kind in (
        (FREE_BAG_RE, "free"),
        (BAGS_FOR_FREE_RE, "free"),
        (TOTAL_BAG_RE, "total"),
    ):
        for m in regex.finditer(text):
            token = m.group(1).lower()
            claims.append((kind, int(token) if token.isdigit() else COUNT_WORDS[token]))
    return claims


def test_nl_bag_counts_consistent(plus_tasks, spec):
    """Bag-count claims in nl_assertions must be plus-correct, not canonical.

    Two anchors, tightest first: an assertion that names a membership tier
    and a cabin states a per-passenger allowance, which must equal the spec
    matrix cell; any other assertion with a bag-count claim must agree with
    the task's gold baggage arguments (free == total - nonfree, total ==
    total). A claim with neither anchor is itself a defect. Pre-fix, tasks
    3/21/22/24 all failed here with canonical-matrix counts."""
    allowance = {
        tier: vals["new"] for tier, vals in spec["baggage_allowance"].items()
    }
    problems = []
    for task in plus_tasks:
        ec = task.get("evaluation_criteria") or {}
        bag_golds = [
            (a["arguments"]["total_baggages"], a["arguments"]["nonfree_baggages"])
            for a in ec.get("actions") or []
            if a["name"] in ("update_reservation_baggages", "book_reservation")
            and a.get("arguments", {}).get("total_baggages") is not None
        ]
        for assertion in ec.get("nl_assertions") or []:
            claims = _bag_claims(assertion)
            if not claims:
                continue
            membership = MEMBERSHIP_RE.search(assertion)
            cabin = CABIN_RE.search(assertion)
            if membership and cabin:
                cell = allowance[membership.group(1).lower()][
                    CABIN_INDEX[re.sub(r"\s+", "_", cabin.group(1).lower())]
                ]
                for kind, count in claims:
                    if kind == "free" and count != cell:
                        problems.append(
                            f"task {task['id']}: {count} free vs allowance "
                            f"{cell}: {assertion!r}"
                        )
                continue
            if not bag_golds:
                problems.append(
                    f"task {task['id']}: bag claim with no gold baggage action "
                    f"and no tier+cabin anchor: {assertion!r}"
                )
                continue
            for kind, count in claims:
                expected = (
                    {total - nonfree for total, nonfree in bag_golds}
                    if kind == "free"
                    else {total for total, _ in bag_golds}
                )
                if count not in expected:
                    problems.append(
                        f"task {task['id']}: {count} {kind} vs gold "
                        f"{sorted(expected)}: {assertion!r}"
                    )
    assert not problems, "\n".join(problems)
