"""Intrinsic committed-tree invariants for retail_plus (hardening plan PR B).

Post-cutover companions to test_retail_plus.py, pinning the properties the
2026-08-04 audit found violated:

- order tokens quoted in task prose must ground in the plus db in EVERY
  spelling (pre-fix: hash-stripped W5061109/W4284542 and bare digit pair
  9502126/9502127 escaped the #W-keyed remap and grounded nowhere);
- communicate_info values must not be substrings of the task's own tokens
  (pre-fix: "10" was spuriously satisfied by order id #W5910505 — the
  airline suite had this guard, retail didn't);
- nl_assertion dollar amounts must stay disjoint from the canonical twin's.

Canonical retail files are read ONLY as a frozen oracle.
"""

import json
import re
from pathlib import Path

import pytest

from tau2.utils.utils import DATA_DIR

from .test_retail_plus import EXPECTED_REPLAY_FAILURES

PLUS_DIR = Path(DATA_DIR) / "tau2" / "domains" / "retail_plus"
RETAIL_DIR = Path(DATA_DIR) / "tau2" / "domains" / "retail"
CANONICAL_AIRLINE_DIR = Path(DATA_DIR) / "tau2" / "domains" / "airline"

# Deliberate near-miss tokens: ids a scripted user quotes that must NOT
# resolve (typo probes). Every entry needs a reason.
ALLOWED_UNGROUNDED_TEXT_TOKENS = {
    # tasks 45/46/47: the user's mistyped order id; the corrected id
    # 7699162 resolves to gold order #W7699162.
    "7699161",
}


@pytest.fixture(scope="module")
def plus_db():
    return json.loads((PLUS_DIR / "db.json").read_text())


@pytest.fixture(scope="module")
def canonical_db():
    return json.loads((RETAIL_DIR / "db.json").read_text())


@pytest.fixture(scope="module")
def plus_tasks():
    return json.loads((PLUS_DIR / "tasks.json").read_text())


@pytest.fixture(scope="module")
def canonical_tasks():
    return json.loads((RETAIL_DIR / "tasks.json").read_text())


def _gold_actions(task):
    return (task.get("evaluation_criteria") or {}).get("actions") or []


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


def test_order_tokens_ground_in_db(plus_db, canonical_db, plus_tasks):
    """Every order reference in task prose grounds in the plus db, in every
    spelling: '#W1234567', bare 'W1234567', and bare seven digits. The
    pre-fix tree carried canonical W5061109/W4284542/9502126/9502127."""
    orders = set(plus_db["orders"])
    canonical_orders = set(canonical_db["orders"])
    problems = []
    for task in plus_tasks:
        text = _task_texts(task)
        candidates = set()
        for m in re.finditer(r"#?W\d{7}\b", text):
            candidates.add(m.group(0).lstrip("#").lstrip("W"))
        for m in re.finditer(r"(?<![#\dW_])\d{7}(?!\d)", text):
            candidates.add(m.group(0))
        for digits in candidates:
            if digits in ALLOWED_UNGROUNDED_TEXT_TOKENS:
                continue
            if f"#W{digits}" in canonical_orders and f"#W{digits}" not in orders:
                problems.append(f"task {task['id']}: canonical order {digits}")
            elif f"#W{digits}" not in orders:
                problems.append(f"task {task['id']}: ungrounded order {digits}")
    assert not problems, "\n".join(problems)


def test_gold_order_args_ground_or_are_declared_probes(plus_db, plus_tasks):
    """order_id gold arguments resolve in the plus db unless the action is a
    declared wrong-lookup probe (the replay suite pins those to fail)."""
    orders = set(plus_db["orders"])
    problems = []
    for task in plus_tasks:
        probes = EXPECTED_REPLAY_FAILURES.get(task["id"], set())
        for action in _gold_actions(task):
            order_id = (action.get("arguments") or {}).get("order_id")
            if not order_id or action["action_id"] in probes:
                continue
            if order_id not in orders:
                problems.append(
                    f"task {task['id']}/{action['action_id']}: {order_id}"
                )
    assert not problems, "\n".join(problems)


def test_communicate_info_collisions(plus_tasks):
    """A numeric communicate_info string must not appear as a substring of
    any other numeric token in the same task's gold arguments or scenario
    text (the evaluator does substring matching over the transcript).
    Ported from the airline suite; retail lacked it and tasks 2/3/4 shipped
    with '10' inside their own gold order id."""
    for task in plus_tasks:
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


def test_nl_amounts_disjoint_from_canonical(plus_tasks, canonical_tasks):
    """No dollar literal in a plus task's nl_assertions may equal the same
    canonical task's literal. Legitimate coincidences belong in the
    allowlist with a reason."""
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


def _addresses(db, include_orders):
    ents = [u["address"] for u in db["users"].values() if "address" in u]
    if include_orders:
        ents += [o["address"] for o in db["orders"].values() if "address" in o]
    return ents


