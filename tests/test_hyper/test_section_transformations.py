"""Tests for the section-transformation registry and built-in transformations."""

import io
import json
import zipfile
from pathlib import Path

import pytest

import tau2.hyper.transformations.email_threads as email_threads_module
from tau2.hyper.sandbox.kit import (
    _copy_sop_variant_materials,
    _pool_uploaded_material_names,
)
from tau2.hyper.transformations import (
    TransformationArtifact,
    get_transformation,
    has_transformation,
    known_representations,
    resolve_section_transformations,
    select_section_transformation,
)
from tau2.hyper.transformations.api_contract_pack import build_api_contract_zip
from tau2.hyper.transformations.bundles import resolve_transformation_bundles
from tau2.hyper.transformations.helpdesk_automation_export import (
    build_helpdesk_export_zip,
)
from tau2.hyper.transformations.modality import parse_modality_profile

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_builtin_representations_are_registered():
    assert known_representations() == [
        "api_contract_pack",
        "case_ledger_export",
        "client_knowledge",
        "contact_center_qa_export",
        "customer_kickoff_document",
        "device_ui_screenshot",
        "email_thread_archive",
        "explicit_rules",
        "helpdesk_automation_export",
        "interactive_screen_recording",
        "jira_issue_export",
        "knowledge_base_html_export",
        "process_flowchart",
        "process_presentation",
        "recorded_working_session",
        "reference_document",
        "slack_mcp_dump",
        "support_transcripts",
        "website_screenshot",
    ]


def test_aliases_resolve_to_canonical_transformations():
    assert get_transformation("example_transcripts") is get_transformation(
        "support_transcripts"
    )
    assert get_transformation("sop_prose") is get_transformation("explicit_rules")
    assert get_transformation("helpdesk_export") is get_transformation(
        "helpdesk_automation_export"
    )
    assert get_transformation("openapi_contract_pack") is get_transformation(
        "api_contract_pack"
    )
    assert get_transformation("qa_review_export") is get_transformation(
        "contact_center_qa_export"
    )
    assert get_transformation("customer_document") is get_transformation(
        "customer_kickoff_document"
    )
    assert get_transformation("client_held") is get_transformation("client_knowledge")
    assert get_transformation("phone_screenshot") is get_transformation(
        "device_ui_screenshot"
    )
    assert get_transformation("email_threads") is get_transformation(
        "email_thread_archive"
    )
    assert get_transformation("slack_threads") is get_transformation("slack_mcp_dump")
    assert get_transformation("process_map") is get_transformation("process_flowchart")
    assert get_transformation("presentation_deck") is get_transformation(
        "process_presentation"
    )
    assert get_transformation("zoom_transcript") is get_transformation(
        "recorded_working_session"
    )
    assert get_transformation("screen_recording") is get_transformation(
        "interactive_screen_recording"
    )
    assert get_transformation("jira_export") is get_transformation("jira_issue_export")
    assert get_transformation("html_knowledge_archive") is get_transformation(
        "knowledge_base_html_export"
    )
    assert get_transformation("reference_attachment") is get_transformation(
        "reference_document"
    )


def test_unknown_representation_raises_with_known_list():
    assert not has_transformation("interpretive_dance")
    with pytest.raises(KeyError, match="support_transcripts"):
        get_transformation("interpretive_dance")


def test_transformation_placement_and_utterance_flags():
    transcripts = get_transformation("support_transcripts")
    assert transcripts.placement == "pooled"
    assert transcripts.carries_agent_utterances is True
    screenshots = get_transformation("website_screenshot")
    assert screenshots.placement == "pooled"
    assert screenshots.kit_dirname == "uploaded_materials"
    assert screenshots.carries_agent_utterances is False
    device_screenshots = get_transformation("device_ui_screenshot")
    assert device_screenshots.placement == "pooled"
    assert device_screenshots.kit_dirname == "uploaded_materials"
    assert device_screenshots.carries_agent_utterances is False
    kickoff = get_transformation("customer_kickoff_document")
    assert kickoff.placement == "named"
    assert kickoff.kit_dirname == "uploaded_materials"
    assert kickoff.carries_agent_utterances is False
    emails = get_transformation("email_thread_archive")
    assert emails.placement == "named"
    assert emails.kit_dirname == "uploaded_materials"
    assert emails.carries_agent_utterances is False
    references = get_transformation("reference_document")
    assert references.placement == "named"
    assert references.kit_dirname == "uploaded_materials"
    assert references.carries_agent_utterances is False
    slack = get_transformation("slack_mcp_dump")
    assert slack.placement == "named"
    assert slack.kit_dirname == "uploaded_materials"
    assert slack.carries_agent_utterances is False
    flowchart = get_transformation("process_flowchart")
    assert flowchart.placement == "named"
    assert flowchart.kit_dirname == "uploaded_materials"
    assert flowchart.carries_agent_utterances is False
    presentation = get_transformation("process_presentation")
    assert presentation.placement == "named"
    assert presentation.kit_dirname == "uploaded_materials"
    assert presentation.carries_agent_utterances is False
    working_session = get_transformation("recorded_working_session")
    assert working_session.placement == "named"
    assert working_session.kit_dirname == "uploaded_materials"
    assert working_session.carries_agent_utterances is False
    helpdesk = get_transformation("helpdesk_automation_export")
    assert helpdesk.placement == "named"
    assert helpdesk.kit_dirname == "uploaded_materials"
    assert helpdesk.carries_agent_utterances is False
    api_contract = get_transformation("api_contract_pack")
    assert api_contract.placement == "named"
    assert api_contract.kit_dirname == "uploaded_materials"
    assert api_contract.carries_agent_utterances is False
    screen_recording = get_transformation("interactive_screen_recording")
    assert screen_recording.placement == "named"
    assert screen_recording.kit_dirname == "uploaded_materials"
    assert screen_recording.carries_agent_utterances is False
    jira = get_transformation("jira_issue_export")
    assert jira.placement == "named"
    assert jira.kit_dirname == "uploaded_materials"
    assert jira.carries_agent_utterances is False
    qa_export = get_transformation("contact_center_qa_export")
    assert qa_export.placement == "named"
    assert qa_export.kit_dirname == "uploaded_materials"
    assert qa_export.carries_agent_utterances is True
    html_archive = get_transformation("knowledge_base_html_export")
    assert html_archive.placement == "named"
    assert html_archive.kit_dirname == "uploaded_materials"
    assert html_archive.carries_agent_utterances is False

    # Only the non-materializing representations skip kit output.
    assert get_transformation("explicit_rules").materializes is False
    client = get_transformation("client_knowledge")
    assert client.materializes is False
    assert client.carries_agent_utterances is False
    assert transcripts.materializes is True
    assert helpdesk.materializes is True


def _qa_interaction(ordinal: int) -> dict:
    day = f"{ordinal:02d}"
    prefix = f"qa-{ordinal}"
    return {
        "interaction_id": f"interaction-{ordinal}",
        "channel": "voice" if ordinal % 2 else "chat",
        "queue": "Card Servicing",
        "language": "en-US",
        "customer_reference": f"customer-{1000 + ordinal}",
        "agent_id": "agent-1",
        "disposition": "resolved",
        "started_at": f"2026-07-{day}T10:00:00-07:00",
        "ended_at": f"2026-07-{day}T10:06:00-07:00",
        "transcript": [
            {
                "turn_id": f"{prefix}-turn-1",
                "speaker_role": "customer",
                "started_at": f"2026-07-{day}T10:00:05-07:00",
                "ended_at": f"2026-07-{day}T10:00:20-07:00",
                "text": "I want to close this card because I no longer use it.",
            },
            {
                "turn_id": f"{prefix}-turn-2",
                "speaker_role": "agent",
                "speaker_id": "agent-1",
                "started_at": f"2026-07-{day}T10:00:25-07:00",
                "ended_at": f"2026-07-{day}T10:00:55-07:00",
                "text": (
                    "I will check closure eligibility before discussing any "
                    "retention offer."
                ),
            },
            {
                "turn_id": f"{prefix}-turn-3",
                "speaker_role": "system",
                "started_at": f"2026-07-{day}T10:01:00-07:00",
                "ended_at": f"2026-07-{day}T10:01:05-07:00",
                "text": "Closure readiness check completed.",
            },
            {
                "turn_id": f"{prefix}-turn-4",
                "speaker_role": "agent",
                "speaker_id": "agent-1",
                "started_at": f"2026-07-{day}T10:01:10-07:00",
                "ended_at": f"2026-07-{day}T10:01:35-07:00",
                "text": "The account is eligible, so we can continue the review.",
            },
        ],
        "evaluations": [
            {
                "evaluation_id": f"{prefix}-evaluation",
                "rubric_id": "card-servicing-v3",
                "reviewer_id": "reviewer-1",
                "status": "final",
                "created_at": f"2026-07-{day}T10:20:00-07:00",
                "finalized_at": f"2026-07-{day}T11:00:00-07:00",
                "items": [
                    {
                        "item_id": "ordered-eligibility",
                        "result": "pass",
                        "score": 5,
                        "reviewer_note": (
                            "Approved handling: eligibility precedes retention."
                        ),
                        "evidence_turn_ids": [f"{prefix}-turn-2"],
                    },
                    {
                        "item_id": "case-documentation",
                        "result": "pass",
                        "score": 5,
                        "reviewer_note": "The interaction has a complete case trail.",
                        "evidence_turn_ids": [f"{prefix}-turn-3"],
                    },
                ],
                "overall_score": 100,
                "critical_failure": False,
            }
        ],
        "review_history": [
            {
                "event_id": f"{prefix}-history-1",
                "actor_id": "reviewer-1",
                "event_type": "assigned",
                "created_at": f"2026-07-{day}T10:15:00-07:00",
                "note": "Assigned from the weekly sample.",
            },
            {
                "event_id": f"{prefix}-history-2",
                "actor_id": "reviewer-1",
                "event_type": "finalized",
                "created_at": f"2026-07-{day}T11:00:00-07:00",
                "note": "Final review published.",
            },
        ],
    }


