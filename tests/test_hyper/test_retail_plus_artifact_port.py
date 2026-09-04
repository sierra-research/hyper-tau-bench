"""Gates for the retail_plus transformation artifacts.

The multimodal artifacts under data/tau2/hyper/sops/retail_plus/ were
originally ported from the canonical retail artifacts; since the 2026-08-04
standalone cutover the tree is edited directly, and the porter tooling and
the frozen canonical trees are not part of this release. The porter's
forbidden-token expectations (retired phrases, the canonical identifier
universe read off the shipped canonical retail db) are pinned in
tests/plus_support/retail_plus.py. These tests enforce integrity of the
committed tree: the delivered-order, working-session, helpdesk, and
API-contract corpora keep their losslessness invariants, render provenance
pins match, schema artifact references and declared transformations resolve,
no canonical retail phrase or identifier survives in the text artifacts,
storefront photo bindings resolve to the deranged plus item ids by option
combination, storefront routes and refund-window rewrites ground in the plus
db, and call-audio renditions are complete.
"""

import io
import json
import re
import struct
import zipfile
from pathlib import Path
from statistics import median

import pytest
from plus_support import retail_plus as expectations
from plus_support.leakage import scan_leakage

from tau2.hyper.transformations import get_transformation

REPO_ROOT = Path(__file__).resolve().parents[2]
DST_ROOT = REPO_ROOT / "data" / "tau2" / "hyper" / "sops" / "retail_plus"
PLUS_DB_PATH = REPO_ROOT / "data" / "tau2" / "domains" / "retail_plus" / "db.json"

STOREFRONT = DST_ROOT / "sections/service_foundations/website_screenshot_001_full_site"
PENDING = DST_ROOT / "sections/manage_pending_order"
FLOWCHART = PENDING / "process_flowchart_001"
DECK = PENDING / "process_presentation_001"
EMAIL = PENDING / "email_thread_archive_001"
SLACK = PENDING / "slack_mcp_dump_001"
IDENTITY = DST_ROOT / "sections/customer_identity/customer_kickoff_document_001"
DELIVERED_RECORDS = DST_ROOT / "sections/manage_delivered_order/support_transcripts_001"
WORKING_SESSION = DST_ROOT / "sections/service_foundations/recorded_working_session_001"
HELPDESK_EXPORT = (
    DST_ROOT / "sections/service_foundations/helpdesk_automation_export_001"
)
API_CONTRACT = DST_ROOT / "sections/service_foundations/api_contract_pack_001"


@pytest.fixture(scope="module")
def plus_db():
    return json.loads(PLUS_DB_PATH.read_text())


def png_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG"
    width, height = struct.unpack(">II", header[16:24])
    return width, height


def test_customer_identity_intake_is_sparse_and_lossless():
    schema_path = DST_ROOT / "sections/customer_identity/schema.json"
    schema = json.loads(schema_path.read_text())
    expected_fact_ids = {fact["id"] for fact in schema["facts"]}
    spec = next(
        spec
        for spec in schema["transformations"]
        if spec["id"] == "retail_customer_identity_discovery_intake"
    )

    transformation = get_transformation("customer_kickoff_document")
    artifacts = transformation.discover_artifacts(schema, schema_path, spec)
    assert transformation.validate(schema, artifacts) == []
    assert transformation.covered_fact_ids(schema, artifacts) == expected_fact_ids
    assert len(artifacts) == 1

    text = transformation.to_text(artifacts[0])
    assert len(text.splitlines()) >= 700
    assert len(text.split()) >= 4000
    assert text.count("Confirmed pilot decision") >= 12
    assert not any(fact_id in text for fact_id in expected_fact_ids)

    manifest = json.loads((IDENTITY / "eval_manifest.json").read_text())
    manifest_facts = manifest["authoritative_facts"]
    assert {fact["id"] for fact in manifest_facts} == expected_fact_ids
    assert all(len(fact["evidence_locations"]) == 2 for fact in manifest_facts)
    assert len(manifest["excluded_claims"]) >= 6
    assert len(manifest["non_policy_context"]) >= 7

    kit_file = transformation.neutralize(artifacts[0], 1)
    assert kit_file.relative_path == (
        "uploaded_materials/northstar_identity_and_crm_readiness_intake.md"
    )
    assert kit_file.content == artifacts[0].source_path.read_bytes()


