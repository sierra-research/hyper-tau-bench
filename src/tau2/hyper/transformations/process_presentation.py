"""Business-process presentation transformation.

The Developer receives a PDF under ``uploaded_materials/``. Editable PowerPoint
files, source code, generated screen assets, and evaluation metadata stay
author-side. A separate text source makes slide-level fact coverage
deterministic without depending on PDF text extraction.
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


class ProcessPresentationTransformation(SectionTransformation):
    """Represent process facts in a customer-authored PDF presentation."""

    representation = "process_presentation"
    aliases = ("business_process_presentation", "presentation_deck")
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
                "process_presentation transformation for section schema "
                f"{schema.get('id', '<unknown>')!r} must declare artifacts "
                "with path, text_source_path, page_fact_ids, and "
                "included_fact_ids entries"
            )

        artifacts = []
        for entry in declared:
            metadata = {
                key: value
                for key, value in entry.items()
                if key not in {"included_fact_ids", "path"}
            }
            for path_key in (
                "author_source_path",
                "eval_manifest_path",
                "generation_source_path",
                "text_source_path",
            ):
                if metadata.get(path_key):
                    metadata[path_key] = self._resolve(metadata[path_key])
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
        )

    def to_text(self, artifact: TransformationArtifact) -> str:
        text_source_path = artifact.metadata.get("text_source_path")
        if not text_source_path:
            return ""
        return Path(text_source_path).read_text().rstrip() + "\n"

    def validate(
        self, schema: dict[str, Any], artifacts: list[TransformationArtifact]
    ) -> list[str]:
        issues = super().validate(schema, artifacts)
        seen_filenames: set[str] = set()
        for artifact in artifacts:
            name = artifact.source_path.name
            if artifact.source_path.suffix.lower() != ".pdf":
                issues.append(f"{name}: process presentation must be a PDF")
            if not artifact.source_path.is_file():
                issues.append(f"{name}: process presentation file not found")

            text_source_path = artifact.metadata.get("text_source_path")
            if not text_source_path:
                issues.append(f"{name}: text_source_path is required")
            elif not Path(text_source_path).is_file():
                issues.append(f"{name}: text_source_path not found")
            author_source_path = artifact.metadata.get("author_source_path")
            if author_source_path and not Path(author_source_path).is_file():
                issues.append(f"{name}: author_source_path not found")
            generation_source_path = artifact.metadata.get("generation_source_path")
            if generation_source_path and not Path(generation_source_path).is_file():
                issues.append(f"{name}: generation_source_path not found")

            kit_filename = str(
                artifact.metadata.get("kit_filename", artifact.source_path.name)
            )
            if Path(kit_filename).name != kit_filename:
                issues.append(f"{name}: kit_filename must be a plain filename")
            if Path(kit_filename).suffix.lower() != ".pdf":
                issues.append(f"{name}: kit_filename must end with .pdf")
            if kit_filename in seen_filenames:
                issues.append(f"{name}: duplicate kit_filename {kit_filename!r}")
            seen_filenames.add(kit_filename)

            page_fact_ids = artifact.metadata.get("page_fact_ids")
            if not isinstance(page_fact_ids, list) or not page_fact_ids:
                issues.append(f"{name}: page_fact_ids is required")
                continue

            page_numbers: set[int] = set()
            mapped_fact_ids: list[str] = []
            for page_entry in page_fact_ids:
                if not isinstance(page_entry, dict):
                    issues.append(f"{name}: page_fact_ids entries must be objects")
                    continue
                page = page_entry.get("page")
                fact_ids = page_entry.get("fact_ids")
                if not isinstance(page, int) or page < 1:
                    issues.append(
                        f"{name}: page_fact_ids page must be a positive integer"
                    )
                elif page in page_numbers:
                    issues.append(f"{name}: duplicate page_fact_ids page {page}")
                else:
                    page_numbers.add(page)
                if not isinstance(fact_ids, list):
                    issues.append(f"{name}: page {page!r} fact_ids must be a list")
                    continue
                if len(fact_ids) > 3:
                    issues.append(
                        f"{name}: page {page!r} carries more than three facts"
                    )
                mapped_fact_ids.extend(str(fact_id) for fact_id in fact_ids)

            if len(mapped_fact_ids) != len(set(mapped_fact_ids)):
                issues.append(f"{name}: a fact may map to only one page")
            if set(mapped_fact_ids) != set(artifact.included_fact_ids):
                issues.append(
                    f"{name}: page_fact_ids must exactly match included_fact_ids"
                )

            eval_manifest_path = artifact.metadata.get("eval_manifest_path")
            if eval_manifest_path:
                issues.extend(
                    self._validate_eval_manifest(
                        name,
                        Path(eval_manifest_path),
                        page_fact_ids,
                        artifact.included_fact_ids,
                    )
                )
        return issues

    @staticmethod
    def _validate_eval_manifest(
        artifact_name: str,
        manifest_path: Path,
        page_fact_ids: list[dict[str, Any]],
        included_fact_ids: list[str],
    ) -> list[str]:
        if not manifest_path.is_file():
            return [f"{artifact_name}: eval_manifest_path not found"]
        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError as error:
            return [f"{artifact_name}: invalid eval manifest JSON ({error})"]
        if manifest.get("page_fact_ids") != page_fact_ids:
            return [
                f"{artifact_name}: eval manifest page_fact_ids must match "
                "artifact metadata"
            ]
        authoritative_ids = [
            str(fact.get("id"))
            for fact in manifest.get("authoritative_facts") or []
            if isinstance(fact, dict) and fact.get("id")
        ]
        if set(authoritative_ids) != set(included_fact_ids):
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


register_transformation(ProcessPresentationTransformation())
