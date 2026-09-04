"""Tests for variant compilation: coverage, overlap, fallback, reports."""

import json
from pathlib import Path

import pytest

from tau2.hyper.transformations import (
    compile_variant_transformations,
    render_fallback_markdown,
)
from tau2.hyper.transformations.sop_variants import (
    _bundle_section_replacements,
    assemble_sop_variant,
)


def _write_section(
    section_dir: Path,
    facts: list[str],
    *,
    transcript_covered: list[list[str]] | None = None,
    document_covered: list[str] | None = None,
) -> Path:
    """Write a section schema declaring transcript and/or document transformations."""
    section_dir.mkdir(parents=True)
    transformations = []

    if transcript_covered is not None:
        records_dir = section_dir / "training_records"
        records_dir.mkdir()
        artifacts = []
        for index, included in enumerate(transcript_covered):
            record_path = records_dir / f"case_{index + 1:03d}.md"
            record_path.write_text(
                f"# Case {chr(ord('A') + index)}\n\n**Agent:** Hi.\n"
            )
            artifacts.append({"path": str(record_path), "included_fact_ids": included})
        stub_path = section_dir / "transcript_induction_001.md"
        stub_path.write_text("Case records are in `uploaded_materials/`.\n")
        transformations.append(
            {
                "representation": "support_transcripts",
                "stub_path": str(stub_path),
                "artifacts": artifacts,
            }
        )

    if document_covered is not None:
        document_path = section_dir / "operating_reference.md"
        document_path.write_text(
            "# Operating reference\n\nApproved operating guidance.\n"
        )
        stub_path = section_dir / "customer_kickoff_document_001.md"
        stub_path.write_text("The operating reference is in `uploaded_materials/`.\n")
        transformations.append(
            {
                "representation": "customer_kickoff_document",
                "stub_path": str(stub_path),
                "artifacts": [
                    {
                        "path": str(document_path),
                        "kit_filename": f"{section_dir.name}_reference.md",
                        "included_fact_ids": document_covered,
                    }
                ],
            }
        )

    schema = {
        "id": f"{section_dir.name}_schema",
        "facts": [{"id": f, "statement": f"Statement for {f}."} for f in facts],
        "transformations": transformations,
    }
    schema_path = section_dir / "schema.json"
    schema_path.write_text(json.dumps(schema))
    return schema_path


def test_full_coverage_compiles_clean(tmp_path):
    schema = _write_section(
        tmp_path / "s1", ["F1", "F2"], transcript_covered=[["F1"], ["F2"]]
    )
    compilation = compile_variant_transformations(
        {"id": "v", "section_source_schemas": {"s1": str(schema)}}
    )
    assert compilation.errors == []
    assert compilation.warnings == []
    assert compilation.uncovered_facts == []
    assert [a.representation for a in compilation.activations] == [
        "support_transcripts"
    ]
    report = compilation.report()
    assert report["totals"] == {
        "facts": 2,
        "covered": 2,
        "uncovered": 0,
        "multiply_represented": 0,
    }


def test_journey_inherits_global_facts_without_representing_them_again(tmp_path):
    identity_schema_path = _write_section(
        tmp_path / "identity",
        ["G1"],
        transcript_covered=[["G1"]],
    )
    identity_schema = json.loads(identity_schema_path.read_text())
    identity_schema["domain_hierarchy"] = {"role": "global_prerequisite"}
    identity_schema_path.write_text(json.dumps(identity_schema))

    booking_schema_path = _write_section(
        tmp_path / "booking",
        ["B1"],
        transcript_covered=[["B1"]],
    )
    booking_schema = json.loads(booking_schema_path.read_text())
    booking_schema["domain_hierarchy"] = {
        "role": "journey",
        "requires": [{"section_id": "identity", "fact_ids": ["G1"]}],
    }
    booking_schema_path.write_text(json.dumps(booking_schema))

    compilation = compile_variant_transformations(
        {
            "id": "global_dependency",
            "section_source_schemas": {
                "identity": str(identity_schema_path),
                "booking": str(booking_schema_path),
            },
        }
    )

    assert compilation.errors == []
    booking_activation = next(
        activation
        for activation in compilation.activations
        if activation.section_id == "booking"
    )
    assert booking_activation.covered_fact_ids == ["B1"]
    assert booking_activation.inherited_fact_ids == ["identity.G1"]
    identity_fact = next(
        fact
        for fact in compilation.facts
        if fact.section_id == "identity" and fact.fact_id == "G1"
    )
    assert identity_fact.representations == ["support_transcripts"]
    assert identity_fact.inherited_by_section_ids == ["booking"]
    assert compilation.report()["totals"] == {
        "facts": 2,
        "covered": 2,
        "uncovered": 0,
        "multiply_represented": 0,
    }


def test_journey_rejects_missing_global_fact_owner(tmp_path):
    booking_schema_path = _write_section(
        tmp_path / "booking",
        ["B1"],
        transcript_covered=[["B1"]],
    )
    booking_schema = json.loads(booking_schema_path.read_text())
    booking_schema["domain_hierarchy"] = {
        "role": "journey",
        "requires": [{"section_id": "identity", "fact_ids": ["G1"]}],
    }
    booking_schema_path.write_text(json.dumps(booking_schema))

    compilation = compile_variant_transformations(
        {
            "id": "missing_global_dependency",
            "section_source_schemas": {"booking": str(booking_schema_path)},
        }
    )

    assert any(
        "requires unknown section 'identity'" in error for error in compilation.errors
    )


def test_additional_transformation_adds_coverage_and_documents_overlap(tmp_path):
    # Transcripts (primary) cover F1+F2; the document (additional) covers
    # F2+F3. F2 is multiply represented — legal and documented, not a warning.
    schema = _write_section(
        tmp_path / "s1",
        ["F1", "F2", "F3"],
        transcript_covered=[["F1", "F2"]],
        document_covered=["F2", "F3"],
    )
    stub = json.loads(schema.read_text())["transformations"][0]["stub_path"]
    manifest = {
        "id": "v",
        "section_source_schemas": {"s1": str(schema)},
        "section_replacements": {"s1": stub},
        "additional_transformations": [
            {"section_id": "s1", "representation": "customer_kickoff_document"}
        ],
    }
    compilation = compile_variant_transformations(manifest)
    assert compilation.errors == []
    assert compilation.warnings == []
    assert compilation.uncovered_facts == []
    assert [(a.representation, a.primary) for a in compilation.activations] == [
        ("support_transcripts", True),
        ("customer_kickoff_document", False),
    ]
    overlaps = compilation.multiply_represented_facts
    assert [f.fact_id for f in overlaps] == ["F2"]
    assert overlaps[0].representations == [
        "support_transcripts",
        "customer_kickoff_document",
    ]


def test_additional_transformation_requires_unambiguous_selector(tmp_path):
    schema_path = _write_section(
        tmp_path / "s1", ["F1", "F2"], transcript_covered=[["F1"]]
    )
    schema = json.loads(schema_path.read_text())
    alternate = dict(schema["transformations"][0])
    alternate["stub_path"] = str(tmp_path / "s1" / "alternate.md")
    schema["transformations"].append(alternate)
    schema_path.write_text(json.dumps(schema))

    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema_path)},
            "additional_transformations": [
                {
                    "section_id": "s1",
                    "representation": "support_transcripts",
                }
            ],
        }
    )

    assert any("selector is ambiguous" in error for error in compilation.errors)


def test_invalid_bundle_selection_does_not_activate_legacy_replacement(tmp_path):
    schema_path = _write_section(
        tmp_path / "s1",
        ["F1"],
        transcript_covered=[["F1"]],
    )
    transcript_stub = json.loads(schema_path.read_text())["transformations"][0][
        "stub_path"
    ]

    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema_path)},
            "section_replacements": {"s1": transcript_stub},
            "section_bundles": ["not", "an", "object"],
        }
    )

    assert compilation.errors == ["section_bundles must be an object"]
    assert compilation.activations == []
    assert compilation.bundles == []


def test_bundle_compiles_authority_and_cross_member_dependencies(tmp_path):
    schema_path = _write_section(
        tmp_path / "s1",
        ["F1", "F2"],
        transcript_covered=[["F1"]],
        document_covered=["F2"],
    )
    schema = json.loads(schema_path.read_text())
    transcript_spec, document_spec = schema["transformations"]
    transcript_spec["id"] = "records"
    document_spec["id"] = "document"
    schema["transformation_bundles"] = [
        {
            "id": "coordinated_evidence",
            "stub_path": transcript_spec["stub_path"],
            "fact_ids": ["F1", "F2"],
            "members": [
                {
                    "transformation_id": "records",
                    "primary": True,
                    "authoritative_fact_ids": ["F1"],
                    "depends_on_fact_ids": ["F2"],
                },
                {
                    "transformation_id": "document",
                    "authoritative_fact_ids": ["F2"],
                },
            ],
        }
    ]
    schema_path.write_text(json.dumps(schema))

    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema_path)},
            "section_bundles": {"s1": "coordinated_evidence"},
        }
    )

    assert compilation.errors == []
    assert compilation.warnings == []
    assert len(compilation.bundles) == 1
    bundle = compilation.bundles[0]
    assert bundle.bundle_id == "coordinated_evidence"
    assert [
        (
            member.spec["id"],
            member.authoritative_fact_ids,
            member.depends_on_fact_ids,
        )
        for member in bundle.members
    ] == [
        ("records", ["F1"], ["F2"]),
        ("document", ["F2"], []),
    ]
    assert [fact.representations for fact in compilation.facts] == [
        ["support_transcripts"],
        ["customer_kickoff_document"],
    ]


