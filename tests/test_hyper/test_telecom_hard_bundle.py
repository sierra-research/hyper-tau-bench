"""Contract tests for the telecom hard evidence bundle.

The hard bundle is the strictly additive sibling of the telecom core
evidence bundle (docs/telecom-hard-bundle-plan.md): identical 155-fact
authority partition, identical response-phrasing pack, identical
114-scenario evaluation split, with the evidence surface deepened by
per-fact arcs and intra-artifact complexity. Every core telecom artifact
stays byte-identical; hard packs reference the frozen core read-only and
add hard-owned artifacts under hard_bundle_001/.
"""

from __future__ import annotations

import json
import re
from collections import Counter

from tau2.hyper.sandbox.kit import _copy_sop_variant_materials
from tau2.hyper.task_loader import load_hyper_tau_task
from tau2.hyper.transformations import compile_variant_transformations
from tau2.hyper.transformations.sop_variants import load_sop_variant_manifest
from tau2.utils.utils import DATA_DIR

TELECOM_ROOT = DATA_DIR / "tau2/hyper/sops/telecom"
HARD_ROOT = TELECOM_ROOT / "hard_bundle_001"
HARD_MANIFEST_PATH = (
    "tau2/hyper/sops/telecom/variants/core_evidence_bundle_hard_001.json"
)
BASELINE_MANIFEST_PATH = (
    "tau2/hyper/sops/telecom/variants/core_evidence_bundle_001.json"
)
# The release corpus pairs the hard evidence surface (015) with the core
# bundle it must not change (013); both run the same all-defects client API
# deployment at the same performance tier, so the only declared difference is
# the evidence surface.
HARD_TASK_ID = (
    "015_telecom_construction_core_evidence_hard_all_defects_performance_medium"
)
BASELINE_TASK_ID = (
    "013_telecom_construction_core_evidence_seeded_all_defects_performance_medium"
)

SECTION_IDS = [
    "customer_identity",
    "service_foundations",
    "resume_suspended_line",
    "refuel_data",
    "change_plan",
    "restore_data_abroad",
    "restore_service",
    "restore_mobile_data",
    "restore_mms",
]

# Phase-1 pin: the hard packs reference exactly the core artifact set. Waves
# grow these counts; every wave updates this table in the same commit.
EXPECTED_HARD_TRANSFORMATION_ARTIFACT_COUNTS = {
    "telecom_customer_identity_care_console_recording_hard_001": 1,
    "telecom_customer_identity_email_archive_hard_001": 6,
    "telecom_customer_identity_support_transcripts_hard_001": 9,
    "telecom_customer_identity_helpdesk_export_hard_001": 1,
    "telecom_service_foundations_email_archive_hard_001": 40,
    "telecom_service_foundations_slack_archive_hard_001": 8,
    "telecom_service_foundations_meeting_series_hard_001": 15,
    "telecom_service_foundations_reference_documents_hard_001": 31,
    "telecom_resume_suspended_line_html_knowledge_archive_hard_001": 1,
    "telecom_resume_suspended_line_launch_scope_review_hard_001": 3,
    "telecom_resume_suspended_line_support_transcripts_hard_001": 6,
    "telecom_refuel_data_care_console_recording_hard_001": 1,
    "telecom_refuel_data_email_archive_hard_001": 6,
    "telecom_refuel_data_support_transcripts_hard_001": 10,
    "telecom_refuel_data_helpdesk_export_hard_001": 1,
    "telecom_change_plan_care_console_recording_hard_001": 1,
    "telecom_change_plan_email_archive_hard_001": 6,
    "telecom_change_plan_support_transcripts_hard_001": 9,
    "telecom_change_plan_helpdesk_export_hard_001": 1,
    "telecom_restore_data_abroad_roaming_recovery_maps_hard_001": 2,
    "telecom_restore_data_abroad_jira_decision_export_hard_001": 1,
    "telecom_restore_data_abroad_support_transcripts_hard_001": 6,
    "telecom_restore_service_full_journey_flowchart_hard_001": 3,
    "telecom_restore_service_apn_recording_controlled_distractors_hard_001": 1,
    "telecom_restore_service_support_transcripts_hard_001": 7,
    "telecom_restore_mobile_data_web_surfaces_hard_001": 37,
    "telecom_restore_mobile_data_device_capture_selection_hard_001": 27,
    "telecom_restore_mobile_data_email_archive_hard_001": 36,
    "telecom_restore_mobile_data_scoped_routing_chart_hard_001": 2,
    "telecom_restore_mobile_data_support_transcripts_hard_001": 8,
    "telecom_restore_mms_help_center_full_site_hard_001": 22,
    "telecom_restore_mms_device_capture_selection_hard_001": 27,
    "telecom_restore_mms_dense_slack_mcp_dump_hard_001": 1,
    "telecom_restore_mms_support_transcripts_hard_001": 6,
}

# Kit census (342 pack references, 338 unique files: the two device-capture
# selections share core archive screens, deduplicating four).
EXPECTED_KIT_FILE_COUNT = 338
EXPECTED_KIT_SUFFIXES = {
    ".md": 66,
    ".png": 116,
    ".eml": 94,
    ".html": 8,
    ".vtt": 18,
    ".docx": 2,
    ".txt": 9,
    ".xlsx": 2,
    ".pptx": 1,
    ".csv": 5,
    ".mp4": 4,
    ".zip": 3,
    ".json": 10,
}
# Substring fragments would false-positive on legitimate names ("archive"
# contains "arc"), so filenames are split into tokens on [_-.] first.
FORBIDDEN_KIT_NAME_TOKENS = (
    "hard",
    "fact",
    "facts",
    "metrics",
    "arc",
    "arcs",
    "ledger",
    "rendition",
    "renditions",
    "transformation",
    "pack",
)


