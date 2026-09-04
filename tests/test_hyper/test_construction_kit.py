"""Tests for construction kit assembly and loading."""

import json
import py_compile
import re
from email import policy
from email.parser import BytesParser

import pytest

from tau2.data_model.tasks import NLAssertion, RewardType
from tau2.hyper.data_model import HyperMetadata
from tau2.hyper.sandbox.kit import (
    _build_construction_agent_stub,
    _build_construction_readme,
    _developer_model_menu,
    _load_construction_scoring_tasks,
    build_kit,
)
from tau2.hyper.sandbox.orchestrator import SandboxOrchestrator
from tau2.hyper.task_loader import load_all_hyper_tau_tasks, load_hyper_tau_task
from tau2.hyper.transformations.sop_variants import (
    assemble_sop_variant,
    load_sop_variant_manifest,
)
from tau2.run import get_tasks
from tau2.utils.utils import DATA_DIR

# Everything the developer-facing manifest may carry. Runtime wiring (domain,
# user simulator settings, contract digest, reference-tool flags) is
# host-injected and must never appear in the kit; the Client-API contract
# version lives only in openapi.yaml's info.version.
DEPLOYMENT_MANIFEST_ALLOWED_KEYS = {
    "allowed_agent_models",
    "performance_requirements",
}


def _load_deployment_manifest(kit_path):
    manifest_path = kit_path / "framework" / "deployment_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    assert set(manifest) <= DEPLOYMENT_MANIFEST_ALLOWED_KEYS
    assert not (kit_path / "kit_config.json").exists()
    return manifest


PREMATURE_OUTCOME_NL_ASSERTION = (
    "The assistant avoided premature outcome language: it did not state or "
    "imply that a fix resolved the issue, an action was completed, or a "
    "requested change should or will work before the conversation contained a "
    "successful tool result or explicit customer confirmation verifying that "
    "outcome. It is acceptable to explain eligibility, ask for confirmation, "
    "or describe what will happen if the customer confirms, as long as the "
    "assistant does not present the outcome as already achieved or as expected "
    "to work before verification. If no fix/action outcome is discussed, this "
    "assertion is satisfied."
)

IDENTIFIER_MINIMIZATION_NL_ASSERTION = (
    "The assistant handled sensitive identifiers appropriately: it did not "
    "expose internal payment, account, database, or tool identifiers when a "
    "customer-facing label was available. Customer-facing identifiers such as "
    "reservation IDs, order IDs, item IDs, flight numbers, and phone numbers "
    "may be used when useful for authentication, lookup, disambiguation, "
    "comparing options, or explicit confirmation of a customer-requested "
    "action. Once an entity is clearly established and no exact confirmation "
    "or disambiguation is needed, the assistant should prefer natural labels "
    "or partial identifiers. If no identifiers are discussed, this assertion "
    "is satisfied."
)

REPEATED_OPENINGS_NL_ASSERTION = NLAssertion(
    id="avoid_repeated_openings",
    judge="response_openings",
    assertion=(
        "The assistant did not begin multiple customer-facing responses with "
        "the same opening phrase template."
    ),
)

REPEATED_OPENINGS_NL_ASSERTION_JSON = {
    "id": "avoid_repeated_openings",
    "assertion": (
        "The assistant did not begin multiple customer-facing responses with "
        "the same opening phrase template."
    ),
    "judge": "response_openings",
}

TELECOM_REPEATED_OPENINGS_NL_ASSERTION = NLAssertion(
    id="avoid_repeated_openings",
    judge="response_openings",
    assertion=(
        "The assistant did not begin multiple customer-facing responses with the "
        "same exact opening phrase or a trivially reworded variant of the same "
        "first clause. Only flag repeated openings when the initial phrase or "
        "sentence frame itself repeats; do not flag responses merely because "
        "independent training cases ask for the same required diagnostic step or "
        "reuse policy-required procedure words, entity labels, or setting names."
    ),
)


def test_construction_agent_stub_is_architecture_neutral(tmp_path):
    stub = _build_construction_agent_stub("telecom")
    agent_path = tmp_path / "agent.py"
    agent_path.write_text(stub)

    py_compile.compile(str(agent_path), doraise=True)
    assert "def create_agent():" in stub
    assert "from tau2.hyper.agent_context import get_agent_context" in stub
    assert "DEFAULT_AGENT_CONFIG" not in stub
    assert "Implement any agent logic here." in stub
    assert "raise NotImplementedError" in stub
    assert "LLMAgent" not in stub
    assert "system_prompt" not in stub


def test_construction_instructions_require_agent_implementation():
    readme = _build_construction_readme("telecom")
    assert "quality is measured by the proportion of evaluation cases" in readme
    assert "complex multi-step or multi-intent requests" in readme
    assert "incomplete or changing information" in readme
    assert "requests that must be declined or redirected" in readme
    assert "no particular architecture or development process" in readme
    assert "leaves the system in the correct state" in readme
    assert "communicates the right information" in readme
    assert "interface-only scaffold" in readme
    assert "works out of the box" not in readme
    assert "depends entirely" not in readme


def test_construction_kit_allows_generic_evidence_files(tmp_path):
    task = load_hyper_tau_task(
        "015_telecom_construction_core_evidence_hard_all_defects_performance_medium"
    )

    kit_path = build_kit(task, tmp_path / "kit")
    readme = (kit_path / "README.md").read_text()

    assert not (kit_path / "workspace" / "domain_rules.md").exists()
    assert not (kit_path / "workspace" / "policy.md").exists()
    assert "workspace/domain_rules.md" not in readme
    assert "any supplied kit artifact" in readme
    assert "using any organization you choose" in readme
    assert "agent's system prompt" not in readme


def test_construction_kit_rejects_copied_database_mode(tmp_path):
    task = load_hyper_tau_task(
        "015_telecom_construction_core_evidence_hard_all_defects_performance_medium"
    )
    task = task.model_copy(
        update={"hyper": task.hyper.model_copy(update={"client_api_mode": None})}
    )

    with pytest.raises(ValueError, match="copied-database construction kits"):
        build_kit(task, tmp_path / "kit")


def test_agent_contract_has_no_default_implementation_example():
    contract = (
        DATA_DIR / "tau2" / "hyper" / "framework_reference" / "agent_contract.md"
    ).read_text()

    assert "## Simplest implementation" not in contract
    assert "## Advanced: custom agent logic" not in contract
    assert "LLMAgent" not in contract
    assert "generate(" not in contract


def test_agent_contract_prescribes_no_architectures_or_state_designs():
    # The contract states the interface only; it must not seed the developer
    # with architecture menus or suggest what to put in the agent state.
    contract = (
        DATA_DIR / "tau2" / "hyper" / "framework_reference" / "agent_contract.md"
    ).read_text()
    flattened = " ".join(contract.split())

    assert "## Implementation freedom" not in contract
    assert "design labels" not in contract
    assert "Direct model loop" not in contract
    assert "Router with specialists" not in contract
    assert "Workflow or state machine" not in contract
    assert "Retrieval-backed agent" not in contract
    assert "Planner, executor, and verifier" not in contract
    assert "Validated action gateway" not in contract
    assert "Use it to store conversation history" not in flattened
    assert "routing" not in contract.lower()
    assert "cheaper" not in contract.lower()
    assert "class MyAgent" not in contract
    assert "return MyAgent" not in contract


def test_client_api_contract_is_domain_neutral_and_non_leading():
    # Ships to every REST-mode kit: no domain names, no eval vocabulary,
    # no implementation suggestions beyond the interface mechanics.
    contract = (
        DATA_DIR / "tau2" / "hyper" / "framework_reference" / "client_api_contract.md"
    ).read_text()

    assert "Retail" not in contract
    assert "Airline" not in contract
    assert "Telecom" not in contract
    assert "Banking" not in contract
    assert "trial" not in contract.lower()
    assert "such as arithmetic" not in contract
    assert "agent's tools" not in contract
    assert "preserve a small" not in contract


NO_GENERIC_SERVICE_INVITATIONS_NL_ASSERTION = (
    "The assistant did not invite the customer to ask for additional help, "
    "request anything else, or reach out later for more assistance. This "
    "includes generic service-closing invitations such as 'Is there anything "
    "else I can help you with?', 'Let me know if you need anything else', "
    "'feel free to reach out', or similar. Initial greetings that ask how the "
    "assistant can help, procedural questions needed to complete the current "
    "request, confirmations before taking an action, and concrete transfer or "
    "handoff statements do not violate this rule."
)

NO_SUPPORT_DEFLECTION_NL_ASSERTION = (
    "The assistant did not tell the customer to contact, call, reach out to, "
    "or speak with customer support, customer service, the company/store/"
    "airline/provider, or another support team/channel outside the current "
    "conversation. The assistant may offer or initiate a transfer, escalation, "
    "handoff, connection to a human agent or specialist, or contact/escalate "
    "on the customer's behalf from within the current conversation. If the "
    "assistant handles the request directly, asks procedural questions, or "
    "offers an in-conversation transfer/handoff/escalation, this assertion is "
    "satisfied."
)

CUSTOMER_VISIBLE_FAILURE_NL_ASSERTION = (
    "When the assistant describes a failed, blocked, or unexpected internal "
    "action/tool/system/backend operation, it explains the customer-visible "
    "outcome in plain language and gives a concrete next step without quoting "
    "raw error strings or exposing internal tool/API/backend/system mechanics. "
    "Violations include phrases such as 'the system returned an error', quoted "
    "backend errors, wrong API/tool explanations, or statements that a "
    "tool/API/system response was inconsistent. If the assistant does not "
    "describe a failed, blocked, or unexpected internal operation, this "
    "assertion is satisfied."
)

NO_INTERNAL_TOOL_MENTIONS_NL_ASSERTION = (
    "The assistant did not mention internal tools, tool calls, tool results, "
    "tool availability, or internal tooling/source limitations in "
    "customer-facing text. Violations include saying the assistant has or "
    "lacks a tool, referring to available/provided/order tools or "
    "policy/tools, naming a cancellation/return/exchange/modify/order tool, "
    "or explaining what a tool can or cannot do. Do not count customer-visible "
    "product language such as power tools, garden tool sets, hand tools, bike "
    "repair tools, measuring tools, hair styling tools, tool-free assembly, "
    "or saying no tools are required for a product."
)

NO_LONG_MENU_DUMPS_NL_ASSERTION = (
    "The assistant avoided broad next-step menu dumps when the customer needed "
    "focused guidance. If the customer was confused, frustrated, blocked by a "
    "limitation or policy, or affected by an error or failed action, mark a "
    "violation when the assistant responds by making the customer choose among "
    "a menu of several next paths, or combines multiple unrelated decisions, "
    "checks, or actions in one turn, instead of identifying the best next step. "
    "This includes three-or-more alternative paths, 'your options are' lists "
    "after a refusal or limitation, or a long turn that mixes status summaries, "
    "policy limits, possible actions, payment or refund choices, and "
    "confirmation requests. Do not mark concise one- or two-option choices, "
    "authentication alternatives, required details for one already-selected "
    "action, option comparisons the customer explicitly requested, or "
    "step-by-step instructions for one customer-visible action as violations. "
    "If no blocked, confused, or error context occurs, this assertion is "
    "satisfied."
)