def test_bundle_linked_evidence_route_owns_only_jointly_established_fact(tmp_path):
    schema_path = _write_section(
        tmp_path / "s1",
        ["F1", "F2"],
        transcript_covered=[["F1"]],
        document_covered=[],
    )
    schema = json.loads(schema_path.read_text())
    transcript_spec, document_spec = schema["transformations"]
    transcript_spec["id"] = "instructions"
    transcript_spec["artifacts"][0]["artifact_ref"] = "article-1042"
    document_spec["id"] = "screen"
    document_spec["artifacts"][0]["artifact_ref"] = "device_capture_07.png"
    schema["transformation_bundles"] = [
        {
            "id": "linked",
            "stub_path": transcript_spec["stub_path"],
            "fact_ids": ["F1", "F2"],
            "members": [
                {
                    "transformation_id": "instructions",
                    "authoritative_fact_ids": ["F1"],
                },
                {
                    "transformation_id": "screen",
                    "authoritative_fact_ids": [],
                },
            ],
            "evidence_routes": [
                {
                    "id": "article_to_screen",
                    "authoritative_fact_ids": ["F2"],
                    "hops": [
                        {
                            "transformation_id": "instructions",
                            "artifact_ref": "article-1042",
                        },
                        {
                            "transformation_id": "screen",
                            "artifact_ref": "device_capture_07.png",
                        },
                    ],
                    "evidence_text": "Instruction plus cited screen establishes F2.",
                    "plausibility": "The screen is a normal support attachment.",
                    "scope_cue": "Only the cited setting is in scope.",
                    "forbidden_inference": "Do not treat neighboring controls as steps.",
                }
            ],
        }
    ]
    schema_path.write_text(json.dumps(schema))

    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema_path)},
            "section_bundles": {"s1": "linked"},
        }
    )

    assert compilation.errors == []
    assert compilation.warnings == []
    assert [fact.representations for fact in compilation.facts] == [
        ["support_transcripts"],
        ["linked_evidence_route"],
    ]
    (route,) = compilation.bundles[0].evidence_routes
    assert route.route_id == "article_to_screen"
    assert route.authoritative_fact_ids == ["F2"]
    report_route = compilation.report()["bundles"][0]["evidence_routes"][0]
    assert report_route["hops"][1]["artifact_ref"] == "device_capture_07.png"


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("missing_ref", "does not resolve"),
        ("one_hop", "at least two artifacts"),
        ("duplicate_authority", "multiple authoritative owners"),
    ],
)
def test_bundle_rejects_broken_linked_evidence_routes(tmp_path, mutation, expected):
    schema_path = _write_section(
        tmp_path / "s1",
        ["F1"],
        transcript_covered=[[]],
        document_covered=[],
    )
    schema = json.loads(schema_path.read_text())
    first, second = schema["transformations"]
    first["id"] = "first"
    first["artifacts"][0]["artifact_ref"] = "first-ref"
    second["id"] = "second"
    second["artifacts"][0]["artifact_ref"] = "second-ref"
    route = {
        "id": "route",
        "authoritative_fact_ids": ["F1"],
        "hops": [
            {"transformation_id": "first", "artifact_ref": "first-ref"},
            {"transformation_id": "second", "artifact_ref": "second-ref"},
        ],
        "evidence_text": "Together they establish F1.",
        "plausibility": "Normal linked evidence.",
        "scope_cue": "Only F1.",
        "forbidden_inference": "No neighboring facts.",
    }
    members = [
        {"transformation_id": "first", "authoritative_fact_ids": []},
        {"transformation_id": "second", "authoritative_fact_ids": []},
    ]
    if mutation == "missing_ref":
        route["hops"][1]["artifact_ref"] = "missing"
    elif mutation == "one_hop":
        route["hops"] = route["hops"][:1]
    else:
        members[0]["authoritative_fact_ids"] = ["F1"]
    schema["transformation_bundles"] = [
        {
            "id": "broken",
            "stub_path": first["stub_path"],
            "fact_ids": ["F1"],
            "members": members,
            "evidence_routes": [route],
        }
    ]
    schema_path.write_text(json.dumps(schema))

    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema_path)},
            "section_bundles": {"s1": "broken"},
        }
    )

    assert any(expected in error for error in compilation.errors)
    assert compilation.activations == []
    assert compilation.bundles == []


def test_selected_bundles_require_one_shared_stub_path(tmp_path):
    schema_path = _write_section(
        tmp_path / "s1",
        ["F1", "F2"],
        transcript_covered=[["F1"]],
        document_covered=["F2"],
    )
    schema = json.loads(schema_path.read_text())
    transcript_spec, document_spec = schema["transformations"]
    transcript_spec["id"] = "records"
    document_spec["id"] = "document"
    schema["transformation_bundles"] = [
        {
            "id": "records_bundle",
            "stub_path": transcript_spec["stub_path"],
            "fact_ids": ["F1"],
            "members": [
                {
                    "transformation_id": "records",
                    "authoritative_fact_ids": ["F1"],
                }
            ],
        },
        {
            "id": "document_bundle",
            "stub_path": document_spec["stub_path"],
            "fact_ids": ["F2"],
            "members": [
                {
                    "transformation_id": "document",
                    "authoritative_fact_ids": ["F2"],
                }
            ],
        },
    ]
    schema_path.write_text(json.dumps(schema))

    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema_path)},
            "section_bundles": {
                "s1": ["records_bundle", "document_bundle"],
            },
        }
    )

    assert any(
        "selected bundles must resolve to exactly one shared stub_path" in error
        for error in compilation.errors
    )


def test_bundle_section_replacements_reject_missing_bundle_stub(tmp_path):
    section_dir = tmp_path / "s1"
    section_dir.mkdir()
    replacement = section_dir / "bundle_stub.md"
    replacement.write_text("## S1\nEvidence is in the bundled artifacts.\n")
    schema_path = section_dir / "schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "facts": [],
                "transformations": [],
                "transformation_bundles": [
                    {"id": "with_stub", "stub_path": str(replacement)},
                    {"id": "without_stub"},
                ],
            }
        )
    )

    with pytest.raises(ValueError, match="must declare a non-empty string stub_path"):
        _bundle_section_replacements(
            {
                "section_source_schemas": {"s1": str(schema_path)},
                "section_bundles": {"s1": ["with_stub", "without_stub"]},
            },
            data_dir=tmp_path,
        )


def test_bundle_rejects_ambiguous_authority_and_unresolved_dependencies(tmp_path):
    schema_path = _write_section(
        tmp_path / "s1",
        ["F1", "F2"],
        transcript_covered=[["F1"]],
        document_covered=["F2"],
    )
    schema = json.loads(schema_path.read_text())
    transcript_spec, document_spec = schema["transformations"]
    transcript_spec["id"] = "records"
    document_spec["id"] = "document"
    schema["transformation_bundles"] = [
        {
            "id": "broken",
            "stub_path": transcript_spec["stub_path"],
            "fact_ids": ["F1", "F2"],
            "members": [
                {
                    "transformation_id": "records",
                    "authoritative_fact_ids": ["F1"],
                    "depends_on_fact_ids": ["F3"],
                },
                {
                    "transformation_id": "document",
                    "authoritative_fact_ids": ["F1"],
                },
            ],
        }
    ]
    schema_path.write_text(json.dumps(schema))

    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema_path)},
            "section_bundles": {"s1": "broken"},
        }
    )

    assert any(
        "multiple authoritative members" in error for error in compilation.errors
    )
    assert any(
        "must exactly match bundle fact_ids" in error for error in compilation.errors
    )
    assert any(
        "not represented inside the bundle" in error for error in compilation.errors
    )
    assert compilation.activations == []
    assert compilation.bundles == []
    assert all(not fact.covered for fact in compilation.facts)


def test_bundle_coverage_mismatch_discards_all_member_activations(tmp_path):
    schema_path = _write_section(
        tmp_path / "s1",
        ["F1", "F2"],
        transcript_covered=[["F1"]],
        document_covered=["F2"],
    )
    schema = json.loads(schema_path.read_text())
    transcript_spec, document_spec = schema["transformations"]
    transcript_spec["id"] = "records"
    document_spec["id"] = "document"
    document_spec["artifacts"][0]["included_fact_ids"] = ["F1"]
    schema["transformation_bundles"] = [
        {
            "id": "evidence",
            "stub_path": transcript_spec["stub_path"],
            "fact_ids": ["F1", "F2"],
            "members": [
                {
                    "transformation_id": "records",
                    "authoritative_fact_ids": ["F1"],
                },
                {
                    "transformation_id": "document",
                    "authoritative_fact_ids": ["F2"],
                },
            ],
        }
    ]
    schema_path.write_text(json.dumps(schema))

    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema_path)},
            "section_bundles": {"s1": "evidence"},
        }
    )

    assert any(
        "artifact coverage must exactly match" in error for error in compilation.errors
    )
    assert compilation.activations == []
    assert compilation.bundles == []
    assert all(not fact.covered for fact in compilation.facts)


