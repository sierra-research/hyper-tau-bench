from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from tau2.data_model.message import AssistantMessage
from tau2.hyper.data_model import (
    CreditPerformanceRequirement,
    HyperTauTask,
    LatencyPerformanceRequirement,
)
from tau2.hyper.performance import (
    evaluate_performance_requirements,
    format_credit_summary,
    parse_performance_requirement,
)
from tau2.hyper.performance_profiles import (
    BUCKET_CREDIT_RATES,
    MODEL_BUCKETS,
    PRICING_BASIS,
    RATE_CARD_DATE,
    get_performance_profile,
    get_primary_model_config,
)
from tau2.hyper.task_loader import load_active_hyper_tau_tasks, load_hyper_tau_task
from tau2.orchestrator.orchestrator import Orchestrator


def _bucket_rates(bucket):
    return {
        **BUCKET_CREDIT_RATES[bucket],
        "rate_card_date": RATE_CARD_DATE,
        "pricing_basis": PRICING_BASIS,
    }


EASY_BUCKET_RATES = _bucket_rates("easy")
MEDIUM_BUCKET_RATES = _bucket_rates("medium")
HARD_BUCKET_RATES = _bucket_rates("hard")


def test_agent_turn_timing_and_suite_level_latency_gate(monkeypatch):
    class FakeAgent:
        def generate_next_message(self, message, state):
            return AssistantMessage(role="assistant", content="done"), state

    orchestrator = object.__new__(Orchestrator)
    orchestrator.agent = FakeAgent()
    orchestrator.agent_state = SimpleNamespace()
    clock = iter([10.0, 12.5])
    monkeypatch.setattr(
        "tau2.orchestrator.orchestrator.time.perf_counter", lambda: next(clock)
    )

    measured, _ = orchestrator._generate_agent_message(None)
    assert measured.agent_turn_latency_seconds == 2.5
    measured.agent_turn_latency_seconds = 1.0
    messages = [
        measured,
        AssistantMessage(
            role="assistant", content="two", agent_turn_latency_seconds=2.0
        ),
        AssistantMessage(
            role="assistant", content="three", agent_turn_latency_seconds=3.0
        ),
        AssistantMessage(
            role="assistant", content="four", agent_turn_latency_seconds=4.0
        ),
        AssistantMessage(
            role="assistant", content="five", agent_turn_latency_seconds=5.0
        ),
    ]
    requirements = [
        LatencyPerformanceRequirement(id="p50", percentile=50, max_seconds=3.0),
        LatencyPerformanceRequirement(id="p90", percentile=90, max_seconds=4.0),
    ]

    result = evaluate_performance_requirements(requirements, messages)

    assert result["summary"] == {
        "sample_count": 5,
        "p50_seconds": 3.0,
        "p90_seconds": 4.6,
        "max_seconds": 5.0,
    }
    assert [detail["met"] for detail in result["requirements"]] == [True, False]
    assert result["reward"] == 0.0


def test_latency_requirement_rejects_unsupported_percentile():
    with pytest.raises(ValidationError):
        LatencyPerformanceRequirement(id="p95", percentile=95, max_seconds=5.0)


def test_credit_budget_uses_set_wide_mean_overage():
    requirement = CreditPerformanceRequirement(id="budget", budget=1.0)
    result = evaluate_performance_requirements(
        [requirement],
        [],
        [
            {"total_credits": 0.8},
            {"total_credits": 1.2},
            {"total_credits": 3.0},
            None,
        ],
    )

    assert result["penalty"] == pytest.approx(0.25)
    assert result["credit_summary"] == {
        "sample_count": 4,
        "mean_credits": pytest.approx(1.25),
        "budget": 1.0,
    }
    assert result["requirements"][0]["mean_overage"] == pytest.approx(0.25)
    assert format_credit_summary(result["credit_summary"]) == (
        "Agent model credits: mean=1.2500, budget=1.0000 — over budget by 25.0%"
    )


