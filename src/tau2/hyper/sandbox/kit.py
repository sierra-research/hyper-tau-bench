"""
Developer kit builder and format for sandbox mode.

A "kit" is a self-contained directory that provides everything a coding
agent needs to build a τ-bench agent — and *nothing* it shouldn't see
(no deployment database rows, future customer requests, or production traces).

Every maintained task is a construction (build-from-scratch) task, and every
kit uses the construction layout::

    <kit-dir>/
        README.md                # Instructions: build a domain from this SOP
        sop.md                   # Operational SOP/runbook — omitted when the
                                 #   variant manifest sets sop_delivery:
                                 #   uploaded_material (the prose then ships as
                                 #   one more pooled customer document)
        response_phrasing_rules.md  # Optional customer-facing phrasing rules
        uploaded_materials/      # Optional customer file drop: support records,
                                 #   documents, screenshots, exports, decks —
                                 #   generic type-based names, no topical labels
        knowledge_base/          # Optional supporting documents for KB domains
        client_api/              # Client-owned business-state boundary
            openapi.yaml         # Client-owned REST API contract
            development_seed.json # Synthetic local-test record selectors
        framework/
            README.md            # Framework overview
            client_api_contract.md # Client API-backed toolkit contract
            agent_contract.md    # create_agent() contract
            scenario_contract.md # Customer scenario format
            deployment_manifest.json # Allowed agent models + perf requirements
        workspace/               # Empty stubs — or, when the task sets
                                 #   starting_workspace_path, the authored
                                 #   starting-workspace tree (brownfield)
            tools.py             # Empty — Developer writes this
            agent.py             # Stub with create_agent signature
        simulations/             # Host simulation artifacts

The kit is built from a :class:`HyperTask` via :func:`build_kit`.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import textwrap
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from tau2.hyper.client_api.defects import load_defect_profile
from tau2.hyper.client_api.development import development_seed_manifest
from tau2.hyper.client_api.runtime import build_openapi_contract
from tau2.hyper.data_model import HyperTask
from tau2.hyper.response_phrasing import (
    apply_response_phrasing_rule_pack_to_tasks,
    load_selected_response_phrasing_rule_pack_for_task,
    render_response_phrasing_rules_markdown,
)
from tau2.hyper.transformations import (
    DEFAULT_KIT_MODALITY_PROFILE,
    KitFile,
    ModalityProfile,
    SectionTransformation,
    TransformationArtifact,
    compile_variant_transformations,
    modality_for_path,
    parse_modality_profile,
    render_fallback_markdown,
)
from tau2.hyper.transformations.sop_variants import (
    assemble_sop_variant,
    load_sop_variant_manifest,
    renumber_numbered_section_headings,
)
from tau2.runner.build import build_environment
from tau2.utils import load_file
from tau2.utils.utils import DATA_DIR


def _write_knowledge_base_index(kb_dir: Path) -> None:
    """Write a lightweight index for copied construction knowledge-base docs."""
    entries: list[tuple[str, str, str]] = []
    for path in sorted(kb_dir.rglob("*")):
        if not path.is_file() or path.name == "INDEX.md":
            continue

        rel_path = path.relative_to(kb_dir).as_posix()
        doc_id = path.stem
        title = ""
        if path.suffix == ".json":
            try:
                payload = json.loads(path.read_text())
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                doc_id = str(payload.get("id") or doc_id)
                title = str(payload.get("title") or "")
        entries.append((rel_path, doc_id, title))

    lines = [
        "# Knowledge Base Index",
        "",
        f"Total documents: {len(entries)}",
        "",
        "| File | Document ID | Title |",
        "|------|-------------|-------|",
    ]
    for rel_path, doc_id, title in entries:
        lines.append(f"| `{rel_path}` | `{doc_id}` | {title} |")
    lines.append("")
    (kb_dir / "INDEX.md").write_text("\n".join(lines))


def _withheld_knowledge_base_documents(task: HyperTask) -> set[str]:
    """Document filenames the SOP variant manifest withholds from the kit.

    Transcript-induction variants replace document content with training
    transcripts; shipping the source documents alongside them would defeat
    the information-distribution manipulation.
    """
    if not task.sop_variant_manifest_path:
        return set()
    manifest = load_sop_variant_manifest(task.sop_variant_manifest_path)
    return set(manifest.get("withheld_knowledge_base_documents", []))


def _copy_knowledge_base(task: HyperTask, out_dir: Path) -> Optional[Path]:
    """Copy optional construction knowledge-base documents into the kit."""
    if not task.knowledge_base_path:
        return None

    source = DATA_DIR / task.knowledge_base_path
    if not source.exists():
        raise FileNotFoundError(f"Knowledge base path not found: {source}")

    withheld = _withheld_knowledge_base_documents(task)
    included = (
        set(task.knowledge_base_documents)
        if task.knowledge_base_documents is not None
        else None
    )
    destination = out_dir / "knowledge_base"
    if source.is_dir():
        if included is not None:
            available = {p.name for p in source.rglob("*") if p.is_file()}
            missing = included - available
            if missing:
                raise FileNotFoundError(
                    f"{len(missing)} knowledge_base_documents entries not found "
                    f"under {source}: {sorted(missing)[:5]}"
                )

        def _excluded(directory: str, names: list[str]) -> list[str]:
            return [
                n
                for n in names
                if n in withheld
                or (
                    included is not None
                    and (Path(directory) / n).is_file()
                    and n not in included
                )
            ]

        shutil.copytree(source, destination, ignore=_excluded)
        if included is not None:
            copied = sum(1 for p in destination.rglob("*") if p.is_file())
            logger.info(
                f"Scoped knowledge base to {copied} of "
                f"{len(included)} selected documents"
            )
        if withheld:
            unmatched = {
                n for n in withheld if n not in {p.name for p in source.rglob("*")}
            }
            if unmatched:
                logger.warning(
                    f"{len(unmatched)} withheld knowledge-base documents were "
                    f"not found in {source}: {sorted(unmatched)[:5]}..."
                )
            logger.info(
                f"Withheld {len(withheld) - len(unmatched)} knowledge-base "
                "documents per SOP variant manifest"
            )
    else:
        destination.mkdir()
        if source.name not in withheld and (
            included is None or source.name in included
        ):
            shutil.copy2(source, destination / source.name)

    _write_knowledge_base_index(destination)
    return destination


def _write_construction_sop(
    task: HyperTask, out_dir: Path
) -> tuple[Optional[dict[str, Any]], Optional[KitFile]]:
    """Write the construction SOP from a file or variant manifest.

    Returns ``(variant_manifest, demoted_sop_file)``. Normally the SOP is
    written to ``<kit>/sop.md`` and ``demoted_sop_file`` is None. A variant
    manifest may instead set ``"sop_delivery": "uploaded_material"``: no
    kit-root SOP is written, and the canonical prose sections (replaced or
    bundle-backed sections omitted, headings renumbered) come back as a
    KitFile for :func:`_copy_sop_variant_materials` to pool into
    ``uploaded_materials/`` — the policy text then arrives as one more
    anonymous customer document the Developer has to find, instead of a
    labelled source of truth.
    """
    sop_dest = out_dir / "sop.md"
    if task.sop_variant_manifest_path:
        # The SOP-variant helpers resolve data-relative paths themselves;
        # pre-joining DATA_DIR here double-prefixed the path whenever
        # DATA_DIR is relative (TAU2_DATA_DIR=data from the repo root).
        manifest_path = task.sop_variant_manifest_path
        manifest = load_sop_variant_manifest(manifest_path)
        sop_delivery = manifest.get("sop_delivery", "kit_root")
        if sop_delivery == "uploaded_material":
            if not manifest.get("section_source_schemas"):
                raise ValueError(
                    "sop_delivery: uploaded_material requires "
                    "section_source_schemas — without transformation "
                    "materials there is no uploaded_materials/ pool to "
                    "deliver the SOP through."
                )
            handbook = renumber_numbered_section_headings(
                assemble_sop_variant(manifest_path, drop_replaced_sections=True)
            )
            logger.debug(
                "  Demoting SOP into uploaded_materials/ per variant manifest "
                f"{manifest_path}"
            )
            return manifest, KitFile(
                relative_path="uploaded_materials/customer_service_handbook.md",
                content=handbook.encode(),
                artifact_kind="reference_document",
            )
        if sop_delivery != "kit_root":
            raise ValueError(
                f"Unknown sop_delivery value {sop_delivery!r}; expected "
                "'kit_root' or 'uploaded_material'."
            )
        sop_dest.write_text(assemble_sop_variant(manifest_path))
        logger.debug(f"  Wrote sop.md from variant manifest {manifest_path}")
        return manifest, None

    if not task.sop_document_path:
        raise ValueError(
            "Construction tasks must set sop_document_path or "
            "sop_variant_manifest_path."
        )

    sop_path = DATA_DIR / task.sop_document_path
    if not sop_path.exists():
        raise FileNotFoundError(f"SOP document not found: {sop_path}")
    shutil.copy2(sop_path, sop_dest)
    logger.debug(f"  Copied sop.md from {sop_path}")
    return None, None


def _resolve_data_relative_artifact(path: str | Path) -> Path:
    """Resolve a manifest artifact path that may be absolute or data-relative."""
    artifact_path = Path(path)
    if artifact_path.is_absolute():
        return artifact_path
    return DATA_DIR / artifact_path


_GENERIC_ARTIFACT_STEMS = {
    "api_contract_pack": "api_contract",
    "contact_center_qa_export": "qa_review_export",
    "customer_kickoff_document": "intake_form",
    "device_ui_screenshot": "device_screen",
    "email_thread_archive": "email",
    "helpdesk_automation_export": "system_export",
    "interactive_screen_recording": "screen_recording",
    "jira_issue_export": "work_item_export",
    "knowledge_base_html_export": "knowledge_archive",
    "process_flowchart": "process_map",
    "process_presentation": "slide_deck",
    "recorded_working_session": "meeting_transcript",
    "reference_document": "reference_document",
    "slack_mcp_dump": "workspace_export",
    "support_transcripts": "case_file",
    "website_screenshot": "screenshot",
}

_GENERIC_EXTENSION_STEMS = {
    ".csv": "data_table",
    ".docx": "document",
    ".eml": "email",
    ".html": "knowledge_archive",
    ".json": "data_export",
    ".md": "document",
    ".pdf": "document",
    ".png": "image",
    ".pptx": "slide_deck",
    ".txt": "document",
    ".vtt": "transcript",
    ".xlsx": "workbook",
    ".zip": "archive",
}


def _generic_artifact_stem(kit_file: KitFile) -> str:
    """Return a neutral genre label without exposing an artifact's topic."""
    if kit_file.artifact_kind in _GENERIC_ARTIFACT_STEMS:
        return _GENERIC_ARTIFACT_STEMS[kit_file.artifact_kind]
    return _GENERIC_EXTENSION_STEMS.get(
        Path(kit_file.relative_path).suffix.lower(), "file"
    )


