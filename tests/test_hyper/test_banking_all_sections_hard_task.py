"""Regression tests for the consolidated banking hard-evidence task.

Banking's hard evidence surface ships as a single variant manifest that
activates every section's ``evidence_corpus_hard_001`` bundle at once —
twenty-three single-section corpora over the full 93-scenario banking eval
set. There are deliberately no per-section task files; the per-section
variant manifests and the twelve deep overlay bundles remain in the tree for
ad hoc runs and are exercised by their own regression files. These tests pin
that contract: the manifest maps exactly the sections that own a hard corpus
to that corpus's bundle id, the combined compile is clean with the same
complete authority partition as the transcript-induction baseline, and the
release tasks that carry the combined manifest wire to it everywhere over one
shared eval set.
"""

from __future__ import annotations

import json
from pathlib import Path

from tau2.hyper.task_loader import load_hyper_tau_tasks
from tau2.hyper.transformations import compile_variant_transformations
from tau2.hyper.transformations.sop_variants import load_sop_variant_manifest
from tau2.utils.utils import DATA_DIR

BANKING_ROOT = DATA_DIR / "tau2/hyper/sops/banking_knowledge"
SECTIONS_ROOT = BANKING_ROOT / "sections"
BASELINE_MANIFEST_PATH = (
    "tau2/hyper/sops/banking_knowledge/variants/"
    "core_sections_transcript_induction_001.json"
)
ALL_HARD_MANIFEST_PATH = (
    "tau2/hyper/sops/banking_knowledge/variants/"
    "all_sections_evidence_corpus_hard_001.json"
)

ALL_HARD_TASK_IDS = [
    "019_banking_knowledge_construction_evidence_corpus_hard_live_experiment",
    "020_banking_knowledge_construction_evidence_corpus_hard_performance_medium",
    "021_banking_knowledge_construction_evidence_corpus_hard_performance_hard",
]
EVAL_TASK_ID_COUNT = 93


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _authority(compilation) -> set[str]:
    facts = {
        f"{activation.section_id}.{fact_id}"
        for activation in compilation.activations
        for fact_id in (
            activation.authoritative_fact_ids or activation.covered_fact_ids
        )
    }
    facts |= {
        f"{bundle.section_id}.{fact_id}"
        for bundle in compilation.bundles
        for route in bundle.evidence_routes
        for fact_id in route.authoritative_fact_ids
    }
    return facts


def _expected_section_bundles() -> dict[str, str]:
    expected = {}
    for section_dir in sorted(SECTIONS_ROOT.iterdir()):
        pack_path = section_dir / "evidence_corpus_hard_001/transformation_pack.json"
        if not pack_path.exists():
            continue
        bundles = _load_json(pack_path)["transformation_bundles"]
        assert len(bundles) == 1, section_dir.name
        expected[section_dir.name] = bundles[0]["id"]
    return expected


def test_manifest_maps_every_hard_corpus_section_to_its_bundle():
    manifest = _load_json(DATA_DIR / ALL_HARD_MANIFEST_PATH)
    expected = _expected_section_bundles()
    assert len(expected) == 23
    assert manifest["section_bundles"] == expected


def test_combined_compile_is_clean_with_the_baseline_authority_partition():
    baseline = compile_variant_transformations(
        load_sop_variant_manifest(BASELINE_MANIFEST_PATH)
    )
    all_hard = compile_variant_transformations(
        load_sop_variant_manifest(ALL_HARD_MANIFEST_PATH)
    )

    for compilation in (baseline, all_hard):
        assert compilation.errors == []
        assert compilation.warnings == []
        totals = compilation.report()["totals"]
        assert totals["uncovered"] == 0
        assert totals["multiply_represented"] == 0

    assert len(all_hard.bundles) == 23
    assert _authority(all_hard) == _authority(baseline)


def test_task_wiring_points_at_the_combined_manifest():
    carriers = [
        task
        for task in load_hyper_tau_tasks("banking_knowledge")
        if task.sop_variant_manifest_path == ALL_HARD_MANIFEST_PATH
    ]
    assert sorted(task.id for task in carriers) == ALL_HARD_TASK_IDS

    eval_task_ids = set()
    for task in carriers:
        stages = [
            stage
            for stage in task.composition_pipeline
            if stage["stage"] == "information_distribution"
        ]
        assert len(stages) == 1, task.id
        assert stages[0]["variant_manifest_path"] == ALL_HARD_MANIFEST_PATH, task.id
        assert len(task.test_task_ids) == EVAL_TASK_ID_COUNT, task.id
        eval_task_ids.add(tuple(task.test_task_ids))

    # One eval set across the trio: the hard corpus deepens the evidence
    # surface only, so the tasks differ by performance tier, nothing else.
    assert len(eval_task_ids) == 1
    assert {next(iter(task.performance_profile)) for task in carriers} == {
        "easy",
        "medium",
        "hard",
    }
