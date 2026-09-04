"""
Tests for Hyper-τ task loading and the HyperTauTask data model.
"""

import pytest

from tau2.hyper.data_model import HyperTauTask
from tau2.hyper.task_loader import (
    HYPER_TAU_TASKS_DIR,
    list_hyper_tau_task_ids,
    load_active_hyper_tau_task,
    load_active_hyper_tau_tasks,
    load_all_hyper_tau_tasks,
    load_hyper_tau_task,
    load_hyper_tau_tasks,
)

ACTIVE_RETAIL_TASK_ID = "008_retail_plus_construction_core_evidence_performance_hard"
ACTIVE_CLIENT_TASK_ID = (
    "004_airline_plus_construction_core_evidence_hard_client_performance_medium"
)
REMOVED_LEGACY_TASK_IDS = {
    "airline_construction_001",
    "airline_construction_response_phrasing_001",
    "airline_construction_core_evidence_bundle_001",
    "airline_construction_core_evidence_bundle_performance_001",
    "retail_construction_001",
    "retail_construction_response_phrasing_001",
    "retail_construction_core_transcript_induction_001",
}
AIRLINE_PLUS_TASK_IDS = {
    "001_airline_plus_construction_core_evidence_all_defects_live_experiment_performance_medium",
    "002_airline_plus_construction_core_evidence_seeded_performance_hard",
    "003_airline_plus_construction_core_evidence_hard_all_defects_performance_easy",
    "004_airline_plus_construction_core_evidence_hard_client_performance_medium",
    "005_airline_plus_construction_core_evidence_hard_client_seeded_all_defects_performance_hard",
    "006_airline_plus_construction_core_evidence_response_phrasing_performance_medium",
}
RETAIL_PLUS_TASK_IDS = {
    "007_retail_plus_construction_core_evidence_seeded_all_defects_performance_easy",
    "008_retail_plus_construction_core_evidence_performance_hard",
    "009_retail_plus_construction_core_evidence_hard_seeded_live_experiment_performance_medium",
    "010_retail_plus_construction_core_evidence_hard_client_all_defects_performance_medium",
    "011_retail_plus_construction_core_evidence_hard_client_all_defects_performance_hard",
    "012_retail_plus_construction_core_evidence_hard_client_all_defects_response_phrasing_performance_hard",
}
# (task id, phrasing rule pack, SOP variant manifest) for every task whose
# composition pipeline layers response phrasing on top of an evidence bundle.
# Release tasks declare the rule pack and the selected rules inline instead of
# forking a separate phrasing task.
RESPONSE_PHRASING_TASKS = (
    (
        "006_airline_plus_construction_core_evidence_response_phrasing_performance_medium",
        "tau2/hyper/response_phrasing/airline_plus_response_phrasing.yaml",
        "tau2/hyper/sops/airline_plus/variants/core_evidence_bundle_001.json",
    ),
    (
        "012_retail_plus_construction_core_evidence_hard_client_all_defects_response_phrasing_performance_hard",
        "tau2/hyper/response_phrasing/retail_plus_response_phrasing.yaml",
        "tau2/hyper/sops/retail_plus/variants/core_evidence_bundle_hard_client_001.json",
    ),
    (
        "018_telecom_construction_core_evidence_hard_client_response_phrasing_performance_medium",
        "tau2/hyper/response_phrasing/telecom_response_phrasing.yaml",
        "tau2/hyper/sops/telecom/variants/core_evidence_bundle_hard_client_001.json",
    ),
    (
        "039_banking_knowledge_construction_client_api_deposit_services_response_phrasing_performance_medium",
        "tau2/hyper/response_phrasing/banking_response_phrasing.yaml",
        "tau2/hyper/sops/banking_knowledge/variants/core_evidence_bundle_001.json",
    ),
    (
        "044_banking_knowledge_construction_client_card_servicing_client_response_phrasing_performance_medium",
        "tau2/hyper/response_phrasing/banking_response_phrasing.yaml",
        "tau2/hyper/sops/banking_knowledge/variants/card_servicing_sections_hard_client_001.json",
    ),
    (
        "053_banking_knowledge_construction_client_debit_security_client_response_phrasing_performance_medium",
        "tau2/hyper/response_phrasing/banking_response_phrasing.yaml",
        "tau2/hyper/sops/banking_knowledge/variants/debit_security_sections_hard_client_001.json",
    ),
)
REMOVED_BANKING_TASK_IDS = {
    "banking_knowledge_construction_business_checking_evidence_corpus_hard_001",
    "banking_knowledge_construction_business_credit_card_evidence_corpus_hard_001",
    "banking_knowledge_construction_business_savings_evidence_corpus_hard_001",
    "banking_knowledge_construction_personal_cc_rewards_evidence_corpus_hard_001",
    "banking_knowledge_construction_client_api_001",
}
# Journey-scoped Banking Client API bundles: evaluation size = the subdomain
# manifest partition minus the ACTION-basis tasks rest mode cannot score
# (task_032/033/035 in card_servicing, task_083 in debit_security).
BANKING_SUBDOMAIN_EVALUATION_SIZES = {
    "deposit_opening": 19,
    "deposit_services": 25,
    "card_selection": 26,
    "card_servicing": 27,
    "business": 20,
    "debit_security": 23,
}