def _pool_uploaded_material_names(kit_files: list[KitFile]) -> list[KitFile]:
    """Assign generic type-based names to pooled customer materials.

    Topic-bearing filenames (``case_007.md``, ``012_RE_subject.eml``, or
    ``cancellation_operations_workbook.pdf``) reveal content and chronology
    before a file is opened. Files instead receive neutral genre names such as
    ``case_file_01.md``, ``email_02.eml``, or ``slide_deck.pdf``. Within each
    genre, content-digest ordering carries no authoring-order or chronology
    signal. File type remains visible so a Developer can orient and choose an
    appropriate inspection tool.
    """
    uploaded: list[KitFile] = []
    passthrough: list[KitFile] = []
    seen_artifacts: dict[tuple[str, str], bool] = {}
    for kit_file in kit_files:
        digest = hashlib.sha256(kit_file.content).hexdigest()
        if (kit_file.relative_path, digest) in seen_artifacts:
            # One artifact may back several sections (a single workspace
            # export can carry every section's decision arcs); the kit
            # includes such a shared file once. Same-named artifacts with
            # different content are distinct files: uploaded ones receive
            # unique generic names below, and any remaining destination
            # collision is caught at write time.
            continue
        seen_artifacts[(kit_file.relative_path, digest)] = True
        if (
            Path(kit_file.relative_path).parts[0] == "uploaded_materials"
            and not kit_file.preserve_filename
        ):
            uploaded.append(kit_file)
        else:
            passthrough.append(kit_file)

    original_stems = {
        id(kit_file): Path(kit_file.relative_path).stem
        for kit_file in passthrough + uploaded
    }
    uploaded.sort(
        key=lambda kit_file: (
            hashlib.sha256(kit_file.content).hexdigest(),
            kit_file.relative_path,
        )
    )
    totals: dict[str, int] = {}
    for kit_file in uploaded:
        stem = _generic_artifact_stem(kit_file)
        totals[stem] = totals.get(stem, 0) + 1

    ordinals: dict[str, int] = {}
    for kit_file in uploaded:
        stem = _generic_artifact_stem(kit_file)
        ordinals[stem] = ordinals.get(stem, 0) + 1
        suffix = Path(kit_file.relative_path).suffix
        if totals[stem] == 1:
            filename = f"{stem}{suffix}"
        else:
            width = max(2, len(str(totals[stem])))
            filename = f"{stem}_{ordinals[stem]:0{width}d}{suffix}"
        kit_file.relative_path = f"uploaded_materials/{filename}"

    # Cross-section pinned-name de-collision. A section's `kit_filename`
    # pins are validated unique within that section, but a union variant may
    # join sections that pinned the same neutral name (credit_card_referrals
    # and credit_card_replacements both pin device_capture_001.png), which
    # previously crashed the build at write time. The pins are anonymity
    # names, never in-record join keys (verified: no record text cites
    # them), so later carriers move to the next free ordinal of the pin's
    # own stem/width. Carriers are ordered by source basename — stable
    # across the base and client arms (a client fork keeps its base file's
    # basename), so both arms assign identical name sets. Byte-identical
    # same-path copies (true shared carriers) are untouched: the pooling
    # dedupe above already collapsed them. Generic-vs-pinned collisions (a
    # pin matching a name the generic pool just assigned) remain a
    # write-time error: generic stems and pin stems are disjoint by
    # convention today, and silently renaming a generic file would reorder
    # its whole pool.
    taken = {kit_file.relative_path for kit_file in passthrough + uploaded}
    pinned_by_path: dict[str, list[KitFile]] = {}
    for kit_file in passthrough:
        if Path(kit_file.relative_path).parts[0] == "uploaded_materials":
            pinned_by_path.setdefault(kit_file.relative_path, []).append(kit_file)
    for original_path, group in sorted(pinned_by_path.items()):
        if len(group) == 1:
            continue
        group.sort(
            key=lambda kit_file: (
                kit_file.source_name or "",
                hashlib.sha256(kit_file.content).hexdigest(),
            )
        )
        original = Path(original_path)
        match = re.fullmatch(r"(.*?)_(\d+)", original.stem)
        stem, width = (
            (match.group(1), len(match.group(2))) if match else (original.stem, 2)
        )
        next_ordinal = int(match.group(2)) + 1 if match else 1
        for kit_file in group[1:]:
            while True:
                candidate = (
                    f"uploaded_materials/{stem}_{next_ordinal:0{width}d}"
                    f"{original.suffix}"
                )
                next_ordinal += 1
                if candidate not in taken:
                    break
            kit_file.relative_path = candidate
            taken.add(candidate)

    # Companions keep their own suffix — plus any stem tag beyond the
    # primary's pre-pooling stem (the ``_followup`` segment suffix on a
    # multi-call record's second recording) — but share the primary's final
    # stem, so paired deliveries (a call record and its recordings) stay
    # pairable and collision-free after the generic renaming.
    for kit_file in passthrough + uploaded:
        primary = Path(kit_file.relative_path)
        for companion in kit_file.companions:
            companion_path = Path(companion.relative_path)
            tag = ""
            if companion_path.stem.startswith(original_stems[id(kit_file)]):
                tag = companion_path.stem[len(original_stems[id(kit_file)]) :]
            companion.relative_path = str(
                primary.with_name(f"{primary.stem}{tag}{companion_path.suffix}")
            )
    return passthrough + uploaded


