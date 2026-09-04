"""Gates for the retail_plus hyper fact decomposition.

The retail_plus section schemas under data/tau2/hyper/sops/retail_plus/ — and
their support files, the retail_plus_sop.md runbook and the
retail_plus_response_phrasing.yaml rule pack — were originally generated from
the canonical retail counterparts; since the 2026-08-04 standalone cutover
the tree is edited directly, and the porter tooling is not part of this
release. The expectations the porter used to supply (forbidden canonical
phrases, the legacy / hierarchy section lists) are pinned in
tests/plus_support/retail_plus.py. These tests enforce integrity and reference
closure of the committed tree: no canonical sops path or retired policy phrase
survives, the structural fields hold, every fact-id reference resolves, every
path a schema mentions exists, every selected response rule resolves in the
plus pack and is retail_plus-safe, the runbook states the same refund window
as the fact corpora, and the policy gates keep their documented shape.
"""

import json
import re
from pathlib import Path

import yaml
from plus_support import retail_plus as expectations
from plus_support.leakage import iter_fact_id_references, scan_leakage

REPO_ROOT = Path(__file__).resolve().parents[2]
RETAIL_PLUS_ROOT = REPO_ROOT / "data" / "tau2" / "hyper" / "sops" / "retail_plus"
SCHEMA_PATHS = sorted((RETAIL_PLUS_ROOT / "sections").glob("*/schema.json"))


def test_committed_tree_holds_standalone_invariants():
    """Leakage and integrity gates on the committed tree (no regeneration).

    The freshness pin and canonical-parity checks retired with the standalone
    cutover: the tree is edited directly, so the invariants are asserted on
    the committed files themselves.
    """
    committed = [
        path
        for path in sorted(RETAIL_PLUS_ROOT.rglob("*"))
        if path.is_file() and path.suffix in {".json", ".md"}
    ]
    assert committed, "committed retail_plus sops tree is missing"
    assert expectations.SCHEMA_FORBIDDEN_PATTERNS
    scan_leakage(committed, list(expectations.SCHEMA_FORBIDDEN_PATTERNS))

    schemas = {
        section_id: json.loads(
            (RETAIL_PLUS_ROOT / "sections" / section_id / "schema.json").read_text()
        )
        for section_id in [
            *expectations.LEGACY_SECTION_IDS,
            *expectations.HIERARCHY_SECTION_IDS,
        ]
    }
    for section_id, schema in schemas.items():
        assert schema["domain"] == expectations.DOMAIN_NEW, section_id
        context = schema.get("response_phrasing_context")
        if context is not None:
            assert "source_task_id" not in context, section_id
            rules_path = context.get("rules_path")
            assert rules_path == expectations.RESPONSE_PACK_RULES_PATH, section_id
    for section_id in expectations.LEGACY_SECTION_IDS:
        schema = schemas[section_id]
        assert schema.get("studio_hidden"), section_id
        assert schema["transformations"] == [
            {
                "representation": "support_transcripts",
                "stub_path": (
                    "tau2/hyper/sops/retail_plus/sections/"
                    f"{section_id}/transcript_induction_001.md"
                ),
                "artifacts": None,
            }
        ], section_id
        records = sorted(
            (RETAIL_PLUS_ROOT / "sections" / section_id / "training_records").glob(
                "case_*.md"
            )
        )
        assert len(records) == len(schema["transcripts"]), section_id
    for section_id in expectations.HIERARCHY_SECTION_IDS:
        assert "domain_hierarchy" in schemas[section_id], section_id
        assert "policy_structure" in schemas[section_id], section_id
        assert schemas[section_id].get("global_rules_path") == (
            f"tau2/hyper/sops/{expectations.DOMAIN_NEW}/global_rules.json"
        ), section_id

    defined = {fact["id"] for schema in schemas.values() for fact in schema["facts"]}
    for section_id, schema in schemas.items():
        unresolved = iter_fact_id_references(schema) - defined
        assert not unresolved, f"{section_id}: unresolved fact ids {sorted(unresolved)}"

    # Values-registry consistency: policy-value statements must carry the
    # delta_spec value (the spec stays live as the domain values registry;
    # mirrors the airline suite's expectations block).
    spec = expectations.load_spec()
    window = spec["policy_edits"][0]["new"]
    assert spec["policy_edits"][0]["old"] == "5 to 7 business days"
    assert spec["refund_window"]["new"].replace("-", " to ") == window

    window_fact_ids = {
        "card_or_paypal_cancel_refund_timeline",
        "payment_change_refund_timelines",
    }
    stated = set()
    for section_id, schema in schemas.items():
        for fact in schema["facts"]:
            statement = fact["statement"]
            if fact["id"] in window_fact_ids:
                assert window in statement, (
                    f"{section_id}/{fact['id']} does not state {window!r}: {statement}"
                )
                stated.add(fact["id"])
            else:
                # No other fact may quote any refund window spelling: a
                # divergent window in a fact statement is either canonical
                # leakage or a value drifting from the registry.
                assert not re.search(r"\d+(?: to |-)\d+ business days", statement), (
                    f"{section_id}/{fact['id']} quotes a business-day window"
                    f" outside the registry-pinned facts: {statement}"
                )
    assert stated == window_fact_ids, (
        f"window facts missing: {window_fact_ids - stated}"
    )