def test_bundle_stub_drives_sop_section_replacement(tmp_path):
    canonical = tmp_path / "sop.md"
    canonical.write_text("Demo SOP\n\n## S1\nOld prose.\n\n## S2\nKeep me.\n")
    section_dir = tmp_path / "s1"
    section_dir.mkdir()
    replacement = section_dir / "bundle_stub.md"
    replacement.write_text("## S1\nEvidence is in the bundled artifacts.\n")
    schema = section_dir / "schema.json"
    schema.write_text(
        json.dumps(
            {
                "id": "s1",
                "facts": [],
                "transformations": [],
                "transformation_bundles": [
                    {
                        "id": "evidence",
                        "stub_path": str(replacement),
                        "fact_ids": [],
                        "members": [],
                    }
                ],
            }
        )
    )
    manifest = tmp_path / "variant.json"
    manifest.write_text(
        json.dumps(
            {
                "id": "v",
                "canonical_sop_path": str(canonical),
                "section_order": [
                    {"id": "front_matter", "heading": None},
                    {"id": "s1", "heading": "## S1"},
                    {"id": "s2", "heading": "## S2"},
                ],
                "section_source_schemas": {"s1": str(schema)},
                "section_bundles": {"s1": "evidence"},
            }
        )
    )

    assembled = assemble_sop_variant(manifest)

    assert "Evidence is in the bundled artifacts." in assembled
    assert "Old prose." not in assembled
    assert "Keep me." in assembled


def test_uncovered_facts_warn_and_route_to_fallback(tmp_path):
    schema = _write_section(
        tmp_path / "s1", ["F1", "F2", "F3"], transcript_covered=[["F1"]]
    )
    compilation = compile_variant_transformations(
        {"id": "v", "section_source_schemas": {"s1": str(schema)}}
    )
    assert compilation.errors == []
    assert len(compilation.warnings) == 1
    assert "fallback" in compilation.warnings[0]
    assert sorted(f.fact_id for f in compilation.uncovered_facts) == ["F2", "F3"]
    markdown = render_fallback_markdown(compilation.uncovered_facts, manifest_id="v")
    assert markdown.startswith("## Additional Policy Notes")
    assert "- Statement for F2." in markdown
    assert "- Statement for F3." in markdown


def test_uncovered_fact_policy_error(tmp_path):
    schema = _write_section(tmp_path / "s1", ["F1"], transcript_covered=[[]])
    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema)},
            "uncovered_fact_policy": "error",
        }
    )
    assert any("not covered" in error for error in compilation.errors)
    with pytest.raises(ValueError, match="not covered"):
        compilation.raise_on_errors()


def test_unknown_additional_representation_is_an_error(tmp_path):
    schema = _write_section(tmp_path / "s1", ["F1"], transcript_covered=[["F1"]])
    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema)},
            "additional_transformations": [
                {"section_id": "s1", "representation": "interpretive_dance"}
            ],
        }
    )
    assert any("interpretive_dance" in error for error in compilation.errors)


def test_additional_transformation_missing_from_schema_is_an_error(tmp_path):
    # Schema declares only transcripts; activating a document must fail
    # loudly rather than silently claiming coverage.
    schema = _write_section(tmp_path / "s1", ["F1"], transcript_covered=[["F1"]])
    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema)},
            "additional_transformations": [
                {
                    "section_id": "s1",
                    "representation": "customer_kickoff_document",
                }
            ],
        }
    )
    assert any("customer_kickoff_document" in error for error in compilation.errors)


def test_explicit_rules_cannot_be_an_additional_transformation(tmp_path):
    # explicit_rules coverage comes from the section's prose in the SOP;
    # an additional activation materializes nothing, so allowing it would
    # silently mark facts covered that exist nowhere in the kit.
    schema = _write_section(tmp_path / "s1", ["F1", "F2"], transcript_covered=[["F1"]])
    data = json.loads(schema.read_text())
    data["transformations"].append({"representation": "explicit_rules"})
    schema.write_text(json.dumps(data))
    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema)},
            "additional_transformations": [
                {"section_id": "s1", "representation": "explicit_rules"}
            ],
        }
    )
    assert any(
        "cannot be an additional transformation" in error
        for error in compilation.errors
    )
    # The alias must be rejected too.
    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema)},
            "additional_transformations": [
                {"section_id": "s1", "representation": "sop_prose"}
            ],
        }
    )
    assert any(
        "cannot be an additional transformation" in error
        for error in compilation.errors
    )


def test_primary_explicit_rules_covers_facts_and_reports_fact_count(tmp_path):
    section_dir = tmp_path / "s1"
    section_dir.mkdir(parents=True)
    schema_path = section_dir / "schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "id": "s1_schema",
                "facts": [
                    {"id": "F1", "statement": "Rule one."},
                    {"id": "F2", "statement": "Rule two."},
                ],
                "transformations": [{"representation": "explicit_rules"}],
            }
        )
    )
    compilation = compile_variant_transformations(
        {"id": "v", "section_source_schemas": {"s1": str(schema_path)}}
    )
    assert compilation.errors == []
    assert compilation.uncovered_facts == []
    report = compilation.report()
    (entry,) = report["transformations"]
    assert entry["representation"] == "explicit_rules"
    assert entry["artifact_count"] == 0
    assert entry["fact_count"] == 2  # prose coverage, not artifact-derived
    assert report["totals"]["covered"] == 2


def test_unknown_fact_ids_stay_hard_errors(tmp_path):
    schema = _write_section(
        tmp_path / "s1", ["F1"], transcript_covered=[["F1", "GHOST"]]
    )
    compilation = compile_variant_transformations(
        {"id": "v", "section_source_schemas": {"s1": str(schema)}}
    )
    assert any("GHOST" in error for error in compilation.errors)


def test_fallback_order_is_deterministic_and_seeded(tmp_path):
    schema = _write_section(
        tmp_path / "s1", ["F1", "F2", "F3", "F4"], transcript_covered=[[]]
    )
    manifest = {"id": "seed_a", "section_source_schemas": {"s1": str(schema)}}
    first = compile_variant_transformations(manifest)
    second = compile_variant_transformations(manifest)
    md_a = render_fallback_markdown(first.uncovered_facts, manifest_id="seed_a")
    assert md_a == render_fallback_markdown(
        second.uncovered_facts, manifest_id="seed_a"
    )
    # A different manifest id reshuffles the appendix.
    md_b = render_fallback_markdown(first.uncovered_facts, manifest_id="seed_b")
    assert sorted(md_a.splitlines()) == sorted(md_b.splitlines())
    assert md_a != md_b


def test_summary_mentions_fallback_and_overlap(tmp_path):
    schema = _write_section(
        tmp_path / "s1",
        ["F1", "F2", "F3"],
        transcript_covered=[["F1", "F2"]],
        document_covered=["F2"],
    )
    stub = json.loads(schema.read_text())["transformations"][0]["stub_path"]
    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema)},
            "section_replacements": {"s1": stub},
            "additional_transformations": [
                {
                    "section_id": "s1",
                    "representation": "customer_kickoff_document",
                }
            ],
        }
    )
    summary = compilation.summary()
    assert "uncovered: 1" in summary
    assert "multiply represented: 1" in summary
    assert "s1.F2" in summary and "s1.F3" in summary
    # Clean fallback-policy compilation: the appendix really is produced.
    assert compilation.fallback_applies
    assert "Facts routed to fallback (explicit-rules appendix):" in summary


def test_summary_does_not_claim_fallback_under_error_policy(tmp_path):
    schema = _write_section(tmp_path / "s1", ["F1", "F2"], transcript_covered=[["F1"]])
    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema)},
            "uncovered_fact_policy": "error",
        }
    )
    assert not compilation.fallback_applies
    assert compilation.report()["fallback_applies"] is False
    summary = compilation.summary()
    # No appendix is produced under the error policy — the summary must not
    # describe routing that never happens.
    assert "routed to fallback" not in summary
    assert "Uncovered facts (no active transformation):" in summary
    assert "s1.F2" in summary


