"""Gates for the airline_plus hyper fact decomposition.

The airline_plus section schemas under data/tau2/hyper/sops/airline_plus/
were originally generated from the canonical airline schemas; since the
2026-08-04 standalone cutover the tree is edited directly, and the porter
tooling is not part of this release. delta_spec.yaml stays live as the domain
values registry, and the expectations the porter used to supply (retired fact
ids, forbidden canonical values, the section list) are pinned in
tests/plus_support/airline_plus.py. These tests enforce integrity of the
committed tree: no canonical value or retired fact id survives, every
policy-value statement carries the registry's value, every schema path,
fact-id reference, and response rule resolves, policy values are consistent
between the handbook and the schemas, fact statements are atemporal, and the
handbook front matter matches the domain policy clock.
"""

import json
import re
from pathlib import Path

import yaml
from plus_support import airline_plus as expectations
from plus_support.leakage import iter_fact_id_references, scan_leakage

REPO_ROOT = Path(__file__).resolve().parents[2]
AIRLINE_PLUS_ROOT = REPO_ROOT / "data" / "tau2" / "hyper" / "sops" / "airline_plus"
SCHEMA_PATHS = sorted((AIRLINE_PLUS_ROOT / "sections").glob("*/schema.json"))


def test_committed_tree_holds_standalone_invariants():
    """Leakage, values-registry, and closure gates on the committed tree.

    The freshness pin and canonical-parity checks retired with the standalone
    cutover: the tree is edited directly, so the invariants are asserted on
    the committed files themselves.

    The file list is restricted to the schema/SOP layer rather than an rglob
    of the tree: airline_plus also holds the transformation artifacts, which
    follow a deliberately different leakage policy (narrative asks like
    "three gift cards" are allowed there) and carry their own gates.
    """
    spec = expectations.load_spec()

    section_ids = [*expectations.SOURCE_SECTION_IDS, expectations.GENERATED_SECTION_ID]
    committed = sorted(
        {
            *(
                AIRLINE_PLUS_ROOT / "sections" / section_id / "schema.json"
                for section_id in section_ids
            ),
            *AIRLINE_PLUS_ROOT.glob("*.json"),
            expectations.HYPER_ROOT / expectations.SOP_REL,
            expectations.HYPER_ROOT / expectations.RESPONSE_PACK_REL,
        }
    )
    missing = [path for path in committed if not path.exists()]
    assert not missing, f"committed airline_plus files missing: {missing}"
    assert expectations.SCHEMA_FORBIDDEN_PATTERNS
    assert expectations.RETIRED_FACT_IDS
    scan_leakage(committed, list(expectations.SCHEMA_FORBIDDEN_PATTERNS))
    scan_leakage(
        committed,
        [rf"\b{re.escape(old_id)}\b" for old_id in expectations.RETIRED_FACT_IDS],
        label="Old fact id",
    )

    schemas = {
        section_id: json.loads(
            (AIRLINE_PLUS_ROOT / "sections" / section_id / "schema.json").read_text()
        )
        for section_id in section_ids
    }

    # Values-registry consistency: policy-value statements must carry the
    # delta_spec value (the spec stays live as the domain values registry).
    facts_by_id = {
        fact["id"]: fact["statement"]
        for schema in schemas.values()
        for fact in schema["facts"]
    }
    for tier_key, _tier_label in expectations.BAGGAGE_TIERS:
        for cabin_index, (cabin_key, _cabin_label) in enumerate(
            expectations.BAGGAGE_CABINS
        ):
            new_count = spec["baggage_allowance"][tier_key]["new"][cabin_index]
            statement = facts_by_id[f"baggage_{tier_key}_{cabin_key}_allowance"]
            assert expectations.bags_phrase(new_count) in statement, (
                f"baggage_{tier_key}_{cabin_key}_allowance does not state"
                f" {new_count}: {statement}"
            )
    value_expectations = [
        ("additional_bag_cost", f"${spec['fees']['extra_baggage_fee']['new']}"),
        ("additional_checked_bag_cost", f"${spec['fees']['extra_baggage_fee']['new']}"),
        (
            "insurance_cost_per_passenger",
            f"${spec['fees']['insurance_fee_per_passenger']['new']}",
        ),
        (
            "max_passengers_per_reservation",
            f"at most {spec['limits']['max_passengers']['new']} passengers",
        ),
        (
            "booking_payment_method_limits",
            f"at most {spec['limits']['max_gift_cards']['new']} gift card",
        ),
        ("refund_arrival_window", spec["refund_window"]["new"]),
        (
            "cancelled_flight_certificate_amount",
            f"${spec['compensation']['cancelled_flight_per_passenger']['new']}",
        ),
        (
            "delayed_flight_certificate_amount",
            f"${spec['compensation']['delayed_flight_per_passenger']['new']}",
        ),
    ]
    for fact_id, needle in value_expectations:
        assert needle in facts_by_id[fact_id], (
            f"{fact_id} does not state {needle!r}: {facts_by_id[fact_id]}"
        )

    defined = set(facts_by_id)
    for section_id, schema in schemas.items():
        unresolved = iter_fact_id_references(schema) - defined
        assert not unresolved, f"{section_id}: unresolved fact ids {sorted(unresolved)}"


