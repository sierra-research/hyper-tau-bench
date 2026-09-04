"""
Support-transcript transformation: sections rendered as approved case records.

This is the original hyper-tau information-distribution representation.
Each section's facts are re-encoded as QA-approved customer-support
transcripts (``training_records/case_*.md`` on the authoring side, next to the section's fact
schema). At kit-build time the records from every section are pooled into
one flat ``uploaded_materials/`` directory and renumbered so the Developer
sees an ordinary support-training bundle with no section boundaries.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from tau2.hyper.transformations.base import (
    KitFile,
    SectionTransformation,
    TransformationArtifact,
    register_transformation,
    schema_fact_ids,
)
from tau2.hyper.transformations.modality import ModalityProfile
from tau2.hyper.transformations.transcript_artifacts import (
    BANKING_ROOM_TURN_RE,
    BANKING_TURN_RE,
    CHANNEL_RE,
    CONSOLE_RE,
    TELECOM_CONSOLE_RE,
    TELECOM_QA_RE,
    TELECOM_SCENE_RE,
    TELECOM_SEGMENT_RE,
    TELECOM_TURN_RE,
    TURN_RE,
    parse_telecom_transcript,
    phone_transcript_dialect,
)
from tau2.utils.utils import DATA_DIR

_RECORDING_NOTE = (
    "Recording: the spoken dialogue for this call is in the companion "
    "call-recording audio file that shares this case file's number."
)
_CONSOLE_NOTE = (
    "Support-console events logged during the call are preserved below; "
    "their turn numbers refer to positions in the recording."
)
# Stamped dialects (banking / telecom) keep their non-spoken log lines with
# the authored timestamps; those stamps are the transcript's own call
# timeline, so the note must not promise recording offsets.
_STAMPED_CONSOLE_NOTE = (
    "Support-console entries and other non-spoken log lines from the call "
    "are preserved below with their original timestamps."
)
# The evidence-room micro form is unstamped and unnumbered.
_ROOM_CONSOLE_NOTE = (
    "Support-console events logged during the call are preserved below."
)


def _strip_spoken_dialogue(text: str, dialect: str) -> str:
    """Replace a phone-call record's spoken turns with a recording pointer.

    Mirrors the transcript parser's line semantics for the record's
    dialect: header material and everything that never made it into the
    audio (console events and other non-spoken log lines, trailing prose
    sections, chat segments) is kept, while spoken turns and their
    hard-wrap continuations are dropped. Purely mechanical — no authored
    content is added beyond the fixed pointer notes.
    """
    if dialect == "sections":
        return _strip_marker_dialogue(text, _classify_sections_line, _CONSOLE_NOTE)
    if dialect == "banking_room":
        return _strip_marker_dialogue(text, _classify_room_line, _ROOM_CONSOLE_NOTE)
    if dialect == "banking":
        return _strip_banking_dialogue(text)
    if dialect == "telecom":
        return _strip_telecom_dialogue(text)
    raise ValueError(f"unknown phone-transcript dialect: {dialect!r}")


def _classify_sections_line(line: str) -> str | None:
    if TURN_RE.match(line):
        return "spoken"
    if CONSOLE_RE.match(line):
        return "kept"
    return None


def _classify_room_line(line: str) -> str | None:
    match = BANKING_ROOM_TURN_RE.match(line)
    if match is None:
        return None
    return "kept" if match.group(1) == "Console" else "spoken"


def _strip_marker_dialogue(
    text: str, classify: Callable[[str], str | None], console_note: str
) -> str:
    """Strip flat marker dialects: sections/hard and the room micro form.

    Everything before the first marker is header material and copied
    verbatim; afterwards, non-spoken markers and their hard-wrap
    continuations are kept while spoken turns and theirs are dropped.
    """
    header: list[str] = []
    kept_blocks: list[list[str]] = []
    mode: str | None = None  # None until the first marker
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        kind = classify(line)
        if kind == "spoken":
            mode = "spoken"
        elif kind == "kept":
            mode = "kept"
            kept_blocks.append([line])
        elif mode is None:
            header.append(line)
        elif mode == "kept" and line.strip():
            kept_blocks[-1].append(line)

    while header and not header[-1].strip():
        header.pop()
    note = _RECORDING_NOTE + (f" {console_note}" if kept_blocks else "")
    parts = ["\n".join(header), note]
    parts.extend("\n".join(block) for block in kept_blocks)
    return "\n\n".join(part for part in parts if part).rstrip() + "\n"


def _strip_banking_dialogue(text: str) -> str:
    """Strip the banking stamped support-case form.

    The record header and everything from the first heading after
    ``## Transcript`` on (Follow-up / Case notes / QA review — dated prose
    logs, never audio) are copied verbatim; within the transcript,
    ``**Support console:**`` entries keep their stamps while spoken turns
    are dropped.
    """
    header: list[str] = []
    kept_blocks: list[list[str]] = []
    trailing: list[str] = []
    phase = "header"
    mode: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if phase == "trailing":
            trailing.append(line)
            continue
        if line.startswith("## "):
            if phase == "transcript":
                phase = "trailing"
                trailing.append(line)
            else:
                phase = "transcript"  # "## Transcript"
            continue
        if phase == "header":
            header.append(line)
        elif match := BANKING_TURN_RE.match(line):
            if match.group(3) == "Support console":
                mode = "kept"
                kept_blocks.append([line])
            else:
                mode = "spoken"
        elif mode == "kept" and line.strip():
            kept_blocks[-1].append(line)

    while header and not header[-1].strip():
        header.pop()
    note = _RECORDING_NOTE + (f" {_STAMPED_CONSOLE_NOTE}" if kept_blocks else "")
    parts = ["\n".join(header), "## Transcript", note]
    parts.extend("\n".join(block) for block in kept_blocks)
    while trailing and not trailing[-1].strip():
        trailing.pop()
    while trailing and not trailing[0].strip():
        trailing.pop(0)
    if trailing:
        parts.append("\n".join(trailing))
    return "\n\n".join(part for part in parts if part).rstrip() + "\n"


def _followup_recording_note(segment_label: str) -> str:
    return (
        "Recording: the spoken dialogue for this follow-up call is in the "
        "companion call-recording audio file that shares this case file's "
        f"number with a '_{segment_label}' suffix."
    )


def _strip_telecom_dialogue(text: str) -> str:
    """Strip the telecom stamped archive form, segment by segment.

    Mirrors ``parse_telecom_transcript``'s chunking: each ``## Transcript``
    / ``## Follow-up contact`` segment has its own channel (the first
    inherits the record header's). Phone segments drop spoken turns and
    keep their header block plus every stamped non-spoken line (console
    notes, call events, QA annotations); chat segments never render to
    audio and are copied verbatim. Each phone segment gets its own pointer
    note because each renders to its own recording
    (``case_007.m4a`` / ``case_007_followup.m4a``).
    """
    chunks: list[tuple[str | None, list[str]]] = [(None, [])]
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if TELECOM_SEGMENT_RE.match(line):
            chunks.append((line, []))
        else:
            chunks[-1][1].append(line)
    header_lines, segment_chunks = chunks[0][1], chunks[1:]

    record_channel = ""
    for line in header_lines:
        if match := CHANNEL_RE.match(line):
            record_channel = match.group(1)
            break
    while header_lines and not header_lines[-1].strip():
        header_lines.pop()
    parts = ["\n".join(header_lines)]

    for index, (heading, lines) in enumerate(segment_chunks):
        channel = record_channel if index == 0 else ""
        for line in lines:
            if match := CHANNEL_RE.match(line):
                channel = match.group(1)
                break
        if channel != "Phone":
            while lines and not lines[-1].strip():
                lines.pop()
            while lines and not lines[0].strip():
                lines.pop(0)
            parts.append("\n".join([heading, "", *lines]) if lines else heading)
            continue

        segment_header: list[str] = []
        kept_blocks: list[list[str]] = []
        mode: str | None = None
        for line in lines:
            if TELECOM_TURN_RE.match(line):
                mode = "spoken"
            elif (
                TELECOM_CONSOLE_RE.match(line)
                or TELECOM_SCENE_RE.match(line)
                or TELECOM_QA_RE.match(line)
            ):
                mode = "kept"
                kept_blocks.append([line])
            elif mode is None:
                if line.strip():
                    segment_header.append(line)
            elif mode == "kept" and line.strip():
                kept_blocks[-1].append(line)

        label = f"followup{index if index > 1 else ''}" if index > 0 else ""
        note = _RECORDING_NOTE if not label else _followup_recording_note(label)
        if kept_blocks:
            note += f" {_STAMPED_CONSOLE_NOTE}"
        segment_parts = [heading]
        if segment_header:
            segment_parts.append("\n".join(segment_header))
        segment_parts.append(note)
        segment_parts.extend("\n".join(block) for block in kept_blocks)
        parts.append("\n\n".join(segment_parts))

    return "\n\n".join(part for part in parts if part).rstrip() + "\n"


class SupportTranscriptsTransformation(SectionTransformation):
    representation = "support_transcripts"
    aliases = ("example_transcripts",)
    placement = "pooled"
    carries_agent_utterances = True

    def discover_artifacts(
        self,
        schema: dict[str, Any],
        schema_path: Path,
        spec: dict[str, Any],
    ) -> list[TransformationArtifact]:
        declared = spec.get("artifacts")
        if declared:
            return [
                TransformationArtifact(
                    source_path=self._resolve(entry["path"], schema_path),
                    included_fact_ids=list(entry.get("included_fact_ids", [])),
                    metadata={k: v for k, v in entry.items() if k != "path"},
                )
                for entry in declared
            ]

        configured_records_dir = schema.get("case_records_dir")
        if configured_records_dir:
            records_dir = self._resolve(configured_records_dir, schema_path)
        else:
            rendered_section_path = self._resolve(
                schema["rendered_section_path"], schema_path
            )
            records_dir = rendered_section_path.parent / "training_records"
        if not records_dir.exists():
            raise FileNotFoundError(
                f"SOP training records directory not found: {records_dir}"
            )

        record_paths = sorted(records_dir.glob("case_*.md"))
        plans = schema.get("transcripts") or []
        artifacts = []
        for index, source_path in enumerate(record_paths):
            plan = (
                plans[index]
                if index < len(plans) and len(plans) == len(record_paths)
                else {}
            )
            artifacts.append(
                TransformationArtifact(
                    source_path=source_path,
                    included_fact_ids=list(plan.get("included_fact_ids", [])),
                    metadata={"plan_id": plan.get("id")} if plan else {},
                )
            )
        return artifacts

    def neutralize(self, artifact: TransformationArtifact, ordinal: int) -> KitFile:
        text = artifact.source_path.read_text().lstrip()
        lines = text.splitlines()
        if lines and lines[0].startswith("# Case"):
            lines[0] = f"# Case {ordinal:03d}"
            text = "\n".join(lines).rstrip() + "\n"
        else:
            text = f"# Case {ordinal:03d}\n\n{text.rstrip()}\n"
        return KitFile(
            relative_path=f"{self.kit_dirname}/case_{ordinal:03d}.md",
            content=text.encode(),
        )

    def to_text(self, artifact: TransformationArtifact) -> str:
        return artifact.source_path.read_text()

    def deliver(
        self,
        artifact: TransformationArtifact,
        ordinal: int,
        profile: ModalityProfile,
    ) -> KitFile:
        """Upgrade phone-call records to their audio rendition when allowed.

        Case records are text-native, so the transcript is the default
        rendition at every profile. Under a profile that allows audio, a
        phone-call record (any transcript dialect) with committed sibling
        recordings (``recordings/<case>.m4a``) ships as the recordings plus
        a stub case file whose spoken dialogue is replaced by a pointer —
        substitution, not addition, so audio-capable models must actually
        listen. Console events, headers, trailing prose sections, and chat
        segments stay in the stub: they are not speech and never made it
        into the audio.
        """
        kit_file = self.neutralize(artifact, ordinal)
        if not profile.allows("audio"):
            return kit_file
        dialect = phone_transcript_dialect(artifact.source_path)
        if dialect is None:
            return kit_file
        recordings = self._recording_paths(artifact.source_path, dialect)
        if recordings is None:
            return kit_file
        kit_file.content = _strip_spoken_dialogue(
            kit_file.content.decode(), dialect
        ).encode()
        kit_file.substituted_from = "text"
        primary = Path(kit_file.relative_path)
        kit_file.companions = [
            KitFile(
                relative_path=str(primary.with_name(f"{primary.stem}{tag}.m4a")),
                content=recording_path.read_bytes(),
            )
            for tag, recording_path in recordings
        ]
        return kit_file

    @staticmethod
    def _recording_paths(
        source_path: Path, dialect: str
    ) -> list[tuple[str, Path]] | None:
        """Committed audio renditions of a phone-call record, if complete.

        Telecom archive records render one recording per phone segment
        (``case_007.m4a`` / ``case_007_followup.m4a``); every other dialect
        is a single call with a single rendition. The upgrade is
        all-or-nothing: unless every phone segment has its committed
        recording the record stays a transcript, so spoken dialogue is
        never dropped without its audio. Returns ``(stem tag, path)``
        pairs so companions keep the per-segment suffixes.
        """
        if dialect == "telecom":
            tags = [
                f"_{segment.segment_label}" if segment.segment_label else ""
                for segment in parse_telecom_transcript(source_path)
                if segment.channel == "Phone"
            ]
        else:
            tags = [""]
        recordings = [
            (tag, source_path.parent / "recordings" / f"{source_path.stem}{tag}.m4a")
            for tag in tags
        ]
        if not recordings or not all(path.is_file() for _, path in recordings):
            return None
        return recordings

    def validate(
        self, schema: dict[str, Any], artifacts: list[TransformationArtifact]
    ) -> list[str]:
        # A declared-path typo must fail at compile, not at kit build:
        # discover_artifacts trusts spec["artifacts"] paths verbatim, and
        # neutralize() is the first reader otherwise (client overlay packs
        # re-declare every case path, so this is where a typo would land).
        missing = [
            artifact for artifact in artifacts if not artifact.source_path.is_file()
        ]
        if missing:
            return [
                f"declared transcript artifact does not exist: {artifact.source_path}"
                for artifact in missing
            ]
        context_only = [
            artifact.metadata.get("context_only") is True for artifact in artifacts
        ]
        if any(context_only):
            if not all(context_only):
                return [
                    "support-transcript transformations must not mix context-only "
                    "and fact-bearing artifacts"
                ]
            issues = super().validate(schema, artifacts)
            for artifact in artifacts:
                if artifact.included_fact_ids:
                    issues.append(
                        f"{artifact.source_path.name}: context-only transcripts "
                        "must not declare included_fact_ids"
                    )
            return issues

        if not any(artifact.included_fact_ids for artifact in artifacts):
            # Legacy schemas track coverage on the transcript plan entries,
            # not per case file; validate the plan ids instead.
            fact_ids = schema_fact_ids(schema)
            declared: set[str] = set()
            for plan in schema.get("transcripts") or []:
                declared.update(plan.get("included_fact_ids", []))
            unknown = declared - fact_ids
            if unknown:
                return [f"transcript plans declare unknown fact ids: {sorted(unknown)}"]
            return []
        return super().validate(schema, artifacts)

    def covered_fact_ids(
        self, schema: dict[str, Any], artifacts: list[TransformationArtifact]
    ) -> set[str]:
        if not artifacts:
            # No case records exist on disk — plan entries alone must not
            # claim coverage for material that never reaches the kit.
            return set()
        if all(artifact.metadata.get("context_only") is True for artifact in artifacts):
            return set()
        covered = super().covered_fact_ids(schema, artifacts)
        if covered:
            return covered
        # Legacy schemas: coverage lives on the transcript plan entries.
        return {
            fact_id
            for plan in schema.get("transcripts") or []
            for fact_id in plan.get("included_fact_ids", [])
        }

    @staticmethod
    def _resolve(path: str | Path, schema_path: Path) -> Path:
        resolved = Path(path)
        if resolved.is_absolute():
            return resolved
        return DATA_DIR / resolved


register_transformation(SupportTranscriptsTransformation())