def test_transcript_plans_without_case_records_claim_no_coverage(tmp_path):
    # Legacy schemas track coverage on transcript plan entries — but a plan
    # is a promise, not a kit file. With zero case records on disk the
    # Developer can learn nothing, so the facts must show as uncovered.
    section_dir = tmp_path / "s1"
    (section_dir / "training_records").mkdir(parents=True)  # empty
    rendered = section_dir / "section.md"
    rendered.write_text("## Section\n")
    schema_path = section_dir / "schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "id": "s1_schema",
                "facts": [{"id": "F1", "statement": "Rule one."}],
                "rendered_section_path": str(rendered),
                "transcripts": [{"id": "plan_1", "included_fact_ids": ["F1"]}],
            }
        )
    )
    compilation = compile_variant_transformations(
        {"id": "v", "section_source_schemas": {"s1": str(schema_path)}}
    )
    assert compilation.errors == []
    assert [f.fact_id for f in compilation.uncovered_facts] == ["F1"]
    (activation,) = compilation.activations
    assert activation.artifacts == []
    assert activation.covered_fact_ids == []


def test_duplicate_additional_entries_activate_once(tmp_path):
    schema = _write_section(
        tmp_path / "s1",
        ["F1", "F2"],
        transcript_covered=[["F1"]],
        document_covered=["F2"],
    )
    stub = json.loads(schema.read_text())["transformations"][0]["stub_path"]
    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema)},
            "section_replacements": {"s1": stub},
            "additional_transformations": [
                {
                    "section_id": "s1",
                    "representation": "customer_kickoff_document",
                },
                {
                    "section_id": "s1",
                    "representation": "customer_kickoff_document",
                },
            ],
        }
    )
    assert compilation.errors == []
    # The document activates exactly once — a duplicated manifest entry must
    # not duplicate its artifacts in the kit.
    assert [(a.representation, a.primary) for a in compilation.activations] == [
        ("support_transcripts", True),
        ("customer_kickoff_document", False),
    ]
    assert any("duplicate additional" in warning for warning in compilation.warnings)


def test_duplicate_fact_ids_are_an_error(tmp_path):
    schema = _write_section(tmp_path / "s1", ["F1", "F1"], transcript_covered=[["F1"]])
    compilation = compile_variant_transformations(
        {"id": "v", "section_source_schemas": {"s1": str(schema)}}
    )
    assert any("duplicate fact id" in error for error in compilation.errors)
    # The surviving copy is still audited normally — no phantom uncovered
    # fact, no fallback routing.
    assert compilation.report()["totals"] == {
        "facts": 1,
        "covered": 1,
        "uncovered": 0,
        "multiply_represented": 0,
    }


def test_malformed_schema_json_is_an_error_not_a_crash(tmp_path):
    section_dir = tmp_path / "s1"
    section_dir.mkdir(parents=True)
    schema_path = section_dir / "schema.json"
    schema_path.write_text("{not json")
    compilation = compile_variant_transformations(
        {"id": "v", "section_source_schemas": {"s1": str(schema_path)}}
    )
    assert any("not readable JSON" in error for error in compilation.errors)


def test_malformed_fact_entry_is_an_error(tmp_path):
    schema = _write_section(tmp_path / "s1", ["F1"], transcript_covered=[["F1"]])
    data = json.loads(schema.read_text())
    data["facts"].append({"statement": "orphan rule with no id"})
    schema.write_text(json.dumps(data))
    compilation = compile_variant_transformations(
        {"id": "v", "section_source_schemas": {"s1": str(schema)}}
    )
    assert any("malformed fact" in error for error in compilation.errors)
    assert compilation.report()["totals"]["facts"] == 1


def test_replacement_stub_matching_no_transformation_warns(tmp_path):
    # A stub path the schema does not declare means the assembled SOP and
    # the materialized artifacts may disagree — silent fallback to the first
    # declared transformation must at least be surfaced.
    schema = _write_section(tmp_path / "s1", ["F1"], transcript_covered=[["F1"]])
    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema)},
            "section_replacements": {"s1": str(tmp_path / "nonexistent_stub.md")},
        }
    )
    assert compilation.errors == []
    assert any(
        "matches no declared transformation" in warning
        for warning in compilation.warnings
    )
    assert [a.representation for a in compilation.activations] == [
        "support_transcripts"
    ]


def test_explicit_rules_primary_requires_sop_placement(tmp_path):
    # Prose coverage only exists if the section's prose is actually part of
    # the assembled SOP. A manifest whose section_order omits the section
    # must not let explicit_rules mark its facts covered.
    section_dir = tmp_path / "s1"
    section_dir.mkdir(parents=True)
    schema_path = section_dir / "schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "id": "s1_schema",
                "facts": [{"id": "F1", "statement": "Rule one."}],
                "transformations": [{"representation": "explicit_rules"}],
            }
        )
    )
    section_order = [
        {"id": "front_matter"},
        {"id": "other", "heading": "## Other"},
    ]
    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_order": section_order,
            "section_source_schemas": {"s1": str(schema_path)},
        }
    )
    assert any(
        "does not appear in the manifest's section_order" in error
        for error in compilation.errors
    )
    # Adding the section to section_order resolves it.
    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_order": section_order + [{"id": "s1", "heading": "## S1"}],
            "section_source_schemas": {"s1": str(schema_path)},
        }
    )
    assert compilation.errors == []
    assert compilation.uncovered_facts == []


def test_invalid_additional_entry_does_not_hide_primary_coverage(tmp_path):
    # A bad additional entry is an error, but the section audit still runs
    # so --compile-report shows the primary coverage picture alongside it.
    schema = _write_section(
        tmp_path / "s1", ["F1", "F2"], transcript_covered=[["F1", "F2"]]
    )
    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema)},
            "additional_transformations": [
                {"section_id": "s1", "representation": "interpretive_dance"}
            ],
        }
    )
    assert any("interpretive_dance" in error for error in compilation.errors)
    report = compilation.report()
    assert report["totals"]["facts"] == 2
    assert report["totals"]["covered"] == 2
    assert [a.representation for a in compilation.activations] == [
        "support_transcripts"
    ]


# ---------------------------------------------------------------------------
# client_knowledge: facts held by the Client simulator
# ---------------------------------------------------------------------------


def _write_client_knowledge_bundle_section(tmp_path):
    """A section whose bundle splits facts between transcripts and the Client.

    The client bundle is an overlay on ``records_base``: the base's
    ``records_all`` transcripts (carrying F1 and F2) are substituted with
    the rewritten ``records`` transcripts (carrying only F1), and F2 moves
    to the Client.
    """
    schema_path = _write_section(
        tmp_path / "s1", ["F1", "F2"], transcript_covered=[["F1"]]
    )
    schema = json.loads(schema_path.read_text())
    transcript_spec = schema["transformations"][0]
    transcript_spec["id"] = "records"
    schema["transformations"].append(
        {
            "id": "held",
            "representation": "client_knowledge",
            "stub_path": transcript_spec["stub_path"],
            "fact_ids": ["F2"],
        }
    )
    base_records_dir = tmp_path / "s1" / "base_records"
    base_records_dir.mkdir()
    base_record_path = base_records_dir / "case_001.md"
    base_record_path.write_text("# Case A\n\n**Agent:** Hi.\n")
    schema["transformations"].append(
        {
            "id": "records_all",
            "representation": "support_transcripts",
            "stub_path": transcript_spec["stub_path"],
            "artifacts": [
                {
                    "path": str(base_record_path),
                    "included_fact_ids": ["F1", "F2"],
                }
            ],
        }
    )
    schema["transformation_bundles"] = [
        {
            "id": "records_plus_client",
            "stub_path": transcript_spec["stub_path"],
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
            "stub_path": transcript_spec["stub_path"],
            "fact_ids": ["F1", "F2"],
            "members": [
                {
                    "transformation_id": "records_all",
                    "primary": True,
                    "authoritative_fact_ids": ["F1", "F2"],
                },
            ],
        },
    ]
    schema_path.write_text(json.dumps(schema))
    return schema_path


def test_client_knowledge_bundle_covers_facts_without_artifacts(tmp_path):
    schema_path = _write_client_knowledge_bundle_section(tmp_path)
    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema_path)},
            "section_bundles": {"s1": "records_plus_client"},
        }
    )
    assert compilation.errors == []
    assert compilation.warnings == []
    assert compilation.uncovered_facts == []
    assert [fact.representations for fact in compilation.facts] == [
        ["support_transcripts"],
        ["client_knowledge"],
    ]
    assert compilation.client_held_fact_ids == {"s1": ["F2"]}


def test_client_knowledge_coverage_must_match_bundle_authority(tmp_path):
    schema_path = _write_client_knowledge_bundle_section(tmp_path)
    schema = json.loads(schema_path.read_text())
    # The Client claims F2 but the bundle makes it authoritative for F1 too.
    schema["transformation_bundles"][0]["members"][0]["authoritative_fact_ids"] = []
    schema["transformation_bundles"][0]["members"][1]["authoritative_fact_ids"] = [
        "F1",
        "F2",
    ]
    schema_path.write_text(json.dumps(schema))
    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema_path)},
            "section_bundles": {"s1": "records_plus_client"},
        }
    )
    assert any(
        "artifact coverage must exactly match authoritative_fact_ids" in error
        for error in compilation.errors
    )