def test_delivered_order_case_corpus_is_large_and_lossless():
    schema_path = DST_ROOT / "sections/manage_delivered_order/schema.json"
    schema = json.loads(schema_path.read_text())
    all_fact_ids = {fact["id"] for fact in schema["facts"]}
    neighboring_fact_ids = {
        "exchange_new_variant_available",
        "exchange_refund_destination_any_saved_payment_method",
        "return_can_include_some_or_all_items",
        "return_refund_destination_disallowed_options",
        "return_refund_destination_original_or_existing_gift_card",
    }
    expected_owned = all_fact_ids - neighboring_fact_ids
    spec = next(
        spec
        for spec in schema["transformations"]
        if spec["id"] == "retail_manage_delivered_order_support_transcripts"
    )

    transformation = get_transformation("support_transcripts")
    artifacts = transformation.discover_artifacts(schema, schema_path, spec)
    assert transformation.validate(schema, artifacts) == []
    assert transformation.covered_fact_ids(schema, artifacts) == expected_owned
    assert len(artifacts) == 40

    manifest = json.loads((DELIVERED_RECORDS / "eval_manifest.json").read_text())
    assert manifest["case_count"] == 40
    assert manifest["distribution"] == {
        "fact_bearing_cases": 13,
        "distractor_cases": 27,
        "channels": {"chat": 20, "phone call": 20},
        "full_conversations": 26,
        "later_turn_excerpts": 14,
    }
    owned_by_case = [case["authoritative_fact_ids"] for case in manifest["cases"]]
    assert all(len(fact_ids) <= 1 for fact_ids in owned_by_case)
    assert {
        fact_id for fact_ids in owned_by_case for fact_id in fact_ids
    } == expected_owned

    length_spec = manifest["length_distribution"]
    word_counts = {
        case["filename"]: len(
            (DELIVERED_RECORDS / case["filename"]).read_text().split()
        )
        for case in manifest["cases"]
    }
    median_words = median(word_counts.values())
    long_tail = {
        filename
        for filename, count in word_counts.items()
        if count >= median_words * length_spec["long_tail_median_multiplier"]
    }
    extreme_tail = {
        filename
        for filename, count in word_counts.items()
        if count >= median_words * length_spec["extreme_tail_median_multiplier"]
    }
    roles_by_file = {case["filename"]: case["role"] for case in manifest["cases"]}
    assert length_spec["shape"] == "right_skewed"
    assert len(long_tail) >= length_spec["minimum_long_tail_cases"]
    assert len(extreme_tail) >= length_spec["minimum_extreme_tail_cases"]
    assert {roles_by_file[filename] for filename in long_tail} == {
        "fact_bearing",
        "distractor",
    }
    assert max(word_counts.values()) >= 3 * median_words

    corpus = "\n".join(transformation.to_text(artifact) for artifact in artifacts)
    assert corpus.count("QA status: approved") == 40
    assert corpus.count("· Agent:**") + corpus.count("· Customer:**") >= 450
    assert not any(fact_id in corpus for fact_id in all_fact_ids)

    bundle = next(
        bundle
        for bundle in schema["transformation_bundles"]
        if bundle["id"] == "manage_delivered_order_multimodal"
    )
    assert set(bundle["fact_ids"]) == all_fact_ids
    assert len(bundle["members"]) == 3
    member = next(
        member
        for member in bundle["members"]
        if member["transformation_id"]
        == "retail_manage_delivered_order_support_transcripts"
    )
    assert set(member["authoritative_fact_ids"]) == expected_owned
    assert set(member["depends_on_fact_ids"]) == neighboring_fact_ids


