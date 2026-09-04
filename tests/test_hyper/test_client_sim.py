"""Tests for the Client-simulator tooling (deterministic parts only)."""

import json
import re

import pytest

from tau2.hyper.client_sim.instructions import (
    list_section_ids,
    load_section_facts,
    render_client_instructions,
    resolve_task_client_instructions,
)
from tau2.utils.utils import DATA_DIR


@pytest.fixture
def sections_fixture(tmp_path):
    """A minimal domain data dir with two section schemas."""
    domain_dir = tmp_path / "tau2/hyper/sops/mockdomain/sections"
    schemas = {
        "widget_returns": {
            "id": "mock_widget_returns_schema",
            "facts": [
                {
                    "id": "return_window",
                    "category": "eligibility",
                    "statement": "Widgets can be returned within 30 days.",
                },
                {
                    "id": "refund_destination",
                    "category": "refunds",
                    "statement": "Refunds go back to the original payment method.",
                },
            ],
        },
        "widget_exchanges": {
            "id": "mock_widget_exchanges_schema",
            "facts": [
                {
                    "id": "exchange_once",
                    "category": "eligibility",
                    "statement": "Each order can be exchanged at most once.",
                },
                # Malformed entries must be skipped, not crash the loader.
                {"category": "eligibility"},
            ],
        },
    }
    for section_id, schema in schemas.items():
        section_dir = domain_dir / section_id
        section_dir.mkdir(parents=True)
        (section_dir / "schema.json").write_text(json.dumps(schema))
    return tmp_path


def test_list_section_ids(sections_fixture):
    assert list_section_ids("mockdomain", sections_fixture) == [
        "widget_exchanges",
        "widget_returns",
    ]


def test_load_section_facts_skips_malformed_entries(sections_fixture):
    section = load_section_facts("mockdomain", "widget_exchanges", sections_fixture)
    assert [f.id for f in section.facts] == ["exchange_once"]


def test_render_default_is_pure_point_back(sections_fixture):
    """With no held or confirmable facts the prompt embeds no policy at all."""
    rendered = render_client_instructions(
        "mockdomain", ["widget_returns", "widget_exchanges"], sections_fixture
    )
    assert rendered.fact_count == 3
    assert rendered.held_fact_count == 0
    assert rendered.confirmable_fact_count == 0
    for statement in (
        "Widgets can be returned within 30 days.",
        "Refunds go back to the original payment method.",
        "Each order can be exchanged at most once.",
    ):
        assert statement not in rendered.prompt
    assert "What only you know" not in rendered.prompt
    assert "Questions you can settle" not in rendered.prompt
    # The behavioral contract must survive template edits.
    assert "Never recite, list, or summarize policy rules" in rendered.prompt
    assert "you point back to the records" in rendered.prompt


def test_render_with_client_held_adds_held_tier_only(sections_fixture):
    held = {"widget_returns": ["refund_destination"]}
    rendered = render_client_instructions(
        "mockdomain", ["widget_returns", "widget_exchanges"], sections_fixture, held
    )
    assert rendered.fact_count == 3
    assert rendered.held_fact_count == 1
    prompt = rendered.prompt
    assert "<what_only_you_know>" in prompt
    # Only the held fact is embedded; everything else stays out of the prompt.
    statement = "Refunds go back to the original payment method."
    assert prompt.count(statement) == 1
    assert prompt.index(statement) > prompt.index("<what_only_you_know>")
    assert "Widgets can be returned within 30 days." not in prompt
    assert '"check the records" is not an acceptable answer' in prompt
    assert "Nearly all the rules" in prompt
    # The kickoff opening stays silent about the gaps: nothing in the
    # prompt tells the developer that undocumented points exist.
    assert "ask you directly" not in prompt