def _require_client_held_facts_reachable(
    manifest_id: str,
    client_held_sections: set[str],
    client_sections: Optional[list[str]],
    client_has_custom_instructions: bool,
) -> None:
    """client_knowledge facts appear in no kit artifact, so every section
    holding them must be reachable through a live Client: either declared in
    the task's ``client_sections`` (rendered Client knowledge), or covered by
    a hand-authored ``client_instructions`` prompt — which owns what the
    Client reveals, including deliberately withholding control arms
    (stonewall tasks), so undeclared sections only warn there."""
    unreachable = sorted(client_held_sections - set(client_sections or []))
    if not unreachable:
        return
    if client_has_custom_instructions:
        logger.warning(
            f"Variant {manifest_id!r} assigns client_knowledge facts in "
            f"sections {unreachable} not declared in client_sections; the "
            "task's hand-authored client_instructions own what the Client "
            "reveals, so the kit builds with those facts uncarried."
        )
        return
    raise ValueError(
        f"Variant {manifest_id!r} assigns client_knowledge "
        f"facts in sections {unreachable} that the task does not declare "
        "in client_sections; no kit artifact carries them and the Client "
        "would not know them, so they would be unlearnable"
    )


def _substitute_client_carriers(
    kit_files: list[KitFile],
    report_rows: list[dict[str, str]],
) -> list[KitFile]:
    """Drop base-member files shadowed by a client-overlay substitution.

    A shared carrier (one artifact file backing several sections — the
    Beacon Slack workspace export, a full-site page) may reach the kit both
    from a clientized section's substituted member and from another
    section's base member. The two versions contradict each other (the
    client fork deliberately omits the held rulings), so the kit must carry
    exactly one: the client version wins at its kit path, base files at the
    same path are dropped. Two *client* files disagreeing at one path is an
    authoring error, not a substitution.

    Path identity only holds for files whose delivered name survives the
    generic-name pooling (``preserve_filename``, or placed outside
    ``uploaded_materials/``). Pooled files carry per-section ordinal names
    at this stage (two sections' unrelated refdocs both arrive as
    ``reference_document_01.pdf``), so equal paths there are coincidence,
    not a shared carrier; the pooling assigns them distinct names.

    Even at a stable path, path identity alone is not carrier identity:
    two sections may pin the same neutral ``kit_filename`` for unrelated
    artifacts (credit_card_referrals and credit_card_replacements both pin
    ``device_capture_001.png``). Carrier identity is therefore the pair
    (kit path, source basename) — a client fork lives at the same
    corpus-relative path as the base file it replaces, so its basename
    matches its own carrier's and never an unrelated same-pin artifact's.
    """

    def stable_kit_path(kit_file: KitFile) -> bool:
        return (
            kit_file.preserve_filename
            or Path(kit_file.relative_path).parts[0] != "uploaded_materials"
        )

    def carrier_key(kit_file: KitFile) -> tuple[str, str]:
        return (kit_file.relative_path, kit_file.source_name or "")

    client_digests: dict[tuple[str, str], str] = {}
    for kit_file in kit_files:
        if not kit_file.client_substitute or not stable_kit_path(kit_file):
            continue
        digest = hashlib.sha256(kit_file.content).hexdigest()
        previous = client_digests.get(carrier_key(kit_file))
        if previous is not None and previous != digest:
            raise ValueError(
                "Conflicting client-substituted artifacts at kit path "
                f"{kit_file.relative_path!r}; each kit path may carry only "
                "one client version"
            )
        client_digests[carrier_key(kit_file)] = digest

    if not client_digests:
        return kit_files

    kept: list[KitFile] = []
    for kit_file in kit_files:
        if (
            not kit_file.client_substitute
            and stable_kit_path(kit_file)
            and carrier_key(kit_file) in client_digests
            # A byte-identical base copy is the same version, not a
            # contradiction; the generic-name pooling dedups it.
            and hashlib.sha256(kit_file.content).hexdigest()
            != client_digests[carrier_key(kit_file)]
        ):
            report_rows.append(
                {
                    "kit_path": kit_file.relative_path,
                    "representation": kit_file.artifact_kind or "",
                    "replaced_by": "client_overlay_substitution",
                }
            )
            continue
        kept.append(kit_file)
    return kept


