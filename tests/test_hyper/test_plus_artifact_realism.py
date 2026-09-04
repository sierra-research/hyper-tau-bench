"""Cross-domain realism guards for maintained Airline+ and Retail+ artifacts."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from pathlib import Path

from tau2.utils.utils import DATA_DIR

SOPS_ROOT = DATA_DIR / "tau2/hyper/sops"
AIRLINE_HARD = SOPS_ROOT / "airline_plus/hard_bundle_001"
RETAIL_HARD = SOPS_ROOT / "retail_plus/hard_bundle_001"
ONTOLOGY_TERMS = re.compile(
    r"\b(?:answer key|learner transcript|evaluator|evaluation corpus|fact ids?|"
    r"test fixture|developer package|author-side|distractor)\b",
    re.IGNORECASE,
)


def _plain_body(path: Path) -> tuple[object, str]:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    body = message.get_body(preferencelist=("plain",))
    assert body is not None, path
    return message, body.get_content()


def _header_value(block: str, name: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(name)}:\s*(.+)$", block)
    return match.group(1).strip() if match else None


def _assert_thread_chain(path: Path) -> None:
    message, body = _plain_body(path)
    quoted = body.split("-----Original Message-----")[1:]
    assert quoted, path

    message_ids = [str(message["Message-ID"])]
    message_ids.extend(_header_value(block, "Message-ID") for block in quoted)
    assert all(message_ids), path
    assert len(message_ids) == len(set(message_ids)), path

    top_references = str(message["References"]).split()
    assert str(message["In-Reply-To"]) == message_ids[1], path
    assert top_references == list(reversed(message_ids[1:])), path

    for position, block in enumerate(quoted, start=1):
        parent = _header_value(block, "In-Reply-To")
        references = (_header_value(block, "References") or "").split()
        if position == len(message_ids) - 1:
            assert parent is None, path
            assert references == [], path
            continue
        assert parent == message_ids[position + 1], path
        assert references == list(reversed(message_ids[position + 1 :])), path


def _slack_messages(path: Path) -> dict[tuple[str, str], str]:
    payload = json.loads(path.read_text())
    messages: dict[tuple[str, str], str] = {}

    def walk(value: object) -> None:
        if isinstance(value, dict):
            if isinstance(value.get("ts"), str) and isinstance(value.get("text"), str):
                key = (str(value.get("channel_id", "")), value["ts"])
                previous = messages.setdefault(key, value["text"])
                assert previous == value["text"]
            for nested in value.values():
                walk(nested)
        elif isinstance(value, list):
            for nested in value:
                walk(nested)

    walk(payload)
    return messages


def _vtt_cues(path: Path) -> list[tuple[int, int, str, str]]:
    cue_pattern = re.compile(
        r"(?P<sh>\d+):(?P<sm>\d{2}):(?P<ss>\d{2})\.(?P<sms>\d{3}) --> "
        r"(?P<eh>\d+):(?P<em>\d{2}):(?P<es>\d{2})\.(?P<ems>\d{3})\n"
        r"<v (?P<speaker>[^>]+)>(?P<text>.*)"
    )
    cues = []
    for match in cue_pattern.finditer(path.read_text()):
        start = (
            int(match["sh"]) * 3_600 + int(match["sm"]) * 60 + int(match["ss"])
        ) * 1_000 + int(match["sms"])
        end = (
            int(match["eh"]) * 3_600 + int(match["em"]) * 60 + int(match["es"])
        ) * 1_000 + int(match["ems"])
        cues.append((start, end, match["speaker"], match["text"]))
    return cues


def test_email_archives_preserve_complete_rfc_reply_chains():
    directories = (
        SOPS_ROOT / "airline_plus/sections/authorized_scope/email_thread_archive_001",
        SOPS_ROOT
        / "retail_plus/sections/manage_pending_order/email_thread_archive_001",
        AIRLINE_HARD / "booking_emails",
        AIRLINE_HARD / "manage_emails",
        RETAIL_HARD / "pending_emails",
    )
    paths = [path for directory in directories for path in directory.glob("*.eml")]
    assert len(paths) == 181
    for path in paths:
        _assert_thread_chain(path)


def test_hard_email_archives_do_not_postdate_the_snapshot():
    snapshot = datetime(2026, 8, 6, 18, tzinfo=timezone.utc)
    paths = [
        *AIRLINE_HARD.joinpath("booking_emails").glob("*.eml"),
        *AIRLINE_HARD.joinpath("manage_emails").glob("*.eml"),
        *RETAIL_HARD.joinpath("pending_emails").glob("*.eml"),
    ]
    for path in paths:
        message, _body = _plain_body(path)
        assert parsedate_to_datetime(str(message["Date"])) <= snapshot, path


def test_core_support_records_open_like_delivered_archives():
    # The fact-carrying case records must pool with the hand-authored filler
    # archives, which open directly at a numbered turn. A labeled opening
    # scaffold (or any templated block before the first turn) would mark
    # every carrier record on sight.
    directories = (
        SOPS_ROOT
        / "airline_plus/sections/booking_flight/bundles/booking_visual_hybrid/training_records",
        SOPS_ROOT
        / "airline_plus/sections/modifying_reservation/bundles/modification_visual_hybrid/training_records",
        SOPS_ROOT
        / "airline_plus/sections/compensation_certificates/bundles/compensation_website_hybrid/training_records",
        SOPS_ROOT
        / "retail_plus/sections/manage_customer_profile/support_transcripts_001",
        SOPS_ROOT
        / "retail_plus/sections/manage_delivered_order/support_transcripts_001",
    )
    records = [
        path for directory in directories for path in directory.glob("case_*.md")
    ]
    assert len(records) == 133
    openings: dict[str, Path] = {}
    for path in records:
        text = path.read_text()
        assert "**Channel opening" not in text, path
        assert "(brief overlap)" not in text and "(quietly)" not in text, path
        assert re.search(
            r"^Channel:.*\b(?:phone|chat)\b", text, re.MULTILINE | re.IGNORECASE
        ), path
        first_block = re.search(r"(?m)^\*\*", text)
        assert first_block, path
        assert re.match(r"\*\*Turn\s+\d+\b", text[first_block.start() :]), path
        first_customer = re.search(r"(?m)^\*\*Turn \d+ · Customer:\*\* (.+)$", text)
        assert first_customer, path
        opening = " ".join(first_customer.group(1).split()).lower()
        # Agents open from a script, so their greetings legitimately repeat;
        # two customers opening with the same long message is a template
        # fingerprint.
        if len(opening.split()) >= 8:
            previous = openings.setdefault(opening, path)
            assert previous == path, (previous, path, opening[:80])


def test_generated_support_records_have_varied_lengths_and_no_turn_loops():
    # Realism gate is distribution shape, never specific phrases or pinned
    # length tails: a mandated verbal tic or a fixed floor/ceiling/tail-count
    # is itself a corpus signature a reader could exploit to separate carrier
    # records from filler.
    airline_records = [
        *AIRLINE_HARD.joinpath("booking_records").glob("case_*.md"),
        *AIRLINE_HARD.joinpath("modification_records").glob("case_*.md"),
        *AIRLINE_HARD.joinpath("compensation_records").glob("case_*.md"),
    ]
    retail_records = [
        *RETAIL_HARD.joinpath("profile_records").glob("case_*.md"),
        *RETAIL_HARD.joinpath("delivered_records").glob("case_*.md"),
    ]
    airline_lengths = []
    retail_lengths = []
    for path in airline_records:
        text = path.read_text()
        turns = re.findall(r"(?m)^\*\*Turn \d+ · [^:]+:\*\* (.+)$", text)
        assert len(turns) == len(set(turns)), path
        airline_lengths.append(len(turns))
    for path in retail_records:
        text = path.read_text()
        turns = re.findall(r"(?m)^\*\*Turn \d+ · [^:]+:\*\* (.+)$", text)
        assert len(turns) == len(set(turns)), path
        retail_lengths.append(len(turns))
    for lengths in (airline_lengths, retail_lengths):
        assert min(lengths) >= 6
        # Production calls run to ~200 turns when interruptions pile up, so
        # the ceiling is a runaway-generation-loop guard, not a length pin.
        assert max(lengths) <= 200
        assert max(lengths) - min(lengths) >= 10
        assert len(set(lengths)) >= 8
        assert max(Counter(lengths).values()) <= len(lengths) // 4


def test_recorded_sessions_sound_like_meetings_without_evaluator_ontology():
    core_paths = sorted(
        SOPS_ROOT.joinpath(
            "retail_plus/sections/service_foundations/recorded_working_session_001"
        ).glob("*.vtt")
    )
    hard_paths = sorted(RETAIL_HARD.joinpath("recordings").glob("*.vtt"))
    assert len(core_paths) == 5
    assert len(hard_paths) == 4
    for path in [*core_paths, *hard_paths]:
        cues = _vtt_cues(path)
        assert cues, path
        spoken = " ".join(text for _start, _end, _speaker, text in cues)
        assert ONTOLOGY_TERMS.search(spoken) is None, path

    # The hard sessions must pool with the core series on mechanical texture
    # (cue density, speaking pace, cast size) rather than matching any
    # scripted phrasing, and no long sentence may repeat across the series.
    def _density(path):
        cues = _vtt_cues(path)
        return len(cues) / (max(end for _s, end, _sp, _t in cues) / 60_000)

    def _sentences(path):
        cues = _vtt_cues(path)
        spoken = " ".join(text for _start, _end, _speaker, text in cues)
        return {
            sentence.strip().lower()
            for sentence in re.split(r"(?<=[.!?])\s+", spoken)
            if len(sentence.split()) >= 8
        }

    core_density = [_density(path) for path in core_paths]
    core_sentences = set().union(*(_sentences(path) for path in core_paths))
    seen_sentences: dict[str, Path] = {}
    openings = []
    for path in hard_paths:
        cues = _vtt_cues(path)
        texts = [text for _start, _end, _speaker, text in cues]
        assert min(core_density) - 1.0 <= _density(path) <= max(core_density) + 1.0, (
            path
        )
        speech_minutes = (
            sum(end - start for start, end, _speaker, _text in cues) / 60_000
        )
        words_per_minute = sum(len(text.split()) for text in texts) / speech_minutes
        assert 90 <= words_per_minute <= 115, path
        assert len(texts) == len(set(texts)), path
        assert len({speaker for _start, _end, speaker, _text in cues}) >= 4, path
        openings.append(" ".join(texts[:8]).lower())
        for sentence in _sentences(path):
            assert sentence not in core_sentences, (path, sentence[:90])
            previous = seen_sentences.setdefault(sentence, path)
            assert previous == path, (previous, path, sentence[:90])
    assert len(openings) == len(set(openings))


def test_generated_websites_are_page_specific_and_not_evaluator_facing():
    pages = [
        *AIRLINE_HARD.joinpath("booking_website/pages").glob("*.html"),
        *AIRLINE_HARD.joinpath("modification_website/pages").glob("*.html"),
        *AIRLINE_HARD.joinpath("compensation_website/pages").glob("*.html"),
        *RETAIL_HARD.joinpath("website/pages").glob("*.html"),
    ]
    bodies = []
    paragraphs = []
    for path in pages:
        text = path.read_text()
        assert (
            re.search(
                r"do not infer|distractor|answer key|not a (?:servicing|policy) source",
                text,
                re.IGNORECASE,
            )
            is None
        ), path
        body = re.sub(r"<[^>]+>", " ", text)
        bodies.append(" ".join(body.split()))
        # Authored article copy must be page-specific. The retail hard pages
        # share the core site archive's chrome (headers, endings, directory
        # modules), whose boilerplate legitimately repeats across the site,
        # so restrict the uniqueness check to the article main content when
        # that structure is present.
        article_match = re.search(
            r'<div class="help-article__main">(.*?)</div>', text, re.DOTALL
        )
        scope = article_match.group(1) if article_match else text
        paragraphs.extend(
            " ".join(re.sub(r"<[^>]+>", " ", value).split())
            for value in re.findall(r"<p[^>]*>(.*?)</p>", scope, re.DOTALL)
            if len(value.split()) >= 12
        )
    assert len(bodies) == len(set(bodies))
    assert len(paragraphs) == len(set(paragraphs))


def test_generated_slack_messages_do_not_repeat_scripted_replies():
    captures = (
        AIRLINE_HARD / "slack_capture/passenger_servicing_capture.json",
        RETAIL_HARD / "slack/beacon_workspace_capture_hard.json",
    )
    for path in captures:
        messages = _slack_messages(path)
        repeated = {
            text: count
            for text, count in Counter(messages.values()).items()
            if count > 1 and len(text.split()) >= 8
        }
        assert repeated == {}, path


def test_flowcharts_and_long_form_documents_do_not_use_one_template():
    flowcharts = sorted(RETAIL_HARD.joinpath("flowcharts").glob("*.txt"))
    assert len(flowcharts) == 6
    assert (RETAIL_HARD / "flowcharts/beacon_program_operations_board.html").exists()
    seen_sentences: dict[str, Path] = {}
    for number, path in enumerate(flowcharts, start=1):
        text = path.read_text()
        assert text.startswith(f"Frame {number} -"), path
        for sentence in re.split(r"(?<=[.!?])\s+", " ".join(text.split())):
            if len(sentence.split()) < 8:
                continue
            previous = seen_sentences.setdefault(sentence.lower(), path)
            assert previous == path, (previous, path, sentence[:80])

    documents = [
        *AIRLINE_HARD.joinpath("kickoff_documents").glob("*.md"),
        *RETAIL_HARD.joinpath("identity_docs").glob("*.md"),
    ]
    long_paragraphs = []
    for path in documents:
        paragraphs = [
            " ".join(block.split())
            for block in path.read_text().split("\n\n")
            if len(block.split()) >= 30
        ]
        assert len(paragraphs) == len(set(paragraphs)), path
        long_paragraphs.extend(paragraphs)
    assert len(long_paragraphs) == len(set(long_paragraphs))
