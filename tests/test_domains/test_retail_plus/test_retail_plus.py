"""Gates for the retail_plus domain.

retail_plus was originally derived from canonical retail according to
data/tau2/domains/retail_plus/delta_spec.yaml (plus the new tasks in
new_tasks_source.json). Since the 2026-08-04 standalone cutover
the committed files are edited directly.
These tests enforce:

1. Leakage: canonical ids, emails, and retired policy phrases must not appear
   in the committed files. The canonical token universe is read off the
   committed canonical corpus (see tests/plus_support/) and the retired
   window spellings are pinned literals; nothing is regenerated or diffed.
2. Solvability: every gold action replays cleanly against the environment,
   except the deliberate failed-lookup probes inherited from canonical retail
   (wrong emails / wrong zips / malformed order ids / exchange-on-pending),
   which must fail on exactly the same action ids.
3. Discrimination: the item-id permutation is a derangement (a memorized
   id->variant mapping is always wrong), every price moved by at least the
   spec minimum, a global affine fit cannot recover the canonical price sheet,
   and the cross-world truth flips that the new boundary tasks (115/117/123)
   rely on actually hold.
4. Structure: the new tasks keep the design intent that cannot be expressed in
   the delta spec (payment-method choices, refusal golds with no writes).
"""

import json
import re
from pathlib import Path

import pytest
import yaml
from plus_support import retail_plus as expectations

from tau2.domains.retail.tools import RetailTools
from tau2.domains.retail_plus.environment import get_environment, get_tasks
from tau2.domains.retail_plus.tools import RetailPlusTools
from tau2.registry import registry
from tau2.utils.utils import DATA_DIR

REPO_ROOT = Path(__file__).resolve().parents[3]
PLUS_DIR = Path(DATA_DIR) / "tau2" / "domains" / "retail_plus"
RETAIL_DIR = Path(DATA_DIR) / "tau2" / "domains" / "retail"

# 114-123: the original coverage/discrimination wave; 124-128: the 2026-08-06
# audit wave (gift-card refund destination, one-shot modify, terminal auth
# failure, gift-card-immediate cancel messaging, delivered-address refusal);
# 129-133: the 2026-08-19 client-lever coverage wave (payment-swap refund
# timeline, exact transfer notice, new-card / email-change / quantity-change
# refusals) authored in the 2026-08-19 client-lever coverage wave.
NEW_TASK_IDS = {str(i) for i in range(114, 134)}