def test_render_with_confirmable_adds_settle_block(sections_fixture):
    rendered = render_client_instructions(
        "mockdomain",
        ["widget_returns", "widget_exchanges"],
        sections_fixture,
        client_held={"widget_returns": ["refund_destination"]},
        client_confirmable={"widget_returns": ["return_window"]},
    )
    assert rendered.held_fact_count == 1
    assert rendered.confirmable_fact_count == 1
    prompt = rendered.prompt
    assert "<questions_you_can_settle>" in prompt
    statement = "Widgets can be returned within 30 days."
    assert prompt.count(statement) == 1
    assert prompt.index(statement) > prompt.index("<questions_you_can_settle>")
    # Adjudication may pick among the readings the developer offered...
    assert "name the one that matches" in prompt
    # ...but never supplies a version the developer did not bring.
    assert "Never volunteer a version they did not offer" in prompt
    assert "without supplying the correct version" in prompt
    # The unlisted fact stays out of the prompt entirely.
    assert "Each order can be exchanged at most once." not in prompt


def test_behavior_rules_reference_real_prompt_sections(sections_fixture):
    """Every <tag> the rules cite must be a section the prompt actually opens.

    The rules point the Client at its knowledge lists by tag name
    ("The points in <what_only_you_know>..."), so renaming a section tag
    without updating the prose leaves the rules citing nothing.
    """
    rendered = render_client_instructions(
        "mockdomain",
        ["widget_returns", "widget_exchanges"],
        sections_fixture,
        client_held={"widget_returns": ["refund_destination"]},
        client_confirmable={"widget_returns": ["return_window"]},
    )
    prompt = rendered.prompt
    rules = re.search(r"<how_you_behave>\n(.*?)\n</how_you_behave>", prompt, re.DOTALL)
    assert rules, "the prompt no longer has a <how_you_behave> section"
    cited = set(re.findall(r"<([a-z_]+)>", rules.group(1)))
    assert cited, "the rules cite no sections at all — did the tags change?"
    for tag in sorted(cited):
        assert f"<{tag}>" in prompt.replace(rules.group(0), ""), (
            f"the rules cite <{tag}>, which the prompt never opens"
        )
        assert f"</{tag}>" in prompt, f"<{tag}> is opened but never closed"


def test_render_without_held_facts_is_unchanged(sections_fixture):
    base = render_client_instructions(
        "mockdomain", ["widget_returns"], sections_fixture
    )
    explicit_empty = render_client_instructions(
        "mockdomain", ["widget_returns"], sections_fixture, {}, {}
    )
    assert base.prompt == explicit_empty.prompt
    assert "What only you know" not in base.prompt
    assert "The rules the agent must follow are all in those records." in base.prompt


def test_render_rejects_unknown_and_overlapping_fact_lists(sections_fixture):
    with pytest.raises(ValueError, match="not being rendered"):
        render_client_instructions(
            "mockdomain",
            ["widget_returns"],
            sections_fixture,
            {"widget_exchanges": ["exchange_once"]},
        )
    with pytest.raises(ValueError, match="unknown facts"):
        render_client_instructions(
            "mockdomain",
            ["widget_returns"],
            sections_fixture,
            {"widget_returns": ["no_such_fact"]},
        )
    with pytest.raises(ValueError, match="unknown facts"):
        render_client_instructions(
            "mockdomain",
            ["widget_returns"],
            sections_fixture,
            client_confirmable={"widget_returns": ["no_such_fact"]},
        )
    with pytest.raises(ValueError, match="both held and confirmable"):
        render_client_instructions(
            "mockdomain",
            ["widget_returns"],
            sections_fixture,
            client_held={"widget_returns": ["return_window"]},
            client_confirmable={"widget_returns": ["return_window"]},
        )


def test_render_with_contested_adds_conflict_block(sections_fixture):
    rendered = render_client_instructions(
        "mockdomain",
        ["widget_returns", "widget_exchanges"],
        sections_fixture,
        client_held={"widget_returns": ["refund_destination", "return_window"]},
        client_contested={"widget_returns": ["return_window"]},
    )
    # A contested fact moves out of the held block: counts split cleanly.
    assert rendered.held_fact_count == 1
    assert rendered.contested_fact_count == 1
    prompt = rendered.prompt
    assert "<records_in_conflict>" in prompt
    contested_statement = "Widgets can be returned within 30 days."
    assert prompt.count(contested_statement) == 1
    assert prompt.index(contested_statement) > prompt.index("<records_in_conflict>")
    # The held block renders before the conflict block, each fact in its own
    # block only. (Tag positions are no proxy for block order: the kickoff
    # scope line cites both tags first.)
    held_statement = "Refunds go back to the original payment method."
    assert prompt.count(held_statement) == 1
    assert prompt.index("<what_only_you_know>") < prompt.index(held_statement)
    assert prompt.index(held_statement) < prompt.index(contested_statement)
    # The kickoff names both gaps: points only in the Client's head AND
    # points the records disagree on.
    assert "live only in your head" in prompt
    assert "the documents do not agree" in prompt
    # Conflicts are settled plainly, never pointed back.
    assert "sending them back to the records is not an acceptable answer" in prompt


