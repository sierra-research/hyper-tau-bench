"""Modality-profile kit materialization: one bundle, per-tier renditions.

A modality profile selects exactly one rendition per artifact — text
substitutes for excluded modalities, audio upgrades for phone-call records
— so a single canonical bundle serves every model class without shipping
parallel task definitions.
"""

import json
from pathlib import Path

import pytest

from tau2.hyper.data_model import HyperMetadata
from tau2.hyper.transformations import get_transformation
from tau2.hyper.transformations.base import KitFile, TransformationArtifact
from tau2.hyper.transformations.modality import (
    DEFAULT_KIT_MODALITY_PROFILE,
    modality_for_path,
    parse_modality_profile,
)
from tau2.hyper.transformations.transcripts import _strip_spoken_dialogue

# ---------------------------------------------------------------------------
# Profile parsing
# ---------------------------------------------------------------------------


def test_profile_parsing_canonicalizes_order_and_implies_text():
    assert str(parse_modality_profile("image+text")) == "text+image"
    assert str(parse_modality_profile("video")) == "text+video"
    assert str(parse_modality_profile("full")) == "text+image+audio+video"
    assert str(parse_modality_profile(" TEXT+Image ")) == "text+image"


def test_profile_parsing_rejects_unknown_modalities():
    with pytest.raises(ValueError, match="hologram"):
        parse_modality_profile("text+hologram")
    with pytest.raises(ValueError, match="empty"):
        parse_modality_profile("")


def test_default_profile_reproduces_pre_profile_kits():
    # Images and videos shipped natively before profiles existed; audio
    # renditions never shipped. Changing this default silently changes
    # every existing benchmark kit.
    assert str(DEFAULT_KIT_MODALITY_PROFILE) == "text+image+video"


def test_suffix_classification():
    assert modality_for_path("a/screen.png") == "image"
    assert modality_for_path("a/call.m4a") == "audio"
    assert modality_for_path("a/walkthrough.mp4") == "video"
    # HTML-derived prints carry real text layers; office files are
    # shell-extractable — both stay text-accessible.
    assert modality_for_path("a/deck.pdf") == "text"
    assert modality_for_path("a/case.md") == "text"


def test_hyper_metadata_normalizes_modality_profile():
    metadata = _minimal_metadata(modality_profile="image+text")
    assert metadata.modality_profile == "text+image"
    with pytest.raises(ValueError, match="unknown modalities"):
        _minimal_metadata(modality_profile="text+smell")
    assert _minimal_metadata().modality_profile is None


def _minimal_metadata(**overrides) -> HyperMetadata:
    return HyperMetadata(
        source_domain="mock",
        task_description="",
        client_instructions="",
        training_task_ids=[],
        test_task_ids=[],
        **overrides,
    )


# ---------------------------------------------------------------------------
# Text substitution for image artifacts
# ---------------------------------------------------------------------------

_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c626001000000ffff03000006000557bfabd40000000049"
    "454e44ae426082"
)


def _screenshot_artifact(tmp_path: Path, **metadata) -> TransformationArtifact:
    png = tmp_path / "promo_banner.png"
    png.write_bytes(_PNG_BYTES)
    html = tmp_path / "promo_banner.html"
    html.write_text(
        "<html><head><style>.x{color:red}</style>"
        "<script>secret()</script></head>"
        "<body><!-- authoring note --><h1>Checked bags</h1>"
        "<p>Two bags fly free.</p></body></html>"
    )
    return TransformationArtifact(
        source_path=png,
        metadata={"text_source_path": html, **metadata},
    )


def test_screenshot_ships_natively_when_profile_allows_image(tmp_path):
    transformation = get_transformation("website_screenshot")
    artifact = _screenshot_artifact(tmp_path)
    kit_file = transformation.deliver(artifact, 1, parse_modality_profile("text+image"))
    assert kit_file.relative_path.endswith("screen_001.png")
    assert kit_file.content == _PNG_BYTES
    assert kit_file.substituted_from is None


def test_screenshot_substitutes_visible_text_under_text_profile(tmp_path):
    transformation = get_transformation("website_screenshot")
    artifact = _screenshot_artifact(tmp_path)
    kit_file = transformation.deliver(artifact, 1, parse_modality_profile("text"))
    assert kit_file.relative_path.endswith("screen_001.txt")
    assert kit_file.substituted_from == "image"
    text = kit_file.content.decode()
    assert "Two bags fly free." in text
    # The substitute is the *visible* text, not the raw source: no markup,
    # styles, scripts, or authoring comments may leak into the kit.
    for leak in ("<", "secret()", "authoring note", "color:red"):
        assert leak not in text


