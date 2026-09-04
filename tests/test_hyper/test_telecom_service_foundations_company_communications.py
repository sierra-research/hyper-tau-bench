"""Coverage tests for the telecom Service Foundations communications bundle."""

from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime
from difflib import SequenceMatcher
from email import policy
from email.parser import BytesParser
from pathlib import Path

from tau2.hyper.sandbox.kit import build_construction_kit
from tau2.hyper.task_loader import load_hyper_tau_task
from tau2.hyper.transformations import (
    compile_variant_transformations,
    get_transformation,
)
from tau2.hyper.transformations.sop_variants import assemble_sop_variant
from tau2.utils.utils import DATA_DIR

SECTION_ROOT = DATA_DIR / "tau2/hyper/sops/telecom/sections/service_foundations"
ARCHIVE = SECTION_ROOT / "company_communications_001"
SCHEMA_PATH = SECTION_ROOT / "schema.json"
VARIANT_PATH = (
    DATA_DIR / "tau2/hyper/sops/telecom/variants/core_evidence_bundle_001.json"
)
VARIANT_RELATIVE_PATH = "tau2/hyper/sops/telecom/variants/core_evidence_bundle_001.json"
TASK_ID = "013_telecom_construction_core_evidence_seeded_all_defects_performance_medium"
SNAPSHOT = datetime.fromisoformat("2025-02-25T12:08:00-05:00")


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def test_workbooks_define_compact_print_layouts():
    expected_sheets = {
        "billing_data_control_v5_2025-02-21.xlsx": 4,
        "service_foundations_rollout_ledger_v7_2025-02-25.xlsx": 3,
    }
    for filename, sheet_count in expected_sheets.items():
        with zipfile.ZipFile(ARCHIVE / "attachments" / filename) as workbook:
            workbook_xml = workbook.read("xl/workbook.xml").decode()
            assert workbook_xml.count('name="_xlnm.Print_Area"') == sheet_count
            for relationships_path in (
                "_rels/.rels",
                "xl/_rels/workbook.xml.rels",
            ):
                relationships_xml = workbook.read(relationships_path).decode()
                relationship_ids = re.findall(
                    r'<Relationship\b[^>]*\bId="([^"]+)"', relationships_xml
                )
                assert relationship_ids
                assert len(relationship_ids) == len(set(relationship_ids))
            for index in range(1, sheet_count + 1):
                sheet_xml = workbook.read(f"xl/worksheets/sheet{index}.xml").decode()
                assert 'fitToPage="1"' in sheet_xml
                assert 'fitToWidth="1"' in sheet_xml
                assert 'fitToHeight="0"' in sheet_xml


def test_all_communications_predate_the_snapshot_and_use_est():
    email = load(ARCHIVE / "email_manifest.json")
    for thread in email["threads"]:
        message = BytesParser(policy=policy.default).parsebytes(
            (ARCHIVE / "emails" / thread["filename"]).read_bytes()
        )
        sent = message["Date"].datetime
        assert sent.utcoffset() == SNAPSHOT.utcoffset()
        assert sent <= SNAPSHOT

    slack = load(ARCHIVE / "slack_manifest.json")
    thread_lengths = []
    for artifact in slack["artifacts"]:
        payload = load(ARCHIVE / "slack" / artifact["filename"])
        for call in payload["tool_calls"]:
            messages = call["response"]["structured_content"]["messages"]
            if call["request"]["params"]["name"] == "slack_get_thread_replies":
                thread_lengths.append(len(messages))
            assert all(
                datetime.fromtimestamp(float(message["ts"]), SNAPSHOT.tzinfo)
                <= SNAPSHOT
                for message in messages
            )
    assert len(thread_lengths) == 60
    assert min(thread_lengths) == 2
    assert max(thread_lengths) >= 18
    assert len(set(thread_lengths)) >= 12

    unique_messages = {
        str(message["text"])
        for artifact in slack["artifacts"]
        for call in load(ARCHIVE / "slack" / artifact["filename"])["tool_calls"]
        for message in call["response"]["structured_content"]["messages"]
    }
    long_messages = [
        re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", text.lower()))
        for text in unique_messages
        if len(re.findall(r"\b[\w’'-]+\b", text)) >= 40
    ]
    assert (
        max(
            SequenceMatcher(None, first, second).ratio()
            for index, first in enumerate(long_messages)
            for second in long_messages[index + 1 :]
        )
        < 0.84
    )

    meetings = load(ARCHIVE / "meeting_manifest.json")
    assert all(
        datetime.fromisoformat(meeting["date"]).replace(tzinfo=SNAPSHOT.tzinfo)
        <= SNAPSHOT
        for meeting in meetings["meetings"]
    )
    recurring = [
        meeting
        for meeting in meetings["meetings"]
        if meeting["meeting_type"] in {"recurring_team_sync", "calibration"}
    ]
    assert len(recurring) >= 7
    assert all(all(meeting["workflow_markers"].values()) for meeting in recurring)
    assert len({meeting["cue_count"] for meeting in meetings["meetings"]}) >= 10