def test_service_foundations_working_session_is_lifecycle_rich_and_lossless():
    schema_path = DST_ROOT / "sections/service_foundations/schema.json"
    schema = json.loads(schema_path.read_text())
    spec = next(
        spec
        for spec in schema["transformations"]
        if spec["id"] == "retail_service_foundations_recorded_working_session"
    )
    manifest = json.loads((WORKING_SESSION / "eval_manifest.json").read_text())
    expected_fact_ids = set(manifest["authoritative_fact_ids"])

    transformation = get_transformation("recorded_working_session")
    artifacts = transformation.discover_artifacts(schema, schema_path, spec)
    assert transformation.validate(schema, artifacts) == []
    assert transformation.covered_fact_ids(schema, artifacts) == expected_fact_ids
    assert len(artifacts) == 5
    assert len(expected_fact_ids) == 16

    texts = [transformation.to_text(artifact) for artifact in artifacts]
    assert all(text.startswith("WEBVTT\n") for text in texts)
    assert sum(text.count(" --> ") for text in texts) >= 900
    assert sum(len(re.findall(r"(?m)^<v [^>]+>", text)) for text in texts) >= 900
    total_words = 0
    durations = []
    for text in texts:
        cue_timestamps = re.findall(
            r"(\d{2}):(\d{2}):(\d{2}\.\d{3}) --> "
            r"(\d{2}):(\d{2}):(\d{2}\.\d{3})",
            text,
        )
        start = cue_timestamps[0][:3]
        end = cue_timestamps[-1][3:]
        start_seconds = int(start[0]) * 3600 + int(start[1]) * 60 + float(start[2])
        end_seconds = int(end[0]) * 3600 + int(end[1]) * 60 + float(end[2])
        duration_minutes = (end_seconds - start_seconds) / 60
        durations.append(duration_minutes)
        spoken = " ".join(re.findall(r"(?m)^<v [^>]+>(.*)$", text))
        words = len(re.findall(r"\b[\w’'-]+\b", spoken))
        total_words += words
        # The series is four hour-scale working sessions plus one short
        # servicing sync; the word floor only makes sense for the former.
        if duration_minutes >= 50:
            assert words >= 4_600
        else:
            assert words >= 2_500
        assert 90 <= words / duration_minutes <= 145
    assert total_words >= 21_000
    assert sum(duration >= 50 for duration in durations) == 4
    assert sum(duration < 30 for duration in durations) == 1
    assert max(durations) > 60
    assert max(durations) - min(durations) >= 10
    combined_text = "\n".join(texts)
    assert not any(fact_id in combined_text for fact_id in expected_fact_ids)
    assert "final_current" not in combined_text
    assert "[crosstalk]" in combined_text
    assert "[inaudible" in combined_text
    assert "um" in combined_text.lower()

    decisions = manifest["decisions"]
    finals = [
        decision for decision in decisions if decision["status"] == "final_current"
    ]
    assert {decision["fact_id"] for decision in finals} == expected_fact_ids
    assert len(finals) == 16
    assert len({decision["speaker"] for decision in finals}) == 4
    assert sum(decision["status"] == "proposal" for decision in decisions) >= 5
    assert (
        sum(decision["status"] in {"rejected", "superseded"} for decision in decisions)
        >= 7
    )
    assert len(manifest["meetings"]) == 5
    assert {decision["meeting_id"] for decision in finals} == {
        meeting["meeting_id"] for meeting in manifest["meetings"]
    }
    events_by_fact = {
        fact_id: [decision for decision in decisions if decision["fact_id"] == fact_id]
        for fact_id in expected_fact_ids
    }
    assert (
        sum(
            len({event["meeting_id"] for event in events}) > 1
            for events in events_by_fact.values()
        )
        >= 5
    )

    expected_filenames = {
        "2026-05-06_care_pilot_intake.vtt",
        "2026-05-13_customer_data_architecture_review.vtt",
        "2026-05-28_qa_calibration_working_session.vtt",
        "2026-05-28_servicing_sync.vtt",
        "2026-06-04_launch_readiness_signoff.vtt",
    }
    assert {artifact.source_path.name for artifact in artifacts} == expected_filenames
    for ordinal, artifact in enumerate(artifacts, 1):
        kit_file = transformation.neutralize(artifact, ordinal)
        assert (
            kit_file.relative_path == f"uploaded_materials/{artifact.source_path.name}"
        )
        assert kit_file.content == artifact.source_path.read_bytes()

    bundle = next(
        bundle
        for bundle in schema["transformation_bundles"]
        if bundle["id"] == "service_foundations_multimodal"
    )
    assert len(bundle["members"]) == 5
    assert len(bundle["fact_ids"]) == 63
    member = next(
        member
        for member in bundle["members"]
        if member["transformation_id"]
        == "retail_service_foundations_recorded_working_session"
    )
    assert set(member["authoritative_fact_ids"]) == expected_fact_ids