def _authoritative_fact_ids(compilation) -> set[str]:
    return {
        f"{activation.section_id}.{fact_id}"
        for activation in compilation.activations
        for fact_id in (
            activation.authoritative_fact_ids or activation.covered_fact_ids
        )
    }


def _compile(manifest_path: str):
    return compile_variant_transformations(load_sop_variant_manifest(manifest_path))


def test_hard_task_preserves_baseline_evaluation_contract():
    baseline = load_hyper_tau_task(BASELINE_TASK_ID)
    hard = load_hyper_tau_task(HARD_TASK_ID)

    assert hard.source_domain == baseline.source_domain == "telecom"
    assert hard.sop_variant_manifest_path == HARD_MANIFEST_PATH
    assert baseline.sop_variant_manifest_path == BASELINE_MANIFEST_PATH
    assert hard.test_task_ids == baseline.test_task_ids
    assert len(hard.test_task_ids) == 119

    (hard_stage,) = hard.composition_pipeline
    (baseline_stage,) = baseline.composition_pipeline
    assert hard_stage == {
        **baseline_stage,
        "variant_manifest_path": HARD_MANIFEST_PATH,
    }

    assert (
        hard.client_api_deployment_manifest
        == baseline.client_api_deployment_manifest
        == "telecom/all_defects_v1"
    )
    assert hard.performance_profile == baseline.performance_profile
    assert hard.sandbox_config == baseline.sandbox_config
    assert hard.user_llm == baseline.user_llm
    assert hard.user_reasoning_effort == baseline.user_reasoning_effort


def test_hard_bundle_compiles_with_the_same_complete_authority_partition():
    baseline = _compile(BASELINE_MANIFEST_PATH)
    hard = _compile(HARD_MANIFEST_PATH)

    for compilation in (baseline, hard):
        assert compilation.errors == []
        assert compilation.warnings == []
        assert compilation.report()["totals"] == {
            "facts": 155,
            "covered": 155,
            "uncovered": 0,
            "multiply_represented": 0,
        }
        assert compilation.fallback_applies is False

    assert _authoritative_fact_ids(hard) == _authoritative_fact_ids(baseline)

    hard_counts = {
        entry["transformation_id"]: entry["artifact_count"]
        for entry in hard.report()["transformations"]
    }
    assert hard_counts == EXPECTED_HARD_TRANSFORMATION_ARTIFACT_COUNTS
    assert sum(hard_counts.values()) == 342


def test_imported_hard_pack_does_not_change_core_bundle():
    baseline = _compile(BASELINE_MANIFEST_PATH)
    baseline_ids = {
        entry["transformation_id"] for entry in baseline.report()["transformations"]
    }
    assert not any("_hard_" in transformation_id for transformation_id in baseline_ids)
    assert (
        sum(entry["artifact_count"] for entry in baseline.report()["transformations"])
        == 244
    )


def test_hard_packs_reference_only_frozen_core_or_hard_owned_paths():
    for section_id in SECTION_IDS:
        pack = json.loads(
            (HARD_ROOT / f"{section_id}_transformation_pack.json").read_text()
        )
        assert pack["section_id"] == section_id
        for transformation in pack["transformations"]:
            assert transformation["id"].endswith("_hard_001")
            for artifact in transformation.get("artifacts") or []:
                rel = artifact.get("path")
                if rel is None:
                    continue
                assert (DATA_DIR / rel).exists(), f"missing artifact: {rel}"
                inside_hard = rel.startswith("tau2/hyper/sops/telecom/hard_bundle_001/")
                inside_core = rel.startswith(
                    (
                        "tau2/hyper/sops/telecom/sections/",
                        "tau2/hyper/sops/telecom/shared/",
                    )
                )
                assert inside_hard or inside_core, (
                    f"{section_id}: artifact escapes the telecom tree: {rel}"
                )
        for bundle in pack["transformation_bundles"]:
            assert bundle["id"].endswith("_hard_001")
            member_ids = {member["transformation_id"] for member in bundle["members"]}
            declared = {t["id"] for t in pack["transformations"]}
            assert member_ids <= declared
            for route in bundle.get("evidence_routes") or []:
                for hop in route.get("hops", []):
                    assert hop["transformation_id"] in declared


def test_hard_bundle_materializes_neutralized_uploaded_materials(tmp_path):
    manifest = load_sop_variant_manifest(HARD_MANIFEST_PATH)
    kit_dir = tmp_path / "kit"
    _copy_sop_variant_materials(manifest, kit_dir)

    materials = sorted((kit_dir / "uploaded_materials").iterdir())
    assert len(materials) == EXPECTED_KIT_FILE_COUNT
    assert Counter(path.suffix for path in materials) == EXPECTED_KIT_SUFFIXES
    for path in materials:
        tokens = set(re.split(r"[_\-.]+", path.name.lower()))
        leaked = tokens.intersection(FORBIDDEN_KIT_NAME_TOKENS)
        assert not leaked, f"kit filename leaks {sorted(leaked)}: {path.name}"