def _minimal_qa_export() -> dict:
    return {
        "export_format": "contact_center_qa_export_v1",
        "exported_at": "2026-07-31T18:00:00-07:00",
        "source_system": {
            "name": "Example Contact Quality",
            "environment": "production",
        },
        "users": [
            {"user_id": "agent-1", "display_name": "Amira Chen", "role": "agent"},
            {
                "user_id": "reviewer-1",
                "display_name": "Mateo Ruiz",
                "role": "reviewer",
            },
            {
                "user_id": "lead-1",
                "display_name": "Priya Shah",
                "role": "qa_lead",
            },
        ],
        "rubrics": [
            {
                "rubric_id": "card-servicing-v3",
                "name": "Card servicing quality review",
                "version": "3.0",
                "status": "published",
                "items": [
                    {
                        "item_id": "ordered-eligibility",
                        "title": "Checks eligibility before retention",
                        "max_score": 5,
                        "critical": True,
                    },
                    {
                        "item_id": "case-documentation",
                        "title": "Maintains a complete case trail",
                        "max_score": 5,
                        "critical": False,
                    },
                ],
            }
        ],
        "interaction_count": 4,
        "evaluation_count": 4,
        "interactions": [_qa_interaction(ordinal) for ordinal in range(1, 5)],
    }


def _minimal_qa_manifest() -> dict:
    return {
        "snapshot": "2026-07-31T18:00:00-07:00",
        "artifact": {
            "filename": "weekly_card_quality_export.json",
            "authoritative_fact_ids": ["F1"],
        },
        "decisions": [
            {
                "fact_id": "F1",
                "interaction_id": "interaction-1",
                "evaluation_id": "qa-1-evaluation",
                "rubric_item_id": "ordered-eligibility",
                "status": "final_current",
                "evidence": [
                    {
                        "source": "turn",
                        "turn_id": "qa-1-turn-2",
                        "excerpt": (
                            "check closure eligibility before discussing any "
                            "retention offer"
                        ),
                    },
                    {
                        "source": "reviewer_note",
                        "excerpt": "eligibility precedes retention",
                    },
                ],
            }
        ],
        "interaction_adjudication": [
            {
                "interaction_id": "interaction-1",
                "role": "authoritative_current",
            },
            {"interaction_id": "interaction-2", "role": "supporting_current"},
            {"interaction_id": "interaction-3", "role": "calibration_history"},
            {"interaction_id": "interaction-4", "role": "distractor"},
        ],
    }


def test_contact_center_qa_export_validates_final_review_evidence(tmp_path):
    export_path = tmp_path / "qa_export.json"
    manifest_path = tmp_path / "eval_manifest.json"
    export_path.write_text(json.dumps(_minimal_qa_export()))
    manifest_path.write_text(json.dumps(_minimal_qa_manifest()))
    schema = {
        "id": "qa_schema",
        "facts": [{"id": "F1", "statement": "Eligibility must precede retention."}],
        "transformations": [
            {
                "representation": "contact_center_qa_export",
                "eval_manifest_path": str(manifest_path),
                "artifacts": [
                    {
                        "path": str(export_path),
                        "kit_filename": "weekly_card_quality_export.json",
                        "included_fact_ids": ["F1"],
                    }
                ],
            }
        ],
    }
    transformation = get_transformation("contact_center_qa_export")
    artifacts = transformation.discover_artifacts(
        schema, tmp_path / "schema.json", schema["transformations"][0]
    )
    assert transformation.validate(schema, artifacts) == []
    neutralized = transformation.neutralize(artifacts[0], 1)
    assert (
        neutralized.relative_path
        == "uploaded_materials/weekly_card_quality_export.json"
    )
    assert neutralized.artifact_kind == "contact_center_qa_export"
    pooled = _pool_uploaded_material_names([neutralized])
    assert pooled[0].relative_path == "uploaded_materials/qa_review_export.json"
    assert "eligibility precedes retention" in transformation.to_text(artifacts[0])

    broken = _minimal_qa_export()
    broken["interactions"][0]["evaluations"][0]["items"][0].update(
        {"result": "fail", "score": 0}
    )
    broken["interactions"][0]["evaluations"][0]["overall_score"] = 50
    export_path.write_text(json.dumps(broken))
    issues = transformation.validate(schema, artifacts)
    assert any(
        "decision item 'ordered-eligibility' must pass" in issue for issue in issues
    )

    unlinked = _minimal_qa_export()
    unlinked["interactions"][0]["evaluations"][0]["items"][0]["evidence_turn_ids"] = [
        "qa-1-turn-3"
    ]
    export_path.write_text(json.dumps(unlinked))
    issues = transformation.validate(schema, artifacts)
    assert any("must be cited by the scored rubric item" in issue for issue in issues)

    artifacts[0].metadata.pop("eval_manifest_path")
    issues = transformation.validate(schema, artifacts)
    assert any("eval_manifest_path is required" in issue for issue in issues)


def test_contact_center_qa_export_guards_malformed_and_stale_inputs(tmp_path):
    export_path = tmp_path / "qa_export.json"
    manifest_path = tmp_path / "eval_manifest.json"
    manifest_path.write_text(json.dumps(_minimal_qa_manifest()))
    schema = {
        "id": "qa_schema",
        "facts": [{"id": "F1", "statement": "Eligibility must precede retention."}],
        "transformations": [
            {
                "representation": "contact_center_qa_export",
                "eval_manifest_path": str(manifest_path),
                "artifacts": [
                    {
                        "path": str(export_path),
                        "kit_filename": "weekly_card_quality_export.json",
                        "included_fact_ids": ["F1"],
                    }
                ],
            }
        ],
    }
    transformation = get_transformation("contact_center_qa_export")
    artifacts = transformation.discover_artifacts(
        schema, tmp_path / "schema.json", schema["transformations"][0]
    )

    # A non-object export root is reported, never raised.
    export_path.write_text("[]")
    issues = transformation.validate(schema, artifacts)
    assert any("root must be an object" in issue for issue in issues)

    # Facts cannot ride an evaluation scored on a non-published rubric.
    retired = _minimal_qa_export()
    retired["rubrics"][0]["status"] = "retired"
    export_path.write_text(json.dumps(retired))
    issues = transformation.validate(schema, artifacts)
    assert any("non-current rubric" in issue for issue in issues)

    # Booleans are int subclasses but are not scores.
    boolean = _minimal_qa_export()
    boolean["interactions"][0]["evaluations"][0]["items"][0]["score"] = True
    export_path.write_text(json.dumps(boolean))
    issues = transformation.validate(schema, artifacts)
    assert any("invalid score" in issue for issue in issues)

    # A critical failure cannot warrant a current fact.
    critical = _minimal_qa_export()
    critical["interactions"][0]["evaluations"][0]["critical_failure"] = True
    export_path.write_text(json.dumps(critical))
    issues = transformation.validate(schema, artifacts)
    assert any("critical failure" in issue for issue in issues)

    # Leak scans reject schema fact ids and adjudication roles.
    leaky = _minimal_qa_export()
    leaky["interactions"][1]["transcript"][0]["text"] += " (see F1)"
    export_path.write_text(json.dumps(leaky))
    issues = transformation.validate(schema, artifacts)
    assert any("author-only fact ids leaked" in issue for issue in issues)

    role_leak = _minimal_qa_export()
    role_leak["interactions"][1]["transcript"][0]["text"] += " authoritative_current"
    export_path.write_text(json.dumps(role_leak))
    issues = transformation.validate(schema, artifacts)
    assert any("adjudication roles leaked" in issue for issue in issues)

    # The author-path leak scan runs even without an eval_manifest_path.
    path_leak = _minimal_qa_export()
    path_leak["interactions"][1]["transcript"][0]["text"] += f" ({export_path})"
    export_path.write_text(json.dumps(path_leak))
    artifacts[0].metadata.pop("eval_manifest_path")
    issues = transformation.validate(schema, artifacts)
    assert any(
        "author-only source or manifest path leaked" in issue for issue in issues
    )