def test_artifact_without_text_rendition_fails_loudly(tmp_path):
    transformation = get_transformation("website_screenshot")
    png = tmp_path / "orphan.png"
    png.write_bytes(_PNG_BYTES)
    artifact = TransformationArtifact(source_path=png)
    with pytest.raises(ValueError, match="no shippable text rendition"):
        transformation.deliver(artifact, 1, parse_modality_profile("text"))


def test_video_timeline_is_not_shipped_without_explicit_declaration(tmp_path):
    # interactive_screen_recording's to_text is the author-side timeline
    # (fixture labels and all); only an explicit kit_text_path may ship.
    transformation = get_transformation("interactive_screen_recording")
    video = tmp_path / "walkthrough.mp4"
    video.write_bytes(b"ftyp-stub")
    timeline = tmp_path / "timeline.md"
    timeline.write_text("# APN recovery — clean fixture\n- 00:00 ...\n")
    artifact = TransformationArtifact(
        source_path=video,
        metadata={
            "kit_filename": "device_walkthrough.mp4",
            "text_source_path": timeline,
        },
    )
    with pytest.raises(ValueError, match="no shippable text rendition"):
        transformation.deliver(artifact, 1, parse_modality_profile("text"))

    shippable = tmp_path / "walkthrough_notes.md"
    shippable.write_text("Reset the APN to the carrier default, then reboot.\n")
    artifact.metadata["kit_text_path"] = shippable
    kit_file = transformation.deliver(artifact, 1, parse_modality_profile("text"))
    assert kit_file.relative_path.endswith("device_walkthrough.txt")
    assert b"carrier default" in kit_file.content
    assert "fixture" not in kit_file.content.decode()


# ---------------------------------------------------------------------------
# Audio upgrade for phone-call records
# ---------------------------------------------------------------------------

_PHONE_CALL_RECORD = """# Case DEMO-1

Channel: phone call
QA status: approved

**Turn 1 · Customer:** Can you hold this fare until Thursday?

**Turn 2 · Agent:** I don't have a way to freeze a quoted fare —
the price that exists Thursday is the price Thursday.

**After turn 2 · Support console:** Fare rules panel opened for MER616;
no hold provision listed.

**Turn 3 · Customer:** Understood, let's book it now then.
"""


def _call_artifact(tmp_path: Path, with_recording: bool) -> TransformationArtifact:
    record = tmp_path / "case_001.md"
    record.write_text(_PHONE_CALL_RECORD)
    if with_recording:
        recordings = tmp_path / "recordings"
        recordings.mkdir(exist_ok=True)
        (recordings / "case_001.m4a").write_bytes(b"m4a-rendition-bytes")
    return TransformationArtifact(source_path=record)


def test_phone_call_keeps_transcript_without_audio_profile(tmp_path):
    transformation = get_transformation("support_transcripts")
    artifact = _call_artifact(tmp_path, with_recording=True)
    kit_file = transformation.deliver(artifact, 7, DEFAULT_KIT_MODALITY_PROFILE)
    assert b"freeze a quoted fare" in kit_file.content
    assert kit_file.companions == []


def test_phone_call_upgrades_to_recording_under_audio_profile(tmp_path):
    transformation = get_transformation("support_transcripts")
    artifact = _call_artifact(tmp_path, with_recording=True)
    kit_file = transformation.deliver(artifact, 7, parse_modality_profile("full"))

    stub = kit_file.content.decode()
    # Substitution, not addition: no spoken dialogue survives in the stub.
    assert "freeze a quoted fare" not in stub
    assert "hold this fare" not in stub
    # Headers and console events are system material, not speech — kept.
    assert "Channel: phone call" in stub
    assert "Fare rules panel opened" in stub
    assert "companion call-recording" in stub

    assert [c.relative_path for c in kit_file.companions] == [
        "uploaded_materials/case_007.m4a"
    ]
    assert kit_file.companions[0].content == b"m4a-rendition-bytes"


def test_phone_call_without_recording_stays_a_transcript(tmp_path):
    transformation = get_transformation("support_transcripts")
    artifact = _call_artifact(tmp_path, with_recording=False)
    kit_file = transformation.deliver(artifact, 7, parse_modality_profile("full"))
    assert b"freeze a quoted fare" in kit_file.content
    assert kit_file.companions == []