def test_service_foundations_helpdesk_export_is_dense_current_and_lossless():
    schema_path = DST_ROOT / "sections/service_foundations/schema.json"
    schema = json.loads(schema_path.read_text())
    spec = next(
        spec
        for spec in schema["transformations"]
        if spec["id"] == "retail_service_foundations_helpdesk_automation_export"
    )
    manifest = json.loads((HELPDESK_EXPORT / "eval_manifest.json").read_text())
    fact_map = json.loads((HELPDESK_EXPORT / "fact_map.json").read_text())
    expected_fact_ids = set(manifest["authoritative_fact_ids"])

    transformation = get_transformation("helpdesk_automation_export")
    artifacts = transformation.discover_artifacts(schema, schema_path, spec)
    assert transformation.validate(schema, artifacts) == []
    assert transformation.covered_fact_ids(schema, artifacts) == expected_fact_ids
    assert len(artifacts) == 1
    assert len(expected_fact_ids) == 25

    authored = json.loads((HELPDESK_EXPORT / "authored_export.json").read_text())
    assert len(authored["macros"]) == 60
    assert len(authored["triggers"]) == 25
    assert len(authored["policy_contracts"]) == 8
    assert len(authored["fields"]) == 55
    assert len(authored["sla_policies"]) == 6
    assert len(authored["views"]) == 12
    contract_index = {
        contract["contract_id"]: contract for contract in authored["policy_contracts"]
    }
    closed_facts = {
        fact_id: evidence
        for fact_id, evidence in fact_map["facts"].items()
        if evidence["claim_type"] == "closed_world_policy"
    }
    assert len(closed_facts) == 9
    assert all(evidence["closure_object_ids"] for evidence in closed_facts.values())
    assert all(
        contract_index[contract_id]["closed_world"]["complete"] is True
        and contract_index[contract_id]["closed_world"]["unlisted_behavior"]
        in {"deny", "reject", "reject_transaction"}
        for evidence in closed_facts.values()
        for contract_id in evidence["closure_object_ids"]
    )
    assert any(
        macro["status"] == "retired" and macro["historical_usage"] > 0
        for macro in authored["macros"]
    )
    assert any(
        macro["status"] == "draft" and macro["usage_30d"] == 0
        for macro in authored["macros"]
    )

    artifact = artifacts[0]
    first = transformation.neutralize(artifact, 1)
    second = transformation.neutralize(artifact, 1)
    assert first.relative_path == (
        "uploaded_materials/northstar_care_admin_export_2026-06-05.zip"
    )
    assert first.content == second.content
    with zipfile.ZipFile(io.BytesIO(first.content)) as archive:
        assert archive.namelist() == [
            "cover_email.eml",
            "macros.json",
            "triggers.json",
            "policy_contracts.json",
            "fields.csv",
            "sla_policies.json",
            "views.json",
        ]
        corpus = "\n".join(
            archive.read(filename).decode() for filename in archive.namelist()
        )
    assert not any(fact_id in corpus for fact_id in expected_fact_ids)
    assert 'active"' in corpus
    assert "superseded_by" in corpus
    assert "Retired group router" in corpus

    bundle = next(
        bundle
        for bundle in schema["transformation_bundles"]
        if bundle["id"] == "service_foundations_multimodal"
    )
    member = next(
        member
        for member in bundle["members"]
        if member["transformation_id"]
        == "retail_service_foundations_helpdesk_automation_export"
    )
    assert set(member["authoritative_fact_ids"]) == expected_fact_ids
    assert len(bundle["fact_ids"]) == 63
    assert set(fact["id"] for fact in schema["facts"]) == set(bundle["fact_ids"])


