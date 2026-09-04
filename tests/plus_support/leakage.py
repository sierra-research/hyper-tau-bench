"""Leakage-scan mechanics for the plus corpora.

Ported verbatim out of the retired maintainer-only port machinery so the
committed-tree leakage gates keep the exact matching semantics they were
written against (notably the literal prefilter, which is what makes an
identifier scan with thousands of bounded regexes tractable over large
generated artifacts).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

FACT_ID_LIST_KEYS = {
    "fact_ids",
    "included_fact_ids",
    "authoritative_fact_ids",
    "depends_on_fact_ids",
    "intentionally_omitted_fact_ids",
}


def iter_fact_id_references(schema: dict[str, Any]) -> set[str]:
    """Every fact id referenced (not defined) anywhere in a schema."""
    refs: set[str] = set()

    def walk(node: Any, key: str | None) -> None:
        if isinstance(node, dict):
            for child_key, value in node.items():
                walk(value, child_key)
        elif isinstance(node, list):
            if key in FACT_ID_LIST_KEYS:
                refs.update(item for item in node if isinstance(item, str))
            else:
                for item in node:
                    walk(item, key)

    walk(schema, None)
    return refs


def scan_leakage(
    paths: list[Path], forbidden_patterns: list[str], label: str = "Canonical leakage"
) -> None:
    """Raise on the first forbidden pattern found in any of ``paths``."""

    def literal_hint(pattern: str) -> str | None:
        """Return a required literal fragment for the simple leakage patterns.

        Identifier scans can contain thousands of individually bounded regexes.
        Searching every regex across every large generated artifact made the
        Plus integrity gate effectively unbounded. These patterns have no
        alternation, so a longest literal fragment is a safe prefilter before
        the regex search.
        """
        if "|" in pattern:
            return None
        cleaned = re.sub(r"\(\?[a-zA-Z-]+\)", "", pattern)
        cleaned = re.sub(r"\(\?(?:<[=!]|[=!]).*?\)", " ", cleaned)
        if "?" in cleaned or "*" in cleaned or re.search(r"\{0(?:,|\})", cleaned):
            return None
        cleaned = cleaned.replace(r"\b", " ")
        cleaned = re.sub(r"\[[^]]*\]", " ", cleaned)
        cleaned = re.sub(r"\\([.^$*+?{}\[\]|()/#@_-])", r"\1", cleaned)
        cleaned = re.sub(r"\\[A-Za-z]", " ", cleaned)
        candidates = re.findall(r"[A-Za-z0-9_@./#-]{4,}", cleaned)
        return max(candidates, key=len) if candidates else None

    compiled = [
        (re.compile(pattern), literal_hint(pattern)) for pattern in forbidden_patterns
    ]
    for path in paths:
        text = path.read_text()
        folded = text.casefold()
        for pattern, hint in compiled:
            if hint is not None and hint.casefold() not in folded:
                continue
            if pattern.search(text):
                raise ValueError(f"{label} {pattern.pattern!r} in {path}")