def _iter_path_references(value):
    """Every repo path a schema node references.

    Keys ending in "path" hold a single data-relative path; "paths" keys
    (domain_constraints.source_paths) hold lists mixing data-relative
    (tau2/...) and repo-relative (src/...) entries.
    """
    if isinstance(value, dict):
        for key, child in value.items():
            if (
                key.endswith("path")
                and isinstance(child, str)
                and child.startswith("tau2/")
            ):
                yield child
            elif key.endswith("paths") and isinstance(child, list):
                yield from (item for item in child if isinstance(item, str))
            else:
                yield from _iter_path_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_path_references(child)


def test_all_schema_paths_and_response_rules_resolve():
    """Every retail_plus schema dependency is present and domain-safe."""
    assert len(SCHEMA_PATHS) == 14
    selected_rule_ids = set()
    contexts = 0
    for schema_path in [*SCHEMA_PATHS, RETAIL_PLUS_ROOT / "global_rules.json"]:
        schema = json.loads(schema_path.read_text())
        assert "source_task_id" not in json.dumps(schema)
        references = list(_iter_path_references(schema))
        assert references, schema_path
        for reference in references:
            root = REPO_ROOT / "data" if reference.startswith("tau2/") else REPO_ROOT
            assert (root / reference).exists(), reference
        context = schema.get("response_phrasing_context")
        if context:
            contexts += 1
            assert context["rules_path"] == (
                "tau2/hyper/response_phrasing/retail_plus_response_phrasing.yaml"
            )
            selected_rule_ids.update(context["selected_rule_ids"])
    assert contexts == 9, "each legacy transcript-induction section carries a context"

    rules_path = (
        REPO_ROOT
        / "data"
        / "tau2"
        / "hyper"
        / "response_phrasing"
        / "retail_plus_response_phrasing.yaml"
    )
    rules = yaml.safe_load(rules_path.read_text())["rules"]
    by_id = {rule["id"]: rule for rule in rules}
    assert selected_rule_ids <= by_id.keys()
    for rule in rules:
        assert "retail_plus" in rule["domain_safety"]
    for rule_id in selected_rule_ids:
        # Retail deliberately selects no_generic_service_invitations despite
        # safe: false; the pack's safe_if condition is mirrored by the
        # schemas' context notes. Every other selected rule must be safe.
        safety = by_id[rule_id]["domain_safety"]["retail_plus"]
        assert safety["safe"] is True or safety.get("safe_if"), rule_id


def test_refund_window_is_consistent_between_handbook_and_schemas():
    """The ported runbook and fact corpora state the same refund window."""
    handbook = (RETAIL_PLUS_ROOT.parent / "retail_plus_sop.md").read_text()
    assert handbook.count("3 to 6 business days") == 2
    assert "5 to 7 business days" not in handbook

    schema_text = "\n".join(path.read_text() for path in SCHEMA_PATHS)
    assert "3 to 6 business days" in schema_text
    assert "5 to 7 business days" not in schema_text

    record_text = "\n".join(
        path.read_text()
        for path in RETAIL_PLUS_ROOT.glob("sections/*/training_records/case_*.md")
    )
    assert record_text.count("3 to 6 business days") == 5
    assert "5 to 7 business days" not in record_text


