"""Gates for the airline_plus image and document artifacts.

The image-bearing artifacts under data/tau2/hyper/sops/airline_plus/ were
originally ported from the canonical airline artifacts; since the 2026-08-04
standalone cutover the tree is edited directly, and the porter tooling and
the frozen canonical trees are not part of this release. The forbidden-token
list the porter used to supply is pinned in tests/plus_support/airline_plus.py.
These tests enforce integrity of the committed tree: every PNG in the render
manifest exists at its pinned dimensions, render provenance pins match,
call-audio renditions are complete, schema artifact references and declared
transformations resolve, no canonical token survives in the text artifacts,
ported prose and record arithmetic keep their identity invariants, and the
cancellation workbook has the expected document structure.
"""

import json
import re
import struct
import zipfile
from datetime import date
from pathlib import Path

import yaml
from plus_support import airline_plus as expectations
from plus_support.leakage import scan_leakage

REPO_ROOT = Path(__file__).resolve().parents[2]
DST_ROOT = REPO_ROOT / "data" / "tau2" / "hyper" / "sops" / "airline_plus"
BOOKING = DST_ROOT / "sections" / "booking_flight"
COMPENSATION = DST_ROOT / "sections" / "compensation_certificates"
CANCELLING = DST_ROOT / "sections" / "cancelling_reservation"
MODIFYING = DST_ROOT / "sections" / "modifying_reservation"
COMPENSATION_SITE = COMPENSATION / "website_screenshot_001_full_site" / "screenshots"

# (path, expected width, expected height or None when content-dependent)
EXPECTED_RENDERS = [
    (BOOKING / "process_flowchart_001" / "booking_process_map.png", 1760, 1180),
    (
        BOOKING / "website_screenshot_001" / "travel_insurance_checkout.png",
        1280,
        1817,
    ),
    (
        BOOKING
        / "website_screenshot_002"
        / "passenger_selector_maximum_with_images.png",
        1280,
        1004,
    ),
] + [
    (path, 1440, None)
    for path in sorted((BOOKING / "faq_screenshots_001" / "screenshots").glob("*.png"))
]

REMAINING_FIXED_RENDERS = [
    (
        COMPENSATION
        / "process_flowchart_002_handdrawn"
        / "delayed_flight_certificate_workshop_map.png",
        1536,
        1024,
    ),
    (
        CANCELLING
        / "website_screenshot_001"
        / "cancellation_confirmation_email_v1_ambiguous.png",
        1280,
        1900,
    ),
    (
        CANCELLING
        / "website_screenshot_001"
        / "cancellation_confirmation_email_v2_clarified.png",
        1280,
        1900,
    ),
    (
        CANCELLING / "website_screenshot_002" / "business_cancellation_eligibility.png",
        1440,
        1220,
    ),
    (
        MODIFYING
        / "website_screenshot_002"
        / "travel_certificate_unavailable_with_images.png",
        1280,
        915,
    ),
    (
        MODIFYING
        / "website_screenshot_003"
        / "gift_card_insufficient_balance_with_images.png",
        1280,
        915,
    ),
]


def png_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:33]
    return struct.unpack(">II", header[16:24])


def test_renders_present_with_expected_dimensions():
    """Booking renders remain present at their expected dimensions."""
    faq_pngs = [p for p, _, h in EXPECTED_RENDERS if h is None]
    assert len(faq_pngs) == 10, "expected 10 rendered FAQ screenshots"
    for path, width, height in EXPECTED_RENDERS:
        assert path.exists(), f"missing render: {path}"
        got_w, got_h = png_dimensions(path)
        assert got_w == width, f"{path.name}: width {got_w} != {width}"
        if height is not None:
            assert got_h == height, f"{path.name}: height {got_h} != {height}"


def test_remaining_renders_match_canonical_dimensions():
    """The hand-drawn, cancellation, and modification PNGs keep exact sizes."""
    for path, width, height in REMAINING_FIXED_RENDERS:
        assert path.exists(), f"missing render: {path}"
        assert png_dimensions(path) == (width, height), path.name


