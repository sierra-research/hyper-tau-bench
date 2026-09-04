"""Versioned business-reference attachments used as policy evidence.

The representation deliberately accepts ordinary office files rather than
requiring every attachment to masquerade as a presentation.  A plain-text
sidecar remains author-side so fact coverage can be audited without depending
on binary extraction support in the construction runtime.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tau2.hyper.transformations.base import (
    KitFile,
    SectionTransformation,
    TransformationArtifact,
    register_transformation,
)
from tau2.utils.utils import DATA_DIR

_SUPPORTED_SUFFIXES = {
    ".csv",
    ".docx",
    ".html",
    ".md",
    ".pdf",
    ".pptx",
    ".txt",
    ".xlsx",
}


class ReferenceDocumentTransformation(SectionTransformation):
    """Deliver versioned office attachments with author-side text sources."""

    representation = "reference_document"
    aliases = ("business_reference_document", "reference_attachment")
    placement = "named"
    carries_agent_utterances = False

    def discover_artifacts(
        self,
        schema: dict[str, Any],
        schema_path: Path,
        spec: dict[str, Any],
    ) -> list[TransformationArtifact]:
        del schema_path
        declared = spec.get("artifacts")
        if not declared:
            raise ValueError(
                "reference_document transformation for section schema "
                f"{schema.get('id', '<unknown>')!r} must declare artifacts"
            )

        manifest_path = spec.get("eval_manifest_path")
        resolved_manifest = self._resolve(manifest_path) if manifest_path else None
        artifacts = []
        for entry in declared:
            metadata = {
                key: value
                for key, value in entry.items()
                if key not in {"included_fact_ids", "path"}
            }
            if metadata.get("text_source_path"):
                metadata["text_source_path"] = self._resolve(
                    metadata["text_source_path"]
                )
            if resolved_manifest:
                metadata["eval_manifest_path"] = resolved_manifest
            artifacts.append(
                TransformationArtifact(
                    source_path=self._resolve(entry["path"]),
                    included_fact_ids=list(entry.get("included_fact_ids", [])),
                    metadata=metadata,
                )
            )
        return artifacts

    def neutralize(self, artifact: TransformationArtifact, ordinal: int) -> KitFile:
        del ordinal
        kit_filename = str(
            artifact.metadata.get("kit_filename", artifact.source_path.name)
        )
        return KitFile(
            relative_path=f"{self.kit_dirname}/{kit_filename}",
            content=artifact.source_path.read_bytes(),
            artifact_kind=self.representation,
        )

    def to_text(self, artifact: TransformationArtifact) -> str:
        text_source = artifact.metadata.get("text_source_path")
        if text_source:
            return Path(text_source).read_text().rstrip() + "\n"
        if artifact.source_path.suffix.lower() in {".csv", ".html", ".md", ".txt"}:
            return artifact.source_path.read_text().rstrip() + "\n"
        return ""

    def validate(
        self, schema: dict[str, Any], artifacts: list[TransformationArtifact]
    ) -> list[str]:
        issues = super().validate(schema, artifacts)
        seen_filenames: set[str] = set()
        for artifact in artifacts:
            path = artifact.source_path
            name = path.name
            suffix = path.suffix.lower()
            if suffix not in _SUPPORTED_SUFFIXES:
                issues.append(
                    f"{name}: reference attachment must end with one of "
                    f"{sorted(_SUPPORTED_SUFFIXES)}"
                )
            if not path.is_file():
                issues.append(f"{name}: reference attachment not found")
                continue

            kit_filename = str(artifact.metadata.get("kit_filename", name))
            if Path(kit_filename).name != kit_filename:
                issues.append(f"{name}: kit_filename must be a bare filename")
            elif Path(kit_filename).suffix.lower() != suffix:
                issues.append(f"{name}: kit_filename must preserve the source suffix")
            elif kit_filename in seen_filenames:
                issues.append(f"{name}: duplicate kit_filename {kit_filename!r}")
            seen_filenames.add(kit_filename)

            text_source = artifact.metadata.get("text_source_path")
            if suffix in {".docx", ".pdf", ".pptx", ".xlsx"} and not text_source:
                issues.append(f"{name}: binary attachment requires text_source_path")
            elif text_source and not Path(text_source).is_file():
                issues.append(f"{name}: text_source_path not found")

        manifest_paths = {
            Path(path)
            for artifact in artifacts
            if (path := artifact.metadata.get("eval_manifest_path"))
        }
        if len(manifest_paths) > 1:
            issues.append("reference attachments declare more than one eval manifest")
        elif manifest_paths:
            issues.extend(
                self._validate_eval_manifest(next(iter(manifest_paths)), artifacts)
            )
        return issues

    @staticmethod
    def _validate_eval_manifest(
        manifest_path: Path,
        artifacts: list[TransformationArtifact],
    ) -> list[str]:
        if not manifest_path.is_file():
            return ["reference attachment eval_manifest_path not found"]
        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError as error:
            return [f"reference attachment manifest is invalid JSON ({error})"]

        declared = {
            str(entry.get("filename")): set(entry.get("authoritative_fact_ids", []))
            for entry in manifest.get("artifacts") or []
            if isinstance(entry, dict) and entry.get("filename")
        }
        actual = {
            str(artifact.metadata.get("kit_filename", artifact.source_path.name)): set(
                artifact.included_fact_ids
            )
            for artifact in artifacts
        }
        if declared != actual:
            return [
                "reference attachment eval manifest must exactly match artifact "
                "filenames and included_fact_ids"
            ]
        return []

    @staticmethod
    def _resolve(path: str | Path) -> Path:
        resolved = Path(path)
        if resolved.is_absolute():
            return resolved
        return DATA_DIR / resolved


register_transformation(ReferenceDocumentTransformation())