MATCH_WARMTH_TO_OUTCOME_NL_ASSERTION = (
    "The assistant matched warmth to the outcome. Mark a violation when an "
    "assistant response begins with a celebratory outcome opener or global "
    "upbeat framing such as 'Great news', 'Good news', 'Perfect', 'Awesome', "
    "'Excellent news', 'Fantastic', 'Wonderful', or a standalone 'Great' or "
    "'Excellent', and the same response delivers a meaningful denial, failed "
    "action, unavailable option, ineligible request, unsupported action, or "
    "unresolved limitation for the customer. This applies when the cheerful "
    "wording frames the overall turn before the assistant says the requested "
    "action cannot be done, does not qualify, is not available, failed, or "
    "still needs unresolved troubleshooting. Do not mark neutral "
    "acknowledgements such as 'Great question' or 'Great, thanks', technical "
    "quality labels such as 'Excellent' speed or signal, or cheerful language "
    "that only reports a verified successful resolution. Do not mark a routine "
    "procedural warning or equivalent supported path if it does not block or "
    "constrain the customer's request. If no denial, failure, unavailable "
    "option, ineligible request, unsupported action, or unresolved limitation "
    "occurs in the assistant response, this assertion is satisfied."
)

AIRLINE_MODIFY_RESPONSE_PHRASING_RULE_IDS = [
    "never_say_unfortunately",
    "max_one_apology_per_conversation",
    "no_premature_outcome_language",
    "identifier_minimization",
    "avoid_repeated_openings",
    "no_generic_service_invitations",
    "customer_visible_failure_language",
    "no_long_menu_dumps",
    "match_warmth_to_outcome",
    "no_internal_tool_or_source_language",
]

RETAIL_RESPONSE_PHRASING_RULE_IDS = [
    "never_say_unfortunately",
    "max_one_apology_per_conversation",
    "no_premature_outcome_language",
    "identifier_minimization",
    "avoid_repeated_openings",
    "no_generic_service_invitations",
    "no_support_deflection",
    "customer_visible_failure_language",
    "no_long_menu_dumps",
    "match_warmth_to_outcome",
    "no_first_person_cant",
    "no_internal_tool_mentions",
    "no_policy_jargon",
]

RETAIL_TRANSFER_RESPONSE_PHRASING_RULE_IDS = [
    rule_id
    for rule_id in RETAIL_RESPONSE_PHRASING_RULE_IDS
    if rule_id != "avoid_repeated_openings"
]

RETAIL_TRANSCRIPT_SECTION_IDS = [
    "who_you_can_help",
    "what_you_can_do",
    "cancelling_pending_order",
    "changing_pending_order",
    "updating_default_shipping_address",
    "returning_delivered_order",
    "exchanging_delivered_order",
    "wrong_entitlement",
    "transferring_to_person",
]

RETAIL_EVIDENCE_BUNDLE_SECTION_IDS = [
    "customer_identity",
    "service_foundations",
    "manage_pending_order",
    "manage_delivered_order",
    "manage_customer_profile",
]

TELECOM_RESPONSE_PHRASING_RULE_IDS = [
    "one_visible_action",
    "no_tool_or_code_language",
    "no_markdown_formatting",
    "no_premature_outcome_language",
    "identifier_minimization",
    "avoid_repeated_openings",
    "no_generic_service_invitations",
    "no_support_deflection",
    "customer_visible_failure_language",
    "no_long_menu_dumps",
    "match_warmth_to_outcome",
    "apologize_at_most_once",
    "no_ai_self_limitation",
    "restrained_frustration_acknowledgement",
]

BANKING_TRANSCRIPT_SECTION_IDS = [
    "business_checking_opening_promotions",
    "business_credit_card_selection_promos",
    "business_savings_opening_promotions",
    "cash_back_disputes_and_corrections",
    "checking_atm_fee_rebates_and_credits",
    "checking_referral_programs_and_optimization",
    "credit_card_closure_retention_downgrade_payoff",
    "credit_card_declines_and_backend_incidents",
    "credit_card_referrals",
    "credit_card_replacements",
    "credit_card_transaction_disputes",
    "credit_limit_increases",
    "debit_card_disputes_declines_pin_limits",
    "debit_card_lost_stolen_freeze_replace",
    "direct_deposit_delay_and_escalation",
    "green_checking_faq",
    "mobile_check_deposit",
    "personal_account_closure_and_debit_cleanup",
    "personal_checking_opening_recommendation",
    "personal_credit_card_account_services",
    "personal_credit_card_application_recommendation",
    "personal_credit_card_rewards_and_promos",
    "personal_savings_opening_recommendation",
    "savings_apy_boosts_interest_discrepancies",
    "transfer_and_account_recovery_boundaries",
]


def test_telecom_construction_task_references_existing_tasks():
    for task_id in (
        "013_telecom_construction_core_evidence_seeded_all_defects_performance_medium",
        "014_telecom_construction_core_evidence_seeded_performance_hard",
        "017_telecom_construction_core_evidence_hard_client_live_experiment_"
        "performance_hard",
        "018_telecom_construction_core_evidence_hard_client_response_phrasing_"
        "performance_medium",
    ):
        task = load_hyper_tau_task(task_id)

        assert task.source_domain == "telecom"
        assert task.sop_document_path is None
        assert task.sop_variant_manifest_path.startswith(
            "tau2/hyper/sops/telecom/variants/"
        )

        telecom_task_ids = {str(task.id) for task in get_tasks("telecom")}
        missing = set(task.test_task_ids) - telecom_task_ids
        assert missing == set()


def test_banking_construction_task_references_existing_tasks():
    for task_id in (
        "022_banking_knowledge_construction_kb_performance_medium",
        "023_banking_knowledge_construction_kb_performance_hard",
        "028_banking_knowledge_construction_client_api_deposits_business_super_kb_"
        "performance_medium",
    ):
        task = load_hyper_tau_task(task_id)

        assert task.source_domain == "banking_knowledge"
        assert task.sop_document_path == "tau2/hyper/sops/banking_sop.md"
        assert task.knowledge_base_path == "tau2/domains/banking_knowledge/documents"

        banking_task_ids = {str(task.id) for task in get_tasks("banking_knowledge")}
        missing = set(task.test_task_ids) - banking_task_ids
        assert missing == set()


def test_airline_booking_modification_hybrid_task_references_existing_tasks():
    task = load_hyper_tau_task(
        "006_airline_plus_construction_core_evidence_response_phrasing_"
        "performance_medium"
    )

    assert task.source_domain == "airline_plus"
    assert task.sop_document_path is None
    assert task.sop_variant_manifest_path == (
        "tau2/hyper/sops/airline_plus/variants/core_evidence_bundle_001.json"
    )
    assert task.response_phrasing_rules_path == (
        "tau2/hyper/response_phrasing/airline_plus_response_phrasing.yaml"
    )
    assert task.composition_pipeline == [
        {
            "stage": "response_phrasing",
            "selected_rule_ids": AIRLINE_MODIFY_RESPONSE_PHRASING_RULE_IDS,
        },
        {
            "stage": "information_distribution",
            "variant_manifest_path": (
                "tau2/hyper/sops/airline_plus/variants/core_evidence_bundle_001.json"
            ),
            "transformed_sections": [
                "booking_flight",
                "manage_existing_reservation",
            ],
        },
    ]

    airline_task_ids = {str(task.id) for task in get_tasks("airline_plus")}
    missing = set(task.test_task_ids) - airline_task_ids
    assert missing == set()


def test_retail_core_evidence_bundle_task_references_existing_tasks():
    task = load_hyper_tau_task(
        "008_retail_plus_construction_core_evidence_performance_hard"
    )

    assert task.source_domain == "retail_plus"
    assert task.sop_document_path is None
    assert task.sop_variant_manifest_path == (
        "tau2/hyper/sops/retail_plus/variants/core_evidence_bundle_001.json"
    )
    assert task.composition_pipeline == [
        {
            "stage": "information_distribution",
            "variant_manifest_path": (
                "tau2/hyper/sops/retail_plus/variants/core_evidence_bundle_001.json"
            ),
            "transformed_sections": RETAIL_EVIDENCE_BUNDLE_SECTION_IDS,
        },
    ]

    retail_task_ids = {str(task.id) for task in get_tasks("retail_plus")}
    missing = set(task.test_task_ids) - retail_task_ids
    assert missing == set()


def test_construction_tasks_pin_user_reasoning_effort():
    tasks = load_all_hyper_tau_tasks()

    assert tasks
    for task in tasks:
        assert task.user_reasoning_effort == "none"


def test_maintained_construction_bundles_use_performance_profiles():
    task_root = DATA_DIR / "tau2/hyper/tasks"
    task_paths = sorted(task_root.glob("*.json"))

    assert task_paths
    for task_path in task_paths:
        payload = json.loads(task_path.read_text())
        assert "agent_llm" not in payload
        assert "agent_llm_args" not in payload
        assert "agent_reasoning_effort" not in payload
        assert "allowed_agent_models" not in payload
        # Each task pins exactly one tier spec; the tier name it is drawn
        # from stays internal to the benchmark.
        assert set(payload["performance_profile"]) <= {"easy", "medium", "hard"}
        assert len(payload["performance_profile"]) == 1

        task = load_hyper_tau_task(payload["id"])
        assert task.performance_profile == payload["performance_profile"]
        assert task.performance_requirements
        assert task.allowed_agent_models
        assert all("credit_rates" in config for config in task.allowed_agent_models)


def test_sandbox_orchestrator_derives_stock_fallback_from_model_list():
    task = load_hyper_tau_task(
        "006_airline_plus_construction_core_evidence_response_phrasing_"
        "performance_medium"
    )

    orchestrator = SandboxOrchestrator.from_task(task, builder=object())

    stock_model = task.allowed_agent_models[0]
    assert orchestrator.agent_llm == stock_model["model"]
    # Empty constraints normalize to None (the orchestrator treats both as
    # "no args").
    assert (orchestrator.agent_llm_args or {}) == stock_model["constraints"]
    assert orchestrator.allowed_agent_models == task.allowed_agent_models


def test_sandbox_orchestrator_can_expose_only_the_primary_model():
    task = load_hyper_tau_task(
        "006_airline_plus_construction_core_evidence_response_phrasing_"
        "performance_medium"
    )
    primary_config = {
        "model": "deepseek/deepseek-v4-flash",
        "constraints": {"reasoning_effort": "high"},
        "credit_rates": {"input_per_million": 0.14},
    }

    orchestrator = SandboxOrchestrator.from_task(
        task,
        builder=object(),
        allowed_agent_models_override=[primary_config],
    )

    assert orchestrator.agent_llm == primary_config["model"]
    assert orchestrator.agent_llm_args == primary_config["constraints"]
    assert orchestrator.allowed_agent_models == [primary_config]
    assert task.performance_requirements[0].budget == pytest.approx(0.061)


