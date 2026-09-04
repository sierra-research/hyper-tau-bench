"""Schema helpers for coordinated transformation bundles.

A transformation spec describes one reusable artifact set. A transformation
bundle describes how several of those artifact sets jointly represent a
cohesive set of facts. Bundle members explicitly own facts so compilation can
prove that every bundled fact has exactly one authoritative representation.
"""

from __future__ import annotations

from typing import Any

from tau2.hyper.transformations.base import (
    resolve_section_transformations,
    resolve_transformation_imports,
)


def resolve_transformation_bundles(
    schema: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return the transformation bundles declared by a section schema."""
    bundles = [
        *(schema.get("transformation_bundles") or []),
        *[
            bundle
            for payload in resolve_transformation_imports(schema)
            for bundle in payload.get("transformation_bundles") or []
        ],
    ]
    if not isinstance(bundles, list):
        raise ValueError("transformation_bundles must be a list")
    if not all(isinstance(bundle, dict) for bundle in bundles):
        raise ValueError("every transformation_bundles entry must be an object")
    return list(bundles)


def resolve_transformation_spec_by_id(
    schema: dict[str, Any], transformation_id: str
) -> dict[str, Any]:
    """Resolve one uniquely named transformation spec."""
    matches = [
        spec
        for spec in resolve_section_transformations(schema)
        if spec.get("id") == transformation_id
    ]
    if not matches:
        raise ValueError(
            f"unknown transformation_id {transformation_id!r}; bundle members "
            "must reference a schema transformation with that id"
        )
    if len(matches) > 1:
        raise ValueError(f"duplicate transformation id {transformation_id!r}")
    return matches[0]


def resolve_transformation_bundle(
    schema: dict[str, Any], bundle_id: str
) -> dict[str, Any]:
    """Resolve one uniquely named transformation bundle."""
    matches = [
        bundle
        for bundle in resolve_transformation_bundles(schema)
        if bundle.get("id") == bundle_id
    ]
    if not matches:
        raise ValueError(f"unknown transformation bundle {bundle_id!r}")
    if len(matches) > 1:
        raise ValueError(f"duplicate transformation bundle id {bundle_id!r}")
    return matches[0]


def normalize_section_bundle_selection(
    manifest: dict[str, Any],
) -> dict[str, list[str]]:
    """Normalize manifest ``section_bundles`` values to ordered id lists.

    A string is convenient for the common one-bundle-per-section case. Lists
    allow a future variant to compose several disjoint bundles for a section.
    """
    raw = manifest.get("section_bundles") or {}
    if not isinstance(raw, dict):
        raise ValueError("section_bundles must be an object")

    normalized: dict[str, list[str]] = {}
    for raw_section_id, raw_bundle_ids in raw.items():
        section_id = str(raw_section_id)
        if isinstance(raw_bundle_ids, str):
            bundle_ids = [raw_bundle_ids]
        elif isinstance(raw_bundle_ids, list) and all(
            isinstance(bundle_id, str) for bundle_id in raw_bundle_ids
        ):
            bundle_ids = list(raw_bundle_ids)
        else:
            raise ValueError(
                f"section_bundles[{section_id!r}] must be a bundle id or "
                "a list of bundle ids"
            )
        if not bundle_ids:
            raise ValueError(
                f"section_bundles[{section_id!r}] must select at least one bundle"
            )
        if len(bundle_ids) != len(set(bundle_ids)):
            raise ValueError(
                f"section_bundles[{section_id!r}] selects a duplicate bundle id"
            )
        normalized[section_id] = bundle_ids
    return normalized
