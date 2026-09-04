"""Pinned derivation expectations for the airline_plus corpora.

airline_plus (domain data and hyper-sops fact tree) was originally derived
from canonical airline by a generator and two porters that are no longer part
of the benchmark. Everything those tools contributed to a test expectation is
pinned here:

* the retired policy phrases, brand patterns, and retired fact ids they banned
  from the ported tree, as plain literals;
* the canonical identifier universe they remapped, rebuilt from the committed
  canonical corpus (``data/tau2/domains/airline``) — the canonical tokens are
  exactly the map *keys*, so no seeded draw is needed to know what must be
  absent;
* the pricing arithmetic the discrimination gates need, ported from the
  generator's engine (it mirrors ``src/tau2/domains/airline_plus/tools.py``).

``data/tau2/domains/airline_plus/delta_spec.yaml`` is unaffected by the script
removal and stays the live registry for the domain's own values.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
CANONICAL_DIR = DATA_DIR / "tau2" / "domains" / "airline"
PLUS_DIR = DATA_DIR / "tau2" / "domains" / "airline_plus"

CABINS = ("basic_economy", "economy", "business")

# ---------------------------------------------------------------------------
# Domain-data leakage expectations (data/tau2/domains/airline_plus)
# ---------------------------------------------------------------------------

# Retired policy sentences: the canonical values these state were replaced by
# delta_spec, so any surviving copy is a stale edit.
RETIRED_POLICY_PHRASES = (
    "at most five passengers",
    "at most three gift cards",
    "is 50 dollars",
    "is 30 dollars per passenger",
    "$100 times the number of passengers",
    "$50 times the number of passengers",
    "within 5 to 7 business days",
)

# Case-insensitive canonical brand family. The exact-token scan below is
# case-sensitive, so lowercase spellings (hatairlines.slack.com, hat_airlines
# ids, hat123 flight tokens) need their own patterns.
BRAND_PATTERNS = (
    (r"(?i)(?<![a-z])hat[\s_-]?airlines", "brand"),
    (r"(?i)(?<![a-z])hatairlines", "brand"),
    (r"(?i)(?<![a-z])hat\d{3}", "flight prefix (any case)"),
)

# Retired-value spellings banned on the eval surface (policy + agent-visible
# task text) only: task description blocks legitimately document canonical
# values for the ghost-witness tasks and are never shown to the agent.
EVAL_SURFACE_PATTERNS = (
    (r"(?i)certificates? of \$(?:50|100)\b", "canonical certificate rate"),
    (r"(?i)\$(?:50|100) (?:travel )?certificates?\b", "canonical certificate rate"),
    (
        r"(?i)\b(?:5|five)[ \t]*(?:-|–|—|to)[ \t]*(?:-|–|—)?[ \t]*(?:7|seven)"
        r"[ \t-]*(?:business|calendar)?[ \t-]*days?\b",
        "retired window spelling",
    ),
)

TASK_TEXT_KEYS = (
    "task_instructions",
    "reason_for_call",
    "known_info",
    "unknown_info",
)


def _gold_actions(task: dict) -> list:
    return (task.get("evaluation_criteria") or {}).get("actions") or []


def _canonical_dobs(db: dict, tasks: list) -> set[str]:
    dobs = set()
    for user in db["users"].values():
        dobs.add(user["dob"])
        for passenger in user.get("saved_passengers", []):
            dobs.add(passenger["dob"])
    for reservation in db["reservations"].values():
        for passenger in reservation.get("passengers", []):
            dobs.add(passenger["dob"])
    for task in tasks:
        for action in _gold_actions(task):
            for passenger in (action.get("arguments") or {}).get("passengers") or []:
                dobs.add(passenger["dob"])
    return dobs


def canonical_identifier_tokens() -> dict[str, set[str]]:
    """Canonical airline tokens that must not appear in airline_plus.

    These are the domains of the generator's remap tables, so they are
    readable straight off the committed canonical corpus.
    """
    spec = yaml.safe_load((PLUS_DIR / "delta_spec.yaml").read_text())
    db = json.loads((CANONICAL_DIR / "db.json").read_text())
    tasks = json.loads((CANONICAL_DIR / "tasks.json").read_text())
    new_tasks_path = PLUS_DIR / "new_tasks_source.json"
    new_tasks = (
        json.loads(new_tasks_path.read_text()) if new_tasks_path.exists() else []
    )
    reservation_ids = set(db["reservations"])
    reservation_ids.update(spec["identifiers"]["new_reservation_ids"]["old"])
    return {
        "user_id": set(db["users"]),
        "reservation_id": reservation_ids,
        "payment_id": {
            payment_id
            for user in db["users"].values()
            for payment_id in user["payment_methods"]
        },
        "email": {user["email"] for user in db["users"].values()},
        "flight": set(db["flights"]),
        "dob": _canonical_dobs(db, tasks + new_tasks),
    }


def collect_committed_leakage() -> list[str]:
    """Every canonical token or retired phrase found in committed airline_plus.

    The committed files are hand-edited post-cutover, so the scan targets them
    directly (there is nothing to regenerate and diff against).
    """
    spec = yaml.safe_load((PLUS_DIR / "delta_spec.yaml").read_text())
    policy = (PLUS_DIR / "policy.md").read_text()
    tasks = json.loads((PLUS_DIR / "tasks.json").read_text())
    blob = "\n".join(
        [policy]
        + [
            json.dumps(json.loads((PLUS_DIR / name).read_text()), ensure_ascii=False)
            for name in ("db.json", "tasks.json", "split_tasks.json")
        ]
    )

    leaked = []
    for label, tokens in canonical_identifier_tokens().items():
        leaked.extend(f"{label}:{token}" for token in sorted(tokens) if token in blob)

    # Canonical name tokens must not survive in task text (db addresses keep
    # canonical street names, so this scan is task-text only).
    exceptions = {
        (str(entry["task"]), entry["token"])
        for entry in spec.get("text_name_exceptions") or []
    }
    canonical_names = set(spec["first_names"]) | set(spec["last_names"])
    for task in tasks:
        task_id = str(task["id"])
        instructions = task["user_scenario"]["instructions"]
        criteria = task.get("evaluation_criteria") or {}
        texts = [instructions.get(key) or "" for key in TASK_TEXT_KEYS]
        texts += (criteria.get("nl_assertions") or []) + (
            criteria.get("communicate_info") or []
        )
        for name in sorted(canonical_names):
            if (task_id, name) in exceptions:
                continue
            if any(re.search(rf"\b{re.escape(name)}\b", text) for text in texts):
                leaked.append(f"name token in task {task_id}: {name}")

    old_prefix = spec["identifiers"]["flight_prefix"]["old"]
    if re.search(rf"{old_prefix}\d{{3}}", blob):
        leaked.append(f"flight prefix {old_prefix}###")
    for phrase in RETIRED_POLICY_PHRASES:
        if phrase in blob:
            leaked.append(f"policy phrase: {phrase!r}")
    for pattern, label in BRAND_PATTERNS:
        if re.search(pattern, blob):
            leaked.append(f"{label}: {pattern!r}")

    surface = "\n".join(
        [policy]
        + [
            text
            for task in tasks
            for text in (
                [
                    (task["user_scenario"]["instructions"].get(key) or "")
                    for key in TASK_TEXT_KEYS
                ]
                + ((task.get("evaluation_criteria") or {}).get("nl_assertions") or [])
                + (
                    (task.get("evaluation_criteria") or {}).get("communicate_info")
                    or []
                )
            )
        ]
    )
    for pattern, label in EVAL_SURFACE_PATTERNS:
        if re.search(pattern, surface):
            leaked.append(f"{label}: {pattern!r}")
    return leaked


# ---------------------------------------------------------------------------
# Pricing arithmetic for the canonical-ghost gates
# ---------------------------------------------------------------------------


def allowance(matrix: dict, membership: str, cabin: str) -> int:
    return matrix[membership][CABINS.index(cabin)]


def booking_total(
    db: dict, args: dict, *, bag_fee: int, insurance_fee: int, matrix: dict
) -> int:
    """Total charge for a ``book_reservation`` gold under the given values.

    Mirrors ``AirlinePlusTools.book_reservation``: airfare per passenger per
    leg, optional insurance per passenger, and the extra-bag fee for every bag
    beyond the membership/cabin allowance.
    """
    user = db["users"][args["user_id"]]
    passengers = len(args["passengers"])
    total = (
        sum(
            db["flights"][leg["flight_number"]]["dates"][leg["date"]]["prices"][
                args["cabin"]
            ]
            for leg in args["flights"]
        )
        * passengers
    )
    if args.get("insurance") == "yes":
        total += insurance_fee * passengers
    free = allowance(matrix, user["membership"], args["cabin"]) * passengers
    return total + bag_fee * max(0, args.get("total_baggages", 0) - free)


def baggage_update_context(db: dict, task: dict, action: dict) -> tuple[str, str, int]:
    """The (membership, cabin, passengers) an ``update_reservation_baggages``
    gold is priced against.

    Sequence-aware: a cabin or passenger-list change earlier in the same gold
    moves the allowance the baggage update is charged under.
    """
    args = action["arguments"]
    reservation = db["reservations"][args["reservation_id"]]
    cabin = reservation["cabin"]
    passengers = len(reservation["passengers"])
    for earlier in _gold_actions(task):
        if earlier["action_id"] == action["action_id"]:
            break
        earlier_args = earlier.get("arguments") or {}
        if earlier_args.get("reservation_id") != args["reservation_id"]:
            continue
        if earlier["name"] == "update_reservation_flights":
            cabin = earlier_args["cabin"]
        elif earlier["name"] == "update_reservation_passengers":
            passengers = len(earlier_args["passengers"])
    return db["users"][reservation["user_id"]]["membership"], cabin, passengers


def split_payment(db: dict, user_id: str, plan: list[str], total: int) -> list[dict]:
    """Ordered-exhaustion payment split (ported from the generator's engine).

    Limited instruments (gift cards, certificates) pay ``min(balance, rest)``;
    the final method absorbs the remainder.
    """
    methods = db["users"][user_id]["payment_methods"]
    remaining = total
    out = []
    for payment_id in plan:
        method = methods[payment_id]
        if method["source"] in ("gift_card", "certificate"):
            amount = min(int(method["amount"]), remaining)
        else:
            amount = remaining
        out.append({"payment_id": payment_id, "amount": amount})
        remaining -= amount
    if remaining != 0:
        raise AssertionError(
            f"payment plan {plan} does not cover total {total} ({remaining} left)"
        )
    return out


# ---------------------------------------------------------------------------
# Hyper-sops expectations (data/tau2/hyper/sops/airline_plus)
# ---------------------------------------------------------------------------

HYPER_ROOT = DATA_DIR / "tau2" / "hyper"
SOPS_ROOT = HYPER_ROOT / "sops" / "airline_plus"
SOP_REL = Path("sops/airline_plus_sop.md")
RESPONSE_PACK_REL = Path("response_phrasing/airline_plus_response_phrasing.yaml")

SOURCE_SECTION_IDS = (
    "authorized_scope",
    "booking_flight",
    "cancelling_reservation",
    "compensation_certificates",
    "customer_identity",
    "modifying_reservation",
)
# Composed from the source sections rather than authored directly.
GENERATED_SECTION_ID = "manage_existing_reservation"

BAGGAGE_TIERS = (("regular", "Regular"), ("silver", "Silver"), ("gold", "Gold"))
BAGGAGE_CABINS = (
    ("basic_economy", "Basic Economy"),
    ("economy", "Economy"),
    ("business", "Business"),
)

# Fact ids that embedded a canonical value and were renamed value-free during
# the port. None may reappear anywhere in the committed tree.
RETIRED_FACT_IDS = (
    "max_five_passengers",
    "additional_bag_cost_50",
    "insurance_cost_30_per_passenger",
    "additional_checked_bag_cost_50",
    "refund_arrival_5_to_7_business_days",
    "baggage_regular_basic_economy_zero",
    "baggage_regular_economy_one",
    "baggage_regular_business_two",
    "baggage_silver_basic_economy_one",
    "baggage_silver_economy_two",
    "baggage_silver_business_three",
    "baggage_gold_basic_economy_two",
    "baggage_gold_economy_three",
    "baggage_gold_business_four",
)

# Canonical values that must not survive anywhere in the schema/SOP layer.
SCHEMA_FORBIDDEN_PATTERNS = (
    r"\$50\b",
    r"\$30\b",
    r"\$100\b",
    r"5 to 7 business days",
    r"at most 5 passengers",
    r"at most five passengers",
    r"3 gift cards",
    r"three gift cards",
    r"HAT",
    r"(?i)(?<![a-z])hat[\s_.-]?airlines",
    r"(?i)(?<![a-z])hatairlines",
    r"(?i)(?<![a-z])hat\d{3}",
)

# The artifact tree follows a looser policy than the schema layer: bare values
# occur legitimately as unrelated fares, price differences, and balances in
# support records, so only context-bearing policy echoes are banned.
ARTIFACT_FORBIDDEN_PATTERNS = (
    r"HAT",
    r"(?i)(?<![a-z])hat[\s_.-]?airlines",
    r"(?i)(?<![a-z])hatairlines",
    r"(?i)(?<![a-z])hat\d{3}",
    r"(?:additional|extra) checked bag[^\n]*\$50",
    r"\$50[^\n]*(?:additional|extra) checked bag",
    r"(?:travel )?insurance[^\n]*\$30 per passenger",
    r"\$30 per passenger[^\n]*(?:travel )?insurance",
    r"\$100 travel certificate per passenger",
    r"\$50 travel certificate per passenger",
    r"certificates? (?:at|worth) \$(?:100|50) each",
    r"5 to 7 business days",
    r"5[–-]7 business days",
    r"(?:at most|up to|[Mm]aximum) (?:5|five) passengers",
    # Policy-echo forms only: a customer *asking* for three gift cards (and
    # being declined) is discrimination content, not leakage.
    r"at most (?:3|three) gift cards",
    r"(?:3|three) gift cards in a single booking",
    r"limit of at most (?:3|three) gift cards",
    r"and (?:3|three) gift cards\?",
)


def bags_phrase(count: int) -> str:
    plural = "" if count == 1 else "s"
    return f"{count} free checked bag{plural}"


def load_spec() -> dict[str, Any]:
    return yaml.safe_load((PLUS_DIR / "delta_spec.yaml").read_text())
