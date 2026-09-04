"""Frozen model and credit-budget profiles for Hyper-τ construction tasks."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

PerformanceProfileName = Literal["easy", "medium", "hard"]

RATE_CARD_DATE = "2026-08-23"
PRICING_BASIS = "capability_bucket_median_list_price"

# --- Capability-bucket pricing -----------------------------------------------
#
# Every registry model has one home bucket and bills at that bucket's frozen
# flat rate wherever it is offered. The rates were derived from historical
# price inputs at calibration time; benchmark execution needs only this
# resolved configuration.
MODEL_BUCKETS: dict[str, str] = {
    "gpt-5.6-sol": "easy",
    "anthropic/claude-opus-5": "easy",
    "google/gemini-3.1-pro-preview": "easy",
    "moonshotai/kimi-k3": "easy",
    "deepseek/deepseek-v4-flash": "easy",
    "gpt-5.6-terra": "medium",
    "anthropic/claude-sonnet-5": "medium",
    "qwen/qwen3.8-27b": "medium",
    "google/gemma-4-31b-it": "medium",
    "google/gemini-3-flash-preview": "medium",
    "gpt-5.6-luna": "hard",
    "anthropic/claude-haiku-4-5": "hard",
    "qwen/qwen3-30b-a3b-instruct-2507": "hard",
    "qwen/qwen3.6-27b": "hard",
    "google/gemma-4-26b-a4b-it": "hard",
    "gpt-4.1-mini": "hard",
    "gpt-4o-mini": "hard",
    "gpt-5-mini": "hard",
    "stepfun/step-3.7-flash": "hard",
    "moonshotai/kimi-k2.6": "hard",
    "gpt-5.4-nano": "hard",
    "google/gemini-3.1-flash-lite": "hard",
}

# Median member list prices per bucket, frozen 2026-08-23. Blended 5:1
# input:output ratios land at easy/medium 5.3x and medium/hard 2.0x — the
# medians' outcome, not designed constants.
BUCKET_CREDIT_RATES: dict[str, dict[str, float]] = {
    "easy": {"input_per_million": 3.0, "output_per_million": 15.0},
    "medium": {"input_per_million": 0.5, "output_per_million": 3.2},
    "hard": {"input_per_million": 0.25, "output_per_million": 1.6},
}


def _credit_rates(bucket: str) -> dict[str, Any]:
    rates = BUCKET_CREDIT_RATES[bucket]
    return {
        "input_per_million": rates["input_per_million"],
        "output_per_million": rates["output_per_million"],
        "rate_card_date": RATE_CARD_DATE,
        "pricing_basis": PRICING_BASIS,
    }


def _model(model: str, *, constraints: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": model,
        "constraints": constraints,
        "credit_rates": _credit_rates(MODEL_BUCKETS[model]),
    }


# Provider-diverse models approved for the Easy performance tier. Easy leaves
# reasoning unconstrained (2026-08-27): every effort level is allowed, and
# pinning the top settings would tell the Developer which configuration wins.
_EASY_MODELS = [
    _model("gpt-5.6-sol", constraints={}),
    _model("anthropic/claude-opus-5", constraints={}),
    _model("google/gemini-3.1-pro-preview", constraints={}),
    _model("moonshotai/kimi-k3", constraints={}),
    _model("deepseek/deepseek-v4-flash", constraints={}),
]

_GPT_56_TERRA_MODEL = _model("gpt-5.6-terra", constraints={"reasoning_effort": "none"})

# Medium replaces the frontier options with lower-cost Terra and Sonnet.
_MEDIUM_PRIMARY_MODELS = [
    _GPT_56_TERRA_MODEL,
    _model(
        "anthropic/claude-sonnet-5",
        constraints={"extra_body": {"thinking": {"type": "disabled"}}},
    ),
]

# Latest stable model from each represented provider below its frontier line.
_MEDIUM_SECONDARY_MODELS = [
    _model("gpt-5.6-luna", constraints={"reasoning_effort": "none"}),
    _model(
        "anthropic/claude-haiku-4-5",
        constraints={"extra_body": {"thinking": {"type": "disabled"}}},
    ),
    _model(
        "google/gemini-3-flash-preview",
        constraints={"reasoning_effort": "minimal"},
    ),
    _model(
        "moonshotai/kimi-k2.6",
        constraints={"extra_body": {"thinking": {"type": "disabled"}}},
    ),
]

_MEDIUM_ONLY_MODELS = [
    _model(
        "qwen/qwen3.8-27b",
        constraints={"extra_body": {"reasoning": {"enabled": False}}},
    ),
    _model(
        "google/gemma-4-31b-it",
        constraints={"extra_body": {"reasoning": {"effort": "low"}}},
    ),
]

_HARD_TERTIARY_MODELS = [
    _model("gpt-5.4-nano", constraints={"reasoning_effort": "none"}),
    _model(
        "google/gemini-3.1-flash-lite",
        constraints={"reasoning_effort": "minimal"},
    ),
]

_QWEN_3_30B_MODEL = _model(
    "qwen/qwen3-30b-a3b-instruct-2507",
    constraints={},
)
_GEMMA_4_26B_MODEL = _model(
    "google/gemma-4-26b-a4b-it",
    constraints={"extra_body": {"reasoning": {"enabled": False}}},
)
_GPT_41_MINI_MODEL = _model("gpt-4.1-mini", constraints={})
_GPT_4O_MINI_MODEL = _model("gpt-4o-mini", constraints={})
_GPT_5_MINI_MODEL = _model("gpt-5-mini", constraints={"reasoning_effort": "low"})
_QWEN_36_27B_MODEL = _model(
    "qwen/qwen3.6-27b",
    # Thinking pinned OFF (Ben, 2026-08-26): with reasoning enabled this
    # 27B out-executes the entire medium menu on banking given distilled
    # policies (0.71-0.98 hard-cell pairs), inverting the tier ordering,
    # and the 0.085 banking hard budget never binds a bottom-bucket model.
    constraints={"extra_body": {"reasoning": {"enabled": False}}},
)
_STEP_37_FLASH_MODEL = _model(
    "stepfun/step-3.7-flash",
    constraints={"reasoning_effort": "medium"},
)

_DOMAIN_MODEL_ADDITIONS = {
    ("medium", "telecom"): [_GPT_5_MINI_MODEL],
    ("hard", "airline_plus"): [
        _QWEN_3_30B_MODEL,
        _GEMMA_4_26B_MODEL,
        _GPT_41_MINI_MODEL,
    ],
    ("hard", "retail_plus"): [
        _QWEN_3_30B_MODEL,
        _GPT_41_MINI_MODEL,
        _GPT_4O_MINI_MODEL,
    ],
    ("hard", "telecom"): [
        _GEMMA_4_26B_MODEL,
        _GPT_41_MINI_MODEL,
        _GPT_56_TERRA_MODEL,
    ],
    ("hard", "banking_knowledge"): [
        _QWEN_36_27B_MODEL,
        _STEP_37_FLASH_MODEL,
    ],
}


# Budgets cap mean credits per conversation across the evaluated set. They
# were calibrated experimentally; runtime consumes the frozen values below.
_EASY_BUDGETS = {
    "airline_plus": 0.29,
    "retail_plus": 0.28,
    "telecom": 0.51,
    "banking_knowledge": 3.7,
}
_MEDIUM_BUDGETS = {
    "airline_plus": 0.047,
    "retail_plus": 0.035,
    "telecom": 0.056,
    "banking_knowledge": 0.60,
}
_HARD_BUDGETS = {
    "airline_plus": 0.0067,
    "retail_plus": 0.0049,
    "telecom": 0.0081,
    "banking_knowledge": 0.085,
}

_PROFILE_MODELS = {
    "easy": _EASY_MODELS,
    "medium": _MEDIUM_PRIMARY_MODELS + _MEDIUM_SECONDARY_MODELS + _MEDIUM_ONLY_MODELS,
    "hard": _MEDIUM_SECONDARY_MODELS + _HARD_TERTIARY_MODELS,
}
_PROFILE_BUDGETS = {
    "easy": _EASY_BUDGETS,
    "medium": _MEDIUM_BUDGETS,
    "hard": _HARD_BUDGETS,
}

_DOMAIN_MODEL_EXCLUSIONS = {
    ("medium", "airline_plus"): {
        "anthropic/claude-sonnet-5",
        "moonshotai/kimi-k2.6",
    },
    ("hard", "airline_plus"): {
        "google/gemini-3.1-flash-lite",
        "google/gemini-3-flash-preview",
        "moonshotai/kimi-k2.6",
    },
    ("medium", "retail_plus"): {
        "anthropic/claude-sonnet-5",
        "google/gemini-3-flash-preview",
        "google/gemma-4-31b-it",
    },
    ("hard", "retail_plus"): {
        "gpt-4.1-mini",
        "gpt-5.6-luna",
        "anthropic/claude-haiku-4-5",
        "google/gemini-3.1-flash-lite",
        "google/gemini-3-flash-preview",
        "moonshotai/kimi-k2.6",
    },
    ("medium", "telecom"): {
        "gpt-5.6-terra",
        "moonshotai/kimi-k2.6",
    },
    ("hard", "telecom"): {
        "google/gemini-3-flash-preview",
        "moonshotai/kimi-k2.6",
    },
}

# The highest-scoring open-weight configuration with a matching result in the
# maintained experiment record. Keep this explicit so primary-only runs remain
# reproducible when model ordering or the rest of a profile changes.
_PRIMARY_OPEN_WEIGHT_MODELS: dict[tuple[PerformanceProfileName, str], str] = {
    ("easy", "airline_plus"): "deepseek/deepseek-v4-flash",
    ("medium", "airline_plus"): "qwen/qwen3.8-27b",
    ("hard", "airline_plus"): "google/gemma-4-26b-a4b-it",
    ("easy", "retail_plus"): "deepseek/deepseek-v4-flash",
    ("medium", "retail_plus"): "qwen/qwen3.8-27b",
    ("hard", "retail_plus"): "qwen/qwen3-30b-a3b-instruct-2507",
    ("easy", "telecom"): "deepseek/deepseek-v4-flash",
    ("medium", "telecom"): "qwen/qwen3.8-27b",
    ("hard", "telecom"): "google/gemma-4-26b-a4b-it",
    ("easy", "banking_knowledge"): "moonshotai/kimi-k3",
    ("medium", "banking_knowledge"): "qwen/qwen3.8-27b",
    ("hard", "banking_knowledge"): "qwen/qwen3.6-27b",
}


def get_performance_profile(
    profile: PerformanceProfileName,
    domain: str,
) -> tuple[list[dict[str, Any]], float]:
    """Return independent model configs and the domain's credit budget."""
    try:
        budget = _PROFILE_BUDGETS[profile][domain]
    except KeyError as error:
        raise ValueError(
            f"Performance profile {profile!r} does not support domain {domain!r}"
        ) from error
    excluded_models = _DOMAIN_MODEL_EXCLUSIONS.get((profile, domain), set())
    models = [
        deepcopy(config)
        for config in _PROFILE_MODELS[profile]
        if config["model"] not in excluded_models
    ]
    models.extend(
        deepcopy(config)
        for config in _DOMAIN_MODEL_ADDITIONS.get((profile, domain), [])
        if config["model"] not in excluded_models
    )
    return models, budget