def test_credit_budget_does_not_penalize_outlier_below_set_wide_mean_budget():
    requirement = CreditPerformanceRequirement(id="budget", budget=1.0)
    result = evaluate_performance_requirements(
        [requirement],
        [],
        [
            {"total_credits": 0.1},
            {"total_credits": 0.1},
            {"total_credits": 2.0},
        ],
    )

    assert result["credit_summary"]["mean_credits"] == pytest.approx(2.2 / 3)
    assert result["penalty"] == 0.0
    assert result["requirements"][0]["mean_overage"] == 0.0
    assert result["requirements"][0]["met"] is True


def test_named_credit_profile_expands_models_rates_and_domain_budget():
    task = HyperTauTask(
        id="profile_test",
        source_domain="airline_plus",
        task_description="test",
        client_instructions="",
        training_task_ids=[],
        test_task_ids=["1"],
        performance_profile="hard",
    )

    assert task.performance_profile == "hard"
    assert task.performance_requirements[0].budget == pytest.approx(0.0067)
    assert {config["model"] for config in task.allowed_agent_models} == {
        "gpt-5.6-luna",
        "anthropic/claude-haiku-4-5",
        "gpt-5.4-nano",
        "qwen/qwen3-30b-a3b-instruct-2507",
        "google/gemma-4-26b-a4b-it",
        "gpt-4.1-mini",
    }
    assert all("credit_rates" in config for config in task.allowed_agent_models)


def test_telecom_medium_moves_gpt5_mini_into_pool():
    configs, budget = get_performance_profile("medium", "telecom")
    configs_by_model = {config["model"]: config for config in configs}

    assert budget == pytest.approx(0.056)
    assert set(configs_by_model) == {
        "gpt-5-mini",
        "anthropic/claude-sonnet-5",
        "gpt-5.6-luna",
        "anthropic/claude-haiku-4-5",
        "google/gemini-3-flash-preview",
        "qwen/qwen3.8-27b",
        "google/gemma-4-31b-it",
    }
    # A model bills at its home bucket wherever it is offered: gpt-5-mini is
    # a Hard-bucket model inside the Medium pool.
    assert configs_by_model["gpt-5-mini"]["constraints"] == {"reasoning_effort": "low"}
    assert configs_by_model["gpt-5-mini"]["credit_rates"] == HARD_BUCKET_RATES
    assert configs_by_model["anthropic/claude-sonnet-5"]["constraints"] == {
        "extra_body": {"thinking": {"type": "disabled"}}
    }
    assert configs_by_model["anthropic/claude-sonnet-5"]["credit_rates"] == (
        MEDIUM_BUCKET_RATES
    )
    assert configs_by_model["qwen/qwen3.8-27b"] == {
        "model": "qwen/qwen3.8-27b",
        "constraints": {"extra_body": {"reasoning": {"enabled": False}}},
        "credit_rates": MEDIUM_BUCKET_RATES,
    }
    assert configs_by_model["google/gemma-4-31b-it"] == {
        "model": "google/gemma-4-31b-it",
        "constraints": {"extra_body": {"reasoning": {"effort": "low"}}},
        "credit_rates": MEDIUM_BUCKET_RATES,
    }


@pytest.mark.parametrize(
    ("profile", "domain", "excluded_models", "new_provider_candidates"),
    [
        (
            "medium",
            "airline_plus",
            {
                "anthropic/claude-sonnet-5",
                "moonshotai/kimi-k2.6",
            },
            {"anthropic/claude-haiku-4-5"},
        ),
        (
            "hard",
            "airline_plus",
            {
                "google/gemini-3.1-flash-lite",
                "google/gemini-3-flash-preview",
                "moonshotai/kimi-k2.6",
            },
            {"google/gemma-4-26b-a4b-it"},
        ),
        (
            "medium",
            "retail_plus",
            {
                "anthropic/claude-sonnet-5",
                "google/gemini-3-flash-preview",
                "google/gemma-4-31b-it",
            },
            {"anthropic/claude-haiku-4-5"},
        ),
        (
            "hard",
            "retail_plus",
            {
                "gpt-4.1-mini",
                "gpt-5.6-luna",
                "anthropic/claude-haiku-4-5",
                "google/gemini-3.1-flash-lite",
                "google/gemini-3-flash-preview",
                "moonshotai/kimi-k2.6",
            },
            {"gpt-4o-mini"},
        ),
        (
            "medium",
            "telecom",
            {
                "gpt-5.6-terra",
                "moonshotai/kimi-k2.6",
            },
            {"gpt-5-mini"},
        ),
        (
            "hard",
            "telecom",
            {
                "gpt-5-mini",
                "google/gemini-3-flash-preview",
                "moonshotai/kimi-k2.6",
            },
            {"gpt-5.6-terra", "google/gemini-3.1-flash-lite"},
        ),
    ],
)
def test_domain_score_cutoffs_remove_models_and_leave_next_provider_candidate(
    profile,
    domain,
    excluded_models,
    new_provider_candidates,
):
    configs, _ = get_performance_profile(profile, domain)
    models = {config["model"] for config in configs}

    assert models.isdisjoint(excluded_models)
    assert new_provider_candidates <= models


