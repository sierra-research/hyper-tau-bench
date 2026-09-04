# Copyright Sierra
"""Runtime parser for Telecom transcript artifacts.

Telecom records (``Channel: Phone``) use a timestamped archive form::

    [MM:SS] **Agent:** <spoken text>
    [MM:SS] **Customer:** <spoken text>
    [MM:SS] **Console note:** <non-spoken system event>

under a ``## Transcript`` section; a record may carry additional call
segments (``## Follow-up contact``), each with its own header block
(Channel / Start time / Handle time) and its own agent. Timestamps are the
authored pacing and reset per segment. ``parse_telecom_transcript`` returns
one ``CallTranscript`` per segment with synthetic 1..N turn numbers and
``timestamp_s`` set on every event.

Generic and Banking parsers used only to render source call audio are
maintained privately with the authoring tooling; the benchmark runtime
carries only what kit assembly and artifact substitution need.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal, Union

from pydantic import BaseModel

TURN_RE = re.compile(r"^\*\*Turn (\d+) · (Agent|Customer):\*\*\s*(.*)$")
CONSOLE_RE = re.compile(
    r"^\*\*(?:After turn|Turn) (\d+) · Support console:\*\*\s*(.*)$"
)
CASE_RE = re.compile(r"^# Case (.+)$")
CHANNEL_RE = re.compile(r"^Channel:\s*(.+?)\s*$")
QA_STATUS_RE = re.compile(r"^QA status:\s*(.+?)\s*$")


class SpokenTurn(BaseModel):
    kind: Literal["turn"] = "turn"
    turn: int
    # "agent2" is a second agent joining the same call (telecom warm
    # transfer); sections/hard records only ever use agent/customer.
    role: Literal["agent", "customer", "agent2"]
    text: str
    # Telecom archive form only: authored start offset within the call.
    timestamp_s: float | None = None


class ConsoleEvent(BaseModel):
    kind: Literal["console"] = "console"
    after_turn: int
    text: str
    timestamp_s: float | None = None


CallEvent = Union[SpokenTurn, ConsoleEvent]


class CallTranscript(BaseModel):
    case_id: str
    channel: str
    qa_status: str
    record_type: str = ""
    case_reference: str = ""
    source_path: Path
    events: list[CallEvent]
    # Telecom archive form only.
    segment_label: str = ""  # "" primary; "followup" for later segments
    handle_time_s: float | None = None
    scene_events: list["SceneEvent"] = []

    @property
    def timestamped(self) -> bool:
        return any(e.timestamp_s is not None for e in self.events)

    @property
    def spoken_turns(self) -> list[SpokenTurn]:
        return [event for event in self.events if isinstance(event, SpokenTurn)]

    @property
    def console_events(self) -> list[ConsoleEvent]:
        return [event for event in self.events if isinstance(event, ConsoleEvent)]

    @property
    def is_phone_call(self) -> bool:
        return self.channel == "phone call"


# --- Telecom archive form -------------------------------------------------

TELECOM_TURN_RE = re.compile(
    r"^\[(\d\d):(\d\d)\] \*\*(Agent 2|Agent|Customer):\*\*\s*(.*)$"
)
TELECOM_CONSOLE_RE = re.compile(r"^\[(\d\d):(\d\d)\] \*\*Console note:\*\*\s*(.*)$")
TELECOM_SEGMENT_RE = re.compile(r"^## (Transcript|Follow-up contact)\s*$")
_TELECOM_HEADER_RES = {
    "start_time": re.compile(r"^Start time:\s*(.+?)\s*$"),
    "archive_date": re.compile(r"^Archive date:\s*(.+?)\s*$"),
    "handle_time": re.compile(r"^Handle time:\s*(?:(\d+)m\s*)?(\d+)s\s*$"),
}
_TELECOM_PHONE_RE = re.compile(r"^Channel:\s*Phone\s*$", re.MULTILINE)
_PHONE_CHANNEL_RE = re.compile(r"^Channel:\s*phone call\s*$", re.MULTILINE)
_BANKING_CASE_ID_RE = re.compile(r"^Case ID:\s*\S", re.MULTILINE)
_BANKING_ROOM_PHONE_RE = re.compile(r"^Channel:\s*phone\s*$", re.MULTILINE)

BANKING_TURN_RE = re.compile(r"^\[(\d\d):(\d\d)\] \*\*([^:*]+):\*\*\s*(.*)$")
BANKING_ROOM_TURN_RE = re.compile(r"^\*\*([^:*]+):\*\*\s*(.*)$")

# Runtime artifact substitution supports every committed transcript dialect,
# even though only Telecom needs a full parser while assembling a kit.
PhoneDialect = Literal["sections", "banking", "telecom", "banking_room"]


def phone_transcript_dialect(path: Path) -> PhoneDialect | None:
    """Classify the phone-record dialect needed for audio substitution."""
    text = path.read_text()
    if _PHONE_CHANNEL_RE.search(text):
        return "sections"
    if _TELECOM_PHONE_RE.search(text):
        return "banking" if _BANKING_CASE_ID_RE.search(text) else "telecom"
    if _BANKING_ROOM_PHONE_RE.search(text):
        return "banking_room"
    return None


def is_telecom_phone_file(path: Path) -> bool:
    """Check the telecom Channel header line (``Channel: Phone``)."""
    return _TELECOM_PHONE_RE.search(path.read_text()) is not None


def find_telecom_phone_transcripts(root: Path) -> list[Path]:
    """Find all telecom phone-archive records under a directory."""
    paths = []
    for path in sorted(root.rglob("case_*.md")):
        if ".claude" in path.parts:
            continue
        if is_telecom_phone_file(path):
            paths.append(path)
    return paths


TELECOM_SCENE_RE = re.compile(r"^\[(\d\d):(\d\d)\] \*\*Call event:\*\*\s*(.*)$")
TELECOM_QA_RE = re.compile(
    r"^\[(\d\d):(\d\d)\] \*\*QA annotation \(post-review[^)]*\):\*\*\s*(.*)$"
)
# Chat segments stamp lines with wall-clock datetimes; their content is
# consumed without phone-format validation (chat never renders).
_CHAT_STAMP_RE = re.compile(r"^\[\d{4}-\d{2}-\d{2} [^\]]+\] \*\*")
_HEADER_KV_RE = re.compile(r"^[A-Z][A-Za-z' -]*:\s+\S")
_HANDLE_TIME_RE = re.compile(r"^Handle time:\s*(?:(\d+)m\s*)?(\d+)s\s*$")


class SceneEvent(BaseModel):
    """Non-spoken ambient marker (``**Call event:**``) — never rendered as
    speech; the authored timestamps already carry the pause it implies."""

    kind: Literal["scene"] = "scene"
    after_turn: int
    text: str
    timestamp_s: float | None = None


def parse_telecom_transcript(path: Path) -> list[CallTranscript]:
    """Parse a telecom archive record into one CallTranscript per segment.

    Segments are ``## Transcript`` and ``## Follow-up contact`` blocks, each
    with its own header (Channel / Start time / Handle time) and its own
    agent; the first segment inherits the record header. Channel is
    per-segment — a chat record may carry a phone follow-up and vice versa.
    Phone segments parse strictly (turns, console notes, call events, QA
    annotations; timestamps non-decreasing); chat segments are consumed
    without validation and returned with their channel so callers can skip
    them. Spoken turns get synthetic 1..N numbers per segment. QA
    annotations are validated and dropped: they are post-review notes, not
    part of the call.
    """
    lines = path.read_text().splitlines()

    # Chunk the file: record header, then one chunk per "## ..." heading.
    chunks: list[list[tuple[int, str]]] = [[]]
    for line_no, raw in enumerate(lines, start=1):
        line = raw.rstrip()
        if TELECOM_SEGMENT_RE.match(line):
            chunks.append([])
            continue
        chunks[-1].append((line_no, line))

    header, segment_chunks = chunks[0], chunks[1:]
    if not segment_chunks:
        raise ValueError(f"{path}: no '## Transcript' section found")

    case_id = ""
    record_channel = ""
    qa_status = ""
    for _, line in header:
        if not line:
            continue
        if m := CASE_RE.match(line):
            case_id = m.group(1).strip()
        elif m := CHANNEL_RE.match(line):
            record_channel = m.group(1)
        elif m := QA_STATUS_RE.match(line):
            qa_status = m.group(1)
        elif not _HEADER_KV_RE.match(line):
            raise ValueError(f"{path}: unexpected record-header line: {line!r}")
    if not case_id:
        raise ValueError(f"{path}: missing '# Case ...' header")
    record_handle = _parse_handle_time(header)

    segments: list[CallTranscript] = []
    for index, chunk in enumerate(segment_chunks):
        channel = record_channel if index == 0 else ""
        handle_time = record_handle if index == 0 else None
        for _, line in chunk:
            if m := CHANNEL_RE.match(line):
                channel = m.group(1)
                break
        if index > 0:
            handle_time = _parse_handle_time(chunk)

        transcript = CallTranscript(
            case_id=case_id,
            channel=channel,
            qa_status=qa_status,
            source_path=path,
            events=[],
            segment_label=f"followup{index if index > 1 else ''}" if index > 0 else "",
            handle_time_s=handle_time,
        )
        if channel == "Phone":
            _parse_phone_segment(path, chunk, transcript)
            if not transcript.spoken_turns:
                raise ValueError(f"{path}: phone segment {index} has no spoken turns")
        segments.append(transcript)
    return segments


def _parse_handle_time(chunk: list[tuple[int, str]]) -> float | None:
    for _, line in chunk:
        if m := _HANDLE_TIME_RE.match(line):
            return float(int(m.group(1) or 0) * 60 + int(m.group(2)))
    return None


def _parse_phone_segment(
    path: Path, chunk: list[tuple[int, str]], transcript: CallTranscript
) -> None:
    current: SpokenTurn | ConsoleEvent | SceneEvent | None = None
    swallow = False  # continuation lines of a validated-then-dropped marker
    turn_no = 0
    last_ts = 0.0

    def stamp(minutes: str, seconds: str, line_no: int) -> float:
        nonlocal last_ts
        ts = float(int(minutes) * 60 + int(seconds))
        if ts < last_ts:
            raise ValueError(
                f"{path}:{line_no}: timestamp [{minutes}:{seconds}] goes "
                "backwards within a segment"
            )
        last_ts = ts
        return ts

    for line_no, line in chunk:
        if not line:
            continue
        if m := TELECOM_TURN_RE.match(line):
            turn_no += 1
            current = SpokenTurn(
                turn=turn_no,
                role=m.group(3).lower().replace("agent 2", "agent2"),
                text=m.group(4).strip(),
                timestamp_s=stamp(m.group(1), m.group(2), line_no),
            )
            transcript.events.append(current)
            swallow = False
        elif m := TELECOM_CONSOLE_RE.match(line):
            current = ConsoleEvent(
                after_turn=turn_no,
                text=m.group(3).strip(),
                timestamp_s=stamp(m.group(1), m.group(2), line_no),
            )
            transcript.events.append(current)
            swallow = False
        elif m := TELECOM_SCENE_RE.match(line):
            current = SceneEvent(
                after_turn=turn_no,
                text=m.group(3).strip(),
                timestamp_s=stamp(m.group(1), m.group(2), line_no),
            )
            transcript.scene_events.append(current)
            swallow = False
        elif m := TELECOM_QA_RE.match(line):
            stamp(m.group(1), m.group(2), line_no)
            current = None
            swallow = True
        elif line.startswith(("**", "[")):
            raise ValueError(f"{path}:{line_no}: unrecognized marker line: {line!r}")
        elif _HEADER_KV_RE.match(line) and current is None and not swallow:
            continue  # segment header block (Channel / Start time / ...)
        elif current is not None:
            current.text = f"{current.text} {line.strip()}".strip()
        elif swallow:
            continue
        else:
            raise ValueError(
                f"{path}:{line_no}: content line outside any turn: {line!r}"
            )
