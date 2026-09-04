"""Clock-coherence gate for the airline_plus tree.

The airline_plus world clock is 2024-05-15 15:00 EST (policy.md front matter,
db.json flight instances). Every in-world *record* timestamp — email Date
headers, authored ``sent``/``sent_at`` stamps, Slack root epochs and capture
``ts`` values, dated stamps inside training records — must precede the clock.
Future *travel* dates are legitimate (bookings reach past the clock), so the
gate targets year tokens and machine timestamps, never bare month-day prose.

Allowlisted exception: ``authored_fact_renditions.json`` carries out-of-world
construction metadata (``adjudicated_by`` blocks dated 2026-08); those stamps
describe when maintainers adjudicated a rendition, not anything in-world.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from email import message_from_bytes
from email.utils import parsedate_to_datetime
from pathlib import Path

from tau2.utils.utils import DATA_DIR

PLUS_ROOT = DATA_DIR / "tau2/hyper/sops/airline_plus"
DOMAIN_ROOT = DATA_DIR / "tau2/domains/airline_plus"

# 2024-05-15 15:00 US/Eastern (EDT) == 19:00 UTC.
CLOCK = datetime(2024, 5, 15, 19, 0, tzinfo=timezone.utc)
CLOCK_EPOCH = int(CLOCK.timestamp())

TEXT_SUFFIXES = {
    ".md",
    ".json",
    ".txt",
    ".html",
    ".eml",
    ".py",
    ".csv",
    ".yaml",
    ".mjs",
    ".cjs",
}

# Post-clock year token. Hex guards keep hash-derived Message-IDs, Slack
# permalink microsecond runs, and render digests from false-positiving while
# still catching prose years and ISO dates (their neighbours are spaces,
# punctuation, or hyphens). The underscore guard skips numeric identifier
# suffixes (db handles like helena_everett_2027).
POST_CLOCK_YEAR_RE = re.compile(r"(?<![0-9a-fA-F_])202[5-9](?![0-9a-fA-F])")

# Non-temporal / out-of-world lines the year scan must ignore:
#   - db money values that happen to land on a year-shaped number
#   - task provenance notes (maintainer metadata, never delivered in-world)
YEAR_SCAN_LINE_ALLOW_RE = re.compile(r'"(?:amount|price)"\s*:\s*202[5-9]\b')
TASK_FILES_WITH_NOTES = {"tasks.json", "new_tasks_source.json"}

# delta_spec.yaml is the construction-values registry: out-of-world
# provenance comments (PR phases, cutover stamps) live there by design.
YEAR_SCAN_SKIP_FILES = {"authored_fact_renditions.json", "delta_spec.yaml"}

# ISO timestamps (date + time) are always record stamps, never travel dates.
ISO_STAMP_RE = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)[ T](\d\d):(\d\d)")


def _text_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            yield path


def test_no_post_clock_year_tokens() -> None:
    offenders: list[str] = []
    for root in (PLUS_ROOT, DOMAIN_ROOT):
        for path in _text_files(root):
            if path.name in YEAR_SCAN_SKIP_FILES:
                continue  # renditions checked structurally below; delta_spec is provenance
            text = path.read_text(encoding="utf-8", errors="ignore")
            for i, line in enumerate(text.splitlines(), 1):
                if not POST_CLOCK_YEAR_RE.search(line):
                    continue
                if YEAR_SCAN_LINE_ALLOW_RE.search(line):
                    continue
                if path.name in TASK_FILES_WITH_NOTES and re.match(
                    r'\s*"notes"\s*:', line
                ):
                    continue
                offenders.append(
                    f"{path.relative_to(DATA_DIR)}:{i}: {line.strip()[:120]}"
                )
    assert not offenders, "post-clock year tokens found:\n" + "\n".join(offenders[:40])


def test_eml_date_headers_precede_clock() -> None:
    offenders: list[str] = []
    for path in sorted(PLUS_ROOT.rglob("*.eml")):
        message = message_from_bytes(path.read_bytes())
        stamp = parsedate_to_datetime(message["Date"])
        if stamp > CLOCK:
            offenders.append(f"{path.relative_to(PLUS_ROOT)}: {message['Date']}")
    assert not offenders, "post-clock eml Date headers:\n" + "\n".join(offenders[:20])


def test_iso_record_stamps_precede_clock() -> None:
    offenders: list[str] = []
    for path in _text_files(PLUS_ROOT):
        if path.name == "authored_fact_renditions.json":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in ISO_STAMP_RE.finditer(text):
            year, month, day, hour, minute = (int(g) for g in match.groups())
            try:
                stamp = datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
            except ValueError:
                continue
            # Compare on the date only: local-time stamps carry no offset, so
            # granting the rest of the clock day absorbs any timezone skew.
            if stamp.date() > CLOCK.date():
                offenders.append(f"{path.relative_to(PLUS_ROOT)}: {match.group(0)}")
    assert not offenders, "post-clock ISO record stamps:\n" + "\n".join(offenders[:20])