def test_non_phone_records_never_gain_recordings(tmp_path):
    record = tmp_path / "case_001.md"
    record.write_text(
        "# Case DEMO-2\n\nChannel: chat\nQA status: approved\n\n"
        "**Turn 1 · Customer:** Hello.\n"
    )
    recordings = tmp_path / "recordings"
    recordings.mkdir()
    (recordings / "case_001.m4a").write_bytes(b"stray")
    transformation = get_transformation("support_transcripts")
    artifact = TransformationArtifact(source_path=record)
    kit_file = transformation.deliver(artifact, 1, parse_modality_profile("full"))
    assert kit_file.companions == []
    assert b"Hello." in kit_file.content


def test_strip_spoken_dialogue_mirrors_parser_continuations():
    stripped = _strip_spoken_dialogue(_PHONE_CALL_RECORD, "sections")
    # The hard-wrapped continuation of Turn 2 must not leak.
    assert "price Thursday" not in stripped
    # The hard-wrapped continuation of the console event must survive.
    assert "no hold provision listed" in stripped
    assert stripped.startswith("# Case DEMO-1")


# ---------------------------------------------------------------------------
# Audio upgrade: banking stamped support cases
# ---------------------------------------------------------------------------

_BANKING_CALL_RECORD = """# Case 011

Case ID: CRF-2511-0355
Channel: Phone
Contact date: 2025-11-07
Handle time: 6m 30s
QA status: kept-call library

## Transcript
[11:19] **Agent (Hana R.):** Rho card services, this is Hana.

[11:19] **Customer:** I need a referral link for my EcoCard —
my neighbor's applying this weekend.

[11:21] **Support console:** Identity verified, two factors matched.
Referral bonus history: bonus posted 11/03 08:52.

[11:22] **Supervisor:** Approved the exception on my authority.

## Case notes
2025-11-12 — Ratified at norming; a third referral inside a seven-day
window auto-denies.
"""


def _banking_call_artifact(
    tmp_path: Path, with_recording: bool
) -> TransformationArtifact:
    record = tmp_path / "case_011.md"
    record.write_text(_BANKING_CALL_RECORD)
    if with_recording:
        recordings = tmp_path / "recordings"
        recordings.mkdir(exist_ok=True)
        (recordings / "case_011.m4a").write_bytes(b"banking-m4a-bytes")
    return TransformationArtifact(source_path=record)


def test_banking_phone_case_upgrades_under_audio_profile(tmp_path):
    transformation = get_transformation("support_transcripts")
    artifact = _banking_call_artifact(tmp_path, with_recording=True)
    kit_file = transformation.deliver(artifact, 3, parse_modality_profile("full"))

    stub = kit_file.content.decode()
    # Spoken turns are gone — including hard-wrap continuations and the
    # named extra speaker a banking call may carry.
    assert "Rho card services" not in stub
    assert "referral link" not in stub
    assert "applying this weekend" not in stub
    assert "Approved the exception" not in stub
    # Header, console entries (with continuations), and trailing prose
    # sections never made it into the audio — all kept.
    assert "Case ID: CRF-2511-0355" in stub
    assert "## Transcript" in stub
    assert "[11:21] **Support console:** Identity verified" in stub
    assert "bonus posted 11/03 08:52" in stub
    assert "## Case notes" in stub
    assert "window auto-denies" in stub
    assert "companion call-recording" in stub

    assert [c.relative_path for c in kit_file.companions] == [
        "uploaded_materials/case_003.m4a"
    ]
    assert kit_file.companions[0].content == b"banking-m4a-bytes"


def test_banking_phone_case_without_recording_stays_a_transcript(tmp_path):
    transformation = get_transformation("support_transcripts")
    artifact = _banking_call_artifact(tmp_path, with_recording=False)
    kit_file = transformation.deliver(artifact, 3, parse_modality_profile("full"))
    assert b"Rho card services" in kit_file.content
    assert kit_file.companions == []


def test_banking_phone_case_keeps_transcript_without_audio_profile(tmp_path):
    transformation = get_transformation("support_transcripts")
    artifact = _banking_call_artifact(tmp_path, with_recording=True)
    kit_file = transformation.deliver(artifact, 3, DEFAULT_KIT_MODALITY_PROFILE)
    assert b"Rho card services" in kit_file.content
    assert kit_file.companions == []


_BANKING_ROOM_RECORD = """# Case 004

Channel: phone
Opened: 2025-11-03
Queue: card services

**Agent:** Thanks for calling, how can I help?

**Customer:** I want to close my card but keep the rewards.

**Console:** Account pulled; retention offer panel opened.
No prior downgrade on file.

**Agent:** Let me walk you through the downgrade path instead.
"""