# Super-subdomain slots: each combines three subdomain suites (disjoint
# unions — the six subdomain partitions share no eval tasks). cards =
# card_selection + card_servicing + debit_security; deposits_business =
# deposit_opening + deposit_services + business.
BANKING_SUPER_SUBDOMAIN_EVALUATION_SIZES = {
    "cards_super": 26 + 27 + 23,
    "deposits_business_super": 19 + 25 + 20,
}

BANKING_WHOLE_DOMAIN_EVALUATION_SIZE = 93


class TestHyperTauTaskModel:
    """Tests for the HyperTauTask Pydantic model."""

    def test_create_minimal(self):
        task = HyperTauTask(
            id="test_task",
            source_domain="mock",
            task_description="Build an agent.",
            client_instructions="You are a client.",
            training_task_ids=["1", "2"],
            test_task_ids=["3", "4"],
        )
        assert task.id == "test_task"
        assert task.client_enabled is True

    def test_simulator_seats_are_task_configurable(self):
        task = HyperTauTask(
            id="test_task_seats",
            source_domain="mock",
            task_description="Test",
            client_instructions="You are a client.",
            training_task_ids=["1"],
            test_task_ids=["2"],
            client_llm="gpt-5.5",
            client_reasoning_effort="low",
            user_llm="gpt-5.4",
            user_reasoning_effort="none",
        )
        assert task.client_llm == "gpt-5.5"
        assert task.client_reasoning_effort == "low"
        assert task.hyper.client_llm == "gpt-5.5"

        reloaded = HyperTauTask.model_validate_json(task.model_dump_json())
        assert reloaded.client_llm == "gpt-5.5"
        assert reloaded.client_reasoning_effort == "low"

    def test_simulator_seats_default_to_unset(self):
        task = HyperTauTask(
            id="test_task_seats_unset",
            source_domain="mock",
            task_description="Test",
            client_instructions="You are a client.",
            training_task_ids=["1"],
            test_task_ids=["2"],
        )
        assert task.client_llm is None
        assert task.client_reasoning_effort is None

    def test_serialization_roundtrip(self):
        task = HyperTauTask(
            id="roundtrip_test",
            source_domain="mock",
            task_description="Test",
            client_instructions="You are a client.",
            training_task_ids=["1"],
            test_task_ids=["2"],
        )
        json_str = task.model_dump_json()
        reloaded = HyperTauTask.model_validate_json(json_str)
        assert reloaded.id == task.id
        assert reloaded.task_description == task.task_description

    def test_retired_policy_fields_are_not_part_of_the_model(self):
        task = HyperTauTask(
            id="retired_fields",
            source_domain="mock",
            task_description="Test",
            test_task_ids=["1"],
            base_policy="ignored",
            solution_policy="ignored",
            interaction_mode="meta_tool",
            task_type="deletion",
        )

        assert "base_policy" not in task.hyper.model_dump()
        assert "solution_policy" not in task.hyper.model_dump()
        assert "interaction_mode" not in task.hyper.model_dump()
        assert "task_type" not in task.hyper.model_dump()