def test_jira_issue_export_validates_history_links_and_author_ownership(tmp_path):
    users = [
        {"accountId": "u1", "displayName": "Maya"},
        {"accountId": "u2", "displayName": "Jonah"},
        {"accountId": "u3", "displayName": "Priya"},
    ]
    issues = []
    for ordinal in range(1, 5):
        key = f"CARE-{ordinal}"
        first_comment = (
            "Approved current decision with released implementation."
            if ordinal == 1
            else f"Ordinary project discussion for work item {ordinal}."
        )
        issues.append(
            {
                "id": str(ordinal),
                "key": key,
                "fields": {
                    "summary": f"Work item {ordinal}",
                    "description": "Tracked decision and delivery context.",
                    "issuetype": {"name": "Story"},
                    "status": {"name": "Done"},
                    "priority": {"name": "Medium"},
                    "project": {"key": "CARE"},
                    "created": "2026-07-01T09:00:00-07:00",
                    "updated": "2026-07-02T15:00:00-07:00",
                    "reporter": {"accountId": "u1"},
                    "assignee": {"accountId": "u2"},
                    "labels": ["care"],
                    "components": [{"name": "Care"}],
                    "fixVersions": [{"name": "2026.07"}],
                    "comment": {
                        "comments": [
                            {
                                "id": f"c{ordinal}a",
                                "author": {"accountId": "u1"},
                                "body": first_comment,
                                "created": "2026-07-01T10:00:00-07:00",
                            },
                            {
                                "id": f"c{ordinal}b",
                                "author": {"accountId": "u3"},
                                "body": "QA and owner follow-up recorded here.",
                                "created": "2026-07-02T11:00:00-07:00",
                            },
                        ]
                    },
                    "issuelinks": [
                        {
                            "type": {"name": "Relates"},
                            "issueKey": f"CARE-{ordinal % 4 + 1}",
                        }
                    ],
                },
                "changelog": {
                    "histories": [
                        {
                            "id": f"h{ordinal}",
                            "author": {"accountId": "u2"},
                            "created": "2026-07-02T15:00:00-07:00",
                            "items": [
                                {
                                    "field": "status",
                                    "fromString": "Open",
                                    "toString": "Done",
                                }
                            ],
                        }
                    ]
                },
            }
        )
    export = tmp_path / "jira.json"
    export.write_text(
        json.dumps(
            {
                "export_format": "jira_cloud_issue_export_v1",
                "exported_at": "2026-07-03T12:00:00-07:00",
                "projects": [{"key": "CARE", "name": "Care"}],
                "users": users,
                "issues": issues,
            }
        )
    )
    manifest = tmp_path / "eval_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "snapshot": "2026-07-03T12:00:00-07:00",
                "artifact": {
                    "filename": "work_items.json",
                    "authoritative_fact_ids": ["F1"],
                },
                "decisions": [
                    {
                        "fact_id": "F1",
                        "issue_key": "CARE-1",
                        "status": "final_current",
                        "evidence": [
                            {
                                "comment_id": "c1a",
                                "excerpt": (
                                    "Approved current decision with released "
                                    "implementation."
                                ),
                            }
                        ],
                    }
                ],
                "issue_adjudication": [
                    {
                        "issue_key": f"CARE-{ordinal}",
                        "role": (
                            "authoritative_current"
                            if ordinal == 1
                            else "distractor_closed"
                        ),
                    }
                    for ordinal in range(1, 5)
                ],
            }
        )
    )
    schema = {"id": "jira", "facts": [{"id": "F1", "statement": "decision"}]}
    spec = {
        "representation": "jira_issue_export",
        "eval_manifest_path": str(manifest),
        "artifacts": [
            {
                "path": str(export),
                "kit_filename": "work_items.json",
                "included_fact_ids": ["F1"],
            }
        ],
    }

    transformation = get_transformation("jira_issue_export")
    artifacts = transformation.discover_artifacts(schema, tmp_path, spec)
    assert transformation.validate(schema, artifacts) == []
    neutralized = transformation.neutralize(artifacts[0], 0)
    assert neutralized.relative_path == "uploaded_materials/work_items.json"
    assert neutralized.artifact_kind == "jira_issue_export"


def test_context_only_support_transcripts_do_not_inherit_legacy_plan_coverage(
    tmp_path,
):
    case_a = tmp_path / "case_a.md"
    case_b = tmp_path / "case_b.md"
    case_a.write_text("# Case 001\n\n**Customer:** Hi\n\n**Agent:** Hello\n")
    case_b.write_text("# Case 002\n\n**Customer:** Hi\n\n**Agent:** Hello\n")
    schema = {
        "facts": [{"id": "F001"}],
        "transcripts": [{"included_fact_ids": ["F001"]}],
    }
    artifacts = [
        TransformationArtifact(
            source_path=path,
            metadata={"context_only": True},
        )
        for path in (case_a, case_b)
    ]
    transformation = get_transformation("support_transcripts")

    assert transformation.validate(schema, artifacts) == []
    assert transformation.covered_fact_ids(schema, artifacts) == set()


def test_context_only_support_transcripts_reject_mixed_or_fact_bearing_sets(tmp_path):
    case_a = tmp_path / "case_a.md"
    case_b = tmp_path / "case_b.md"
    case_a.write_text("# Case 001\n")
    case_b.write_text("# Case 002\n")
    transformation = get_transformation("support_transcripts")
    schema = {"facts": [{"id": "F001"}]}

    mixed = [
        TransformationArtifact(
            source_path=case_a,
            metadata={"context_only": True},
        ),
        TransformationArtifact(source_path=case_b),
    ]
    assert transformation.validate(schema, mixed) == [
        "support-transcript transformations must not mix context-only and "
        "fact-bearing artifacts"
    ]

    fact_bearing = [
        TransformationArtifact(
            source_path=case_a,
            included_fact_ids=["F001"],
            metadata={"context_only": True},
        )
    ]
    assert transformation.validate(schema, fact_bearing) == [
        "case_a.md: context-only transcripts must not declare included_fact_ids"
    ]


def test_knowledge_base_html_export_delivers_raw_self_contained_archive(tmp_path):
    archive = tmp_path / "care_archive.html"
    archive.write_text(
        "<!doctype html><html><head><style>.x{color:#123}</style></head><body>"
        '<article data-article-id="KB-100"><h1>Current procedure</h1>'
        "<p>Verify the record before continuing.</p></article>"
        '<article data-article-id="KB-200"><h1>Adjacent reference</h1>'
        "<p>Use the normal account page.</p></article>"
        "<script>const hidden = 'not visible';</script></body></html>"
    )
    manifest = tmp_path / "eval_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "filename": archive.name,
                "authoritative_fact_ids": ["F1"],
                "articles": [
                    {"article_id": "KB-100", "authoritative_fact_ids": ["F1"]},
                    {"article_id": "KB-200", "authoritative_fact_ids": []},
                ],
            }
        )
    )
    schema = {"id": "archive", "facts": [{"id": "F1", "statement": "verify"}]}
    spec = {
        "representation": "knowledge_base_html_export",
        "minimum_articles": 2,
        "minimum_context_articles": 1,
        "artifacts": [
            {
                "path": str(archive),
                "kit_filename": "knowledge_archive.html",
                "eval_manifest_path": str(manifest),
                "included_fact_ids": ["F1"],
            }
        ],
    }
    transformation = get_transformation("knowledge_base_html_export")
    (artifact,) = transformation.discover_artifacts(
        schema, tmp_path / "schema.json", spec
    )

    assert transformation.validate(schema, [artifact]) == []
    assert "Verify the record" in transformation.to_text(artifact)
    assert "not visible" not in transformation.to_text(artifact)
    kit_file = transformation.neutralize(artifact, 1)
    assert kit_file.relative_path == "uploaded_materials/knowledge_archive.html"
    assert kit_file.content == archive.read_bytes()
    assert kit_file.artifact_kind == "knowledge_base_html_export"

    archive.write_text(
        archive.read_text().replace(
            "</body>", '<img src="https://example.test/x.png"></body>'
        )
    )
    assert any(
        "archive must be self-contained" in issue
        for issue in transformation.validate(schema, [artifact])
    )


def test_interactive_screen_recording_uses_author_timeline_and_neutral_video(
    tmp_path,
):
    source = tmp_path / "apn_fix.mp4"
    source.write_bytes(b"\x00\x00\x00\x18ftypisom")
    timeline = tmp_path / "timeline.md"
    timeline.write_text("At 2s the active SIM opens APN settings.\n")
    manifest = tmp_path / "eval_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "artifacts": [
                    {
                        "filename": source.name,
                        "fixture": "clean",
                        "events": [
                            {
                                "kind": "authoritative",
                                "start_seconds": 1,
                                "end_seconds": 5,
                                "fact_ids": ["F1"],
                            }
                        ],
                    }
                ]
            }
        )
    )
    schema = {"id": "screen", "facts": [{"id": "F1", "statement": "fix"}]}
    spec = {
        "representation": "interactive_screen_recording",
        "artifacts": [
            {
                "path": str(source),
                "kit_filename": "device_walkthrough.mp4",
                "text_source_path": str(timeline),
                "eval_manifest_path": str(manifest),
                "duration_seconds": 6,
                "included_fact_ids": ["F1"],
            }
        ],
    }
    transformation = get_transformation("interactive_screen_recording")
    artifacts = transformation.discover_artifacts(
        schema, tmp_path / "schema.json", spec
    )

    assert transformation.validate(schema, artifacts) == []
    assert transformation.to_text(artifacts[0]) == timeline.read_text()
    kit_file = transformation.neutralize(artifacts[0], 1)
    assert kit_file.relative_path == "uploaded_materials/device_walkthrough.mp4"
    assert kit_file.content == source.read_bytes()
    assert kit_file.artifact_kind == "interactive_screen_recording"


def _minimal_api_contract_spec() -> dict:
    return {
        "format": "api_contract_pack_v1",
        "release": {
            "environment": "production",
            "status": "published",
            "current": True,
            "superseded_by": None,
        },
        "cover_email": "From: api@example.test\n\nAttached contract.\n",
        "openapi": {"openapi": "3.1.0", "info": {"title": "Example"}, "paths": {}},
        "postman_collection": {"info": {"name": "Example"}, "item": []},
        "error_behavior_columns": ["rule_id"],
        "error_behavior": [{"rule_id": "ERR-1"}],
        "record_contract_notes": "# Record notes\n",
    }


def test_api_contract_pack_is_deterministic_and_builds_expected_files(tmp_path):
    spec = _minimal_api_contract_spec()
    first = build_api_contract_zip(spec)
    assert first == build_api_contract_zip(spec)
    with zipfile.ZipFile(io.BytesIO(first)) as archive:
        assert archive.namelist() == [
            "cover_email.eml",
            "openapi.yaml",
            "postman_collection.json",
            "error_behavior.csv",
            "record_contract_notes.md",
        ]
        assert "openapi: 3.1.0" in archive.read("openapi.yaml").decode()
        assert archive.read("error_behavior.csv").decode() == "rule_id\nERR-1\n"
        # no in-world date on the release block: legacy fixed fallback
        assert all(
            info.date_time == (2026, 1, 1, 0, 0, 0) for info in archive.infolist()
        )

    # member timestamps are spec-derived: release.snapshot_at wins, then
    # release.published_on, so the delivered archive carries the pack's own
    # in-world date instead of a build-era constant
    spec["release"]["snapshot_at"] = "2025-11-14T12:00:00-05:00"
    with zipfile.ZipFile(io.BytesIO(build_api_contract_zip(spec))) as archive:
        assert all(
            info.date_time == (2025, 11, 14, 12, 0, 0) for info in archive.infolist()
        )
    del spec["release"]["snapshot_at"]
    spec["release"]["published_on"] = "2025-10-16"
    with zipfile.ZipFile(io.BytesIO(build_api_contract_zip(spec))) as archive:
        assert all(
            info.date_time == (2025, 10, 16, 0, 0, 0) for info in archive.infolist()
        )
    del spec["release"]["published_on"]

    source_path = tmp_path / "authored_contract.json"
    source_path.write_text(json.dumps(spec))
    schema = {
        "id": "api_contract_schema",
        "facts": [{"id": "A1", "statement": "Published schema rule."}],
        "transformations": [
            {
                "representation": "api_contract_pack",
                "artifacts": [
                    {
                        "path": str(source_path),
                        "kit_filename": "contract.zip",
                        "included_fact_ids": ["A1"],
                    }
                ],
            }
        ],
    }
    transformation = get_transformation("api_contract_pack")
    artifacts = transformation.discover_artifacts(
        schema, tmp_path / "schema.json", schema["transformations"][0]
    )
    assert transformation.validate(schema, artifacts) == []
    assert transformation.neutralize(artifacts[0], 1).content == first
    assert "## openapi.yaml" in transformation.to_text(artifacts[0])