def test_banking_room_phone_case_upgrades_under_audio_profile(tmp_path):
    transformation = get_transformation("support_transcripts")
    record = tmp_path / "case_004.md"
    record.write_text(_BANKING_ROOM_RECORD)
    (tmp_path / "recordings").mkdir()
    (tmp_path / "recordings" / "case_004.m4a").write_bytes(b"room-m4a-bytes")
    artifact = TransformationArtifact(source_path=record)
    kit_file = transformation.deliver(artifact, 2, parse_modality_profile("full"))

    stub = kit_file.content.decode()
    assert "close my card" not in stub
    assert "downgrade path" not in stub
    assert "Queue: card services" in stub
    assert "**Console:** Account pulled" in stub
    assert "No prior downgrade on file" in stub
    assert "companion call-recording" in stub
    assert [c.relative_path for c in kit_file.companions] == [
        "uploaded_materials/case_002.m4a"
    ]


# ---------------------------------------------------------------------------
# Audio upgrade: telecom stamped archive records
# ---------------------------------------------------------------------------

_TELECOM_CALL_RECORD = """# Case G

Channel: Phone
QA status: Approved
Archive date: 2026-08-05
Start time: 2026-08-01T17:02:44-07:00
Handle time: 2m 41s

## Transcript

[00:00] **Agent:** Northline Care, this is Elise.

[00:06] **Customer:** My data is gone and I'm boarding
in twenty minutes.

[00:15] **Console note:** Line 6640 identified and selected.
Everyday 5 GB plan.

[00:22] **Call event:** A boarding announcement plays; the customer
pauses to listen.

[00:30] **Agent 2:** Supervisor joining the line.

[00:41] **QA annotation (post-review, 2026-08-04):** Flagged. The
pre-apply review covered the amount only.

## Follow-up contact

Channel: Phone
Start time: 2026-08-02T09:14:00-07:00
Handle time: 1m 02s

[00:00] **Agent:** Calling back about yesterday's refuel.

[00:09] **Customer:** The charge posted twice.
"""


def _telecom_call_artifact(
    tmp_path: Path, recordings: list[str]
) -> TransformationArtifact:
    record = tmp_path / "case_007.md"
    record.write_text(_TELECOM_CALL_RECORD)
    recordings_dir = tmp_path / "recordings"
    recordings_dir.mkdir(exist_ok=True)
    for name in recordings:
        (recordings_dir / name).write_bytes(f"audio:{name}".encode())
    return TransformationArtifact(source_path=record)


def test_telecom_record_upgrades_every_phone_segment(tmp_path):
    transformation = get_transformation("support_transcripts")
    artifact = _telecom_call_artifact(
        tmp_path, ["case_007.m4a", "case_007_followup.m4a"]
    )
    kit_file = transformation.deliver(artifact, 5, parse_modality_profile("full"))

    stub = kit_file.content.decode()
    # Spoken turns from both segments are gone, continuations included.
    for spoken in (
        "this is Elise",
        "in twenty minutes",
        "Supervisor joining",
        "yesterday's refuel",
        "charge posted twice",
    ):
        assert spoken not in stub
    # Console notes, call events, and QA annotations never render to
    # audio — kept with their stamps, continuations included.
    assert "[00:15] **Console note:** Line 6640" in stub
    assert "Everyday 5 GB plan" in stub
    assert "[00:22] **Call event:**" in stub
    assert "pauses to listen" in stub
    assert "QA annotation (post-review, 2026-08-04)" in stub
    # Both segment headings and the follow-up header block survive.
    assert "## Transcript" in stub
    assert "## Follow-up contact" in stub
    assert "Start time: 2026-08-02T09:14:00-07:00" in stub
    assert "'_followup' suffix" in stub

    assert [c.relative_path for c in kit_file.companions] == [
        "uploaded_materials/case_005.m4a",
        "uploaded_materials/case_005_followup.m4a",
    ]
    assert kit_file.companions[0].content == b"audio:case_007.m4a"
    assert kit_file.companions[1].content == b"audio:case_007_followup.m4a"