def test_render_with_only_contested_drops_held_block(sections_fixture):
    rendered = render_client_instructions(
        "mockdomain",
        ["widget_returns"],
        sections_fixture,
        client_held={"widget_returns": ["return_window"]},
        client_contested={"widget_returns": ["return_window"]},
    )
    assert rendered.held_fact_count == 0
    assert rendered.contested_fact_count == 1
    prompt = rendered.prompt
    assert "<what_only_you_know>" not in prompt
    assert "<records_in_conflict>" in prompt
    # The contested-only scope line claims no undocumented points.
    assert "you know which version is current" in prompt
    assert "live only in your head" not in prompt


def test_render_rejects_contested_facts_not_held(sections_fixture):
    with pytest.raises(ValueError, match="contested facts must be held"):
        render_client_instructions(
            "mockdomain",
            ["widget_returns"],
            sections_fixture,
            client_held={"widget_returns": ["refund_destination"]},
            client_contested={"widget_returns": ["return_window"]},
        )


# ---------------------------------------------------------------------------
# Sandbox wiring: client_sections opt-in
# ---------------------------------------------------------------------------


AIRLINE_CORE_EVIDENCE_TASK_ID = (
    "002_airline_plus_construction_core_evidence_seeded_performance_hard"
)


def _construction_task_with_client_sections(sections):
    from tau2.hyper.task_loader import load_hyper_tau_task

    task = load_hyper_tau_task(AIRLINE_CORE_EVIDENCE_TASK_ID).model_copy(deep=True)
    task.hyper.client_sections = sections
    return task


def test_client_sections_and_instructions_are_mutually_exclusive():
    from pydantic import ValidationError

    from tau2.hyper.task_loader import load_hyper_tau_task

    task = load_hyper_tau_task(AIRLINE_CORE_EVIDENCE_TASK_ID)
    payload = task.hyper.model_dump()
    payload["client_instructions"] = "You are a stakeholder."
    payload["client_sections"] = ["customer_identity"]
    from tau2.hyper.data_model import HyperMetadata

    with pytest.raises(ValidationError, match="mutually"):
        HyperMetadata.model_validate(payload)


def test_construction_task_client_gating():
    from tau2.hyper.harnesses.codex import CodexSandboxBuilder
    from tau2.hyper.sandbox.orchestrator import SandboxOrchestrator

    no_client = _construction_task_with_client_sections(None)
    orchestrator = SandboxOrchestrator(no_client, CodexSandboxBuilder(llm="gpt-5.4"))
    assert not orchestrator._client_enabled()
    brief = orchestrator._build_brief("")
    assert "talk_to_client" not in brief

    with_client = _construction_task_with_client_sections(["customer_identity"])
    orchestrator = SandboxOrchestrator(with_client, CodexSandboxBuilder(llm="gpt-5.4"))
    assert orchestrator._client_enabled()
    brief = orchestrator._build_brief("Hi, I run support ops. Here's what I need.")
    assert brief.startswith("Hi, I run support ops.")
    assert "talk_to_client" in brief
    assert "README.md" in brief


def test_retail_plus_baseline_task_compiles_with_default_client():
    """The non-client retail evidence line keeps the default
    engaged-but-knowledge-less Client (all facts stay in the records). The
    client arm lives on the hard bundle (RETAIL_HARD_CLIENT_TASK_ID, below);
    the core-overlay A/B twin was retired 2026-08-19 with the hard
    migration."""
    from tau2.hyper.task_loader import load_hyper_tau_task
    from tau2.hyper.transformations import compile_hyper_task

    task_id = "008_retail_plus_construction_core_evidence_performance_hard"
    task = load_hyper_tau_task(task_id)
    compile_hyper_task(task_id).raise_on_errors()
    assert task.hyper.client_enabled is True
    assert task.hyper.client_sections is None


