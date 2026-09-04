"""Regression tests for the enlarged Retail+ hard evidence bundle."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from tau2.hyper.sandbox.kit import _copy_sop_variant_materials
from tau2.hyper.task_loader import load_hyper_tau_task
from tau2.hyper.transformations import compile_variant_transformations
from tau2.hyper.transformations.sop_variants import load_sop_variant_manifest
from tau2.utils.utils import DATA_DIR

HARD_ROOT = DATA_DIR / "tau2/hyper/sops/retail_plus/hard_bundle_001"
HARD_MANIFEST_PATH = (
    "tau2/hyper/sops/retail_plus/variants/core_evidence_bundle_hard_001.json"
)
HARD_CLIENT_MANIFEST_PATH = (
    "tau2/hyper/sops/retail_plus/variants/core_evidence_bundle_hard_client_001.json"
)
BASELINE_MANIFEST_PATH = (
    "tau2/hyper/sops/retail_plus/variants/core_evidence_bundle_001.json"
)
# The release corpus pairs the hard evidence surface (009) with the core
# bundle it must not change (008); neither carries client API defects, so the
# only declared difference is the evidence surface.
HARD_TASK_ID = (
    "009_retail_plus_construction_core_evidence_hard_seeded"
    "_live_experiment_performance_medium"
)
BASELINE_TASK_ID = "008_retail_plus_construction_core_evidence_performance_hard"

EXPECTED_SCALE_TARGETS = {
    "customer_kickoff_documents": 4,
    "website_screenshots": 120,
    "slack_tool_calls": 131,
    "slack_message_occurrences": 915,
    "profile_support_records": 24,
    "delivered_support_records": 100,
    "email_threads": 38,
    "process_flowchart_frames": 11,
    "qa_deck_pages": 25,
    "recorded_sessions": 8,
    "recorded_session_minutes": 420,
    "helpdesk_objects": 355,
    "api_pack_files": 15,
}

EXPECTED_TRANSFORMATION_ARTIFACT_COUNTS = {
    "retail_customer_identity_discovery_intake_hard_001": 4,
    "manage_customer_profile_hard_screenshots_001": 16,
    "manage_customer_profile_hard_records_001": 24,
    "manage_delivered_order_hard_screenshots_001": 17,
    "manage_delivered_order_hard_slack_001": 1,
    "manage_delivered_order_hard_records_001": 100,
    "manage_pending_order_hard_screenshots_001": 17,
    "manage_pending_order_hard_slack_001": 1,
    "manage_pending_order_hard_email_archive_001": 38,
    "manage_pending_order_hard_flowchart_001": 11,
    "manage_pending_order_hard_qa_deck_001": 1,
    "service_foundations_hard_screenshots_001": 70,
    "service_foundations_hard_slack_001": 1,
    "service_foundations_hard_recordings_001": 8,
    "service_foundations_hard_helpdesk_export_001": 1,
    "service_foundations_hard_api_contracts_001": 3,
}


# The client overlay substitutes twelve members without adding or removing
# artifacts: every substituted member keeps its base artifact count, and the
# three client_knowledge members materialize nothing.
EXPECTED_CLIENT_TRANSFORMATION_ARTIFACT_COUNTS = {
    **EXPECTED_TRANSFORMATION_ARTIFACT_COUNTS,
    **{
        base_id.replace("_hard_", "_hard_client_"): count
        for base_id, count in EXPECTED_TRANSFORMATION_ARTIFACT_COUNTS.items()
        if base_id
        in {
            "manage_pending_order_hard_slack_001",
            "manage_pending_order_hard_email_archive_001",
            "manage_pending_order_hard_flowchart_001",
            "manage_pending_order_hard_qa_deck_001",
            "manage_delivered_order_hard_screenshots_001",
            "manage_delivered_order_hard_slack_001",
            "manage_delivered_order_hard_records_001",
            "service_foundations_hard_screenshots_001",
            "service_foundations_hard_slack_001",
            "service_foundations_hard_recordings_001",
            "service_foundations_hard_helpdesk_export_001",
        }
    },
    # The compile report counts each client_knowledge stub as one artifact;
    # nothing is materialized into the kit (the 311-file kit census in
    # test_client_sim proves it).
    "manage_pending_order_hard_client_knowledge_001": 1,
    "manage_delivered_order_hard_client_knowledge_001": 1,
    "service_foundations_hard_client_knowledge_001": 1,
}
for _base_id in (
    "manage_pending_order_hard_slack_001",
    "manage_pending_order_hard_email_archive_001",
    "manage_pending_order_hard_flowchart_001",
    "manage_pending_order_hard_qa_deck_001",
    "manage_delivered_order_hard_screenshots_001",
    "manage_delivered_order_hard_slack_001",
    "manage_delivered_order_hard_records_001",
    "service_foundations_hard_screenshots_001",
    "service_foundations_hard_slack_001",
    "service_foundations_hard_recordings_001",
    "service_foundations_hard_helpdesk_export_001",
):
    del EXPECTED_CLIENT_TRANSFORMATION_ARTIFACT_COUNTS[_base_id]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _vtt_duration_milliseconds(path: Path) -> int:
    cue_ends = re.findall(r"-->\s*(\d+):(\d{2}):(\d{2})\.(\d{3})", path.read_text())
    return max(
        ((int(hours) * 60 + int(minutes)) * 60 + int(seconds)) * 1_000
        + int(milliseconds)
        for hours, minutes, seconds, milliseconds in cue_ends
    )


def _authoritative_fact_ids(compilation) -> set[str]:
    return {
        f"{activation.section_id}.{fact_id}"
        for activation in compilation.activations
        for fact_id in (
            activation.authoritative_fact_ids or activation.covered_fact_ids
        )
    }


def _model_pool(task) -> list[dict]:
    # Each entry carries the performance tier that resolved it; the pool
    # itself (model, constraints, credit rates) is tier-independent.
    return [
        {key: value for key, value in config.items() if key != "tier"}
        for config in task.allowed_agent_models
    ]


def test_hard_task_preserves_baseline_evaluation_contract():
    baseline = load_hyper_tau_task(BASELINE_TASK_ID)
    hard = load_hyper_tau_task(HARD_TASK_ID)

    assert hard.source_domain == baseline.source_domain == "retail_plus"
    assert hard.sop_variant_manifest_path == HARD_MANIFEST_PATH
    assert baseline.sop_variant_manifest_path == BASELINE_MANIFEST_PATH
    assert (
        hard.test_task_ids
        == baseline.test_task_ids
        == [str(index) for index in range(134)]
    )

    (hard_stage,) = hard.composition_pipeline
    (baseline_stage,) = baseline.composition_pipeline
    assert hard_stage == {
        **baseline_stage,
        "variant_manifest_path": HARD_MANIFEST_PATH,
    }

    assert hard.client_api_deployment_manifest is None
    assert baseline.client_api_deployment_manifest is None
    assert _model_pool(hard) == _model_pool(baseline)
    assert hard.user_llm == baseline.user_llm
    assert hard.user_reasoning_effort == baseline.user_reasoning_effort
    assert hard.sandbox_config == baseline.sandbox_config


def test_hard_bundle_compiles_with_the_same_complete_authority_partition():
    baseline = compile_variant_transformations(
        load_sop_variant_manifest(BASELINE_MANIFEST_PATH)
    )
    hard = compile_variant_transformations(
        load_sop_variant_manifest(HARD_MANIFEST_PATH)
    )

    for compilation in (baseline, hard):
        assert compilation.errors == []
        assert compilation.warnings == []
        assert compilation.report()["totals"] == {
            "facts": 119,
            "covered": 119,
            "uncovered": 0,
            "multiply_represented": 0,
        }
    assert _authoritative_fact_ids(hard) == _authoritative_fact_ids(baseline)

    baseline_artifact_count = sum(
        entry["artifact_count"] for entry in baseline.report()["transformations"]
    )
    hard_counts = {
        entry["transformation_id"]: entry["artifact_count"]
        for entry in hard.report()["transformations"]
    }
    # 139 = the audited 138 plus the 2026-05-28 servicing-sync session that
    # settles failed_verification_handling in the core series.
    assert baseline_artifact_count == 139
    assert hard_counts == EXPECTED_TRANSFORMATION_ARTIFACT_COUNTS
    assert sum(hard_counts.values()) == 313


def test_hard_client_overlay_preserves_partition_and_artifact_census():
    """The client overlay moves ownership of the 19 held facts to the three
    client_knowledge members without changing the fact partition or the
    delivered artifact census: substitution, never addition."""
    hard = compile_variant_transformations(
        load_sop_variant_manifest(HARD_MANIFEST_PATH)
    )
    client = compile_variant_transformations(
        load_sop_variant_manifest(HARD_CLIENT_MANIFEST_PATH)
    )

    assert client.errors == []
    assert client.warnings == []
    assert client.report()["totals"] == {
        "facts": 119,
        "covered": 119,
        "uncovered": 0,
        "multiply_represented": 0,
    }
    assert _authoritative_fact_ids(client) == _authoritative_fact_ids(hard)

    client_counts = {
        entry["transformation_id"]: entry["artifact_count"]
        for entry in client.report()["transformations"]
    }
    assert client_counts == EXPECTED_CLIENT_TRANSFORMATION_ARTIFACT_COUNTS
    assert sum(client_counts.values()) == 316

    # The client deck reuses the reviewed 25-page shape and drops only the
    # held page-5 pin; the other three page pins survive verbatim.
    client_pack = _load_json(
        HARD_ROOT
        / "client_overlay"
        / "manage_pending_order_client_transformation_pack.json"
    )
    deck = next(
        transformation
        for transformation in client_pack["transformations"]
        if transformation["id"] == "manage_pending_order_hard_client_qa_deck_001"
    )
    artifact = deck["artifacts"][0]
    assert artifact["path"].endswith(
        "client_overlay/qa_deck/pending_order_qa_calibration_deck.pdf"
    )
    assert [entry["page"] for entry in artifact["page_fact_ids"]] == [8, 10, 13]


def test_hard_bundle_hits_every_enlarged_scale_target():
    slack = _load_json(HARD_ROOT / "slack/beacon_workspace_capture_hard.json")
    assert len(slack["tool_calls"]) == 131
    assert (
        sum(
            len(call["response"]["structured_content"].get("messages") or [])
            for call in slack["tool_calls"]
        )
        == 915
    )

    helpdesk = _load_json(HARD_ROOT / "helpdesk/authored_export_hard.json")
    assert (
        sum(
            len(helpdesk[key])
            for key in (
                "macros",
                "triggers",
                "policy_contracts",
                "fields",
                "sla_policies",
                "views",
            )
        )
        == 355
    )


def test_recorded_session_minutes_are_measured_from_vtt_timestamps():
    service_pack = _load_json(
        HARD_ROOT / "service_foundations_transformation_pack.json"
    )
    recordings = next(
        transformation["artifacts"]
        for transformation in service_pack["transformations"]
        if transformation["id"] == "service_foundations_hard_recordings_001"
    )

    assert len(recordings) == EXPECTED_SCALE_TARGETS["recorded_sessions"]
    assert (
        sum(
            _vtt_duration_milliseconds(DATA_DIR / artifact["path"])
            for artifact in recordings
        )
        == EXPECTED_SCALE_TARGETS["recorded_session_minutes"] * 60_000
    )


def test_adjacent_api_packs_pool_with_the_record_contract():
    # The adjacent packs are filler beside the care record contract; a
    # reader must not be able to separate them by structural census
    # (route/schema/error-row/saved-example counts) or by lifecycle mix.
    carrier = _load_json(
        DATA_DIR
        / "tau2/hyper/sops/retail_plus/sections/service_foundations"
        / "api_contract_pack_001/authored_contract.json"
    )
    packs = [
        _load_json(HARD_ROOT / f"api_contracts/adjacent_contract_{index:02d}.json")
        for index in (1, 2)
    ]
    carrier_routes = len(carrier["openapi"]["paths"])
    carrier_rows = len(carrier["error_behavior"])
    for pack in packs:
        assert list(pack) == list(carrier)
        assert len(pack["openapi"]["paths"]) >= carrier_routes
        assert len(pack["error_behavior"]) >= carrier_rows - 2
        assert {row["status"] for row in pack["error_behavior"]} >= {
            "published",
            "retired",
            "draft",
        }
        assert len(pack["postman_collection"]["item"]) >= 7
        for entry in pack["error_behavior"]:
            assert list(entry) == carrier["error_behavior_columns"]


def test_artifact_lengths_pool_carriers_with_filler():
    """Carriers must be unfindable by length in every pooled family: medians
    pooled with filler, no carrier in the top length band, and the longest
    artifact always filler. The delivered pool additionally keeps the core
    archive's heavy tail on the filler side. The client-overlay pools run
    the same gates: the client copies join their families as ex-carriers
    (their held pins dropped), so they must stay length-anonymous among the
    filler they now pool with."""
    pools = {
        "manage_customer_profile_hard_records_001": (
            "manage_customer_profile_transformation_pack.json",
            False,
        ),
        "manage_delivered_order_hard_records_001": (
            "manage_delivered_order_transformation_pack.json",
            True,
        ),
        "manage_pending_order_hard_email_archive_001": (
            "manage_pending_order_transformation_pack.json",
            False,
        ),
        "manage_delivered_order_hard_client_records_001": (
            "client_overlay/manage_delivered_order_client_transformation_pack.json",
            True,
        ),
        "manage_pending_order_hard_client_email_archive_001": (
            "client_overlay/manage_pending_order_client_transformation_pack.json",
            False,
        ),
    }

    def median(values: list[int]) -> float:
        mid = len(values) // 2
        if len(values) % 2:
            return float(values[mid])
        return (values[mid - 1] + values[mid]) / 2

    for transformation_id, (pack_name, heavy_tail) in pools.items():
        pack = _load_json(HARD_ROOT / pack_name)
        (transformation,) = [
            entry
            for entry in pack["transformations"]
            if entry["id"] == transformation_id
        ]
        lengths = {}
        carriers = set()
        for artifact in transformation["artifacts"]:
            path = DATA_DIR / artifact["path"]
            lengths[artifact["path"]] = len(path.read_text().split())
            if artifact["included_fact_ids"]:
                carriers.add(artifact["path"])
        filler_lengths = sorted(
            words for name, words in lengths.items() if name not in carriers
        )
        carrier_lengths = sorted(lengths[name] for name in carriers)
        assert carriers and filler_lengths

        ratio = median(carrier_lengths) / median(filler_lengths)
        assert 0.7 <= ratio <= 1.4, (transformation_id, ratio)
        top_band = max(2, len(lengths) // 10)
        longest = sorted(lengths, key=lengths.get, reverse=True)[:top_band]
        assert not carriers.intersection(longest), (transformation_id, longest)
        if heavy_tail:
            assert max(filler_lengths) >= 2 * median(filler_lengths), transformation_id


def test_hard_qa_deck_reuses_reviewed_source_without_padding():
    pending_pack = _load_json(
        HARD_ROOT / "manage_pending_order_transformation_pack.json"
    )
    deck = next(
        transformation
        for transformation in pending_pack["transformations"]
        if transformation["id"] == "manage_pending_order_hard_qa_deck_001"
    )
    artifact = deck["artifacts"][0]
    assert artifact["path"].endswith("pending_order_qa_calibration_deck.pdf")
    assert artifact["path"].split("/")[-2] != "qa_deck"
    assert [entry["page"] for entry in artifact["page_fact_ids"]] == [5, 8, 10, 13]


def test_hard_bundle_materializes_311_neutralized_uploaded_materials(tmp_path):
    manifest = load_sop_variant_manifest(HARD_MANIFEST_PATH)
    kit_dir = tmp_path / "kit"
    _copy_sop_variant_materials(manifest, kit_dir)

    materials = sorted((kit_dir / "uploaded_materials").iterdir())
    assert len(materials) == 311
    assert Counter(path.suffix for path in materials) == {
        ".eml": 38,
        ".json": 1,
        ".md": 128,
        ".pdf": 1,
        ".png": 131,
        ".vtt": 8,
        ".zip": 4,
    }
    assert not any("hard" in path.name for path in materials)
    assert not any("fact" in path.name for path in materials)
    assert not any("metrics" in path.name for path in materials)
    assert not any("transformation_pack" in path.name for path in materials)