def _copy_sop_variant_materials(
    manifest: Optional[dict[str, Any]],
    out_dir: Path,
    extra_kit_files: Optional[list[KitFile]] = None,
    modality_profile: Optional[ModalityProfile | str] = None,
    client_sections: Optional[list[str]] = None,
    client_has_custom_instructions: bool = False,
) -> Optional[list[Path]]:
    """Materialize section-transformation artifacts into the construction kit.

    SOP variant manifests are backed by per-section fact schemas whose facts
    were re-encoded into some artifact representation (support transcripts,
    customer-authored documents, ...). The variant is first *compiled*
    (:func:`tau2.hyper.transformations.compile.compile_variant_transformations`)
    into activations + a fact-coverage audit; each representation's
    registered transformation then neutralizes its artifacts so the
    Developer sees ordinary support material without section ids,
    generation filenames, or fact schemas.

    ``pooled`` transformations flatten artifacts from every section into one shared
    kit directory in a manifest-seeded shuffled section order, hiding section
    boundaries; ``named`` transformations are neutralized independently. Final
    assembly gives both placements generic artifact-genre filenames.

    Facts no active transformation covers are routed into an explicit-rules
    appendix (appended to ``sop.md``, or written as
    ``additional_policy_notes.md`` when the kit has no SOP yet) and logged as
    warnings — unless the manifest sets ``"uncovered_fact_policy": "error"``.
    The full coverage report is written *next to* the kit directory
    (``<kit>.transformation_report.json``), never inside it, because it
    enumerates the fact schemas the Developer must not see.

    ``modality_profile`` selects one rendition per artifact for the target
    model class (see :mod:`tau2.hyper.transformations.modality`): artifacts
    whose native modality exceeds the profile ship as their text rendition;
    phone-call records upgrade to their committed audio rendition under
    audio-capable profiles. The default profile reproduces pre-profile kits
    exactly.
    """
    profile = (
        DEFAULT_KIT_MODALITY_PROFILE
        if modality_profile is None
        else parse_modality_profile(modality_profile)
    )
    if manifest is None or not (manifest.get("section_source_schemas") or {}):
        if extra_kit_files:
            raise ValueError(
                "extra_kit_files require a variant manifest with "
                "section_source_schemas; the files would otherwise be dropped."
            )
        return None

    compilation = compile_variant_transformations(manifest)
    compilation.raise_on_errors()
    for warning in compilation.warnings:
        logger.warning(f"Variant {compilation.manifest_id}: {warning}")

    _require_client_held_facts_reachable(
        compilation.manifest_id,
        set(compilation.client_held_fact_ids),
        client_sections,
        client_has_custom_instructions,
    )

    pooled: dict[
        str,
        tuple[SectionTransformation, list[tuple[TransformationArtifact, bool]]],
    ] = {}
    named: list[tuple[SectionTransformation, TransformationArtifact, bool]] = []
    for activation in compilation.activations:
        transformation = activation.transformation
        if not activation.artifacts or not transformation.materializes:
            # Non-materializing coverage (SOP prose, client-held facts)
            # writes nothing into the kit.
            continue
        if transformation.placement == "pooled":
            _, pool = pooled.setdefault(
                transformation.representation, (transformation, [])
            )
            pool.extend(
                (artifact, activation.client_substitute)
                for artifact in activation.artifacts
            )
        else:
            named.extend(
                (transformation, artifact, activation.client_substitute)
                for artifact in activation.artifacts
            )

    created_dirs: list[Path] = []
    written_paths: set[str] = set()

    def _write_kit_file(kit_file: KitFile) -> None:
        relative = Path(kit_file.relative_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(
                f"Section transformation artifact escapes the kit: {relative}"
            )
        if kit_file.relative_path in written_paths:
            raise ValueError(
                f"Section transformation artifact collision: {kit_file.relative_path}"
            )
        written_paths.add(kit_file.relative_path)
        destination = out_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(kit_file.content)
        top_dir = out_dir / relative.parts[0]
        if top_dir.is_dir() and top_dir not in created_dirs:
            created_dirs.append(top_dir)

    substitutions: list[dict[str, str]] = []

    def _deliver(
        transformation: SectionTransformation,
        artifact: TransformationArtifact,
        ordinal: int,
        client_substitute: bool,
    ) -> KitFile:
        kit_file = transformation.deliver(artifact, ordinal, profile)
        kit_file.artifact_kind = transformation.representation
        kit_file.client_substitute = client_substitute
        kit_file.source_name = artifact.source_path.name
        for companion in kit_file.companions:
            companion.source_name = artifact.source_path.name
        if kit_file.substituted_from:
            delivered = sorted(
                {
                    modality_for_path(delivered_file.relative_path)
                    for delivered_file in (kit_file, *kit_file.companions)
                }
            )
            substitutions.append(
                {
                    "representation": transformation.representation,
                    "source": artifact.source_path.name,
                    "substituted_from": kit_file.substituted_from,
                    "delivered": "+".join(delivered),
                }
            )
        return kit_file

    kit_files: list[KitFile] = list(extra_kit_files or [])
    for transformation, artifacts in pooled.values():
        for ordinal, (artifact, client_substitute) in enumerate(artifacts, start=1):
            kit_files.append(
                _deliver(transformation, artifact, ordinal, client_substitute)
            )
    for ordinal, (transformation, artifact, client_substitute) in enumerate(
        named, start=1
    ):
        kit_files.append(_deliver(transformation, artifact, ordinal, client_substitute))
    client_replacements: list[dict[str, str]] = []
    kit_files = _substitute_client_carriers(kit_files, client_replacements)
    for kit_file in _pool_uploaded_material_names(kit_files):
        _write_kit_file(kit_file)
        for companion in kit_file.companions:
            _write_kit_file(companion)

    if compilation.fallback_applies:
        fallback_markdown = render_fallback_markdown(
            compilation.uncovered_facts, manifest_id=compilation.manifest_id
        )
        sop_path = out_dir / "sop.md"
        if sop_path.exists():
            sop_path.write_text(
                sop_path.read_text().rstrip() + "\n\n" + fallback_markdown
            )
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "additional_policy_notes.md").write_text(fallback_markdown)

    report = compilation.report()
    report["modality_profile"] = str(profile)
    if substitutions:
        report["modality_substitutions"] = substitutions
    if client_replacements:
        report["client_carrier_replacements"] = client_replacements
    report_path = out_dir.parent / f"{out_dir.name}.transformation_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    logger.debug(f"  Wrote transformation coverage report to {report_path}")

    return created_dirs or None


