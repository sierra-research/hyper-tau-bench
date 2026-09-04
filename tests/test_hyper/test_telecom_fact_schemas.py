"""Losslessness and ownership gates for the telecom fact decomposition."""

import json
import re
from datetime import datetime
from email import policy
from email.parser import BytesParser
from pathlib import Path
from statistics import median

import pytest
from PIL import Image

from tau2.hyper.task_loader import load_hyper_tau_tasks
from tau2.hyper.transformations import (
    compile_hyper_task,
    compile_variant_transformations,
    get_transformation,
)
from tau2.hyper.transformations.fact_hierarchy import resolve_domain_fact_hierarchy
from tau2.hyper.transformations.sop_variants import assemble_sop_variant

REPO_ROOT = Path(__file__).resolve().parents[2]
TELECOM_ROOT = REPO_ROOT / "data" / "tau2" / "hyper" / "sops" / "telecom"
CANONICAL_SOP = TELECOM_ROOT.parent / "telecom_sop.md"
COMPOSITE_VARIANT_PATH = TELECOM_ROOT / "variants/core_evidence_bundle_001.json"
COMPOSITE_VARIANT_RELATIVE_PATH = (
    "tau2/hyper/sops/telecom/variants/core_evidence_bundle_001.json"
)
HARD_VARIANT_RELATIVE_PATH = (
    "tau2/hyper/sops/telecom/variants/core_evidence_bundle_hard_001.json"
)
HARD_CLIENT_VARIANT_RELATIVE_PATH = (
    "tau2/hyper/sops/telecom/variants/core_evidence_bundle_hard_client_001.json"
)
COMPOSITE_TASK_ID = (
    "013_telecom_construction_core_evidence_seeded_all_defects_performance_medium"
)
VTT_CUE_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2}\.\d{3})\s+-->\s+"
    r"(?P<end>\d{2}:\d{2}:\d{2}\.\d{3})\n(?P<body>[^\n]+)"
)
ZOOM_SPEECH_MARKER_RE = re.compile(
    r"\b(?:yeah|yep|mm-hm|sorry|wait|actually|i mean|right|okay)\b|—|\.\.\.",
    re.IGNORECASE,
)
ZOOM_BANNED_LANGUAGE = {
    "retained as evidence",
    "standalone policy source",
    "construction artifact",
    "fact id",
    "later approved artifact controls",
    "model can reconstruct",
    "author-side manifest",
    "transcript generator",
    "checker will confirm",
    "evaluator annotations",
    "developer kit",
    "test-fixture",
    "test fixture",
    "good distractor",
    "only fact here",
    "only owner",
    "meeting owns",
    "owns only",
    "owns the three",
    "author manifest",
    "manifest timestamps",
    "private labels",
    "model should infer",
    "fact ownership",
    "re-owning",
}
SUPPORT_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[.’'-][A-Za-z0-9]+)*")
SUPPORT_PHONE_PHENOMENA = {
    "self_repair": re.compile(
        r"\b(?:actually|sorry|i mean|no, wait|wait)\b|—", re.IGNORECASE
    ),
    "backchannel": re.compile(
        r"\b(?:okay|got it|yeah|right|mm-hm|go ahead)\b", re.IGNORECASE
    ),
    "repeat_or_reframe": re.compile(
        r"\b(?:did you say|heard|catch that|repeat|say that|more clearly)\b",
        re.IGNORECASE,
    ),
    "pause_or_hold": re.compile(
        r"\b(?:give me a moment|take a moment|i'll wait|while i|i'm back)\b",
        re.IGNORECASE,
    ),
    "background_interruption": re.compile(r"\*\*Call event:\*\*"),
}

SHARED_SECTION_IDS = ("customer_identity", "service_foundations")
WORKFLOW_SECTION_IDS = (
    "resume_suspended_line",
    "refuel_data",
    "change_plan",
    "restore_data_abroad",
    "restore_service",
    "restore_mobile_data",
    "restore_mms",
)
SEMANTIC_SECTION_IDS = (*SHARED_SECTION_IDS, *WORKFLOW_SECTION_IDS)
RETIRED_TRANSCRIPT_SECTION_IDS = (
    "general_conduct",
    "customer_identity_line_access",
    "what_you_can_do",
    "overdue_bills_suspended_lines",
    "data_refueling",
    "roaming",
    "no_service_or_cannot_call",
    "unavailable_or_slow_mobile_data",
    "mms_picture_messaging",
)


def load_schemas() -> dict[str, dict]:
    return {
        section_id: json.loads(
            (TELECOM_ROOT / "sections" / section_id / "schema.json").read_text()
        )
        for section_id in SEMANTIC_SECTION_IDS
    }


def vtt_seconds(value: str) -> float:
    hours, minutes, remainder = value.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(remainder)


def support_duration_seconds(text: str, label: str) -> int:
    match = re.search(rf"(?m)^{re.escape(label)}: (\d+)m (\d+)s$", text)
    assert match is not None
    return int(match.group(1)) * 60 + int(match.group(2))


def test_catalog_is_shared_foundations_plus_workflows():
    schemas = load_schemas()
    assert set(schemas) == set(SEMANTIC_SECTION_IDS)
    assert schemas["customer_identity"]["domain_hierarchy"]["role"] == (
        "global_prerequisite"
    )
    assert schemas["service_foundations"]["domain_hierarchy"]["role"] == (
        "shared_reference"
    )
    assert all(
        schemas[section_id]["domain_hierarchy"]["role"] == "journey"
        for section_id in WORKFLOW_SECTION_IDS
    )
    for section_id in RETIRED_TRANSCRIPT_SECTION_IDS:
        assert not (TELECOM_ROOT / "sections" / section_id).exists()

    assert not (
        TELECOM_ROOT / "variants" / "core_sections_transcript_induction_001.json"
    ).exists()

    global_rules = json.loads((TELECOM_ROOT / "global_rules.json").read_text())
    global_rule_ids = {rule["id"] for rule in global_rules["rules"]}
    assert {
        "identify_customer_before_technical_support",
        "account_access_requires_documented_lookup",
        "deny_requests_against_policy",
    } <= global_rule_ids


def test_telecom_uses_only_composite_information_distribution_tasks_and_variants():
    """Telecom sanctions exactly three composites: the core evidence bundle,
    its hard sibling, and the client-knowledge overlay of the hard sibling.
    Section-specific variants and tasks stay banned; the hard variant must
    select the ``_hard_001`` sibling of every core bundle so the composites
    cover the same nine sections, and the client variant substitutes the
    ``_hard_client_001`` sibling for exactly its seven overlaid sections
    (the 2026-08-20 swap widened the overlay to restore_mms and
    restore_mobile_data; refuel_data and change_plan stay pass-through)."""
    variant_paths = sorted((TELECOM_ROOT / "variants").glob("*.json"))
    hard_variant_path = TELECOM_ROOT / "variants" / "core_evidence_bundle_hard_001.json"
    client_variant_path = (
        TELECOM_ROOT / "variants" / "core_evidence_bundle_hard_client_001.json"
    )
    assert variant_paths == [
        COMPOSITE_VARIANT_PATH,
        hard_variant_path,
        client_variant_path,
    ]

    core_section_bundles = {
        "service_foundations": "service_foundations_company_communications",
        "customer_identity": ("customer_identity_recording_communications_automation"),
        "resume_suspended_line": "resume_suspended_line_html_zoom_archive",
        "refuel_data": "refuel_data_recording_communications_automation",
        "change_plan": "change_plan_recording_communications_automation",
        "restore_data_abroad": "restore_data_abroad_jira_flowchart_archive",
        "restore_service": "restore_service_full_flowchart_recording",
        "restore_mobile_data": "restore_mobile_data_multisurface_archive",
        "restore_mms": "restore_mms_multihop_archive",
    }
    variant = json.loads(COMPOSITE_VARIANT_PATH.read_text())
    assert variant["section_bundles"] == core_section_bundles
    hard_variant = json.loads(hard_variant_path.read_text())
    assert hard_variant["section_bundles"] == {
        section: f"{bundle}_hard_001"
        for section, bundle in core_section_bundles.items()
    }
    client_overlaid_sections = {
        "service_foundations",
        "customer_identity",
        "resume_suspended_line",
        "restore_data_abroad",
        "restore_service",
        "restore_mms",
        "restore_mobile_data",
    }
    client_variant = json.loads(client_variant_path.read_text())
    assert client_variant["section_bundles"] == {
        section: (
            f"{bundle}_hard_client_001"
            if section in client_overlaid_sections
            else f"{bundle}_hard_001"
        )
        for section, bundle in core_section_bundles.items()
    }

    telecom_tasks = load_hyper_tau_tasks("telecom")
    manifest_by_task = {
        task.id: task.sop_variant_manifest_path for task in telecom_tasks
    }
    assert set(manifest_by_task.values()) == {
        COMPOSITE_VARIANT_RELATIVE_PATH,
        HARD_VARIANT_RELATIVE_PATH,
        HARD_CLIENT_VARIANT_RELATIVE_PATH,
    }
    assert manifest_by_task[COMPOSITE_TASK_ID] == COMPOSITE_VARIANT_RELATIVE_PATH

    client_tasks = [
        task
        for task in telecom_tasks
        if manifest_by_task[task.id] == HARD_CLIENT_VARIANT_RELATIVE_PATH
    ]
    assert client_tasks
    for task in client_tasks:
        assert sorted(task.client_sections) == sorted(client_overlaid_sections)
    compile_hyper_task(client_tasks[0].id).raise_on_errors()


def test_final_three_sections_use_recordings_communications_and_automation():
    schemas = load_schemas()
    expectations = {
        "customer_identity": {
            "bundle": "customer_identity_recording_communications_automation",
            "owner_counts": [4, 2, 3, 4],
            "duration": 56,
            "email_messages": [5, 4, 6],
            "support_fact_bearing": 2,
        },
        "change_plan": {
            "bundle": "change_plan_recording_communications_automation",
            "owner_counts": [1, 1, 2, 1],
            "duration": 58,
            "email_messages": [5, 4, 4],
            "support_fact_bearing": 1,
        },
        "refuel_data": {
            "bundle": "refuel_data_recording_communications_automation",
            "owner_counts": [3, 2, 3, 2],
            "duration": 58,
            "email_messages": [5, 4, 6],
            "support_fact_bearing": 2,
        },
    }

    for section_id, expected in expectations.items():
        section_root = TELECOM_ROOT / "sections" / section_id
        schema_path = section_root / "schema.json"
        schema = schemas[section_id]
        bundle = next(
            item
            for item in schema["transformation_bundles"]
            if item["id"] == expected["bundle"]
        )
        ownership = [
            fact_id
            for member in bundle["members"]
            for fact_id in member["authoritative_fact_ids"]
        ]
        assert [
            len(member["authoritative_fact_ids"]) for member in bundle["members"]
        ] == expected["owner_counts"]
        assert len(ownership) == len(set(ownership)) == len(schema["facts"])
        assert set(ownership) == {fact["id"] for fact in schema["facts"]}

        representations = {spec["representation"] for spec in schema["transformations"]}
        assert representations == {
            "explicit_rules",
            "interactive_screen_recording",
            "email_thread_archive",
            "support_transcripts",
            "helpdesk_automation_export",
        }
        assert "process_flowchart" not in representations
        assert "api_contract_pack" not in representations
        for spec in schema["transformations"]:
            if spec["representation"] == "explicit_rules":
                continue
            transformation = get_transformation(spec["representation"])
            artifacts = transformation.discover_artifacts(schema, schema_path, spec)
            assert transformation.validate(schema, artifacts) == []

        recording_spec = next(
            spec
            for spec in schema["transformations"]
            if spec["representation"] == "interactive_screen_recording"
        )
        recording = recording_spec["artifacts"][0]
        recording_path = REPO_ROOT / "data" / recording["path"]
        assert recording["duration_seconds"] == expected["duration"]
        assert recording_path.stat().st_size >= 250_000
        assert b"ftyp" in recording_path.read_bytes()[:32]
        recording_manifest = json.loads(
            (
                section_root
                / recording["eval_manifest_path"].split(f"/{section_id}/", 1)[1]
            ).read_text()
        )
        events = recording_manifest["artifacts"][0]["events"]
        assert {event["kind"] for event in events} >= {
            "authoritative",
            "distractor",
        }
        assert all(
            event.get("disposition") in {"failed", "rejected", "unrelated"}
            for event in events
            if event["kind"] == "distractor"
        )
        assert all(
            "&amp;#8230;" not in screen.read_text()
            for screen in (recording_path.parent / "screens").glob("*.html")
        )

        email_root = section_root / "email_thread_archive_001"
        email_manifest = json.loads((email_root / "eval_manifest.json").read_text())
        assert email_manifest["realism"]["message_counts"] == expected["email_messages"]
        assert min(email_manifest["realism"]["participant_counts"]) >= 3
        assert (
            sum(
                not thread["authoritative_fact_ids"]
                for thread in email_manifest["threads"]
            )
            == 2
        )
        assert all(
            b"Subject: RE: RE:" not in email_path.read_bytes()
            for email_path in email_root.glob("*.eml")
        )
        for thread, email_path in zip(
            email_manifest["threads"], sorted(email_root.glob("*.eml")), strict=True
        ):
            message = BytesParser(policy=policy.default).parsebytes(
                email_path.read_bytes()
            )
            references = str(message["References"]).split()
            assert message["In-Reply-To"]
            assert len(references) == thread["message_count"] - 1
            assert references[-1] == str(message["In-Reply-To"])
            quoted_ids = re.findall(
                r"^Message-ID:\s*(<[^>]+>)$",
                message.get_content(),
                flags=re.MULTILINE,
            )
            assert quoted_ids == list(reversed(references))

        support_manifest = json.loads(
            (section_root / "support_transcripts_001/eval_manifest.json").read_text()
        )
        assert support_manifest["case_count"] == 5
        assert (
            support_manifest["realism"]["fact_bearing_count"]
            == expected["support_fact_bearing"]
        )
        assert support_manifest["realism"]["distractor_count"] >= 3
        assert support_manifest["realism"]["word_counts"]["minimum"] >= 90

        helpdesk = json.loads(
            (
                section_root / "helpdesk_automation_export_001/authored_export.json"
            ).read_text()
        )
        assert helpdesk["snapshot"]["environment"] == "production"
        assert all(
            helpdesk[collection]
            for collection in (
                "macros",
                "triggers",
                "policy_contracts",
                "fields",
                "sla_policies",
                "views",
            )
        )
        automation_objects = [
            *helpdesk["macros"],
            *helpdesk["triggers"],
            *helpdesk["policy_contracts"],
        ]
        assert len(helpdesk["macros"]) >= 4
        assert len(helpdesk["triggers"]) >= 5
        assert len(helpdesk["policy_contracts"]) >= 3
        assert len(helpdesk["fields"]) >= 7
        assert any(
            item.get("environment") != "production" or item.get("active") is False
            for item in automation_objects
        )

        helpdesk_fact_map = json.loads(
            (section_root / "helpdesk_automation_export_001/fact_map.json").read_text()
        )
        helpdesk_manifest = json.loads(
            (
                section_root / "helpdesk_automation_export_001/eval_manifest.json"
            ).read_text()
        )
        cover_lower = helpdesk["cover_email"].lower()
        assert not any(
            phrase in cover_lower
            for phrase in (
                "current authority comes from",
                "usage is context only",
                "distinguish workflow authority",
            )
        )
        assert {
            evidence["fact_id"]: {
                key: value for key, value in evidence.items() if key != "fact_id"
            }
            for evidence in helpdesk_manifest["fact_evidence"]
        } == helpdesk_fact_map["facts"]
        authoritative_object_ids = {
            object_id
            for fact in helpdesk_fact_map["facts"].values()
            for object_id in fact["object_ids"]
        }
        neutral_automation = [
            item
            for item in [*helpdesk["macros"], *helpdesk["triggers"]]
            if next(
                str(item.get(key))
                for key in ("macro_id", "trigger_id")
                if item.get(key)
            )
            not in authoritative_object_ids
            and item.get("active") is True
            and item.get("environment") == "production"
            and item.get("status") == "published"
        ]
        assert any(item.get("usage_30d", 0) > 0 for item in neutral_automation)
        authoritative_sizes = [
            len(json.dumps(item, sort_keys=True))
            for item in automation_objects
            if next(
                str(item.get(key))
                for key in ("macro_id", "trigger_id", "contract_id")
                if item.get(key)
            )
            in authoritative_object_ids
        ]
        neutral_sizes = [
            len(json.dumps(item, sort_keys=True))
            for item in automation_objects
            if next(
                str(item.get(key))
                for key in ("macro_id", "trigger_id", "contract_id")
                if item.get(key)
            )
            not in authoritative_object_ids
            and item.get("active") is True
            and item.get("environment") == "production"
        ]
        assert max(neutral_sizes) >= median(authoritative_sizes)
        field_keys = {field["field_key"] for field in helpdesk["fields"]}
        current_references = {
            str(entry["field"])
            for collection in (helpdesk["triggers"], helpdesk["views"])
            for item in collection
            if item.get("active") is True
            and item.get("environment") == "production"
            and item.get("status", "published") == "published"
            for entry in (item.get("conditions") or item.get("filters") or [])
            if entry.get("field")
        }
        assert current_references <= field_keys
        object_files = {
            str(item[id_key]): filename
            for collection, id_key, filename in (
                ("macros", "macro_id", "macros.json"),
                ("triggers", "trigger_id", "triggers.json"),
                ("policy_contracts", "contract_id", "policy_contracts.json"),
                ("fields", "row_id", "fields.csv"),
                ("sla_policies", "policy_id", "sla_policies.json"),
                ("views", "view_id", "views.json"),
            )
            for item in helpdesk[collection]
        }
        for fact_evidence in helpdesk_fact_map["facts"].values():
            expected_files = list(
                dict.fromkeys(
                    object_files[object_id] for object_id in fact_evidence["object_ids"]
                )
            )
            assert fact_evidence["file"] == expected_files[0]
            if len(expected_files) > 1:
                assert fact_evidence["files"] == expected_files
            else:
                assert "files" not in fact_evidence

    variant = json.loads(COMPOSITE_VARIANT_PATH.read_text())
    assert set(variant["information_distribution"]["transformed_sections"]) == set(
        SEMANTIC_SECTION_IDS
    )
    assert variant["information_distribution"]["preserved_canonical_sections"] == []


def test_final_three_support_transcripts_pass_channel_realism_audit():
    all_cases = []
    for section_id in ("customer_identity", "change_plan", "refuel_data"):
        records_root = (
            TELECOM_ROOT / "sections" / section_id / "support_transcripts_001"
        )
        manifest = json.loads((records_root / "eval_manifest.json").read_text())
        schema = json.loads(
            (TELECOM_ROOT / "sections" / section_id / "schema.json").read_text()
        )
        bundle = next(
            item
            for item in schema["transformation_bundles"]
            if item["id"].endswith("recording_communications_automation")
        )
        support_member = next(
            member
            for member in bundle["members"]
            if member["transformation_id"].endswith("support_transcripts")
        )
        declared_dependencies = set(support_member["depends_on_fact_ids"])
        case_dependencies = {
            fact_id
            for case in manifest["cases"]
            for fact_id in case["depends_on_fact_ids"]
        }
        assert case_dependencies == declared_dependencies
        assert manifest["realism"]["channel_counts"] == {
            "Phone": 3,
            "Live chat": 2,
        }

        for case in manifest["cases"]:
            text = (records_root / case["filename"]).read_text()
            all_cases.append((case, text))
            assert "QA status: Approved" in text
            assert "## Transcript" in text
            assert "## QA review" not in text
            assert "Coaching note" not in text
            assert case["turn_count"] >= 12
            assert case["customer_turn_count"] >= 4
            assert case["agent_turn_count"] >= 4
            assert case["console_event_count"] >= 1
            assert not set(case["authoritative_fact_ids"]) & set(
                case["depends_on_fact_ids"]
            )
            assert set(case["depends_on_fact_ids"]) <= declared_dependencies
            assert case["word_count"] == len(text.replace("—", " ").split())
            assert len(case["realism_markers"]) >= 4

            agent_text = "\n".join(
                line for line in text.splitlines() if "**Agent:**" in line
            )
            assert not re.search(
                r"anything else|feel free to reach out|unfortunately|as an ai|"
                r"\b[a-z]+_[a-z0-9_]+\b|"
                r"\b(?:console|workspace|billing ledger|system returned)\b",
                agent_text,
                re.IGNORECASE,
            )

            if case["channel"] == "Phone":
                assert "Start time: 2026-08-" in text
                assert "Active handle time:" not in text
                assert "Chat span:" not in text
                relative_timestamps = [
                    int(minutes) * 60 + int(seconds)
                    for minutes, seconds in re.findall(
                        r"(?m)^\[(\d{2}):(\d{2})\]", text
                    )
                ]
                assert relative_timestamps == sorted(relative_timestamps)
                handle_seconds = support_duration_seconds(text, "Handle time")
                assert max(relative_timestamps) <= handle_seconds
                assert handle_seconds <= max(relative_timestamps) + 60

                spoken_turns = [
                    line
                    for line in text.splitlines()
                    if "**Customer:**" in line or "**Agent:**" in line
                ]
                spoken_text = "\n".join(spoken_turns)
                spoken_word_count = sum(
                    len(SUPPORT_WORD_RE.findall(line.split(":**", 1)[-1]))
                    for line in spoken_turns
                )
                words_per_minute = spoken_word_count / (handle_seconds / 60)
                assert 90 <= words_per_minute <= 145
                assert (
                    min(
                        len(SUPPORT_WORD_RE.findall(line.split(":**", 1)[-1]))
                        for line in spoken_turns
                    )
                    <= 8
                )
                observed = {
                    name
                    for name, pattern in SUPPORT_PHONE_PHENOMENA.items()
                    if pattern.search(
                        spoken_text if name != "background_interruption" else text
                    )
                }
                assert len(observed) >= 2
                assert (
                    text.count("**Console note:**") + text.count("**Call event:**") >= 2
                )
            else:
                assert "Channel: Live chat" in text
                assert "Chat opened: 2026-08-" in text
                assert "Active handle time:" in text
                assert "**Call event:**" not in text
                assert not re.search(r"\b(?:um|uh|mm-hm)\b", text, re.IGNORECASE)
                chat_timestamps = [
                    datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                    for value in re.findall(
                        r"(?m)^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) PT\]",
                        text,
                    )
                ]
                assert chat_timestamps == sorted(chat_timestamps)
                active_seconds = support_duration_seconds(text, "Active handle time")
                span_seconds = support_duration_seconds(text, "Chat span")
                assert 0 < active_seconds < span_seconds

                roles = re.findall(r"(?m)^\[[^]]+\] \*\*(Customer|Agent):\*\*", text)
                assert any(left == right for left, right in zip(roles, roles[1:]))
                typed_turns = [
                    line
                    for line in text.splitlines()
                    if "**Customer:**" in line or "**Agent:**" in line
                ]
                assert (
                    min(
                        len(SUPPORT_WORD_RE.findall(line.split(":**", 1)[-1]))
                        for line in typed_turns
                    )
                    <= 5
                )

    assert sum(case["channel"] == "Phone" for case, _ in all_cases) == 9
    assert sum(case["channel"] == "Live chat" for case, _ in all_cases) == 6

    word_counts = [case["word_count"] for case, _ in all_cases]
    median_words = median(word_counts)
    assert sum(count >= 1.75 * median_words for count in word_counts) >= 3
    assert sum(count >= 2.5 * median_words for count in word_counts) >= 1

    shortest = min(all_cases, key=lambda item: item[0]["word_count"])[0]
    longest = max(all_cases, key=lambda item: item[0]["word_count"])[0]
    assert not shortest["authoritative_fact_ids"]
    assert not longest["authoritative_fact_ids"]
    assert any(
        case["authoritative_fact_ids"] and case["word_count"] >= 1.75 * median_words
        for case, _ in all_cases
    )


def test_restore_data_abroad_jira_and_flowchart_bundle_is_lossless_and_realistic():
    schema = load_schemas()["restore_data_abroad"]
    schema_path = TELECOM_ROOT / "sections/restore_data_abroad/schema.json"
    bundle = next(
        item
        for item in schema["transformation_bundles"]
        if item["id"] == "restore_data_abroad_jira_flowchart_archive"
    )
    ownership = [
        fact_id
        for member in bundle["members"]
        for fact_id in member["authoritative_fact_ids"]
    ]
    assert len(ownership) == len(set(ownership)) == 13
    assert set(ownership) == {fact["id"] for fact in schema["facts"]}
    assert {
        member["transformation_id"]: len(member["authoritative_fact_ids"])
        for member in bundle["members"]
    } == {
        "telecom_restore_data_abroad_roaming_recovery_maps": 8,
        "telecom_restore_data_abroad_jira_decision_export": 5,
    }

    for spec in schema["transformations"]:
        if spec["representation"] == "explicit_rules":
            continue
        transformation = get_transformation(spec["representation"])
        artifacts = transformation.discover_artifacts(schema, schema_path, spec)
        assert transformation.validate(schema, artifacts) == []

    root = TELECOM_ROOT / "sections/restore_data_abroad"
    jira_dir = root / "jira_issue_export_001"
    export = json.loads((jira_dir / "jira_issue_export.json").read_text())
    manifest = json.loads((jira_dir / "eval_manifest.json").read_text())
    issues = export["issues"]
    issue_keys = {issue["key"] for issue in issues}
    assert len(issues) == 24
    assert sum(len(issue["fields"]["comment"]["comments"]) for issue in issues) >= 80
    assert sum(len(issue["changelog"]["histories"]) for issue in issues) >= 48
    assert len({issue["fields"]["status"]["name"] for issue in issues}) >= 7
    assert len({issue["fields"]["issuetype"]["name"] for issue in issues}) >= 7
    realism = manifest["realism_metrics"]
    assert realism["issue_count"] == 24
    assert realism["comment_count"] >= 80
    assert realism["changelog_count"] >= 48
    assert realism["issue_link_count"] >= 40
    assert realism["user_count"] >= 8
    assert 25 <= realism["comment_word_lengths"]["median"] <= 40
    assert realism["comment_word_lengths"]["maximum"] >= 35
    assert realism["description_word_lengths"]["minimum"] >= 65
    assert realism["description_word_lengths"]["median"] >= 80
    assert realism["comments_per_issue"] == {
        "minimum": 7,
        "median": 8,
        "maximum": 10,
    }
    assert {decision["issue_key"] for decision in manifest["decisions"]} == {
        "ROAM-248",
        "ROAM-251",
        "ROAM-264",
    }
    assert {decision["fact_id"] for decision in manifest["decisions"]} == set(
        next(
            member["authoritative_fact_ids"]
            for member in bundle["members"]
            if member["transformation_id"]
            == "telecom_restore_data_abroad_jira_decision_export"
        )
    )
    assert {item["issue_key"] for item in manifest["issue_adjudication"]} == issue_keys
    assert {
        "authoritative_current",
        "supporting_current",
        "superseded",
        "rejected",
        "distractor_current",
        "distractor_closed",
    } <= {item["role"] for item in manifest["issue_adjudication"]}

    snapshot = datetime.fromisoformat(export["exported_at"])
    for issue in issues:
        created = datetime.fromisoformat(issue["fields"]["created"])
        updated = datetime.fromisoformat(issue["fields"]["updated"])
        assert updated <= snapshot
        comment_dates = [
            datetime.fromisoformat(comment["created"])
            for comment in issue["fields"]["comment"]["comments"]
        ]
        assert comment_dates == sorted(comment_dates)
        assert created <= comment_dates[0] <= comment_dates[-1] <= updated
        assert len({comment_date.date() for comment_date in comment_dates}) >= 2
        assert all(
            datetime.fromisoformat(history["created"]) <= snapshot
            for history in issue["changelog"]["histories"]
        )
        assert {
            link["issueKey"] for link in issue["fields"]["issuelinks"]
        } <= issue_keys

    flow_dir = root / "process_flowchart_001_roaming_recovery"
    flow_manifest = json.loads((flow_dir / "eval_manifest.json").read_text())
    assert [
        len(artifact["authoritative_fact_ids"])
        for artifact in flow_manifest["artifacts"]
    ] == [5, 3]
    for artifact in flow_manifest["artifacts"]:
        with Image.open(flow_dir / artifact["raster"]) as image:
            assert image.size == (1760, 1280)
    referenced_issues = {
        edge["target"]
        for edge in flow_manifest["cross_references"]
        if edge["target"].startswith("ROAM-")
    }
    assert referenced_issues <= issue_keys

    compilation = compile_variant_transformations(
        json.loads(COMPOSITE_VARIANT_PATH.read_text())
    )
    assert compilation.errors == []
    assert compilation.warnings == []
    assert compilation.report()["totals"] == {
        "facts": 155,
        "covered": 155,
        "uncovered": 0,
        "multiply_represented": 0,
    }
    assert compilation.fallback_applies is False
    roaming_facts = [
        fact for fact in compilation.facts if fact.section_id == "restore_data_abroad"
    ]
    assert len(roaming_facts) == 13
    assert all(len(fact.representations) == 1 for fact in roaming_facts)

    assembled = assemble_sop_variant(COMPOSITE_VARIANT_RELATIVE_PATH)
    assert "exported work-item" in assembled
    assert "ROAM-*" in assembled
    assert "Roaming has two layers:" not in assembled
    assert "If carrier-side roaming is off" not in assembled


def test_semantic_sections_cover_every_canonical_policy_heading():
    schemas = load_schemas()
    covered_headings = set()
    for schema in schemas.values():
        source = schema["source_section"]
        covered_headings.add(source["heading"])
        covered_headings.update(source.get("component_headings", []))

    canonical_headings = set(
        re.findall(r"^## .+$", CANONICAL_SOP.read_text(), flags=re.MULTILINE)
    )
    assert covered_headings == canonical_headings


def test_facts_have_one_owner_and_one_policy_structure_assignment():
    schemas = load_schemas()
    domain_fact_ids = []
    for section_id, schema in schemas.items():
        facts = {fact["id"]: fact for fact in schema["facts"]}
        assert len(facts) == len(schema["facts"]), section_id
        domain_fact_ids.extend(facts)

        units = schema["policy_structure"]["units"]
        unit_ids = {unit["id"] for unit in units}
        assert len(unit_ids) == len(units), section_id
        assigned = [fact_id for unit in units for fact_id in unit["fact_ids"]]
        assert set(assigned) == set(facts), section_id
        assert len(assigned) == len(set(assigned)), section_id

        for relation in schema["policy_structure"]["relations"]:
            assert relation["source_id"] in unit_ids, (section_id, relation)
            assert relation["target_id"] in unit_ids, (section_id, relation)

    assert len(domain_fact_ids) == 155
    assert len(domain_fact_ids) == len(set(domain_fact_ids))


def test_hierarchy_is_valid_and_workflow_handoffs_match_policy():
    schemas = load_schemas()
    hierarchy = resolve_domain_fact_hierarchy(schemas)
    assert all(not item.validation_issues for item in hierarchy.values())

    for section_id in WORKFLOW_SECTION_IDS:
        required_sections = {
            requirement.section_id for requirement in hierarchy[section_id].requirements
        }
        assert {"customer_identity", "service_foundations"} <= required_sections
        assert (
            "customer_identity.identify_customer_before_technical_support"
            in hierarchy[section_id].inherited_fact_ids
        )

    workflow_dependencies = {
        section_id: {
            requirement.section_id
            for requirement in hierarchy[section_id].requirements
            if requirement.relationship == "workflow_handoff"
        }
        for section_id in WORKFLOW_SECTION_IDS
    }
    assert workflow_dependencies == {
        "resume_suspended_line": set(),
        "refuel_data": set(),
        "change_plan": set(),
        "restore_data_abroad": set(),
        "restore_service": {"resume_suspended_line"},
        "restore_mobile_data": {
            "restore_service",
            "restore_data_abroad",
            "refuel_data",
            "change_plan",
        },
        "restore_mms": {"restore_service", "restore_mobile_data"},
    }


def test_previously_lossy_rules_remain_explicit():
    schemas = load_schemas()
    statements = {
        fact["id"]: fact["statement"]
        for schema in schemas.values()
        for fact in schema["facts"]
    }

    required_fragments = {
        "identify_customer_before_technical_support": (
            "before beginning technical support",
        ),
        "entry_no_service_or_cannot_connect": (
            "cannot connect to the cellular network",
        ),
        "connected_status_not_a_no_service_issue": ("not facing a no-service issue",),
        "missing_sim_reseat_and_recheck": ("check that the SIM is active",),
        "transfer_triggers_out_of_scope_or_policy_step": (
            "cannot be handled within the scope",
        ),
        "deny_requests_against_policy": ("against the handbook's policy",),
        "no_subjective_recommendations_or_comments": ("subjective recommendations",),
        "multiple_issues_address_connectivity_first": ("basic connectivity first",),
        "dob_required_for_verification": ("for verification purposes",),
        "check_usage_against_plan_limit": (
            "still unavailable after the mobile-data setting check",
            "plan limit plus any previously refueled data",
        ),
        "on_2g_switch_to_at_least_3g_and_retry": ("at least 3G",),
        "can_show_available_plans_and_change_selected_plan": (
            "available plans",
            "new monthly price",
        ),
        "work_relevant_steps_before_technical_transfer": (
            "every relevant in-scope resolution step",
            "does not transfer merely to avoid troubleshooting",
        ),
        "speed_scale_by_network_generation": (
            "signal strength",
            "2G is very poor",
            "3G ranges from very poor to poor",
            "4G ranges from fair to good",
            "5G ranges from good to excellent",
        ),
        "verify_selected_bill_overdue_before_request": (
            "selected bill is Overdue",
            "does not perform that eligibility check",
        ),
        "only_one_awaiting_payment_request_at_a_time": (
            "only one bill in Awaiting Payment",
        ),
        "all_overdue_bills_paid_before_resume": (
            "all of the customer's overdue bills are paid",
        ),
        "resume_line_after_confirmation": (
            "After the customer confirms",
            "all overdue bills are paid",
            "resume the affected line",
        ),
        "total_refueled_data_may_not_exceed_two_gb": (
            "total amount refueled on a line",
            "already refueled",
            "above 2 GB",
        ),
        "explain_carrier_roaming_needed_when_off": ("at no cost",),
        "incorrect_apn_reset_reboot_recheck": (
            "If the APN settings are incorrect",
            "reset",
            "reboot",
            "recheck the status bar",
        ),
        "ended_contract_suspension_uses_suspended_line_handling": (
            "ended-contract handling",
            "suspended-line workflow",
        ),
        "unresolved_service_after_supported_steps_transfers": (
            "all relevant device-side checks",
            "no supported suspension flow restores service",
        ),
        "resolved_when_status_bar_connected": ("connected service on the status bar",),
        "exhausted_data_offer_plan_change_or_refuel": (
            "changing to a plan with more data",
            "data-refueling workflow",
        ),
        "rerun_speed_test_after_carrier_correction": (
            "plan change or data refuel",
            "rerun the speed test",
        ),
        "unavailable_after_carrier_correction_transfers": (
            "still unavailable after the selected carrier-side correction",
        ),
        "exhausted_data_without_supported_correction_transfers": (
            "declines both options",
            "required transfer message",
        ),
        "not_exhausted_rerun_speed_test": ("usage is not exhausted",),
        "not_exhausted_still_unavailable_transfers": (
            "usage is not exhausted",
            "required transfer message",
        ),
        "working_but_slow_returns_to_slow_data_steps": (
            "return to the slow-data steps",
        ),
        "unavailable_with_both_layers_on_returns_to_mobile_data_settings": (
            "both roaming layers are confirmed on",
            "mobile-data setting check",
        ),
        "slow_data_below_excellent_after_steps_transfers": (
            "all relevant slow-data steps",
            "still below excellent",
        ),
        "wifi_calling_blocking_disable_and_retry": (
            "if Wi-Fi Calling is on",
            "turn it off and retry MMS",
        ),
        "unresolved_mms_after_supported_steps_transfers": (
            "all relevant MMS troubleshooting steps",
            "MMS still fails",
        ),
        "gather_and_present_available_plans": ("relevant details",),
        "confirm_selected_plan_and_price": (
            "selected plan",
            "new monthly price",
        ),
        "apply_selected_plan_after_confirmation": (
            "only after",
            "confirmed",
        ),
    }
    for fact_id, fragments in required_fragments.items():
        statement = statements[fact_id]
        for fragment in fragments:
            assert fragment in statement, (fact_id, fragment, statement)

    retired_lossy_ids = {
        "max_refuel_two_gb_per_request",
        "exhausted_data_use_refuel_flow",
        "active_sim_no_service_reset_apn_reboot_recheck",
        "ended_contract_suspension_transfers",
        "broken_mms_apn_reset_reboot_retry",
    }
    assert retired_lossy_ids.isdisjoint(statements)

    retired_divergent_ids = {
        "entry_no_service_or_cannot_call",
        "connected_status_verify_calls_and_texts",
        "connected_but_calls_or_texts_fail_continue_diagnostics",
        "dob_required_because_names_not_unique",
        "transfer_triggers_person_out_of_handbook_or_policy_step",
        "on_2g_switch_to_4g_5g_and_retry",
    }
    assert retired_divergent_ids.isdisjoint(statements)


def test_restore_mms_linked_bundle_is_lossless_and_runnable():
    schemas = load_schemas()
    for section_id, schema in schemas.items():
        assert any(
            transformation["representation"] == "explicit_rules"
            for transformation in schema["transformations"]
        ), section_id

    restore_mms = schemas["restore_mms"]
    bundle = next(
        item
        for item in restore_mms["transformation_bundles"]
        if item["id"] == "restore_mms_multihop_archive"
    )
    member_ownership = [
        fact_id
        for member in bundle["members"]
        for fact_id in member["authoritative_fact_ids"]
    ]
    route_ownership = [
        fact_id
        for route in bundle["evidence_routes"]
        for fact_id in route["authoritative_fact_ids"]
    ]
    ownership = [*member_ownership, *route_ownership]
    assert len(member_ownership) == 7
    assert len(route_ownership) == 4
    assert len(ownership) == len(set(ownership)) == 11
    assert set(ownership) == {fact["id"] for fact in restore_mms["facts"]}
    assert {
        member["transformation_id"]: len(member["authoritative_fact_ids"])
        for member in bundle["members"]
    } == {
        "telecom_restore_mms_help_center_full_site": 5,
        "telecom_restore_mms_device_capture_selection": 0,
        "telecom_restore_mms_dense_slack_mcp_dump": 2,
    }
    assert all(len(route["hops"]) == 3 for route in bundle["evidence_routes"])
    assert all(
        [hop["artifact_ref"] for hop in route["hops"][:2]]
        == ["NW-MSG-1042", "NW-DEVICE-5044"]
        for route in bundle["evidence_routes"]
    )
    expected_route_screens = {
        "samsung_network_mode_2g_only",
        "iphone_wifi_calling_on",
        "samsung_messages_permissions_missing",
        "samsung_apn_mmsc_missing",
    }
    assert {
        route["hops"][2]["artifact_ref"] for route in bundle["evidence_routes"]
    } == expected_route_screens
    device_transformation = next(
        transformation
        for transformation in restore_mms["transformations"]
        if transformation["id"] == "telecom_restore_mms_device_capture_selection"
    )
    assert len(device_transformation["artifacts"]) == 20
    assert expected_route_screens <= {
        artifact["artifact_ref"] for artifact in device_transformation["artifacts"]
    }

    manifest = json.loads(COMPOSITE_VARIANT_PATH.read_text())
    compilation = compile_variant_transformations(manifest)
    assert compilation.errors == []
    assert compilation.warnings == []
    assert compilation.report()["totals"] == {
        "facts": 155,
        "covered": 155,
        "uncovered": 0,
        "multiply_represented": 0,
    }
    assert compilation.fallback_applies is False

    assembled = assemble_sop_variant(COMPOSITE_VARIANT_RELATIVE_PATH)
    assert "distributed across the uploaded" in assembled
    assert assembled.count("Follow citations between those sources") == 1
    assert "## MMS Picture Messaging" in assembled
    assert "If the MMSC URL is missing or incorrect" not in assembled


def test_telecom_device_archive_is_dense_unique_and_explicitly_selected():
    archive_dir = TELECOM_ROOT / "shared" / "device_capture_archive_001"
    catalog = json.loads((archive_dir / "catalog.json").read_text())
    manifest = json.loads((archive_dir / "eval_manifest.json").read_text())
    artifacts = catalog["artifacts"]
    artifact_ids = [artifact["id"] for artifact in artifacts]

    assert catalog["artifact_count"] == manifest["artifact_count"] == 36
    assert catalog["platforms"] == {"iphone": 16, "samsung": 20}
    assert len(artifact_ids) == len(set(artifact_ids)) == 36
    assert len({artifact["visible_state_signature"] for artifact in artifacts}) == 36
    assert (
        len(
            {
                (archive_dir / artifact["filename"]).read_bytes()
                for artifact in artifacts
            }
        )
        == 36
    )

    for artifact in artifacts:
        assert (archive_dir / artifact["filename"]).is_file()
        assert (archive_dir / artifact["source"]).is_file()
        assert set(artifact["consumers"]) <= {"restore_mms", "restore_mobile_data"}
        if artifact["density"] == "standard":
            assert artifact["row_count"] >= 5
            assert artifact["sparse_reason"] is None
        else:
            assert artifact["sparse_reason"]

    selections = catalog["workflow_selections"]
    assert set(selections) == {"restore_mms", "restore_mobile_data"}
    mms_ids = selections["restore_mms"]["screen_ids"]
    mobile_ids = selections["restore_mobile_data"]["screen_ids"]
    assert len(mms_ids) == len(set(mms_ids)) == 20
    assert len(mobile_ids) == len(set(mobile_ids)) == 20
    assert set(mms_ids) | set(mobile_ids) <= set(artifact_ids)
    assert (
        set(mms_ids) & set(mobile_ids)
        == set(selections["restore_mms"]["shared_context"])
        == set(selections["restore_mobile_data"]["shared_context"])
    )
    assert len(set(mms_ids) & set(mobile_ids)) == 4
    assert manifest["distribution"] == {
        "canonical_screens": 36,
        "restore_mms_selected": 20,
        "restore_mobile_data_selected": 20,
        "shared_between_initial_consumers": 4,
        "required_route_hops": 8,
        "facts_supported_by_routes": 9,
    }


def test_restore_mobile_data_bundle_is_lossless_and_runnable():
    mobile_data = load_schemas()["restore_mobile_data"]
    bundle = next(
        item
        for item in mobile_data["transformation_bundles"]
        if item["id"] == "restore_mobile_data_multisurface_archive"
    )
    member_ownership = [
        fact_id
        for member in bundle["members"]
        for fact_id in member["authoritative_fact_ids"]
    ]
    route_ownership = [
        fact_id
        for route in bundle["evidence_routes"]
        for fact_id in route["authoritative_fact_ids"]
    ]
    ownership = [*member_ownership, *route_ownership]
    assert len(member_ownership) == 13
    assert len(route_ownership) == 5
    assert len(ownership) == len(set(ownership)) == 18
    assert set(ownership) == {fact["id"] for fact in mobile_data["facts"]}
    assert {
        member["transformation_id"]: len(member["authoritative_fact_ids"])
        for member in bundle["members"]
    } == {
        "telecom_restore_mobile_data_web_surfaces": 7,
        "telecom_restore_mobile_data_device_capture_selection": 0,
        "telecom_restore_mobile_data_email_archive": 4,
        "telecom_restore_mobile_data_scoped_routing_chart": 2,
    }
    assert len(bundle["evidence_routes"]) == 4
    assert all(len(route["hops"]) == 3 for route in bundle["evidence_routes"])
    assert all(
        [hop["artifact_ref"] for hop in route["hops"][:2]]
        == ["NW-DATA-2101", "NW-DEVICE-5088"]
        for route in bundle["evidence_routes"]
    )
    expected_route_screens = {
        "samsung_mobile_data_off",
        "iphone_low_data_mode",
        "samsung_network_mode_3g_2g",
        "iphone_vpn_connected",
    }
    assert {
        route["hops"][2]["artifact_ref"] for route in bundle["evidence_routes"]
    } == expected_route_screens
    device_transformation = next(
        transformation
        for transformation in mobile_data["transformations"]
        if transformation["id"]
        == "telecom_restore_mobile_data_device_capture_selection"
    )
    assert len(device_transformation["artifacts"]) == 20
    assert expected_route_screens <= {
        artifact["artifact_ref"] for artifact in device_transformation["artifacts"]
    }

    manifest = json.loads(COMPOSITE_VARIANT_PATH.read_text())
    compilation = compile_variant_transformations(manifest)
    assert compilation.errors == []
    assert compilation.warnings == []
    assert compilation.report()["totals"] == {
        "facts": 155,
        "covered": 155,
        "uncovered": 0,
        "multiply_represented": 0,
    }
    assert compilation.fallback_applies is False

    assembled = assemble_sop_variant(COMPOSITE_VARIANT_RELATIVE_PATH)
    assert assembled.count("distributed across the uploaded Northline") == 1
    assert assembled.count("Follow natural links") == 1
    assert "## Unavailable Or Slow Mobile Data" in assembled
    assert "If usage is exhausted, offer" not in assembled


def test_restore_mobile_data_routes_and_distractors_are_scoped():
    artifact_root = TELECOM_ROOT / "sections" / "restore_mobile_data"
    web_dir = artifact_root / "web_surfaces_001_dense"
    device_dir = TELECOM_ROOT / "shared" / "device_capture_archive_001"
    email_dir = artifact_root / "email_thread_archive_001_dense"
    flow_dir = artifact_root / "process_flowchart_002_scoped_routing"

    web_manifest = json.loads((web_dir / "eval_manifest.json").read_text())
    assert web_manifest["artifact_count"] == 34
    assert web_manifest["surface_distribution"] == {
        "public_help_center": 24,
        "signed_in_support_console": 10,
    }
    assert web_manifest["grounded_distractors"]["help_pages"] == 22
    assert web_manifest["grounded_distractors"]["console_views"] == 7
    web_facts = [
        fact_id
        for artifact in web_manifest["artifacts"]
        for fact_id in artifact["authoritative_fact_ids"]
    ]
    assert len(web_facts) == len(set(web_facts)) == 7

    hub_html = (web_dir / "help-fix-unavailable-or-slow-mobile-data.html").read_text()
    guide_html = (web_dir / "help-find-mobile-data-settings.html").read_text()
    assert "NW-DEVICE-5088" in hub_html
    assert "device_capture_" not in hub_html
    assert guide_html.count("Enlarge image") == 4
    for number in range(5, 9):
        filename = f"device_capture_{number:03d}.png"
        assert filename in guide_html
        assert (device_dir / filename).is_file()
        assert f"../../../shared/device_capture_archive_001/{filename}" in guide_html

    for source_name, visible_state in {
        "device_capture_005.html": (
            '<span class="label">Mobile data</span><span class="toggle">',
        ),
        "device_capture_006.html": ("Low Data Mode",),
        "device_capture_007.html": ("3G/2G (auto connect)", "Selected"),
        "device_capture_008.html": ("VPN", "Connected"),
    }.items():
        source = (device_dir / source_name).read_text()
        assert all(fragment in source for fragment in visible_state)

    email_manifest = json.loads((email_dir / "eval_manifest.json").read_text())
    assert email_manifest["thread_count"] == 24
    assert email_manifest["distribution"]["fact_bearing_current"] == 4
    assert email_manifest["distribution"]["superseded_history"] == 4
    assert email_manifest["distribution"]["distractor_only"] == 16
    assert email_manifest["distribution"]["minimum_messages_per_thread"] == 4
    assert email_manifest["distribution"]["maximum_messages_per_thread"] == 10
    assert len(email_manifest["distribution"]["distinct_message_counts"]) >= 6
    for events in email_manifest["scope_change_histories"].values():
        assert [event["status"] for event in events] == [
            "superseded",
            "final_current",
        ]

    archive_texts = []
    for thread in email_manifest["threads"]:
        message = BytesParser(policy=policy.default).parsebytes(
            (email_dir / thread["filename"]).read_bytes()
        )
        assert all(
            message.get(header)
            for header in (
                "From",
                "To",
                "Date",
                "Subject",
                "Message-ID",
                "MIME-Version",
                "Thread-Topic",
                "Thread-Index",
            )
        )
        body = message.get_body(preferencelist=("plain",))
        text = str(body.get_content() if body is not None else message.get_payload())
        assert text.count("-----Original Message-----") >= 3
        archive_texts.append(text)
    archive_text = "\n".join(archive_texts)
    evidence_phrases = [
        phrase
        for thread in email_manifest["threads"]
        for field in ("evidence_phrases", "historical_evidence_phrases")
        for phrase in thread[field].values()
    ]
    assert all(archive_text.count(phrase) == 1 for phrase in evidence_phrases)

    flow_text = (flow_dir / "mobile_data_quick_route.txt").read_text()
    assert "use Restore cellular service first" in flow_text
    assert "use Restore data while abroad" in flow_text
    assert "owns only the no-service and abroad handoffs" in flow_text
    assert not (artifact_root / "device_ui_screenshot_001_raw_archive").exists()
    assert not (artifact_root / "helpdesk_automation_export_001").exists()
    assert not (artifact_root / "process_flowchart_001").exists()


@pytest.mark.parametrize(
    ("fixture", "transformation_id", "duration", "distractor_count"),
    [
        (
            "clean",
            "telecom_restore_service_apn_recording_clean",
            30,
            0,
        ),
        (
            "controlled_distractors",
            "telecom_restore_service_apn_recording_controlled_distractors",
            50,
            3,
        ),
    ],
)
def test_restore_service_apn_recordings_are_paired_and_auditable(
    fixture, transformation_id, duration, distractor_count
):
    schema_path = TELECOM_ROOT / "sections/restore_service/schema.json"
    schema = json.loads(schema_path.read_text())
    spec = next(
        item for item in schema["transformations"] if item["id"] == transformation_id
    )
    transformation = get_transformation(spec["representation"])
    artifacts = transformation.discover_artifacts(schema, schema_path, spec)
    assert transformation.validate(schema, artifacts) == []
    assert len(artifacts) == 1

    artifact_dir = (
        TELECOM_ROOT
        / "sections/restore_service/interactive_screen_recording_001_apn_recovery"
    )
    eval_manifest = json.loads((artifact_dir / "eval_manifest.json").read_text())
    entry = next(
        item for item in eval_manifest["artifacts"] if fixture in item["filename"]
    )
    assert entry["duration_seconds"] == duration
    assert sum(event["kind"] == "distractor" for event in entry["events"]) == (
        distractor_count
    )
    video = artifact_dir / entry["filename"]
    assert b"ftyp" in video.read_bytes()[:32]


def test_restore_service_full_flowchart_bundle_is_lossless_and_buildable():
    restore_service = load_schemas()["restore_service"]
    bundle = next(
        item
        for item in restore_service["transformation_bundles"]
        if item["id"] == "restore_service_full_flowchart_recording"
    )
    ownership = [
        fact_id
        for member in bundle["members"]
        for fact_id in member["authoritative_fact_ids"]
    ]
    assert len(ownership) == len(set(ownership)) == 15
    assert set(ownership) == {fact["id"] for fact in restore_service["facts"]}
    assert {
        member["transformation_id"]: len(member["authoritative_fact_ids"])
        for member in bundle["members"]
    } == {
        "telecom_restore_service_full_journey_flowchart": 12,
        "telecom_restore_service_apn_recording_controlled_distractors": 3,
    }

    flow_dir = (
        TELECOM_ROOT / "sections/restore_service/process_flowchart_001_full_journey"
    )
    flow_manifest = json.loads((flow_dir / "eval_manifest.json").read_text())
    artifacts = flow_manifest["artifacts"]
    assert flow_manifest["artifact_count"] == len(artifacts) == 3
    assert [len(artifact["authoritative_fact_ids"]) for artifact in artifacts] == [
        5,
        3,
        4,
    ]
    flow_ownership = [
        fact_id
        for artifact in artifacts
        for fact_id in artifact["authoritative_fact_ids"]
    ]
    assert len(flow_ownership) == len(set(flow_ownership)) == 12
    for artifact in artifacts:
        assert (artifact["width"], artifact["height"]) == (1760, 1280)
        png = (flow_dir / artifact["raster"]).read_bytes()
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        assert (
            int.from_bytes(png[16:20], "big"),
            int.from_bytes(png[20:24], "big"),
        ) == (1760, 1280)

    manifest = json.loads(COMPOSITE_VARIANT_PATH.read_text())
    assert manifest["uncovered_fact_policy"] == "error"
    compilation = compile_variant_transformations(manifest)
    assert compilation.errors == []
    assert compilation.warnings == []
    assert compilation.report()["totals"] == {
        "facts": 155,
        "covered": 155,
        "uncovered": 0,
        "multiply_represented": 0,
    }
    assert compilation.fallback_applies is False

    sop = assemble_sop_variant(COMPOSITE_VARIANT_RELATIVE_PATH)
    assert "Read Charts 1, 2, and 3 at full resolution" in sop
    assert "uncovered source facts" not in sop


def test_telecom_zoom_meetings_follow_realism_standard():
    service_root = (
        TELECOM_ROOT / "sections/service_foundations/company_communications_001"
    )
    resume_root = (
        TELECOM_ROOT / "sections/resume_suspended_line/recorded_working_session_001"
    )
    sources = [
        (
            service_root / "meetings",
            json.loads((service_root / "meeting_manifest.json").read_text()),
        ),
        (resume_root, json.loads((resume_root / "eval_manifest.json").read_text())),
    ]

    durations = []
    participant_counts = []
    meeting_count = 0
    for transcript_root, manifest in sources:
        for meeting in manifest["meetings"]:
            meeting_count += 1
            transcript = (transcript_root / meeting["filename"]).read_text()
            cues = list(VTT_CUE_RE.finditer(transcript))
            assert len(cues) >= 40
            spoken_cues = []
            stage_cues = 0
            for cue in cues:
                cue_duration = vtt_seconds(cue["end"]) - vtt_seconds(cue["start"])
                speaker_match = re.match(r"<v ([^>]+)>(.*)$", cue["body"])
                if speaker_match is None:
                    stage_cues += 1
                    continue
                utterance = speaker_match.group(2)
                word_count = len(re.findall(r"\b[\w’'-]+\b", utterance))
                spoken_cues.append(
                    (speaker_match.group(1), utterance, word_count, cue_duration)
                )
                assert cue_duration <= 15.01
                assert cue_duration <= max(3.0, word_count / 1.15 + 1.5) + 0.01

            duration = (
                vtt_seconds(cues[-1]["end"]) - vtt_seconds(cues[0]["start"])
            ) / 60
            word_count = sum(cue[2] for cue in spoken_cues)
            speakers = {cue[0] for cue in spoken_cues}
            assert 25 <= duration <= 40
            assert 90 <= word_count / duration <= 145
            assert speakers == set(meeting["participants"])
            assert sum(cue[2] <= 4 for cue in spoken_cues) >= 4
            assert stage_cues >= 2
            assert (
                sum(bool(ZOOM_SPEECH_MARKER_RE.search(cue[1])) for cue in spoken_cues)
                >= 4
            )
            assert (
                sum(
                    first[0] != second[0]
                    for first, second in zip(spoken_cues, spoken_cues[1:])
                )
                >= 30
            )
            lowered = transcript.lower()
            assert not any(phrase in lowered for phrase in ZOOM_BANNED_LANGUAGE)
            durations.append(round(duration, 1))
            participant_counts.append(len(speakers))

    assert meeting_count == 18
    assert len(set(durations)) >= 10
    assert len(set(participant_counts)) >= 5


def test_resume_suspended_line_html_zoom_bundle_is_lossless_and_buildable():
    schema_path = TELECOM_ROOT / "sections/resume_suspended_line/schema.json"
    resume_schema = json.loads(schema_path.read_text())
    bundle = next(
        item
        for item in resume_schema["transformation_bundles"]
        if item["id"] == "resume_suspended_line_html_zoom_archive"
    )
    ownership = [
        fact_id
        for member in bundle["members"]
        for fact_id in member["authoritative_fact_ids"]
    ]
    assert len(ownership) == len(set(ownership)) == 19
    assert set(ownership) == {fact["id"] for fact in resume_schema["facts"]}
    assert {
        member["transformation_id"]: len(member["authoritative_fact_ids"])
        for member in bundle["members"]
    } == {
        "telecom_resume_suspended_line_html_knowledge_archive": 14,
        "telecom_resume_suspended_line_launch_scope_review": 5,
    }

    transformations = {item["id"]: item for item in resume_schema["transformations"]}
    for transformation_id in (
        "telecom_resume_suspended_line_html_knowledge_archive",
        "telecom_resume_suspended_line_launch_scope_review",
    ):
        spec = transformations[transformation_id]
        transformation = get_transformation(spec["representation"])
        artifacts = transformation.discover_artifacts(resume_schema, schema_path, spec)
        assert transformation.validate(resume_schema, artifacts) == []

    html_dir = (
        TELECOM_ROOT / "sections/resume_suspended_line/knowledge_base_html_export_001"
    )
    html_manifest = json.loads((html_dir / "eval_manifest.json").read_text())
    assert len(html_manifest["articles"]) == 38
    assert (
        sum(
            not article["authoritative_fact_ids"]
            for article in html_manifest["articles"]
        )
        == 34
    )
    assert len(html_manifest["authoritative_fact_ids"]) == 14
    html_text = (html_dir / html_manifest["filename"]).read_text()
    assert html_text.lower().startswith("<!doctype html>")
    assert html_text.count('data-article-id="') == 38
    assert not re.search(r'(?:src|href)="(?:https?:)?//', html_text)

    meeting_dir = (
        TELECOM_ROOT / "sections/resume_suspended_line/recorded_working_session_001"
    )
    meeting_manifest = json.loads((meeting_dir / "eval_manifest.json").read_text())
    final_decisions = [
        decision
        for decision in meeting_manifest["decisions"]
        if decision["status"] == "final_current"
    ]
    assert len(final_decisions) == 5
    assert all(decision["evidence_spans"] for decision in final_decisions)
    assert len(meeting_manifest["meetings"]) == 3
    assert [
        len(meeting["authoritative_fact_ids"])
        for meeting in meeting_manifest["meetings"]
    ] == [1, 3, 1]
    meeting_bytes = set()
    for meeting in meeting_manifest["meetings"]:
        transcript_path = meeting_dir / meeting["filename"]
        transcript = transcript_path.read_text()
        assert transcript.startswith("WEBVTT")
        assert set(re.findall(r"(?m)^<v ([^>]+)>", transcript)) == set(
            meeting["participants"]
        )
        assert meeting["title"] in transcript
        assert not any(fact_id in transcript for fact_id in ownership)
        meeting_bytes.add(transcript_path.read_bytes())

    variant = json.loads(COMPOSITE_VARIANT_PATH.read_text())
    assert variant["uncovered_fact_policy"] == "error"
    compilation = compile_variant_transformations(variant)
    assert compilation.errors == []
    assert compilation.warnings == []
    assert compilation.report()["totals"] == {
        "facts": 155,
        "covered": 155,
        "uncovered": 0,
        "multiply_represented": 0,
    }
    assert compilation.fallback_applies is False

    assert len(meeting_bytes) == 3
    sop = assemble_sop_variant(COMPOSITE_VARIANT_RELATIVE_PATH)
    assert "three dated working-session transcripts" in sop
    assert "uncovered source facts" not in sop