def test_resolve_client_instructions_renders_from_sections():
    task = _construction_task_with_client_sections(["customer_identity"])
    prompt = resolve_task_client_instructions(task)
    # The task's variant holds nothing with the Client, so the prompt is a
    # pure point-back stakeholder: contract present, no facts embedded.
    assert "Every interaction begins by identifying the customer." not in prompt
    assert "Never recite, list, or summarize policy rules" in prompt
    assert "you point back to the records" in prompt

    task = _construction_task_with_client_sections(None)
    assert resolve_task_client_instructions(task) == task.client_instructions


def test_render_generalizes_across_domains():
    """The contract is domain-agnostic: every hyper domain with section fact
    schemas renders, with held/confirmable lists taken from any section."""
    for domain in ("retail_plus", "telecom", "banking_knowledge"):
        section_ids = list_section_ids(domain)
        assert section_ids, f"domain {domain!r} has no section fact schemas"
        section = load_section_facts(domain, section_ids[0])
        held = {section.section_id: [section.facts[0].id]}
        confirmable = (
            {section.section_id: [section.facts[1].id]}
            if len(section.facts) > 1
            else {}
        )
        rendered = render_client_instructions(
            domain,
            [section.section_id],
            client_held=held,
            client_confirmable=confirmable,
        )
        assert rendered.held_fact_count == 1
        assert section.facts[0].statement in rendered.prompt
        assert "you point back to the records" in rendered.prompt
        # Every shipped domain has a stakeholder-facing business blurb.
        assert "at a company" not in rendered.prompt


def _retail_variant_kit_corpus(manifest, kit_dir, client_sections):
    """Build a variant kit and sweep its text files into a corpus.

    Quoted-printable emails are decoded (soft breaks split phrases), binary
    renders skipped (PNG/PDF bytes false-positive on digit runs), and ZIP
    exports expanded member-by-member — a phrase inside an export archive
    is just as much in the kit as one in a loose file.
    """
    import quopri
    import zipfile

    from tau2.hyper.sandbox.kit import _copy_sop_variant_materials

    _copy_sop_variant_materials(manifest, kit_dir, client_sections=client_sections)
    corpus = {}
    for path in kit_dir.rglob("*"):
        if not path.is_file() or path.suffix in {".png", ".pdf"}:
            continue
        if path.suffix == ".zip":
            with zipfile.ZipFile(path) as archive:
                corpus[path] = "".join(
                    archive.read(name).decode("utf-8", errors="ignore")
                    for name in archive.namelist()
                ).lower()
            continue
        raw = path.read_bytes()
        if path.suffix == ".eml":
            raw = quopri.decodestring(raw)
        corpus[path] = raw.decode("utf-8", errors="ignore").lower()
    assert corpus
    return corpus


# ---------------------------------------------------------------------------
# Airline+ hard client overlay
# ---------------------------------------------------------------------------

AIRLINE_HARD_TASK_ID = (
    "003_airline_plus_construction_core_evidence_hard_all_defects_performance_easy"
)
AIRLINE_HARD_CLIENT_TASK_ID = (
    "004_airline_plus_construction_core_evidence_hard_client_performance_medium"
)
AIRLINE_HARD_CLIENT_MANIFEST = (
    "tau2/hyper/sops/airline_plus/variants/core_evidence_bundle_hard_client_001.json"
)
AIRLINE_HARD_CLIENT_SECTIONS = ["booking_flight", "manage_existing_reservation"]