def _construction_reference_environment_kwargs(domain: str) -> dict[str, str]:
    """Return lightweight reference environment options for kit introspection."""
    if domain == "banking_knowledge":
        return {"retrieval_variant": "bm25"}
    return {}


def _load_construction_scoring_tasks(task: HyperTask):
    """Load the inner tasks used by a construction HyperTask."""
    from tau2.data_model.tasks import Task
    from tau2.run import get_tasks

    task_ids = task.test_task_ids or task.training_task_ids
    if not task_ids:
        return []

    if task.test_tasks_path:
        raw_tasks = load_file(DATA_DIR / task.test_tasks_path)
        if isinstance(raw_tasks, dict) and "tasks" in raw_tasks:
            raw_tasks = raw_tasks["tasks"]
        tasks = [Task.model_validate(raw_task) for raw_task in raw_tasks]
        tasks = [inner_task for inner_task in tasks if inner_task.id in task_ids]
        missing = set(task_ids) - {inner_task.id for inner_task in tasks}
        if missing:
            raise ValueError(
                f"Not all construction scoring tasks were found in "
                f"{task.test_tasks_path}: {missing}"
            )
        pack = load_selected_response_phrasing_rule_pack_for_task(task)
        return apply_response_phrasing_rule_pack_to_tasks(tasks, pack)

    tasks = get_tasks(task.source_domain, task_ids=task_ids)
    pack = load_selected_response_phrasing_rule_pack_for_task(task)
    return apply_response_phrasing_rule_pack_to_tasks(tasks, pack)


_SMALL_MODEL_CONTEXT_ROUTING_HINT = (
    "The available agent models are small enough that they may not reliably "
    "follow the complete Telecom instruction set when all of those instructions "
    "are placed in every main inference call.\n\n"
    "Your agent architecture must make a routing or classification model call "
    "before each main response call. Use that routing result to select only the "
    "instruction sections relevant to the current request and conversation state, "
    "and assemble a compact context or system prompt for the main call. Do not "
    "substitute brittle keyword or regular-expression routing for this model call; "
    "the routing or classification decision itself must come from the model. Do "
    "not place the complete Telecom runbook in every main inference call."
)

_STRICT_WORKFLOW_HINT = (
    "Use a strict workflow setup for as many of the Telecom flows, and as much of "
    "each flow, as is workflow-like. Explicitly define the ordered steps in each "
    "such workflow. Once the routing classifier activates a workflow, track its "
    "current step and use model calls to advance from one defined workflow step to "
    "the next. The active step must constrain which actions are valid.\n\n"
    "The routing classifier must always allow the user to switch from one workflow, "
    "flow, or journey to another when the user's request changes and the Telecom "
    "domain rules permit that switch. Do not trap the user in the currently active "
    "workflow."
)

_MODEL_TOOL_REVIEW_HINT = (
    "Whenever the main model proposes an agent-side tool call, your agent must make "
    "a separate model-based review call before executing that tool call. The "
    "reviewer must decide whether the proposed action is warranted at the current "
    "point in the procedure. If it is premature or unsupported, do not execute it; "
    "feed the reviewer's guidance back into the main-model loop. The classifier, "
    "main response, and tool reviewer may all use any allowed agent model. The "
    "implementation structure is otherwise up to you."
)

_DEVELOPER_HINT_PROFILES = {
    "small_model_context_routing_and_tool_review": "\n\n".join(
        (_SMALL_MODEL_CONTEXT_ROUTING_HINT, _MODEL_TOOL_REVIEW_HINT)
    ),
    "small_model_context_routing_tool_review_and_strict_workflows": "\n\n".join(
        (
            _SMALL_MODEL_CONTEXT_ROUTING_HINT,
            _STRICT_WORKFLOW_HINT,
            _MODEL_TOOL_REVIEW_HINT,
        )
    ),
}


def _developer_model_menu(
    model_configs: list[dict[str, Any]],
    *,
    meters_credits: bool,
) -> list[dict[str, Any]]:
    """Project the allowed-model list down to what the Developer can act on.

    ``tier`` records which profile tier owns a model for scoring and is only
    ever read harness-side. ``credit_rates`` prices metered usage, so a kit
    with no credit budget would otherwise ship a rate card that constrains
    nothing.
    """
    hidden = {"tier"} if meters_credits else {"tier", "credit_rates"}
    return [
        {key: value for key, value in config.items() if key not in hidden}
        for config in model_configs
    ]


def _developer_performance_requirements(
    requirements: list[Any],
) -> list[dict[str, Any]]:
    """Serialize requirements without the profile tier they were derived from.

    Tier names are a statement about where the task sits on the benchmark's
    difficulty scale, not about the agent being built, so the kit describes a
    budget by the models it meters and its price rather than by "easy" or
    "hard". The tiered ids stay on the task for harness-side reporting.
    """
    payloads = [
        requirement.model_dump(mode="json", exclude_none=True)
        for requirement in requirements
    ]
    credit_payloads = [payload for payload in payloads if payload["type"] == "credits"]
    for index, payload in enumerate(credit_payloads, start=1):
        payload.pop("tier", None)
        payload["id"] = (
            "agent_credit_budget"
            if len(credit_payloads) == 1
            else f"agent_credit_budget_{index}"
        )
    return payloads