@pytest.mark.parametrize(
    "domain",
    ["airline_plus", "retail_plus", "telecom", "banking_knowledge"],
)
def test_easy_profile_leaves_reasoning_unconstrained(domain):
    configs, _ = get_performance_profile("easy", domain)
    configs_by_model = {config["model"]: config for config in configs}

    assert set(configs_by_model) == {
        "gpt-5.6-sol",
        "anthropic/claude-opus-5",
        "google/gemini-3.1-pro-preview",
        "moonshotai/kimi-k3",
        "deepseek/deepseek-v4-flash",
    }
    # No pinned thinking configuration on any Easy entry: pinning the top
    # settings would tell the Developer which configuration wins.
    assert all(config["constraints"] == {} for config in configs_by_model.values())
    # The Easy-bucket flat rate is precisely the outlier fix: deepseek's list
    # price is ~35x below its bucket peers, but it bills like an Easy model.
    assert configs_by_model["deepseek/deepseek-v4-flash"] == {
        "model": "deepseek/deepseek-v4-flash",
        "constraints": {},
        "credit_rates": EASY_BUCKET_RATES,
    }


def test_easy_profile_banking_budget():
    _, banking_budget = get_performance_profile("easy", "banking_knowledge")

    assert banking_budget == pytest.approx(3.7)


@pytest.mark.parametrize(
    ("domain", "expected_additions"),
    [
        (
            "airline_plus",
            {
                "qwen/qwen3-30b-a3b-instruct-2507",
                "google/gemma-4-26b-a4b-it",
                "gpt-4.1-mini",
            },
        ),
        (
            "retail_plus",
            {
                "qwen/qwen3-30b-a3b-instruct-2507",
                "gpt-4o-mini",
            },
        ),
        (
            "telecom",
            {
                "google/gemma-4-26b-a4b-it",
                "gpt-4.1-mini",
                "gpt-5.6-terra",
            },
        ),
        (
            "banking_knowledge",
            {
                "qwen/qwen3.6-27b",
                "stepfun/step-3.7-flash",
            },
        ),
    ],
)
def test_hard_profile_uses_domain_specific_model_additions(
    domain,
    expected_additions,
):
    configs, _ = get_performance_profile("hard", domain)
    models = {config["model"] for config in configs}
    shared_models = {
        "gpt-5.6-luna",
        "anthropic/claude-haiku-4-5",
        "google/gemini-3-flash-preview",
        "moonshotai/kimi-k2.6",
        "gpt-5.4-nano",
        "google/gemini-3.1-flash-lite",
    }
    if domain == "airline_plus":
        shared_models -= {
            "google/gemini-3.1-flash-lite",
            "google/gemini-3-flash-preview",
            "moonshotai/kimi-k2.6",
        }
    elif domain == "retail_plus":
        shared_models -= {
            "gpt-5.6-luna",
            "anthropic/claude-haiku-4-5",
            "google/gemini-3.1-flash-lite",
            "google/gemini-3-flash-preview",
            "moonshotai/kimi-k2.6",
        }
    elif domain == "telecom":
        shared_models -= {
            "google/gemini-3-flash-preview",
            "moonshotai/kimi-k2.6",
        }

    assert models == shared_models | expected_additions