def test_client_knowledge_outside_a_bundle_is_an_error(tmp_path):
    schema_path = _write_client_knowledge_bundle_section(tmp_path)
    schema = json.loads(schema_path.read_text())
    # Make client_knowledge the stub-selected primary, no bundle in play.
    schema["transformations"] = [schema["transformations"][1]]
    del schema["transformation_bundles"]
    schema_path.write_text(json.dumps(schema))
    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema_path)},
        }
    )
    assert any(
        "outside a transformation bundle" in error for error in compilation.errors
    )


def test_client_knowledge_requires_nonempty_fact_ids(tmp_path):
    schema_path = _write_client_knowledge_bundle_section(tmp_path)
    schema = json.loads(schema_path.read_text())
    schema["transformations"][1]["fact_ids"] = []
    schema_path.write_text(json.dumps(schema))
    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema_path)},
            "section_bundles": {"s1": "records_plus_client"},
        }
    )
    assert any(
        "non-empty fact_ids list of strings" in error for error in compilation.errors
    )


def _compile_client_bundle(schema_path):
    return compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema_path)},
            "section_bundles": {"s1": "records_plus_client"},
        }
    )


def test_client_knowledge_confirmable_facts_compile_and_are_exposed(tmp_path):
    schema_path = _write_client_knowledge_bundle_section(tmp_path)
    schema = json.loads(schema_path.read_text())
    schema["transformations"][1]["confirmable_fact_ids"] = ["F1"]
    schema_path.write_text(json.dumps(schema))
    compilation = _compile_client_bundle(schema_path)
    assert compilation.errors == []
    assert compilation.client_held_fact_ids == {"s1": ["F2"]}
    assert compilation.client_confirmable_fact_ids == {"s1": ["F1"]}


def test_client_knowledge_confirmable_rejects_held_overlap_and_unknown(tmp_path):
    schema_path = _write_client_knowledge_bundle_section(tmp_path)
    schema = json.loads(schema_path.read_text())
    # A held fact declared confirmable trips the carrier check: the member's
    # own authority is excluded from "carried by other bundle members".
    schema["transformations"][1]["confirmable_fact_ids"] = ["F2"]
    schema_path.write_text(json.dumps(schema))
    compilation = _compile_client_bundle(schema_path)
    assert any(
        "confirmable_fact_ids must be carried by other bundle members" in error
        for error in compilation.errors
    )

    # The spec-level messages (overlap, unknown, duplicates) come from
    # discover_artifacts directly.
    from tau2.hyper.transformations.client_knowledge import (
        ClientKnowledgeTransformation,
    )

    transformation = ClientKnowledgeTransformation()
    spec = dict(schema["transformations"][1])
    for confirmable, message in [
        (["F2"], "overlap the held fact_ids"),
        (["no_such_fact"], "not in the section schema"),
        (["F1", "F1"], "duplicate confirmable_fact_ids"),
    ]:
        spec["confirmable_fact_ids"] = confirmable
        with pytest.raises(ValueError, match=message):
            transformation.discover_artifacts(schema, schema_path, spec)


def test_client_knowledge_confirmable_must_be_carried_in_bundle(tmp_path):
    schema_path = _write_client_knowledge_bundle_section(tmp_path)
    schema = json.loads(schema_path.read_text())
    # F3 exists in the section but no bundle member carries it, so the
    # Client would adjudicate a fact the Developer cannot find in the kit.
    schema["facts"].append({"id": "F3", "statement": "Statement for F3."})
    schema["transformations"][1]["confirmable_fact_ids"] = ["F3"]
    schema_path.write_text(json.dumps(schema))
    compilation = _compile_client_bundle(schema_path)
    assert any(
        "confirmable_fact_ids must be carried by other bundle members" in error
        for error in compilation.errors
    )


# ---------------------------------------------------------------------------
# client_knowledge: overlay declaration against the base bundle
# ---------------------------------------------------------------------------


def _mutate_client_bundle(schema_path, mutate):
    schema = json.loads(schema_path.read_text())
    mutate(schema)
    schema_path.write_text(json.dumps(schema))


def test_client_bundle_must_declare_its_overlay_base(tmp_path):
    schema_path = _write_client_knowledge_bundle_section(tmp_path)
    _mutate_client_bundle(
        schema_path,
        lambda schema: schema["transformation_bundles"][0].pop("client_overlay_of"),
    )
    compilation = _compile_client_bundle(schema_path)
    assert any(
        "must declare client_overlay_of" in error for error in compilation.errors
    )


def test_client_overlay_base_must_exist_and_not_be_self_or_client(tmp_path):
    schema_path = _write_client_knowledge_bundle_section(tmp_path)

    def unknown(schema):
        schema["transformation_bundles"][0]["client_overlay_of"] = "no_such_bundle"

    _mutate_client_bundle(schema_path, unknown)
    compilation = _compile_client_bundle(schema_path)
    assert any("client_overlay_of" in error for error in compilation.errors)

    def self_reference(schema):
        schema["transformation_bundles"][0]["client_overlay_of"] = "records_plus_client"

    _mutate_client_bundle(schema_path, self_reference)
    compilation = _compile_client_bundle(schema_path)
    assert any(
        "may not name the bundle itself" in error for error in compilation.errors
    )

    def base_with_client_member(schema):
        schema["transformation_bundles"][0]["client_overlay_of"] = "records_base"
        schema["transformation_bundles"][1]["fact_ids"] = ["F1", "F2"]
        schema["transformation_bundles"][1]["members"] = [
            {"transformation_id": "records", "authoritative_fact_ids": ["F1"]},
            {"transformation_id": "held", "authoritative_fact_ids": ["F2"]},
        ]

    _mutate_client_bundle(schema_path, base_with_client_member)
    compilation = _compile_client_bundle(schema_path)
    assert any(
        "must name an artifact-only bundle" in error for error in compilation.errors
    )


def test_client_overlay_fact_sets_must_match_base(tmp_path):
    schema_path = _write_client_knowledge_bundle_section(tmp_path)

    def shrink_base(schema):
        schema["transformation_bundles"][1]["fact_ids"] = ["F1"]
        schema["transformation_bundles"][1]["members"][0]["authoritative_fact_ids"] = [
            "F1"
        ]

    _mutate_client_bundle(schema_path, shrink_base)
    compilation = _compile_client_bundle(schema_path)
    assert any(
        "overlay must declare the same fact_ids as base" in error
        for error in compilation.errors
    )


def test_client_overlay_members_are_substitution_never_addition(tmp_path):
    schema_path = _write_client_knowledge_bundle_section(tmp_path)
    _mutate_client_bundle(
        schema_path,
        lambda schema: schema["transformation_bundles"][0].pop("member_substitutions"),
    )
    compilation = _compile_client_bundle(schema_path)
    assert any("substitution, never addition" in error for error in compilation.errors)


def test_client_overlay_replacement_sheds_exactly_the_held_facts(tmp_path):
    schema_path = _write_client_knowledge_bundle_section(tmp_path)

    def keep_held_fact(schema):
        # The rewritten records member still claims the client-held F2.
        schema["transformation_bundles"][0]["members"][0]["authoritative_fact_ids"] = [
            "F1",
            "F2",
        ]

    _mutate_client_bundle(schema_path, keep_held_fact)
    compilation = _compile_client_bundle(schema_path)
    assert any(
        "authority minus the client-held facts" in error for error in compilation.errors
    )


def test_client_overlay_held_facts_come_from_substituted_members(tmp_path):
    schema_path = _write_client_knowledge_bundle_section(tmp_path)

    def held_from_unchanged_member(tmp_schema):
        # Base splits F1/F2 across two members but only the F1 member is
        # substituted; the held F2 lives on a member the overlay keeps.
        tmp_schema["transformations"].append(
            {
                "id": "records_f2",
                "representation": "support_transcripts",
                "stub_path": tmp_schema["transformations"][0]["stub_path"],
                "artifacts": [],
            }
        )
        tmp_schema["transformation_bundles"][1]["members"] = [
            {
                "transformation_id": "records_all",
                "primary": True,
                "authoritative_fact_ids": ["F1"],
            },
            {"transformation_id": "records_f2", "authoritative_fact_ids": ["F2"]},
        ]
        tmp_schema["transformation_bundles"][0]["members"] = [
            {
                "transformation_id": "records",
                "primary": True,
                "authoritative_fact_ids": ["F1"],
            },
            {"transformation_id": "records_f2", "authoritative_fact_ids": []},
            {"transformation_id": "held", "authoritative_fact_ids": ["F2"]},
        ]

    _mutate_client_bundle(schema_path, held_from_unchanged_member)
    compilation = _compile_client_bundle(schema_path)
    assert any(
        "carved out of substituted base members" in error
        for error in compilation.errors
    )


def test_client_overlay_primary_follows_base_and_client_never_primary(tmp_path):
    schema_path = _write_client_knowledge_bundle_section(tmp_path)

    def client_primary(schema):
        members = schema["transformation_bundles"][0]["members"]
        del members[0]["primary"]
        members[1]["primary"] = True

    _mutate_client_bundle(schema_path, client_primary)
    compilation = _compile_client_bundle(schema_path)
    assert any("may not be primary" in error for error in compilation.errors)
    assert any(
        "primary member must follow base" in error for error in compilation.errors
    )