# --- Tier-spec resolution ---------------------------------------------------
#
# Tasks may activate several tiers at once and override a tier's model pool
# or credit budget. The task JSON forms are:
#
#   "performance_profile": "easy"                      one stock tier
#   "performance_profile": ["easy", "medium"]          several stock tiers
#   "performance_profile": {"easy": {}, "medium": {"budget": 2.0}}
#
# A tier override object supports exactly two keys. "models" replaces the
# tier's pool: a bare string names a registry model and leaves its inference
# constraints EMPTY (the Developer picks any thinking configuration), while a
# {"model", "constraints", "credit_rates"} object pins constraints and may
# introduce a non-registry model when it carries explicit credit_rates.
# "budget" overrides the tier's domain budget; an explicit null removes the
# credit requirement for that tier entirely.

_TIER_ORDER: tuple[PerformanceProfileName, ...] = ("easy", "medium", "hard")
_TIER_OVERRIDE_KEYS = frozenset({"models", "budget"})
_MODEL_ENTRY_KEYS = frozenset({"model", "constraints", "credit_rates"})


def _registry_credit_rates() -> dict[str, dict[str, Any]]:
    """Map every registry model name to its frozen credit rates."""
    pools: list[list[dict[str, Any]]] = [
        _EASY_MODELS,
        _MEDIUM_PRIMARY_MODELS,
        _MEDIUM_SECONDARY_MODELS,
        _MEDIUM_ONLY_MODELS,
        _HARD_TERTIARY_MODELS,
        *_DOMAIN_MODEL_ADDITIONS.values(),
    ]
    rates: dict[str, dict[str, Any]] = {}
    for pool in pools:
        for config in pool:
            rates.setdefault(config["model"], config["credit_rates"])
    return rates