@pytest.mark.parametrize(
    ("profile", "domain", "expected_model"),
    [
        ("easy", "airline_plus", "deepseek/deepseek-v4-flash"),
        ("medium", "airline_plus", "qwen/qwen3.8-27b"),
        ("hard", "airline_plus", "google/gemma-4-26b-a4b-it"),
        ("easy", "retail_plus", "deepseek/deepseek-v4-flash"),
        ("medium", "retail_plus", "qwen/qwen3.8-27b"),
        (
            "hard",
            "retail_plus",
            "qwen/qwen3-30b-a3b-instruct-2507",
        ),
        ("easy", "telecom", "deepseek/deepseek-v4-flash"),
        ("medium", "telecom", "qwen/qwen3.8-27b"),
        ("hard", "telecom", "google/gemma-4-26b-a4b-it"),
        ("easy", "banking_knowledge", "moonshotai/kimi-k3"),
        ("medium", "banking_knowledge", "qwen/qwen3.8-27b"),
        ("hard", "banking_knowledge", "qwen/qwen3.6-27b"),
    ],
)
def test_primary_model_is_in_its_profile(profile, domain, expected_model):
    primary = get_primary_model_config(profile, domain)
    configs, _ = get_performance_profile(profile, domain)

    assert primary["model"] == expected_model
    assert primary in configs


def test_primary_model_config_is_an_independent_copy():
    primary = get_primary_model_config("medium", "telecom")
    primary["constraints"]["mutated"] = True

    fresh = get_primary_model_config("medium", "telecom")

    assert "mutated" not in fresh["constraints"]


def test_every_active_named_profile_bundle_has_a_primary_model():
    tasks = load_active_hyper_tau_tasks()

    for task in tasks:
        if not isinstance(task.performance_profile, str):
            continue
        primary = get_primary_model_config(
            task.performance_profile,
            task.source_domain,
        )
        assert primary in task.allowed_agent_models


@pytest.mark.parametrize(
    ("profile", "domain", "model", "constraints", "bucket_rates"),
    [
        (
            "hard",
            "airline_plus",
            "qwen/qwen3-30b-a3b-instruct-2507",
            {},
            HARD_BUCKET_RATES,
        ),
        (
            "hard",
            "airline_plus",
            "google/gemma-4-26b-a4b-it",
            {"extra_body": {"reasoning": {"enabled": False}}},
            HARD_BUCKET_RATES,
        ),
        ("hard", "airline_plus", "gpt-4.1-mini", {}, HARD_BUCKET_RATES),
        ("hard", "retail_plus", "gpt-4o-mini", {}, HARD_BUCKET_RATES),
        (
            "medium",
            "telecom",
            "gpt-5-mini",
            {"reasoning_effort": "low"},
            HARD_BUCKET_RATES,
        ),
        # Home-bucket billing in the other direction: a Medium-bucket model
        # offered in a Hard pool keeps the Medium rate.
        (
            "hard",
            "telecom",
            "gpt-5.6-terra",
            {"reasoning_effort": "none"},
            MEDIUM_BUCKET_RATES,
        ),
        (
            "hard",
            "banking_knowledge",
            "qwen/qwen3.6-27b",
            # Thinking pinned OFF 2026-08-26 (tier-ordering inversion; see
            # the model definition in performance_profiles.py).
            {"extra_body": {"reasoning": {"enabled": False}}},
            HARD_BUCKET_RATES,
        ),
        (
            "hard",
            "banking_knowledge",
            "stepfun/step-3.7-flash",
            {"reasoning_effort": "medium"},
            HARD_BUCKET_RATES,
        ),
    ],
)
def test_hard_domain_model_addition_configs(
    profile,
    domain,
    model,
    constraints,
    bucket_rates,
):
    configs, _ = get_performance_profile(profile, domain)
    config = {config["model"]: config for config in configs}[model]

    assert config == {
        "model": model,
        "constraints": constraints,
        "credit_rates": bucket_rates,
    }