def test_telecom_record_with_missing_segment_recording_stays_text(tmp_path):
    # All-or-nothing: stripping the follow-up's dialogue while shipping
    # only the primary recording would silently lose content.
    transformation = get_transformation("support_transcripts")
    artifact = _telecom_call_artifact(tmp_path, ["case_007.m4a"])
    kit_file = transformation.deliver(artifact, 5, parse_modality_profile("full"))
    assert b"this is Elise" in kit_file.content
    assert b"charge posted twice" in kit_file.content
    assert kit_file.companions == []


_TELECOM_CHAT_PRIMARY_RECORD = """# Case H

Channel: Live chat
QA status: Approved
Archive date: 2026-08-05
Chat opened: 2026-08-01T17:02:44-07:00

## Transcript

[2026-08-01 17:02:44 PT] **Customer:** hi, need 2 more gigs

[2026-08-01 17:03:02 PT] **Agent:** I can help with that.

## Follow-up contact

Channel: Phone
Start time: 2026-08-02T09:14:00-07:00
Handle time: 1m 02s

[00:00] **Agent:** Calling back about the refuel.

[00:09] **Customer:** it charged me twice
"""


def test_telecom_chat_segment_stays_text_next_to_upgraded_phone_segment(
    tmp_path,
):
    transformation = get_transformation("support_transcripts")
    record = tmp_path / "case_009.md"
    record.write_text(_TELECOM_CHAT_PRIMARY_RECORD)
    (tmp_path / "recordings").mkdir()
    (tmp_path / "recordings" / "case_009_followup.m4a").write_bytes(b"fu-bytes")
    artifact = TransformationArtifact(source_path=record)
    kit_file = transformation.deliver(artifact, 4, parse_modality_profile("full"))

    stub = kit_file.content.decode()
    # The chat segment never renders to audio — kept verbatim.
    assert "hi, need 2 more gigs" in stub
    assert "I can help with that." in stub
    # The phone follow-up's dialogue is in its recording.
    assert "Calling back about the refuel" not in stub
    assert "it charged me twice" not in stub
    assert [c.relative_path for c in kit_file.companions] == [
        "uploaded_materials/case_004_followup.m4a"
    ]
    assert kit_file.companions[0].content == b"fu-bytes"


# ---------------------------------------------------------------------------
# Companion pooling keeps pairs pairable
# ---------------------------------------------------------------------------


def test_pooled_renaming_keeps_companions_on_the_primary_stem():
    from tau2.hyper.sandbox.kit import _pool_uploaded_material_names

    primaries = []
    for index in range(2):
        companion = KitFile(
            relative_path=f"uploaded_materials/case_{index:03d}.m4a",
            content=f"audio-{index}".encode(),
        )
        primaries.append(
            KitFile(
                relative_path=f"uploaded_materials/case_{index:03d}.md",
                content=f"stub-{index}".encode(),
                artifact_kind="support_transcripts",
                companions=[companion],
            )
        )

    pooled = _pool_uploaded_material_names(primaries)
    for kit_file in pooled:
        stem = Path(kit_file.relative_path)
        assert stem.name.startswith("case_file_")
        [companion] = kit_file.companions
        assert companion.relative_path == str(stem.with_suffix(".m4a"))


def test_pooled_renaming_keeps_per_segment_companion_suffixes():
    # A telecom multi-call record ships one recording per phone segment;
    # the ``_followup`` stem tag must survive the generic renaming or the
    # two companions would collide at the primary's stem.
    from tau2.hyper.sandbox.kit import _pool_uploaded_material_names

    primary = KitFile(
        relative_path="uploaded_materials/case_007.md",
        content=b"stub",
        artifact_kind="support_transcripts",
        companions=[
            KitFile(
                relative_path="uploaded_materials/case_007.m4a",
                content=b"audio-primary",
            ),
            KitFile(
                relative_path="uploaded_materials/case_007_followup.m4a",
                content=b"audio-followup",
            ),
        ],
    )
    [pooled] = _pool_uploaded_material_names([primary])
    stem = Path(pooled.relative_path)
    assert stem.name == "case_file.md"
    assert [c.relative_path for c in pooled.companions] == [
        str(stem.with_suffix(".m4a")),
        str(stem.with_name(f"{stem.stem}_followup.m4a")),
    ]


# ---------------------------------------------------------------------------
# Committed banking rendition: real case, both arms
# ---------------------------------------------------------------------------

_CCREF_CASE_011 = (
    "tau2/hyper/sops/banking_knowledge/sections/credit_card_referrals/"
    "evidence_corpus_hard_001/support_cases/case_011.md"
)


def _deliver_committed_banking_case(source: Path) -> KitFile:
    transformation = get_transformation("support_transcripts")
    artifact = TransformationArtifact(source_path=source)
    return transformation.deliver(artifact, 11, parse_modality_profile("full"))


