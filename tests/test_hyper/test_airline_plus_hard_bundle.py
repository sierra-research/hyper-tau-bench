"""Regression tests for the scaled Airline+ hard evidence bundle."""

from __future__ import annotations

import json
import re
from collections import Counter
from email import message_from_bytes
from pathlib import Path
from zipfile import ZipFile

from tau2.hyper.sandbox.kit import _copy_sop_variant_materials
from tau2.hyper.task_loader import load_hyper_tau_task
from tau2.hyper.transformations import compile_variant_transformations
from tau2.hyper.transformations.sop_variants import load_sop_variant_manifest
from tau2.utils.utils import DATA_DIR

HARD_ROOT = DATA_DIR / "tau2/hyper/sops/airline_plus/hard_bundle_001"
HARD_MANIFEST_PATH = (
    "tau2/hyper/sops/airline_plus/variants/core_evidence_bundle_hard_001.json"
)
BASELINE_MANIFEST_PATH = (
    "tau2/hyper/sops/airline_plus/variants/core_evidence_bundle_001.json"
)
# The release corpus pairs the hard evidence surface (003) with the core
# bundle it must not change (001); both run the same all-defects client API
# deployment, so the only declared difference is the evidence surface.
HARD_TASK_ID = (
    "003_airline_plus_construction_core_evidence_hard_all_defects_performance_easy"
)
BASELINE_TASK_ID = (
    "001_airline_plus_construction_core_evidence_all_defects"
    "_live_experiment_performance_medium"
)