@pytest.mark.parametrize(
    ("task_id", "tier", "budget"),
    [
        # One slot per (domain, tier) cell. Budgets are the ceiling-derived
        # caps carried on the task's tier spec, not the stock formula caps.
        (
            "003_airline_plus_construction_core_evidence_hard_all_defects_performance_easy",
            "easy",
            0.30,
        ),
        (
            "001_airline_plus_construction_core_evidence_all_defects_live_experiment_performance_medium",
            "medium",
            0.061,
        ),
        (
            "002_airline_plus_construction_core_evidence_seeded_performance_hard",
            "hard",
            0.022,
        ),
        (
            "007_retail_plus_construction_core_evidence_seeded_all_defects_performance_easy",
            "easy",
            0.32,
        ),
        (
            "009_retail_plus_construction_core_evidence_hard_seeded_live_experiment_performance_medium",
            "medium",
            0.082,
        ),
        ("008_retail_plus_construction_core_evidence_performance_hard", "hard", 0.032),
        (
            "016_telecom_construction_core_evidence_hard_client_all_defects_performance_easy",
            "easy",
            0.76,
        ),
        (
            "013_telecom_construction_core_evidence_seeded_all_defects_performance_medium",
            "medium",
            0.054,
        ),
        (
            "014_telecom_construction_core_evidence_seeded_performance_hard",
            "hard",
            0.036,
        ),
        ("030_banking_knowledge_construction_client_api_card_selection", "easy", 0.80),
        ("022_banking_knowledge_construction_kb_performance_medium", "medium", 0.55),
        ("023_banking_knowledge_construction_kb_performance_hard", "hard", 0.46),
    ],
)
def test_tasks_select_credit_performance_profiles(task_id, tier, budget):
    task = load_hyper_tau_task(task_id)

    assert set(task.performance_profile) == {tier}
    assert len(task.performance_requirements) == 1
    requirement = task.performance_requirements[0]
    assert requirement.id == f"{tier}_agent_credit_budget"
    assert requirement.tier == tier
    assert requirement.budget == pytest.approx(budget)
    assert task.allowed_agent_models
    assert all("credit_rates" in config for config in task.allowed_agent_models)
    assert all(config["tier"] == tier for config in task.allowed_agent_models)


# --- Tier-spec profiles (list and dict performance_profile forms) -----------


def _tier_task(performance_profile, source_domain="banking_knowledge"):
    return HyperTauTask(
        id="tier_spec_test",
        source_domain=source_domain,
        task_description="test",
        client_instructions="",
        training_task_ids=[],
        test_task_ids=["1"],
        performance_profile=performance_profile,
    )


def test_string_profile_lowering_is_unchanged_by_tier_specs():
    task = _tier_task("easy")

    requirement = task.performance_requirements[0]
    assert requirement == CreditPerformanceRequirement(
        id="easy_agent_credit_budget",
        budget=3.7,
    )
    assert requirement.tier is None
    assert requirement.models is None
    assert all("tier" not in config for config in task.allowed_agent_models)


def test_list_profile_activates_multiple_stock_tiers():
    task = _tier_task(["easy", "medium"], source_domain="telecom")
    stock_easy, easy_budget = get_performance_profile("easy", "telecom")
    stock_medium, medium_budget = get_performance_profile("medium", "telecom")

    easy_names = [config["model"] for config in stock_easy]
    owners = {config["model"]: config["tier"] for config in task.allowed_agent_models}
    assert set(owners) == set(easy_names) | {config["model"] for config in stock_medium}
    assert all(owners[name] == "easy" for name in easy_names)

    requirements = task.performance_requirements
    assert [requirement.tier for requirement in requirements] == ["easy", "medium"]
    assert requirements[0].budget == pytest.approx(easy_budget)
    assert requirements[1].budget == pytest.approx(medium_budget)
    assert sorted(requirements[0].models) == sorted(easy_names)
    # Models present in both tiers are owned (and metered) by the higher one.
    assert set(requirements[1].models).isdisjoint(easy_names)


def test_tier_budget_override_and_stock_pool():
    task = _tier_task({"easy": {"budget": 2.5}})
    stock_easy, _ = get_performance_profile("easy", "banking_knowledge")

    assert task.performance_requirements[0].budget == pytest.approx(2.5)
    assert [config["model"] for config in task.allowed_agent_models] == [
        config["model"] for config in stock_easy
    ]
    # Stock pools keep their frozen constraints (Easy pins none since
    # 2026-08-27: the Developer picks any thinking configuration).
    sol = next(
        config
        for config in task.allowed_agent_models
        if config["model"] == "gpt-5.6-sol"
    )
    assert sol["constraints"] == {}