AIRLINE_BOOKING_HELD = (
    "additional_bag_cost",
    "baggage_gold_economy_allowance",
    "baggage_silver_business_allowance",
    "booking_payment_method_limits",
    "insurance_cost_per_passenger",
    "insurance_refund_health_weather",
    "max_passengers_per_reservation",
)
AIRLINE_MANAGE_HELD = (
    "additional_checked_bag_cost",
    "basic_economy_no_flight_changes",
    "cabin_change_reprice_all_segments_current_new_cabin_rate",
    "cancelled_flight_certificate_amount",
    "delayed_flight_certificate_amount",
    "flight_change_new_segments_use_current_price",
    "insurance_cannot_be_added_after_booking",
    "insurance_health_weather_allows_cancellation",
    "refund_arrival_window",
    "within_24_hours_allows_cancellation",
)


def test_airline_plus_hard_client_task_preserves_hard_contract():
    """Release task 004 is the hard task plus the Client overlay: same 67 eval
    tasks and sandbox envelope, client access on exactly the two overlaid
    journeys."""
    from tau2.hyper.task_loader import load_hyper_tau_task
    from tau2.hyper.transformations import compile_hyper_task

    hard = load_hyper_tau_task(AIRLINE_HARD_TASK_ID)
    client = load_hyper_tau_task(AIRLINE_HARD_CLIENT_TASK_ID)
    compile_hyper_task(AIRLINE_HARD_CLIENT_TASK_ID).raise_on_errors()

    assert client.hyper.client_enabled is True
    assert client.hyper.client_sections == AIRLINE_HARD_CLIENT_SECTIONS
    assert client.hyper.sop_variant_manifest_path == AIRLINE_HARD_CLIENT_MANIFEST
    assert client.test_task_ids == hard.test_task_ids
    assert client.hyper.sandbox_config == hard.hyper.sandbox_config
    assert list(client.hyper.performance_profile) == ["medium"]


def test_airline_plus_hard_client_bundle_end_to_end(tmp_path):
    """The hard client overlay compiles, renders, and builds a kit with the
    same 377-file delivered census as the hard bundle (substitution, never
    addition) while every held value stays out of the kit text and the
    mechanism carriers make it in exactly once."""
    from collections import Counter

    from tau2.hyper.transformations import compile_variant_transformations

    manifest = json.loads((DATA_DIR / AIRLINE_HARD_CLIENT_MANIFEST).read_text())
    compilation = compile_variant_transformations(manifest)
    assert compilation.errors == []
    assert compilation.client_held_fact_ids == {
        "booking_flight": list(AIRLINE_BOOKING_HELD),
        "manage_existing_reservation": list(AIRLINE_MANAGE_HELD),
    }
    assert compilation.client_confirmable_fact_ids == {
        "booking_flight": [
            "baggage_silver_economy_allowance",
            "payment_methods_saved_only",
        ],
        "manage_existing_reservation": [
            "business_cabin_allows_cancellation",
            "qualifies_insurance",
        ],
    }
    # One contested fact per journey, two readings each: the per-bag fee
    # (record $70 vs mailbox $65) and the cabin-reprice basis (current rate
    # vs original ticketing date).
    assert {
        section: {fact: len(readings) for fact, readings in contested.items()}
        for section, contested in compilation.client_contested_fact_ids.items()
    } == {
        "booking_flight": {"additional_bag_cost": 2},
        "manage_existing_reservation": {
            "cabin_change_reprice_all_segments_current_new_cabin_rate": 2
        },
    }

    rendered = render_client_instructions(
        "airline_plus",
        AIRLINE_HARD_CLIENT_SECTIONS,
        client_held=compilation.client_held_fact_ids,
        client_confirmable=compilation.client_confirmable_fact_ids,
        client_contested=compilation.client_contested_fact_ids,
    )
    # 17 held facts; the 2 contested ones render inside
    # <records_in_conflict>, not the plain held block.
    assert rendered.held_fact_count == 15
    assert rendered.confirmable_fact_count == 4
    assert "<what_only_you_know>" in rendered.prompt
    assert "<questions_you_can_settle>" in rendered.prompt
    assert "<records_in_conflict>" in rendered.prompt

    corpus = _retail_variant_kit_corpus(
        manifest, tmp_path / "kit", AIRLINE_HARD_CLIENT_SECTIONS
    )
    materials = sorted((tmp_path / "kit" / "uploaded_materials").iterdir())
    assert len(materials) == 377
    assert Counter(path.suffix for path in materials) == {
        ".md": 169,
        ".png": 113,
        ".eml": 93,
        ".json": 1,
        ".pdf": 1,
    }

    # Held-value spellings must survive nowhere in the kit text. (The two
    # contested readings are asserted separately below; binary renders are
    # out of corpus scope, and the deck's undecided 10-vs-12 fork lives on
    # a PDF page.)
    for leak in (
        "$45",  # insurance cost per passenger
        "$85",  # delayed-flight certificate amount
        "$170",  # cancelled-flight certificate amount
        "12 business days",  # ratified refund arrival window
        "10 business days",  # the fork's dead draft
        "within the last 24 hours",  # booking-grace window
        "24 hours",
        "48-hour",  # the retired launch-era grace spelling
        "health or weather",  # trip-protection covered reasons
        "at most 4",  # passenger cap
        "2 free checked",  # gold economy allowance
        "4 free checked",  # silver business allowance
        "one gift card",  # payment-combination limits
        "one travel certificate",
    ):
        hits = [path.name for path, text in corpus.items() if leak in text]
        assert not hits, f"held value {leak!r} leaked into {hits}"

    # Mechanism carriers, each exactly once: the two contested per-bag-fee
    # readings (record vs mailbox), the C10 named-schedule reference, the
    # F20 silent-gap pointer, and the two cabin-reprice readings (the kept
    # current-rate explanation vs the mailbox ticketing-date version).
    for breadcrumb, count in (
        ("$70", 1),
        ("$65", 1),
        ("$65 a bag in the sandbox", 1),
        ("payments operations combination schedule", 1),
        ("flat list rate per extra checked bag", 1),
        ("current rate", 1),
        ("ticketing date", 1),
        ("at the original ticketing date minus what was paid then", 1),
    ):
        assert sum(text.count(breadcrumb) for text in corpus.values()) == count, (
            f"breadcrumb {breadcrumb!r} must appear exactly {count}x"
        )


