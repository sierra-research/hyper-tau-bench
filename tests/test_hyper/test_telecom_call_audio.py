# Copyright Sierra
"""Gates for the telecom call-audio renditions.

Telecom phone records use the timestamped archive form (`Channel: Phone`,
`[MM:SS]` turns) and may carry a follow-up call segment, so one record can
own two renditions: recordings/case_N.m4a and recordings/case_N_followup.m4a.
These gates keep the rendition set all-or-nothing across the whole tree —
a partial set would mark which records matter (evidence-class anonymity) —
and pin every rendition byte to the committed provenance.
"""

import fnmatch
import hashlib
import json
from pathlib import Path

from tau2.hyper.transformations.transcript_artifacts import (
    find_telecom_phone_transcripts,
    parse_telecom_transcript,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
TELECOM_ROOT = REPO_ROOT / "data" / "tau2" / "hyper" / "sops" / "telecom"


def _phone_segments():
    """(record path, segment) for every Phone segment in the tree."""
    return [
        (path, segment)
        for path in find_telecom_phone_transcripts(TELECOM_ROOT)
        for segment in parse_telecom_transcript(path)
        if segment.channel == "Phone"
    ]


def _rendition_path(record: Path, segment) -> Path:
    stem = record.stem + (f"_{segment.segment_label}" if segment.segment_label else "")
    return record.parent / "recordings" / f"{stem}.m4a"


def test_call_audio_renditions_complete():
    """Every Phone segment has a committed rendition and every rendition
    maps back to a Phone segment.

    All-or-nothing per tree: if only some phone calls carried audio, the
    rendition set itself would mark which records matter. Chat segments
    never render — a rendition for one is as much drift as a missing one.
    Byte-level integrity is the provenance pin's job; this gate owns the
    mapping, including the segment-suffix convention for follow-up calls.
    """
    segments = _phone_segments()
    assert segments, "no telecom phone segments found"

    expected = {_rendition_path(record, segment) for record, segment in segments}
    committed = set(TELECOM_ROOT.rglob("recordings/*.m4a"))

    missing = sorted(str(p.relative_to(TELECOM_ROOT)) for p in expected - committed)
    orphaned = sorted(str(p.relative_to(TELECOM_ROOT)) for p in committed - expected)
    assert not missing and not orphaned, (
        f"renditions out of sync — missing {missing}, orphaned {orphaned}"
    )


def test_render_provenance_pins_match():
    """Every pinned call-audio source and output hashes to the committed pin.

    TTS renders run out of band, so CI cannot re-render and compare. The
    pin proves staleness instead: a transcript edited without re-rendering
    + re-pinning, an .m4a swapped without re-pinning, or a new/removed file
    dodging a pinned glob all break here (same contract as the airline and
    retail artifact-port suites).
    """
    pin = json.loads((TELECOM_ROOT / "render_provenance.json").read_text())
    assert pin["groups"]
    problems = []
    for group in pin["groups"]:
        for glob_key, files_key in (
            ("source_glob", "sources"),
            ("output_glob", "outputs"),
        ):
            pattern = group.get(glob_key)
            if not pattern:
                continue
            current = {
                str(p.relative_to(TELECOM_ROOT)) for p in TELECOM_ROOT.glob(pattern)
            }
            pinned = {rel for rel in group[files_key] if fnmatch.fnmatch(rel, pattern)}
            if current != pinned:
                problems.append(
                    f"{group['id']}: {glob_key} drift — unpinned"
                    f" {sorted(current - pinned)},"
                    f" missing {sorted(pinned - current)}"
                )
        for files_key in ("sources", "outputs"):
            for rel, pinned_sha in group[files_key].items():
                path = TELECOM_ROOT / rel
                if not path.exists():
                    problems.append(f"{group['id']}: {rel} missing")
                    continue
                if hashlib.sha256(path.read_bytes()).hexdigest() != pinned_sha:
                    problems.append(
                        f"{group['id']}: {rel} hash drift — if a source"
                        " changed, re-render its outputs and update the"
                        " pinned hashes in render_provenance.json"
                    )
    assert not problems, "\n".join(problems)


def test_pinned_records_dirs_cover_every_phone_record():
    """The provenance pin's telecom group list spans the whole tree.

    A phone record added in a new directory must join a pinned group; this
    fails loudly instead of letting an unpinned directory drift.
    """
    pin = json.loads((TELECOM_ROOT / "render_provenance.json").read_text())
    pinned_dirs = {
        group["call_audio_records_dir"]
        for group in pin["groups"]
        if "call_audio_records_dir" in group
    }
    actual_dirs = {
        record.parent.relative_to(TELECOM_ROOT).as_posix()
        for record in find_telecom_phone_transcripts(TELECOM_ROOT)
    }
    assert actual_dirs == pinned_dirs, (
        f"unpinned record dirs {sorted(actual_dirs - pinned_dirs)}, "
        f"stale pinned dirs {sorted(pinned_dirs - actual_dirs)}"
    )