def _last_fours(db):
    return {
        m["last_four"]
        for u in db["users"].values()
        for m in u.get("payment_methods", {}).values()
        if "last_four" in m
    }


def test_redrawn_values_disjoint_from_canonical(plus_db, canonical_db):
    """Street lines, unit numbers and card last-fours (users AND orders) share
    no value with EITHER canonical db — the PR C redraw drew from pools
    disjoint from the union, so exact set disjointness is the contract.
    Zips (redrawn earlier by the generator) are checked against canonical
    retail only: six coincide with canonical *airline* zips, which was never
    a de-memorization requirement here. Pre-redraw, every one of these
    families was carried over from canonical retail verbatim."""
    canonical_airline_db = json.loads(
        (CANONICAL_AIRLINE_DIR / "db.json").read_text()
    )
    canon = _addresses(canonical_db, True) + _addresses(canonical_airline_db, False)
    canon_a1 = {a["address1"] for a in canon}
    canon_a2 = {a["address2"] for a in canon if a.get("address2")}
    canon_l4 = _last_fours(canonical_db) | _last_fours(canonical_airline_db)

    plus = _addresses(plus_db, True)
    assert not {a["address1"] for a in plus} & canon_a1
    assert not {a["address2"] for a in plus if a.get("address2")} & canon_a2
    assert not _last_fours(plus_db) & canon_l4
    canon_retail_zips = {a["zip"] for a in _addresses(canonical_db, True)}
    assert not {a["zip"] for a in plus} & canon_retail_zips


def _money_candidates(db, task):
    """Every dollar value the plus db can justify for this task's texts.

    Built from the task's gold entities: order totals/items/payment history,
    per-action refund sums and exchange/modify diffs (and their nets, also
    applied to order totals and gift-card balances — "new order total",
    "balance after the swap"), subset sums of order items ("the office
    items"), savings vs the cheapest available variant ("exchanging to the
    cheapest saves $X"), per-product spend across the scenario user's whole
    order history ("all the grills you bought"), and full variant sheets of
    gold products plus products the task text names. Deliberately generous:
    this is a drift tripwire — an amount no expression can produce anymore —
    not a proof of the one intended derivation (the audit owns exactness)."""
    orders, products, users = db["orders"], db["products"], db["users"]
    item_price = {
        iid: v["price"]
        for p in products.values()
        for iid, v in p["variants"].items()
    }

    def subset_sums(vals, cap=20):
        sums = {0.0}
        for v in vals[:cap]:
            sums |= {round(s + v, 2) for s in sums}
        sums.discard(0.0)
        return sums

    def cheapest_available(pid):
        av = [v["price"] for v in products[pid]["variants"].values() if v["available"]]
        return min(av) if av else None

    cands = set()
    gold = _gold_actions(task)
    text = " ".join(
        filter(
            None,
            (
                task["user_scenario"]["instructions"].get(k)
                for k in ("task_instructions", "reason_for_call")
            ),
        )
    ).lower()
    oids, pids, uids, diffs, refunds = set(), set(), set(), [], []
    for action in gold:
        args = action.get("arguments") or {}
        if args.get("order_id") in orders:
            oids.add(args["order_id"])
        if args.get("product_id") in products:
            pids.add(args["product_id"])
        if args.get("user_id") in users:
            uids.add(args["user_id"])
        items = [i for i in args.get("item_ids") or [] if i in item_price]
        new = [i for i in args.get("new_item_ids") or [] if i in item_price]
        cands.update(item_price[i] for i in items + new)
        if action["name"] in (
            "exchange_delivered_order_items",
            "modify_pending_order_items",
        ) and items and new:
            diff = sum(map(item_price.get, new)) - sum(map(item_price.get, items))
            diffs.append(diff)
            cands.update(
                {
                    diff,
                    -diff,
                    abs(diff),
                    sum(map(item_price.get, items)),
                    sum(map(item_price.get, new)),
                }
            )
        if action["name"] == "return_delivered_order_items" and items:
            refund = sum(map(item_price.get, items))
            refunds.append(refund)
            cands.add(refund)
            if args.get("order_id") in orders:
                total = sum(i["price"] for i in orders[args["order_id"]]["items"])
                cands.add(total - refund)  # "total paid for remaining items"
        if action["name"] == "cancel_pending_order" and args.get("order_id") in orders:
            refunds.append(orders[args["order_id"]]["payment_history"][0]["amount"])

    item_pool, savings_pool = [], []
    for oid in oids:
        order = orders[oid]
        uids.add(order["user_id"])
        cands.update(h["amount"] for h in order["payment_history"])
        for item in order["items"]:
            cands.add(item["price"])
            item_pool.append(item["price"])
            pids.add(item["product_id"])
            cheapest = cheapest_available(item["product_id"])
            if cheapest is not None:
                savings_pool.append(item["price"] - cheapest)
        cands.add(sum(i["price"] for i in order["items"]))
    cands |= subset_sums(item_pool)
    cands |= subset_sums(savings_pool)
    order_totals = [sum(i["price"] for i in orders[oid]["items"]) for oid in oids]
    cands |= subset_sums(order_totals)

    net = sum(diffs) if diffs else None
    if diffs:
        cands.update({net, -net, abs(net)})
        for total in order_totals:
            for diff in diffs + [net]:
                cands.update({total + diff, total - diff})
    if refunds:
        cands.add(sum(refunds))

    for uid in uids:
        user = users[uid]
        per_product = {}
        for oid in user["orders"]:
            for item in orders[oid]["items"]:
                cands.add(item["price"])
                per_product.setdefault(item["name"], []).append(item["price"])
        cands.update(sum(vals) for vals in per_product.values())
        for pm in user["payment_methods"].values():
            if "balance" in pm:
                balance = pm["balance"]
                cands.add(balance)
                for delta in diffs + refunds + ([net] if net is not None else []):
                    cands.update({balance - delta, balance + delta})

    for pid, product in products.items():
        if product["name"].lower() in text:
            pids.add(pid)
    for pid in pids:
        variants = list(products[pid]["variants"].values())
        cands.update(v["price"] for v in variants)
        available = [v["price"] for v in variants if v["available"]]
        if available:
            cands.update({min(available), max(available), sum(available)})
        cands.add(sum(v["price"] for v in variants))
    return {round(c, 2) for c in cands}