def test_null_tier_budget_removes_the_credit_requirement():
    task = _tier_task(
        {"easy": {"budget": None, "models": ["gpt-5.6-sol"]}},
    )

    assert task.performance_requirements == []
    assert [config["model"] for config in task.allowed_agent_models] == ["gpt-5.6-sol"]


def test_bare_model_name_leaves_thinking_configuration_to_the_developer():
    task = _tier_task({"easy": {"models": ["gpt-5.6-sol"]}})

    sol = task.allowed_agent_models[0]
    assert sol["constraints"] == {}
    assert sol["credit_rates"]["input_per_million"] == pytest.approx(3.0)
    assert task.performance_requirements[0].budget == pytest.approx(3.7)
    assert task.performance_requirements[0].models == ["gpt-5.6-sol"]


def test_model_entry_object_pins_constraints():
    task = _tier_task(
        {
            "easy": {
                "models": [
                    {
                        "model": "gpt-5.6-sol",
                        "constraints": {"reasoning_effort": "xhigh"},
                    }
                ]
            }
        },
    )

    sol = task.allowed_agent_models[0]
    assert sol["constraints"] == {"reasoning_effort": "xhigh"}
    assert sol["tier"] == "easy"


def test_model_entry_can_offer_a_bounded_choice_of_settings():
    task = _tier_task(
        {
            "easy": {
                "models": [
                    {
                        "model": "gpt-5.6-sol",
                        "constraints": {
                            "reasoning_effort": {"one_of": ["high", "medium"]}
                        },
                    }
                ]
            }
        },
    )

    sol = task.allowed_agent_models[0]
    assert sol["constraints"] == {"reasoning_effort": {"one_of": ["high", "medium"]}}
    # One model is still one metering unit: credits bucket by model name.
    assert task.performance_requirements[0].models == ["gpt-5.6-sol"]
    assert task.performance_requirements[0].budget == pytest.approx(3.7)


@pytest.mark.parametrize(
    "choice,message",
    [
        ({"one_of": ["high"]}, "at least two"),
        ({"one_of": []}, "at least two"),
        ({"one_of": "high"}, "at least two"),
        ({"one_of": ["high", "high"]}, "repeats a"),
        ({"one_of": ["high", "medium"], "extra": 1}, "mixes"),
    ],
)
def test_malformed_choices_are_rejected_at_authoring_time(choice, message):
    with pytest.raises(ValidationError, match=message):
        _tier_task(
            {
                "easy": {
                    "models": [
                        {
                            "model": "gpt-5.6-sol",
                            "constraints": {"reasoning_effort": choice},
                        }
                    ]
                }
            },
        )


def test_unknown_model_requires_inline_credit_rates_when_budgeted():
    with pytest.raises(ValidationError, match="credit_rates"):
        _tier_task({"easy": {"models": [{"model": "acme/novel-model"}]}})

    task = _tier_task(
        {"easy": {"budget": None, "models": [{"model": "acme/novel-model"}]}},
    )
    assert task.allowed_agent_models[0]["model"] == "acme/novel-model"
    assert task.performance_requirements == []


def test_tier_spec_rejects_unknown_tiers_keys_and_duplicates():
    with pytest.raises(ValidationError, match="Unknown performance tiers"):
        _tier_task({"frontier": {}})
    with pytest.raises(ValidationError, match="unknown override keys"):
        _tier_task({"easy": {"budgets": 1.0}})
    with pytest.raises(ValidationError, match="lists a tier twice"):
        _tier_task(["easy", "easy"])
    with pytest.raises(ValidationError, match="lists a model twice"):
        _tier_task({"easy": {"models": ["gpt-5.6-sol", "gpt-5.6-sol"]}})