def _iter_artifact_paths(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if (
                key.endswith("path")
                and isinstance(child, str)
                and child.startswith("tau2/")
            ):
                yield child
            yield from _iter_artifact_paths(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_artifact_paths(child)


def test_all_schema_artifact_references_exist():
    """Every artifact path exposed by every airline_plus transformation resolves."""
    schema_paths = sorted((DST_ROOT / "sections").glob("*/schema.json"))
    assert len(schema_paths) == 7
    references = []
    for schema_path in schema_paths:
        schema = json.loads(schema_path.read_text())
        for transformation in schema.get("transformations", []):
            references.extend(_iter_artifact_paths(transformation))
        for bundle in schema.get("transformation_bundles", []):
            references.extend(_iter_artifact_paths(bundle))
    assert references
    for reference in references:
        assert (REPO_ROOT / "data" / reference).exists(), reference


def test_render_provenance_pins_match():
    """Every render source and output hashes to the committed provenance pin.

    Renders run out of band (headless Chrome / ImageGen / LibreOffice), so
    CI cannot re-render and compare. The pin proves staleness instead: a
    source edited without re-rendering + re-pinning, an output swapped
    without re-pinning, or a new/removed file dodging a pinned glob all
    break here. It cannot prove causality — that the committed pixels came
    from the committed sources rests on the authoring-side re-render
    workflow plus review of pin-only diffs.
    """
    import fnmatch
    import hashlib

    pin = json.loads((DST_ROOT / "render_provenance.json").read_text())
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
            current = {str(p.relative_to(DST_ROOT)) for p in DST_ROOT.glob(pattern)}
            pinned = {rel for rel in group[files_key] if fnmatch.fnmatch(rel, pattern)}
            if current != pinned:
                problems.append(
                    f"{group['id']}: {glob_key} drift — unpinned {sorted(current - pinned)},"
                    f" missing {sorted(pinned - current)}"
                )
        for files_key in ("sources", "outputs"):
            for rel, pinned_sha in group[files_key].items():
                path = DST_ROOT / rel
                if not path.exists():
                    problems.append(f"{group['id']}: {rel} missing")
                    continue
                if hashlib.sha256(path.read_bytes()).hexdigest() != pinned_sha:
                    problems.append(
                        f"{group['id']}: {rel} hash drift — if a source changed,"
                        " re-render its outputs and update the"
                        " pinned hashes in render_provenance.json"
                    )
    assert not problems, "\n".join(problems)


def test_call_audio_renditions_complete():
    """Every phone-call training record has a committed audio rendition
    (recordings/<case>.m4a) and every rendition has a phone-call source.

    All-or-nothing per tree: if only some phone-call cases carried audio,
    the rendition set itself would mark which records matter. Chat-channel
    cases never render, and their renditions are as much drift as missing
    ones. Byte-level integrity is the provenance pin's job; this gate owns
    the mapping.
    """
    phone_re = re.compile(r"^Channel:\s*phone call\s*$", re.MULTILINE)
    case_paths = [
        path
        for path in sorted(DST_ROOT.rglob("case_*.md"))
        if ".claude" not in path.parts
    ]
    assert case_paths
    problems = []
    for case_path in case_paths:
        rendition = case_path.parent / "recordings" / (case_path.stem + ".m4a")
        if phone_re.search(case_path.read_text()):
            if not rendition.exists():
                problems.append(f"missing rendition: {rendition.relative_to(DST_ROOT)}")
        elif rendition.exists():
            problems.append(
                f"rendition for non-phone-call case: {rendition.relative_to(DST_ROOT)}"
            )
    for m4a in sorted(DST_ROOT.rglob("recordings/*.m4a")):
        if not (m4a.parent.parent / (m4a.stem + ".md")).exists():
            problems.append(f"orphaned rendition: {m4a.relative_to(DST_ROOT)}")
    assert not problems, "\n".join(problems)


def test_all_declared_transformations_resolve():
    """Every transformation spec resolved from every committed schema
    discovers its artifacts, and every discovered source file exists.

    Stronger than the textual reference walk above: this exercises the
    transformation layer itself (including legacy-adapter fallbacks), which
    is what kit compilation consumes.
    """
    from tau2.hyper.transformations import (
        get_transformation,
        resolve_section_transformations,
    )

    schema_paths = sorted((DST_ROOT / "sections").glob("*/schema.json"))
    assert schema_paths
    resolved_any = False
    for schema_path in schema_paths:
        schema = json.loads(schema_path.read_text())
        for spec in resolve_section_transformations(schema):
            transformation = get_transformation(spec["representation"])
            # Must not raise; explicit_rules legitimately discovers no
            # artifact files (its coverage is the section prose).
            artifacts = transformation.discover_artifacts(schema, schema_path, spec)
            for artifact in artifacts:
                assert artifact.source_path.exists(), (
                    f"{schema_path.parent.name}: {artifact.source_path}"
                )
            resolved_any = True
    assert resolved_any


def test_no_canonical_tokens_survive():
    """The committed artifact tree carries no forbidden canonical tokens.

    The port ran this scan once, at port time; after the standalone cutover
    the tree is edited directly, so the scan must hold on the committed files
    themselves (the 2026-08 audit found ``hatairlines.slack.com`` permalinks
    sitting committed with no gate). The forbidden-token list is pinned in
    tests/plus_support/airline_plus.py. Mirrors the retail suite's
    ``test_no_canonical_values_survive``.
    """
    text_files = [
        path
        for path in sorted(DST_ROOT.rglob("*"))
        if path.is_file()
        and path.suffix
        in {".md", ".html", ".txt", ".json", ".py", ".eml", ".cjs", ".mjs", ".css"}
        and "__pycache__" not in path.parts
        # The provenance pin is sha256 hex + tree-relative paths; hex digit
        # runs collide with numeric token bans.
        and path.name != "render_provenance.json"
    ]
    assert text_files
    assert expectations.ARTIFACT_FORBIDDEN_PATTERNS
    scan_leakage(text_files, list(expectations.ARTIFACT_FORBIDDEN_PATTERNS))


def test_context_sensitive_record_arithmetic_and_identifiers():
    """Reviewed stories retain coherent arithmetic, caps, and spoken identifiers."""
    booking_case = (BOOKING / "training_records" / "case_005.md").read_text()
    assert "Total cost: $715." in booking_case
    assert "Baggage fees: $65" in booking_case
    assert "$560 + $65 + $90 = $715" in booking_case
    assert "$200 travel certificate, $100 gift card, and $415" in booking_case

    booking_hybrid = BOOKING / "bundles" / "booking_visual_hybrid"
    cap_case = (booking_hybrid / "training_records" / "case_036.md").read_text()
    assert "So: four passengers." in cap_case
    assert "Four seats at $140 is $560" in cap_case
    assert "Do you want to book the four right now?" in cap_case
    assert "Nothing today is booked or held" in cap_case

    compensation_hybrid = (
        COMPENSATION / "bundles" / "compensation_website_hybrid" / "training_records"
    )
    linked_case = (compensation_hybrid / "case_028.md").read_text()
    assert "five of us across two linked reservations" in linked_case
    assert "second booking" in linked_case

    baggage_case = (compensation_hybrid / "case_017.md").read_text()
    for expected in [
        "final sequence as 01291",
        "701291",
        "ends 701219, not 701291",
        "JFKMER701219",
        "search the file as 701219",
    ]:
        assert expected in baggage_case
    for stale in ["JFKHAT374219", "374291", "374219"]:
        assert stale not in baggage_case

    modification_case = (
        MODIFYING
        / "bundles"
        / "modification_visual_hybrid"
        / "training_records"
        / "case_003.md"
    ).read_text()
    assert "return MER958 March 22" in modification_case
    assert "Meridian... nine five eight" in modification_case


def test_name_derived_accounts_and_policy_arithmetic_are_synchronized():
    """Remapped names and policy values agree with their surrounding records."""
    root_compensation = COMPENSATION / "training_records"
    cancelled = (root_compensation / "case_002.md").read_text()
    delayed = (root_compensation / "case_003.md").read_text()
    assert "one $510 travel certificate" in cancelled
    assert "One aggregate travel certificate issued for $510" in cancelled
    assert "samira_chung_48" in delayed
    assert "samira_lee_48" not in delayed
    assert "one $170 travel certificate" in delayed
    assert "One aggregate travel certificate issued for $170" in delayed

    hybrid_records = (
        COMPENSATION / "bundles" / "compensation_website_hybrid" / "training_records"
    )
    assert "owen.choi.31" in (hybrid_records / "case_006.md").read_text()
    assert "nora_mehta_91" in (hybrid_records / "case_009.md").read_text()

    modification = (MODIFYING / "training_records" / "case_005.md").read_text()
    assert "two more checked bags would cost $130 total" in modification
    assert "each additional checked bag is $65" in modification


def test_visible_initials_and_handdrawn_grammar_match_remapped_people():
    """Rendered-source initials and narration reflect the reviewed identities."""
    insurance = (
        BOOKING / "website_screenshot_001" / "travel_insurance_checkout.html"
    ).read_text()
    assert '<span class="avatar">HK</span>' in insurance
    assert '<span class="avatar">WK</span>' in insurance
    assert '<span class="avatar">DM</span>' not in insurance
    assert '<span class="avatar">CM</span>' not in insurance

    cancellation = (
        CANCELLING / "website_screenshot_002" / "business_cancellation_eligibility.html"
    ).read_text()
    for initials in ["WE", "AW", "AB"]:
        assert f'<span class="traveler-avatar">{initials}</span>' in cancellation
    for stale in ["CJ", "RS", "FM"]:
        assert f'<span class="traveler-avatar">{stale}</span>' not in cancellation

    full_site_pages = COMPENSATION_SITE.parent / "pages"
    traveler_details = (full_site_pages / "005_traveler_details.html").read_text()
    confirmation = (full_site_pages / "010_booking_confirmation.html").read_text()
    assert "Xiu Villanueva" in traveler_details
    assert "xiu.villanueva6648@example.com" in traveler_details
    assert "xiu.villanueva6648@example.com" in confirmation
    assert "xiu.villanueva@example" not in traveler_details + confirmation
    assert "mei.hernandez@example.com" not in traveler_details + confirmation

    handdrawn = (
        COMPENSATION
        / "process_flowchart_002_handdrawn"
        / "delayed_flight_certificate_workshop_map.txt"
    ).read_text()
    handdrawn_words = " ".join(handdrawn.split())
    assert "an $85 travel certificate" in handdrawn_words
    assert "a $85 travel certificate" not in handdrawn_words


def test_cancellation_workbook_exports_are_valid():
    """The regenerated PPTX contains 11 slides and has a nonempty PDF export."""
    workbook_dir = CANCELLING / "process_presentation_001"
    pptx_path = workbook_dir / "cancellation_operations_workbook.pptx"
    pdf_path = workbook_dir / "cancellation_operations_workbook.pdf"
    assert zipfile.is_zipfile(pptx_path)
    with zipfile.ZipFile(pptx_path) as archive:
        slides = [
            name
            for name in archive.namelist()
            if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
        ]
    assert len(slides) == 11
    assert pdf_path.read_bytes().startswith(b"%PDF-")


def test_grounded_values_rederive_from_the_plus_db():
    """Db-grounded showcase values equal a fresh derivation from the plus db.

    The port remaps the identity layer with the seeded bijection; this gate
    proves the transactional layer moved with it: every dollar figure,
    payment-instrument digit run, and passenger DOB shown for a db-backed
    reservation re-derives from data/tau2/domains/airline_plus/db.json, and
    grounding provenance never cites the canonical db.
    """
    plus_db = json.loads(
        (REPO_ROOT / "data/tau2/domains/airline_plus/db.json").read_text()
    )
    spec = yaml.safe_load(
        (REPO_ROOT / "data/tau2/domains/airline_plus/delta_spec.yaml").read_text()
    )
    ins_new = spec["fees"]["insurance_fee_per_passenger"]["new"]
    reservations = plus_db["reservations"]

    def long_date(iso: str) -> str:
        d = date.fromisoformat(iso)
        return f"{d.strftime('%B')} {d.day}, {d.year}"

    # Provenance: no ported artifact grounds against the canonical db.
    for path in sorted(DST_ROOT.rglob("*.json")):
        assert "data/tau2/domains/airline/db.json" not in path.read_text(), path

    # EFDWA0 — the checkout itemizes the reservation's leg prices plus
    # insurance for its passengers. (Since the 2026-08 payment-history
    # rebuild the db's recorded payment equals this same component total.)
    efdwa0 = reservations["EFDWA0"]
    pax = len(efdwa0["passengers"])
    airfare = sum(leg["price"] for leg in efdwa0["flights"]) * pax
    total = airfare + ins_new * pax
    checkout = (
        BOOKING / "website_screenshot_001" / "travel_insurance_checkout.html"
    ).read_text()
    assert f">${airfare}.00<" in checkout
    assert f">${total}.00<" in checkout
    assert "$564" not in checkout
    for passenger in efdwa0["passengers"]:
        assert f"Date of birth · {long_date(passenger['dob'])}" in checkout
    booking_manifest = json.loads(
        (BOOKING / "website_screenshot_001" / "eval_manifest.json").read_text()
    )
    visible = booking_manifest["grounded_distractors"]["visible_values"]
    assert f"${airfare} airfare" in visible
    assert f"${total} total" in visible

    # ZSPX3D — the cancellation refund returns exactly the recorded payment.
    refund = reservations["ZSPX3D"]["payment_history"][0]["amount"]
    for stem in (
        "cancellation_confirmation_email_v1_ambiguous",
        "cancellation_confirmation_email_v2_clarified",
    ):
        email = (CANCELLING / "website_screenshot_001" / f"{stem}.html").read_text()
        assert f">${refund:,}<" in email
        assert "$1,574" not in email

    # O6HO62 — the cabin-change charge re-derives from the paid economy legs
    # and the current business fares for the same flights and dates; the
    # certificate and gift card are the owner's remapped payment methods.
    o6 = reservations["O6HO62"]
    o6_pax = len(o6["passengers"])
    econ_air = sum(leg["price"] for leg in o6["flights"]) * o6_pax
    bus_air = (
        sum(
            plus_db["flights"][leg["flight_number"]]["dates"][leg["date"]]["prices"][
                "business"
            ]
            for leg in o6["flights"]
        )
        * o6_pax
    )
    charge = bus_air - econ_air
    methods = plus_db["users"][o6["user_id"]]["payment_methods"].values()
    cert = next(m for m in methods if m["source"] == "certificate")
    gift = next(m for m in methods if m["source"] == "gift_card")
    shortfall = charge - int(gift["amount"])

    ws2 = (
        MODIFYING / "website_screenshot_002" / "travel_certificate_unavailable.html"
    ).read_text()
    assert ws2.count(f"${charge:,}.00") == 2
    assert f"Travel certificate ending in {cert['id'][-4:]}" in ws2
    assert f"${int(cert['amount'])}.00 balance" in ws2
    ws3 = (
        MODIFYING / "website_screenshot_003" / "gift_card_insufficient_balance.html"
    ).read_text()
    assert ws3.count(f"${charge:,}.00") == 4
    assert f"gift card ending in {gift['id'][-4:]}" in ws3
    assert f"${int(gift['amount'])}.00 balance" in ws3
    assert f"${shortfall:,}.00" in ws3
    assert "$2,532" not in ws2 + ws3

    for rel, label in [
        ("website_screenshot_002", "modification charge"),
        ("website_screenshot_003", "cabin-change charge"),
    ]:
        manifest = json.loads((MODIFYING / rel / "eval_manifest.json").read_text())
        derived = {
            entry["value"]: entry["derivation"]
            for entry in manifest["grounded_distractors"]["derived_values"]
        }
        derivation = derived[f"${charge:,} {label}"]
        assert f"= ${econ_air:,}." in derivation
        assert f"= ${bus_air:,}." in derivation
        assert f"= ${charge:,}." in derivation
    ws3_manifest = json.loads(
        (MODIFYING / "website_screenshot_003" / "eval_manifest.json").read_text()
    )
    shortfall_entries = {
        entry["value"]: entry["derivation"]
        for entry in ws3_manifest["grounded_distractors"]["derived_values"]
    }
    assert (
        shortfall_entries[f"${shortfall:,} additional balance needed"]
        == f"${charge:,} cabin-change charge - ${int(gift['amount'])} gift card"
        f" balance = ${shortfall:,}."
    )
    ws2_manifest = json.loads(
        (MODIFYING / "website_screenshot_002" / "eval_manifest.json").read_text()
    )
    assert (
        f"Saved travel certificate ending in {cert['id'][-4:]} with a"
        f" ${int(cert['amount'])} balance"
        in ws2_manifest["grounded_distractors"]["visible_values"]
    )
    assert (
        f"Saved gift card ending in {gift['id'][-4:]} with a"
        f" ${int(gift['amount'])} balance"
        in ws3_manifest["grounded_distractors"]["visible_values"]
    )