def test_nl_and_communicate_amounts_derive_from_db(plus_db, plus_tasks):
    """Every dollar literal in nl_assertions / communicate_info must still be
    derivable from the plus db via the task's own gold entities. Gold replay
    stays green when a db price edit silently falsifies these amounts (writes
    still succeed); this is the tripwire the 2026-08-06 audit found missing —
    task 95's family of drift would land here."""
    money_nl = re.compile(r"\$([\d,]+(?:\.\d+)?)")
    money_comm = re.compile(r"^-?\d+\.\d{2}$")
    problems = []
    for task in plus_tasks:
        ec = task.get("evaluation_criteria") or {}
        amounts = {
            m.replace(",", "")
            for a in ec.get("nl_assertions") or []
            for m in money_nl.findall(a)
        }
        amounts |= {
            c.lstrip("-")
            for c in ec.get("communicate_info") or []
            if money_comm.fullmatch(c)
        }
        if not amounts:
            continue
        cands = _money_candidates(plus_db, task)
        for amount in sorted(amounts):
            if round(float(amount), 2) not in cands:
                problems.append(f"task {task['id']}: ${amount} derives from nothing")
    assert not problems, "\n".join(problems)


def test_calculate_expressions_carry_plus_values(plus_db, plus_tasks, canonical_tasks):
    """Gold `calculate` expressions must be built from plus-world numbers.

    Pre-fix, all 13 expressions were carried over from canonical retail
    verbatim (e.g. task 46's '652.61 + 473.43' vs the true plus refund
    885.87 + 375.31) — invisible to replay (the tool just evaluates the
    string) and to reward (ACTION is not a reward basis). Two pins: every
    literal must derive from the plus db, and no expression may be
    string-identical to the canonical twin's."""
    canonical = {t["id"]: t for t in canonical_tasks}
    problems = []
    for task in plus_tasks:
        calcs = [a for a in _gold_actions(task) if a["name"] == "calculate"]
        if not calcs:
            continue
        cands = _money_candidates(plus_db, task)
        twin = canonical.get(task["id"])
        twin_exprs = {
            a["arguments"]["expression"]
            for a in (_gold_actions(twin) if twin else [])
            if a["name"] == "calculate"
        }
        for action in calcs:
            expr = action["arguments"]["expression"]
            if expr in twin_exprs:
                problems.append(
                    f"task {task['id']}/{action['action_id']}: expression "
                    f"{expr!r} is canonical retail's, verbatim"
                )
            for literal in re.findall(r"\d+(?:\.\d+)?", expr):
                if round(float(literal), 2) not in cands:
                    problems.append(
                        f"task {task['id']}/{action['action_id']}: literal "
                        f"{literal} derives from nothing in the plus db"
                    )
    assert not problems, "\n".join(problems)


def test_gold_address_args_ground_or_are_user_dictated(plus_db, plus_tasks):
    """Every gold ``address1`` argument is either a db address or an address
    the scripted user dictates in the task's own text (a new-address write,
    e.g. task 22's '311 Parkway'; tasks 41/42 write the near-miss the user
    mis-quotes before correction). An address satisfying neither is a
    redraw sync miss."""
    db_a1 = {a["address1"] for a in _addresses(plus_db, True)}
    problems = []
    for task in plus_tasks:
        text = _task_texts(task)
        for action in _gold_actions(task):
            a1 = (action.get("arguments") or {}).get("address1")
            if a1 and a1 not in db_a1 and a1 not in text:
                problems.append(f"task {task['id']}/{action['action_id']}: {a1!r}")
    assert not problems, "\n".join(problems)