def _minimal_helpdesk_spec() -> dict:
    return {
        "format": "helpdesk_automation_export_v2",
        "snapshot": {
            "source_system": "Example Desk",
            "environment": "production",
            "exported_at": "2026-06-05T18:00:00-04:00",
        },
        "cover_email": "From: ops@example.test\n\nAttached export.\n",
        "macros": [{"macro_id": "MAC-1"}],
        "triggers": [{"trigger_id": "TRG-1"}],
        "policy_contracts": [{"contract_id": "CONTRACT-1"}],
        "field_columns": ["row_id"],
        "fields": [{"row_id": "FLD-1"}],
        "sla_policies": [{"policy_id": "SLA-1"}],
        "views": [{"view_id": "VIEW-1"}],
    }


def test_helpdesk_export_is_deterministic_and_builds_expected_files(tmp_path):
    spec = _minimal_helpdesk_spec()
    first = build_helpdesk_export_zip(spec)
    second = build_helpdesk_export_zip(spec)
    assert first == second
    with zipfile.ZipFile(io.BytesIO(first)) as archive:
        assert archive.namelist() == [
            "cover_email.eml",
            "macros.json",
            "triggers.json",
            "policy_contracts.json",
            "fields.csv",
            "sla_policies.json",
            "views.json",
        ]
        assert '"macro_id": "MAC-1"' in archive.read("macros.json").decode()
        assert archive.read("fields.csv").decode() == "row_id\nFLD-1\n"
        assert all(
            info.date_time == (2026, 6, 5, 18, 0, 0) for info in archive.infolist()
        )

    section_dir = tmp_path / "helpdesk"
    section_dir.mkdir()
    spec_path = section_dir / "authored_export.json"
    spec_path.write_text(json.dumps(spec))
    schema = {
        "id": "helpdesk_schema",
        "facts": [{"id": "H1", "statement": "Configured behavior."}],
        "transformations": [
            {
                "representation": "helpdesk_automation_export",
                "artifacts": [
                    {
                        "path": str(spec_path),
                        "kit_filename": "admin_export.zip",
                        "included_fact_ids": ["H1"],
                    }
                ],
            }
        ],
    }
    schema_path = section_dir / "schema.json"
    schema_path.write_text(json.dumps(schema))
    transformation = get_transformation("helpdesk_automation_export")
    artifacts = transformation.discover_artifacts(
        schema, schema_path, schema["transformations"][0]
    )
    assert transformation.validate(schema, artifacts) == []
    assert transformation.neutralize(artifacts[0], 1).content == first
    text = transformation.to_text(artifacts[0])
    assert "## macros.json" in text
    assert "## policy_contracts.json" in text
    assert "## fields.csv" in text


def test_helpdesk_export_rejects_closed_world_facts_without_enforcing_contract(
    tmp_path,
):
    spec = _minimal_helpdesk_spec()
    spec["policy_contracts"][0].update(
        {
            "active": True,
            "environment": "production",
            "status": "published",
            "superseded_by": None,
            "closed_world": {
                "complete": False,
                "unlisted_behavior": "allow",
            },
        }
    )
    spec_path = tmp_path / "authored_export.json"
    spec_path.write_text(json.dumps(spec))
    fact_map_path = tmp_path / "fact_map.json"
    fact_map_path.write_text(
        json.dumps(
            {
                "facts": {
                    "H1": {
                        "file": "policy_contracts.json",
                        "object_ids": ["CONTRACT-1"],
                        "locations": ["policy_contracts[].closed_world"],
                        "claim_type": "closed_world_policy",
                        "closure_object_ids": ["CONTRACT-1"],
                    }
                }
            }
        )
    )
    schema = {
        "id": "helpdesk_schema",
        "facts": [{"id": "H1", "statement": "No other action is supported."}],
        "transformations": [
            {
                "representation": "helpdesk_automation_export",
                "fact_map_path": str(fact_map_path),
                "artifacts": [
                    {
                        "path": str(spec_path),
                        "kit_filename": "admin_export.zip",
                        "included_fact_ids": ["H1"],
                    }
                ],
            }
        ],
    }
    transformation = get_transformation("helpdesk_automation_export")
    artifacts = transformation.discover_artifacts(
        schema, tmp_path / "schema.json", schema["transformations"][0]
    )
    issues = transformation.validate(schema, artifacts)
    assert any("non-enforcing contract 'CONTRACT-1'" in issue for issue in issues)


def test_helpdesk_export_rejects_dangling_current_field_references(tmp_path):
    spec = _minimal_helpdesk_spec()
    spec["triggers"][0].update(
        {
            "active": True,
            "environment": "production",
            "status": "published",
            "superseded_by": None,
            "conditions": [{"field": "case.missing", "operator": "is", "value": True}],
        }
    )
    source = tmp_path / "authored_export.json"
    source.write_text(json.dumps(spec))
    schema = {
        "id": "helpdesk_schema",
        "facts": [],
        "transformations": [
            {
                "representation": "helpdesk_automation_export",
                "artifacts": [
                    {
                        "path": str(source),
                        "kit_filename": "admin_export.zip",
                        "included_fact_ids": [],
                    }
                ],
            }
        ],
    }
    transformation = get_transformation("helpdesk_automation_export")
    artifacts = transformation.discover_artifacts(
        schema, tmp_path / "schema.json", schema["transformations"][0]
    )

    assert any(
        "unknown fields ['case.missing']" in issue
        for issue in transformation.validate(schema, artifacts)
    )


def test_helpdesk_export_rejects_evaluator_facing_cover_email(tmp_path):
    spec = _minimal_helpdesk_spec()
    spec["cover_email"] = (
        "From: ops@example.test\n\nUsage is context only; "
        "current authority comes from active objects.\n"
    )
    source = tmp_path / "authored_export.json"
    source.write_text(json.dumps(spec))
    schema = {
        "id": "helpdesk_schema",
        "facts": [],
        "transformations": [
            {
                "representation": "helpdesk_automation_export",
                "artifacts": [
                    {
                        "path": str(source),
                        "kit_filename": "admin_export.zip",
                        "included_fact_ids": [],
                    }
                ],
            }
        ],
    }
    transformation = get_transformation("helpdesk_automation_export")
    artifacts = transformation.discover_artifacts(
        schema, tmp_path / "schema.json", schema["transformations"][0]
    )

    assert any(
        "evaluator-facing language" in issue
        for issue in transformation.validate(schema, artifacts)
    )


def test_customer_kickoff_document_keeps_business_context_without_author_metadata(
    tmp_path,
):
    section_dir = tmp_path / "sections" / "scope"
    section_dir.mkdir(parents=True)
    document_path = section_dir / "kickoff_background.md"
    document_path.write_text(
        "# Kickoff session background\n\n"
        "## POC journeys\n\n"
        "The agent must not add payment methods to customer accounts.\n"
    )
    eval_manifest_path = section_dir / "eval_manifest.json"
    eval_manifest_path.write_text(
        json.dumps(
            {
                "authoritative_facts": [
                    {
                        "id": "F1",
                        "statement": "Do not add payment methods.",
                    }
                ]
            }
        )
    )
    schema = {
        "id": "scope_schema",
        "facts": [{"id": "F1", "statement": "Do not add payment methods."}],
        "transformations": [
            {
                "representation": "customer_kickoff_document",
                "artifacts": [
                    {
                        "path": str(document_path),
                        "kit_filename": "kickoff_questionnaire.md",
                        "eval_manifest_path": str(eval_manifest_path),
                        "included_fact_ids": ["F1"],
                    }
                ],
            }
        ],
    }
    transformation = get_transformation("customer_kickoff_document")
    (artifact,) = transformation.discover_artifacts(
        schema, section_dir / "schema.json", schema["transformations"][0]
    )

    assert transformation.validate(schema, [artifact]) == []
    assert "must not add payment methods" in transformation.to_text(artifact)
    kit_file = transformation.neutralize(artifact, 1)
    assert kit_file.relative_path == ("uploaded_materials/kickoff_questionnaire.md")
    assert kit_file.content == document_path.read_bytes()


