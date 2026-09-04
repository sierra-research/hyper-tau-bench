"""Interactive screen recordings used as temporal procedure evidence."""

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

_VIDEO_SUFFIXES = {".mp4", ".webm"}
_EVENT_KINDS = {"context", "authoritative", "distractor", "outcome"}


class InteractiveScreenRecordingTransformation(SectionTransformation):
    """Deliver short UI recordings with author-side timestamp annotations."""

    representation = "interactive_screen_recording"
    aliases = ("screen_recording", "device_screen_recording")
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
                "interactive_screen_recording transformation for section schema "
                f"{schema.get('id', '<unknown>')!r} must declare artifacts"
            )

        artifacts = []
        for entry in declared:
            metadata = {
                key: value
                for key, value in entry.items()
                if key not in {"included_fact_ids", "path"}
            }
            for path_key in (
                "text_source_path",
                "kit_text_path",
                "eval_manifest_path",
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
        return KitFile(
            relative_path=(f"{self.kit_dirname}/{artifact.metadata['kit_filename']}"),
            content=artifact.source_path.read_bytes(),
            artifact_kind=self.representation,
        )

    def to_text(self, artifact: TransformationArtifact) -> str:
        """Return the author-side timeline used by fact-coverage judges."""
        return Path(artifact.metadata["text_source_path"]).read_text()

    def validate(
        self, schema: dict[str, Any], artifacts: list[TransformationArtifact]
    ) -> list[str]:
        issues = super().validate(schema, artifacts)
        seen_filenames: set[str] = set()
        manifest_groups: dict[Path, list[TransformationArtifact]] = {}

        for artifact in artifacts:
            path = artifact.source_path
            suffix = path.suffix.lower()
            if suffix not in _VIDEO_SUFFIXES:
                issues.append(
                    f"{path.name}: screen recording must be one of "
                    f"{sorted(_VIDEO_SUFFIXES)}"
                )
            if not path.is_file():
                issues.append(f"{path.name}: screen recording not found")
            elif path.stat().st_size == 0:
                issues.append(f"{path.name}: screen recording is empty")
            elif suffix == ".mp4" and b"ftyp" not in path.read_bytes()[:32]:
                issues.append(f"{path.name}: file does not have an MP4 signature")
            elif suffix == ".webm" and not path.read_bytes().startswith(
                b"\x1a\x45\xdf\xa3"
            ):
                issues.append(f"{path.name}: file does not have a WebM signature")

            kit_filename = str(artifact.metadata.get("kit_filename") or "")
            if not kit_filename:
                issues.append(f"{path.name}: kit_filename is required")
            elif Path(kit_filename).name != kit_filename:
                issues.append(f"{path.name}: kit_filename must be a bare filename")
            elif Path(kit_filename).suffix.lower() != suffix:
                issues.append(
                    f"{path.name}: kit_filename must preserve the video suffix"
                )
            elif kit_filename in seen_filenames:
                issues.append(f"{path.name}: duplicate kit_filename {kit_filename!r}")
            if kit_filename:
                seen_filenames.add(kit_filename)

            text_source = artifact.metadata.get("text_source_path")
            if not text_source:
                issues.append(f"{path.name}: text_source_path is required")
            elif not Path(text_source).is_file():
                issues.append(f"{path.name}: text_source_path not found")

            manifest_path = artifact.metadata.get("eval_manifest_path")
            if not manifest_path:
                issues.append(f"{path.name}: eval_manifest_path is required")
            else:
                manifest_groups.setdefault(Path(manifest_path), []).append(artifact)

            duration = artifact.metadata.get("duration_seconds")
            if not isinstance(duration, (int, float)) or duration <= 0:
                issues.append(f"{path.name}: duration_seconds must be positive")

        for manifest_path, grouped_artifacts in manifest_groups.items():
            issues.extend(self._validate_manifest(manifest_path, grouped_artifacts))
        return issues

    @staticmethod
    def _validate_manifest(
        manifest_path: Path, artifacts: list[TransformationArtifact]
    ) -> list[str]:
        if not manifest_path.is_file():
            return [f"{manifest_path.name}: evaluation manifest not found"]
        try:
            payload = json.loads(manifest_path.read_text())
        except json.JSONDecodeError as error:
            return [f"{manifest_path.name}: invalid JSON ({error})"]

        entries = payload.get("artifacts")
        if not isinstance(entries, list):
            return [f"{manifest_path.name}: artifacts must be a list"]
        by_filename = {
            str(entry.get("filename")): entry
            for entry in entries
            if isinstance(entry, dict)
        }
        issues: list[str] = []
        for artifact in artifacts:
            entry = by_filename.get(artifact.source_path.name)
            if entry is None:
                issues.append(
                    f"{manifest_path.name}: missing {artifact.source_path.name}"
                )
                continue
            duration = artifact.metadata.get("duration_seconds")
            events = entry.get("events")
            if not isinstance(events, list) or not events:
                issues.append(f"{artifact.source_path.name}: events must be non-empty")
                continue

            authoritative_facts: set[str] = set()
            distractor_count = 0
            previous_start = -1.0
            for index, event in enumerate(events):
                if not isinstance(event, dict):
                    issues.append(
                        f"{artifact.source_path.name}: event {index} must be an object"
                    )
                    continue
                kind = event.get("kind")
                start = event.get("start_seconds")
                end = event.get("end_seconds")
                if kind not in _EVENT_KINDS:
                    issues.append(
                        f"{artifact.source_path.name}: event {index} has invalid kind"
                    )
                if not isinstance(start, (int, float)) or not isinstance(
                    end, (int, float)
                ):
                    issues.append(
                        f"{artifact.source_path.name}: event {index} needs numeric bounds"
                    )
                    continue
                if start < previous_start or end <= start or end > duration:
                    issues.append(
                        f"{artifact.source_path.name}: event {index} has invalid bounds"
                    )
                previous_start = start
                if kind == "authoritative":
                    authoritative_facts.update(event.get("fact_ids") or [])
                elif kind == "distractor":
                    distractor_count += 1
                    if event.get("disposition") not in {
                        "failed",
                        "rejected",
                        "unrelated",
                    }:
                        issues.append(
                            f"{artifact.source_path.name}: distractor event {index} "
                            "must be failed, rejected, or unrelated"
                        )

            if authoritative_facts != set(artifact.included_fact_ids):
                issues.append(
                    f"{artifact.source_path.name}: authoritative timeline facts do "
                    "not match included_fact_ids"
                )
            if entry.get("fixture") == "controlled_distractor" and not distractor_count:
                issues.append(
                    f"{artifact.source_path.name}: controlled-distractor fixture "
                    "contains no distractor events"
                )
        return issues

    @staticmethod
    def _resolve(path: str | Path) -> Path:
        resolved = Path(path)
        return resolved if resolved.is_absolute() else DATA_DIR / resolved


register_transformation(InteractiveScreenRecordingTransformation())
