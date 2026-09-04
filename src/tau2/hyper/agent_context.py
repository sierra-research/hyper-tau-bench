"""Architecture-neutral inputs supplied to Hyper-τ agent factories."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Iterator, Mapping, Optional, Sequence

from loguru import logger

from tau2.data_model.message import AssistantMessage, Message, UserMessage
from tau2.environment.tool import Tool
from tau2.hyper.action_catalog import ActionCatalog, ActionDefinition
from tau2.utils.llm_utils import generate


@dataclass(frozen=True)
class ActionInterface:
    """Authoritative actions without prescribing how an agent uses them."""

    catalog: ActionCatalog

    @property
    def available(self) -> tuple[Tool, ...]:
        """Return all executable actions in catalog order."""
        return self.catalog.tools()

    @property
    def definitions(self) -> tuple[ActionDefinition, ...]:
        """Return metadata for every available action."""
        return self.catalog.definitions

    def select(self, names: Sequence[str]) -> tuple[Tool, ...]:
        """Resolve an agent-selected action subset by canonical name."""
        return self.catalog.tools(names)


@dataclass(frozen=True)
class KitResources:
    """Generic access to files supplied with an agent kit."""

    root: Path
    files: tuple[str, ...]

    @classmethod
    def from_root(cls, root: Path) -> "KitResources":
        """Build a stable relative file inventory beneath ``root``."""
        resolved_root = root.resolve()
        excluded_parts = {".git", "__pycache__", "simulations"}
        files = tuple(
            path.relative_to(resolved_root).as_posix()
            for path in sorted(resolved_root.rglob("*"))
            if path.is_file() and not excluded_parts.intersection(path.parts)
        )
        return cls(root=resolved_root, files=files)

    def path(self, relative_path: str) -> Path:
        """Resolve a kit-relative path without allowing root escape."""
        candidate = (self.root / relative_path).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError(f"Evidence path escapes the kit root: {relative_path!r}")
        return candidate

    def read_text(self, relative_path: str) -> str:
        """Read a text resource by its kit-relative path."""
        return self.path(relative_path).read_text()


@dataclass(frozen=True)
class CreditRates:
    """Frozen per-million-token rates used for benchmark credits."""

    input_per_million: float
    output_per_million: float
    rate_card_date: Optional[str] = None
    pricing_basis: Optional[str] = None
    source_url: Optional[str] = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CreditRates":
        """Validate and construct rates from a kit model configuration."""
        input_rate = float(value["input_per_million"])
        output_rate = float(value["output_per_million"])
        if input_rate < 0 or output_rate < 0:
            raise ValueError("Model credit rates must be non-negative")
        return cls(
            input_per_million=input_rate,
            output_per_million=output_rate,
            rate_card_date=value.get("rate_card_date"),
            pricing_basis=value.get("pricing_basis"),
            source_url=value.get("source_url"),
        )

    def credits(self, *, prompt_tokens: int, completion_tokens: int) -> float:
        """Price one normalized usage record in benchmark credits."""
        return (
            prompt_tokens * self.input_per_million
            + completion_tokens * self.output_per_million
        ) / 1_000_000


CHOICE_KEY = "one_of"


def choice_values(expected: Any) -> Optional[list[Any]]:
    """Return the allowed values when a constraint offers a choice.

    A constraint value of ``{"one_of": [...]}`` lets the caller pick among
    several settings instead of pinning one. The wrapper is explicit because
    ``constrained_args`` is a general keyword passthrough where a bare list is
    a legitimate value (``stop`` sequences, for instance).
    """
    if isinstance(expected, Mapping) and set(expected) == {CHOICE_KEY}:
        return list(expected[CHOICE_KEY])
    return None


def resolve_stock_constraints(constraints: Mapping[str, Any]) -> dict[str, Any]:
    """Collapse choices for a seat that cannot make one.

    The stock-agent fallback configures a single concrete model up front and
    has no per-call hook to select a setting, so it takes each choice's first
    allowed value. Generated agents go through :class:`ModelGateway` instead
    and must choose explicitly.
    """
    resolved: dict[str, Any] = {}
    for name, expected in constraints.items():
        choices = choice_values(expected)
        resolved[name] = choices[0] if choices else expected
    return resolved


def constraints_allow(constraints: Mapping[str, Any], args: Mapping[str, Any]) -> bool:
    """Return whether concrete arguments satisfy one config's constraints."""
    for name, expected in constraints.items():
        choices = choice_values(expected)
        if choices is not None:
            if name not in args or args[name] not in choices:
                return False
        elif args.get(name) != expected:
            return False
    return True


def _constraint_permits(expected: Any, name: str, kwargs: Mapping[str, Any]) -> bool:
    """Return whether a call's arguments are compatible with one constraint."""
    if name not in kwargs:
        return True
    choices = choice_values(expected)
    if choices is not None:
        return kwargs[name] in choices
    return kwargs[name] == expected