def test_client_overlay_of_must_name_an_artifact_only_base(tmp_path):
    schema_path = _write_client_knowledge_bundle_section(tmp_path)
    _mutate_client_bundle(
        schema_path,
        lambda schema: schema["transformation_bundles"][1].update(
            {"client_overlay_of": "records_plus_client"}
        ),
    )
    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema_path)},
            "section_bundles": {"s1": "records_base"},
        }
    )
    assert any(
        "must name an artifact-only bundle" in error for error in compilation.errors
    )


def test_member_substitutions_require_client_overlay_of(tmp_path):
    schema_path = _write_client_knowledge_bundle_section(tmp_path)
    _mutate_client_bundle(
        schema_path,
        lambda schema: schema["transformation_bundles"][1].update(
            {"member_substitutions": {"records_all": "records"}}
        ),
    )
    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema_path)},
            "section_bundles": {"s1": "records_base"},
        }
    )
    assert any(
        "member_substitutions requires client_overlay_of" in error
        for error in compilation.errors
    )


def _add_carrier_lockstep_bundle(schema):
    """A no-held overlay that swaps the carrier but keeps authority intact.

    Models the trio-spine consumer case: a section holds no facts of its
    own, but its bundle delivers a shared carrier that a sibling section's
    overlay forked, so it must substitute the same fork in lockstep.
    """
    schema["transformations"].append(
        {
            "id": "records_fork",
            "representation": "support_transcripts",
            "stub_path": schema["transformations"][0]["stub_path"],
            "artifacts": [
                {
                    "path": schema["transformations"][0]["artifacts"][0]["path"],
                    "included_fact_ids": ["F1", "F2"],
                }
            ],
        }
    )
    schema["transformation_bundles"].append(
        {
            "id": "records_lockstep",
            "stub_path": schema["transformations"][0]["stub_path"],
            "fact_ids": ["F1", "F2"],
            "client_overlay_of": "records_base",
            "member_substitutions": {"records_all": "records_fork"},
            "members": [
                {
                    "transformation_id": "records_fork",
                    "primary": True,
                    "authoritative_fact_ids": ["F1", "F2"],
                },
            ],
        }
    )


def test_carrier_lockstep_overlay_without_client_member_compiles(tmp_path):
    schema_path = _write_client_knowledge_bundle_section(tmp_path)
    _mutate_client_bundle(schema_path, _add_carrier_lockstep_bundle)
    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema_path)},
            "section_bundles": {"s1": "records_lockstep"},
        }
    )
    assert compilation.errors == []
    assert compilation.client_held_fact_ids == {}


def test_carrier_lockstep_overlay_may_not_drop_authority(tmp_path):
    schema_path = _write_client_knowledge_bundle_section(tmp_path)

    def lockstep_dropping_f2(schema):
        _add_carrier_lockstep_bundle(schema)
        schema["transformation_bundles"][-1]["members"][0]["authoritative_fact_ids"] = [
            "F1"
        ]

    _mutate_client_bundle(schema_path, lockstep_dropping_f2)
    compilation = compile_variant_transformations(
        {
            "id": "v",
            "section_source_schemas": {"s1": str(schema_path)},
            "section_bundles": {"s1": "records_lockstep"},
        }
    )
    assert any(
        "keep base member" in error and "authority minus the client-held" in error
        for error in compilation.errors
    )


# ---------------------------------------------------------------------------
# client_knowledge: overlays over bundles with evidence_routes
# (L1 carry-through / L2 route substitution)
# ---------------------------------------------------------------------------


ROUTE_NARRATIVE = {
    "evidence_text": "Article plus cited screen establishes R1 and R2.",
    "plausibility": "The screen is a normal support attachment.",
    "scope_cue": "Only the cited setting is in scope.",
    "forbidden_inference": "Do not treat neighboring controls as steps.",
}


def _write_routes_overlay_section(tmp_path):
    """A routes base plus a client overlay that carries the route through.

    Base ``records_base``: transcripts ``records_all`` (F1+F2, primary,
    artifact ``article-1``) + document ``screen_all`` (no facts, artifact
    ``screen-1``); route ``route_r`` owns R1+R2 across
    article-1 -> screen-1. Overlay ``records_plus_client`` substitutes
    ``records_all`` with ``records`` (F1 only; F2 moves to the Client) and
    re-declares the route byte-equivalently with the hop mapped through the
    substitution (L1 carry-through).
    """
    schema_path = _write_section(
        tmp_path / "s1",
        ["F1", "F2", "R1", "R2"],
        transcript_covered=[["F1"]],
        document_covered=[],
    )
    schema = json.loads(schema_path.read_text())
    transcript_spec, document_spec = schema["transformations"]
    transcript_spec["id"] = "records"
    transcript_spec["artifacts"][0]["artifact_ref"] = "article-1"
    document_spec["id"] = "screen_all"
    document_spec["artifacts"][0]["artifact_ref"] = "screen-1"
    schema["transformations"].append(
        {
            "id": "held",
            "representation": "client_knowledge",
            "stub_path": transcript_spec["stub_path"],
            "fact_ids": ["F2"],
        }
    )
    base_records_dir = tmp_path / "s1" / "base_records"
    base_records_dir.mkdir()
    base_record_path = base_records_dir / "case_001.md"
    base_record_path.write_text("# Case A\n\n**Agent:** Hi.\n")
    schema["transformations"].append(
        {
            "id": "records_all",
            "representation": "support_transcripts",
            "stub_path": transcript_spec["stub_path"],
            "artifacts": [
                {
                    "path": str(base_record_path),
                    "included_fact_ids": ["F1", "F2"],
                    "artifact_ref": "article-1",
                }
            ],
        }
    )

    def route(**overrides):
        declared = {
            "id": "route_r",
            "authoritative_fact_ids": ["R1", "R2"],
            "hops": [
                {"transformation_id": "records_all", "artifact_ref": "article-1"},
                {"transformation_id": "screen_all", "artifact_ref": "screen-1"},
            ],
            **ROUTE_NARRATIVE,
        }
        declared.update(overrides)
        return declared

    schema["transformation_bundles"] = [
        {
            "id": "records_plus_client",
            "stub_path": transcript_spec["stub_path"],
            "fact_ids": ["F1", "F2", "R1", "R2"],
            "client_overlay_of": "records_base",
            "member_substitutions": {"records_all": "records"},
            "members": [
                {
                    "transformation_id": "records",
                    "primary": True,
                    "authoritative_fact_ids": ["F1"],
                },
                {"transformation_id": "screen_all", "authoritative_fact_ids": []},
                {"transformation_id": "held", "authoritative_fact_ids": ["F2"]},
            ],
            "evidence_routes": [
                route(
                    hops=[
                        {"transformation_id": "records", "artifact_ref": "article-1"},
                        {"transformation_id": "screen_all", "artifact_ref": "screen-1"},
                    ]
                )
            ],
        },
        {
            "id": "records_base",
            "stub_path": transcript_spec["stub_path"],
            "fact_ids": ["F1", "F2", "R1", "R2"],
            "members": [
                {
                    "transformation_id": "records_all",
                    "primary": True,
                    "authoritative_fact_ids": ["F1", "F2"],
                },
                {"transformation_id": "screen_all", "authoritative_fact_ids": []},
            ],
            "evidence_routes": [route()],
        },
    ]
    schema_path.write_text(json.dumps(schema))
    return schema_path


def test_routes_base_overlay_accepted_under_l1_carry_through(tmp_path):
    schema_path = _write_routes_overlay_section(tmp_path)
    compilation = _compile_client_bundle(schema_path)
    assert compilation.errors == []
    assert compilation.warnings == []
    assert compilation.client_held_fact_ids == {"s1": ["F2"]}
    coverage = {fact.fact_id: fact.representations for fact in compilation.facts}
    assert coverage["F2"] == ["client_knowledge"]
    assert coverage["R1"] == ["linked_evidence_route"]
    assert coverage["R2"] == ["linked_evidence_route"]
    # The report round-trips the re-declared route with mapped hops.
    (bundle_report,) = compilation.report()["bundles"]
    (route_report,) = bundle_report["evidence_routes"]
    assert route_report["route_id"] == "route_r"
    assert route_report["authoritative_fact_ids"] == ["R1", "R2"]
    assert route_report["hops"][0]["transformation_id"] == "records"
    assert route_report["evidence_text"] == ROUTE_NARRATIVE["evidence_text"]


def test_routes_overlay_route_owned_confirmable_is_legal(tmp_path):
    schema_path = _write_routes_overlay_section(tmp_path)
    _mutate_client_bundle(
        schema_path,
        lambda schema: schema["transformations"][2].update(
            {"confirmable_fact_ids": ["R1"]}
        ),
    )
    compilation = _compile_client_bundle(schema_path)
    assert compilation.errors == []
    assert compilation.client_confirmable_fact_ids == {"s1": ["R1"]}