def test_committed_banking_case_selects_recording_and_strips_transcript():
    from tau2.utils.utils import DATA_DIR

    source = DATA_DIR / _CCREF_CASE_011
    kit_file = _deliver_committed_banking_case(source)

    recording = source.parent / "recordings" / "case_011.m4a"
    assert [c.relative_path for c in kit_file.companions] == [
        "uploaded_materials/case_011.m4a"
    ]
    assert kit_file.companions[0].content == recording.read_bytes()

    stub = kit_file.content.decode()
    # No spoken turn from the committed transcript survives in the stub —
    # sampled from the opening, middle, and closing of the call.
    spoken_samples = [
        "Rho card services, this is Hana.",
        "Hi Hana. Easy one for you. I need a ref",
        "It's not new, it's just invisible until",
        "No, that's it. You saved my neighbor re",
    ]
    for sample in spoken_samples:
        assert sample not in stub
    # Console entries and the case header stay: they are not in the audio.
    assert "Case ID: CRF-2511-0355" in stub
    assert "Identity verified, two factors matched" in stub
    assert "Case closed" in stub
    assert "companion call-recording" in stub


def test_committed_banking_case_upgrade_is_arm_symmetric(tmp_path):
    # A client arm delivers a *fork* of the case from the overlay tree with
    # its own sibling recordings/; the lookup is source-relative, so both
    # arms take the identical upgrade path.
    from tau2.utils.utils import DATA_DIR

    source = DATA_DIR / _CCREF_CASE_011
    client_dir = tmp_path / "client_overlay" / "support_cases"
    (client_dir / "recordings").mkdir(parents=True)
    client_case = client_dir / "case_011.md"
    # The fork edits a name that occurs only in spoken turns, so the two
    # arms' stubs must come out byte-identical after stripping.
    client_case.write_text(source.read_text().replace("Hana", "Mara"))
    (client_dir / "recordings" / "case_011.m4a").write_bytes(b"client-take")

    base = _deliver_committed_banking_case(source)
    client = _deliver_committed_banking_case(client_case)

    assert client.companions[0].content == b"client-take"
    assert base.companions[0].content != b"client-take"
    # The stubs strip identically: same non-spoken skeleton on both arms.
    assert client.content == base.content


# ---------------------------------------------------------------------------
# End-to-end kit materialization
# ---------------------------------------------------------------------------


def _committed_recording_count() -> int:
    """Recordings committed for the airline_plus sections bundles.

    The audio tier is data-dependent by design: kits upgrade phone-call
    records only where a committed ``recordings/<case>.m4a`` rendition
    exists (PR #682 ships them), and fall back to transcripts elsewhere.
    """
    from tau2.utils.utils import DATA_DIR

    sections = DATA_DIR / "tau2" / "hyper" / "sops" / "airline_plus" / "sections"
    return sum(1 for _ in sections.rglob("recordings/*.m4a"))


@pytest.mark.parametrize("profile", [None, "text", "full"])
def test_evidence_bundle_kit_materializes_per_profile(tmp_path, profile):
    from tau2.hyper.sandbox.kit import build_kit
    from tau2.hyper.task_loader import load_hyper_tau_task

    task = load_hyper_tau_task(
        "001_airline_plus_construction_core_evidence"
        "_all_defects_live_experiment_performance_medium"
    )
    kit = build_kit(task, tmp_path / "kit", modality_profile=profile)

    materials = list((kit / "uploaded_materials").iterdir())
    by_suffix = {
        suffix: sum(1 for path in materials if path.suffix == f".{suffix}")
        for suffix in ("png", "txt", "m4a")
    }
    if profile == "text":
        expected = {"png": 0, "txt": 53, "m4a": 0}
    else:
        recordings = _committed_recording_count() if profile == "full" else 0
        expected = {"png": 53, "txt": 0, "m4a": recordings}
    assert by_suffix == expected

    report = json.loads(
        (kit.parent / f"{kit.name}.transformation_report.json").read_text()
    )
    assert report["modality_profile"] == str(
        parse_modality_profile(profile) if profile else DEFAULT_KIT_MODALITY_PROFILE
    )

    # Every recording ships as a companion of its stub: stems must pair.
    for recording in (kit / "uploaded_materials").glob("*.m4a"):
        stub = recording.with_suffix(".md")
        assert stub.exists()
        assert "companion call-recording" in stub.read_text()