def test_recorded_working_session_validates_zoom_style_decision_history(tmp_path):
    session_dir = tmp_path / "working_session"
    session_dir.mkdir()
    transcript_path = session_dir / "service_foundations_review.vtt"
    transcript_path.write_text(
        "WEBVTT\n\n"
        "00:00:00.000 --> 00:00:08.000\n"
        "<v Maya Ortiz>Let’s use this session to close the service rules.\n\n"
        "00:04:00.000 --> 00:04:15.000\n"
        "<v Jordan Lee>I propose that every record change gets a recap.\n\n"
        "00:12:00.000 --> 00:12:18.000\n"
        "<v Maya Ortiz>That first version is too broad; read-only lookups are not changes.\n\n"
        "00:25:00.000 --> 00:26:00.000\n"
        "<v Jordan Lee>Final decision: recap and confirmation apply before a record change.\n"
    )
    manifest_path = session_dir / "eval_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "decisions": [
                    {
                        "fact_id": "F1",
                        "status": "proposal",
                        "timestamp": "00:04:00.000",
                    },
                    {
                        "fact_id": "F1",
                        "status": "rejected",
                        "timestamp": "00:12:00.000",
                    },
                    {
                        "fact_id": "F1",
                        "status": "final_current",
                        "timestamp": "00:25:00.000",
                    },
                ]
            }
        )
    )
    schema = {
        "id": "service_foundations_schema",
        "facts": [{"id": "F1", "statement": "Recap changes before submission."}],
    }
    spec = {
        "representation": "recorded_working_session",
        "eval_manifest_path": str(manifest_path),
        "minimum_duration_minutes": 25,
        "maximum_duration_minutes": 40,
        "minimum_speakers": 2,
        "artifacts": [
            {
                "path": str(transcript_path),
                "kit_filename": "service_foundations_working_session.vtt",
                "included_fact_ids": ["F1"],
            }
        ],
    }
    transformation = get_transformation("recorded_working_session")
    (artifact,) = transformation.discover_artifacts(
        schema, session_dir / "schema.json", spec
    )

    assert transformation.validate(schema, [artifact]) == []
    assert "Final decision" in transformation.to_text(artifact)
    kit_file = transformation.neutralize(artifact, 1)
    assert kit_file.relative_path == (
        "uploaded_materials/service_foundations_working_session.vtt"
    )
    assert kit_file.content == transcript_path.read_bytes()
    assert b"F1" not in kit_file.content

    artifact.metadata["minimum_duration_minutes"] = 27
    assert (
        "service_foundations_review.vtt: transcript is 26.0 minutes; minimum is 27"
        in transformation.validate(schema, [artifact])
    )

    artifact.metadata["minimum_duration_minutes"] = 25
    artifact.metadata["minimum_words_per_minute"] = 5
    assert (
        "service_foundations_review.vtt: transcript has 1.5 words per minute; "
        "minimum is 5" in transformation.validate(schema, [artifact])
    )
    artifact.metadata.pop("minimum_words_per_minute")
    manifest = json.loads(manifest_path.read_text())
    manifest["decisions"][-1]["status"] = "superseded"
    manifest_path.write_text(json.dumps(manifest))
    assert (
        "service_foundations_review.vtt: final_current decisions must exactly match "
        "included_fact_ids" in transformation.validate(schema, [artifact])
    )


def test_recorded_working_session_validates_cross_meeting_decision_series(tmp_path):
    session_dir = tmp_path / "working_session_series"
    session_dir.mkdir()
    first_path = session_dir / "2026-04-01_intake.vtt"
    first_path.write_text(
        "WEBVTT\n\n"
        "00:00:00.000 --> 00:00:20.000\n"
        "<v Maya Ortiz>Um, we still need a decision on recap scope.\n\n"
        "00:01:00.000 --> 00:01:20.000\n"
        "<v Jordan Lee>I propose a recap only when money moves.\n\n"
        "00:03:00.000 --> 00:05:00.000\n"
        "<v Maya Ortiz>Responses stay grounded in customer statements and records.\n"
    )
    second_path = session_dir / "2026-04-08_calibration.vtt"
    second_path.write_text(
        "WEBVTT\n\n"
        "00:00:00.000 --> 00:00:20.000\n"
        "<v Jordan Lee>Let's revisit the recap proposal.\n\n"
        "00:02:00.000 --> 00:02:20.000\n"
        "<v Maya Ortiz>Address changes show money is the wrong boundary.\n\n"
        "00:03:00.000 --> 00:05:00.000\n"
        "<v Jordan Lee>Every record change gets a recap and confirmation.\n"
    )
    manifest_path = session_dir / "eval_manifest.json"
    manifest = {
        "meetings": [
            {
                "meeting_id": "intake",
                "filename": first_path.name,
                "date": "2026-04-01",
                "authoritative_fact_ids": ["F2"],
            },
            {
                "meeting_id": "calibration",
                "filename": second_path.name,
                "date": "2026-04-08",
                "authoritative_fact_ids": ["F1"],
            },
        ],
        "authoritative_fact_ids": ["F1", "F2"],
        "decisions": [
            {
                "fact_id": "F1",
                "status": "proposal",
                "meeting_id": "intake",
                "timestamp": "00:01:00.000",
            },
            {
                "fact_id": "F2",
                "status": "final_current",
                "meeting_id": "intake",
                "timestamp": "00:03:00.000",
                "evidence_spans": [
                    {
                        "meeting_id": "intake",
                        "start": "00:03:00.000",
                        "end": "00:05:00.000",
                    }
                ],
            },
            {
                "fact_id": "F1",
                "status": "final_current",
                "meeting_id": "calibration",
                "timestamp": "00:03:00.000",
                "evidence_spans": [
                    {
                        "meeting_id": "calibration",
                        "start": "00:02:00.000",
                        "end": "00:05:00.000",
                    }
                ],
            },
        ],
    }
    manifest_path.write_text(json.dumps(manifest))
    schema = {
        "id": "service_foundations_schema",
        "facts": [
            {"id": "F1", "statement": "Recap changes before submission."},
            {"id": "F2", "statement": "Ground responses in records."},
        ],
    }
    spec = {
        "representation": "recorded_working_session",
        "eval_manifest_path": str(manifest_path),
        "minimum_meetings": 2,
        "artifacts": [
            {
                "path": str(first_path),
                "kit_filename": first_path.name,
                "meeting_id": "intake",
                "meeting_date": "2026-04-01",
                "minimum_duration_minutes": 4,
                "maximum_duration_minutes": 6,
                "minimum_speakers": 2,
                "included_fact_ids": ["F2"],
            },
            {
                "path": str(second_path),
                "kit_filename": second_path.name,
                "meeting_id": "calibration",
                "meeting_date": "2026-04-08",
                "minimum_duration_minutes": 4,
                "maximum_duration_minutes": 6,
                "minimum_speakers": 2,
                "included_fact_ids": ["F1"],
            },
        ],
    }
    transformation = get_transformation("recorded_working_session")
    artifacts = transformation.discover_artifacts(
        schema, session_dir / "schema.json", spec
    )

    assert transformation.validate(schema, artifacts) == []
    assert transformation.covered_fact_ids(schema, artifacts) == {"F1", "F2"}
    assert transformation.neutralize(artifacts[1], 2).relative_path == (
        "uploaded_materials/2026-04-08_calibration.vtt"
    )

    manifest["decisions"][-1].pop("evidence_spans")
    manifest_path.write_text(json.dumps(manifest))
    assert (
        "eval_manifest.json: final decision 3 needs evidence_spans"
        in transformation.validate(schema, artifacts)
    )


def test_email_thread_archive_resolves_entry_manifest_and_requires_histories(
    tmp_path,
    monkeypatch,
):
    data_dir = tmp_path / "data"
    archive_dir = data_dir / "archive"
    archive_dir.mkdir(parents=True)
    email_path = archive_dir / "scope_review.eml"
    email_path.write_text(
        "From: Pat Lee <pat@example.com>\n"
        "To: Alex Kim <alex@example.com>\n"
        "Date: Tue, 7 Apr 2026 10:00:00 -0700\n"
        "Subject: RE: Scope review\n"
        "Message-ID: <message-4@example.com>\n"
        "MIME-Version: 1.0\n"
        "Content-Type: text/plain; charset=UTF-8\n"
        "Thread-Topic: Scope review\n"
        "Thread-Index: AQHscope-review-thread\n"
        "\n"
        "The current list is complete.\n\n"
        "-----Original Message-----\nEarlier note 3.\n\n"
        "-----Original Message-----\nEarlier note 2.\n\n"
        "-----Original Message-----\nEarlier note 1.\n"
    )
    manifest_path = archive_dir / "eval_manifest.json"
    manifest = {
        "thread_count": 1,
        "threads": [
            {
                "filename": "scope_review.eml",
                "authoritative_fact_ids": ["F1"],
            }
        ],
    }
    manifest_path.write_text(json.dumps(manifest))
    monkeypatch.setattr(email_threads_module, "DATA_DIR", data_dir)

    schema = {
        "id": "scope_schema",
        "facts": [{"id": "F1", "statement": "The list is complete."}],
    }
    spec = {
        "representation": "email_thread_archive",
        "artifacts": [
            {
                "path": "archive/scope_review.eml",
                "kit_filename": "scope_review.eml",
                "eval_manifest_path": "archive/eval_manifest.json",
                "included_fact_ids": ["F1"],
            }
        ],
    }
    transformation = get_transformation("email_thread_archive")
    (artifact,) = transformation.discover_artifacts(
        schema, data_dir / "schema.json", spec
    )

    assert artifact.metadata["eval_manifest_path"] == manifest_path
    assert transformation.validate(schema, [artifact]) == []
    assert "The current list is complete." in transformation.to_text(artifact)
    kit_file = transformation.neutralize(artifact, 1)
    assert kit_file.relative_path == "uploaded_materials/scope_review.eml"
    assert kit_file.content == email_path.read_bytes()
    assert b"F1" not in kit_file.content

    manifest["threads"][0]["historical_fact_ids"] = ["F0"]
    manifest_path.write_text(json.dumps(manifest))
    assert (
        "email archive scope_change_histories is required when threads "
        "declare historical_fact_ids"
    ) in transformation.validate(schema, [artifact])