def test_bundle_partitions_all_51_facts_and_production_validators_pass():
    schema = load(SCHEMA_PATH)
    bundle = next(
        item
        for item in schema["transformation_bundles"]
        if item["id"] == "service_foundations_company_communications"
    )
    schema_fact_ids = [fact["id"] for fact in schema["facts"]]
    authoritative = [
        fact_id
        for member in bundle["members"]
        for fact_id in member["authoritative_fact_ids"]
    ]
    assert len(schema_fact_ids) == 51
    assert len(authoritative) == len(set(authoritative)) == 51
    assert set(authoritative) == set(schema_fact_ids)

    for spec in schema["transformations"]:
        transformation = get_transformation(spec["representation"])
        artifacts = transformation.discover_artifacts(schema, SCHEMA_PATH, spec)
        assert transformation.validate(schema, artifacts) == []

    compilation = compile_variant_transformations(load(VARIANT_PATH))
    assert compilation.errors == []
    assert compilation.warnings == []
    assert compilation.uncovered_facts == []
    service_facts = [
        fact for fact in compilation.facts if fact.section_id == "service_foundations"
    ]
    assert len(service_facts) == 51
    assert all(len(fact.representations) == 1 for fact in service_facts)


def test_variant_folds_all_four_canonical_service_foundation_sections():
    sop = assemble_sop_variant(VARIANT_PATH)

    assert "Archive snapshot: August 8, 2026 at 16:30 PDT" in sop
    assert "dated company materials" in sop
    assert "February 25, 2025 at 12:08 EST" in sop
    assert "Looking up a customer account, affected wireless line" not in sop
    assert "Bill statuses are Draft, Issued, Paid" not in sop
    assert "5G service should be excellent, 4G good" not in sop
    assert "Use only what the customer tells you" not in sop


def test_current_exact_handoff_ruling_and_reference_edges_are_resolvable():
    email_text = "\n".join(
        BytesParser(policy=policy.default)
        .parsebytes(path.read_bytes())
        .get_body(preferencelist=("plain",))
        .get_content()
        for path in sorted((ARCHIVE / "emails").glob("*.eml"))
    )
    assert "YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON." in email_text
    assert "transfer_to_human_agents" in email_text

    combined = "\n".join(
        path.read_text(errors="replace")
        for folder in ("slack", "meetings", "attachments")
        for path in sorted((ARCHIVE / folder).glob("*"))
        if path.suffix in {".json", ".vtt", ".txt", ".md", ".csv", ".html"}
    ).lower()
    assert "wednesday's billing controls sync" in combined
    assert "friday's launch-readiness review" in combined
    assert "customer data & phone sync" in combined
    assert "february 25 rollout ledger" in combined


def test_task_is_discoverable_and_points_at_the_new_variant():
    task = load_hyper_tau_task(TASK_ID)
    assert task.source_domain == "telecom"
    assert len(task.test_task_ids) == 119
    assert task.sop_variant_manifest_path == VARIANT_RELATIVE_PATH


def test_one_task_packages_every_completed_section_transformation(tmp_path):
    task = load_hyper_tau_task(TASK_ID)
    kit = build_construction_kit(task, tmp_path / "telecom-information-distribution")
    materials = kit / "uploaded_materials"
    names = sorted(path.name for path in materials.iterdir())

    assert len(names) == 240
    assert sum(name.startswith("case_file_") for name in names) == 15
    assert sum(name.startswith("device_capture_") for name in names) == 36
    assert sum(name.startswith("screenshot_") for name in names) == 54
    assert sum(name.startswith("email_") for name in names) == 63
    assert sum(name.startswith("meeting_transcript_") for name in names) == 18
    assert sum(name.startswith("process_map_") for name in names) == 6
    assert sum(name.startswith("screen_recording") for name in names) == 4
    assert sum(name.startswith("system_export") for name in names) == 3
    assert sum(name.startswith("workspace_export_") for name in names) == 9
    assert sum(name.startswith("reference_document_") for name in names) == 30
    assert "knowledge_archive.html" in names
    assert "work_item_export.json" in names

    assert not list(kit.rglob("eval_manifest.json"))
    assert not list(kit.rglob("authored_session.json"))
    assert not list(kit.rglob("archive_source.json"))
    assert not list(kit.rglob("*timeline*"))
    assert not list(kit.rglob("catalog.json"))
    assert not list(kit.rglob("contact_sheet.png"))

    sop = (kit / "sop.md").read_text()
    for marker in (
        "dated company materials",
        "three dated working-session transcripts",
        "Read Charts 1, 2, and 3 at full resolution",
        "exported work-item",
        "Follow natural links",
        "Follow citations between those sources",
    ):
        assert marker in sop


def test_reference_document_adapter_packages_binary_and_text_evidence():
    schema = load(SCHEMA_PATH)
    spec = next(
        item
        for item in schema["transformations"]
        if item["representation"] == "reference_document"
    )
    transformation = get_transformation("reference_document")
    artifacts = transformation.discover_artifacts(schema, SCHEMA_PATH, spec)

    assert len(artifacts) == 30
    assert transformation.validate(schema, artifacts) == []

    binary = next(
        artifact
        for artifact in artifacts
        if artifact.source_path.suffix in {".docx", ".pptx", ".xlsx"}
    )
    packaged = transformation.neutralize(binary, 1)
    assert packaged.artifact_kind == "reference_document"
    assert packaged.content == binary.source_path.read_bytes()
    assert transformation.to_text(binary).strip()