def _build_construction_readme(
    domain: str,
    *,
    has_knowledge_base: bool = False,
    has_root_sop: bool = True,
    has_starting_workspace: bool = False,
    performance_requirements: Optional[list[dict[str, Any]]] = None,
    developer_hint_profile: Optional[str] = None,
    sample_scenario_count: int = 0,
) -> str:
    """Generate the README.md for a construction kit.

    ``has_root_sop`` is False when the variant delivers its policy text as
    customer material instead of a kit-root ``sop.md``; the README then
    points at the client-provided materials rather than "the SOP".

    ``has_starting_workspace`` is True when the kit ships an inherited
    implementation in ``workspace/`` (brownfield construction). The README
    stays neutral about the code's condition — auditing it against the
    supplied materials is part of the task.
    """
    sop_term = "the SOP" if has_root_sop else "the client-provided materials"
    operation_scope = (
        f"that implement the operations described across {sop_term} and "
        "`knowledge_base/`."
        if has_knowledge_base
        else f"that implement all the operations described in {sop_term}."
    )
    scenario_source = (
        f"scenarios in {sop_term} and knowledge base."
        if has_knowledge_base
        else f"scenarios in {sop_term}."
    )

    build_items = [
        (
            "`workspace/tools.py`",
            "A `ClientAPIToolKitBase` subclass with `@is_tool`-decorated "
            f"agent operations {operation_scope} Each method uses the injected "
            "`self.client_api`. See `framework/client_api_contract.md` and "
            "`client_api/openapi.yaml`.",
        ),
    ]

    # Brownfield kits state nothing here: the inherited code speaks for
    # itself, and the section preamble already gives the import contract.
    agent_entry_note = (
        ""
        if has_starting_workspace
        else "The interface-only scaffold defines "
        "the runtime entry point; implement the agent logic you want "
        "evaluated. "
    )
    build_items.append(
        (
            "`workspace/agent.py`",
            f"The agent implementation. {agent_entry_note}"
            "It may read any supplied kit artifact and may add "
            "helper, prompt, rule, index, or other evidence files under "
            "`workspace/` using any organization you choose. See "
            "`framework/agent_contract.md`.",
        )
    )

    workspace_area_note = (
        "`workspace/` already contains the organization's existing "
        "implementation, inherited as-is."
        if has_starting_workspace
        else "`workspace/` is the implementation area."
    )
    required_outputs = "\n\n".join(
        f"{index}. **{title}** — {body}"
        for index, (title, body) in enumerate(build_items, start=1)
    )
    performance_section = ""
    if performance_requirements:
        requirement_lines = []
        for requirement in performance_requirements:
            if requirement["type"] == "latency":
                requirement_lines.append(
                    f"- `{requirement['id']}`: p{requirement['percentile']} "
                    "latency for the complete `generate_next_message()` call "
                    f"must be at most {requirement['max_seconds']:g} seconds."
                )
            elif requirement["type"] == "credits":
                metered = requirement.get("models")
                if metered:
                    scope = ", ".join(f"`{model}`" for model in metered)
                    verb, subject = (
                        ("has", "that model")
                        if len(metered) == 1
                        else ("share", "those models")
                    )
                    requirement_lines.append(
                        f"- `{requirement['id']}`: {scope} {verb} a "
                        f"{requirement['budget']:.4f}-credit budget per "
                        "conversation. Every input and output token from every "
                        f"model-gateway call on {subject} counts; reasoning "
                        "tokens count as output."
                    )
                else:
                    requirement_lines.append(
                        f"- `{requirement['id']}`: model usage has a "
                        f"{requirement['budget']:.4f}-credit budget per conversation. "
                        "Every input and output token from every model-gateway call "
                        "counts; reasoning tokens count as output."
                    )
        credit_count = sum(
            1
            for requirement in performance_requirements
            if requirement["type"] == "credits"
        )
        overage_note = (
            " Each budget is metered separately and their overages add up."
            if credit_count > 1
            else ""
        )
        performance_section = (
            "## Performance requirements\n\n"
            + "\n".join(requirement_lines)
            + "\n\nUse `run_local_test` to inspect measured performance while "
            "you iterate. Credit overage is a soft penalty: final score is mean "
            "task reward minus the mean per-conversation fraction over budget, "
            f"floored at zero.{overage_note} Latency requirements remain hard "
            "gates.\n\n"
        )
    hint_section = ""
    if developer_hint_profile is not None:
        hint_section = (
            "## Suggested solution direction\n\n"
            + _DEVELOPER_HINT_PROFILES[developer_hint_profile]
            + "\n\n"
        )
    sample_scenarios_note = (
        (
            f"The client supplied {sample_scenario_count} sample customer "
            "scenarios recorded from their support operation; call "
            "`run_sample_scenarios()` to run the current candidate against "
            "all of them (runs are quota-limited). Each run returns the "
            "recorded conversations with the client's quality score for "
            "each; diagnosing what to improve is up to you. You can also write "
        )
        if sample_scenario_count
        else "No sample scenarios are provided; write "
    )
    return (
        f"# Build a Customer Service Agent: {domain}\n\n"
        "Your job is to build a robust customer service agent from the domain "
        "materials in this kit. The exact artifact set varies by domain; use "
        "the file tree and file-level documentation to orient yourself, then "
        "turn those materials into a working implementation.\n\n"
        "## What success means\n\n"
        "Agent quality is measured by the proportion of evaluation cases the "
        "agent passes. The evaluation cases are not visible in advance and may "
        "exercise the full range of behavior represented in the supplied "
        "materials: routine requests, complex multi-step or multi-intent "
        "requests, unusual edge cases, incomplete or changing information, and "
        "requests that must be declined or redirected.\n\n"
        "A case succeeds only when the agent handles the underlying operation "
        "correctly, leaves the system in the correct state, follows the domain "
        "rules, and communicates the right information to the customer. Subject "
        "to the framework contracts, no particular architecture or development "
        "process is required.\n\n"
        "## How to use this kit\n\n"
        "Treat the kit directory as the inventory of available materials. Source "
        "information may be spread across policy documents, API contracts, "
        "knowledge-base files, training records, or other client-provided artifacts. "
        "Read nearby file headers, directory indexes, and filenames as the "
        "description of each artifact.\n\n"
        f"{workspace_area_note} `framework/` explains the "
        "contracts your implementation must satisfy. `simulations/` stores "
        "artifacts written by candidate-only local simulation runs.\n\n"
        f"{hint_section}"
        "## Required outputs\n\n"
        "The evaluator imports these files as stable entry points. You can add "
        "helper modules, retrieval layers, planners, validation scenarios, or any other "
        "supporting architecture you need; the files below are only the "
        "integration surface.\n\n"
        f"{required_outputs}\n\n"
        "## Simulation environment\n\n"
        "You have access to a simulation environment where you can create "
        "simulated customer scenarios and let those customers interact with "
        f"your customer service agent. {sample_scenarios_note}"
        "your own JSON files based on "
        f"{scenario_source}\n\n"
        "See `framework/scenario_contract.md` for the customer scenario format.\n\n"
        "To run a candidate-only end-to-end simulation, call `run_local_test` "
        "tool with your scenario path, for example "
        '`run_local_test(task_path="workspace/my_customer_scenario.json")`. '
        "That tool runs only the scenario files you wrote against your own "
        "assistant toolkit. It routes "
        "customer/user tool calls through the provided customer-side runtime "
        "when the domain includes one. Each run writes a timestamped JSON "
        "artifact under `simulations/` so you can inspect prior transcripts "
        "and rewards later.\n"
        "For black-box behavioral checks, use natural-language assertions and inspect\n"
        "the returned transcript rather than depending on internal function names.\n\n"
        f"{performance_section}"
        "## Important\n\n"
        "- The allowed agent models and their inference constraints are fixed "
        "by `framework/deployment_manifest.json`. Your implementation may "
        "select among them.\n"
        "- Developer-authored scenarios are local probes, not the final "
        "evaluation distribution. Your final assessment depends on behavior "
        "across the broader set of unseen customer requests.\n"
    )