def normalize_performance_profile(
    profile: str | list[str] | dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Normalize every accepted profile form to ordered {tier: overrides}."""
    if isinstance(profile, str):
        spec: dict[str, Any] = {profile: {}}
    elif isinstance(profile, list):
        if len(set(profile)) != len(profile):
            raise ValueError(f"performance_profile lists a tier twice: {profile!r}")
        spec = {tier: {} for tier in profile}
    elif isinstance(profile, dict):
        spec = profile
    else:
        raise ValueError(
            f"performance_profile must be a tier name, a list of tier names, "
            f"or a tier mapping; got {type(profile).__name__}"
        )
    if not spec:
        raise ValueError("performance_profile must activate at least one tier")

    unknown_tiers = set(spec) - set(_TIER_ORDER)
    if unknown_tiers:
        raise ValueError(
            f"Unknown performance tiers {sorted(unknown_tiers)}; "
            f"expected a subset of {list(_TIER_ORDER)}"
        )
    for tier, overrides in spec.items():
        if not isinstance(overrides, dict):
            raise ValueError(
                f"Tier {tier!r} overrides must be an object; use {{}} for the "
                "stock tier"
            )
        unknown_keys = set(overrides) - _TIER_OVERRIDE_KEYS
        if unknown_keys:
            raise ValueError(
                f"Tier {tier!r} has unknown override keys {sorted(unknown_keys)}; "
                f"supported: {sorted(_TIER_OVERRIDE_KEYS)}"
            )
    return {tier: dict(spec[tier]) for tier in _TIER_ORDER if tier in spec}


def _validate_constraint_choices(
    constraints: dict[str, Any],
    *,
    tier: str,
    model: str,
) -> None:
    """Reject malformed ``one_of`` choices before they reach the gateway."""
    from tau2.hyper.agent_context import CHOICE_KEY

    for name, expected in constraints.items():
        if not isinstance(expected, dict) or CHOICE_KEY not in expected:
            continue
        if set(expected) != {CHOICE_KEY}:
            raise ValueError(
                f"Tier {tier!r} model {model!r} constraint {name!r} mixes "
                f"{CHOICE_KEY!r} with other keys: {sorted(expected)}"
            )
        values = expected[CHOICE_KEY]
        if not isinstance(values, list) or len(values) < 2:
            raise ValueError(
                f"Tier {tier!r} model {model!r} constraint {name!r} must list "
                f"at least two {CHOICE_KEY} values; pin the value directly to "
                "allow only one"
            )
        if len(values) != len({repr(value) for value in values}):
            raise ValueError(
                f"Tier {tier!r} model {model!r} constraint {name!r} repeats a "
                f"{CHOICE_KEY} value: {values!r}"
            )


def _resolve_model_entry(
    entry: str | dict[str, Any],
    *,
    tier: str,
    stock_by_name: dict[str, dict[str, Any]],
    registry_rates: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Resolve one "models" override entry into a runtime model config."""
    if isinstance(entry, str):
        name, constraints, explicit_rates = entry, {}, None
    elif isinstance(entry, dict):
        unknown_keys = set(entry) - _MODEL_ENTRY_KEYS
        if unknown_keys:
            raise ValueError(
                f"Tier {tier!r} model entry has unknown keys {sorted(unknown_keys)}; "
                f"supported: {sorted(_MODEL_ENTRY_KEYS)}"
            )
        if "model" not in entry:
            raise ValueError(f"Tier {tier!r} model entry is missing 'model'")
        name = str(entry["model"])
        constraints = deepcopy(entry.get("constraints") or {})
        _validate_constraint_choices(constraints, tier=tier, model=name)
        explicit_rates = deepcopy(entry.get("credit_rates"))
    else:
        raise ValueError(
            f"Tier {tier!r} model entries must be model names or objects; "
            f"got {type(entry).__name__}"
        )

    credit_rates = explicit_rates
    if credit_rates is None:
        stock_config = stock_by_name.get(name)
        if stock_config is not None:
            credit_rates = deepcopy(stock_config.get("credit_rates"))
        else:
            credit_rates = deepcopy(registry_rates.get(name))
    if credit_rates is None and isinstance(entry, str):
        raise ValueError(
            f"Tier {tier!r} names unknown model {name!r}; registry models can "
            "be named directly, others need an object with credit_rates"
        )
    config: dict[str, Any] = {"model": name, "constraints": constraints}
    if credit_rates is not None:
        config["credit_rates"] = credit_rates
    return config


def resolve_performance_profile_tiers(
    profile: str | list[str] | dict[str, Any],
    domain: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Resolve a tier spec into tier-tagged model configs and budget specs.

    Returns ``(models, tiers)``. ``models`` is the cross-tier union in
    easy->medium->hard order, each config tagged with the ``"tier"`` that owns
    it; a model appearing in several active tiers is owned (and metered) by
    the highest one. ``tiers`` holds one ``{"tier", "budget", "models"}`` spec
    per active tier, where ``budget`` is ``None`` for an uncapped tier and
    ``models`` lists the model names the tier owns.
    """
    spec = normalize_performance_profile(profile)
    registry_rates = _registry_credit_rates()
    union: list[dict[str, Any]] = []
    owner_by_model: dict[str, str] = {}
    tier_specs: list[dict[str, Any]] = []
    for tier, overrides in spec.items():
        stock_models, stock_budget = get_performance_profile(tier, domain)
        budget = overrides["budget"] if "budget" in overrides else stock_budget
        if budget is not None and (not isinstance(budget, (int, float)) or budget <= 0):
            raise ValueError(f"Tier {tier!r} budget must be a positive number or null")

        if "models" in overrides:
            entries = overrides["models"]
            if not isinstance(entries, list) or not entries:
                raise ValueError(f"Tier {tier!r} 'models' must be a non-empty list")
            stock_by_name = {config["model"]: config for config in stock_models}
            tier_models = [
                _resolve_model_entry(
                    entry,
                    tier=tier,
                    stock_by_name=stock_by_name,
                    registry_rates=registry_rates,
                )
                for entry in entries
            ]
            names = [config["model"] for config in tier_models]
            if len(set(names)) != len(names):
                raise ValueError(f"Tier {tier!r} lists a model twice: {names!r}")
        else:
            tier_models = deepcopy(stock_models)

        if budget is not None:
            unpriced = [
                config["model"]
                for config in tier_models
                if config.get("credit_rates") is None
            ]
            if unpriced:
                raise ValueError(
                    f"Tier {tier!r} has a credit budget but no credit_rates for "
                    f"{unpriced}; add rates or set the tier budget to null"
                )

        owned_names = []
        for config in tier_models:
            name = config["model"]
            if name in owner_by_model:
                continue
            owner_by_model[name] = tier
            config["tier"] = tier
            union.append(config)
            owned_names.append(name)
        tier_specs.append({"tier": tier, "budget": budget, "models": owned_names})
    return union, tier_specs


def iter_profile_model_ids(
    profile: str | list[str] | dict[str, Any],
    domain: str,
) -> list[str]:
    """Every model id a task's performance profile can expose, in menu order."""
    union, _ = resolve_performance_profile_tiers(profile, domain)
    seen: dict[str, None] = {}
    for config in union:
        seen.setdefault(str(config["model"]), None)
    return list(seen)


def get_primary_model_config(
    profile: PerformanceProfileName,
    domain: str,
) -> dict[str, Any]:
    """Return the designated open-weight primary config for a profile pair."""
    try:
        primary_model = _PRIMARY_OPEN_WEIGHT_MODELS[(profile, domain)]
    except KeyError as error:
        raise ValueError(
            f"No primary model is configured for profile {profile!r} and "
            f"domain {domain!r}"
        ) from error

    models, _ = get_performance_profile(profile, domain)
    matching_configs = [config for config in models if config["model"] == primary_model]
    if len(matching_configs) != 1:
        raise ValueError(
            f"Primary model {primary_model!r} must appear exactly once in "
            f"profile {profile!r} for domain {domain!r}"
        )
    return matching_configs[0]