# ---------------------------------------------------------------------------
# Retail+ hard client overlay
# ---------------------------------------------------------------------------

RETAIL_HARD_TASK_ID = (
    "009_retail_plus_construction_core_evidence_hard_seeded_live_experiment"
    "_performance_medium"
)
RETAIL_HARD_CLIENT_TASK_ID = (
    "010_retail_plus_construction_core_evidence_hard_client_all_defects"
    "_performance_medium"
)
RETAIL_HARD_CLIENT_MANIFEST = (
    "tau2/hyper/sops/retail_plus/variants/core_evidence_bundle_hard_client_001.json"
)
RETAIL_HARD_CLIENT_SECTIONS = [
    "manage_pending_order",
    "manage_delivered_order",
    "service_foundations",
]

RETAIL_PENDING_HELD = (
    "ask_cancel_reason_before_processing",
    "cancel_sets_status_cancelled_and_refunds_full_amount",
    "card_or_paypal_cancel_refund_timeline",
    "gift_card_cancel_refund_immediate",
    "item_change_one_shot_locks_order",
    "payment_change_refund_timelines",
)
RETAIL_DELIVERED_HELD = (
    "exchange_one_shot_complete_list_before_submit",
    "exchange_refund_destination_any_saved_payment_method",
    "return_can_include_some_or_all_items",
    "return_refund_destination_disallowed_options",
    "return_refund_destination_original_or_existing_gift_card",
)
RETAIL_FOUNDATIONS_HELD = (
    "cancelled_orders_have_no_further_action",
    "cannot_add_new_payment_method",
    "cannot_change_order_quantity",
    "cannot_change_profile_email",
    "customer_information_lookup_allowed",
    "failed_verification_handling",
    "nontrivial_money_math_uses_calculator",
    "transfer_uses_exact_notice",
)