def test_email_scope_histories_allow_dates_declared_only_on_events():
    manifest_threads = [
        {
            "filename": "superseded.eml",
            "historical_fact_ids": ["F1"],
        },
        {
            "filename": "current.eml",
            "authoritative_fact_ids": ["F1"],
        },
    ]
    histories = {
        "F1": [
            {
                "thread": "superseded.eml",
                "status": "superseded",
                "decision_date": "2026-04-01",
            },
            {
                "thread": "current.eml",
                "status": "final_current",
                "decision_date": "2026-04-02",
            },
        ]
    }

    assert (
        email_threads_module.EmailThreadArchiveTransformation._validate_scope_histories(
            histories, manifest_threads
        )
        == []
    )

    manifest_threads[0]["decision_date"] = "2026-04-03"
    assert (
        "scope history 'F1' decision date does not match thread 'superseded.eml'"
        in email_threads_module.EmailThreadArchiveTransformation._validate_scope_histories(
            histories, manifest_threads
        )
    )


def test_slack_mcp_dump_validates_tool_calls_and_keeps_fact_labels_author_side(
    tmp_path,
):
    section_dir = tmp_path / "sections" / "modification"
    section_dir.mkdir(parents=True)

    def message(thread_ordinal: int, reply: bool) -> dict[str, object]:
        root_ts = f"177000000{thread_ordinal}.000000"
        ts = root_ts if not reply else f"177000001{thread_ordinal}.000000"
        return {
            "channel_id": "C01TEST",
            "channel_name": "proj-test",
            "ts": ts,
            "thread_ts": root_ts,
            "user_id": "U01TEST",
            "text": "Current decision." if thread_ordinal == 4 else "Working note.",
            "permalink": f"https://workspace.slack.com/archives/C01TEST/p{ts}",
        }

    calls = []
    for ordinal in range(1, 5):
        calls.append(
            {
                "call_id": f"call_{ordinal:03d}",
                "request": {
                    "method": "tools/call",
                    "params": {
                        "name": "slack_get_thread_replies",
                        "arguments": {
                            "channel_id": "C01TEST",
                            "thread_ts": f"177000000{ordinal}.000000",
                        },
                    },
                },
                "response": {
                    "is_error": False,
                    "structured_content": {
                        "messages": [
                            message(ordinal, False),
                            message(ordinal, True),
                        ]
                    },
                },
            }
        )
    capture_path = section_dir / "slack_capture.json"
    capture_path.write_text(
        json.dumps(
            {
                "capture_format": "slack_mcp_tool_call_log",
                "server": "slack",
                "tool_calls": calls,
            }
        )
    )
    manifest_path = section_dir / "eval_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "artifacts": [
                    {
                        "filename": "slack_capture.json",
                        "authoritative_fact_ids": ["F1"],
                    }
                ],
                "decision_history": [
                    {
                        "status": "superseded",
                        "decision_timestamp": "2026-03-01T10:00:00Z",
                    },
                    {
                        "status": "final_current",
                        "decision_timestamp": "2026-03-02T10:00:00Z",
                        "authoritative_fact_ids": ["F1"],
                    },
                ],
            }
        )
    )
    schema = {
        "id": "modification_schema",
        "facts": [{"id": "F1", "statement": "Current decision."}],
        "transformations": [
            {
                "representation": "slack_mcp_dump",
                "eval_manifest_path": str(manifest_path),
                "artifacts": [
                    {
                        "path": str(capture_path),
                        "kit_filename": "slack_capture.json",
                        "included_fact_ids": ["F1"],
                    }
                ],
            }
        ],
    }
    transformation = get_transformation("slack_mcp_dump")
    (artifact,) = transformation.discover_artifacts(
        schema, section_dir / "schema.json", schema["transformations"][0]
    )

    assert transformation.validate(schema, [artifact]) == []
    assert "Current decision." in transformation.to_text(artifact)
    kit_file = transformation.neutralize(artifact, 1)
    assert kit_file.relative_path == "uploaded_materials/slack_capture.json"
    assert kit_file.content == capture_path.read_bytes()
    assert b"F1" not in kit_file.content

    malformed_capture = json.loads(capture_path.read_text())
    malformed_capture["tool_calls"][0]["response"]["structured_content"]["messages"][
        0
    ] = None
    issues = transformation._validate_capture("slack_capture.json", malformed_capture)
    assert "slack_capture.json: call_001 contains a non-object message" in issues

    empty_capture = json.loads(capture_path.read_text())
    empty_capture["tool_calls"][0]["response"]["structured_content"]["messages"] = []
    issues = transformation._validate_capture("slack_capture.json", empty_capture)
    assert "slack_capture.json: call_001 thread fetch must contain messages" in issues
    assert "slack_capture.json: Slack MCP dump must include at least four threads" in (
        issues
    )

    mixed_timestamp_manifest = json.loads(manifest_path.read_text())
    mixed_timestamp_manifest["decision_history"][0]["decision_timestamp"] = (
        "2026-03-01T10:00:00"
    )
    manifest_path.write_text(json.dumps(mixed_timestamp_manifest))
    assert (
        "Slack MCP decision_history timestamps must include timezone offsets"
        in transformation.validate(schema, [artifact])
    )


# ---------------------------------------------------------------------------
# Transformation resolution from schemas
# ---------------------------------------------------------------------------


def test_legacy_schema_synthesizes_transcript_transformation():
    schema = {
        "id": "s1",
        "rendered_section_path": "tau2/hyper/sops/x/sections/a/stub.md",
        "transcripts": [],
    }
    transformations = resolve_section_transformations(schema)
    assert transformations == [
        {
            "representation": "support_transcripts",
            "stub_path": "tau2/hyper/sops/x/sections/a/stub.md",
            "artifacts": None,
        }
    ]


def test_explicit_transformations_selected_by_active_stub_path():
    schema = {
        "id": "s1",
        "transformations": [
            {"representation": "support_transcripts", "stub_path": "a/transcripts.md"},
            {"representation": "process_flowchart", "stub_path": "a/flowchart.md"},
        ],
    }
    assert (
        select_section_transformation(schema, "a/flowchart.md")["representation"]
        == "process_flowchart"
    )
    # Unknown or missing stub path falls back to the first declared transformation.
    assert (
        select_section_transformation(schema, "a/other.md")["representation"]
        == "support_transcripts"
    )
    assert (
        select_section_transformation(schema)["representation"] == "support_transcripts"
    )


def test_schema_loads_transformations_and_bundles_from_external_pack(tmp_path):
    pack_path = tmp_path / "hard_pack.json"
    pack_path.write_text(
        json.dumps(
            {
                "section_id": "s1",
                "transformations": [
                    {
                        "id": "imported_records",
                        "representation": "support_transcripts",
                        "stub_path": "a/hard.md",
                    }
                ],
                "transformation_bundles": [{"id": "imported_bundle", "members": []}],
            }
        )
    )
    schema = {
        "section_id": "s1",
        "transformations": [
            {"id": "current_records", "representation": "support_transcripts"}
        ],
        "transformation_bundles": [{"id": "current_bundle", "members": []}],
        "transformation_imports": [{"path": str(pack_path)}],
    }

    assert [
        transformation["id"]
        for transformation in resolve_section_transformations(schema)
    ] == ["current_records", "imported_records"]
    assert [bundle["id"] for bundle in resolve_transformation_bundles(schema)] == [
        "current_bundle",
        "imported_bundle",
    ]


def test_schema_rejects_external_pack_for_another_section(tmp_path):
    pack_path = tmp_path / "wrong_section.json"
    pack_path.write_text(json.dumps({"section_id": "s2", "transformations": []}))
    schema = {
        "section_id": "s1",
        "transformation_imports": [{"path": str(pack_path)}],
    }

    with pytest.raises(ValueError, match="targets section 's2', not 's1'"):
        resolve_section_transformations(schema)


def test_schema_without_transformations_raises():
    with pytest.raises(ValueError, match="declares no transformations"):
        select_section_transformation({"id": "bare"})


# ---------------------------------------------------------------------------
# Process-flowchart transformation
# ---------------------------------------------------------------------------


def test_process_flowchart_keeps_editable_source_author_side(tmp_path):
    section_dir = tmp_path / "sections" / "booking"
    source_dir = section_dir / "process_flowchart_001"
    source_dir.mkdir(parents=True)
    image_path = source_dir / "booking_map.png"
    image_bytes = b"\x89PNG\r\n\x1a\nprocess map bytes"
    image_path.write_bytes(image_bytes)
    text_path = source_dir / "booking_map.txt"
    text_path.write_text(
        "Identify customer -> collect trip details -> find available flights.\n"
        "Trip type is one-way or round-trip. Options may be direct or one-stop.\n"
    )
    html_path = source_dir / "booking_map.html"
    html_path.write_text("<html><body>editable source</body></html>\n")
    stub_path = section_dir / "flowchart_bundle.md"
    stub_path.write_text("Reference process maps are in `uploaded_materials/`.\n")
    schema = {
        "id": "booking_schema",
        "facts": [
            {"id": "sequence", "statement": "Follow the booking sequence."},
            {"id": "trip_types", "statement": "Support one-way and round-trip."},
        ],
        "transformations": [
            {
                "representation": "process_flowchart",
                "stub_path": str(stub_path),
                "artifacts": [
                    {
                        "path": str(image_path),
                        "kit_filename": "new_booking_process_map.png",
                        "text_source_path": str(text_path),
                        "author_source_path": str(html_path),
                        "included_fact_ids": ["sequence", "trip_types"],
                    }
                ],
            }
        ],
    }
    schema_path = section_dir / "schema.json"
    schema_path.write_text(json.dumps(schema))

    transformation = get_transformation("process_flowchart")
    (artifact,) = transformation.discover_artifacts(
        schema, schema_path, schema["transformations"][0]
    )
    assert transformation.validate(schema, [artifact]) == []
    assert "one-way or round-trip" in transformation.to_text(artifact)
    kit_file = transformation.neutralize(artifact, 9)
    assert kit_file.relative_path == "uploaded_materials/new_booking_process_map.png"
    assert kit_file.content == image_bytes

    manifest = {
        "id": "process_flowchart_variant",
        "section_source_schemas": {"booking": str(schema_path)},
        "section_replacements": {"booking": str(stub_path)},
    }
    kit_dir = tmp_path / "kit"
    kit_dir.mkdir()
    _copy_sop_variant_materials(manifest, kit_dir)
    assert (
        kit_dir / "uploaded_materials" / "process_map.png"
    ).read_bytes() == image_bytes
    assert list(kit_dir.rglob("*.html")) == []
    assert list(kit_dir.rglob("*.txt")) == []