class TestTaskLoader:
    """Tests for the task loading functions."""

    def test_tasks_dir_exists(self):
        assert HYPER_TAU_TASKS_DIR.exists(), (
            f"Hyper-τ tasks directory should exist at {HYPER_TAU_TASKS_DIR}"
        )

    def test_load_all_tasks(self):
        tasks = load_all_hyper_tau_tasks()
        assert len(tasks) >= 1
        for task in tasks:
            assert isinstance(task, HyperTauTask)

    def test_load_all_tasks_emits_no_error_logs(self):
        # Non-task scaffolds (e.g. final/solutions/**) must be excluded from
        # the glob, not swept up and error-logged on every startup.
        from loguru import logger

        records: list[str] = []
        sink_id = logger.add(records.append, level="ERROR")
        try:
            load_all_hyper_tau_tasks()
        finally:
            logger.remove(sink_id)
        assert records == []

    def test_maintained_sandbox_tasks_use_wall_clock_without_step_limit(self):
        sandbox_tasks = [
            task for task in load_active_hyper_tau_tasks() if task.sandbox_config
        ]

        assert sandbox_tasks
        for task in sandbox_tasks:
            assert "max_steps" not in task.sandbox_config, task.id
            assert task.sandbox_config["max_time_seconds"] == 8 * 60 * 60, task.id

    def test_service_domains_use_client_rest_boundary(self):
        migrated_domains = {
            "airline_plus",
            "banking_knowledge",
            "retail_plus",
            "telecom",
        }
        tasks = [
            task
            for task in load_active_hyper_tau_tasks()
            if task.source_domain in migrated_domains
        ]

        # The flat release corpus is exactly 53 tasks, and every one of them
        # lives in a migrated service domain.
        assert len(tasks) == 53
        assert all(task.client_api_mode == "rest" for task in tasks)
        assert not any(task.id.endswith("_client_api_001") for task in tasks)
        # Release tasks carry their live-experiment sample inline, so none of
        # them is a partition variant forked off another task.
        assert all(task.live_experiment_source_task_id is None for task in tasks)
        # Seeded slots: one fixed starting workspace per slot, spread across
        # the four domains (airline 002/005, retail 007/009, telecom 013/014,
        # and eight banking slots split across the evidence and client
        # surfaces).
        assert {task.id for task in tasks if task.starting_workspace_path} == {
            "002_airline_plus_construction_core_evidence_seeded_performance_hard",
            "005_airline_plus_construction_core_evidence_hard_client_seeded_all_defects_performance_hard",
            "007_retail_plus_construction_core_evidence_seeded_all_defects_performance_easy",
            "009_retail_plus_construction_core_evidence_hard_seeded_live_experiment_performance_medium",
            "013_telecom_construction_core_evidence_seeded_all_defects_performance_medium",
            "014_telecom_construction_core_evidence_seeded_performance_hard",
            "031_banking_knowledge_construction_client_api_card_selection_seeded_performance_medium",
            "033_banking_knowledge_construction_client_card_selection_client_seeded_performance_hard",
            "037_banking_knowledge_construction_client_deposit_opening_client_seeded_performance_medium",
            "038_banking_knowledge_construction_client_api_deposit_services_seeded_performance_medium",
            "043_banking_knowledge_construction_client_card_servicing_client_seeded_performance_medium",
            "046_banking_knowledge_construction_client_api_business_seeded_performance_medium",
            "051_banking_knowledge_construction_client_api_debit_security_seeded_performance_hard",
            "052_banking_knowledge_construction_client_debit_security_client_seeded_performance_medium",
        }
        assert {task.id for task in tasks if task.client_sections is not None} == {
            "004_airline_plus_construction_core_evidence_hard_client_performance_medium",
            "005_airline_plus_construction_core_evidence_hard_client_seeded_all_defects_performance_hard",
            "010_retail_plus_construction_core_evidence_hard_client_all_defects_performance_medium",
            "011_retail_plus_construction_core_evidence_hard_client_all_defects_performance_hard",
            "012_retail_plus_construction_core_evidence_hard_client_all_defects_response_phrasing_performance_hard",
            "016_telecom_construction_core_evidence_hard_client_all_defects_performance_easy",
            "017_telecom_construction_core_evidence_hard_client_live_experiment_performance_hard",
            "018_telecom_construction_core_evidence_hard_client_response_phrasing_performance_medium",
            # Banking subdomain block (030-053): the client-surface slots,
            # plain and seeded; the evidence-surface slots carry no
            # client_sections.
            "032_banking_knowledge_construction_client_card_selection_client_performance_hard",
            "033_banking_knowledge_construction_client_card_selection_client_seeded_performance_hard",
            "036_banking_knowledge_construction_client_deposit_opening_client",
            "037_banking_knowledge_construction_client_deposit_opening_client_seeded_performance_medium",
            "041_banking_knowledge_construction_client_deposit_services_client_performance_hard",
            "043_banking_knowledge_construction_client_card_servicing_client_seeded_performance_medium",
            "044_banking_knowledge_construction_client_card_servicing_client_response_phrasing_performance_medium",
            "045_banking_knowledge_construction_client_card_servicing_client_performance_hard",
            "048_banking_knowledge_construction_client_business_client",
            "049_banking_knowledge_construction_client_business_client_performance_hard",
            "052_banking_knowledge_construction_client_debit_security_client_seeded_performance_medium",
            "053_banking_knowledge_construction_client_debit_security_client_response_phrasing_performance_medium",
        }

    def test_load_retail_tasks(self):
        tasks = load_hyper_tau_tasks(source_domain="retail_plus")
        assert len(tasks) >= 1
        for task in tasks:
            assert task.source_domain == "retail_plus"

    def test_load_nonexistent_domain(self):
        tasks = load_hyper_tau_tasks(source_domain="nonexistent")
        assert tasks == []

    def test_list_task_ids(self):
        ids = list_hyper_tau_task_ids()
        assert len(ids) >= 1
        assert ACTIVE_RETAIL_TASK_ID in ids

    def test_list_task_ids_by_domain(self):
        ids = list_hyper_tau_task_ids(source_domain="retail_plus")
        assert ACTIVE_RETAIL_TASK_ID in ids

        ids_other = list_hyper_tau_task_ids(source_domain="airline_plus")
        assert ACTIVE_RETAIL_TASK_ID not in ids_other

    def test_load_specific_task(self):
        task = load_hyper_tau_task(ACTIVE_RETAIL_TASK_ID)
        assert task.id == ACTIVE_RETAIL_TASK_ID
        assert task.source_domain == "retail_plus"

    def test_load_nonexistent_task(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_hyper_tau_task("nonexistent_task_id")

    def test_active_task_discovery_hides_frozen_airline_and_retail(self):
        tasks = load_active_hyper_tau_tasks()
        assert tasks
        assert {task.source_domain for task in tasks}.isdisjoint({"airline", "retail"})

    def test_removed_legacy_tasks_are_not_loadable_even_with_opt_in(self):
        for task_id in REMOVED_LEGACY_TASK_IDS:
            with pytest.raises(FileNotFoundError, match="not found"):
                load_active_hyper_tau_task(task_id, allow_legacy=True)

    def test_every_removed_task_has_a_plus_replacement(self):
        tasks = {task.id: task for task in load_all_hyper_tau_tasks()}
        assert REMOVED_LEGACY_TASK_IDS.isdisjoint(tasks)
        assert AIRLINE_PLUS_TASK_IDS | RETAIL_PLUS_TASK_IDS <= tasks.keys()

        for task_id in AIRLINE_PLUS_TASK_IDS:
            task = tasks[task_id]
            assert task.source_domain == "airline_plus"
            assert task.test_task_ids == [str(index) for index in range(67)]
        for task_id in RETAIL_PLUS_TASK_IDS:
            task = tasks[task_id]
            assert task.source_domain == "retail_plus"
            assert task.test_task_ids == [str(index) for index in range(134)]

    def test_core_evidence_bundle_tasks_compose_response_phrasing(self):
        for task_id, rules_path, manifest_path in RESPONSE_PHRASING_TASKS:
            task = load_active_hyper_tau_task(task_id)
            assert task.sop_variant_manifest_path == manifest_path
            assert task.response_phrasing_rules_path == rules_path
            assert task.composition_pipeline[0]["stage"] == "response_phrasing"
            assert task.composition_pipeline[0]["selected_rule_ids"]
            assert task.composition_pipeline[1]["stage"] == "information_distribution"
            assert (
                task.composition_pipeline[1]["variant_manifest_path"] == manifest_path
            )

    def test_removed_banking_section_tasks_are_not_discoverable(self):
        task_ids = {task.id for task in load_active_hyper_tau_tasks()}
        assert REMOVED_BANKING_TASK_IDS.isdisjoint(task_ids)
        for task_id in REMOVED_BANKING_TASK_IDS:
            with pytest.raises(FileNotFoundError, match="not found"):
                load_active_hyper_tau_task(task_id)

    def test_banking_tasks_use_client_rest_and_exclude_wrapper_action_rewards(self):
        tasks = [
            task
            for task in load_active_hyper_tau_tasks()
            if task.source_domain == "banking_knowledge"
        ]

        # 24 subdomain slots (four per subdomain), six super-subdomain slots
        # (an Easy/Medium/Hard trio each), and five whole-domain slots.
        assert len(tasks) == 35
        assert all(task.client_api_mode == "rest" for task in tasks)
        subdomain_sizes = BANKING_SUBDOMAIN_EVALUATION_SIZES
        super_sizes = BANKING_SUPER_SUBDOMAIN_EVALUATION_SIZES
        subdomain_tasks: dict[str, list] = {name: [] for name in subdomain_sizes}
        super_subdomain_tasks: dict[str, list] = {name: [] for name in super_sizes}
        full_domain_tasks = []
        for task in tasks:
            # Super-subdomains are matched first: their ids embed a member
            # subdomain's name (deposits_business_super contains business).
            super_name = next((name for name in super_sizes if name in task.id), None)
            if super_name is not None:
                super_subdomain_tasks[super_name].append(task)
                continue
            subdomain = next(
                (name for name in subdomain_sizes if name in task.id), None
            )
            if subdomain is not None:
                subdomain_tasks[subdomain].append(task)
            else:
                full_domain_tasks.append(task)
        # Every subdomain ships four slots split across the evidence and
        # client surfaces; the block rotates which of them carry the vetted
        # seeded trees, but all four score the subdomain's whole partition.
        for subdomain, expected_size in subdomain_sizes.items():
            bundle_tasks = subdomain_tasks[subdomain]
            assert len(bundle_tasks) == 4, subdomain
            assert all(
                len(task.test_task_ids) == expected_size for task in bundle_tasks
            ), subdomain
        for super_name, expected_size in super_sizes.items():
            group = super_subdomain_tasks[super_name]
            assert len(group) == 3, super_name
            assert all(len(task.test_task_ids) == expected_size for task in group), (
                super_name
            )
        # Union, not sum: release live-experiment slots keep their sample in
        # the scored suite, so every whole-domain slot covers all 93 tasks.
        assert len(full_domain_tasks) == 5
        assert all(
            len(set(task.test_task_ids) | set(task.live_experiment_task_ids))
            == BANKING_WHOLE_DOMAIN_EVALUATION_SIZE
            for task in full_domain_tasks
        )
        removed_action_tasks = {"task_032", "task_033", "task_035", "task_083"}
        assert all(
            removed_action_tasks.isdisjoint(task.test_task_ids) for task in tasks
        )
        assert not any(task.id.endswith("_client_api_001") for task in tasks)

    def test_active_task_not_found_message_does_not_advertise_legacy_tasks(self):
        with pytest.raises(FileNotFoundError) as error:
            load_active_hyper_tau_task("nonexistent_task_id")
        assert "retail_construction_001" not in str(error.value)


class TestClientSimulatorWithTaskInstructions:
    """Test that ClientSimulator uses client_instructions as system prompt."""

    def test_instructions_become_system_prompt(self):
        from tau2.hyper.client import ClientSimulator
        from tau2.hyper.client_sim.instructions import (
            resolve_task_client_instructions,
        )

        # Release tasks define the Client persona through ``client_sections``,
        # which renders into the brief the simulator runs on.
        task = load_hyper_tau_task(ACTIVE_CLIENT_TASK_ID)
        instructions = resolve_task_client_instructions(task)
        client = ClientSimulator(
            llm="gpt-4.1-mini",
            client_instructions=instructions,
        )

        assert instructions
        assert client.system_prompt == instructions

    def test_init_state_has_instructions_as_system_message(self):
        from tau2.hyper.client import ClientSimulator

        instructions = "You are a test client. Be helpful."
        client = ClientSimulator(
            llm="gpt-4.1-mini",
            client_instructions=instructions,
        )
        state = client.get_init_state()
        assert state.system_messages[0].content == instructions