def test_construction_brief_leads_with_behavioral_quality_objective():
    task = load_hyper_tau_task(
        "006_airline_plus_construction_core_evidence_response_phrasing_"
        "performance_medium"
    )
    orchestrator = SandboxOrchestrator.from_task(task, builder=object())

    brief = orchestrator._build_brief("")

    assert "Quality is measured by the proportion" in brief
    assert "unseen evaluation cases" in brief
    assert "routine, complex, and unusual customer requests" in brief
    assert "No particular architecture or development process is required" in brief
    assert "Start by reading README.md" in brief


def test_sandbox_orchestrator_preserves_task_model_configurations():
    task = load_hyper_tau_task(
        "006_airline_plus_construction_core_evidence_response_phrasing_"
        "performance_medium"
    )
    model_configs = [
        {"model": "gpt-5.5", "constraints": {"reasoning_effort": "none"}},
        {"model": "gpt-5.5", "constraints": {"reasoning_effort": "xhigh"}},
    ]
    task = task.model_copy(
        update={
            "hyper": task.hyper.model_copy(
                update={"allowed_agent_models": model_configs}
            )
        }
    )

    orchestrator = SandboxOrchestrator.from_task(
        task,
        builder=object(),
        agent_llm="gpt-5.5",
        agent_llm_args={"reasoning_effort": "xhigh"},
    )

    assert orchestrator.allowed_agent_models == model_configs


def test_sandbox_orchestrator_rejects_constraints_outside_model_configurations():
    task = load_hyper_tau_task(
        "006_airline_plus_construction_core_evidence_response_phrasing_"
        "performance_medium"
    )
    task = task.model_copy(
        update={
            "hyper": task.hyper.model_copy(
                update={
                    "allowed_agent_models": [
                        {
                            "model": "gpt-5.5",
                            "constraints": {"reasoning_effort": "none"},
                        },
                        {
                            "model": "gpt-5.5",
                            "constraints": {"reasoning_effort": "xhigh"},
                        },
                    ]
                }
            )
        }
    )

    with pytest.raises(ValueError, match="must match its configured constraints"):
        SandboxOrchestrator.from_task(
            task,
            builder=object(),
            agent_llm="gpt-5.5",
            agent_llm_args={"reasoning_effort": "high"},
        )


def test_airline_plus_base_sop_variant_manifest_assembles_plus_sop():
    manifest_path = (
        DATA_DIR / "tau2/hyper/sops/airline_plus/variants/base_explicit_rules.json"
    )

    manifest = load_sop_variant_manifest(manifest_path)
    assembled_sop = assemble_sop_variant(manifest_path)
    canonical_sop = (DATA_DIR / "tau2/hyper/sops/airline_plus_sop.md").read_text()

    assert manifest["id"] == "airline_plus_base_explicit_rules"
    assert manifest["section_replacements"] == {}
    assert assembled_sop == canonical_sop


def test_construction_kit_can_build_sop_from_variant_manifest(tmp_path):
    task = load_hyper_tau_task(
        "004_airline_plus_construction_core_evidence_hard_client_performance_medium"
    )
    task = task.model_copy(
        update={
            "hyper": task.hyper.model_copy(
                update={
                    "sop_document_path": None,
                    "sop_variant_manifest_path": (
                        "tau2/hyper/sops/airline_plus/variants/base_explicit_rules.json"
                    ),
                    "composition_pipeline": None,
                }
            )
        }
    )

    kit_path = build_kit(task, tmp_path / "kit")

    assert (kit_path / "sop.md").read_text() == (
        DATA_DIR / "tau2/hyper/sops/airline_plus_sop.md"
    ).read_text()

    config = _load_deployment_manifest(kit_path)
    assert "sop_variant_manifest_path" not in config
    assert "sop_variant_id" not in config
    assert "information_distribution" not in config
    assert "transcripts_path" not in config


def test_construction_kit_exposes_performance_requirements(tmp_path):
    task = load_hyper_tau_task(
        "004_airline_plus_construction_core_evidence_hard_client_performance_medium"
    )

    kit_path = build_kit(task, tmp_path / "kit")
    config = _load_deployment_manifest(kit_path)
    readme = (kit_path / "README.md").read_text()

    # The tier the budget came from is a statement about benchmark difficulty,
    # so the kit names the budget neutrally and prices it instead.
    assert "performance_profile" not in config
    (requirement,) = config["performance_requirements"]
    assert requirement == {
        "id": "agent_credit_budget",
        "type": "credits",
        "measurement": "agent_model_calls",
        "budget": 0.061,
        "models": [entry["model"] for entry in task.allowed_agent_models],
    }
    assert task.performance_requirements[0].id == "medium_agent_credit_budget"
    assert "agent_credit_budget" in readme
    assert "0.0610-credit budget per conversation" in readme
    assert not re.search(r"\b(easy|medium)\b", readme, re.IGNORECASE)


def test_developer_model_menu_hides_harness_only_bookkeeping():
    configs = [
        {
            "model": "gpt-5.6-sol",
            "constraints": {},
            "credit_rates": {"input_per_million": 5.0},
            "tier": "easy",
        }
    ]

    metered = _developer_model_menu(configs, meters_credits=True)
    assert metered == [
        {
            "model": "gpt-5.6-sol",
            "constraints": {},
            "credit_rates": {"input_per_million": 5.0},
        }
    ]

    unmetered = _developer_model_menu(configs, meters_credits=False)
    assert unmetered == [{"model": "gpt-5.6-sol", "constraints": {}}]

    # The projection must not mutate the task-owned configs it reads.
    assert configs[0]["tier"] == "easy"


def test_multi_tier_budgets_are_described_by_the_models_they_meter():
    requirements = [
        {
            "id": "agent_credit_budget_1",
            "type": "credits",
            "measurement": "agent_model_calls",
            "budget": 0.68,
            "models": ["gpt-5.6-sol"],
        },
        {
            "id": "agent_credit_budget_2",
            "type": "credits",
            "measurement": "agent_model_calls",
            "budget": 0.44,
            "models": ["gpt-5.6-luna", "gpt-5-mini"],
        },
    ]

    readme = _build_construction_readme(
        "telecom", performance_requirements=requirements
    )

    # A one-model budget reads as singular; a shared one as plural.
    assert "`gpt-5.6-sol` has a 0.6800-credit budget" in readme
    assert "call on that model counts" in readme
    assert "`gpt-5.6-luna`, `gpt-5-mini` share a 0.4400-credit budget" in readme
    assert "call on those models counts" in readme
    assert "their overages add up" in readme
    assert not re.search(r"\b(easy|medium)\b", readme, re.IGNORECASE)


def test_uncapped_tier_spec_kit_omits_credit_and_tier_vocabulary(tmp_path):
    # No shipped final slot is uncapped anymore, so synthesize one: reuse a
    # real construction corpus but re-resolve its profile as a tier spec
    # whose explicit null budget removes the credit requirement.
    base_task = load_hyper_tau_task(
        "022_banking_knowledge_construction_kb_performance_medium"
    )
    task = base_task.model_copy(
        update={
            "hyper": HyperMetadata(
                **{
                    **base_task.hyper.model_dump(),
                    "performance_profile": {
                        "easy": {"models": ["gpt-5.6-sol"], "budget": None}
                    },
                    "allowed_agent_models": None,
                    "performance_requirements": [],
                }
            )
        }
    )
    assert task.performance_requirements == []
    assert task.allowed_agent_models[0]["tier"] == "easy"
    assert "credit_rates" in task.allowed_agent_models[0]

    kit_path = build_kit(task, tmp_path / "kit")
    config = _load_deployment_manifest(kit_path)
    readme = (kit_path / "README.md").read_text()

    assert config["allowed_agent_models"] == [
        {"model": "gpt-5.6-sol", "constraints": {}}
    ]
    assert config["performance_requirements"] == []
    assert "performance_profile" not in config
    assert "credit" not in readme.lower()


def test_sop_delivery_uploaded_material_validates_manifest(tmp_path):
    canonical = tmp_path / "canonical_sop.md"
    canonical.write_text("# Handbook\n\nIntro.\n\n## 1. Only Section\n\nBe kind.\n")
    manifest = {
        "id": "demoted_without_materials",
        "canonical_sop_path": str(canonical),
        "sop_delivery": "uploaded_material",
        "section_order": [
            {"id": "front_matter", "heading": None},
            {"id": "only", "heading": "## 1. Only Section"},
        ],
    }
    manifest_path = tmp_path / "variant.json"
    manifest_path.write_text(json.dumps(manifest))

    task = load_hyper_tau_task(
        "004_airline_plus_construction_core_evidence_hard_client_performance_medium"
    )
    task = task.model_copy(
        update={
            "hyper": task.hyper.model_copy(
                update={
                    "sop_document_path": None,
                    "sop_variant_manifest_path": str(manifest_path),
                    "composition_pipeline": None,
                }
            )
        }
    )

    # Demotion needs an uploaded_materials/ pool to deliver the SOP through.
    with pytest.raises(ValueError, match="section_source_schemas"):
        build_kit(task, tmp_path / "kit_no_materials")

    manifest["sop_delivery"] = "attachment"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Unknown sop_delivery"):
        build_kit(task, tmp_path / "kit_bad_value")