def test_process_flowchart_html_source_has_safe_text_rendition(tmp_path):
    image_path = tmp_path / "account_flow.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nprocess map bytes")
    html_path = tmp_path / "account_flow.html"
    html_path.write_text(
        """
        <html>
          <style>.hidden { content: "author scaffolding"; }</style>
          <body>
            <h1>Account opening</h1>
            <p>Verify the customer, then submit the application.</p>
          </body>
        </html>
        """
    )
    schema = {
        "id": "account_opening",
        "facts": [{"id": "sequence", "statement": "Verify before opening."}],
        "transformations": [
            {
                "representation": "process_flowchart",
                "stub_path": str(tmp_path / "stub.md"),
                "artifacts": [
                    {
                        "path": str(image_path),
                        "text_source_path": str(html_path),
                        "included_fact_ids": ["sequence"],
                    }
                ],
            }
        ],
    }
    transformation = get_transformation("process_flowchart")
    (artifact,) = transformation.discover_artifacts(
        schema, tmp_path / "schema.json", schema["transformations"][0]
    )

    kit_file = transformation.deliver(artifact, 1, parse_modality_profile("text"))

    assert kit_file.relative_path == "uploaded_materials/account_flow.txt"
    rendered = kit_file.content.decode()
    assert "Account opening" in rendered
    assert "Verify the customer" in rendered
    assert "author scaffolding" not in rendered
    assert "<html>" not in rendered
    assert transformation.to_text(artifact) == rendered


# ---------------------------------------------------------------------------
# Process-presentation transformation
# ---------------------------------------------------------------------------


def test_process_presentation_keeps_author_material_out_of_kit(tmp_path):
    section_dir = tmp_path / "sections" / "cancellation"
    source_dir = section_dir / "process_presentation_001"
    source_dir.mkdir(parents=True)
    pdf_path = source_dir / "operations_workbook.pdf"
    pdf_bytes = b"%PDF-1.4\nfictional process presentation\n"
    pdf_path.write_bytes(pdf_bytes)
    text_path = source_dir / "operations_workbook.txt"
    text_path.write_text(
        "Page 2: identify the reservation and ask the cancellation reason.\n"
        "Page 3: return refunds to the original payment methods.\n"
    )
    pptx_path = source_dir / "operations_workbook.pptx"
    pptx_path.write_bytes(b"author-side editable source")
    generator_path = source_dir / "build_deck.mjs"
    generator_path.write_text("export function buildDeck() {}\n")
    eval_manifest_path = source_dir / "eval_manifest.json"
    eval_manifest_path.write_text(
        json.dumps(
            {
                "page_fact_ids": [
                    {"page": 2, "fact_ids": ["identify"]},
                    {"page": 3, "fact_ids": ["refund"]},
                ],
                "authoritative_facts": [
                    {"id": "identify", "page": 2},
                    {"id": "refund", "page": 3},
                ],
            }
        )
    )
    stub_path = source_dir / "stub.md"
    stub_path.write_text("Reference `uploaded_materials/operations_workbook.pdf`.\n")
    schema = {
        "id": "cancellation_schema",
        "facts": [
            {"id": "identify", "statement": "Identify the reservation."},
            {"id": "refund", "statement": "Refund the original methods."},
        ],
        "transformations": [
            {
                "representation": "process_presentation",
                "stub_path": str(stub_path),
                "artifacts": [
                    {
                        "path": str(pdf_path),
                        "kit_filename": "cancellation_operations.pdf",
                        "text_source_path": str(text_path),
                        "author_source_path": str(pptx_path),
                        "generation_source_path": str(generator_path),
                        "eval_manifest_path": str(eval_manifest_path),
                        "page_fact_ids": [
                            {"page": 2, "fact_ids": ["identify"]},
                            {"page": 3, "fact_ids": ["refund"]},
                        ],
                        "included_fact_ids": ["identify", "refund"],
                    }
                ],
            }
        ],
    }
    schema_path = section_dir / "schema.json"
    schema_path.write_text(json.dumps(schema))

    transformation = get_transformation("process_presentation")
    (artifact,) = transformation.discover_artifacts(
        schema, schema_path, schema["transformations"][0]
    )
    assert transformation.validate(schema, [artifact]) == []
    assert "original payment methods" in transformation.to_text(artifact)
    kit_file = transformation.neutralize(artifact, 4)
    assert kit_file.relative_path == "uploaded_materials/cancellation_operations.pdf"
    assert kit_file.content == pdf_bytes

    manifest = {
        "id": "process_presentation_variant",
        "section_source_schemas": {"cancellation": str(schema_path)},
        "section_replacements": {"cancellation": str(stub_path)},
    }
    kit_dir = tmp_path / "kit"
    kit_dir.mkdir()
    _copy_sop_variant_materials(manifest, kit_dir)
    assert (kit_dir / "uploaded_materials" / "slide_deck.pdf").read_bytes() == pdf_bytes
    assert list(kit_dir.rglob("*.pptx")) == []
    assert list(kit_dir.rglob("*.mjs")) == []
    assert list(kit_dir.rglob("*.txt")) == []
    assert list(kit_dir.rglob("eval_manifest.json")) == []


# ---------------------------------------------------------------------------
# Device-UI-screenshot transformation
# ---------------------------------------------------------------------------


def test_device_ui_screenshot_is_text_auditable_and_requires_reference_metadata(
    tmp_path,
):
    section_dir = tmp_path / "sections" / "mms"
    source_dir = section_dir / "device_ui_screenshot_001"
    source_dir.mkdir(parents=True)
    image_path = source_dir / "wifi_calling.png"
    image_bytes = b"\x89PNG\r\n\x1a\ndevice screenshot bytes"
    image_path.write_bytes(image_bytes)
    html_path = source_dir / "wifi_calling.html"
    html_path.write_text(
        """
        <html>
          <style>.hidden { content: "not visible"; }</style>
          <body>
            <h1>Wi-Fi Calling</h1>
            <p>If it is on, turn it off and retry MMS.</p>
          </body>
        </html>
        """
    )
    schema = {
        "id": "mms_schema",
        "facts": [{"id": "wifi", "statement": "Turn off Wi-Fi Calling."}],
        "transformations": [
            {
                "representation": "device_ui_screenshot",
                "artifacts": [
                    {
                        "path": str(image_path),
                        "text_source_path": str(html_path),
                        "platform": "cross_platform",
                        "reference_id": "MMS-215",
                        "included_fact_ids": ["wifi"],
                    }
                ],
            }
        ],
    }
    transformation = get_transformation("device_ui_screenshot")
    (artifact,) = transformation.discover_artifacts(
        schema, section_dir / "schema.json", schema["transformations"][0]
    )

    assert transformation.validate(schema, [artifact]) == []
    assert "turn it off and retry MMS" in transformation.to_text(artifact)
    kit_file = transformation.neutralize(artifact, 2)
    assert kit_file.relative_path == "uploaded_materials/device_screen_002.png"
    assert kit_file.content == image_bytes
    assert kit_file.preserve_filename is False

    artifact.metadata["kit_filename"] = "device_capture_02.png"
    stable_kit_file = transformation.neutralize(artifact, 2)
    assert stable_kit_file.relative_path == "uploaded_materials/device_capture_02.png"
    assert stable_kit_file.preserve_filename is True
    assert transformation.validate(schema, [artifact]) == []
    artifact.metadata.pop("kit_filename")

    artifact.metadata.pop("reference_id")
    assert "wifi_calling.png: reference_id is required" in transformation.validate(
        schema, [artifact]
    )
    artifact.metadata["reference_id"] = "MMS-215"
    artifact.metadata["platform"] = "windows_phone"
    assert any(
        "platform must be one of" in issue
        for issue in transformation.validate(schema, [artifact])
    )
    artifact.metadata["platform"] = "cross_platform"
    assert (
        "wifi_calling.png: duplicate reference_id 'MMS-215'"
        in transformation.validate(schema, [artifact, artifact])
    )


# ---------------------------------------------------------------------------
# Website-screenshot transformation
# ---------------------------------------------------------------------------


def test_website_screenshot_is_text_auditable_and_kit_only_gets_png(tmp_path):
    section_dir = tmp_path / "sections" / "booking"
    source_dir = section_dir / "website_screenshot_001"
    source_dir.mkdir(parents=True)
    image_path = source_dir / "checkout.png"
    image_bytes = b"\x89PNG\r\n\x1a\nwebsite screenshot bytes"
    image_path.write_bytes(image_bytes)
    html_path = source_dir / "checkout.html"
    html_path.write_text(
        """
        <html>
          <style>.hidden { content: "not visible"; }</style>
          <body>
            <h1>Travel protection</h1>
            <p>$30 per passenger</p>
            <p>Full refund for cancellation due to health or weather.</p>
          </body>
        </html>
        """
    )
    stub_path = section_dir / "website_screenshot_001.md"
    stub_path.write_text("Reference screenshots are in `uploaded_materials/`.\n")
    schema = {
        "id": "booking_schema",
        "facts": [
            {
                "id": "insurance",
                "statement": "Insurance is $30 and covers health or weather.",
            }
        ],
        "transformations": [
            {
                "representation": "website_screenshot",
                "stub_path": str(stub_path),
                "artifacts": [
                    {
                        "path": str(image_path),
                        "text_source_path": str(html_path),
                        "included_fact_ids": ["insurance"],
                    }
                ],
            }
        ],
    }
    schema_path = section_dir / "schema.json"
    schema_path.write_text(json.dumps(schema))

    transformation = get_transformation("website_screenshot")
    (artifact,) = transformation.discover_artifacts(
        schema, schema_path, schema["transformations"][0]
    )
    assert transformation.validate(schema, [artifact]) == []
    extracted = transformation.to_text(artifact)
    assert "$30 per passenger" in extracted
    assert "health or weather" in extracted
    assert "not visible" not in extracted
    kit_file = transformation.neutralize(artifact, 7)
    assert kit_file.relative_path == "uploaded_materials/screen_007.png"
    assert kit_file.content == image_bytes

    manifest = {
        "id": "website_screenshot_variant",
        "section_source_schemas": {"booking": str(schema_path)},
        "section_replacements": {"booking": str(stub_path)},
    }
    kit_dir = tmp_path / "kit"
    kit_dir.mkdir()
    _copy_sop_variant_materials(manifest, kit_dir)
    assert (
        kit_dir / "uploaded_materials" / "screenshot.png"
    ).read_bytes() == image_bytes
    assert list(kit_dir.rglob("*.html")) == []
    assert list(kit_dir.rglob("*.json")) == []