def test_routes_overlay_rejects_held_route_fact_without_shed(tmp_path):
    schema_path = _write_routes_overlay_section(tmp_path)

    def hold_route_fact(schema):
        # The Client claims R1 while the re-declared route still owns it —
        # duplicate authority inside the overlay bundle, and the overlay
        # contract names the route interaction explicitly.
        schema["transformations"][2]["fact_ids"] = ["F2", "R1"]
        schema["transformation_bundles"][0]["members"][2]["authoritative_fact_ids"] = [
            "F2",
            "R1",
        ]

    _mutate_client_bundle(schema_path, hold_route_fact)
    compilation = _compile_client_bundle(schema_path)
    assert any(
        "multiple authoritative" in error or "must be shed" in error
        for error in compilation.errors
    )


def test_routes_overlay_rejects_silently_absent_route(tmp_path):
    schema_path = _write_routes_overlay_section(tmp_path)

    def drop_route(schema):
        overlay = schema["transformation_bundles"][0]
        del overlay["evidence_routes"]
        # Keep authority totality plausible so the absence check is what
        # fires: hand the route facts to the client member.
        schema["transformations"][2]["fact_ids"] = ["F2", "R1", "R2"]
        overlay["members"][2]["authoritative_fact_ids"] = ["F2", "R1", "R2"]

    _mutate_client_bundle(schema_path, drop_route)
    compilation = _compile_client_bundle(schema_path)
    assert any("never silently absent" in error for error in compilation.errors)


def test_routes_overlay_rejects_renamed_or_invented_route(tmp_path):
    schema_path = _write_routes_overlay_section(tmp_path)

    def rename_route(schema):
        schema["transformation_bundles"][0]["evidence_routes"][0]["id"] = "route_x"

    _mutate_client_bundle(schema_path, rename_route)
    compilation = _compile_client_bundle(schema_path)
    assert any("never invent new ones" in error for error in compilation.errors)
    assert any("never silently absent" in error for error in compilation.errors)


def test_routes_overlay_rejects_route_gaining_facts(tmp_path):
    schema_path = _write_routes_overlay_section(tmp_path)

    def grow_route(schema):
        overlay = schema["transformation_bundles"][0]
        overlay["evidence_routes"][0]["authoritative_fact_ids"] = ["R1", "R2", "F1"]
        overlay["members"][0]["authoritative_fact_ids"] = []

    _mutate_client_bundle(schema_path, grow_route)
    compilation = _compile_client_bundle(schema_path)
    assert any("may not add facts beyond base" in error for error in compilation.errors)


def test_routes_overlay_rejects_narrative_drift_without_shed(tmp_path):
    schema_path = _write_routes_overlay_section(tmp_path)

    def drift(schema):
        schema["transformation_bundles"][0]["evidence_routes"][0]["evidence_text"] = (
            "Reworded narrative that no longer matches the base."
        )

    _mutate_client_bundle(schema_path, drift)
    compilation = _compile_client_bundle(schema_path)
    assert any(
        "must keep base" in error and "evidence_text identical" in error
        for error in compilation.errors
    )


def test_routes_overlay_rejects_unmapped_hop(tmp_path):
    schema_path = _write_routes_overlay_section(tmp_path)

    def keep_base_member_hop(schema):
        # The overlay re-declares the hop against the substituted-away base
        # member instead of mapping it through member_substitutions.
        schema["transformation_bundles"][0]["evidence_routes"][0]["hops"][0][
            "transformation_id"
        ] = "records_all"

    _mutate_client_bundle(schema_path, keep_base_member_hop)
    compilation = _compile_client_bundle(schema_path)
    assert any(
        "references non-member transformation" in error
        or "hops must match base" in error
        for error in compilation.errors
    )


def test_routes_overlay_rejects_hop_ref_missing_in_replacement(tmp_path):
    schema_path = _write_routes_overlay_section(tmp_path)

    def drop_replacement_ref(schema):
        del schema["transformations"][0]["artifacts"][0]["artifact_ref"]

    _mutate_client_bundle(schema_path, drop_replacement_ref)
    compilation = _compile_client_bundle(schema_path)
    assert any("does not resolve" in error for error in compilation.errors)


def _shed_r2_to_client(schema):
    """Mutate the fixture into a legal L2 shed: R2 moves to the Client.

    The terminal member ``screen_all`` is substituted with ``screen`` (same
    artifact_ref, rewritten content in the real corpus), the re-declared
    route keeps R1 only, and the client member holds F2+R2.
    """
    document_spec = schema["transformations"][1]
    screen_spec = dict(document_spec)
    screen_spec["id"] = "screen"
    schema["transformations"].append(screen_spec)
    overlay = schema["transformation_bundles"][0]
    overlay["member_substitutions"] = {
        "records_all": "records",
        "screen_all": "screen",
    }
    overlay["members"] = [
        {
            "transformation_id": "records",
            "primary": True,
            "authoritative_fact_ids": ["F1"],
        },
        {"transformation_id": "screen", "authoritative_fact_ids": []},
        {"transformation_id": "held", "authoritative_fact_ids": ["F2", "R2"]},
    ]
    schema["transformations"][2]["fact_ids"] = ["F2", "R2"]
    overlay["evidence_routes"] = [
        {
            "id": "route_r",
            "authoritative_fact_ids": ["R1"],
            "hops": [
                {"transformation_id": "records", "artifact_ref": "article-1"},
                {"transformation_id": "screen", "artifact_ref": "screen-1"},
            ],
            **{
                **ROUTE_NARRATIVE,
                "evidence_text": "Article plus cited screen establishes R1.",
            },
        }
    ]


def test_routes_overlay_l2_shed_accepted_with_terminal_substitution(tmp_path):
    schema_path = _write_routes_overlay_section(tmp_path)
    _mutate_client_bundle(schema_path, _shed_r2_to_client)
    compilation = _compile_client_bundle(schema_path)
    assert compilation.errors == []
    assert compilation.client_held_fact_ids == {"s1": ["F2", "R2"]}
    coverage = {fact.fact_id: fact.representations for fact in compilation.facts}
    assert coverage["R2"] == ["client_knowledge"]
    assert coverage["R1"] == ["linked_evidence_route"]


def test_routes_overlay_l2_shed_narrative_may_be_reauthored(tmp_path):
    # _shed_r2_to_client already re-authors evidence_text; the L1
    # narrative-identity requirement must not fire for shed routes.
    schema_path = _write_routes_overlay_section(tmp_path)
    _mutate_client_bundle(schema_path, _shed_r2_to_client)
    compilation = _compile_client_bundle(schema_path)
    assert not any("identical" in error for error in compilation.errors)


def test_routes_overlay_l2_shed_requires_terminal_substitution(tmp_path):
    schema_path = _write_routes_overlay_section(tmp_path)

    def shed_without_terminal(schema):
        _shed_r2_to_client(schema)
        overlay = schema["transformation_bundles"][0]
        overlay["member_substitutions"] = {"records_all": "records"}
        overlay["members"][1] = {
            "transformation_id": "screen_all",
            "authoritative_fact_ids": [],
        }
        overlay["evidence_routes"][0]["hops"][1]["transformation_id"] = "screen_all"

    _mutate_client_bundle(schema_path, shed_without_terminal)
    compilation = _compile_client_bundle(schema_path)
    assert any(
        "may shed facts only when its terminal member" in error
        for error in compilation.errors
    )


def test_routes_overlay_l2_shed_facts_must_be_client_held(tmp_path):
    schema_path = _write_routes_overlay_section(tmp_path)

    def shed_to_artifact_member(schema):
        _shed_r2_to_client(schema)
        overlay = schema["transformation_bundles"][0]
        # R2 lands on the replacement terminal instead of the Client.
        overlay["members"][1]["authoritative_fact_ids"] = ["R2"]
        overlay["members"][2]["authoritative_fact_ids"] = ["F2"]
        schema["transformations"][2]["fact_ids"] = ["F2"]

    _mutate_client_bundle(schema_path, shed_to_artifact_member)
    compilation = _compile_client_bundle(schema_path)
    assert any(
        "shed facts must be client-held" in error for error in compilation.errors
    )


def test_routes_overlay_rejects_husk_route(tmp_path):
    schema_path = _write_routes_overlay_section(tmp_path)

    def shed_everything(schema):
        _shed_r2_to_client(schema)
        overlay = schema["transformation_bundles"][0]
        overlay["evidence_routes"][0]["authoritative_fact_ids"] = []
        overlay["members"][2]["authoritative_fact_ids"] = ["F2", "R1", "R2"]
        schema["transformations"][2]["fact_ids"] = ["F2", "R1", "R2"]

    _mutate_client_bundle(schema_path, shed_everything)
    compilation = _compile_client_bundle(schema_path)
    assert any(
        "authoritative_fact_ids must not be empty" in error
        for error in compilation.errors
    )


