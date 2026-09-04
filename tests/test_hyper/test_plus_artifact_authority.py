"""Regression gates for genuine authority contradictions in Plus artifacts."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOPS_ROOT = REPO_ROOT / "data" / "tau2" / "hyper" / "sops"
AIRLINE = SOPS_ROOT / "airline_plus"
RETAIL = SOPS_ROOT / "retail_plus"


def _json(path: Path) -> dict:
    return json.loads(path.read_text())


def _facts(path: Path) -> dict[str, str]:
    return {fact["id"]: fact["statement"] for fact in _json(path)["facts"]}


def test_airline_sources_align_booking_and_cabin_contracts() -> None:
    booking = _facts(AIRLINE / "sections/booking_flight/schema.json")
    managing = _facts(AIRLINE / "sections/manage_existing_reservation/schema.json")

    sequence = booking["booking_step_sequence"]
    assert "prepare saved payment methods" in sequence
    assert "confirm before the reservation write processes payment" in sequence
    assert (
        "current availability and pricing"
        in managing["cabin_change_reprice_all_segments_current_new_cabin_rate"]
    )

    # These remain intentionally unexpanded until their contracts are decided.
    assert (
        managing["insurance_cannot_be_added_after_booking"]
        == "Travel insurance cannot be added after the initial booking."
    )
    assert (
        "No exact denial wording is required"
        not in managing["no_other_compensation_reasons"]
    )


def test_airline_examples_do_not_invent_actions_timelines_or_certificate_shapes() -> (
    None
):
    modification_records = (
        AIRLINE
        / "sections/modifying_reservation/bundles/modification_visual_hybrid/training_records"
    )
    receipt_case = (modification_records / "case_016.md").read_text()
    refund_case = (modification_records / "case_019.md").read_text()
    assert "no action that generates or sends an itemized receipt" in receipt_case
    assert "Receipt generated" not in receipt_case
    assert "handful of business days" not in refund_case
    assert "card issuer controls" not in refund_case

    root_records = AIRLINE / "sections/compensation_certificates/training_records"
    cancelled = (root_records / "case_002.md").read_text()
    delayed = (root_records / "case_003.md").read_text()
    assert "one $510 travel certificate" in cancelled.lower()
    assert "three $170 travel certificates" not in cancelled.lower()
    assert "one $170 travel certificate" in delayed.lower()
    assert "two $85 travel certificates" not in delayed.lower()

    hybrid_records = (
        AIRLINE
        / "sections/compensation_certificates/bundles/compensation_website_hybrid/training_records"
    )
    aggregate_cases = "\n".join(
        (hybrid_records / name).read_text() for name in ("case_024.md", "case_027.md")
    )
    assert "One aggregate $510 travel certificate" in aggregate_cases
    assert "One $170 travel certificate issued" in aggregate_cases
    assert "one for each of you" not in aggregate_cases.lower()


def test_airline_transfer_contract_has_no_second_consent_gate() -> None:
    rules = {rule["id"]: rule for rule in _json(AIRLINE / "global_rules.json")["rules"]}
    condition = rules["transfer_out_of_scope_or_on_request"]["statement"]
    notice = rules["exact_transfer_notice"]["statement"]
    assert "does not ask a separate consent question" in condition
    assert "first initiates the transfer" in notice


def test_retail_qa_calibration_cards_carry_dated_rescope() -> None:
    """The six zero-fact conduct cards are scoped by a dated in-world ruling.

    Authority must be decidable by reading each card's corner tag (the same
    mechanism as the RETIRED and WHOLESALE fences) — never by an enumerated
    roster or a builder-facing label.
    """
    regular_dir = RETAIL / "sections/manage_pending_order/process_presentation_001"
    pack = _json(
        RETAIL / "hard_bundle_001/manage_pending_order_transformation_pack.json"
    )
    (deck_entry,) = [
        transformation
        for transformation in pack["transformations"]
        if transformation["id"] == "manage_pending_order_hard_qa_deck_001"
    ]
    (deck_artifact,) = deck_entry["artifacts"]
    # The hard bundle serves the repaired section deck, not a fork of it.
    assert deck_artifact["path"].endswith(
        "process_presentation_001/pending_order_qa_calibration_deck.pdf"
    )
    assert deck_artifact["text_source_path"].endswith(
        "process_presentation_001/pending_order_qa_calibration_deck.txt"
    )
    delivered_texts = (
        (regular_dir / "pending_order_qa_calibration_deck.html").read_text(),
        (regular_dir / "pending_order_qa_calibration_deck.txt").read_text(),
    )
    card_ids = ("G-1", "C-8", "G-4", "A-6", "G-7", "I-9")
    for text in delivered_texts:
        flat = " ".join(text.split())
        assert flat.upper().count("CALIBRATION-ONLY 6.9.26") >= 6
        assert "6.9.26 quarterly card audit" in flat
        for card_id in card_ids:
            assert f"RULE {card_id}" in flat
            assert f"EXERCISE {card_id}" not in flat
        upper = flat.upper()
        assert "NON-POLICY" not in upper
        assert "NOT AN OPERATING RULE" not in upper
        assert "MUST NOT BE COPIED INTO AN AGENT POLICY" not in upper
        # No page may enumerate the operating roster; the reader must visit
        # each card and read its tag.
        assert "C-2, C-5, A-3, and I-6" not in flat


def test_retail_transfer_contract_does_not_add_a_second_consent_gate() -> None:
    rules = {rule["id"]: rule for rule in _json(RETAIL / "global_rules.json")["rules"]}
    conditions = rules["transfer_on_request_escalation_or_uncertainty"]["statement"]
    notice = rules["exact_transfer_notice"]["statement"]
    assert "does not require a second consent question" in conditions
    assert "first initiates the transfer" in notice
    assert "standalone sentence" in notice


def test_airline_declined_requests_are_not_transfer_conditions() -> None:
    rules = {rule["id"]: rule for rule in _json(AIRLINE / "global_rules.json")["rules"]}
    condition = rules["transfer_out_of_scope_or_on_request"]["statement"]
    assert "not by itself a transfer condition" in condition

    sop = (SOPS_ROOT / "airline_plus_sop.md").read_text()
    assert "A request this handbook prohibits is not by itself a" in sop

    hybrid_records = (
        AIRLINE
        / "sections/compensation_certificates/bundles/compensation_website_hybrid/training_records"
    )
    declined_and_closed = (hybrid_records / "case_006.md").read_text()
    assert "No travel certificate issued." in declined_and_closed
    assert "TRANSFERRED TO A HUMAN AGENT" not in declined_and_closed

    escalated_after_decline = (hybrid_records / "case_025.md").read_text()
    assert "unable to assist" in escalated_after_decline
    assert "Customer requested escalation to a person" in escalated_after_decline
    assert (
        "YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON."
        in escalated_after_decline
    )


def test_retail_qa_deck_txt_cover_matches_render() -> None:
    path = (
        RETAIL
        / "sections/manage_pending_order/process_presentation_001/pending_order_qa_calibration_deck.txt"
    )
    flat = " ".join(path.read_text().split())
    assert (
        "nothing leaves the room. Where a card and your memory disagree, "
        "the card — status tag included — wins" in flat
    )
    assert "room. Where a only" not in flat
