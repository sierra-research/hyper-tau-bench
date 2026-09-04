"""Transformation helpers for assembling section-level SOP variants.

Construction kits still receive a single ``sop.md``. These helpers let a
Hyper-τ task describe that SOP as a canonical markdown document plus optional
section replacements or appended sections, so experiments can vary how specific
SOP sections are represented without inventing a new kit layout for every
variant.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from tau2.hyper.transformations.bundles import (
    normalize_section_bundle_selection,
    resolve_transformation_bundle,
)
from tau2.utils.utils import DATA_DIR


def _resolve_data_relative_path(path: str | Path, *, data_dir: Path = DATA_DIR) -> Path:
    """Resolve a path that may be absolute or relative to ``DATA_DIR``."""
    path = Path(path)
    if path.is_absolute():
        return path
    return data_dir / path


def load_sop_variant_manifest(
    manifest_path: str | Path, *, data_dir: Path = DATA_DIR
) -> dict[str, Any]:
    """Load a SOP variant manifest from disk."""
    resolved_path = _resolve_data_relative_path(manifest_path, data_dir=data_dir)
    if not resolved_path.exists():
        raise FileNotFoundError(f"SOP variant manifest not found: {resolved_path}")
    return json.loads(resolved_path.read_text())


def _section_heading_pattern(heading: str) -> re.Pattern[str]:
    escaped = re.escape(heading)
    return re.compile(rf"^{escaped}[ \t]*$", re.MULTILINE)


def _split_markdown_sections(
    markdown: str, section_order: list[dict[str, Any]]
) -> dict[str, str]:
    """Split markdown into blocks using manifest-declared level-2 headings."""
    if not section_order:
        raise ValueError("SOP variant manifest must declare section_order")

    front_matter = section_order[0]
    if front_matter.get("id") != "front_matter" or front_matter.get("heading"):
        raise ValueError(
            "section_order must start with a front_matter entry with no heading"
        )

    heading_entries = [entry for entry in section_order[1:] if entry.get("heading")]
    matches: list[tuple[dict[str, Any], re.Match[str]]] = []
    for entry in heading_entries:
        match = _section_heading_pattern(entry["heading"]).search(markdown)
        if match is None:
            raise ValueError(f"Section heading not found: {entry['heading']}")
        matches.append((entry, match))

    starts = [match.start() for _, match in matches]
    if starts != sorted(starts):
        raise ValueError("section_order does not match the order in the SOP")

    if not matches:
        return {str(front_matter["id"]): markdown}

    sections: dict[str, str] = {
        str(front_matter["id"]): markdown[: matches[0][1].start()]
    }
    for index, (entry, match) in enumerate(matches):
        end = (
            matches[index + 1][1].start() if index + 1 < len(matches) else len(markdown)
        )
        sections[str(entry["id"])] = markdown[match.start() : end]
    return sections


def _bundle_section_replacements(
    manifest: dict[str, Any], *, data_dir: Path
) -> dict[str, str]:
    """Resolve bundle-owned SOP stubs into section replacement paths."""
    selections = normalize_section_bundle_selection(manifest)
    source_schemas = manifest.get("section_source_schemas") or {}
    replacements: dict[str, str] = {}
    for section_id, bundle_ids in selections.items():
        schema_source = source_schemas.get(section_id)
        if not schema_source:
            raise ValueError(
                f"section bundle selection for {section_id!r} has no "
                "section_source_schemas entry"
            )
        schema_path = _resolve_data_relative_path(str(schema_source), data_dir=data_dir)
        if not schema_path.exists():
            raise FileNotFoundError(f"SOP source schema not found: {schema_path}")
        schema = json.loads(schema_path.read_text())
        if not isinstance(schema, dict):
            raise ValueError(f"SOP source schema must be a JSON object: {schema_path}")
        stub_paths: set[str] = set()
        for bundle_id in bundle_ids:
            bundle = resolve_transformation_bundle(schema, bundle_id)
            stub_path = bundle.get("stub_path")
            if not isinstance(stub_path, str) or not stub_path.strip():
                raise ValueError(
                    f"selected bundle {bundle_id!r} for section "
                    f"{section_id!r} must declare a non-empty string stub_path"
                )
            stub_paths.add(stub_path)
        if len(stub_paths) != 1:
            raise ValueError(
                f"selected bundles for section {section_id!r} must resolve "
                f"to exactly one SOP stub_path, got {sorted(stub_paths)}"
            )
        replacements[section_id] = stub_paths.pop()
    return replacements


def assemble_sop_variant(
    manifest_path: str | Path,
    *,
    data_dir: Path = DATA_DIR,
    drop_replaced_sections: bool = False,
) -> str:
    """Assemble a SOP variant manifest into final markdown text.

    A manifest has a canonical SOP and an ordered list of section ids. The
    optional ``section_replacements`` map replaces one or more complete section
    blocks with markdown files. Replacement files are paths relative to
    ``DATA_DIR`` and should include the section heading they replace.
    The optional ``append_sections`` list appends additional markdown blocks
    after the canonical SOP. Appended sections are useful for domains where
    transcript-induced material represents selected knowledge-base bundles
    rather than literal sections of the short canonical handbook.
    A ``section_bundles`` selection whose section id is not one of the
    canonical SOP headings (a composed journey section) is appended the same
    way: its bundle stub, which carries its own heading, lands after the
    canonical sections.

    With ``drop_replaced_sections`` every replaced or bundle-backed section is
    omitted from the output instead of stubbed. The exception is
    ``front_matter``: a front-matter replacement is a content override, not a
    pointer to externalized facts, so it is always applied. The result is a
    prose-only document carrying just the canonical sections — the shape a
    variant needs when its policy text is delivered as one more customer
    document rather than as a kit-root SOP.
    """
    manifest = load_sop_variant_manifest(manifest_path, data_dir=data_dir)
    canonical_path = _resolve_data_relative_path(
        manifest["canonical_sop_path"], data_dir=data_dir
    )
    if not canonical_path.exists():
        raise FileNotFoundError(f"Canonical SOP not found: {canonical_path}")

    canonical_markdown = canonical_path.read_text()
    section_order = manifest.get("section_order") or []
    canonical_sections = _split_markdown_sections(canonical_markdown, section_order)

    replacements = dict(manifest.get("section_replacements") or {})
    bundle_replacements = _bundle_section_replacements(manifest, data_dir=data_dir)
    conflicts = set(replacements) & set(bundle_replacements)
    if conflicts:
        raise ValueError(
            "Sections cannot use both section_replacements and "
            f"section_bundles: {sorted(conflicts)}"
        )
    known_section_ids = set(canonical_sections)

    # A bundle-backed section whose id is not a canonical SOP heading is a
    # composed journey (its facts come from component headings), so its stub
    # cannot be spliced in place. Append it as a self-headed section instead;
    # in drop mode it is omitted, exactly like a spliced bundle stub.
    appended_bundle_stubs = [
        {"id": section_id, "path": path}
        for section_id, path in bundle_replacements.items()
        if section_id not in known_section_ids
    ]
    for entry in appended_bundle_stubs:
        bundle_replacements.pop(str(entry["id"]))
    replacements.update(bundle_replacements)

    append_sections = list(manifest.get("append_sections") or [])
    if not drop_replaced_sections:
        # Manifests may keep a bundle-backed section's stub in
        # append_sections while section_bundles resolves the same section to
        # the same stub file. Appending both would print the section block
        # twice in the assembled SOP, so a bundle stub whose file is already
        # declared in append_sections is skipped.
        declared_stub_paths = {
            _resolve_data_relative_path(str(section["path"]), data_dir=data_dir)
            for section in append_sections
            if section.get("path")
        }
        append_sections.extend(
            stub
            for stub in appended_bundle_stubs
            if _resolve_data_relative_path(str(stub["path"]), data_dir=data_dir)
            not in declared_stub_paths
        )

    if not replacements:
        return _append_sop_variant_sections(
            canonical_markdown,
            append_sections,
            data_dir=data_dir,
        )

    unknown_replacements = set(replacements) - known_section_ids
    if unknown_replacements:
        unknown = ", ".join(sorted(unknown_replacements))
        raise ValueError(f"Replacement section ids are not in section_order: {unknown}")

    assembled_blocks: list[str] = []
    for section in section_order:
        section_id = str(section["id"])
        replacement_path = replacements.get(section_id)
        if drop_replaced_sections and replacement_path and section_id != "front_matter":
            continue
        if replacement_path:
            resolved_replacement = _resolve_data_relative_path(
                replacement_path, data_dir=data_dir
            )
            if not resolved_replacement.exists():
                raise FileNotFoundError(
                    f"SOP replacement section not found: {resolved_replacement}"
                )
            block = resolved_replacement.read_text().rstrip() + "\n"
            if section_id != "front_matter":
                block += "\n"
            assembled_blocks.append(block)
        else:
            assembled_blocks.append(canonical_sections[section_id])

    assembled_markdown = "".join(assembled_blocks)
    return _append_sop_variant_sections(
        assembled_markdown,
        append_sections,
        data_dir=data_dir,
    )


def _append_sop_variant_sections(
    assembled_markdown: str,
    append_sections: list[dict[str, Any]],
    *,
    data_dir: Path = DATA_DIR,
) -> str:
    """Append manifest-declared markdown blocks to an assembled SOP."""
    if not append_sections:
        return assembled_markdown

    appended_blocks: list[str] = []
    for section in append_sections:
        path = section.get("path")
        if not path:
            section_id = section.get("id", "<unknown>")
            raise ValueError(f"Appended SOP section {section_id!r} must include path")

        resolved_path = _resolve_data_relative_path(path, data_dir=data_dir)
        if not resolved_path.exists():
            raise FileNotFoundError(f"Appended SOP section not found: {resolved_path}")
        appended_blocks.append(resolved_path.read_text().rstrip())

    return assembled_markdown.rstrip() + "\n\n" + "\n\n".join(appended_blocks) + "\n"


_NUMBERED_SECTION_HEADING = re.compile(r"^## (\d+)\.(?=\s)", re.MULTILINE)


def renumber_numbered_section_headings(markdown: str) -> str:
    """Renumber ``## N.`` section headings sequentially from 1.

    Dropping sections from an assembled SOP leaves numbering gaps
    (1, 3, 4, ..., 11) that advertise exactly where material was removed.
    Rewriting the survivors to 1..N makes the document read as complete.
    Only the level-2 heading numbers change; body text is untouched.
    """
    counter = 0

    def _replace(match: re.Match[str]) -> str:
        nonlocal counter
        counter += 1
        return f"## {counter}."

    return _NUMBERED_SECTION_HEADING.sub(_replace, markdown)