def test_booking_modification_hybrid_task_compiles_cohesive_artifact_bundle(tmp_path):
    task = load_hyper_tau_task(
        "006_airline_plus_construction_core_evidence_response_phrasing_"
        "performance_medium"
    )

    kit_path = build_kit(task, tmp_path / "kit")
    config = _load_deployment_manifest(kit_path)
    assert "agent_llm" not in config
    assert "agent_llm_args" not in config
    assert "performance_profile" not in config
    # ``tier`` is harness-side scoring bookkeeping and stays out of the kit.
    assert config["allowed_agent_models"] == [
        {key: value for key, value in entry.items() if key != "tier"}
        for entry in task.allowed_agent_models
    ]

    materials_dir = kit_path / "uploaded_materials"
    all_materials = sorted(materials_dir.iterdir())
    assert len(all_materials) == 192
    assert not any(path.name.startswith("upload_") for path in all_materials)
    assert {re.sub(r"_\d+$", "", path.stem) for path in all_materials} <= {
        "case_file",
        "email",
        "intake_form",
        "process_map",
        "reference_document",
        "screenshot",
        "slide_deck",
        "workspace_export",
    }
    screenshots = sorted(materials_dir.glob("*.png"))
    assert len(screenshots) == 53  # 52 payment/website screens + 1 process map
    workbooks = sorted(materials_dir.glob("*.pdf"))
    assert len(workbooks) == 1
    assert workbooks[0].read_bytes().startswith(b"%PDF")
    markdown_files = sorted(materials_dir.glob("*.md"))
    records = [
        path for path in markdown_files if path.read_text().startswith("# Case ")
    ]
    assert len(records) == 85
    assert {path.read_text().splitlines()[0] for path in records} == {
        f"# Case {index:03d}" for index in range(1, 86)
    }
    emails = sorted(materials_dir.glob("*.eml"))
    assert len(emails) == 50
    assert sum("Thread-Topic:" in path.read_text() for path in emails) == 50
    assert all(".example" not in path.read_text() for path in emails)
    assert all("Delivery Partner" not in path.read_text() for path in emails)
    email_archive_text = "\n".join(path.read_text() for path in emails)
    assert "Northstar" not in email_archive_text
    assert "@meridianairlines.com" in email_archive_text
    assert "@harborpointcx.com" in email_archive_text
    json_materials = sorted(materials_dir.glob("*.json"))
    assert len(json_materials) == 1
    slack_capture_path = json_materials[0]
    slack_capture = json.loads(slack_capture_path.read_text())
    assert slack_capture["capture_format"] == "slack_mcp_tool_call_log"
    assert slack_capture["workspace"]["name"] == "Meridian Airlines"
    assert slack_capture["workspace"]["id"] == "T08MeridianAIR1"
    assert len(slack_capture["tool_calls"]) == 22
    assert (
        sum(
            call["request"]["params"]["name"] == "slack_get_thread_replies"
            for call in slack_capture["tool_calls"]
        )
        == 20
    )
    slack_capture_text = slack_capture_path.read_text()
    assert "Northstar" not in slack_capture_text
    assert "https://meridianairlines.slack.com/" in slack_capture_text
    assert "Passenger servicing decision" not in slack_capture_text
    assert all(
        decision_id not in slack_capture_text
        for decision_id in ("D1", "D2", "D3", "D4", "D5", "D6")
    )
    assert "passenger count on an existing reservation cannot be changed" in (
        slack_capture_text
    )
    assert "authoritative_fact_ids" not in slack_capture_text
    assert "decision_history" not in slack_capture_text
    decoded_emails = []
    for path in emails:
        message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
        body = message.get_body(preferencelist=("plain",))
        decoded_emails.append(body.get_content() if body is not None else "")
    assert (
        sum(
            "revised pilot includes assisted booking" in text for text in decoded_emails
        )
        == 1
    )
    non_case_markdown = [path for path in markdown_files if path not in records]
    assert len(non_case_markdown) == 2
    handbook_path = next(
        path
        for path in non_case_markdown
        if path.read_text().startswith(
            "# Meridian Airlines — Customer Service Handbook: Core Standards"
        )
    )
    kickoff_path = next(path for path in non_case_markdown if path != handbook_path)
    kickoff_text = kickoff_path.read_text()
    assert "must not add a new payment method to a customer account" in kickoff_text
    assert "must not change the number of passengers" in kickoff_text
    assert "Inbound voice: Approximately 92,000 offered calls" in kickoff_text
    assert "Pilot budget:" in kickoff_text
    assert "Stakeholder map" in kickoff_text
    assert "Notes from Account-Team Conversations" in kickoff_text
    record_text = "\n".join(path.read_text() for path in records)
    assert "Behavior annotation" not in record_text
    assert record_text.count("modification checkout") == 2
    assert "cabin must stay the same across every flight" in record_text
    assert "everyone on the reservation must travel on those same flights" in (
        record_text
    )
    assert (
        "Whenever a flight or cabin change has a price difference, you provide "
        "one saved payment method from your profile" in record_text
    )
    assert "Passenger count on an existing reservation cannot be changed" not in (
        record_text
    )
    assert "Name and date of birth corrections are allowed" not in record_text
    assert "human supervisor cannot change" not in record_text
    for delegated_rule_text in (
        "$30 per passenger",
        "health or weather reasons",
        "at most 5 passengers",
        "Travel certificates cannot be used for flight or cabin modification payments",
        "must cover the full charge",
        "$100 per passenger",
        "$50 per passenger",
        "Silver and Gold members meet",
        "Travel insurance meets",
        "flying in Business meets",
        "add a new payment method to a customer account",
        "change the number of passengers on an existing reservation",
    ):
        assert delegated_rule_text not in record_text

    assert not (kit_path / "sop.md").exists()
    handbook_text = handbook_path.read_text()
    assert [line for line in handbook_text.splitlines() if line.startswith("## ")] == [
        "## 1. General Conduct",
        "## 2. Customer Identity",
        "## 3. Customer Profiles",
        "## 4. Flights",
        "## 5. Reservations",
        "## 6. Escalation",
    ]
    assert "**Current System Time:** 2024-05-15 15:00:00 EST" in handbook_text
    assert "uploaded_materials" not in handbook_text
    for stub_heading in (
        "## Book Travel",
        "## Manage an Existing Reservation",
        "## Additional Policy Notes",
    ):
        assert stub_heading not in handbook_text
    assert not list(kit_path.rglob("*.html"))
    assert not list(kit_path.rglob("*.pptx"))
    assert not list(kit_path.rglob("eval_manifest.json"))

    report = json.loads((tmp_path / "kit.transformation_report.json").read_text())
    assert report["totals"] == {
        "facts": 85,
        "covered": 85,
        "uncovered": 0,
        "multiply_represented": 0,
    }
    assert report["section_hierarchy"]["customer_identity"]["role"] == (
        "shared_reference"
    )
    expected_inherited_ids = {
        "customer_identity.customer_provided_user_id_required_for_reservation_actions",
    }
    expected_roles = {
        "booking_flight": "journey",
        "manage_existing_reservation": "journey",
    }
    for section_id, expected_role in expected_roles.items():
        hierarchy = report["section_hierarchy"][section_id]
        assert hierarchy["role"] == expected_role
        assert {
            fact["qualified_fact_id"] for fact in hierarchy["inherited_facts"]
        } == expected_inherited_ids
    assert {
        (
            entry["section_id"],
            entry["representation"],
            entry["bundle_id"],
            entry["primary"],
        )
        for entry in report["transformations"]
    } == {
        (
            "customer_identity",
            "explicit_rules",
            None,
            True,
        ),
        (
            "booking_flight",
            "process_flowchart",
            "booking_visual_hybrid",
            True,
        ),
        (
            "booking_flight",
            "website_screenshot",
            "booking_visual_hybrid",
            False,
        ),
        (
            "booking_flight",
            "support_transcripts",
            "booking_visual_hybrid",
            False,
        ),
        (
            "booking_flight",
            "email_thread_archive",
            "booking_visual_hybrid",
            False,
        ),
        (
            "manage_existing_reservation",
            "customer_kickoff_document",
            "manage_existing_reservation_multimodal",
            True,
        ),
        (
            "manage_existing_reservation",
            "email_thread_archive",
            "manage_existing_reservation_multimodal",
            False,
        ),
        (
            "manage_existing_reservation",
            "website_screenshot",
            "manage_existing_reservation_multimodal",
            False,
        ),
        (
            "manage_existing_reservation",
            "support_transcripts",
            "manage_existing_reservation_multimodal",
            False,
        ),
        (
            "manage_existing_reservation",
            "slack_mcp_dump",
            "manage_existing_reservation_multimodal",
            False,
        ),
        (
            "manage_existing_reservation",
            "process_presentation",
            "manage_existing_reservation_multimodal",
            False,
        ),
        (
            "manage_existing_reservation",
            "website_screenshot",
            "manage_existing_reservation_multimodal",
            False,
        ),
        (
            "manage_existing_reservation",
            "support_transcripts",
            "manage_existing_reservation_multimodal",
            False,
        ),
    }
    assert {
        (bundle["section_id"], bundle["bundle_id"]) for bundle in report["bundles"]
    } == {
        ("booking_flight", "booking_visual_hybrid"),
        (
            "manage_existing_reservation",
            "manage_existing_reservation_multimodal",
        ),
    }
    assert all(
        member["authoritative_fact_ids"]
        for bundle in report["bundles"]
        for member in bundle["members"]
    )


def test_retail_core_transcript_variant_replaces_selected_sections():
    manifest_path = (
        DATA_DIR
        / "tau2/hyper/sops/retail_plus/variants/"
        / "core_sections_transcript_induction_001.json"
    )

    manifest = load_sop_variant_manifest(manifest_path)
    assembled_sop = assemble_sop_variant(manifest_path)

    assert set(manifest["section_replacements"]) == set(RETAIL_TRANSCRIPT_SECTION_IDS)
    assert assembled_sop.count("`uploaded_materials/`") == len(
        RETAIL_TRANSCRIPT_SECTION_IDS
    )
    assert "### Transcript" not in assembled_sop
    assert "### Case" not in assembled_sop
    assert "Currency convention" in assembled_sop
    assert "`pending (items modified)`" in assembled_sop
    assert "These are the only valid status values" in assembled_sop
    assert "do not extend the database schema with new fields" in assembled_sop
    assert "Sometimes a customer realizes after placing the order" not in assembled_sop
    assert "Once an order is delivered" not in assembled_sop


def test_retail_core_transcript_schemas_cover_declared_policy_facts():
    manifest_path = (
        DATA_DIR
        / "tau2/hyper/sops/retail_plus/variants/"
        / "core_sections_transcript_induction_001.json"
    )
    manifest = load_sop_variant_manifest(manifest_path)

    assert set(manifest["section_source_schemas"]) == set(RETAIL_TRANSCRIPT_SECTION_IDS)

    for section_id in RETAIL_TRANSCRIPT_SECTION_IDS:
        schema_path = DATA_DIR / manifest["section_source_schemas"][section_id]
        schema = json.loads(schema_path.read_text())
        rendered_section_path = DATA_DIR / schema["rendered_section_path"]
        case_records = sorted(
            (rendered_section_path.parent / "training_records").glob("case_*.md")
        )
        fact_ids = {fact["id"] for fact in schema["facts"]}
        covered_fact_ids = {
            fact_id
            for transcript in schema["transcripts"]
            for fact_id in transcript["included_fact_ids"]
        }
        source_case_ids = {
            path.read_text().splitlines()[0].removeprefix("# Case ").strip()
            for path in case_records
        }

        assert schema["domain"] == "retail_plus"
        assert schema["section_id"] == section_id
        assert schema["response_phrasing_context"]["rules_path"] == (
            "tau2/hyper/response_phrasing/retail_plus_response_phrasing.yaml"
        )
        expected_rule_ids = (
            RETAIL_TRANSFER_RESPONSE_PHRASING_RULE_IDS
            if section_id in {"transferring_to_person", "wrong_entitlement"}
            else RETAIL_RESPONSE_PHRASING_RULE_IDS
        )
        assert schema["response_phrasing_context"]["selected_rule_ids"] == (
            expected_rule_ids
        )
        assert fact_ids == covered_fact_ids
        assert len(schema["facts"]) == len(fact_ids)
        assert len(schema["transcripts"]) == len(source_case_ids)
        assert source_case_ids == {
            transcript["id"] for transcript in schema["transcripts"]
        }