def _build_construction_agent_stub(domain: str) -> str:
    """Generate an architecture-neutral agent.py stub for construction kits."""
    return textwrap.dedent(f'''\
    """
    Agent for the {domain} domain.

    The evaluator imports this file and calls create_agent() to build
    the inner-loop agent.

    Contract:
        create_agent() -> agent

    The agent must implement:
        - get_init_state() -> state
        - generate_next_message(message, state) -> (AssistantMessage, state)

    Call ``get_agent_context()`` inside the factory to access the available
    actions, kit resources, model gateway, and runtime configuration.
    The model gateway is the supported path for model inference.
    """

    from tau2.hyper.agent_context import get_agent_context

    def create_agent():
        """Build and return the agent evaluated by the runtime.

        Call ``get_agent_context()`` here for runtime-provided resources.
        Implement any agent logic here.
        The returned object must provide ``get_init_state`` and
        ``generate_next_message`` as described above.
        """
        raise NotImplementedError(
            "Implement create_agent with the agent logic you want to evaluate."
        )
    ''')


def build_construction_kit(
    task: HyperTask,
    out_dir: Path,
    *,
    allowed_agent_models: Optional[list[dict]] = None,
    modality_profile: Optional[ModalityProfile | str] = None,
) -> Path:
    """Build a developer kit from a HyperTask.

    The kit contains the SOP, the configured business-state boundary,
    framework reference docs, and a workspace. No private evaluation tasks or
    canonical assistant tools are included.

    Args:
        task: The HyperTask (must have ``sop_document_path`` set).
        out_dir: Directory to create/populate.
        allowed_agent_models: Model configurations available to the agent.
        modality_profile: Per-run override of the task's kit materialization
            profile (see :mod:`tau2.hyper.transformations.modality`).

    Returns:
        Path to the kit directory.
    """
    if task.client_api_mode != "rest":
        raise ValueError(
            "Hyper-τ release tasks require client_api_mode='rest'; "
            "copied-database construction kits are no longer supported"
        )

    out_dir = Path(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(
            f"Kit directory {out_dir} already exists and is not empty."
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    domain = task.source_domain
    if modality_profile is None:
        modality_profile = task.modality_profile
    if modality_profile is not None:
        modality_profile = parse_modality_profile(modality_profile)
        logger.info(f"Kit modality profile: {modality_profile}")
    logger.info(f"Building construction kit for domain={domain} at {out_dir}")

    # 1. SOP document
    sop_variant_manifest, demoted_sop_file = _write_construction_sop(task, out_dir)
    _copy_sop_variant_materials(
        sop_variant_manifest,
        out_dir,
        extra_kit_files=[demoted_sop_file] if demoted_sop_file else None,
        modality_profile=modality_profile,
        client_sections=task.client_sections,
        client_has_custom_instructions=bool(
            task.client_enabled and task.client_instructions.strip()
        ),
    )
    has_root_sop = demoted_sop_file is None

    response_phrasing_pack = load_selected_response_phrasing_rule_pack_for_task(task)
    if response_phrasing_pack is not None:
        (out_dir / "response_phrasing_rules.md").write_text(
            render_response_phrasing_rules_markdown(response_phrasing_pack)
        )
        logger.debug("  Wrote response_phrasing_rules.md")

    # 2. Client-owned REST boundary. Business state remains in the trusted host;
    # the kit receives only its public contract and synthetic development seeds.
    client_api_deployment_profile = None
    if task.client_api_deployment_manifest is not None:
        client_api_deployment_profile = load_defect_profile(
            task.client_api_deployment_manifest,
            expected_domain=domain,
        )
    client_api_dir = out_dir / "client_api"
    client_api_dir.mkdir()
    contract = build_openapi_contract(
        build_environment(
            domain,
            env_kwargs=_construction_reference_environment_kwargs(domain),
        ),
        defect_profile=client_api_deployment_profile,
    )
    # JSON is valid YAML 1.2 and avoids adding a parser dependency to the
    # construction runtime.
    (client_api_dir / "openapi.yaml").write_text(json.dumps(contract, indent=2) + "\n")
    (client_api_dir / "development_seed.json").write_text(
        json.dumps(development_seed_manifest(domain), indent=2) + "\n"
    )
    logger.debug("  Wrote client_api/openapi.yaml")
    logger.debug("  Wrote client_api/development_seed.json")

    # 3. Optional knowledge-base documents for document-heavy construction domains.
    knowledge_base_path = _copy_knowledge_base(task, out_dir)
    if knowledge_base_path is not None:
        logger.debug(
            f"  Copied knowledge_base/ from {DATA_DIR / task.knowledge_base_path}"
        )

    if domain == "banking_knowledge":
        from tau2.hyper.client_api.banking_docs import (
            rewrite_banking_client_api_file,
        )

        document_roots = [out_dir / "sop.md", out_dir / "knowledge_base"]
        uploaded_materials = out_dir / "uploaded_materials"
        if uploaded_materials.exists():
            document_roots.append(uploaded_materials)
        rewritten_count = 0
        for root in document_roots:
            paths = [root] if root.is_file() else root.rglob("*")
            for path in paths:
                if not path.is_file():
                    continue
                before = path.read_bytes()
                rewrite_banking_client_api_file(path)
                rewritten_count += path.read_bytes() != before
        logger.debug(
            f"  Rewrote {rewritten_count} Banking documents as Client API contracts"
        )

    # 4. Framework contract docs. Copy only generic docs, not example domains
    # that could become accidental reference hints.
    framework_src = DATA_DIR / "tau2" / "hyper" / "framework_reference"
    framework_dest = out_dir / "framework"
    if framework_src.exists():
        framework_dest.mkdir()
        interface_contract = "client_api_contract.md"
        for doc_name in (
            "agent_contract.md",
            "scenario_contract.md",
            interface_contract,
        ):
            src_doc = framework_src / doc_name
            if src_doc.exists():
                shutil.copy2(src_doc, framework_dest / doc_name)
        interface_description = "How to write agent tools backed by the Client REST API"
        (framework_dest / "README.md").write_text(
            "# Agent Framework Reference\n\n"
            "This directory contains documentation for the tau2 agent "
            "framework — an open-source agent framework that this platform "
            "embeds within its own architecture. The `tau2.*` imports in "
            "these contracts come from that framework. Read these docs to "
            "understand the contracts your implementation must satisfy.\n\n"
            "## Files\n\n"
            "| File | What it covers |\n"
            "|------|---------------|\n"
            f"| `{interface_contract}` | {interface_description} |\n"
            "| `agent_contract.md` | How to write the agent "
            "(create_agent factory, HalfDuplexAgent) |\n"
            "| `scenario_contract.md` | How to write simulated customer "
            "scenarios |\n"
            "| `deployment_manifest.json` | Allowed agent models and "
            "performance requirements |\n"
        )
        logger.debug("  Copied framework/ contract docs")
    else:
        framework_dest.mkdir()
        logger.warning("  Framework reference docs not found, created empty dir")

    # 5. Workspace. Brownfield tasks ship an authored starting workspace;
    # greenfield tasks get empty stubs. Substitution, never overlay: mixing
    # generated stubs into an authored tree would create a texture tell
    # separating the two populations, so the authored tree must be complete.
    workspace = out_dir / "workspace"
    has_starting_workspace = task.starting_workspace_path is not None
    if has_starting_workspace:
        from tau2.hyper.sandbox.starting_workspace import (
            copy_starting_workspace_tree,
            resolve_starting_workspace_path,
        )

        source_workspace = resolve_starting_workspace_path(task.starting_workspace_path)
        copied = copy_starting_workspace_tree(source_workspace, workspace)
        logger.debug(
            f"  Seeded workspace/ from {source_workspace} ({len(copied)} files)"
        )
    else:
        workspace.mkdir()
        (workspace / "tools.py").write_text(
            textwrap.dedent(
                '''\
                """Agent tools backed by the client-owned REST API."""

                from tau2.hyper.client_api import ClientAPIToolKitBase


                class Tools(ClientAPIToolKitBase):
                    """Implement @is_tool methods using self.client_api."""
                '''
            )
        )
        (workspace / "agent.py").write_text(_build_construction_agent_stub(domain))
        logger.debug("  Created workspace/ with empty stubs")

    # 6. Developer deployment manifest (allowed inner models and constraints).
    # Runtime wiring — the inner user-simulator settings, the source-domain
    # name, and the contract digest — deliberately never enters the kit:
    # anything on disk in the kit is Developer-readable, and the Developer has
    # no use for it. The harness injects it host-side instead (builder
    # local-test wiring and the sealed candidate's configure handshake).
    model_constraints = allowed_agent_models or task.hyper.allowed_agent_models
    if model_constraints is None:
        constraints = {}
        if task.hyper.agent_reasoning_effort:
            constraints["reasoning_effort"] = task.hyper.agent_reasoning_effort
        model_constraints = [
            {
                "model": task.hyper.agent_llm or "gpt-5.5",
                "constraints": constraints,
            }
        ]
    if not model_constraints:
        raise ValueError("At least one allowed agent model must be configured")
    performance_requirements = _developer_performance_requirements(
        task.performance_requirements
    )
    # A tier spec whose budgets are all null leaves nothing metered, so the
    # kit must not present credit vocabulary the Developer cannot act on and
    # the harness will never score.
    meters_credits = any(
        requirement["type"] == "credits" for requirement in performance_requirements
    )
    manifest = {
        "allowed_agent_models": _developer_model_menu(
            model_constraints, meters_credits=meters_credits
        ),
        "performance_requirements": performance_requirements,
    }
    # The Client-API contract version lives only in openapi.yaml's
    # info.version; the manifest never repeats it.
    # Response-phrasing requirements reach the Developer only through the
    # customer-facing response_phrasing_rules.md spec. The grader's compiled
    # assertions stay harness-side (the evaluator loads them from the task).
    (out_dir / "framework" / "deployment_manifest.json").write_text(
        json.dumps(manifest, indent=2)
    )
    logger.debug("  Wrote framework/deployment_manifest.json")

    # 7. README
    (out_dir / "README.md").write_text(
        _build_construction_readme(
            domain,
            has_knowledge_base=knowledge_base_path is not None,
            has_root_sop=has_root_sop,
            has_starting_workspace=has_starting_workspace,
            performance_requirements=manifest["performance_requirements"],
            developer_hint_profile=task.developer_hint_profile,
            sample_scenario_count=len(task.training_task_ids),
        )
    )
    logger.debug("  Wrote README.md")

    # 8. Simulations output directory for candidate-only simulation artifacts.
    (out_dir / "simulations").mkdir()

    logger.info(
        f"Construction kit built at {out_dir} ({len(list(out_dir.rglob('*')))} files)"
    )
    return out_dir


def build_kit(
    task: HyperTask,
    out_dir: Path,
    *,
    allowed_agent_models: Optional[list[dict]] = None,
    modality_profile: Optional[ModalityProfile | str] = None,
) -> Path:
    """Build a developer kit directory from a HyperTask.

    Creates a self-contained construction workspace at ``out_dir`` with
    domain artifacts derived from the task. The kit includes only local
    development data; no deployment database rows, future customer requests,
    or production traces are materialized.

    Every maintained task is a construction task; the legacy
    policy-perturbation kit builder was removed together with the structured
    meta-tool mode.
    """
    return build_construction_kit(
        task,
        out_dir,
        allowed_agent_models=allowed_agent_models,
        modality_profile=modality_profile,
    )
