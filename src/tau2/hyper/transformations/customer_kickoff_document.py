"""Customer kickoff documents used as sparse requirements evidence.

Kickoff questionnaires are ordinary customer-authored Markdown documents.
Their business filenames remain author-side; the assembled kit exposes only a
generic intake-form name while schema paths and fact annotations remain hidden.
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

_TEXT_SUFFIXES = {".md", ".txt"}


class CustomerKickoffDocumentTransformation(SectionTransformation):
    """Deliver a partially completed customer kickoff questionnaire."""

    representation = "customer_kickoff_document"
    aliases = ("customer_document", "kickoff_document")
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
                "customer_kickoff_document transformation for section schema "
                f"{schema.get('id', '<unknown>')!r} must declare artifacts "
                "with path, kit_filename, and included_fact_ids entries"
            )

        artifacts = []
        for entry in declared:
            metadata = {
                key: value
                for key, value in entry.items()
                if key not in {"included_fact_ids", "path"}
            }
            if metadata.get("eval_manifest_path"):
                metadata["eval_manifest_path"] = self._resolve(
                    metadata["eval_manifest_path"]
                )
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
        kit_filename = str(artifact.metadata["kit_filename"])
        return KitFile(
            relative_path=f"{self.kit_dirname}/{kit_filename}",
            content=artifact.source_path.read_bytes(),
        )

    def to_text(self, artifact: TransformationArtifact) -> str:
        return artifact.source_path.read_text()

    def validate(
        self, schema: dict[str, Any], artifacts: list[TransformationArtifact]
    ) -> list[str]:
        issues = super().validate(schema, artifacts)
        seen_filenames: set[str] = set()
        for artifact in artifacts:
            name = artifact.source_path.name
            if artifact.source_path.suffix.lower() not in _TEXT_SUFFIXES:
                issues.append(
                    f"{name}: kickoff document must be one of {sorted(_TEXT_SUFFIXES)}"
                )
            if not artifact.source_path.is_file():
                issues.append(f"{name}: kickoff document file not found")

            kit_filename = artifact.metadata.get("kit_filename")
            if not kit_filename:
                issues.append(f"{name}: kit_filename is required")
                continue
            kit_filename = str(kit_filename)
            if Path(kit_filename).name != kit_filename:
                issues.append(f"{name}: kit_filename must be a bare filename")
            if Path(kit_filename).suffix.lower() not in _TEXT_SUFFIXES:
                issues.append(
                    f"{name}: kit_filename must end with one of "
                    f"{sorted(_TEXT_SUFFIXES)}"
                )
            if kit_filename in seen_filenames:
                issues.append(f"{name}: duplicate kit_filename {kit_filename!r}")
            seen_filenames.add(kit_filename)

            manifest_path = artifact.metadata.get("eval_manifest_path")
            if manifest_path:
                issues.extend(
                    self._validate_eval_manifest(
                        name,
                        Path(manifest_path),
                        artifact.included_fact_ids,
                    )
                )
        return issues

    @staticmethod
    def _validate_eval_manifest(
        artifact_name: str,
        manifest_path: Path,
        included_fact_ids: list[str],
    ) -> list[str]:
        if not manifest_path.is_file():
            return [f"{artifact_name}: eval_manifest_path not found"]
        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError as error:
            return [f"{artifact_name}: invalid eval manifest JSON ({error})"]
        facts = manifest.get("authoritative_facts") or []
        manifest_fact_ids = [
            str(fact.get("id"))
            for fact in facts
            if isinstance(fact, dict) and fact.get("id")
        ]
        if set(manifest_fact_ids) != set(included_fact_ids):
            return [
                f"{artifact_name}: eval manifest authoritative facts "
                "must exactly match included_fact_ids"
            ]
        return []

    @staticmethod
    def _resolve(path: str | Path) -> Path:
        resolved = Path(path)
        if resolved.is_absolute():
            return resolved
        return DATA_DIR / resolved


register_transformation(CustomerKickoffDocumentTransformation())
