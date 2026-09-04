"""Website-screenshot transformation for visually encoded domain facts.

The Developer receives only anonymized image files under ``uploaded_materials/``.
Author-side HTML or an explicit text description supplies a deterministic
plain-text representation for fact-coverage judging; it is never copied into
the construction kit.
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


class WebsiteScreenshotTransformation(SectionTransformation):
    """Render a small set of facts as an anonymized website screenshot."""

    representation = "website_screenshot"
    aliases = ("website_screenshots",)
    placement = "pooled"
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
                f"website_screenshot transformation for section schema "
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
        suffix = artifact.source_path.suffix.lower()
        return KitFile(
            relative_path=f"{self.kit_dirname}/screen_{ordinal:03d}{suffix}",
            content=artifact.source_path.read_bytes(),
        )

    def to_text(self, artifact: TransformationArtifact) -> str:
        explicit_text = artifact.metadata.get("text")
        if explicit_text:
            return str(explicit_text).rstrip() + "\n"

        text_source_path = artifact.metadata.get("text_source_path")
        if not text_source_path:
            return ""
        return visible_text_from_html(text_source_path)

    def kit_text(self, artifact: TransformationArtifact) -> str | None:
        """Visible-text parse of the authored HTML is shippable as-is.

        The parser emits only rendered text — no markup, comments, class
        names, or generation scaffolding — so the text rendition carries
        exactly what a viewer of the screenshot could read.
        """
        declared = super().kit_text(artifact)
        if declared is not None:
            return declared
        text = self.to_text(artifact)
        return text if text.strip() else None

    def validate(
        self, schema: dict[str, Any], artifacts: list[TransformationArtifact]
    ) -> list[str]:
        issues = super().validate(schema, artifacts)
        for artifact in artifacts:
            name = artifact.source_path.name
            if artifact.source_path.suffix.lower() not in _IMAGE_SUFFIXES:
                issues.append(
                    f"{name}: screenshot must be one of {sorted(_IMAGE_SUFFIXES)}"
                )
            if not artifact.source_path.is_file():
                issues.append(f"{name}: screenshot file not found")
            text_source_path = artifact.metadata.get("text_source_path")
            if text_source_path and not Path(text_source_path).is_file():
                issues.append(f"{name}: text_source_path not found")
            if not text_source_path and not artifact.metadata.get("text"):
                issues.append(
                    f"{name}: declare text_source_path or text for "
                    "fact-coverage judging"
                )
        return issues

    @staticmethod
    def _resolve(path: str | Path) -> Path:
        resolved = Path(path)
        if resolved.is_absolute():
            return resolved
        return DATA_DIR / resolved


register_transformation(WebsiteScreenshotTransformation())