# ---------------------------------------------------------------------------
# Transcript transformation
# ---------------------------------------------------------------------------


def _write_transcript_section(
    section_dir: Path, fact_ids: list[str], covered: list[list[str]]
) -> Path:
    """Create a minimal legacy transcript section; returns the schema path."""
    records_dir = section_dir / "training_records"
    records_dir.mkdir(parents=True)
    plans = []
    for index, included in enumerate(covered):
        plan_id = chr(ord("A") + index)
        plans.append({"id": plan_id, "included_fact_ids": included})
        (records_dir / f"case_{index + 1:03d}.md").write_text(
            f"# Case {plan_id}\n\n**Customer:** Hello.\n\n**Agent:** Hi.\n"
        )
    stub_path = section_dir / "transcript_induction_001.md"
    stub_path.write_text("Approved case records are in `uploaded_materials/`.\n")
    schema = {
        "id": f"{section_dir.name}_schema",
        "rendered_section_path": str(stub_path),
        "facts": [{"id": fact_id, "statement": fact_id} for fact_id in fact_ids],
        "transcripts": plans,
    }
    schema_path = section_dir / "schema.json"
    schema_path.write_text(json.dumps(schema))
    return schema_path


def test_transcript_coverage_gap_falls_back_to_explicit_rules(tmp_path):
    schema_path = _write_transcript_section(
        tmp_path / "sections" / "gaps", ["F1", "F2"], [["F1"]]
    )
    manifest = {
        "id": "variant_gaps",
        "section_source_schemas": {"gaps": str(schema_path)},
    }
    kit_dir = tmp_path / "kit"
    _copy_sop_variant_materials(manifest, kit_dir)
    # Uncovered F2 is routed into the fallback appendix, not an error.
    notes = (kit_dir / "additional_policy_notes.md").read_text()
    assert "- F2" in notes and "- F1" not in notes
    report = json.loads((tmp_path / "kit.transformation_report.json").read_text())
    assert report["totals"] == {
        "facts": 2,
        "covered": 1,
        "uncovered": 1,
        "multiply_represented": 0,
    }
    assert report["warnings"]


def test_transcript_coverage_gap_errors_under_strict_policy(tmp_path):
    schema_path = _write_transcript_section(
        tmp_path / "sections" / "gaps", ["F1", "F2"], [["F1"]]
    )
    manifest = {
        "id": "variant_gaps_strict",
        "section_source_schemas": {"gaps": str(schema_path)},
        "uncovered_fact_policy": "error",
    }
    with pytest.raises(ValueError, match=r"not covered.*F2"):
        _copy_sop_variant_materials(manifest, tmp_path / "kit")


def test_transcripts_pool_and_renumber_across_sections(tmp_path):
    schema_one = _write_transcript_section(
        tmp_path / "sections" / "one", ["F1"], [["F1"], ["F1"]]
    )
    schema_two = _write_transcript_section(
        tmp_path / "sections" / "two", ["G1"], [["G1"]]
    )
    manifest = {
        "id": "variant_pool",
        "section_source_schemas": {"one": str(schema_one), "two": str(schema_two)},
    }
    kit_dir = tmp_path / "kit"
    kit_dir.mkdir()
    created = _copy_sop_variant_materials(manifest, kit_dir)
    records = sorted(p.name for p in (kit_dir / "uploaded_materials").iterdir())
    assert records == ["case_file_01.md", "case_file_02.md", "case_file_03.md"]
    headings = set()
    for name in records:
        text = (kit_dir / "uploaded_materials" / name).read_text()
        headings.add(text.splitlines()[0])
        assert "Case A" not in text and "Case B" not in text
    assert headings == {"# Case 001", "# Case 002", "# Case 003"}
    assert created == [kit_dir / "uploaded_materials"]


def test_unknown_manifest_representation_fails_kit_build(tmp_path):
    schema_path = _write_transcript_section(
        tmp_path / "sections" / "one", ["F1"], [["F1"]]
    )
    manifest = {
        "id": "variant_bad_rep",
        "section_source_schemas": {"one": str(schema_path)},
        "information_distribution": {"representation": "interpretive_dance"},
    }
    with pytest.raises(ValueError, match="interpretive_dance"):
        _copy_sop_variant_materials(manifest, tmp_path / "kit")


# ---------------------------------------------------------------------------
# client_knowledge: nothing enters the kit
# ---------------------------------------------------------------------------


def _write_client_bundle_section(section_dir: Path) -> Path:
    """A section splitting facts between transcripts and the Client."""
    records_dir = section_dir / "training_records"
    records_dir.mkdir(parents=True)
    (records_dir / "case_001.md").write_text(
        "# Case A\n\n**Customer:** Hello.\n\n**Agent:** Hi.\n"
    )
    (records_dir / "case_002.md").write_text(
        "# Case B\n\n**Customer:** Hello.\n\n**Agent:** Hi again.\n"
    )
    stub_path = section_dir / "stub.md"
    stub_path.write_text("Approved case records are in `uploaded_materials/`.\n")
    schema = {
        "id": f"{section_dir.name}_schema",
        "facts": [
            {"id": "F1", "statement": "Rule one."},
            {"id": "F2", "statement": "Rule two, held by the Client."},
        ],
        "transformations": [
            {
                "id": "records",
                "representation": "support_transcripts",
                "stub_path": str(stub_path),
                "artifacts": [
                    {
                        "path": str(records_dir / "case_001.md"),
                        "included_fact_ids": ["F1"],
                    }
                ],
            },
            {
                "id": "held",
                "representation": "client_knowledge",
                "stub_path": str(stub_path),
                "fact_ids": ["F2"],
            },
            {
                "id": "records_all",
                "representation": "support_transcripts",
                "stub_path": str(stub_path),
                "artifacts": [
                    {
                        "path": str(records_dir / "case_002.md"),
                        "included_fact_ids": ["F1", "F2"],
                    }
                ],
            },
        ],
        "transformation_bundles": [
            {
                "id": "records_plus_client",
                "stub_path": str(stub_path),
                "fact_ids": ["F1", "F2"],
                "client_overlay_of": "records_base",
                "member_substitutions": {"records_all": "records"},
                "members": [
                    {
                        "transformation_id": "records",
                        "primary": True,
                        "authoritative_fact_ids": ["F1"],
                    },
                    {
                        "transformation_id": "held",
                        "authoritative_fact_ids": ["F2"],
                    },
                ],
            },
            {
                "id": "records_base",
                "stub_path": str(stub_path),
                "fact_ids": ["F1", "F2"],
                "members": [
                    {
                        "transformation_id": "records_all",
                        "primary": True,
                        "authoritative_fact_ids": ["F1", "F2"],
                    },
                ],
            },
        ],
    }
    schema_path = section_dir / "schema.json"
    schema_path.write_text(json.dumps(schema))
    return schema_path


def test_client_knowledge_materializes_nothing_and_skips_fallback(tmp_path):
    schema_path = _write_client_bundle_section(tmp_path / "sections" / "scope")
    manifest = {
        "id": "variant_client_held",
        "section_source_schemas": {"scope": str(schema_path)},
        "section_bundles": {"scope": "records_plus_client"},
    }
    kit_dir = tmp_path / "kit"
    _copy_sop_variant_materials(manifest, kit_dir, client_sections=["scope"])
    uploads = sorted(p.name for p in (kit_dir / "uploaded_materials").iterdir())
    assert uploads == ["case_file.md"]
    # The client-held fact reaches neither an upload nor the fallback notes.
    assert not (kit_dir / "additional_policy_notes.md").exists()
    for path in kit_dir.rglob("*"):
        if path.is_file():
            assert "Rule two" not in path.read_text()
    report = json.loads((tmp_path / "kit.transformation_report.json").read_text())
    assert report["totals"]["uncovered"] == 0


def test_client_knowledge_requires_matching_client_sections(tmp_path):
    schema_path = _write_client_bundle_section(tmp_path / "sections" / "scope")
    manifest = {
        "id": "variant_client_held",
        "section_source_schemas": {"scope": str(schema_path)},
        "section_bundles": {"scope": "records_plus_client"},
    }
    with pytest.raises(ValueError, match=r"unlearnable"):
        _copy_sop_variant_materials(manifest, tmp_path / "kit")


def test_client_knowledge_to_text_renders_held_statements(tmp_path):
    schema_path = _write_client_bundle_section(tmp_path / "sections" / "scope")
    schema = json.loads(schema_path.read_text())
    transformation = get_transformation("client_knowledge")
    artifacts = transformation.discover_artifacts(
        schema, schema_path, schema["transformations"][1]
    )
    assert [a.included_fact_ids for a in artifacts] == [["F2"]]
    text = transformation.to_text(artifacts[0])
    assert "Rule two, held by the Client." in text
    assert "Rule one." not in text
    with pytest.raises(NotImplementedError):
        transformation.neutralize(artifacts[0], 1)
