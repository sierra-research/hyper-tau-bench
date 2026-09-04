"""Recorded working-session transcripts used as decision evidence.

The representation delivers timestamped meeting exports such as Zoom WebVTT
transcripts. Fact ownership, proposal/reversal labels, and decision mappings
remain in an optional author-side evaluation manifest.

Authoring sub-options
---------------------

``case_review``: a session whose agenda is reviewing specific support cases
from a sibling ``support_transcripts`` artifact in the same bundle. Speakers
reference cases by their in-world case number (``CS-94806``) or export
filename and discuss why the handling was good or bad. The cross-artifact
join is the point: the reader can line spoken verdicts up against the
underlying transcripts. First instance: the banking card-servicing evidence
room's case-review session. Authoring notes:

- Referenced case numbers/filenames must resolve against real case artifacts
  in the same bundle; a dangling reference is a broken join, not texture.
- A dated review session is a natural warrant for a conversational record to
  carry policy-relevant judgments, so verdicts may be fact-bearing — but
  reviewers adjudicate behavior ("she ran the payoff from checking before
  touching the fee — that order is right"), never recite a rule sentence
  another artifact owns.
- Mix the verdicts: some reviewed cases good, some bad, and some reviews
  about tone or handle time with no policy content at all, so "case
  discussed in the meeting" never predicts fact-bearing.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from tau2.hyper.transformations.base import (
    KitFile,
    SectionTransformation,
    TransformationArtifact,
    register_transformation,
)
from tau2.utils.utils import DATA_DIR

_TEXT_SUFFIXES = {".md", ".srt", ".txt", ".vtt"}
_DECISION_STATUSES = {"proposal", "rejected", "superseded", "final_current"}
_CUE_RE = re.compile(
    r"(?P<start>(?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})\s+-->\s+"
    r"(?P<end>(?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})"
)
_SPEAKER_RE = re.compile(
    r"(?m)^(?:<v\s+(?P<vtt>[^>]+)>|(?P<label>[A-Za-z][A-Za-z0-9 .'-]{0,60}):\s+\S)"
)
_POINT_TIMESTAMP_RE = re.compile(r"^(?:\d{2}:)?\d{2}:\d{2}[.,]\d{3}$")
_SPOKEN_TEXT_RE = re.compile(
    r"(?m)^(?:<v\s+[^>]+>|[A-Za-z][A-Za-z0-9 .'-]{0,60}:\s+)(?P<text>.*)$"
)
_WORD_RE = re.compile(r"\b[\w’'-]+\b")


class RecordedWorkingSessionTransformation(SectionTransformation):
    """Deliver timestamped meeting transcripts with author-side decisions."""

    representation = "recorded_working_session"
    aliases = ("meeting_transcript", "recorded_meeting", "zoom_transcript")
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
                "recorded_working_session transformation for section schema "
                f"{schema.get('id', '<unknown>')!r} must declare artifacts"
            )

        shared_metadata = {
            key: spec[key]
            for key in (
                "eval_manifest_path",
                "maximum_duration_minutes",
                "minimum_meetings",
                "minimum_duration_minutes",
                "minimum_speakers",
                "maximum_words_per_minute",
                "minimum_words_per_minute",
            )
            if key in spec
        }
        artifacts = []
        for entry in declared:
            metadata = shared_metadata | {
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
        transcript_bounds: dict[Path, tuple[float | None, float | None]] = {}
        manifest_groups: dict[Path, list[TransformationArtifact]] = {}
        for artifact in artifacts:
            path = artifact.source_path
            name = path.name
            suffix = path.suffix.lower()
            supported_suffix = suffix in _TEXT_SUFFIXES
            if not supported_suffix:
                issues.append(
                    f"{name}: working-session transcript must be one of "
                    f"{sorted(_TEXT_SUFFIXES)}"
                )
            if not path.is_file():
                issues.append(f"{name}: working-session transcript not found")
                continue

            kit_filename = str(artifact.metadata.get("kit_filename") or "")
            if not kit_filename:
                issues.append(f"{name}: kit_filename is required")
            elif Path(kit_filename).name != kit_filename:
                issues.append(f"{name}: kit_filename must be a bare filename")
            elif Path(kit_filename).suffix.lower() != suffix:
                issues.append(f"{name}: kit_filename must preserve the source suffix")
            elif kit_filename in seen_filenames:
                issues.append(f"{name}: duplicate kit_filename {kit_filename!r}")
            if kit_filename:
                seen_filenames.add(kit_filename)

            if not supported_suffix:
                continue

            text = path.read_text()
            if suffix == ".vtt" and not text.lstrip().startswith("WEBVTT"):
                issues.append(f"{name}: WebVTT transcript must start with WEBVTT")
            cues = [
                (
                    self._timestamp_seconds(match["start"]),
                    self._timestamp_seconds(match["end"]),
                )
                for match in _CUE_RE.finditer(text)
            ]
            if suffix in {".srt", ".vtt"} and not cues:
                issues.append(f"{name}: transcript contains no timestamp cues")

            transcript_start_seconds = min((start for start, _ in cues), default=None)
            transcript_end_seconds = max((end for _, end in cues), default=None)
            duration_seconds = (
                transcript_end_seconds - transcript_start_seconds
                if transcript_start_seconds is not None
                and transcript_end_seconds is not None
                else None
            )
            transcript_bounds[path] = (
                transcript_start_seconds,
                transcript_end_seconds,
            )
            if any(end < start for start, end in cues):
                issues.append(f"{name}: transcript cue ends before it starts")
            issues.extend(
                self._validate_session_shape(
                    name,
                    text,
                    duration_seconds,
                    artifact.metadata,
                )
            )
            manifest_path = artifact.metadata.get("eval_manifest_path")
            if manifest_path:
                manifest_groups.setdefault(Path(manifest_path), []).append(artifact)

        for manifest_path, manifest_artifacts in manifest_groups.items():
            issues.extend(
                self._validate_eval_manifest(
                    manifest_path,
                    manifest_artifacts,
                    transcript_bounds,
                )
            )
        return issues

    @classmethod
    def _validate_session_shape(
        cls,
        artifact_name: str,
        text: str,
        duration_seconds: float | None,
        metadata: dict[str, Any],
    ) -> list[str]:
        issues: list[str] = []
        minimum_speakers = metadata.get("minimum_speakers", 2)
        if not isinstance(minimum_speakers, int) or minimum_speakers < 2:
            issues.append(f"{artifact_name}: minimum_speakers must be an integer >= 2")
        else:
            speakers = {
                (match.group("vtt") or match.group("label")).strip()
                for match in _SPEAKER_RE.finditer(text)
            }
            if len(speakers) < minimum_speakers:
                issues.append(
                    f"{artifact_name}: transcript has {len(speakers)} speakers; "
                    f"expected at least {minimum_speakers}"
                )

        for key, comparator in (
            ("minimum_duration_minutes", "minimum"),
            ("maximum_duration_minutes", "maximum"),
        ):
            if key not in metadata:
                continue
            value = metadata[key]
            if not isinstance(value, (int, float)) or value <= 0:
                issues.append(f"{artifact_name}: {key} must be a positive number")
                continue
            if duration_seconds is None:
                issues.append(
                    f"{artifact_name}: {key} requires timestamped transcript cues"
                )
                continue
            duration_minutes = duration_seconds / 60
            if comparator == "minimum" and duration_minutes < value:
                issues.append(
                    f"{artifact_name}: transcript is {duration_minutes:.1f} minutes; "
                    f"minimum is {value:g}"
                )
            if comparator == "maximum" and duration_minutes > value:
                issues.append(
                    f"{artifact_name}: transcript is {duration_minutes:.1f} minutes; "
                    f"maximum is {value:g}"
                )

        density_bounds = (
            ("minimum_words_per_minute", "minimum"),
            ("maximum_words_per_minute", "maximum"),
        )
        for key, comparator in density_bounds:
            if key not in metadata:
                continue
            value = metadata[key]
            if not isinstance(value, (int, float)) or value <= 0:
                issues.append(f"{artifact_name}: {key} must be a positive number")
                continue
            if duration_seconds is None:
                issues.append(
                    f"{artifact_name}: {key} requires timestamped transcript cues"
                )
                continue
            spoken_text = " ".join(
                match.group("text") for match in _SPOKEN_TEXT_RE.finditer(text)
            )
            words_per_minute = len(_WORD_RE.findall(spoken_text)) / (
                duration_seconds / 60
            )
            if comparator == "minimum" and words_per_minute < value:
                issues.append(
                    f"{artifact_name}: transcript has {words_per_minute:.1f} words "
                    f"per minute; minimum is {value:g}"
                )
            if comparator == "maximum" and words_per_minute > value:
                issues.append(
                    f"{artifact_name}: transcript has {words_per_minute:.1f} words "
                    f"per minute; maximum is {value:g}"
                )
        return issues

    @classmethod
    def _validate_eval_manifest(
        cls,
        manifest_path: Path,
        artifacts: list[TransformationArtifact],
        transcript_bounds: dict[Path, tuple[float | None, float | None]],
    ) -> list[str]:
        artifact_name = artifacts[0].source_path.name
        if not manifest_path.is_file():
            return [f"{artifact_name}: eval_manifest_path not found"]
        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError as error:
            return [f"{artifact_name}: invalid eval manifest JSON ({error})"]

        if manifest.get("meetings"):
            return cls._validate_series_manifest(
                manifest_path.name,
                manifest,
                artifacts,
                transcript_bounds,
            )
        if len(artifacts) != 1:
            return [
                f"{manifest_path.name}: multiple transcripts require a meetings "
                "registry in the eval manifest"
            ]

        artifact = artifacts[0]
        transcript_start_seconds, transcript_end_seconds = transcript_bounds.get(
            artifact.source_path, (None, None)
        )
        decisions = manifest.get("decisions") or []
        issues: list[str] = []
        final_fact_ids: list[str] = []
        previous_timestamp = -1.0
        for index, decision in enumerate(decisions, 1):
            if not isinstance(decision, dict):
                issues.append(f"{artifact_name}: decision {index} must be an object")
                continue
            status = decision.get("status")
            if status not in _DECISION_STATUSES:
                issues.append(
                    f"{artifact_name}: decision {index} has invalid status {status!r}"
                )
            timestamp = decision.get("timestamp")
            if not isinstance(timestamp, str) or not _POINT_TIMESTAMP_RE.match(
                timestamp
            ):
                issues.append(
                    f"{artifact_name}: decision {index} needs an exact transcript timestamp"
                )
                continue
            timestamp_seconds = cls._timestamp_seconds(timestamp)
            if timestamp_seconds < previous_timestamp:
                issues.append(f"{artifact_name}: decisions must be chronological")
            previous_timestamp = timestamp_seconds
            if (
                transcript_start_seconds is not None
                and timestamp_seconds < transcript_start_seconds
            ):
                issues.append(
                    f"{artifact_name}: decision {index} falls before the transcript starts"
                )
            if (
                transcript_end_seconds is not None
                and timestamp_seconds > transcript_end_seconds
            ):
                issues.append(
                    f"{artifact_name}: decision {index} falls after the transcript ends"
                )
            if status == "final_current" and decision.get("fact_id"):
                final_fact_ids.append(str(decision["fact_id"]))

        if sorted(final_fact_ids) != sorted(artifact.included_fact_ids):
            issues.append(
                f"{artifact_name}: final_current decisions must exactly match "
                "included_fact_ids"
            )
        return issues

    @classmethod
    def _validate_series_manifest(
        cls,
        manifest_name: str,
        manifest: dict[str, Any],
        artifacts: list[TransformationArtifact],
        transcript_bounds: dict[Path, tuple[float | None, float | None]],
    ) -> list[str]:
        """Validate chronology and fact ownership across a meeting series."""
        issues: list[str] = []
        minimum_meetings = artifacts[0].metadata.get("minimum_meetings", 2)
        if not isinstance(minimum_meetings, int) or minimum_meetings < 2:
            issues.append(f"{manifest_name}: minimum_meetings must be an integer >= 2")
        elif len(artifacts) < minimum_meetings:
            issues.append(
                f"{manifest_name}: series has {len(artifacts)} meetings; "
                f"expected at least {minimum_meetings}"
            )

        artifacts_by_meeting: dict[str, TransformationArtifact] = {}
        for artifact in artifacts:
            meeting_id = artifact.metadata.get("meeting_id")
            if not isinstance(meeting_id, str) or not meeting_id:
                issues.append(
                    f"{artifact.source_path.name}: meeting_id is required for a series"
                )
                continue
            if meeting_id in artifacts_by_meeting:
                issues.append(f"{manifest_name}: duplicate meeting_id {meeting_id!r}")
            artifacts_by_meeting[meeting_id] = artifact

        meetings = manifest.get("meetings") or []
        manifest_meetings: dict[str, dict[str, Any]] = {}
        meeting_dates: dict[str, date] = {}
        for index, meeting in enumerate(meetings, 1):
            if not isinstance(meeting, dict):
                issues.append(f"{manifest_name}: meeting {index} must be an object")
                continue
            meeting_id = meeting.get("meeting_id")
            if not isinstance(meeting_id, str) or not meeting_id:
                issues.append(f"{manifest_name}: meeting {index} needs meeting_id")
                continue
            if meeting_id in manifest_meetings:
                issues.append(f"{manifest_name}: duplicate meeting_id {meeting_id!r}")
            manifest_meetings[meeting_id] = meeting
            meeting_date = meeting.get("date")
            try:
                meeting_dates[meeting_id] = date.fromisoformat(str(meeting_date))
            except ValueError:
                issues.append(
                    f"{manifest_name}: meeting {meeting_id!r} needs an ISO date"
                )

        if set(manifest_meetings) != set(artifacts_by_meeting):
            issues.append(
                f"{manifest_name}: manifest meetings must exactly match transcript "
                "meeting_ids"
            )

        for meeting_id, artifact in artifacts_by_meeting.items():
            meeting = manifest_meetings.get(meeting_id)
            if meeting is None:
                continue
            filename = meeting.get("filename")
            kit_filename = artifact.metadata.get("kit_filename")
            if filename != kit_filename:
                issues.append(
                    f"{manifest_name}: meeting {meeting_id!r} filename does not "
                    "match kit_filename"
                )
            if meeting.get("date") != artifact.metadata.get("meeting_date"):
                issues.append(
                    f"{manifest_name}: meeting {meeting_id!r} date does not match "
                    "artifact metadata"
                )
            authoritative = meeting.get("authoritative_fact_ids") or []
            if set(authoritative) != set(artifact.included_fact_ids):
                issues.append(
                    f"{manifest_name}: meeting {meeting_id!r} authoritative facts "
                    "must match included_fact_ids"
                )

        decisions = manifest.get("decisions") or []
        final_by_meeting: dict[str, list[str]] = {
            meeting_id: [] for meeting_id in artifacts_by_meeting
        }
        histories: dict[str, list[dict[str, Any]]] = {}
        previous_order: tuple[date, float] | None = None
        for index, decision in enumerate(decisions, 1):
            if not isinstance(decision, dict):
                issues.append(f"{manifest_name}: decision {index} must be an object")
                continue
            fact_id = decision.get("fact_id")
            if not isinstance(fact_id, str) or not fact_id:
                issues.append(f"{manifest_name}: decision {index} needs fact_id")
                continue
            histories.setdefault(fact_id, []).append(decision)
            status = decision.get("status")
            if status not in _DECISION_STATUSES:
                issues.append(
                    f"{manifest_name}: decision {index} has invalid status {status!r}"
                )
            meeting_id = decision.get("meeting_id")
            artifact = artifacts_by_meeting.get(str(meeting_id))
            if artifact is None:
                issues.append(
                    f"{manifest_name}: decision {index} references unknown meeting "
                    f"{meeting_id!r}"
                )
                continue
            timestamp = decision.get("timestamp")
            if not isinstance(timestamp, str) or not _POINT_TIMESTAMP_RE.match(
                timestamp
            ):
                issues.append(
                    f"{manifest_name}: decision {index} needs an exact transcript "
                    "timestamp"
                )
                continue
            timestamp_seconds = cls._timestamp_seconds(timestamp)
            meeting_date = meeting_dates.get(str(meeting_id))
            if meeting_date is not None:
                order = (meeting_date, timestamp_seconds)
                if previous_order is not None and order < previous_order:
                    issues.append(
                        f"{manifest_name}: decisions must be chronological across "
                        "meetings"
                    )
                previous_order = order
            transcript_start, transcript_end = transcript_bounds.get(
                artifact.source_path, (None, None)
            )
            if transcript_start is not None and timestamp_seconds < transcript_start:
                issues.append(
                    f"{manifest_name}: decision {index} falls before its transcript"
                )
            if transcript_end is not None and timestamp_seconds > transcript_end:
                issues.append(
                    f"{manifest_name}: decision {index} falls after its transcript"
                )
            if status == "final_current":
                final_by_meeting[str(meeting_id)].append(fact_id)
                issues.extend(
                    cls._validate_evidence_spans(
                        manifest_name,
                        index,
                        decision.get("evidence_spans"),
                        artifacts_by_meeting,
                        transcript_bounds,
                    )
                )

        for fact_id, events in histories.items():
            finals = [
                event for event in events if event.get("status") == "final_current"
            ]
            if len(finals) != 1:
                issues.append(
                    f"{manifest_name}: fact {fact_id!r} must have exactly one "
                    "final_current decision"
                )
            elif events[-1] is not finals[0]:
                issues.append(
                    f"{manifest_name}: fact {fact_id!r} has events after its "
                    "final_current decision"
                )

        for meeting_id, artifact in artifacts_by_meeting.items():
            if set(final_by_meeting.get(meeting_id, [])) != set(
                artifact.included_fact_ids
            ):
                issues.append(
                    f"{manifest_name}: final_current decisions for meeting "
                    f"{meeting_id!r} must match included_fact_ids"
                )

        final_fact_ids = {
            fact_id for fact_ids in final_by_meeting.values() for fact_id in fact_ids
        }
        included_fact_ids = {
            fact_id for artifact in artifacts for fact_id in artifact.included_fact_ids
        }
        if final_fact_ids != included_fact_ids:
            issues.append(
                f"{manifest_name}: series final_current decisions must exactly "
                "match included_fact_ids"
            )
        if set(manifest.get("authoritative_fact_ids") or []) != included_fact_ids:
            issues.append(
                f"{manifest_name}: authoritative_fact_ids must match series coverage"
            )
        return issues

    @classmethod
    def _validate_evidence_spans(
        cls,
        manifest_name: str,
        decision_index: int,
        spans: Any,
        artifacts_by_meeting: dict[str, TransformationArtifact],
        transcript_bounds: dict[Path, tuple[float | None, float | None]],
    ) -> list[str]:
        """Ensure final decisions point to bounded transcript evidence."""
        if not isinstance(spans, list) or not spans:
            return [
                f"{manifest_name}: final decision {decision_index} needs evidence_spans"
            ]
        issues: list[str] = []
        for span_index, span in enumerate(spans, 1):
            if not isinstance(span, dict):
                issues.append(
                    f"{manifest_name}: decision {decision_index} evidence span "
                    f"{span_index} must be an object"
                )
                continue
            meeting_id = span.get("meeting_id")
            artifact = artifacts_by_meeting.get(str(meeting_id))
            if artifact is None:
                issues.append(
                    f"{manifest_name}: decision {decision_index} evidence span "
                    f"{span_index} references unknown meeting {meeting_id!r}"
                )
                continue
            start = span.get("start")
            end = span.get("end")
            if (
                not isinstance(start, str)
                or not _POINT_TIMESTAMP_RE.match(start)
                or not isinstance(end, str)
                or not _POINT_TIMESTAMP_RE.match(end)
            ):
                issues.append(
                    f"{manifest_name}: decision {decision_index} evidence span "
                    f"{span_index} needs exact start and end timestamps"
                )
                continue
            start_seconds = cls._timestamp_seconds(start)
            end_seconds = cls._timestamp_seconds(end)
            transcript_start, transcript_end = transcript_bounds.get(
                artifact.source_path, (None, None)
            )
            if end_seconds <= start_seconds:
                issues.append(
                    f"{manifest_name}: decision {decision_index} evidence span "
                    f"{span_index} must end after it starts"
                )
            if transcript_start is not None and start_seconds < transcript_start:
                issues.append(
                    f"{manifest_name}: decision {decision_index} evidence span "
                    f"{span_index} starts before its transcript"
                )
            if transcript_end is not None and end_seconds > transcript_end:
                issues.append(
                    f"{manifest_name}: decision {decision_index} evidence span "
                    f"{span_index} ends after its transcript"
                )
        return issues

    @staticmethod
    def _timestamp_seconds(value: str) -> float:
        parts = value.replace(",", ".").split(":")
        if len(parts) == 2:
            hours = 0
            minutes, seconds = parts
        else:
            hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)

    @staticmethod
    def _resolve(path: str | Path) -> Path:
        resolved = Path(path)
        if resolved.is_absolute():
            return resolved
        return DATA_DIR / resolved


register_transformation(RecordedWorkingSessionTransformation())