def test_retail_plus_hard_client_task_preserves_hard_contract():
    """Release task 010 is the hard task plus the Client overlay: same 134 eval
    tasks and sandbox envelope, client access on exactly the three overlaid
    service areas."""
    from tau2.hyper.task_loader import load_hyper_tau_task
    from tau2.hyper.transformations import compile_hyper_task

    hard = load_hyper_tau_task(RETAIL_HARD_TASK_ID)
    client = load_hyper_tau_task(RETAIL_HARD_CLIENT_TASK_ID)
    compile_hyper_task(RETAIL_HARD_CLIENT_TASK_ID).raise_on_errors()

    assert client.hyper.client_enabled is True
    assert client.hyper.client_sections == RETAIL_HARD_CLIENT_SECTIONS
    assert client.hyper.sop_variant_manifest_path == RETAIL_HARD_CLIENT_MANIFEST
    assert client.test_task_ids == hard.test_task_ids
    assert client.hyper.sandbox_config == hard.hyper.sandbox_config
    assert list(client.hyper.performance_profile) == ["medium"]
    # The overlay swaps the information-distribution manifest and nothing
    # else: the same service areas are transformed in the same order.
    assert [stage["stage"] for stage in client.hyper.composition_pipeline] == [
        stage["stage"] for stage in hard.hyper.composition_pipeline
    ]
    assert (
        client.hyper.composition_pipeline[0]["transformed_sections"]
        == hard.hyper.composition_pipeline[0]["transformed_sections"]
    )