def test_scoped_credit_requirements_meter_only_their_tier_models():
    requirements = [
        CreditPerformanceRequirement(
            id="easy_agent_credit_budget",
            budget=1.0,
            tier="easy",
            models=["sol"],
        ),
        CreditPerformanceRequirement(
            id="medium_agent_credit_budget",
            budget=0.1,
            tier="medium",
            models=["luna"],
        ),
    ]
    usages = [
        {
            "total_credits": 1.7,
            "by_model": {"sol": {"credits": 1.5}, "luna": {"credits": 0.2}},
        },
        {"total_credits": 0.9, "by_model": {"sol": {"credits": 0.9}}},
    ]

    result = evaluate_performance_requirements(requirements, [], usages)

    # easy mean = (1.5 + 0.9) / 2 -> 20% over; medium mean = 0.1 -> at budget.
    assert result["penalty"] == pytest.approx(0.2)
    assert result["requirements"][0]["tier"] == "easy"
    assert result["requirements"][0]["mean_credits"] == pytest.approx(1.2)
    assert result["requirements"][1]["met"] is True
    assert result["credit_summary"]["budget"] is None
    assert result["credit_summary"]["mean_credits"] == pytest.approx(1.3)
    assert [entry["id"] for entry in result["credit_summary"]["budgets"]] == [
        "easy_agent_credit_budget",
        "medium_agent_credit_budget",
    ]
    rendered = format_credit_summary(result["credit_summary"])
    assert (
        "easy_agent_credit_budget: mean=1.2000, budget=1.0000 — over budget by 20.0%"
    ) in rendered
    assert "medium_agent_credit_budget: mean=0.1000, budget=0.1000" in rendered


def test_multi_budget_summary_needs_no_tier_field():
    """The kit strips ``tier`` from developer-facing requirements, so the
    ``run_local_test`` path parses tier-less credit requirements from
    ``framework/deployment_manifest.json``; per-budget feedback must not
    depend on it."""
    requirements = [
        parse_performance_requirement(
            {
                "id": "agent_credit_budget_1",
                "type": "credits",
                "budget": 1.0,
                "models": ["sol"],
            }
        ),
        parse_performance_requirement(
            {
                "id": "agent_credit_budget_2",
                "type": "credits",
                "budget": 0.1,
                "models": ["luna"],
            }
        ),
    ]
    usages = [
        {
            "total_credits": 1.7,
            "by_model": {"sol": {"credits": 1.5}, "luna": {"credits": 0.2}},
        },
        {"total_credits": 0.9, "by_model": {"sol": {"credits": 0.9}}},
    ]

    result = evaluate_performance_requirements(requirements, [], usages)

    assert result["penalty"] == pytest.approx(0.2)
    assert "tier" not in result["requirements"][0]
    rendered = format_credit_summary(result["credit_summary"])
    assert (
        "agent_credit_budget_1: mean=1.2000, budget=1.0000 — over budget by 20.0%"
    ) in rendered
    assert "agent_credit_budget_2: mean=0.1000, budget=0.1000" in rendered


def test_scoped_requirement_falls_back_to_totals_for_legacy_usages():
    requirement = CreditPerformanceRequirement(
        id="easy_agent_credit_budget",
        budget=1.0,
        tier="easy",
        models=["sol"],
    )

    result = evaluate_performance_requirements(
        [requirement],
        [],
        [{"total_credits": 1.5}, None],
    )

    assert result["requirements"][0]["mean_credits"] == pytest.approx(0.75)
    assert result["penalty"] == 0.0