def test_service_foundations_api_contract_is_current_explicit_and_lossless():
    schema_path = DST_ROOT / "sections/service_foundations/schema.json"
    schema = json.loads(schema_path.read_text())
    spec = next(
        spec
        for spec in schema["transformations"]
        if spec["id"] == "retail_service_foundations_api_contract_pack"
    )
    manifest = json.loads((API_CONTRACT / "eval_manifest.json").read_text())
    fact_map = json.loads((API_CONTRACT / "fact_map.json").read_text())
    expected_fact_ids = {
        "customer_profile_fields",
        "customers_can_save_any_number_of_payment_methods",
        "order_records_owner",
        "order_records_payment_history",
        "round_money_arithmetic_before_storage",
        "stored_money_uses_cent_precision",
        "stored_money_rejects_float_precision_artifacts",
    }
    assert set(manifest["authoritative_fact_ids"]) == expected_fact_ids
    assert set(fact_map["facts"]) == expected_fact_ids

    transformation = get_transformation("api_contract_pack")
    artifacts = transformation.discover_artifacts(schema, schema_path, spec)
    assert transformation.validate(schema, artifacts) == []
    assert transformation.covered_fact_ids(schema, artifacts) == expected_fact_ids
    assert len(artifacts) == 1

    authored = json.loads((API_CONTRACT / "authored_contract.json").read_text())
    release = authored["release"]
    assert release == {
        "contract_id": "CONTRACT-CARE-V3",
        "environment": "production",
        "status": "published",
        "current": True,
        "effective_at": "2026-06-12T09:00:00-04:00",
        "snapshot_at": "2026-06-12T16:00:00-04:00",
        "superseded_by": None,
    }
    schemas = authored["openapi"]["components"]["schemas"]
    methods = schemas["User"]["properties"]["payment_methods"]
    assert methods["x-northstar-cardinality"] == {
        "minimum": 0,
        "maximum": None,
        "meaning": "unbounded",
    }
    assert "maxProperties" not in methods
    assert set(schemas["PaymentHistoryEntry"]["properties"]) == {
        "transaction_type",
        "amount",
        "payment_method_id",
    }
    money = schemas["Money"]
    assert money["type"] == "number"
    assert money["multipleOf"] == 0.01
    assert money["x-northstar-storage"] == {
        "precision": "cent",
        "maximum-fractional-decimal-digits": 2,
        "round-arithmetic-before-write": True,
        "reject-float-artifacts": True,
        "json-trailing-zeroes-required": False,
    }
    assert schemas["DeprecatedCustomerV2"]["deprecated"] is True
    assert schemas["DeprecatedCustomerV2"]["x-lifecycle"] == "retired"
    assert schemas["InternalAdminLedgerProjection"]["x-audience"] == "internal_admin"

    artifact = artifacts[0]
    first = transformation.neutralize(artifact, 1)
    second = transformation.neutralize(artifact, 1)
    assert first.content == second.content
    assert first.relative_path == (
        "uploaded_materials/northstar_retail_record_contract_2026-06-12.zip"
    )
    with zipfile.ZipFile(io.BytesIO(first.content)) as archive:
        assert archive.namelist() == [
            "cover_email.eml",
            "openapi.yaml",
            "postman_collection.json",
            "error_behavior.csv",
            "record_contract_notes.md",
        ]
        corpus = "\n".join(
            archive.read(filename).decode() for filename in archive.namelist()
        )
    assert not any(fact_id in corpus for fact_id in expected_fact_ids)
    assert "Saved Postman responses demonstrate concrete payloads" in corpus
    assert "five-card cap visible in the retired v2" in corpus
    assert "does not define a tie-breaking algorithm" in corpus

    bundle = next(
        bundle
        for bundle in schema["transformation_bundles"]
        if bundle["id"] == "service_foundations_multimodal"
    )
    member = next(
        member
        for member in bundle["members"]
        if member["transformation_id"] == "retail_service_foundations_api_contract_pack"
    )
    assert set(member["authoritative_fact_ids"]) == expected_fact_ids
    assert len(bundle["members"]) == 5
    assert set(bundle["fact_ids"]) == {fact["id"] for fact in schema["facts"]}