def _iter_path_references(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if (
                key.endswith("path")
                and isinstance(child, str)
                and child.startswith("tau2/")
            ):
                yield child
            yield from _iter_path_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_path_references(child)


def test_all_schema_paths_and_response_rules_resolve():
    """Every airline_plus schema dependency is present and domain-safe."""
    assert len(SCHEMA_PATHS) == 7
    selected_rule_ids = set()
    for schema_path in SCHEMA_PATHS:
        schema = json.loads(schema_path.read_text())
        assert "source_task_id" not in json.dumps(schema)
        references = list(_iter_path_references(schema))
        assert references, schema_path
        for reference in references:
            assert (REPO_ROOT / "data" / reference).exists(), reference
        context = schema.get("response_phrasing_context")
        if context:
            selected_rule_ids.update(context["selected_rule_ids"])

    rules_path = (
        REPO_ROOT
        / "data"
        / "tau2"
        / "hyper"
        / "response_phrasing"
        / "airline_plus_response_phrasing.yaml"
    )
    rules = yaml.safe_load(rules_path.read_text())["rules"]
    by_id = {rule["id"]: rule for rule in rules}
    assert selected_rule_ids <= by_id.keys()
    for rule in rules:
        assert "airline_plus" in rule["domain_safety"]
    for rule_id in selected_rule_ids:
        assert by_id[rule_id]["domain_safety"]["airline_plus"]["safe"] is True


def test_passenger_cap_is_consistent_between_handbook_and_schemas():
    """The port must not reintroduce the former five-passenger contradiction."""
    handbook = (AIRLINE_PLUS_ROOT.parent / "airline_plus_sop.md").read_text()
    assert "Maximum 4 passengers per reservation." in handbook
    assert "at most 4 passengers" in handbook
    assert "Maximum 5 passengers" not in handbook

    schema_text = "\n".join(path.read_text() for path in SCHEMA_PATHS)
    assert "at most 4 passengers" in schema_text
    assert "at most 5 passengers" not in schema_text


def test_source_policy_controls_are_preserved_without_overbroad_identity_gate():
    """The maintained Airline+ decomposition must not strengthen source policy."""
    handbook = (AIRLINE_PLUS_ROOT.parent / "airline_plus_sop.md").read_text()
    global_rules = json.loads((AIRLINE_PLUS_ROOT / "global_rules.json").read_text())
    identity = json.loads(
        (AIRLINE_PLUS_ROOT / "sections/customer_identity/schema.json").read_text()
    )

    assert "A tool call and a customer-facing response must be separate" in handbook
    assert "not for every interaction or public flight-information lookup" in handbook
    assert "Every interaction begins with identifying the customer" not in handbook
    assert "(local time, EST)" not in handbook
    assert "Seat availability counts refresh nightly" not in handbook

    identity_fact_id = "customer_provided_user_id_required_for_reservation_actions"
    assert identity["domain_hierarchy"]["role"] == "shared_reference"
    assert {fact["id"] for fact in identity["facts"]} == {identity_fact_id}
    assert (
        "booking a flight or modifying or cancelling a reservation"
        in identity["facts"][0]["statement"]
    )
    assert "public flight-information lookup" in identity["facts"][0]["statement"]

    rules_by_id = {rule["id"]: rule for rule in global_rules["rules"]}
    assert "identify_customer_before_access" not in rules_by_id
    assert "customer_id_before_reservation_action" in rules_by_id
    assert "one_tool_call_or_customer_response_at_a_time" in rules_by_id

    requiring_sections = {
        "authorized_scope",
        "booking_flight",
        "modifying_reservation",
        "cancelling_reservation",
        "manage_existing_reservation",
    }
    for section_id in requiring_sections:
        schema = json.loads(
            (AIRLINE_PLUS_ROOT / f"sections/{section_id}/schema.json").read_text()
        )
        requirement = next(
            item
            for item in schema["domain_hierarchy"]["requires"]
            if item["section_id"] == "customer_identity"
        )
        assert requirement["fact_ids"] == [identity_fact_id]
        assert requirement["relationship"] == "shared_reference"

    compensation = json.loads(
        (
            AIRLINE_PLUS_ROOT / "sections/compensation_certificates/schema.json"
        ).read_text()
    )
    assert compensation["domain_hierarchy"]["requires"] == []


def _statement_fields(node, path=""):
    """Yield (json_path, text) for every statement-bearing field in a tree."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("statement", "scope_boundary") and isinstance(value, str):
                yield f"{path}/{key}", value
            yield from _statement_fields(value, f"{path}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _statement_fields(value, f"{path}[{index}]")


def test_fact_statements_are_atemporal():
    """No fact or implication statement may carry an absolute year.

    Artifact authoring metadata (email sent_at headers, slack timestamps,
    copyright footers) is deliberately dated and inherited from canonical;
    the properties that keep those dates harmless are (a) every temporal
    policy rule is relative (24 hours, 12 business days) and (b) no scored
    statement anchors to a calendar year. This pins (b).
    """
    year_token = re.compile(r"\b(19|20)\d{2}\b")
    offenders = []
    statement_sources = list(SCHEMA_PATHS) + sorted(
        (AIRLINE_PLUS_ROOT / "sections").glob("**/eval_manifest.json")
    )
    for source in statement_sources:
        tree = json.loads(source.read_text())
        for json_path, text in _statement_fields(tree):
            if year_token.search(text):
                offenders.append(
                    f"{source.relative_to(AIRLINE_PLUS_ROOT)}:{json_path}: {text[:80]}"
                )
    assert offenders == []


def test_handbook_front_matter_sim_time_matches_domain_policy():
    """The handbook front matter is the only developer-visible sim-time carrier.

    The inner replay swaps the environment policy for the developer's
    reconstruction wholesale, so the built agent's "now" for the 24-hour
    rules comes from what the developer reads here. It must never drift
    from the domain policy's declared current time.
    """
    front_matter = (
        AIRLINE_PLUS_ROOT / "sections" / "uploaded_handbook_front_matter.md"
    ).read_text()
    policy = (
        REPO_ROOT / "data" / "tau2" / "domains" / "airline_plus" / "policy.md"
    ).read_text()

    policy_time = re.search(
        r"The current time is (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} EST)", policy
    )
    front_matter_time = re.search(
        r"\*\*Current System Time:\*\* (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} EST)",
        front_matter,
    )
    assert policy_time is not None
    assert front_matter_time is not None
    assert front_matter_time.group(1) == policy_time.group(1)