def test_banking_core_transcript_variant_appends_all_available_sections():
    manifest_path = (
        DATA_DIR
        / "tau2/hyper/sops/banking_knowledge/variants/"
        / "core_sections_transcript_induction_001.json"
    )

    manifest = load_sop_variant_manifest(manifest_path)
    assembled_sop = assemble_sop_variant(manifest_path)
    canonical_sop = (DATA_DIR / "tau2/hyper/sops/banking_sop.md").read_text()

    assert manifest["section_replacements"] == {}
    assert [section["id"] for section in manifest["append_sections"]] == (
        BANKING_TRANSCRIPT_SECTION_IDS
    )
    assert assembled_sop.startswith(canonical_sop.rstrip())
    assert assembled_sop.count("`uploaded_materials/`") == len(
        BANKING_TRANSCRIPT_SECTION_IDS
    )
    assert "## 7. The Knowledge Base" in assembled_sop
    assert "## Business checking opening, product selection, and promotions" in (
        assembled_sop
    )
    assert "## Human transfer and account-recovery boundary cases" in assembled_sop
    assert "## Checking referral programs, eligibility, and optimization" in (
        assembled_sop
    )
    assert "## Direct-deposit delay inquiries and escalation threshold" in assembled_sop
    assert "## Green Account checking fees, transfers, and PIN-decline FAQ" in (
        assembled_sop
    )
    assert "## Mobile check deposit procedure and issue resolution" in assembled_sop
    assert "## Personal credit-card account management and concierge services" in (
        assembled_sop
    )
    assert "### Transcript" not in assembled_sop
    assert "### Case" not in assembled_sop


def test_banking_core_transcript_schemas_cover_declared_policy_facts():
    manifest_path = (
        DATA_DIR
        / "tau2/hyper/sops/banking_knowledge/variants/"
        / "core_sections_transcript_induction_001.json"
    )
    manifest = load_sop_variant_manifest(manifest_path)

    assert set(manifest["section_source_schemas"]) == set(
        BANKING_TRANSCRIPT_SECTION_IDS
    )

    for section_id in BANKING_TRANSCRIPT_SECTION_IDS:
        schema_path = DATA_DIR / manifest["section_source_schemas"][section_id]
        schema = json.loads(schema_path.read_text())
        rendered_section_path = DATA_DIR / schema["rendered_section_path"]
        case_records = sorted(
            (rendered_section_path.parent / "training_records").glob("case_*.md")
        )
        fact_ids = {fact["id"] for fact in schema["facts"]}
        covered_fact_ids = {
            fact_id
            for transcript in schema["transcripts"]
            for fact_id in transcript["included_fact_ids"]
        }
        source_case_ids = {
            path.read_text().splitlines()[0].removeprefix("# Case ").strip()
            for path in case_records
        }

        assert schema["domain"] == "banking_knowledge"
        assert schema["section_id"] == section_id
        assert schema["response_phrasing_context"]["rules_path"] == (
            "tau2/hyper/response_phrasing/banking_response_phrasing.yaml"
        )
        assert fact_ids == covered_fact_ids
        assert len(schema["facts"]) == len(fact_ids)
        assert len(schema["transcripts"]) == len(source_case_ids)
        assert source_case_ids == {
            transcript["id"] for transcript in schema["transcripts"]
        }


def test_banking_task_pathway_gap_documents_are_decomposed():
    manifest_path = (
        DATA_DIR
        / "tau2/hyper/sops/banking_knowledge/variants/"
        / "core_sections_transcript_induction_001.json"
    )
    manifest = load_sop_variant_manifest(manifest_path)
    covered_document_ids = set()

    for schema_path in manifest["section_source_schemas"].values():
        schema = json.loads((DATA_DIR / schema_path).read_text())
        covered_document_ids.update(
            source_path.rsplit("/", 1)[-1].removesuffix(".json")
            for source_path in schema["domain_constraints"]["source_paths"]
            if "/documents/" in source_path
        )

    tasks = json.loads(
        (DATA_DIR / "tau2/domains/banking_knowledge/tasks.json").read_text()
    )
    tasks_by_id = {task["id"]: task for task in tasks}
    completed_task_ids = {
        "task_006",
        "task_019",
        "task_024",
        "task_025",
        "task_034",
        "task_057",
        "task_063",
        "task_064",
        "task_067",
        "task_070",
        "task_071",
        "task_072",
        "task_073",
        "task_080",
        "task_093",
        "task_098",
        "task_099",
        "task_100",
        "task_101",
        "task_102",
    }

    for task_id in completed_task_ids:
        required_document_ids = set(tasks_by_id[task_id]["required_documents"])
        assert required_document_ids <= covered_document_ids


def test_banking_task_pathway_gap_facts_preserve_losslessness_edges():
    section_root = DATA_DIR / "tau2/hyper/sops/banking_knowledge/sections"

    def statements(section_id: str) -> str:
        schema = json.loads((section_root / section_id / "schema.json").read_text())
        return " ".join(fact["statement"] for fact in schema["facts"])

    business_card_facts = statements("business_credit_card_selection_promos")
    assert "2025-10-01 through 2026-03-31" in business_card_facts
    assert "must post to the account within the first 2 months" in business_card_facts

    business_checking_facts = statements("business_checking_opening_promotions")
    assert "daily mobile check deposit limit is $25,000" in business_checking_facts
    assert "earns 1.25% APY" in business_checking_facts
    assert "compounded daily" in business_checking_facts

    personal_savings_facts = statements("personal_savings_opening_recommendation")
    assert "earns 7.0% APY" in personal_savings_facts
    assert "4 hours of complimentary wealth-guidance" in personal_savings_facts

    savings_apy_facts = statements("savings_apy_boosts_interest_discrepancies")
    assert "Silver Account must maintain at least $1,000" in savings_apy_facts
    assert "Diamond Elite Card credit card APY bonus is +0.6%" in savings_apy_facts
    assert "Crypto-Cash Back Card credit card APY bonus is +0.25%" in (
        savings_apy_facts
    )

    green_faq_facts = statements("green_checking_faq")
    assert "decline code 75" in green_faq_facts
    assert "decline code 83" in green_faq_facts
    assert "wait 10-15 minutes" in green_faq_facts

    card_service_facts = statements("personal_credit_card_account_services")
    assert "minimum monthly payment is 1.0%" in card_service_facts
    assert "initial response within 2 hours" in card_service_facts
    assert "must not finalize a purchase" in card_service_facts

    direct_deposit_facts = statements("direct_deposit_delay_and_escalation")
    assert "explicitly requested a human exactly 8 times" in direct_deposit_facts
    assert "usually post between 6 AM and 9 AM" in direct_deposit_facts
    direct_deposit_case = (
        section_root
        / "direct_deposit_delay_and_escalation/training_records/case_001.md"
    ).read_text()
    assert "Direct-deposit transfer request count: 8" in direct_deposit_case
    assert "transfer_to_human_agents called" in direct_deposit_case
    assert "YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON." in (
        direct_deposit_case
    )

    referral_facts = statements("checking_referral_programs_and_optimization")
    assert "at most 2 referral bonuses in any rolling 9-day window" in referral_facts
    assert "exact timestamps" in referral_facts
    assert "type of checking account a referrer owns does not affect" in referral_facts
    assert "'120 days since opening your first checking account with us.'" in (
        referral_facts
    )
    assert "waived for a free period of 6 months" in referral_facts
    assert "banking history with Rho-Bank" in referral_facts
    assert "deposit $50,000 within 120 days of opening" in referral_facts
    assert "at least 30 additional days" in referral_facts
    assert "Bluest Account balance earns 2.25% APY" in referral_facts
    assert "True Blue referral pays the referrer $350" in referral_facts
    assert "World Blue referral pays the referrer $300" in referral_facts

    mobile_deposit_facts = statements("mobile_check_deposit")
    assert "deposit_check_3847(account_id, check_amount)" in mobile_deposit_facts
    assert "agent cannot deposit a check for the customer" in mobile_deposit_facts
    assert "typically available within 1-2 business days" in mobile_deposit_facts
    assert "duplicate-deposit warning" in mobile_deposit_facts

    assert "Silver Plus Tier 1 earns 3.0% APY" in personal_savings_facts
    assert "Silver Plus Tier 2 earns 4.5% APY" in personal_savings_facts
    assert "up to 25 ATM fee rebates" in personal_savings_facts
    assert "0.025% relationship APY bonus" in personal_savings_facts
    assert "literal value '6.0% percent'" in personal_savings_facts

    personal_checking_facts = statements("personal_checking_opening_recommendation")
    assert "$2,500 daily mobile check deposit limit" in personal_checking_facts
    assert "ATM owner may impose a separate surcharge" in personal_checking_facts
    assert "early direct deposit 0 day(s) before payday" in personal_checking_facts


def test_banking_referral_program_source_bundle_is_losslessly_embedded():
    section_root = (
        DATA_DIR
        / "tau2/hyper/sops/banking_knowledge/sections/"
        / "checking_referral_programs_and_optimization"
    )
    schema = json.loads((section_root / "schema.json").read_text())
    source = (section_root / "source.md").read_text()
    document_paths = [
        source_path
        for source_path in schema["domain_constraints"]["source_paths"]
        if "/documents/" in source_path
    ]

    assert len(document_paths) == 15

    def normalize_trailing_whitespace(text: str) -> str:
        return "\n".join(line.rstrip() for line in text.splitlines())

    normalized_source = normalize_trailing_whitespace(source)
    for document_path in document_paths:
        document = json.loads((DATA_DIR / document_path).read_text())
        assert normalize_trailing_whitespace(document["content"]) in normalized_source


def test_banking_single_gap_source_documents_are_losslessly_embedded():
    section_root = DATA_DIR / "tau2/hyper/sops/banking_knowledge/sections"
    document_sections = {
        "doc_bank_accounts_bank_accounts_(general)_011": "mobile_check_deposit",
        "doc_savings_accounts_silver_plus_account_002": (
            "personal_savings_opening_recommendation"
        ),
        "doc_savings_accounts_gold_plus_account_002": (
            "personal_savings_opening_recommendation"
        ),
        "doc_checking_accounts_green_fee-free_account_003": (
            "personal_checking_opening_recommendation"
        ),
    }

    def normalize_trailing_whitespace(text: str) -> str:
        return "\n".join(line.rstrip() for line in text.splitlines())

    for document_id, section_id in document_sections.items():
        document = json.loads(
            (
                DATA_DIR
                / "tau2/domains/banking_knowledge/documents"
                / f"{document_id}.json"
            ).read_text()
        )
        source = (section_root / section_id / "source.md").read_text()
        assert normalize_trailing_whitespace(document["content"]) in (
            normalize_trailing_whitespace(source)
        )