# Deliberate gold-replay failures inherited from canonical retail: wrong-email /
# wrong-zip lookup probes, malformed order ids, and task 64's exchange on a
# pending order. Keyed by task id -> action ids that MUST fail. Everything else
# must replay cleanly.
EXPECTED_REPLAY_FAILURES = {
    "35": {"35_0"},
    "37": {"37_0"},
    "38": {"38_0"},
    "39": {"39_0"},
    "46": {"46_1", "46_2"},
    "47": {"47_1", "47_2"},
    "54": {"54_0"},
    "55": {"55_0"},
    "64": {"64_6"},
    "67": {"67_0", "67_1"},
    "68": {"68_0"},
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


@pytest.fixture(scope="module")
def canonical_db():
    return json.loads((RETAIL_DIR / "db.json").read_text())


@pytest.fixture(scope="module")
def new_tasks_source():
    return json.loads((PLUS_DIR / "new_tasks_source.json").read_text())


def _gold_actions(task: dict) -> list:
    return (task.get("evaluation_criteria") or {}).get("actions") or []


def _task(tasks: list, tid: str) -> dict:
    return next(t for t in tasks if t["id"] == tid)


def _action(task: dict, name: str) -> dict:
    return next(a for a in _gold_actions(task) if a["name"] == name)


def _variant_index(db: dict) -> dict:
    """(product name, frozen options) -> (item_id, price, available).

    Product ids and item ids are remapped between the two worlds, but product
    names and option sets are not, so this is the stable join key.
    """
    index = {}
    names = [p["name"] for p in db["products"].values()]
    assert len(names) == len(set(names)), "product names are not unique"
    for product in db["products"].values():
        for iid, variant in product["variants"].items():
            key = (product["name"], frozenset(variant["options"].items()))
            assert key not in index, f"duplicate variant key {key}"
            index[key] = (iid, variant["price"], variant["available"])
    return index


def _order_user(db: dict, order_id: str) -> dict:
    return db["users"][db["orders"][order_id]["user_id"]]


def _gc_balance(db: dict, pm_id: str) -> float:
    for user in db["users"].values():
        if pm_id in user["payment_methods"]:
            return user["payment_methods"][pm_id]["balance"]
    raise KeyError(pm_id)


# ---------------------------------------------------------------------------
# 1. Freshness + registration + splits
# ---------------------------------------------------------------------------


def test_committed_outputs_carry_no_canonical_tokens():
    """Canonical ids, emails, and retired policy phrases must not appear in
    the committed files. This is the standalone replacement for the retired
    freshness pin: retail_plus is edited directly, so the scan targets the
    committed files themselves. Price movement, derangement, and affine
    recovery are asserted against the committed db further down."""
    tokens = expectations.canonical_identifier_tokens()
    # Guard the guard: an empty token family would make the scan below pass
    # for the wrong reason.
    assert set(tokens) == {
        "user_id",
        "order_id",
        "payment_id",
        "tracking_id",
        "product_id",
        "email",
    }
    for label, family in tokens.items():
        assert family, f"no canonical {label} tokens to scan for"
    assert expectations.RETIRED_WINDOW_PHRASES
    assert expectations.collect_committed_leakage() == []


def test_registered():
    assert "retail_plus" in registry.get_domains()
    assert "retail_plus" in registry.get_task_sets()


def test_environment_loads():
    env = get_environment()
    assert env.get_domain_name() == "retail_plus"
    with pytest.raises(ValueError):
        get_environment(solo_mode=True)


def test_task_loader_returns_all_tasks(committed_tasks):
    assert len(get_tasks(None)) == len(committed_tasks) == 134


def test_splits(committed_tasks):
    splits = json.loads((PLUS_DIR / "split_tasks.json").read_text())
    retail_splits = json.loads((RETAIL_DIR / "split_tasks.json").read_text())
    ids = {t["id"] for t in committed_tasks}
    assert set(splits["base"]) == ids
    assert NEW_TASK_IDS <= set(splits["test"])
    # train is untouched; new tasks land in base + test only
    assert splits["train"] == retail_splits["train"]
    assert not NEW_TASK_IDS & set(splits["train"])


def test_refund_window_consistency(spec):
    """Policy and the delta spec carry the retail_plus refund window; the tool
    docstring carries NO policy content at all (2026-08-19 lever-criterion
    slim-down: the schema is read by downstream test agents, so a value stated
    there is env-revealed and can never discriminate between policies)."""
    policy = (PLUS_DIR / "policy.md").read_text()
    new_window = spec["refund_window"]["new"]
    assert policy.count("3 to 6 business days") == 2
    assert "5 to 7 business days" not in policy
    plus_doc = RetailPlusTools.cancel_pending_order.__doc__
    assert new_window not in plus_doc
    assert spec["refund_window"]["old"] not in plus_doc
    assert "business days" not in plus_doc
    assert "gift card" not in plus_doc
    assert "'no longer needed'" not in plus_doc
    # canonical tools really do carry the old window (else this override is dead)
    assert spec["refund_window"]["old"] in RetailTools.cancel_pending_order.__doc__


def test_one_shot_docstring_slims():
    """The one-shot lock reveals are stripped from the plus tool schema
    (2026-08-19 lever-criterion slim-down, second pass): canonical retail's
    modify_pending_order_items teaches "this function can only be called
    once" and exchange_delivered_order_items teaches "return or exchange can
    be only done once by the agent" — both are policy content a downstream
    test agent reads for free, voiding the one-shot facts as client-held
    material. The plus overrides drop exactly those sentences; everything
    else in the docstrings is preserved."""
    modify_doc = RetailPlusTools.modify_pending_order_items.__doc__
    exchange_doc = RetailPlusTools.exchange_delivered_order_items.__doc__
    assert "can only be called once" not in modify_doc
    assert "only done once" not in exchange_doc
    assert "once" not in modify_doc
    assert "once" not in exchange_doc
    # non-policy content is preserved
    assert "same product type" in modify_doc
    assert "explicit user confirmation (yes/no)" in modify_doc
    assert "same product type" in exchange_doc
    assert "explicit user confirmation (yes/no)" in exchange_doc
    # canonical tools really do carry the reveals (else these overrides are dead)
    assert (
        "this function can only be called once"
        in RetailTools.modify_pending_order_items.__doc__
    )
    assert (
        "return or exchange can be only done once by the agent"
        in RetailTools.exchange_delivered_order_items.__doc__
    )
    # return_delivered_order_items carries no once-only reveal in canonical
    # retail, so the plus toolkit deliberately does NOT override it.
    assert "once" not in RetailTools.return_delivered_order_items.__doc__
    assert "return_delivered_order_items" not in RetailPlusTools.__dict__


# ---------------------------------------------------------------------------
# 2. Solvability: gold replay with the exact expected-failure set
# ---------------------------------------------------------------------------


def test_gold_actions_replay(committed_tasks):
    unexpected, missing = [], []
    for task in committed_tasks:
        env = get_environment()
        failed = set()
        for action in _gold_actions(task):
            try:
                env.make_tool_call(
                    action["name"],
                    requestor="assistant",
                    **(action.get("arguments") or {}),
                )
            except Exception as exc:  # noqa: BLE001 - collecting all failures
                failed.add(action["action_id"])
                if action["action_id"] not in EXPECTED_REPLAY_FAILURES.get(
                    task["id"], set()
                ):
                    unexpected.append(f"{task['id']}/{action['action_id']}: {exc}")
        for action_id in EXPECTED_REPLAY_FAILURES.get(task["id"], set()) - failed:
            missing.append(f"{task['id']}/{action_id} was expected to fail but passed")
    assert not unexpected, "\n".join(unexpected)
    assert not missing, "\n".join(missing)


def test_new_tasks_replay_clean(committed_tasks):
    assert not NEW_TASK_IDS & set(EXPECTED_REPLAY_FAILURES)


# ---------------------------------------------------------------------------
# 3. Discrimination: permutation, re-pricing, boundary flips
# ---------------------------------------------------------------------------


def test_item_id_permutation_is_derangement(canonical_db, committed_db):
    """Within every product the plus world reuses exactly the canonical id
    strings, but no id may still denote its canonical option set."""
    old_products = {p["name"]: p for p in canonical_db["products"].values()}
    fixed_points = []
    for product in committed_db["products"].values():
        old = old_products[product["name"]]
        assert set(product["variants"]) == set(old["variants"]), product["name"]
        for iid, variant in product["variants"].items():
            if variant["options"] == old["variants"][iid]["options"]:
                fixed_points.append(f"{product['name']}/{iid}")
    assert not fixed_points, f"ids still meaning their canonical variant: {fixed_points}"


def test_product_ids_replaced(canonical_db, committed_db):
    """Product ids are freshly drawn: no canonical product id survives, so a
    memorized name->product-id mapping never resolves."""
    old_ids = set(canonical_db["products"])
    new_ids = set(committed_db["products"])
    assert len(new_ids) == len(old_ids)
    assert not old_ids & new_ids


def test_all_prices_moved(spec, canonical_db, committed_db):
    """Every variant price changed by at least max(min_abs_delta, min_rel_delta)
    and availability was preserved."""
    old_index = _variant_index(canonical_db)
    new_index = _variant_index(committed_db)
    assert set(old_index) == set(new_index)
    min_abs = spec["pricing"]["min_abs_delta"]
    min_rel = spec["pricing"]["min_rel_delta"]
    too_close = []
    for key, (_, old_price, old_avail) in old_index.items():
        _, new_price, new_avail = new_index[key]
        assert new_avail == old_avail, f"availability changed for {key}"
        if abs(new_price - old_price) < max(min_abs, min_rel * old_price) - 1e-9:
            too_close.append((key, old_price, new_price))
    assert not too_close, f"prices too close to canonical: {too_close[:5]}"


def test_price_ranks_preserved_within_product(canonical_db, committed_db):
    """Cheapest/most-expensive style golds survive because re-pricing re-sorts
    draws into the canonical within-product order."""
    old_index = _variant_index(canonical_db)
    new_index = _variant_index(committed_db)
    by_product = {}
    for key in old_index:
        by_product.setdefault(key[0], []).append(key)
    for name, keys in by_product.items():
        # (price, item_id) mirrors the generator's canonical tie-break, so a
        # canonical price tie can't make this assertion order-dependent.
        old_order = sorted(keys, key=lambda k: (old_index[k][1], k[1]))
        new_order = sorted(keys, key=lambda k: (new_index[k][1], k[1]))
        assert old_order == new_order, f"price order changed within {name}"


def test_affine_fit_cannot_recover_prices(canonical_db, committed_db):
    """A single affine map old->new must not recover more than 5% of prices
    within max($0.50, 1%) — i.e. no global rescale to reverse out."""
    old_index = _variant_index(canonical_db)
    new_index = _variant_index(committed_db)
    xs = [old_index[k][1] for k in old_index]
    ys = [new_index[k][1] for k in old_index]
    n = len(xs)
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    var_x = sum((x - mean_x) ** 2 for x in xs)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / var_x
    intercept = mean_y - slope * mean_x
    recoverable = sum(
        1
        for x, y in zip(xs, ys)
        if abs(slope * x + intercept - y) <= max(0.5, 0.01 * y)
    )
    assert recoverable / n <= 0.05, (
        f"affine fit recovers {recoverable}/{n} prices"
    )


def test_gift_card_balances_are_whole_dollars(committed_db):
    for user in committed_db["users"].values():
        for pm in user["payment_methods"].values():
            if pm["source"] == "gift_card":
                assert pm["balance"] == int(pm["balance"]), pm["id"]


# --- new-task boundary flips (cross-world truths that cannot live in the spec
# relations section, because their whole point is to differ between worlds) ---


def test_117_gift_card_boundary_straddle(
    committed_tasks, committed_db, canonical_db
):
    """Plus price diff < pinned balance < canonical price diff. A memorized
    agent concludes the gift card cannot cover the difference and pays with
    the credit card; the true gold pays with the gift card."""
    task = _task(committed_tasks, "117")
    exchange = _action(task, "exchange_delivered_order_items")
    assert exchange["arguments"]["payment_method_id"].startswith("gift_card")

    new_index = _variant_index(committed_db)
    old_index = _variant_index(canonical_db)
    old_key = ("Mechanical Keyboard", frozenset(
        {"switch type": "clicky", "backlight": "white", "size": "80%"}.items()
    ))
    new_key = ("Mechanical Keyboard", frozenset(
        {"switch type": "clicky", "backlight": "none", "size": "80%"}.items()
    ))
    plus_diff = round(new_index[new_key][1] - new_index[old_key][1], 2)
    canonical_diff = round(old_index[new_key][1] - old_index[old_key][1], 2)
    balance = _gc_balance(committed_db, exchange["arguments"]["payment_method_id"])
    assert 0 < plus_diff < balance < canonical_diff, (
        f"straddle broken: plus {plus_diff} / balance {balance} / "
        f"canonical {canonical_diff}"
    )
    # the ghost decision must not sit within a rounding error of the boundary
    assert balance - plus_diff >= 1.0
    assert canonical_diff - balance >= 1.0


def test_123_balance_sufficiency_flips(
    committed_tasks, committed_db, canonical_db, new_tasks_source
):
    """Canonically the gift card cannot cover the order; in retail_plus it can.
    An agent trusting the memorized balance refuses a request it should make."""
    plus_task = _task(committed_tasks, "123")
    swap = _action(plus_task, "modify_pending_order_payment")
    order = committed_db["orders"][swap["arguments"]["order_id"]]
    plus_total = order["payment_history"][0]["amount"]
    plus_balance = _gc_balance(committed_db, swap["arguments"]["payment_method_id"])
    assert plus_balance >= plus_total

    src_task = _task(new_tasks_source, "123")
    src_swap = _action(src_task, "modify_pending_order_payment")
    old_order = canonical_db["orders"][src_swap["arguments"]["order_id"]]
    old_total = old_order["payment_history"][0]["amount"]
    old_balance = _gc_balance(canonical_db, src_swap["arguments"]["payment_method_id"])
    assert old_balance < old_total


def test_115_gift_card_stays_insufficient(committed_tasks, committed_db):
    task = _task(committed_tasks, "115")
    order_id = _action(task, "get_order_details")["arguments"]["order_id"]
    user = _order_user(committed_db, order_id)
    balances = [
        pm["balance"]
        for pm in user["payment_methods"].values()
        if pm["source"] == "gift_card"
    ]
    total = committed_db["orders"][order_id]["payment_history"][0]["amount"]
    assert len(balances) == 1 and balances[0] < total


def test_new_task_amounts_differ_from_canonical(committed_tasks, new_tasks_source):
    """Every dollar amount in the new tasks' evaluation criteria must have been
    rewritten away from its canonical-space value."""
    for src in new_tasks_source:
        plus = _task(committed_tasks, src["id"])
        src_comm = src["evaluation_criteria"]["communicate_info"]
        plus_comm = plus["evaluation_criteria"]["communicate_info"]
        assert len(src_comm) == len(plus_comm)
        for old_value, new_value in zip(src_comm, plus_comm):
            assert old_value != new_value, (
                f"task {src['id']}: communicate_info {old_value!r} not rewritten"
            )


# ---------------------------------------------------------------------------
# 4. New-task structure pins (design intent the spec cannot express)
# ---------------------------------------------------------------------------

WRITE_TOOLS = {
    "cancel_pending_order",
    "exchange_delivered_order_items",
    "modify_pending_order_address",
    "modify_pending_order_items",
    "modify_pending_order_payment",
    "modify_user_address",
    "return_delivered_order_items",
}


def test_new_tasks_present(committed_tasks):
    ids = {t["id"] for t in committed_tasks}
    assert NEW_TASK_IDS <= ids
    for tid in NEW_TASK_IDS:
        task = _task(committed_tasks, tid)
        assert task["evaluation_criteria"]["reward_basis"] == ["DB", "NL_ASSERTION"]


def test_refusal_tasks_have_no_writes(committed_tasks):
    """The refusal tasks must end with an untouched database: 115 (insufficient
    gift card), 121 (someone else's order), 126 (unverifiable caller), and the
    ported write-free refusals 12/25/50/57/65."""
    for tid in ("12", "25", "50", "57", "65", "115", "121", "126"):
        task = _task(committed_tasks, tid)
        writes = [a for a in _gold_actions(task) if a["name"] in WRITE_TOOLS]
        assert not writes, f"task {tid} gold must not write"


def test_refusal_tasks_carry_nl_assertions(committed_tasks):
    """A write-free gold makes 'db unchanged' the entire DB reward, so the
    discriminating refusal must be pinned in NL. Pre-audit, 12/25/50/57/65
    had neither writes nor assertions — an agent that did anything
    non-destructive passed them."""
    for tid in ("12", "25", "50", "57", "65", "115", "121", "126"):
        task = _task(committed_tasks, tid)
        assert task["evaluation_criteria"]["nl_assertions"], (
            f"task {tid} needs nl_assertions to have any discriminating reward"
        )


def test_116_pins_new_refund_window(committed_tasks):
    task = _task(committed_tasks, "116")
    assert any(
        "3 to 6 business days" in a
        for a in task["evaluation_criteria"]["nl_assertions"]
    )
    assert _action(task, "cancel_pending_order")["arguments"]["reason"] == (
        "no longer needed"
    )


def test_118_exchange_targets_unique_available_variant(
    committed_tasks, committed_db
):
    """The options the user describes (gold / leather band / AMOLED) must map
    to exactly one available variant — the gold's new item id."""
    task = _task(committed_tasks, "118")
    exchange = _action(task, "exchange_delivered_order_items")
    product_id = _action(task, "get_product_details")["arguments"]["product_id"]
    variants = committed_db["products"][product_id]["variants"]
    matches = [
        iid
        for iid, v in variants.items()
        if v["available"]
        and v["options"]
        == {"color": "gold", "band material": "leather", "display": "AMOLED"}
    ]
    assert matches == exchange["arguments"]["new_item_ids"]


def test_119_modifies_two_items_of_same_product(committed_tasks, committed_db):
    task = _task(committed_tasks, "119")
    modify = _action(task, "modify_pending_order_items")
    assert len(modify["arguments"]["item_ids"]) == 2
    product_id = _action(task, "get_product_details")["arguments"]["product_id"]
    variants = committed_db["products"][product_id]["variants"]
    for iid in modify["arguments"]["item_ids"] + modify["arguments"]["new_item_ids"]:
        assert iid in variants, f"{iid} is not a variant of product {product_id}"


def test_120_single_exchange_only(committed_tasks):
    task = _task(committed_tasks, "120")
    exchanges = [
        a for a in _gold_actions(task) if a["name"] == "exchange_delivered_order_items"
    ]
    assert len(exchanges) == 1
    assert len(exchanges[0]["arguments"]["item_ids"]) == 1


def test_122_refund_goes_to_original_payment_method(committed_tasks, committed_db):
    task = _task(committed_tasks, "122")
    ret = _action(task, "return_delivered_order_items")
    order = committed_db["orders"][ret["arguments"]["order_id"]]
    original = order["payment_history"][0]["payment_method_id"]
    assert ret["arguments"]["payment_method_id"] == original
    assert original.startswith("paypal")
    # the tempting-but-illegal destination must actually exist on the account
    user = _order_user(committed_db, ret["arguments"]["order_id"])
    assert any(
        pm["source"] == "credit_card" for pm in user["payment_methods"].values()
    )


def test_124_return_refunds_to_existing_gift_card(committed_tasks, committed_db):
    """The suite's only positive coverage of the SECOND legal refund
    destination: the return refunds to the user's existing gift card, which is
    not the order's original payment method (that one is PayPal)."""
    task = _task(committed_tasks, "124")
    ret = _action(task, "return_delivered_order_items")
    order = committed_db["orders"][ret["arguments"]["order_id"]]
    original = order["payment_history"][0]["payment_method_id"]
    destination = ret["arguments"]["payment_method_id"]
    assert destination.startswith("gift_card") and destination != original
    assert original.startswith("paypal")
    user = _order_user(committed_db, ret["arguments"]["order_id"])
    assert destination in user["payment_methods"]


def test_125_single_modify_only(committed_tasks, committed_db):
    """One item modification, then the follow-up must be refused — the
    modify twin of 120's one-exchange probe."""
    task = _task(committed_tasks, "125")
    modifies = [
        a for a in _gold_actions(task) if a["name"] == "modify_pending_order_items"
    ]
    assert len(modifies) == 1
    assert len(modifies[0]["arguments"]["item_ids"]) == 1
    order = committed_db["orders"][modifies[0]["arguments"]["order_id"]]
    assert order["status"] == "pending"


def test_126_identity_grounds_nowhere(committed_tasks, committed_db):
    """The terminal-auth-failure caller must not accidentally match a db user,
    and the gold must be empty (an untouched db is the entire DB reward)."""
    task = _task(committed_tasks, "126")
    assert _gold_actions(task) == []
    matches = [
        u
        for u in committed_db["users"].values()
        if u["name"] == {"first_name": "Nadia", "last_name": "Ashford"}
    ]
    assert not matches


def test_127_cancel_refunds_original_gift_card(committed_tasks, committed_db):
    """Cancelling a gift-card-paid order pins the 'immediately' arm of the
    changed refund sentence (116 pins the 3-6 business day arm)."""
    task = _task(committed_tasks, "127")
    cancel = _action(task, "cancel_pending_order")
    order = committed_db["orders"][cancel["arguments"]["order_id"]]
    assert order["payment_history"][0]["payment_method_id"].startswith("gift_card")
    assert cancel["arguments"]["reason"] == "ordered by mistake"
    assert any(
        "immediately" in a for a in task["evaluation_criteria"]["nl_assertions"]
    )


def test_128_delivered_address_refusal_updates_default_only(
    committed_tasks, committed_db
):
    """No order write is allowed (the order is delivered); the only write is
    the default-address update, whose fields equal the delivered order's
    address, so the gold grounds in the db."""
    task = _task(committed_tasks, "128")
    names = [a["name"] for a in _gold_actions(task)]
    assert "modify_pending_order_address" not in names
    move = _action(task, "modify_user_address")
    order_id = _action(task, "get_order_details")["arguments"]["order_id"]
    order = committed_db["orders"][order_id]
    assert order["status"] == "delivered"
    new_address = {k: v for k, v in move["arguments"].items() if k != "user_id"}
    assert new_address == order["address"]


# ---------------------------------------------------------------------------
# 5. Leakage scans (belt and braces on top of the generator's own gate)
# ---------------------------------------------------------------------------


def test_no_canonical_names_in_outputs(spec, committed_tasks, committed_db):
    blob = json.dumps(committed_tasks) + json.dumps(committed_db)
    for old_name in list(spec["first_names"]) + list(spec["last_names"]):
        assert not re.search(rf"\b{old_name}\b", blob), (
            f"canonical name leaked: {old_name}"
        )


def test_no_canonical_emails_in_outputs(canonical_db, committed_tasks, committed_db):
    blob = json.dumps(committed_tasks) + json.dumps(committed_db)
    for user in canonical_db["users"].values():
        assert user["email"] not in blob, f"canonical email leaked: {user['email']}"