# The shared plus-domain open roster (Ben, 2026-08-28): the union of every
# fenced airline/retail/telecom tier menu — the retired all-models family's
# 15-entry roster (union of the three airline tier menus) plus retail's
# kimi-k2.6 and gpt-4o-mini seats and telecom's Sonnet 5, gpt-5-mini, and
# gemini-3.1-flash-lite seats. Each entry keeps its source menu's pinned
# form (easy seats unconstrained, medium/hard seats keep their stock
# reasoning pins); tier separation is enforced by the ceiling-derived
# budgets plus the cheap seats' load-bearing pins, not by menu fencing.
# Entries are (model, constraints, home bucket); the three Anthropic seats
# run the OpenRouter transport (direct access is retired org-side) and are
# absent from MODEL_BUCKETS, so every bucket is spelled out.
_OPEN_ROSTER = [
    ("gpt-5.6-sol", {}, "easy"),
    ("anthropic/claude-opus-5", {}, "easy"),
    ("google/gemini-3.1-pro-preview", {}, "easy"),
    ("moonshotai/kimi-k3", {}, "easy"),
    ("deepseek/deepseek-v4-flash", {}, "easy"),
    ("gpt-5.6-terra", {"reasoning_effort": "none"}, "medium"),
    ("gpt-5.6-luna", {"reasoning_effort": "none"}, "hard"),
    (
        "anthropic/claude-haiku-4-5",
        {"extra_body": {"reasoning": {"enabled": False}}},
        "hard",
    ),
    ("google/gemini-3-flash-preview", {"reasoning_effort": "minimal"}, "medium"),
    (
        "qwen/qwen3.8-27b",
        {"extra_body": {"reasoning": {"enabled": False}}},
        "medium",
    ),
    (
        "google/gemma-4-31b-it",
        {"extra_body": {"reasoning": {"effort": "low"}}},
        "medium",
    ),
    ("gpt-5.4-nano", {"reasoning_effort": "none"}, "hard"),
    ("qwen/qwen3-30b-a3b-instruct-2507", {}, "hard"),
    (
        "google/gemma-4-26b-a4b-it",
        {"extra_body": {"reasoning": {"enabled": False}}},
        "hard",
    ),
    ("gpt-4.1-mini", {}, "hard"),
    (
        "moonshotai/kimi-k2.6",
        {"extra_body": {"thinking": {"type": "disabled"}}},
        "hard",
    ),
    ("gpt-4o-mini", {}, "hard"),
    (
        "anthropic/claude-sonnet-5",
        {"extra_body": {"reasoning": {"enabled": False}}},
        "medium",
    ),
    ("gpt-5-mini", {"reasoning_effort": "low"}, "hard"),
    ("google/gemini-3.1-flash-lite", {"reasoning_effort": "minimal"}, "hard"),
]


# The banking easy open roster (Ben, 2026-08-28, easy-tier-only in banking):
# the plus slots' 20-model open roster plus banking's two domain-addition
# seats, every model available anywhere in the final set's menus. Banking
# Medium/Hard slots deliberately keep the fenced stock tier menus (gated
# below).
_BANKING_EASY_ROSTER = _OPEN_ROSTER + [
    (
        "qwen/qwen3.6-27b",
        {"extra_body": {"reasoning": {"enabled": False}}},
        "hard",
    ),
    ("stepfun/step-3.7-flash", {"reasoning_effort": "medium"}, "hard"),
]

# Direct Anthropic access is retired org-side, so Anthropic seats on the
# written-out menus run through OpenRouter (same convention as the Opus seat
# on the Easy slots), reasoning pinned off, billed at the model's HOME bucket
# (a hard-bucket model in a medium pool still bills hard rates).
_ANTHROPIC_TRANSPORT_SWAPS = {
    "anthropic/claude-haiku-4-5": (
        "anthropic/claude-haiku-4-5",
        "hard",
    ),
    "anthropic/claude-sonnet-5": (
        "anthropic/claude-sonnet-5",
        "medium",
    ),
}


_BANKING_CLIENT_SLOT_PAIRS = [
    # (client-E slot, evidence-E sibling): the client slots fork the #953
    # per-subdomain client arms (sections_hard_client evidence surface +
    # held-fact overlay) but score on the sibling's partition with the
    # sibling's Easy profile.
    (
        "020_banking_knowledge_construction_client_card_selection_client",
        "002_banking_knowledge_construction_client_api_card_selection",
    ),
    (
        "021_banking_knowledge_construction_client_deposit_opening_client",
        "003_banking_knowledge_construction_client_api_deposit_opening",
    ),
    (
        "022_banking_knowledge_construction_client_deposit_services_client",
        "004_banking_knowledge_construction_client_api_deposit_services",
    ),
    (
        "023_banking_knowledge_construction_client_card_servicing_client",
        "005_banking_knowledge_construction_client_api_card_servicing",
    ),
    (
        "024_banking_knowledge_construction_client_business_client",
        "006_banking_knowledge_construction_client_api_business",
    ),
    (
        "025_banking_knowledge_construction_client_debit_security_client",
        "007_banking_knowledge_construction_client_api_debit_security",
    ),
]


# --- Capability-bucket pricing invariants ------------------------------------


def test_every_registry_model_bills_at_its_home_bucket_rate():
    from tau2.hyper.performance_profiles import _registry_credit_rates

    registry = _registry_credit_rates()
    assert set(registry) == set(MODEL_BUCKETS)
    for model, credit_rates in registry.items():
        assert credit_rates == _bucket_rates(MODEL_BUCKETS[model]), model
