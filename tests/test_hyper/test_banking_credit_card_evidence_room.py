"""Regression coverage for the banking card-servicing evidence room."""

from __future__ import annotations

import json
from collections import Counter

from tau2.hyper.sandbox.kit import _copy_sop_variant_materials
from tau2.hyper.task_loader import load_hyper_tau_task
from tau2.hyper.transformations import (
    compile_variant_transformations,
    get_transformation,
    resolve_section_transformations,
)
from tau2.hyper.transformations.sop_variants import assemble_sop_variant
from tau2.utils.utils import DATA_DIR

SECTION = (
    DATA_DIR / "tau2/hyper/sops/banking_knowledge/sections/"
    "credit_card_closure_retention_downgrade_payoff"
)
ROOM = SECTION / "evidence_room_001"
VARIANT_PATH = (
    "tau2/hyper/sops/banking_knowledge/variants/core_evidence_bundle_001.json"
)
VARIANT = DATA_DIR / VARIANT_PATH
PHRASING_RULES_PATH = "tau2/hyper/response_phrasing/banking_response_phrasing.yaml"
# The only release task that composes response phrasing on top of the core
# evidence bundle; its siblings run the same bundle and eval set unphrased.
TASK_ID = (
    "039_banking_knowledge_construction_client_api_deposit_services"
    "_response_phrasing_performance_medium"
)
UNPHRASED_SIBLING_TASK_IDS = [
    "038_banking_knowledge_construction_client_api_deposit_services"
    "_seeded_performance_medium",
    "040_banking_knowledge_construction_client_api_deposit_services_performance_hard",
]


def test_core_evidence_bundle_task_composes_response_phrasing() -> None:
    task = load_hyper_tau_task(TASK_ID)

    assert task.source_domain == "banking_knowledge"
    assert task.sop_variant_manifest_path == VARIANT_PATH
    assert task.response_phrasing_rules_path == PHRASING_RULES_PATH

    phrasing, distribution = task.composition_pipeline
    assert phrasing["stage"] == "response_phrasing"
    assert len(phrasing["selected_rule_ids"]) == 12
    assert distribution["stage"] == "information_distribution"
    assert distribution["variant_manifest_path"] == VARIANT_PATH

    # Phrasing composes on top of the bundle without touching it: the
    # unphrased siblings carry the identical distribution stage and eval set.
    for sibling_id in UNPHRASED_SIBLING_TASK_IDS:
        sibling = load_hyper_tau_task(sibling_id)
        assert sibling.composition_pipeline == [distribution], sibling_id
        assert sibling.response_phrasing_rules_path is None, sibling_id
        assert sibling.test_task_ids == task.test_task_ids, sibling_id


def test_card_servicing_evidence_room_validates_every_representation() -> None:
    schema = json.loads((SECTION / "schema.json").read_text())
    specs = [
        spec
        for spec in resolve_section_transformations(schema)
        if str(spec.get("id", "")).startswith("banking_card_servicing_")
    ]
    assert len(specs) == 8
    for spec in specs:
        transformation = get_transformation(spec["representation"])
        artifacts = transformation.discover_artifacts(
            schema, SECTION / "schema.json", spec
        )
        assert transformation.validate(schema, artifacts) == []


def test_card_servicing_bundle_has_exact_single_fact_ownership() -> None:
    schema = json.loads((SECTION / "schema.json").read_text())
    expected = {str(fact["id"]) for fact in schema["facts"]}
    pack = json.loads((ROOM / "transformation_pack.json").read_text())
    bundle = next(
        bundle
        for bundle in pack["transformation_bundles"]
        if bundle["id"] == "banking_card_servicing_evidence_room"
    )
    authoritative = [
        fact_id
        for member in bundle["members"]
        for fact_id in member["authoritative_fact_ids"]
    ]
    assert set(authoritative) == expected
    assert all(count == 1 for count in Counter(authoritative).values())
    assert len(authoritative) == 145


def test_card_servicing_variant_compiles_without_fallback_or_duplication() -> None:
    manifest = json.loads(VARIANT.read_text())
    compilation = compile_variant_transformations(manifest)
    assert compilation.errors == []
    assert compilation.uncovered_facts == []
    assert compilation.multiply_represented_facts == []
    target = [
        fact
        for fact in compilation.facts
        if fact.section_id == "credit_card_closure_retention_downgrade_payoff"
    ]
    assert len(target) == 145
    assert all(len(fact.representations) == 1 for fact in target)


def test_card_servicing_bundle_stub_is_appended_for_composed_journey() -> None:
    assembled = assemble_sop_variant(VARIANT)
    heading = (
        "## Credit-card closure, retention, downgrade, payoff, and "
        "statement-credit handling"
    )
    assert assembled.count(heading) == 1
    assert "Working evidence for this journey" in assembled


def test_card_servicing_neutralized_kit_contains_only_delivered_artifacts(
    tmp_path,
) -> None:
    manifest = {
        "id": "card_servicing_materialization_test",
        "domain": "banking_knowledge",
        "section_source_schemas": {
            "credit_card_closure_retention_downgrade_payoff": (
                "tau2/hyper/sops/banking_knowledge/sections/"
                "credit_card_closure_retention_downgrade_payoff/schema.json"
            )
        },
        "section_bundles": {
            "credit_card_closure_retention_downgrade_payoff": (
                "banking_card_servicing_evidence_room"
            )
        },
        "uncovered_fact_policy": "error",
        "information_distribution": {"representation": "website_screenshot"},
    }
    out_dir = tmp_path / "kit"
    created = _copy_sop_variant_materials(manifest, out_dir)
    assert created == [out_dir / "uploaded_materials"]
    delivered = sorted((out_dir / "uploaded_materials").iterdir())
    assert len(delivered) == 51
    assert all("manifest" not in path.name for path in delivered)
    assert all("F0" not in path.name for path in delivered)
    assert {path.suffix for path in delivered} == {
        ".eml",
        ".json",
        ".md",
        ".mp4",
        ".png",
        ".vtt",
    }