def test_banking_mobile_check_record_obeys_response_phrasing_rules():
    case = (
        DATA_DIR
        / "tau2/hyper/sops/banking_knowledge/sections/mobile_check_deposit/"
        / "training_records/case_001.md"
    ).read_text()

    assert "I cannot deposit" not in case
    assert "Mobile check deposits must be completed by you" in case
    assert "First, open the Rho-Bank mobile app" in case
    assert "Sign in to the app" in case
    assert "Select the savings account that should receive the deposit" in case
    assert "Choose Mobile Check Deposit in the app" in case
    assert "Enter $840 exactly as printed on the check" in case
    assert "Submit the deposit in the app" in case
    assert "Keep the paper check secure while the deposit is pending" in case
    assert "Monitor the transaction history for posting and availability" in case


def test_banking_referral_records_preserve_optimization_boundaries():
    section_root = (
        DATA_DIR
        / "tau2/hyper/sops/banking_knowledge/sections/"
        / "checking_referral_programs_and_optimization"
    )
    schema = json.loads((section_root / "schema.json").read_text())
    transcripts = {transcript["id"]: transcript for transcript in schema["transcripts"]}

    case_b = (section_root / "training_records/case_002.md").read_text()
    assert "Each program uses its dashboard referral link" not in case_b
    assert "unique referral link without stating where" in case_b

    case_g = (section_root / "training_records/case_007.md").read_text()
    assert "one IN_PROGRESS referral opened 4 days ago" in case_g
    assert "IN_PROGRESS is not a paid bonus" in case_g
    assert "both bonus slots remain" in case_g
    assert {"F008", "F024"} <= set(transcripts["G"]["included_fact_ids"])

    case_h = (section_root / "training_records/case_008.md").read_text()
    assert "World Blue unavailable today" in case_h
    assert "Hunter Green is the highest eligible referrer bonus at $175" in case_h
    assert "Hunter Green" in transcripts["H"]["case_spec"]

    case_i = (section_root / "training_records/case_009.md").read_text()
    assert "both cross-product bonus slots are available" in case_i
    assert "Purple and Sky Blue referrals should be submitted now" in case_i

    case_j = (section_root / "training_records/case_010.md").read_text()
    assert "Exactly one of the 2 cross-product slots remains" in case_j
    assert "F014" not in transcripts["J"]["included_fact_ids"]
    assert "F015" not in transcripts["J"]["included_fact_ids"]
    assert "F016" not in transcripts["J"]["included_fact_ids"]


def test_retail_core_evidence_bundle_variant_appends_journey_stubs():
    manifest_path = "tau2/hyper/sops/retail_plus/variants/core_evidence_bundle_001.json"

    full = assemble_sop_variant(manifest_path)
    headings = re.findall(r"^## .*$", full, re.MULTILINE)
    assert headings == [
        "## Service and record foundations",
        "## Manage a pending order",
        "## Manage a delivered order",
        "## Update the customer profile",
    ]
    assert "Sometimes a customer realizes after placing the order" not in full
    assert "YOU ARE BEING TRANSFERRED TO A HUMAN AGENT" not in full

    dropped = assemble_sop_variant(manifest_path, drop_replaced_sections=True)
    assert dropped.startswith("# NorthStar Outfitters — Customer Care Handbook")
    assert re.findall(r"^## .*$", dropped, re.MULTILINE) == []
    assert "cover sheet for a working set" in dropped


def test_retail_core_evidence_bundle_task_builds_composed_kit(tmp_path):
    task = load_hyper_tau_task(
        "008_retail_plus_construction_core_evidence_performance_hard"
    )

    kit_path = build_kit(task, tmp_path / "kit")

    assert not (kit_path / "sop.md").exists()
    materials = kit_path / "uploaded_materials"

    handbook = (materials / "reference_document.md").read_text()
    assert handbook.startswith("# NorthStar Outfitters — Customer Care Handbook")
    assert "cover sheet for a working set" in handbook

    workspace_exports = sorted(
        path.name for path in materials.glob("workspace_export*.json")
    )
    assert workspace_exports == ["workspace_export.json"]

    case_files = sorted(path.name for path in materials.glob("case_file*.md"))
    assert len(case_files) == 48
    assert all(re.fullmatch(r"case_file_\d{2}\.md", name) for name in case_files)

    assert (materials / "intake_form.md").exists()
    assert (materials / "system_export.zip").exists()
    assert (materials / "api_contract.zip").exists()
    assert (materials / "slide_deck.pdf").exists()
    assert len(list(materials.glob("meeting_transcript*.vtt"))) == 5
    assert len(list(materials.glob("screenshot*.png"))) == 60

    assert not list(materials.glob("**/schema.json"))
    assert not list(materials.glob("**/eval_manifest.json"))

    config = _load_deployment_manifest(kit_path)
    assert "sop_variant_manifest_path" not in config
    assert "information_distribution" not in config
    assert "response_phrasing_rule_ids" not in config

    report = json.loads(
        (kit_path.parent / f"{kit_path.name}.transformation_report.json").read_text()
    )
    assert not report.get("errors")
    assert not report.get("warnings")


def test_construction_kit_uses_telecom_client_rest_boundary(tmp_path):
    task = load_hyper_tau_task(
        "015_telecom_construction_core_evidence_hard_all_defects_performance_medium"
    )
    kit_path = build_kit(task, tmp_path / "kit")

    assert task.client_api_mode == "rest"
    assert not (kit_path / "database").exists()
    assert (kit_path / "client_api" / "openapi.yaml").is_file()
    assert (kit_path / "framework" / "client_api_contract.md").is_file()
    assert not (kit_path / "workspace" / "data_model.py").exists()
    assert not (kit_path / "workspace" / "user_data_model.py").exists()
    assert not (kit_path / "workspace" / "user_tools.py").exists()
    assert not (kit_path / "workspace" / "environment.py").exists()
    assert "ClientAPIToolKitBase" in (kit_path / "workspace" / "tools.py").read_text()

    scenario_contract = (kit_path / "framework" / "scenario_contract.md").read_text()
    assert not (kit_path / "framework" / "toolkit_contract.md").exists()
    framework_readme = (kit_path / "framework" / "README.md").read_text()
    assert "toolkit_contract.md" not in framework_readme
    assert "client_api_contract.md" in framework_readme
    # The tau2.* imports in the contracts are only anonymous if the README
    # frames tau2 as an embedded open-source framework rather than leaving
    # the package name to read as the platform's own identity.
    assert "open-source agent framework" in framework_readme
    assert "## Backend Lifecycle" in scenario_contract
    assert "## Reward Basis" in scenario_contract
    for reward_type in (
        "NL_ASSERTION",
        "RESPONSE_ASSERTION",
        "COMMUNICATE",
        "ACTION",
        "DB",
        "ENV_ASSERTION",
    ):
        assert reward_type in scenario_contract
    assert "user_scenario.persona" in scenario_contract
    assert "run_local_test" in scenario_contract
    assert "local behavioral probes" in scenario_contract
    assert "They do not become" in scenario_contract
    assert "the final evaluation suite" in scenario_contract
    assert "broader set of unseen evaluation cases" in scenario_contract
    assert "python run_test.py" not in scenario_contract
    assert (
        '"purpose": "Exercise a repeat caller asking about a pending request."'
        in scenario_contract
    )
    # The framework doc ships in every kit: its examples must stay
    # domain-neutral rather than naming another domain's internal ids.
    assert "airline_plus" not in scenario_contract
    assert "airplane_mode" not in scenario_contract
    assert "broken_apn" not in scenario_contract
    assert "mobile_data_off" not in scenario_contract
    assert "cannot use `initialization_data`" in scenario_contract
    assert "cannot use user initialization actions" in scenario_contract
    assert "Developer's own assistant tools" in scenario_contract
    assert "`development_fixture`" in scenario_contract
    assert (kit_path / "client_api" / "development_seed.json").is_file()

    config = _load_deployment_manifest(kit_path)
    # Runtime wiring (source domain, user simulator, mode flags, contract
    # digest) is host-injected and never written into the kit.
    assert "client_api_mode" not in config
    assert "use_reference_user_tools" not in config
    assert "domain" not in config
    assert "user_llm" not in config
    assert "user_llm_args" not in config
    assert "client_api_contract_sha256" not in config
    assert "performance_profile" not in config
    assert config["performance_requirements"] == [
        {
            "id": "agent_credit_budget",
            "type": "credits",
            "measurement": "agent_model_calls",
            "budget": 0.054,
            "models": [entry["model"] for entry in task.allowed_agent_models],
        }
    ]
    assert config["allowed_agent_models"] == [
        {key: value for key, value in entry.items() if key != "tier"}
        for entry in task.allowed_agent_models
    ]
    assert "agent_llm" not in config
    assert "agent_llm_args" not in config

    readme = (kit_path / "README.md").read_text()
    assert "domain materials in this kit" in readme
    assert "file tree and file-level documentation" in readme
    assert "Your source of" not in readme
    assert "## What's here" not in readme
    assert "| Path | Description |" not in readme
    assert "## What you must build" not in readme
    assert "## Workflow" not in readme
    assert "## Required outputs" in readme
    assert "integration surface" in readme
    assert "## Testing" not in readme
    assert "## Simulation environment" in readme
    assert "simulated customer scenarios" in readme
    assert "framework/scenario_contract.md" in readme
    assert "quality is measured by the proportion of evaluation cases" in readme
    assert "broader set of unseen customer requests" in readme
    assert "reference assistant code" not in readme
    assert "host evaluator" not in readme
    assert "benchmark simulation" not in readme
    assert "run_local_test" in readme
    assert "`simulations/`" in readme
    assert "timestamped JSON artifact" in readme
    assert "python run_test.py" not in readme
    assert "run_test.py" not in readme
    assert "database/schema.json" not in readme
    assert not (kit_path / "run_test.py").exists()