def test_source_policy_scope_and_delivered_order_gates_are_lossless():
    """Information reads and status checks must survive the Plus decomposition."""
    handbook = (RETAIL_PLUS_ROOT.parent / "retail_plus_sop.md").read_text()
    global_rules = json.loads((RETAIL_PLUS_ROOT / "global_rules.json").read_text())
    foundations = json.loads(
        (RETAIL_PLUS_ROOT / "sections/service_foundations/schema.json").read_text()
    )
    delivered = json.loads(
        (RETAIL_PLUS_ROOT / "sections/manage_delivered_order/schema.json").read_text()
    )

    assert "provide information about their own profile" in handbook
    assert "complete set of customer-record changes" in handbook
    assert "These limits on record changes do not prevent" in handbook
    assert "A tool call and a customer-facing response must be separate" in handbook
    assert "check the order's current status" in handbook
    assert "You cannot do anything else through this channel" not in handbook

    foundation_facts = {fact["id"]: fact["statement"] for fact in foundations["facts"]}
    assert foundation_facts["customer_information_lookup_allowed"] == (
        "After authentication, customer care may provide information about the "
        "customer's own profile, their orders, and products related to their orders."
    )
    assert (
        "customer record changes"
        in foundation_facts["authorized_actions_are_closed_scope"]
    )

    delivered_facts = {fact["id"]: fact["statement"] for fact in delivered["facts"]}
    for fact_id in (
        "return_requires_delivered_order",
        "exchange_requires_delivered_order",
    ):
        assert "must check the order's current status" in delivered_facts[fact_id]
        assert "current status is delivered" in delivered_facts[fact_id]
    assert (
        "must confirm the order identifier and the exact list of items"
        in (delivered_facts["return_requires_order_id_and_item_list"])
    )

    rule_ids = {rule["id"] for rule in global_rules["rules"]}
    assert "one_tool_call_or_customer_response_at_a_time" in rule_ids

    export_dir = (
        RETAIL_PLUS_ROOT / "sections/service_foundations/helpdesk_automation_export_001"
    )
    manifest = json.loads((export_dir / "eval_manifest.json").read_text())
    fact_map = json.loads((export_dir / "fact_map.json").read_text())
    authored = json.loads((export_dir / "authored_export.json").read_text())
    fact_id = "customer_information_lookup_allowed"
    assert fact_id in manifest["authoritative_fact_ids"]
    assert fact_map["facts"][fact_id]["object_ids"] == ["CONTRACT-1001"]
    action_contract = next(
        contract
        for contract in authored["policy_contracts"]
        if contract["contract_id"] == "CONTRACT-1001"
    )
    assert action_contract["information_access"] == {
        "requires_authenticated_customer": True,
        "allowed_information": [
            {
                "resource": "customer_profile",
                "scope": "the authenticated customer's own profile",
            },
            {
                "resource": "order",
                "scope": "orders owned by the authenticated customer",
            },
            {
                "resource": "product",
                "scope": "products related to the authenticated customer's orders",
            },
        ],
    }


def test_legacy_domains_are_documented_as_frozen_ablation_baselines():
    maintenance_policy = (REPO_ROOT / "AGENTS.md").read_text()
    assert "deprecated, frozen legacy" in maintenance_policy
    assert "future migration or" in maintenance_policy
    assert "ablation study" in maintenance_policy
    assert "do not backport routine" in maintenance_policy


def test_exchange_refund_destination_is_policy_faithful():
    """Exchange price-difference refunds must not inherit the returns-only wall.

    data/tau2/domains/retail_plus/policy.md grants the original-or-existing-
    gift-card limit to returns only, exchange_delivered_order_items accepts any
    payment method saved on the profile, and gold tasks exchange onto a
    different card or an off-order PayPal. The 2026-08-06 audit found the
    decomposition re-imposing the returns wall on exchanges (inherited from the
    frozen canonical baseline), which makes those gold actions unreachable for
    a bundle-faithful agent.
    """
    handbook = (RETAIL_PLUS_ROOT.parent / "retail_plus_sop.md").read_text()
    assert "Same for returns" not in handbook
    assert "any payment method saved on the profile" in handbook

    delivered = json.loads(
        (RETAIL_PLUS_ROOT / "sections/manage_delivered_order/schema.json").read_text()
    )
    delivered_facts = {fact["id"]: fact["statement"] for fact in delivered["facts"]}
    assert delivered_facts["exchange_refund_destination_any_saved_payment_method"] == (
        "When an exchange produces a refund of the price difference, the "
        "customer chooses the payment method that receives it from the methods "
        "saved on their profile; it does not have to be the original payment "
        "method — the two-destination limit applies only to return refunds. "
        "The chosen method is recorded on the exchange at submission and "
        "cannot be changed afterward."
    )

    # The retired reading is banned tree-wide, including the regenerated Slack
    # capture, its manifests, and the training records.
    tree_text = "\n".join(
        path.read_text()
        for path in sorted(RETAIL_PLUS_ROOT.rglob("*"))
        if path.is_file() and path.suffix in {".json", ".md"}
    )
    for retired in (
        "exchange_refund_destination_original_or_existing_gift_card",
        "return_or_exchange_refund_destination_limits",
        "an exchange that settles out as money back follows the same two destinations",
        "Refunds for exchanges or returns go to the original payment method",
    ):
        assert retired not in tree_text, retired

    # Domain anchor: gold tasks exercise exchanges refunded to methods that
    # never charged the order. If this stops holding, the domain moved and the
    # facts above must be revisited together with it.
    db = json.loads((REPO_ROOT / "data/tau2/domains/retail_plus/db.json").read_text())
    tasks = json.loads(
        (REPO_ROOT / "data/tau2/domains/retail_plus/tasks.json").read_text()
    )
    non_original_exchanges = 0
    for task in tasks:
        actions = (task.get("evaluation_criteria") or {}).get("actions") or []
        for action in actions:
            if action.get("name") != "exchange_delivered_order_items":
                continue
            order = db["orders"][action["arguments"]["order_id"]]
            charged_with = {
                event["payment_method_id"]
                for event in order["payment_history"]
                if event["transaction_type"] == "payment"
            }
            if action["arguments"]["payment_method_id"] not in charged_with:
                non_original_exchanges += 1
    assert non_original_exchanges >= 2