def test_render_provenance_pins_match():
    """Every render source and output hashes to the committed provenance pin.

    Renders run out of band (headless Chrome), so CI cannot re-render and
    compare. The pin proves staleness instead: a source edited without
    re-rendering + re-pinning, an output swapped without re-pinning, or a
    new/removed file dodging a pinned glob all break here. It cannot prove
    causality — that the committed pixels came from the committed sources
    rests on the authoring-side re-render workflow
    plus review of pin-only diffs.
    """
    import fnmatch
    import hashlib

    pin = json.loads((DST_ROOT / "render_provenance.json").read_text())
    assert pin["groups"]
    problems = []
    for group in pin["groups"]:
        for glob_key, files_key in (
            ("source_glob", "sources"),
            ("output_glob", "outputs"),
        ):
            pattern = group.get(glob_key)
            if not pattern:
                continue
            current = {str(p.relative_to(DST_ROOT)) for p in DST_ROOT.glob(pattern)}
            pinned = {rel for rel in group[files_key] if fnmatch.fnmatch(rel, pattern)}
            if current != pinned:
                problems.append(
                    f"{group['id']}: {glob_key} drift — unpinned {sorted(current - pinned)},"
                    f" missing {sorted(pinned - current)}"
                )
        for files_key in ("sources", "outputs"):
            for rel, pinned_sha in group[files_key].items():
                path = DST_ROOT / rel
                if not path.exists():
                    problems.append(f"{group['id']}: {rel} missing")
                    continue
                if hashlib.sha256(path.read_bytes()).hexdigest() != pinned_sha:
                    problems.append(
                        f"{group['id']}: {rel} hash drift — if a source changed,"
                        " re-render its outputs and update the"
                        " pinned hashes in render_provenance.json"
                    )
    assert not problems, "\n".join(problems)


def test_all_declared_transformations_resolve():
    """Every transformation spec resolved from every committed schema
    discovers its artifacts, and every discovered source file exists.

    The pre-hardening tree carried nine legacy sections whose schemas
    declared a ``support_transcripts`` transformation with null artifacts;
    discovery fell back to a ``training_records/`` directory the port never
    created, so kit compilation over those sections errored. Those sections
    now declare ``transformations: []`` (authoritative — the canonical
    training records were deliberately not ported).
    """
    from tau2.hyper.transformations import (
        get_transformation,
        resolve_section_transformations,
    )

    schema_paths = sorted((DST_ROOT / "sections").glob("*/schema.json"))
    assert schema_paths
    resolved_any = False
    for schema_path in schema_paths:
        schema = json.loads(schema_path.read_text())
        for spec in resolve_section_transformations(schema):
            transformation = get_transformation(spec["representation"])
            # Must not raise; explicit_rules legitimately discovers no
            # artifact files (its coverage is the section prose).
            artifacts = transformation.discover_artifacts(schema, schema_path, spec)
            for artifact in artifacts:
                assert artifact.source_path.exists(), (
                    f"{schema_path.parent.name}: {artifact.source_path}"
                )
            resolved_any = True
    assert resolved_any