def test_construction_kit_uses_banking_client_rest_boundary(tmp_path):
    task = load_hyper_tau_task(
        "022_banking_knowledge_construction_kb_performance_medium"
    )

    kit_path = build_kit(task, tmp_path / "kit")

    kb_path = kit_path / "knowledge_base"
    assert kb_path.is_dir()
    assert (kb_path / "INDEX.md").exists()
    assert len(list(kb_path.glob("*.json"))) == 698

    assert task.client_api_mode == "rest"
    assert not (kit_path / "database").exists()
    assert (kit_path / "client_api" / "openapi.yaml").is_file()
    assert (kit_path / "framework" / "client_api_contract.md").is_file()
    assert not (kit_path / "workspace" / "id_helpers.py").exists()
    assert not (kit_path / "workspace" / "data_model.py").exists()
    assert "ClientAPIToolKitBase" in (kit_path / "workspace" / "tools.py").read_text()

    index = (kb_path / "INDEX.md").read_text()
    assert "Total documents: 698" in index
    assert "doc_checking_accounts_dark_green_account_002" in index

    config = _load_deployment_manifest(kit_path)
    assert "knowledge_base_path" not in config
    assert "use_reference_user_tools" not in config
    assert "user_llm_args" not in config

    readme = (kit_path / "README.md").read_text()
    assert "domain materials in this kit" in readme
    assert "file tree and file-level documentation" in readme
    assert "Your source of" not in readme
    assert "## What's here" not in readme
    assert "| Path | Description |" not in readme
    assert "## What you must build" not in readme
    assert "## Workflow" not in readme
    assert "## Required outputs" in readme
    assert "integration surface" in readme
    assert "## Testing" not in readme
    assert "## Simulation environment" in readme
    assert "simulated customer scenarios" in readme
    assert "framework/scenario_contract.md" in readme
    assert "quality is measured by the proportion of evaluation cases" in readme
    assert "broader set of unseen customer requests" in readme
    assert "reference assistant code" not in readme
    assert "host evaluator" not in readme
    assert "benchmark simulation" not in readme
    assert "knowledge_base/" in readme
    assert "run_local_test" in readme
    assert "operations described across the SOP and `knowledge_base/`" in readme
    assert "all the operations described in the SOP" not in readme
    assert "scenarios in the SOP and knowledge base" in readme
    assert "workspace/user_tools.py" not in readme
    assert "workspace/user_data_model.py" not in readme
    assert "workspace/environment.py" not in readme
    assert "`simulations/`" in readme
    assert "timestamped JSON artifact" in readme
    assert "python run_test.py" not in readme
    assert "run_test.py" not in readme
    assert not (kit_path / "run_test.py").exists()
    assert not (kit_path / "learnings.md").exists()
    assert (kit_path / "framework" / "scenario_contract.md").exists()
    assert not (kit_path / "workspace" / "user_tools.py").exists()
    assert not (kit_path / "workspace" / "user_data_model.py").exists()
    assert not (kit_path / "workspace" / "environment.py").exists()


def test_construction_kit_omits_user_side_stubs_without_reference_user_tools(
    tmp_path,
):
    for task_id in (
        "004_airline_plus_construction_core_evidence_hard_client_performance_medium",
        "008_retail_plus_construction_core_evidence_performance_hard",
    ):
        task = load_hyper_tau_task(task_id)
        kit_path = build_kit(task, tmp_path / task.source_domain)

        readme = (kit_path / "README.md").read_text()
        assert "workspace/user_tools.py" not in readme
        assert "workspace/user_data_model.py" not in readme
        assert "workspace/environment.py" not in readme
        assert "database/schema.json" not in readme
        assert "Optional user/customer-side files" not in readme
        assert not (kit_path / "workspace" / "user_tools.py").exists()
        assert not (kit_path / "workspace" / "user_data_model.py").exists()
        assert not (kit_path / "workspace" / "environment.py").exists()


def test_airline_response_phrasing_construction_kit(tmp_path):
    task = load_hyper_tau_task(
        "006_airline_plus_construction_core_evidence_response_phrasing_"
        "performance_medium"
    )
    assert task.user_reasoning_effort == "none"

    kit_path = build_kit(task, tmp_path / "kit")

    rules_path = kit_path / "response_phrasing_rules.md"
    assert rules_path.read_text() == (
        '- Never use the word "unfortunately" in responses to the customer.\n'
        "- Do not apologize more than once per conversation.\n"
        "- Do not tell the customer that an issue is resolved, a change is "
        "complete, or a requested action should or will work until the "
        "relevant tool result or customer confirmation has verified that "
        "outcome. Before verification, frame it as the next thing to check or "
        "as what will be attempted after confirmation.\n"
        "- Use the least specific customer identifier that still lets the "
        "customer understand, disambiguate, compare options, or confirm the "
        "action. Customer-facing identifiers such as reservation IDs, order "
        "IDs, item IDs, flight numbers, and phone numbers are allowed when "
        "useful for lookup, disambiguation, option comparison, or explicit "
        "action confirmation. Otherwise, prefer natural labels or partial "
        "identifiers, and do not expose internal payment, account, database, "
        "or tool identifiers when a customer-facing label is available.\n"
        "- Do not begin multiple customer-facing responses with the same "
        "opening phrase. Repeating an opening phrase is allowed only if "
        "another instruction explicitly requires that exact wording.\n"
        "- Do not invite the customer to ask for additional help, request "
        "anything else, or reach out later for more assistance.\n"
        "- When an action fails or behaves unexpectedly, explain the "
        "customer-visible outcome in plain language and give one concrete next "
        "step. Do not quote raw error strings or mention internal tools, APIs, "
        "backend systems, or system mechanics.\n"
        "- When the customer is confused, frustrated, blocked by a limitation "
        "or policy, or affected by an error or failed action, do not present a "
        "large menu of next-step options. Recommend the best next action and "
        "ask for one confirmation or one needed piece of information.\n"
        "- Do not use celebratory or overly positive openings such as "
        '"Great news", "Good news", "Perfect", "Awesome", "Excellent news", '
        "or similar when the same response contains a denial, failure, "
        "unavailable option, ineligible request, unsupported action, or "
        "unresolved limitation. Match the warmth of the response to the "
        "outcome.\n"
        "- Do not mention internal tools, provided policy/source material, "
        "policy/tool availability, booking systems, or source limitations in "
        "customer-facing responses. Explain customer-visible booking facts "
        "directly.\n"
    )

    config = _load_deployment_manifest(kit_path)
    assert "user_llm_args" not in config
    assert "response_phrasing_source_task_id" not in config
    assert "response_phrasing_rules_path" not in config
    assert "response_phrasing_rule_ids" not in config
    assert "response_assertions" not in config
    assert "nl_assertions" not in config

    scoring_tasks = _load_construction_scoring_tasks(task)
    assert scoring_tasks
    first_criteria = scoring_tasks[0].evaluation_criteria
    assert first_criteria is not None
    assert RewardType.RESPONSE_ASSERTION in first_criteria.reward_basis
    assert RewardType.NL_ASSERTION in first_criteria.reward_basis
    assert first_criteria.response_assertions is not None
    assert [assertion.id for assertion in first_criteria.response_assertions] == [
        "never_say_unfortunately",
        "no_internal_tool_or_source_language",
    ]
    assert first_criteria.nl_assertions is not None
    assert "Agent should refuse to proceed with the cancellation." in (
        first_criteria.nl_assertions
    )
    assert "The assistant did not apologize more than once." in (
        first_criteria.nl_assertions
    )
    assert PREMATURE_OUTCOME_NL_ASSERTION in first_criteria.nl_assertions
    assert IDENTIFIER_MINIMIZATION_NL_ASSERTION in first_criteria.nl_assertions
    assert REPEATED_OPENINGS_NL_ASSERTION in first_criteria.nl_assertions
    assert NO_GENERIC_SERVICE_INVITATIONS_NL_ASSERTION in first_criteria.nl_assertions
    assert NO_SUPPORT_DEFLECTION_NL_ASSERTION not in first_criteria.nl_assertions
    assert CUSTOMER_VISIBLE_FAILURE_NL_ASSERTION in first_criteria.nl_assertions
    assert NO_LONG_MENU_DUMPS_NL_ASSERTION in first_criteria.nl_assertions
    assert MATCH_WARMTH_TO_OUTCOME_NL_ASSERTION in first_criteria.nl_assertions


def test_retail_response_phrasing_construction_kit(tmp_path):
    task = load_hyper_tau_task(
        "012_retail_plus_construction_core_evidence_hard_client_all_defects_"
        "response_phrasing_performance_hard"
    )
    assert task.user_reasoning_effort == "none"

    kit_path = build_kit(task, tmp_path / "kit")

    rules_path = kit_path / "response_phrasing_rules.md"
    assert rules_path.read_text() == (
        '- Never use the word "unfortunately" in responses to the customer.\n'
        "- Do not apologize more than once per conversation.\n"
        "- Do not tell the customer that an issue is resolved, a change is "
        "complete, or a requested action should or will work until the "
        "relevant tool result or customer confirmation has verified that "
        "outcome. Before verification, frame it as the next thing to check or "
        "as what will be attempted after confirmation.\n"
        "- Use the least specific customer identifier that still lets the "
        "customer understand, disambiguate, compare options, or confirm the "
        "action. Customer-facing identifiers such as reservation IDs, order "
        "IDs, item IDs, flight numbers, and phone numbers are allowed when "
        "useful for lookup, disambiguation, option comparison, or explicit "
        "action confirmation. Otherwise, prefer natural labels or partial "
        "identifiers, and do not expose internal payment, account, database, "
        "or tool identifiers when a customer-facing label is available.\n"
        "- Do not begin multiple customer-facing responses with the same "
        "opening phrase. Repeating an opening phrase is allowed only if "
        "another instruction explicitly requires that exact wording.\n"
        "- Do not invite the customer to ask for additional help, request "
        "anything else, or reach out later for more assistance.\n"
        "- Do not tell the customer to contact, call, reach out to, or speak "
        "with customer support or another support channel. Handle the request "
        "directly when possible, or offer an in-conversation transfer, "
        "escalation, or handoff when needed.\n"
        "- When an action fails or behaves unexpectedly, explain the "
        "customer-visible outcome in plain language and give one concrete next "
        "step. Do not quote raw error strings or mention internal tools, APIs, "
        "backend systems, or system mechanics.\n"
        "- When the customer is confused, frustrated, blocked by a limitation "
        "or policy, or affected by an error or failed action, do not present a "
        "large menu of next-step options. Recommend the best next action and "
        "ask for one confirmation or one needed piece of information.\n"
        "- Do not use celebratory or overly positive openings such as "
        '"Great news", "Good news", "Perfect", "Awesome", "Excellent news", '
        "or similar when the same response contains a denial, failure, "
        "unavailable option, ineligible request, unsupported action, or "
        "unresolved limitation. Match the warmth of the response to the "
        "outcome.\n"
        '- Do not use first-person inability phrases like "I can\'t", "I cannot", '
        'or "I can not" in responses to the customer.\n'
        "- Do not mention internal tools or tooling in responses to the customer.\n"
        '- Do not use the words "policy" or "policies" in responses to the '
        "customer.\n"
    )

    config = _load_deployment_manifest(kit_path)
    assert "user_llm_args" not in config
    assert "response_phrasing_source_task_id" not in config
    assert "response_phrasing_rules_path" not in config
    assert "response_phrasing_rule_ids" not in config
    assert "response_assertions" not in config
    assert "nl_assertions" not in config

    scoring_tasks = _load_construction_scoring_tasks(task)
    assert scoring_tasks
    first_criteria = scoring_tasks[0].evaluation_criteria
    assert first_criteria is not None
    assert RewardType.RESPONSE_ASSERTION in first_criteria.reward_basis
    assert RewardType.NL_ASSERTION in first_criteria.reward_basis
    assert first_criteria.response_assertions is not None
    assert len(first_criteria.response_assertions) == 3
    assert [assertion.id for assertion in first_criteria.response_assertions] == [
        "never_say_unfortunately",
        "no_first_person_cant",
        "no_policy_jargon",
    ]
    assert first_criteria.nl_assertions is not None
    assert "The assistant did not apologize more than once." in (
        first_criteria.nl_assertions
    )
    assert PREMATURE_OUTCOME_NL_ASSERTION in first_criteria.nl_assertions
    assert IDENTIFIER_MINIMIZATION_NL_ASSERTION in first_criteria.nl_assertions
    assert REPEATED_OPENINGS_NL_ASSERTION in first_criteria.nl_assertions
    assert NO_GENERIC_SERVICE_INVITATIONS_NL_ASSERTION in first_criteria.nl_assertions
    assert NO_SUPPORT_DEFLECTION_NL_ASSERTION in first_criteria.nl_assertions
    assert CUSTOMER_VISIBLE_FAILURE_NL_ASSERTION in first_criteria.nl_assertions
    assert NO_LONG_MENU_DUMPS_NL_ASSERTION in first_criteria.nl_assertions
    assert MATCH_WARMTH_TO_OUTCOME_NL_ASSERTION in first_criteria.nl_assertions
    assert NO_INTERNAL_TOOL_MENTIONS_NL_ASSERTION in first_criteria.nl_assertions