EXPECTED_ARTIFACT_COUNTS = {
    "booking_hard_email_archive_001": 36,
    "booking_hard_process_maps_001": 3,
    "booking_hard_screenshots_001": 30,
    "booking_hard_records_001": 60,
    "manage_hard_email_archive_001": 57,
    "manage_hard_kickoff_documents_001": 3,
    "modification_hard_screenshots_001": 15,
    "modification_hard_records_001": 50,
    "modification_hard_slack_mcp_001": 1,
    "cancellation_hard_presentation_001": 1,
    "compensation_hard_screenshots_001": 65,
    "compensation_hard_records_001": 56,
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


AIRLINE_ROOT = DATA_DIR / "tau2/hyper/sops/airline_plus"

# Metadata files legitimately embed canonical statements (packs, manifests,
# and the authored pin file itself); they are not delivered evidence.
METADATA_FILE_RE = re.compile(
    r"(_transformation_pack\.json|eval_manifest\.json"
    r"|authored_fact_renditions\.json"
    r"|authored_client_email_threads\.json)$"
)

# The audit's subject-line probe (docs/verbatim-carrier-audit.md §3.2): a
# wording-governance subject isolated carrier threads at precision 1.00.
GOVERNANCE_SUBJECT_RE = re.compile(
    r"wording|sign-?off|final|approved|governing|exact|verbatim|compliance"
    r"|legal line|decision|ratif",
    re.IGNORECASE,
)


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _artifact_text(path: Path) -> str:
    if path.suffix == ".eml":
        message = message_from_bytes(path.read_bytes())
        return message.get_payload(decode=True).decode("utf-8")
    return path.read_text()


def _shingles(text: str, size: int) -> set[tuple[str, ...]]:
    words = re.findall(r"[a-z0-9$']+", _flat(text))
    return {tuple(words[i : i + size]) for i in range(len(words) - size + 1)}


def _schema_statements() -> dict[str, str]:
    statements: dict[str, str] = {}
    for section in ("booking_flight", "manage_existing_reservation"):
        schema = _load_json(AIRLINE_ROOT / "sections" / section / "schema.json")
        for fact in schema["facts"]:
            statements[fact["id"]] = fact["statement"]
    return statements


def _pack_transformations() -> list[dict]:
    # The client-overlay packs join the scan so the rewritten client copies
    # obey the same canonical-register, rendition-pin, and governance-subject
    # gates as the hard artifacts they substitute. client_knowledge members
    # materialize nothing, so they carry no artifacts to scan.
    return [
        transformation
        for pack_name in (
            "booking_transformation_pack.json",
            "manage_transformation_pack.json",
            "client_overlay/booking_client_transformation_pack.json",
            "client_overlay/manage_client_transformation_pack.json",
        )
        for transformation in _load_json(HARD_ROOT / pack_name)["transformations"]
        if transformation.get("representation") != "client_knowledge"
    ]


def test_canonical_statements_confined_to_canonical_register_surfaces():
    """No delivered artifact may quote canonical schema wording unless its pin
    carries the ``canonical`` register (surfaces with an in-world warrant:
    flowcharts, the workbook, console lines, help-site policy lines). The
    audit showed verbatim statements let register and shingle probes isolate
    carriers at precision 1.00; conversational carriers must re-voice."""
    statements = _schema_statements()
    allowed: dict[str, set[str]] = {fact_id: set() for fact_id in statements}

    def allow(entry: dict, fact_ids: list[str]) -> None:
        for fact_id in fact_ids:
            for key in (
                "path",
                "text_source_path",
                "generation_source_path",
                "author_source_path",
                "eval_manifest_path",
            ):
                if key in entry:
                    allowed[fact_id].add(str(DATA_DIR / entry[key]))

    for transformation in _pack_transformations():
        for entry in transformation["artifacts"]:
            fact_ids = entry.get("included_fact_ids") or []
            if not fact_ids:
                continue
            if entry.get("rendition_register") == "canonical":
                allow(entry, fact_ids)
                continue
            registers = entry.get("rendition_registers")
            if registers:
                allow(
                    entry,
                    [fid for fid in fact_ids if registers.get(fid) == "canonical"],
                )
                continue
            if "eval_manifest_path" in entry:
                manifest = _load_json(DATA_DIR / entry["eval_manifest_path"])
                allow(
                    entry,
                    [
                        fact["id"]
                        for fact in manifest.get("authoritative_facts", [])
                        if fact.get("rendition_register") == "canonical"
                    ],
                )

    for path in sorted(HARD_ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in {
            ".md",
            ".eml",
            ".html",
            ".txt",
            ".json",
        }:
            continue
        if METADATA_FILE_RE.search(path.name):
            continue
        text = _flat(_artifact_text(path))
        for fact_id, statement in statements.items():
            if _flat(statement) in text:
                assert str(path) in allowed[fact_id], (
                    f"{path.relative_to(HARD_ROOT)} quotes the canonical "
                    f"statement for {fact_id} without a canonical-register pin"
                )


def test_voiced_renditions_are_pinned_owned_and_never_quote_schema_wording():
    """Every carrier's pack entry pins its fact renditions; each voiced
    rendition occurs in its owner, leaks into no sibling artifact, and shares
    no 6-gram with the canonical statement it re-voices."""
    statements = _schema_statements()
    checked = 0
    for transformation in _pack_transformations():
        entries = transformation["artifacts"]
        if not any("fact_renditions" in entry for entry in entries):
            continue
        texts: dict[str, str] = {}
        for entry in entries:
            source = entry.get("text_source_path", entry["path"])
            texts[entry["path"]] = _flat(_artifact_text(DATA_DIR / source))
        for entry in entries:
            fact_ids = entry.get("included_fact_ids") or []
            renditions = entry.get("fact_renditions") or {}
            assert sorted(renditions) == sorted(fact_ids), (
                transformation["id"],
                entry["path"],
            )
            registers = entry.get("rendition_registers") or {}
            for fact_id, rendition in renditions.items():
                assert _flat(rendition) in texts[entry["path"]], (
                    transformation["id"],
                    entry["path"],
                    fact_id,
                )
                for other_path, other_text in texts.items():
                    if other_path != entry["path"]:
                        assert _flat(rendition) not in other_text, (
                            f"rendition for {fact_id} leaks from "
                            f"{entry['path']} into {other_path}"
                        )
                if registers.get(fact_id, "voiced") == "canonical":
                    continue
                statement = statements[fact_id]
                assert _flat(statement) not in _flat(rendition)
                assert _flat(rendition) not in _flat(statement)
                assert not (_shingles(rendition, 6) & _shingles(statement, 6)), (
                    f"voiced rendition for {fact_id} in {entry['path']} "
                    "shares schema wording"
                )
                checked += 1
    assert checked >= 40


def test_email_archives_pool_wording_governance_topics_with_filler():
    """The audit's subject probe must stay dead: wording-governance subjects
    exist on zero-fact threads in both archives (dead proposals, fact-free
    ratifications), and the probe's carrier precision stays at or below 1/2."""
    for transformation in _pack_transformations():
        if not transformation["id"].endswith("email_archive_001"):
            continue
        flagged_carriers = 0
        flagged_filler = 0
        for entry in transformation["artifacts"]:
            message = message_from_bytes((DATA_DIR / entry["path"]).read_bytes())
            subject = message["Subject"]
            if not GOVERNANCE_SUBJECT_RE.search(subject):
                continue
            if entry.get("included_fact_ids"):
                flagged_carriers += 1
            else:
                flagged_filler += 1
        assert flagged_filler >= 3, transformation["id"]
        assert flagged_carriers * 2 <= flagged_carriers + flagged_filler, (
            transformation["id"],
            flagged_carriers,
            flagged_filler,
        )


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

    assert hard.source_domain == baseline.source_domain == "airline_plus"
    assert hard.sop_variant_manifest_path == HARD_MANIFEST_PATH
    assert baseline.sop_variant_manifest_path == BASELINE_MANIFEST_PATH
    assert (
        hard.test_task_ids
        == baseline.test_task_ids
        == [str(index) for index in range(67)]
    )

    (hard_stage,) = hard.composition_pipeline
    (baseline_stage,) = baseline.composition_pipeline
    assert hard_stage["stage"] == baseline_stage["stage"] == "information_distribution"
    assert hard_stage["transformed_sections"] == baseline_stage["transformed_sections"]
    assert hard_stage["variant_manifest_path"] == HARD_MANIFEST_PATH
    assert baseline_stage["variant_manifest_path"] == BASELINE_MANIFEST_PATH

    assert (
        hard.client_api_deployment_manifest
        == baseline.client_api_deployment_manifest
        == "airline_plus/all_defects_v1"
    )
    assert hard.sandbox_config == baseline.sandbox_config
    assert _model_pool(hard) == _model_pool(baseline)
    assert hard.agent_llm == baseline.agent_llm
    assert hard.agent_reasoning_effort == baseline.agent_reasoning_effort
    assert hard.user_llm == baseline.user_llm
    assert hard.user_reasoning_effort == baseline.user_reasoning_effort


def test_hard_bundle_compiles_to_exact_85_fact_377_artifact_contract():
    hard_manifest = load_sop_variant_manifest(HARD_MANIFEST_PATH)
    compilation = compile_variant_transformations(hard_manifest)

    assert compilation.errors == []
    assert compilation.warnings == []
    assert compilation.report()["totals"] == {
        "facts": 85,
        "covered": 85,
        "uncovered": 0,
        "multiply_represented": 0,
    }
    actual_counts = {
        entry["transformation_id"]: entry["artifact_count"]
        for entry in compilation.report()["transformations"]
        if entry["transformation_id"] in EXPECTED_ARTIFACT_COUNTS
    }
    assert actual_counts == EXPECTED_ARTIFACT_COUNTS
    assert sum(actual_counts.values()) == 377


def test_imported_hard_pack_does_not_change_current_bundle():
    baseline_manifest = load_sop_variant_manifest(BASELINE_MANIFEST_PATH)
    compilation = compile_variant_transformations(baseline_manifest)

    assert compilation.errors == []
    assert compilation.warnings == []
    assert compilation.report()["totals"] == {
        "facts": 85,
        "covered": 85,
        "uncovered": 0,
        "multiply_represented": 0,
    }
    baseline_transformation_artifact_count = sum(
        entry["artifact_count"] for entry in compilation.report()["transformations"]
    )
    assert baseline_transformation_artifact_count == 191


def test_hard_bundle_materializes_377_neutralized_artifacts(tmp_path):
    manifest = load_sop_variant_manifest(HARD_MANIFEST_PATH)
    kit_dir = tmp_path / "kit"
    _copy_sop_variant_materials(manifest, kit_dir)

    materials = sorted((kit_dir / "uploaded_materials").iterdir())
    assert len(materials) == 377
    assert Counter(path.suffix for path in materials) == {
        ".md": 169,
        ".png": 113,
        ".eml": 93,
        ".json": 1,
        ".pdf": 1,
    }
    artifact_stems = Counter(re.sub(r"_\d+$", "", path.stem) for path in materials)
    assert artifact_stems == {
        "case_file": 166,
        "email": 93,
        "intake_form": 3,
        "process_map": 3,
        "screenshot": 110,
        "slide_deck": 1,
        "workspace_export": 1,
    }
    assert not any("hard" in path.name for path in materials)
    assert not any("fact" in path.name for path in materials)


def test_hard_bundle_difficulty_levers_remain_realistic_and_auditable():
    kickoff_words = sum(
        len(path.read_text().split())
        for path in (HARD_ROOT / "kickoff_documents").glob("*.md")
    )
    assert 3_000 <= kickoff_words <= 3_500

    slack_manifest = _load_json(HARD_ROOT / "slack_capture/eval_manifest.json")
    assert slack_manifest["tool_call_count"] == 43
    assert slack_manifest["thread_count"] == 38
    assert slack_manifest["message_count"] == 288
    decisions = slack_manifest["decision_history"]
    assert len(decisions) == 10
    assert Counter(decision["status"] for decision in decisions) == {
        "superseded": 9,
        "final_current": 1,
    }

    slack_capture = _load_json(
        HARD_ROOT / "slack_capture/passenger_servicing_capture.json"
    )
    assert slack_capture["workspace"] == {
        "id": "T08MeridianAIR1",
        "name": "Meridian Airlines",
        "project": "Project Atlas",
    }
    assert len(slack_capture["tool_calls"]) == 43
    assert (
        sum(
            len(call["response"]["structured_content"]["messages"])
            for call in slack_capture["tool_calls"]
        )
        == 288
    )
    assert "https://meridianairlines.slack.com/" in json.dumps(slack_capture)

    booking_site = _load_json(HARD_ROOT / "booking_website/eval_manifest.json")
    compensation_site = _load_json(
        HARD_ROOT / "compensation_website/eval_manifest.json"
    )
    assert booking_site["distribution"] == {
        "fact_bearing_pages": 6,
        "distractor_pages": 24,
        "fact_page_ordinals": [2, 9, 13, 22, 27, 29],
    }
    assert compensation_site["distribution"] == {
        "fact_bearing_pages": 5,
        "distractor_pages": 60,
        "fact_page_ordinals": [5, 17, 22, 38, 61],
    }
    for site in (booking_site, compensation_site):
        ordinals = site["distribution"]["fact_page_ordinals"]
        strides = {b - a for a, b in zip(ordinals, ordinals[1:])}
        assert len(strides) >= 3, "fact pages must not sit on a regular stride"

    records = [
        *sorted((HARD_ROOT / "booking_records").glob("case_*.md")),
        *sorted((HARD_ROOT / "modification_records").glob("case_*.md")),
        *sorted((HARD_ROOT / "compensation_records").glob("case_*.md")),
    ]
    assert len(records) == 166
    turn_counts = []
    for record in records:
        turn_lines = [
            line
            for line in record.read_text().splitlines()
            if line.startswith("**Turn ")
        ]
        turn_text = [line.split(":** ", 1)[1] for line in turn_lines]
        assert len(turn_text) == len(set(turn_text))
        turn_counts.append(len(turn_lines))
    # Length must vary like a real QA archive: a wide spread with a genuine
    # heavy tail (core sections run to 82-97 turns), no pinned ceiling, and no
    # dominant length a reader could use to separate carriers from filler.
    assert min(turn_counts) >= 6
    assert 36 <= max(turn_counts) <= 120
    assert max(turn_counts) - min(turn_counts) >= 24
    assert len(set(turn_counts)) >= 12
    assert max(Counter(turn_counts).values()) <= len(records) // 4


def test_record_lengths_pool_carriers_with_filler():
    """Carrier records must be unfindable by length: medians pooled with the
    filler population, no carrier in the top length band, and the longest
    records always filler (the heavy tail belongs to noise, not signal)."""
    packs = {
        "booking_hard_records_001": HARD_ROOT / "booking_transformation_pack.json",
        "modification_hard_records_001": HARD_ROOT / "manage_transformation_pack.json",
        "compensation_hard_records_001": HARD_ROOT / "manage_transformation_pack.json",
    }
    for transformation_id, pack_path in packs.items():
        pack = _load_json(pack_path)
        (transformation,) = [
            entry
            for entry in pack["transformations"]
            if entry["id"] == transformation_id
        ]
        lengths = {}
        carriers = set()
        for artifact in transformation["artifacts"]:
            name = artifact["path"].rsplit("/", 1)[-1]
            record_dir = artifact["path"].rsplit("/", 2)[-2]
            lengths[name] = len((HARD_ROOT / record_dir / name).read_text().split())
            if artifact["included_fact_ids"]:
                carriers.add(name)
        filler_lengths = sorted(
            words for name, words in lengths.items() if name not in carriers
        )
        carrier_lengths = sorted(lengths[name] for name in carriers)
        assert carriers and filler_lengths

        def median(values: list[int]) -> float:
            mid = len(values) // 2
            if len(values) % 2:
                return float(values[mid])
            return (values[mid - 1] + values[mid]) / 2

        ratio = median(carrier_lengths) / median(filler_lengths)
        assert 0.7 <= ratio <= 1.4, (transformation_id, ratio)
        top_band = max(2, len(lengths) // 10)
        longest = sorted(lengths, key=lengths.get, reverse=True)[:top_band]
        assert not carriers.intersection(longest), (transformation_id, longest)
        assert max(filler_lengths) >= 2 * median(filler_lengths), transformation_id


def test_cancellation_workbook_has_28_pages_in_both_declared_formats():
    workbook_dir = HARD_ROOT / "cancellation_workbook"
    pptx_path = workbook_dir / "cancellation_operations_workbook_hard.pptx"
    pdf_path = workbook_dir / "cancellation_operations_workbook_hard.pdf"
    with ZipFile(pptx_path) as archive:
        slide_names = [
            name
            for name in archive.namelist()
            if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
        ]
    assert len(slide_names) == 28
    assert pdf_path.read_bytes().startswith(b"%PDF")

    eval_manifest = _load_json(workbook_dir / "eval_manifest.json")
    assert eval_manifest["page_count"] == 28
    pages = [page["page"] for page in eval_manifest["page_fact_ids"]]
    assert pages == sorted(pages)
    assert 1 <= pages[0] and pages[-1] <= 28
    # The governing pages must not sit on a fixed stride: a constant page
    # interval lets a reader predict every carrier page from the first one.
    strides = {second - first for first, second in zip(pages, pages[1:])}
    assert len(strides) > 1, pages