def test_retail_plus_hard_client_bundle_end_to_end(tmp_path):
    """The hard client overlay compiles, renders, and builds a kit with the
    same 311-file delivered census as the hard bundle (substitution, never
    addition) while every held value stays out of the kit text and the
    mechanism carriers make it in at their pinned counts. Folds the retired
    union overlay gate's checks (kit census, residue regexes, exactly-once
    breadcrumbs) onto the hard kit."""
    import re as _re
    from collections import Counter

    from tau2.hyper.transformations import compile_variant_transformations

    manifest = json.loads((DATA_DIR / RETAIL_HARD_CLIENT_MANIFEST).read_text())
    compilation = compile_variant_transformations(manifest)
    assert compilation.errors == []
    assert compilation.client_held_fact_ids == {
        "manage_pending_order": list(RETAIL_PENDING_HELD),
        "manage_delivered_order": list(RETAIL_DELIVERED_HELD),
        "service_foundations": list(RETAIL_FOUNDATIONS_HELD),
    }
    assert compilation.client_confirmable_fact_ids == {
        "manage_delivered_order": ["return_submission_sets_status_and_sends_email"],
    }
    # Contested censuses: the reason-capture ordering splits three ways
    # (deck posting-line vs slack gate-opens vs ledger while-processing),
    # the delivered destination trio splits two ways each (interim
    # original-only ruling vs hold-queue gift-card floor practice), the
    # quantity prohibition three ways (qs3 ruling vs desk-trim macro vs
    # cancel-and-reorder floor), and the calculator mandate two ways (the
    # reviewer camps).
    assert {
        section: {fact: len(readings) for fact, readings in contested.items()}
        for section, contested in compilation.client_contested_fact_ids.items()
    } == {
        "manage_pending_order": {"ask_cancel_reason_before_processing": 3},
        "manage_delivered_order": {
            "return_refund_destination_original_or_existing_gift_card": 2,
            "return_refund_destination_disallowed_options": 2,
            "exchange_refund_destination_any_saved_payment_method": 2,
        },
        "service_foundations": {
            "cannot_change_order_quantity": 3,
            "nontrivial_money_math_uses_calculator": 2,
        },
    }

    rendered = render_client_instructions(
        "retail_plus",
        RETAIL_HARD_CLIENT_SECTIONS,
        client_held=compilation.client_held_fact_ids,
        client_confirmable=compilation.client_confirmable_fact_ids,
        client_contested=compilation.client_contested_fact_ids,
    )
    # 19 held facts; the 6 contested ones render inside
    # <records_in_conflict>, not the plain held block.
    assert rendered.held_fact_count == 13
    assert rendered.confirmable_fact_count == 1
    assert "<what_only_you_know>" in rendered.prompt
    assert "<questions_you_can_settle>" in rendered.prompt
    assert "<records_in_conflict>" in rendered.prompt

    corpus = _retail_variant_kit_corpus(
        manifest, tmp_path / "kit", RETAIL_HARD_CLIENT_SECTIONS
    )
    materials = sorted((tmp_path / "kit" / "uploaded_materials").iterdir())
    assert len(materials) == 311
    assert Counter(path.suffix for path in materials) == {
        ".eml": 38,
        ".json": 1,
        ".md": 128,
        ".pdf": 1,
        ".png": 131,
        ".vtt": 8,
        ".zip": 4,
    }

    # No spelling of the held card/PayPal refund window may survive; the
    # lookahead keeps the world's benign callback-slot enum ("afternoon
    # (3-6)", present in both arms' helpdesk field table) out of scope.
    window_regexes = [
        _re.compile(r"(?<![\d-])3\s?(?:[–-]|to)\s?6(?=\s*business)"),
        _re.compile(r"three[\s-]to[\s-]six"),
    ]
    for regex in window_regexes:
        hits = [path.name for path, text in corpus.items() if regex.search(text)]
        assert not hits, f"{regex.pattern!r} leaked into {hits}"

    # Held-value spellings and shed authoritative statements must survive
    # nowhere in the kit text (binary renders are out of corpus scope: the
    # board's A2 write-path-matrix deferral and the deck's reworked C-2
    # block live on PNG/PDF pages).
    for leak in (
        "3 to 6 business days",  # card/paypal refund window
        "credited back to that gift card immediately",  # gift-card leg
        "you are being transferred to a human agent",  # exact notice
        "uses the calculator",  # 05-28 mandate phrasings
        "call the calculator",
        "calculator requirement",
        "a cancelled order is complete",  # terminal-state ruling
        "some or all items",  # return scope
        "single return request per order",
        "original payment method or to an existing gift card",  # destinations
        "brand-new gift card",
        "cannot be modified or cancelled again",  # item-change lock
        "can only be called once",
        "complete list of items to exchange",  # exchange one-shot
        "can be only done once",
        "the authenticated customer's own profile",  # lookup scope
        "orders owned by the authenticated customer",
        "cannot add a new payment method",  # C11 pair
        "add it through the website",
        "cannot change the email",  # F22
        "cannot change item quantity",  # G23
        "no flags, holds, or lockouts",  # failed-verification handling
        "self-service account recovery",
    ):
        hits = [path.name for path, text in corpus.items() if leak in text]
        assert not hits, f"held value {leak!r} leaked into {hits}"

    # The intake session's calculator texture is the one deliberate keep
    # (an open proposal predating the reviewer-camp fork): both mentions
    # live in that single transcript and nowhere else.
    calc_files = [path for path, text in corpus.items() if "use the calculator" in text]
    assert len(calc_files) == 1 and "care pilot intake" in corpus[calc_files[0]]
    assert corpus[calc_files[0]].count("use the calculator") == 2

    # Mechanism carriers at their pinned counts: the D13 packet pointer and
    # its visible six-to-nine history, the parked/pasted/404 recording arcs,
    # the helpdesk disposition hold + registry expressions + desk decoys,
    # the slack tracker move with both destination readings, and the
    # case_033 one-list rewrite.
    for breadcrumb, count in (
        ("may enablement packet", 1),
        ("six-to-nine", 1),
        ("where the current window came from", 1),
        ("pasted into the meeting chat", 1),
        ("enablement checklist owners", 2),
        ("two reviewer camps", 1),
        ("404s since the drive reshuffle", 1),
        ("pending policy-desk disposition", 1),
        ("registry expression (not inlined by this extract", 4),
        ("route_to_accounts_desk", 1),
        ("desk quantity trims", 1),
        ("quantity edits are off the table", 3),
        ("decision-tracker entry", 3),
        ("just-cut-them-a-new-gift-card", 1),
        ("nothing outside the entry is selectable", 1),
        ("cancel-and-reorder conversation", 1),
        ("the reason gate opens the conversation", 1),
        ("care enablement owns the wording", 1),
        ("every cover you want changed in one list", 1),
    ):
        assert sum(text.count(breadcrumb) for text in corpus.values()) == count, (
            f"breadcrumb {breadcrumb!r} must appear exactly {count}x"
        )