def test_telecom_response_phrasing_construction_kit(tmp_path):
    task = load_hyper_tau_task(
        "018_telecom_construction_core_evidence_hard_client_response_phrasing_"
        "performance_medium"
    )
    assert task.user_reasoning_effort == "none"

    kit_path = build_kit(task, tmp_path / "kit")

    rules_path = kit_path / "response_phrasing_rules.md"
    assert rules_path.read_text() == (
        "- When giving the customer phone troubleshooting instructions, ask for "
        "only one customer-visible phone action or settings check per assistant "
        "response. It is fine to ask them to report the result of that one "
        "action.\n"
        "- Do not expose raw diagnostic command names, function names, "
        "snake_case identifiers, or code formatting in customer-facing "
        "responses. Describe the customer-visible phone action in plain "
        "language instead.\n"
        "- Do not use markdown formatting, numbered lists, bullet lists, bold "
        "text, or inline code formatting in customer-facing responses.\n"
        "- Do not tell the customer that an issue is resolved, a change is "
        "complete, or a requested action should or will work until the "
        "relevant tool result or customer confirmation has verified that "
        "outcome. Before verification, frame it as the next thing to check or "
        "as what will be attempted after confirmation.\n"
        "- Use the least specific customer identifier that still lets the "
        "customer understand, disambiguate, compare options, or confirm the "
        "action. Customer-facing identifiers such as reservation IDs, order "
        "IDs, item IDs, flight numbers, and phone numbers are allowed when "
        "useful for lookup, disambiguation, option comparison, or explicit "
        "action confirmation. Otherwise, prefer natural labels or partial "
        "identifiers, and do not expose internal payment, account, database, "
        "or tool identifiers when a customer-facing label is available.\n"
        "- Do not begin multiple customer-facing responses with the same "
        "opening phrase. Repeating an opening phrase is allowed only if "
        "another instruction explicitly requires that exact wording.\n"
        "- Do not invite the customer to ask for additional help, request "
        "anything else, or reach out later for more assistance.\n"
        "- Do not tell the customer to contact, call, reach out to, or speak "
        "with customer support or another support channel. Handle the request "
        "directly when possible, or offer an in-conversation transfer, "
        "escalation, or handoff when needed.\n"
        "- When an action fails or behaves unexpectedly, explain the "
        "customer-visible outcome in plain language and give one concrete next "
        "step. Do not quote raw error strings or mention internal tools, APIs, "
        "backend systems, or system mechanics.\n"
        "- When the customer is confused, frustrated, blocked by a limitation "
        "or policy, or affected by an error or failed action, do not present a "
        "large menu of next-step options. Recommend the best next action and "
        "ask for one confirmation or one needed piece of information.\n"
        "- Do not use celebratory or overly positive openings such as "
        '"Great news", "Good news", "Perfect", "Awesome", "Excellent news", '
        "or similar when the same response contains a denial, failure, "
        "unavailable option, ineligible request, unsupported action, or "
        "unresolved limitation. Match the warmth of the response to the "
        "outcome.\n"
        "- Do not apologize more than once per conversation.\n"
        '- Do not explain limitations by saying "as an AI," "as a virtual '
        'assistant," "my primary function," or "my main function." State the '
        "limitation directly.\n"
        "- When the customer expresses frustration, anxiety, confusion, or "
        "worry, acknowledge it briefly and then move directly to a concrete "
        "next step. Do not stack multiple sympathy or apology sentences before "
        "the next step.\n"
    )

    config = _load_deployment_manifest(kit_path)
    assert "user_llm_args" not in config
    assert "response_phrasing_source_task_id" not in config
    assert "response_phrasing_rules_path" not in config
    assert "response_phrasing_rule_ids" not in config
    assert "response_assertions" not in config
    assert "nl_assertions" not in config

    scoring_tasks = _load_construction_scoring_tasks(task)
    assert scoring_tasks
    first_criteria = scoring_tasks[0].evaluation_criteria
    assert first_criteria is not None
    assert RewardType.RESPONSE_ASSERTION in first_criteria.reward_basis
    assert RewardType.NL_ASSERTION in first_criteria.reward_basis
    assert first_criteria.response_assertions is not None
    assert [assertion.id for assertion in first_criteria.response_assertions] == [
        "no_tool_or_code_language",
        "no_markdown_formatting",
        "apologize_at_most_once",
        "no_ai_self_limitation",
    ]
    assert first_criteria.nl_assertions is not None
    assert any(
        "only one customer-visible phone action" in assertion
        for assertion in first_criteria.nl_assertions
    )
    assert PREMATURE_OUTCOME_NL_ASSERTION in first_criteria.nl_assertions
    assert IDENTIFIER_MINIMIZATION_NL_ASSERTION in first_criteria.nl_assertions
    assert TELECOM_REPEATED_OPENINGS_NL_ASSERTION in first_criteria.nl_assertions
    assert NO_GENERIC_SERVICE_INVITATIONS_NL_ASSERTION in first_criteria.nl_assertions
    assert NO_SUPPORT_DEFLECTION_NL_ASSERTION in first_criteria.nl_assertions
    assert CUSTOMER_VISIBLE_FAILURE_NL_ASSERTION in first_criteria.nl_assertions
    assert NO_LONG_MENU_DUMPS_NL_ASSERTION in first_criteria.nl_assertions
    assert MATCH_WARMTH_TO_OUTCOME_NL_ASSERTION in first_criteria.nl_assertions
    assert any(
        "expresses frustration, anxiety, confusion, or worry" in assertion
        for assertion in first_criteria.nl_assertions
    )


def test_banking_response_phrasing_construction_kit(tmp_path):
    full_task = load_hyper_tau_task(
        "039_banking_knowledge_construction_client_api_deposit_services_"
        "response_phrasing_performance_medium"
    )
    task = full_task.model_copy(
        update={
            "hyper": full_task.hyper.model_copy(
                update={"test_task_ids": ["task_001"]},
            )
        },
    )

    kit_path = build_kit(task, tmp_path / "kit")

    rules = (kit_path / "response_phrasing_rules.md").read_text()
    assert "banking self-service, verification, security" in rules
    assert 'Never use the word "unfortunately"' in rules
    assert "Do not tell the customer to contact" not in rules
    assert "Do not use markdown formatting" not in rules
    assert "Do not mention internal tools" not in rules

    config = _load_deployment_manifest(kit_path)
    assert "response_phrasing_source_task_id" not in config
    assert "response_phrasing_rules_path" not in config
    assert "response_phrasing_rule_ids" not in config
    assert "response_assertions" not in config
    assert "nl_assertions" not in config

    scoring_tasks = _load_construction_scoring_tasks(task)
    assert scoring_tasks
    first_criteria = scoring_tasks[0].evaluation_criteria
    assert first_criteria is not None
    assert RewardType.RESPONSE_ASSERTION in first_criteria.reward_basis
    assert RewardType.NL_ASSERTION in first_criteria.reward_basis


def test_pinned_kit_filename_collision_decollides_across_sections():
    """Two sections pinning the same neutral kit_filename must both ship.

    ccref and credit_card_replacements both pin device_capture_001.png;
    before the wave-3 fix a union kit (combined-14, all-sections hard)
    crashed at write time on the collision. The later carrier — stable
    source-basename order, identical in both A/B arms — moves to the next
    free ordinal of the pin's own stem and width.
    """
    from tau2.hyper.sandbox.kit import _pool_uploaded_material_names
    from tau2.hyper.transformations.base import KitFile

    alpha = KitFile(
        "uploaded_materials/device_capture_001.png",
        b"ALPHA",
        preserve_filename=True,
        source_name="device_screen_001_alpha_2025-11-06.png",
    )
    beta = KitFile(
        "uploaded_materials/device_capture_001.png",
        b"BETA",
        preserve_filename=True,
        source_name="device_screen_001_beta_2025-11-08.png",
    )
    other = KitFile(
        "uploaded_materials/device_capture_002.png",
        b"OTHER",
        preserve_filename=True,
        source_name="device_screen_002_beta_2025-11-10.png",
    )
    out = _pool_uploaded_material_names([alpha, beta, other])
    assert sorted(kit_file.relative_path for kit_file in out) == [
        "uploaded_materials/device_capture_001.png",
        "uploaded_materials/device_capture_002.png",
        "uploaded_materials/device_capture_003.png",
    ]
    # source-basename order: alpha keeps the pin, beta bumps PAST the
    # already-taken 002 to 003, keeping the pin's 3-digit width.
    assert alpha.relative_path == "uploaded_materials/device_capture_001.png"
    assert beta.relative_path == "uploaded_materials/device_capture_003.png"


def test_client_carrier_shadow_requires_matching_source_name():
    """A client fork shadows copies of ITS carrier, never an unrelated
    artifact another section pinned to the same neutral kit filename.

    Carrier identity is (kit path, source basename): in the combined-14
    client arm, credit_card_replacements' client device captures must not
    swallow credit_card_referrals' byte-different base captures that happen
    to pin the same device_capture_00N.png names.
    """
    from tau2.hyper.sandbox.kit import _substitute_client_carriers
    from tau2.hyper.transformations.base import KitFile

    path = "uploaded_materials/device_capture_001.png"
    fork = KitFile(
        path,
        b"FORK",
        preserve_filename=True,
        client_substitute=True,
        source_name="capture_alpha.png",
    )
    same_carrier_base_copy = KitFile(
        path,
        b"BASE",
        preserve_filename=True,
        source_name="capture_alpha.png",
    )
    unrelated_same_pin = KitFile(
        path,
        b"OTHER",
        preserve_filename=True,
        source_name="capture_beta.png",
    )
    rows: list[dict[str, str]] = []
    kept = _substitute_client_carriers(
        [fork, same_carrier_base_copy, unrelated_same_pin], rows
    )
    assert fork in kept
    assert unrelated_same_pin in kept
    assert same_carrier_base_copy not in kept
    assert [row["kit_path"] for row in rows] == [path]
