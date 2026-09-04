"""Business-process flowchart transformation.

The Developer receives a recognizable image under ``uploaded_materials/``. Editable
HTML, SVG, or diagram-tool sources stay author-side; a separate text source
makes the visible policy content deterministic for fact-coverage judging.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tau2.hyper.transformations.base import (
    KitFile,
    SectionTransformation,
    TransformationArtifact,
    register_transformation,
)
from tau2.hyper.transformations.html_text import visible_text_from_html
from tau2.utils.utils import DATA_DIR

_IMAGE_SUFFIXES = {".jpeg", ".jpg", ".png", ".webp"}


class ProcessFlowchartTransformation(SectionTransformation):
    """Represent workflow facts in a customer-authored process-map image."""

    representation = "process_flowchart"
    aliases = ("business_process_flowchart", "process_map")
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
                f"process_flowchart transformation for section schema "
                f"{schema.get('id', '<unknown>')!r} must declare artifacts "
                "with path and included_fact_ids entries"
            )

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
        kit_filename = artifact.metadata.get("kit_filename", artifact.source_path.name)
        return KitFile(
            relative_path=f"{self.kit_dirname}/{kit_filename}",
            content=artifact.source_path.read_bytes(),
        )

    def to_text(self, artifact: TransformationArtifact) -> str:
        explicit_text = artifact.metadata.get("text")
        if explicit_text:
            return str(explicit_text).rstrip() + "\n"
        text_source_path = artifact.metadata.get("text_source_path")
        if not text_source_path:
            return ""
        source_path = Path(text_source_path)
        if source_path.suffix.lower() in {".htm", ".html"}:
            return visible_text_from_html(source_path)
        return source_path.read_text().rstrip() + "\n"

    def kit_text(self, artifact: TransformationArtifact) -> str | None:
        """Return a safe text rendition of the visible flowchart content.

        Flowchart text sources are authored as in-world step outlines
        (``.txt``/``.md``) or HTML used to render the delivered image. HTML is
        reduced to visible text so markup and generation scaffolding do not
        enter the kit. Other formats need an explicit ``kit_text_path``.
        """
        declared = super().kit_text(artifact)
        if declared is not None:
            return declared
        explicit_text = artifact.metadata.get("text")
        if explicit_text:
            return str(explicit_text).rstrip() + "\n"
        text_source_path = artifact.metadata.get("text_source_path")
        if text_source_path:
            suffix = Path(text_source_path).suffix.lower()
            if suffix in {".md", ".txt"}:
                return Path(text_source_path).read_text().rstrip() + "\n"
            if suffix in {".htm", ".html"}:
                return visible_text_from_html(text_source_path)
        return None

    def validate(
        self, schema: dict[str, Any], artifacts: list[TransformationArtifact]
    ) -> list[str]:
        issues = super().validate(schema, artifacts)
        seen_filenames: set[str] = set()
        for artifact in artifacts:
            name = artifact.source_path.name
            if artifact.source_path.suffix.lower() not in _IMAGE_SUFFIXES:
                issues.append(
                    f"{name}: process flowchart must be one of "
                    f"{sorted(_IMAGE_SUFFIXES)}"
                )
            if not artifact.source_path.is_file():
                issues.append(f"{name}: process flowchart file not found")
            text_source_path = artifact.metadata.get("text_source_path")
            if text_source_path and not Path(text_source_path).is_file():
                issues.append(f"{name}: text_source_path not found")
            if not text_source_path and not artifact.metadata.get("text"):
                issues.append(
                    f"{name}: declare text_source_path or text for "
                    "fact-coverage judging"
                )
            kit_filename = str(
                artifact.metadata.get("kit_filename", artifact.source_path.name)
            )
            if Path(kit_filename).name != kit_filename:
                issues.append(f"{name}: kit_filename must be a plain filename")
            if kit_filename in seen_filenames:
                issues.append(f"{name}: duplicate kit_filename {kit_filename!r}")
            seen_filenames.add(kit_filename)
        return issues

    @staticmethod
    def _resolve(path: str | Path) -> Path:
        resolved = Path(path)
        if resolved.is_absolute():
            return resolved
        return DATA_DIR / resolved


register_transformation(ProcessFlowchartTransformation())