def test_routes_overlay_retirement_totality(tmp_path):
    schema_path = _write_routes_overlay_section(tmp_path)

    def retire_route(schema):
        _shed_r2_to_client(schema)
        overlay = schema["transformation_bundles"][0]
        overlay["evidence_routes"] = []
        overlay["route_retirements"] = ["route_r"]
        overlay["members"][2]["authoritative_fact_ids"] = ["F2", "R1", "R2"]
        schema["transformations"][2]["fact_ids"] = ["F2", "R1", "R2"]

    _mutate_client_bundle(schema_path, retire_route)
    compilation = _compile_client_bundle(schema_path)
    assert compilation.errors == []
    assert compilation.client_held_fact_ids == {"s1": ["F2", "R1", "R2"]}


def test_routes_overlay_retirement_requires_held_facts_and_a_substituted_hop(tmp_path):
    schema_path = _write_routes_overlay_section(tmp_path)

    def retire_without_either(schema):
        overlay = schema["transformation_bundles"][0]
        overlay["evidence_routes"] = []
        overlay["route_retirements"] = ["route_r"]
        # Route facts go to an artifact member, not the Client, and the
        # route itself is retired without substituting either hop.
        overlay["member_substitutions"] = {}
        overlay["members"][0]["transformation_id"] = "records_all"
        overlay["members"][1]["authoritative_fact_ids"] = ["R1", "R2"]

    _mutate_client_bundle(schema_path, retire_without_either)
    compilation = _compile_client_bundle(schema_path)
    assert any(
        "retired route 'route_r' facts must be client-held" in error
        for error in compilation.errors
    )
    assert any(
        "requires substituting at least one of its hop members" in error
        for error in compilation.errors
    )


def test_routes_overlay_retirement_allows_substituted_nonterminal_hop(tmp_path):
    schema_path = _write_routes_overlay_section(tmp_path)

    def retire_with_nonterminal_substitution(schema):
        _shed_r2_to_client(schema)
        overlay = schema["transformation_bundles"][0]
        overlay["evidence_routes"] = []
        overlay["route_retirements"] = ["route_r"]
        overlay["member_substitutions"] = {"records_all": "records"}
        overlay["members"][1] = {
            "transformation_id": "screen_all",
            "authoritative_fact_ids": [],
        }
        overlay["members"][2]["authoritative_fact_ids"] = ["F2", "R1", "R2"]
        schema["transformations"][2]["fact_ids"] = ["F2", "R1", "R2"]

    _mutate_client_bundle(schema_path, retire_with_nonterminal_substitution)
    compilation = _compile_client_bundle(schema_path)
    assert compilation.errors == []


def test_routes_overlay_retirement_rejects_unknown_and_double_declared(tmp_path):
    schema_path = _write_routes_overlay_section(tmp_path)

    def bad_retirements(schema):
        overlay = schema["transformation_bundles"][0]
        overlay["route_retirements"] = ["route_r", "route_r", "no_such_route"]

    _mutate_client_bundle(schema_path, bad_retirements)
    compilation = _compile_client_bundle(schema_path)
    assert any(
        "route_retirements contains duplicates" in error for error in compilation.errors
    )
    assert any(
        "names routes not declared by base" in error for error in compilation.errors
    )
    assert any("both re-declared and retired" in error for error in compilation.errors)


def test_routes_overlay_rejects_overlay_only_routes(tmp_path):
    schema_path = _write_routes_overlay_section(tmp_path)

    def base_loses_routes(schema):
        base = schema["transformation_bundles"][1]
        del base["evidence_routes"]
        base["fact_ids"] = ["F1", "F2"]
        schema["transformation_bundles"][0]["fact_ids"] = ["F1", "F2"]
        overlay_route = schema["transformation_bundles"][0]["evidence_routes"][0]
        overlay_route["authoritative_fact_ids"] = ["F1"]
        schema["transformation_bundles"][0]["members"][0]["authoritative_fact_ids"] = []
        schema["transformations"][0]["artifacts"][0]["included_fact_ids"] = []

    _mutate_client_bundle(schema_path, base_loses_routes)
    compilation = _compile_client_bundle(schema_path)
    assert any(
        "declares evidence_routes but base" in error for error in compilation.errors
    )


def test_routes_overlay_contested_route_fact_via_l2_shed(tmp_path):
    schema_path = _write_routes_overlay_section(tmp_path)

    def contest_shed_fact(schema):
        _shed_r2_to_client(schema)
        overlay = schema["transformation_bundles"][0]
        overlay["contested_fact_ids"] = {
            "R2": [
                {"member_id": "records", "reading": "thirty minutes"},
                {"member_id": "screen", "reading": "sixty minutes"},
            ]
        }

    _mutate_client_bundle(schema_path, contest_shed_fact)
    compilation = _compile_client_bundle(schema_path)
    assert compilation.errors == []
    assert compilation.client_contested_fact_ids == {
        "s1": {"R2": ["thirty minutes", "sixty minutes"]}
    }


# ---------------------------------------------------------------------------
# client_knowledge: contested_fact_ids (declared record conflicts)
# ---------------------------------------------------------------------------


def _contest_f2(readings):
    return {
        "F2": [{"member_id": "records", "reading": reading} for reading in readings]
    }


def _declare_contested(declaration):
    def mutate(schema):
        schema["transformation_bundles"][0]["contested_fact_ids"] = declaration

    return mutate


def test_contested_facts_compile_and_are_reported(tmp_path):
    schema_path = _write_client_knowledge_bundle_section(tmp_path)
    _mutate_client_bundle(
        schema_path,
        _declare_contested(_contest_f2(["5 business days", "10 business days"])),
    )
    compilation = _compile_client_bundle(schema_path)
    assert compilation.errors == []
    expected = {"s1": {"F2": ["5 business days", "10 business days"]}}
    assert compilation.client_contested_fact_ids == expected
    # The fact itself still compiles as client-held; contesting changes
    # nothing about authority or coverage.
    assert compilation.client_held_fact_ids == {"s1": ["F2"]}
    assert compilation.report()["client_contested_fact_ids"] == expected


def test_uncontested_bundle_reports_no_contested_facts(tmp_path):
    schema_path = _write_client_knowledge_bundle_section(tmp_path)
    compilation = _compile_client_bundle(schema_path)
    assert compilation.errors == []
    assert compilation.client_contested_fact_ids == {}
    assert compilation.report()["client_contested_fact_ids"] == {}


@pytest.mark.parametrize(
    "declaration, expected",
    [
        (["F2"], "contested_fact_ids must be an object"),
        (
            {"F9": [{"member_id": "records", "reading": "a"}] * 2},
            "not in bundle fact_ids",
        ),
        (
            {
                "F1": [
                    {"member_id": "records", "reading": "reading a"},
                    {"member_id": "records", "reading": "reading b"},
                ]
            },
            "must be held by a client_knowledge member",
        ),
        (
            {"F2": [{"member_id": "records", "reading": "only one"}]},
            "needs at least two renditions",
        ),
        ({"F2": "not a list"}, "needs at least two renditions"),
        (
            {"F2": ["bare string", {"member_id": "records", "reading": "b"}]},
            "rendition 0 must be an object",
        ),
        (
            {
                "F2": [
                    {"member_id": "no_such_member", "reading": "a"},
                    {"member_id": "records", "reading": "b"},
                ]
            },
            "names unknown member",
        ),
        (
            {
                "F2": [
                    {"member_id": "held", "reading": "a"},
                    {"member_id": "records", "reading": "b"},
                ]
            },
            "the client member cannot carry a rendition",
        ),
        (
            {
                "F2": [
                    {"member_id": "records", "reading": "   "},
                    {"member_id": "records", "reading": "b"},
                ]
            },
            "needs a non-empty reading",
        ),
        (
            _contest_f2(["Ten  business days", "ten business days"]),
            "readings must be pairwise distinct",
        ),
    ],
)
def test_contested_declaration_rejects_malformed_entries(
    tmp_path, declaration, expected
):
    schema_path = _write_client_knowledge_bundle_section(tmp_path)
    _mutate_client_bundle(schema_path, _declare_contested(declaration))
    compilation = _compile_client_bundle(schema_path)
    assert any(expected in error for error in compilation.errors), (
        f"expected {expected!r} in {compilation.errors}"
    )
    assert compilation.client_contested_fact_ids == {}


def test_contested_rendition_member_may_not_hold_authority(tmp_path):
    """Defense in depth: a carrier with authority over the contested fact is
    rejected here even though the broken authority partition already errors."""
    schema_path = _write_client_knowledge_bundle_section(tmp_path)

    def double_authority(schema):
        members = schema["transformation_bundles"][0]["members"]
        members[0]["authoritative_fact_ids"] = ["F1", "F2"]
        schema["transformation_bundles"][0]["contested_fact_ids"] = _contest_f2(
            ["reading a", "reading b"]
        )

    _mutate_client_bundle(schema_path, double_authority)
    compilation = _compile_client_bundle(schema_path)
    assert any("has authority over the fact" in error for error in compilation.errors)
    assert compilation.client_contested_fact_ids == {}