def _pinned_value(constraints: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    """Return the value nested at ``path`` in a constraint mapping, or None."""
    node: Any = constraints
    for key in path:
        if not isinstance(node, Mapping) or key not in node:
            return None
        node = node[key]
    return node


# Provider spellings of the same evaluation intent: this seat must not spend
# reasoning tokens. Each entry is (nested constraint path, the "off" value).
_REASONING_OFF_PINS: tuple[tuple[tuple[str, ...], Any], ...] = (
    (("extra_body", "thinking", "type"), "disabled"),
    (("extra_body", "reasoning", "enabled"), False),
    (("thinking", "type"), "disabled"),
    (("reasoning_effort",), "none"),
)


def reasoning_off_pin(constraints: Mapping[str, Any]) -> Optional[str]:
    """Return the pin that turns reasoning off, if this configuration has one.

    Only concrete pins count: a ``one_of`` choice leaves the setting
    candidate-chosen, so there is no single expectation to verify against.
    """
    for path, off_value in _REASONING_OFF_PINS:
        pinned = _pinned_value(constraints, path)
        if pinned is off_value or pinned == off_value:
            return f"{'.'.join(path)}={off_value!r}"
    return None


def reasoning_evidence(raw_data: Any) -> Optional[str]:
    """Return where a provider response carries reasoning output, if anywhere.

    Covers the surfaces litellm normalizes: chat-completions messages
    (``reasoning_content``/``reasoning``/``thinking_blocks``, plus the same
    fields under ``provider_specific_fields``) and Responses API ``output``
    items of type ``reasoning`` with non-empty text.
    """
    if not isinstance(raw_data, Mapping):
        return None
    choices = raw_data.get("choices")
    for choice in choices if isinstance(choices, list) else []:
        if not isinstance(choice, Mapping):
            continue
        message = choice.get("message")
        if not isinstance(message, Mapping):
            continue
        sources = [("choices[].message", message)]
        provider_fields = message.get("provider_specific_fields")
        if isinstance(provider_fields, Mapping):
            sources.append(
                ("choices[].message.provider_specific_fields", provider_fields)
            )
        for prefix, fields in sources:
            for field_name in ("reasoning_content", "reasoning"):
                value = fields.get(field_name)
                if isinstance(value, str) and value.strip():
                    return f"{prefix}.{field_name}"
            blocks = fields.get("thinking_blocks")
            if isinstance(blocks, list) and blocks:
                return f"{prefix}.thinking_blocks"
    output_items = raw_data.get("output")
    for item in output_items if isinstance(output_items, list) else []:
        if not isinstance(item, Mapping) or item.get("type") != "reasoning":
            continue
        for part_field in ("summary", "content"):
            parts = item.get(part_field)
            for part in parts if isinstance(parts, list) else []:
                text = part.get("text") if isinstance(part, Mapping) else None
                if isinstance(text, str) and text.strip():
                    return f"output[reasoning].{part_field}"
    return None


@dataclass(frozen=True)
class ModelConfig:
    """One model available to generated agent code."""

    model: str
    constrained_args: Mapping[str, Any] = field(default_factory=dict)
    credit_rates: Optional[CreditRates] = None


@dataclass
class ModelCreditLedger:
    """Conversation-scoped accounting for all gateway model calls."""

    _by_model: dict[str, dict[str, int | float]] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def record(self, config: ModelConfig, response: Message) -> None:
        """Record one priced response, rejecting missing provider usage."""
        if config.credit_rates is None:
            return
        usage = getattr(response, "usage", None)
        if usage is None:
            raise RuntimeError(
                f"Model {config.model!r} returned no token usage; "
                "credit accounting cannot continue"
            )
        prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens = int(usage.get("completion_tokens", 0) or 0)
        credits = config.credit_rates.credits(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        with self._lock:
            model_usage = self._by_model.setdefault(
                config.model,
                {
                    "calls": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "credits": 0.0,
                },
            )
            model_usage["calls"] += 1
            model_usage["prompt_tokens"] += prompt_tokens
            model_usage["completion_tokens"] += completion_tokens
            model_usage["credits"] += credits

    def summary(self) -> dict[str, Any]:
        """Return a JSON-compatible snapshot of the conversation usage."""
        with self._lock:
            by_model = {model: dict(usage) for model, usage in self._by_model.items()}
        return {
            "calls": sum(int(usage["calls"]) for usage in by_model.values()),
            "prompt_tokens": sum(
                int(usage["prompt_tokens"]) for usage in by_model.values()
            ),
            "completion_tokens": sum(
                int(usage["completion_tokens"]) for usage in by_model.values()
            ),
            "total_credits": sum(
                float(usage["credits"]) for usage in by_model.values()
            ),
            "by_model": by_model,
        }


@dataclass
class ConstraintViolationLog:
    """Conversation-scoped record of constraint-defying provider responses.

    ``constrained_args`` are forced into every request, but nothing upstream
    proves the provider applied them: OpenRouter forwards unrecognized
    passthrough toggles that some upstreams silently drop. Every response
    from a configuration that pins reasoning off is therefore checked
    post-hoc, and responses that still carry reasoning output are recorded
    here so the run result can surface the violation.
    """

    _by_model: dict[str, dict[str, Any]] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def record(
        self,
        config: ModelConfig,
        response: Message,
        call_name: Optional[str] = None,
    ) -> None:
        """Check one response against its configuration's verifiable pins."""
        pin = reasoning_off_pin(config.constrained_args)
        if pin is None:
            return
        evidence = reasoning_evidence(getattr(response, "raw_data", None))
        if evidence is None:
            return
        with self._lock:
            entry = self._by_model.get(config.model)
            if entry is None:
                entry = {
                    "violations": 0,
                    "constraint": pin,
                    "evidence": evidence,
                    "first_call_name": call_name,
                }
                self._by_model[config.model] = entry
            entry["violations"] += 1
            first_violation = entry["violations"] == 1
        if first_violation:
            logger.warning(
                f"Model {config.model!r} returned reasoning output at "
                f"{evidence} despite the pinned constraint {pin}; the "
                "provider ignored the constraint. Recording the violation "
                "for the run result."
            )

    def summary(self) -> Optional[dict[str, Any]]:
        """Return a JSON-compatible violation report, or None when clean."""
        with self._lock:
            by_model = {model: dict(entry) for model, entry in self._by_model.items()}
        if not by_model:
            return None
        return {
            "violations": sum(int(entry["violations"]) for entry in by_model.values()),
            "by_model": by_model,
        }


@dataclass(frozen=True)
class ModelGateway:
    """Access to allowed models with enforced inference constraints.

    Each model's ``constrained_args`` contains values selected by the
    evaluation. Calls may omit those arguments, in which case the configured
    values are supplied, but may not override them. Arguments absent from the
    selected model's constraints are passed through for the provider to
    interpret.

    Constraints ride the request as provider passthroughs, so the gateway
    also verifies responses post-hoc where the pin's effect is observable
    (reasoning pinned off must not produce reasoning output) and records
    violations in :attr:`constraint_violation_log`.
    """

    models: tuple[ModelConfig, ...]
    credit_ledger: ModelCreditLedger = field(default_factory=ModelCreditLedger)
    constraint_violation_log: ConstraintViolationLog = field(
        default_factory=ConstraintViolationLog
    )

    def __post_init__(self) -> None:
        if not self.models:
            raise ValueError("At least one model must be configured")

    @property
    def available_models(self) -> tuple[str, ...]:
        """Return distinct model names available to generated code."""
        return tuple(dict.fromkeys(config.model for config in self.models))

    def _config_for(self, model: str, kwargs: Mapping[str, Any]) -> ModelConfig:
        candidates = [config for config in self.models if config.model == model]
        if not candidates:
            allowed = ", ".join(repr(name) for name in self.available_models)
            raise ValueError(f"Model {model!r} is not allowed; choose one of {allowed}")

        matches = [
            config
            for config in candidates
            if all(
                _constraint_permits(expected, name, kwargs)
                for name, expected in config.constrained_args.items()
            )
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(
                f"Model call is ambiguous across {len(matches)} allowed "
                f"configurations for {model!r}; provide constrained arguments "
                "that identify exactly one configuration"
            )

        if len(candidates) == 1:
            config = candidates[0]
            conflicts = []
            for name, expected in config.constrained_args.items():
                if _constraint_permits(expected, name, kwargs):
                    continue
                choices = choice_values(expected)
                requirement = (
                    f"one of {choices!r}" if choices is not None else repr(expected)
                )
                conflicts.append(f"{name} must be {requirement}, got {kwargs[name]!r}")
            details = ", ".join(conflicts)
            raise ValueError(f"Model call violates configured constraints: {details}")

        raise ValueError(
            f"Model call does not match any allowed configuration for {model!r}"
        )

    def _resolve_args(
        self,
        config: ModelConfig,
        kwargs: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Apply pinned constraints and require a value for every choice.

        A pinned constraint supplies its value when the call omits it. A
        choice cannot: there is no defensible default among settings the
        evaluation deliberately left open, so the call must name one.
        """
        request_args: dict[str, Any] = {}
        for name, expected in config.constrained_args.items():
            choices = choice_values(expected)
            if choices is None:
                request_args[name] = expected
            elif name not in kwargs:
                raise ValueError(
                    f"Model {config.model!r} allows {name} in {choices!r}; the "
                    "call must choose one explicitly"
                )
        request_args.update(kwargs)
        return request_args

    def generate(
        self,
        *,
        model: str,
        messages: list[Message],
        actions: Optional[Sequence[Tool]] = None,
        tool_choice: Optional[str] = None,
        call_name: Optional[str] = None,
        **kwargs: Any,
    ) -> UserMessage | AssistantMessage:
        """Generate one model response with optional selected actions."""
        config = self._config_for(model, kwargs)
        request_args = self._resolve_args(config, kwargs)
        response = generate(
            model=config.model,
            messages=messages,
            tools=list(actions) if actions is not None else None,
            tool_choice=tool_choice,
            call_name=call_name,
            **request_args,
        )
        self.credit_ledger.record(config, response)
        self.constraint_violation_log.record(config, response, call_name=call_name)
        return response

    @property
    def credit_usage(self) -> Optional[dict[str, Any]]:
        """Return usage when this gateway has a configured credit rate card."""
        if not any(config.credit_rates is not None for config in self.models):
            return None
        return self.credit_ledger.summary()

    @property
    def constraint_violations(self) -> Optional[dict[str, Any]]:
        """Return detected constraint violations, or None when clean."""
        return self.constraint_violation_log.summary()

    def validate_request(
        self,
        model: str,
        kwargs: Mapping[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        """Validate a request and apply the selected model's constraints."""
        config = self._config_for(model, kwargs)
        return config.model, self._resolve_args(config, kwargs)

    def pinned_constraints(
        self,
        model: str,
        kwargs: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Return the matched configuration's pinned constraint values.

        Choice constraints are excluded: a choice's value is candidate-chosen,
        while a pin is evaluation-supplied, and callers vetting request
        arguments need to tell the two apart.
        """
        config = self._config_for(model, kwargs)
        return {
            name: expected
            for name, expected in config.constrained_args.items()
            if choice_values(expected) is None
        }


def model_config_from_mapping(config: Mapping[str, Any]) -> ModelConfig:
    """Build one validated runtime model configuration."""
    return ModelConfig(
        model=str(config["model"]),
        constrained_args=dict(config.get("constraints", {})),
        credit_rates=(
            CreditRates.from_mapping(config["credit_rates"])
            if config.get("credit_rates") is not None
            else None
        ),
    )


def collect_message_credit_usage(
    messages: Sequence[Message],
    model_config: Mapping[str, Any],
) -> Optional[dict[str, Any]]:
    """Price stock-agent assistant messages using one configured model."""
    config = model_config_from_mapping(model_config)
    if config.credit_rates is None:
        return None
    ledger = ModelCreditLedger()
    for message in messages:
        if isinstance(message, AssistantMessage):
            ledger.record(config, message)
    return ledger.summary()


def collect_message_constraint_violations(
    messages: Sequence[Message],
    model_config: Mapping[str, Any],
) -> Optional[dict[str, Any]]:
    """Verify stock-agent assistant messages against one model's constraints.

    The stock-agent fallback bypasses :class:`ModelGateway`, so its responses
    get the same post-hoc constraint check here, from the recorded messages.
    """
    config = model_config_from_mapping(model_config)
    log = ConstraintViolationLog()
    for message in messages:
        if isinstance(message, AssistantMessage):
            log.record(config, message)
    return log.summary()


@dataclass(frozen=True)
class AgentBuildContext:
    """Resources and capabilities available when constructing an agent."""

    action_interface: ActionInterface
    resources: KitResources
    model_gateway: ModelGateway
    runtime_config: Mapping[str, Any]


_active_agent_context: ContextVar[Optional[AgentBuildContext]] = ContextVar(
    "active_agent_context",
    default=None,
)


@contextmanager
def activate_agent_context(context: AgentBuildContext) -> Iterator[None]:
    """Expose one run's resources while a zero-argument factory executes."""
    token = _active_agent_context.set(context)
    try:
        yield
    finally:
        _active_agent_context.reset(token)


def get_agent_context() -> AgentBuildContext:
    """Return resources while the active agent factory is executing."""
    context = _active_agent_context.get()
    if context is None:
        raise RuntimeError(
            "Agent context is only available while create_agent() is executing"
        )
    return context


def build_agent_context(
    *,
    domain: str,
    tools: Sequence[Tool],
    resource_root: Path,
    model_configs: Sequence[ModelConfig | Mapping[str, Any]],
) -> AgentBuildContext:
    """Build the context passed to a Hyper-τ custom agent factory."""
    configs = tuple(
        config if isinstance(config, ModelConfig) else model_config_from_mapping(config)
        for config in model_configs
    )
    return AgentBuildContext(
        action_interface=ActionInterface(catalog=ActionCatalog(tools)),
        resources=KitResources.from_root(resource_root),
        model_gateway=ModelGateway(models=configs),
        runtime_config={"domain": domain},
    )