def test_transfer_conditions_are_a_closed_set():
    """The decomposition must carry the restrictive half of the transfer rule.

    data/tau2/domains/retail_plus/policy.md licenses transfer "if and only if"
    the request cannot be handled, and the transfer_to_human_agents tool
    contract enumerates exactly the explicit-ask and cannot-solve conditions.
    The 2026-08-07 audit found every transfer fact stated in the permissive
    direction ("transfer when X") with nothing owning the no-fourth-condition
    boundary, leaving a bundle-faithful agent free to invent extra transfer
    conditions. The closed-set fact is owned by the recorded working session,
    whose launch-signoff meeting already carried the boundary verbatim.
    """
    policy = (REPO_ROOT / "data/tau2/domains/retail_plus/policy.md").read_text()
    assert "if and only if" in policy

    handbook = (RETAIL_PLUS_ROOT.parent / "retail_plus_sop.md").read_text()
    assert "And that's the whole list." in handbook

    foundations = json.loads(
        (RETAIL_PLUS_ROOT / "sections/service_foundations/schema.json").read_text()
    )
    foundation_facts = {fact["id"]: fact["statement"] for fact in foundations["facts"]}
    assert foundation_facts["transfer_conditions_are_closed"] == (
        "An explicit customer request for a person, escalation of an "
        "unsupported request after the limit is explained, and genuinely "
        "unclear handling are the only conditions that produce a transfer; "
        "customer frustration, low confidence, or inconvenience alone does not."
    )

    transferring = json.loads(
        (RETAIL_PLUS_ROOT / "sections/transferring_to_person/schema.json").read_text()
    )
    transfer_fact_ids = {fact["id"] for fact in transferring["facts"]}
    assert "transfer_only_under_stated_conditions" in transfer_fact_ids
    carriers = [
        transcript["id"]
        for transcript in transferring["transcripts"]
        if "transfer_only_under_stated_conditions" in transcript["included_fact_ids"]
    ]
    assert carriers, "closed-set mirror fact has no transcript carrier"

    global_rules = json.loads((RETAIL_PLUS_ROOT / "global_rules.json").read_text())
    rules = global_rules if isinstance(global_rules, list) else global_rules["rules"]
    transfer_rule = next(
        rule
        for rule in rules
        if rule["id"] == "transfer_on_request_escalation_or_uncertainty"
    )
    assert "no other situation produces a transfer" in transfer_rule["statement"]
    assert "outside those conditions" in transfer_rule["case_record_requirement"]

    manifest = json.loads(
        (
            RETAIL_PLUS_ROOT
            / "sections/service_foundations/recorded_working_session_001"
            / "eval_manifest.json"
        ).read_text()
    )
    assert "transfer_conditions_are_closed" in manifest["authoritative_fact_ids"]
    closing_finals = [
        decision
        for decision in manifest["decisions"]
        if decision["fact_id"] == "transfer_conditions_are_closed"
        and decision["status"] == "final_current"
    ]
    assert len(closing_finals) == 1
    assert closing_finals[0]["meeting_id"] == "launch_signoff"
    assert closing_finals[0]["evidence_spans"]

    bundle = next(
        bundle
        for bundle in foundations["transformation_bundles"]
        if bundle["id"] == "service_foundations_multimodal"
    )
    session_member = next(
        member
        for member in bundle["members"]
        if member["transformation_id"]
        == "retail_service_foundations_recorded_working_session"
    )
    assert "transfer_conditions_are_closed" in session_member["authoritative_fact_ids"]