def test_hyper_tree_entities_ground_or_are_declared_synthetic(plus_db):
    """Every #W order token and user-id-shaped token anywhere in the
    retail_plus hyper tree grounds in the plus db or is declared in some
    eval manifest's ``synthetic_entities`` block.

    Undeclared invented entities are indistinguishable from porting
    accidents (the domain-task audit found exactly such accidents:
    hash-stripped canonical ids that grounded nowhere), so inventions must
    be declared where a machine can check them.
    """
    orders = set(plus_db["orders"])
    users = set(plus_db["users"])

    declared_orders: set[str] = set()
    declared_users: set[str] = set()
    for manifest_path in sorted(DST_ROOT.rglob("eval_manifest.json")):
        declared = json.loads(manifest_path.read_text()).get("synthetic_entities")
        if declared:
            declared_orders.update(declared.get("order_ids", []))
            declared_users.update(declared.get("user_ids", []))

    order_re = re.compile(r"#W\d{7}\b")
    user_re = re.compile(r"\b[a-z]+_[a-z]+_\d{4}\b")
    problems = []
    for path in sorted(DST_ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in {
            ".md",
            ".html",
            ".txt",
            ".json",
            ".py",
            ".eml",
            ".cjs",
            ".mjs",
            ".css",
        }:
            continue
        text = path.read_text()
        rel = path.relative_to(DST_ROOT)
        for token in set(order_re.findall(text)):
            if token not in orders and token not in declared_orders:
                problems.append(f"{rel}: undeclared order {token}")
        for token in set(user_re.findall(text)):
            if token not in users and token not in declared_users:
                problems.append(f"{rel}: undeclared user {token}")
    assert not problems, "\n".join(sorted(problems))


def test_no_canonical_values_survive():
    """No canonical retail phrase or identifier survives in the committed tree.

    The phrase list and the canonical identifier universe are pinned in
    tests/plus_support/retail_plus.py (the identifiers are read off the
    committed canonical db, whose ids are exactly what the port had to
    rewrite).
    """
    text_files = [
        path
        for path in sorted(DST_ROOT.rglob("*"))
        if path.is_file()
        # Text formats only — binaries (.png, .pdf, .m4a) can't carry
        # readable canonical values and break read_text().
        and path.suffix
        in {
            ".md",
            ".html",
            ".txt",
            ".json",
            ".py",
            ".eml",
            ".cjs",
            ".mjs",
            ".css",
            ".vtt",
            ".csv",
        }
        and "__pycache__" not in path.parts
        # The provenance pin is sha256 hex + tree-relative paths; hex digit
        # runs collide with numeric identifier bans (e.g. canonical zips).
        and path.name != "render_provenance.json"
    ]
    assert text_files
    identifier_patterns = expectations.artifact_forbidden_identifier_patterns()
    assert expectations.ARTIFACT_FORBIDDEN_PHRASES
    assert len(identifier_patterns) > 1000, (
        f"canonical identifier scan collapsed to {len(identifier_patterns)} patterns"
    )
    scan_leakage(text_files, list(expectations.ARTIFACT_FORBIDDEN_PHRASES))
    scan_leakage(text_files, identifier_patterns, label="Canonical identifier")


def test_photo_bindings_resolve_by_option_combination(plus_db):
    """Each product photo depicts one option combination; the plus binding
    must land on the (deranged) item id that carries those options.

    The derangement reuses canonical item-id strings with different meanings,
    so a binding that kept its canonical id would silently point at the wrong
    variant. The canonical side is read off the committed canonical retail db
    (the canonical storefront is not part of this release)."""
    canonical_db = json.loads((expectations.CANONICAL_DIR / "db.json").read_text())
    plus = json.loads((STOREFRONT / "site_data.json").read_text())
    plus_bindings = plus["catalog"]["image_variants"]
    assert len(plus_bindings) == 50

    plus_products = {p["name"]: p for p in plus["catalog"]["products"]}
    db_products = {p["name"]: p for p in plus_db["products"].values()}
    canonical_products = {p["name"]: p for p in canonical_db["products"].values()}
    assert set(plus_bindings) <= set(canonical_products)
    for name, plus_variant in plus_bindings.items():
        db_variant = db_products[name]["variants"][plus_variant["item_id"]]
        assert db_variant["options"] == plus_variant["options"], name
        assert db_variant["price"] == plus_variant["price"], name
        assert plus_products[name]["product_id"] == db_products[name]["product_id"]
        # The derangement is fixed-point free: the canonical variant carrying
        # the same depicted options must sit under a different item id.
        canonical_ids = {
            item_id
            for item_id, variant in canonical_products[name]["variants"].items()
            if variant["options"] == plus_variant["options"]
        }
        assert canonical_ids, name
        assert plus_variant["item_id"] not in canonical_ids, name


def test_site_map_order_routes_ground_in_the_plus_db(plus_db):
    """The account order routes carry hash-stripped order ids
    (/account/orders/W...), a form any '#W'-keyed token scan misses and which
    therefore needs its own gate. The routes must name exactly the featured
    account's plus orders."""
    account_orders = {
        order_id.removeprefix("#")
        for order_id in json.loads((STOREFRONT / "site_data.json").read_text())[
            "account"
        ]["user"]["orders"]
    }
    for name in ("site_map.json", "eval_manifest.json"):
        text = (STOREFRONT / name).read_text()
        bare = set(re.findall(r"/account/orders/(W\d{7})", text))
        assert bare == account_orders, name
        for token in bare:
            assert f"#{token}" in plus_db["orders"], (name, token)


def test_all_schema_artifact_references_exist():
    data_dir = REPO_ROOT / "data"
    for schema_path in sorted(DST_ROOT.glob("sections/*/schema.json")):
        schema = json.loads(schema_path.read_text())
        for spec in schema.get("transformations") or []:
            for artifact in spec.get("artifacts") or []:
                for key in (
                    "path",
                    "text_source_path",
                    "author_source_path",
                    "generation_source_path",
                ):
                    if key in artifact:
                        assert (data_dir / artifact[key]).is_file(), (
                            f"{schema_path.name}: {artifact[key]}"
                        )
            if "eval_manifest_path" in spec:
                assert (data_dir / spec["eval_manifest_path"]).is_file()
            if "stub_path" in spec:
                assert (data_dir / spec["stub_path"]).is_file()


def test_call_audio_renditions_complete():
    """Every phone-call support transcript has a committed audio rendition
    (recordings/<case>.m4a) and every rendition has a phone-call source.

    All-or-nothing per tree: if only some phone-call cases carried audio,
    the rendition set itself would mark which records matter. Chat-channel
    cases never render, and their renditions are as much drift as missing
    ones. Byte-level integrity is the provenance pin's job; this gate owns
    the mapping.
    """
    phone_re = re.compile(r"^Channel:\s*phone call\s*$", re.MULTILINE)
    case_paths = [
        path
        for path in sorted(DST_ROOT.rglob("case_*.md"))
        if ".claude" not in path.parts
    ]
    assert case_paths
    problems = []
    for case_path in case_paths:
        rendition = case_path.parent / "recordings" / (case_path.stem + ".m4a")
        if phone_re.search(case_path.read_text()):
            if not rendition.exists():
                problems.append(f"missing rendition: {rendition.relative_to(DST_ROOT)}")
        elif rendition.exists():
            problems.append(
                f"rendition for non-phone-call case: {rendition.relative_to(DST_ROOT)}"
            )
    for m4a in sorted(DST_ROOT.rglob("recordings/*.m4a")):
        if not (m4a.parent.parent / (m4a.stem + ".md")).exists():
            problems.append(f"orphaned rendition: {m4a.relative_to(DST_ROOT)}")
    assert not problems, "\n".join(problems)
