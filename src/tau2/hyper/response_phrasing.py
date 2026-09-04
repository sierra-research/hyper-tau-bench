from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field, model_validator

from tau2.data_model.tasks import (
    EvaluationCriteria,
    NLAssertion,
    ResponseAssertion,
    RewardType,
    Task,
)
from tau2.utils.utils import DATA_DIR


class ResponsePhrasingAssertion(BaseModel):
    """Machine-facing assertion attached to a response phrasing rule."""

    type: str
    value: str
    scope: str = "assistant_customer_responses"
    match: str = "whole_word_case_insensitive"
    max_count: int | None = None


class DomainSafety(BaseModel):
    """Whether a phrasing rule can be added to a domain without SOP conflict."""

    safe: bool
    reasoning: str | None = None
    reason: str | None = None
    safe_if: str | None = None


class ResponsePhrasingRule(BaseModel):
    """One human-facing response phrasing instruction and its assertion."""

    id: str
    instruction: str
    domain_safety: dict[str, DomainSafety] = Field(default_factory=dict)
    assertion: ResponsePhrasingAssertion | None = None
    nl_assertion: str | NLAssertion | None = None

    @model_validator(mode="after")
    def _require_assertion(self) -> "ResponsePhrasingRule":
        if self.assertion is None and not self.nl_assertion:
            raise ValueError("Response phrasing rules require an assertion")
        return self


class ResponsePhrasingRulePack(BaseModel):
    """A collection of response phrasing rules."""

    rules: list[ResponsePhrasingRule] = Field(default_factory=list)

    @property
    def response_assertions(self) -> list[ResponseAssertion]:
        return [
            ResponseAssertion(
                id=rule.id,
                type=rule.assertion.type,
                value=rule.assertion.value,
                scope=rule.assertion.scope,
                match=rule.assertion.match,
                max_count=rule.assertion.max_count,
            )
            for rule in self.rules
            if rule.assertion is not None
        ]

    @property
    def nl_assertions(self) -> list[str | NLAssertion]:
        return [
            rule.nl_assertion for rule in self.rules if rule.nl_assertion is not None
        ]


@dataclass(frozen=True)
class ResponsePhrasingTaskSelection:
    """Resolved response-phrasing pack and optional selected rule ids for a task."""

    rules_path: str | None
    rule_ids: list[str] | None = None
    source_task_id: str | None = None


def _resolve_rule_pack_path(path: str | Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return DATA_DIR / path


def load_response_phrasing_rule_pack(
    path: Optional[str | Path],
) -> Optional[ResponsePhrasingRulePack]:
    if path is None:
        return None
    resolved = _resolve_rule_pack_path(path)
    payload = yaml.safe_load(resolved.read_text())
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ValueError(f"Response phrasing rule pack must be a mapping: {resolved}")
    return ResponsePhrasingRulePack.model_validate(payload)


def select_response_phrasing_rule_pack(
    pack: Optional[ResponsePhrasingRulePack],
    rule_ids: Optional[list[str]],
) -> Optional[ResponsePhrasingRulePack]:
    """Return a copy of ``pack`` containing only the requested rule ids."""
    if pack is None or rule_ids is None:
        return pack
    if len(rule_ids) != len(set(rule_ids)):
        raise ValueError("response phrasing rule selection contains duplicate ids")

    available_ids = {rule.id for rule in pack.rules}
    missing_ids = set(rule_ids) - available_ids
    if missing_ids:
        raise ValueError(
            "response phrasing rule selection references unknown ids: "
            f"{sorted(missing_ids)}"
        )

    selected_ids = set(rule_ids)
    return pack.model_copy(
        update={"rules": [rule for rule in pack.rules if rule.id in selected_ids]}
    )


def _composition_response_phrasing_stage(task: Any) -> dict[str, Any] | None:
    pipeline = getattr(task, "composition_pipeline", None)
    if pipeline is None and getattr(task, "hyper", None) is not None:
        pipeline = getattr(task.hyper, "composition_pipeline", None)
    if not pipeline:
        return None

    for stage in pipeline:
        if not isinstance(stage, dict):
            continue
        if stage.get("stage") == "response_phrasing":
            return stage
    return None


def resolve_response_phrasing_task_selection(
    task: Any,
    *,
    visited_task_ids: set[str] | None = None,
) -> ResponsePhrasingTaskSelection:
    """Resolve the response-phrasing pack selected by a Hyper-τ task.

    A task can either declare ``response_phrasing_rules_path`` directly, or it
    can compose with an earlier response-phrasing task through a
    ``composition_pipeline`` stage. The current task may narrow that upstream
    pack with ``response_phrasing_rule_ids`` or stage ``selected_rule_ids``.
    """
    if visited_task_ids is None:
        visited_task_ids = set()

    task_id = getattr(task, "id", None)
    if task_id is not None:
        if task_id in visited_task_ids:
            raise ValueError(
                f"Cycle detected in response-phrasing task dependencies: {task_id}"
            )
        visited_task_ids.add(task_id)

    rules_path = getattr(task, "response_phrasing_rules_path", None)
    rule_ids = getattr(task, "response_phrasing_rule_ids", None)
    source_task_id = None

    stage = _composition_response_phrasing_stage(task)
    if stage is not None:
        source_task_id = stage.get("source_task_id") or stage.get("task_id")
        stage_rule_ids = stage.get("selected_rule_ids")
        if rule_ids is None and stage_rule_ids is not None:
            rule_ids = list(stage_rule_ids)

        if rules_path is None and source_task_id:
            from tau2.hyper.task_loader import load_hyper_tau_task

            upstream_task = load_hyper_tau_task(source_task_id)
            source_domain = getattr(task, "source_domain", None)
            if (
                source_domain is not None
                and upstream_task.source_domain != source_domain
            ):
                raise ValueError(
                    "Response phrasing dependency must use the active domain. "
                    f"Task {getattr(task, 'id', '<unknown>')!r} is "
                    f"{source_domain!r}, but dependency {source_task_id!r} is "
                    f"{upstream_task.source_domain!r}."
                )
            upstream_selection = resolve_response_phrasing_task_selection(
                upstream_task,
                visited_task_ids=visited_task_ids,
            )
            rules_path = upstream_selection.rules_path
            if rule_ids is None:
                rule_ids = upstream_selection.rule_ids

    return ResponsePhrasingTaskSelection(
        rules_path=rules_path,
        rule_ids=rule_ids,
        source_task_id=source_task_id,
    )


def load_selected_response_phrasing_rule_pack_for_task(
    task: Any,
) -> Optional[ResponsePhrasingRulePack]:
    selection = resolve_response_phrasing_task_selection(task)
    pack = load_response_phrasing_rule_pack(selection.rules_path)
    return select_response_phrasing_rule_pack(pack, selection.rule_ids)


def render_response_phrasing_rules_markdown(
    pack: ResponsePhrasingRulePack,
) -> str:
    lines = [f"- {rule.instruction}" for rule in pack.rules]
    return "\n".join(lines) + ("\n" if lines else "")


def response_assertions_to_json(assertions: list[ResponseAssertion]) -> list[dict]:
    return [
        assertion.model_dump(mode="json", exclude_none=True) for assertion in assertions
    ]


def response_assertions_from_json(payload: Any) -> list[ResponseAssertion]:
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError("response_assertions must be a list")
    return [ResponseAssertion.model_validate(item) for item in payload]


def nl_assertions_to_json(assertions: list[str | NLAssertion]) -> list[str | dict]:
    return [
        assertion
        if isinstance(assertion, str)
        else assertion.model_dump(mode="json", exclude_none=True)
        for assertion in assertions
    ]


def nl_assertions_from_json(payload: Any) -> list[str | NLAssertion]:
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError("nl_assertions must be a list")
    assertions: list[str | NLAssertion] = []
    for item in payload:
        if isinstance(item, str):
            assertions.append(item)
        else:
            assertions.append(NLAssertion.model_validate(item))
    return assertions


def _nl_assertion_key(assertion: str | NLAssertion) -> tuple[str, str | None, str]:
    if isinstance(assertion, str):
        return ("generic", None, assertion)
    return (assertion.judge, assertion.id, assertion.assertion)


def apply_response_assertions_to_task(
    task: Task,
    response_assertions: list[ResponseAssertion],
) -> Task:
    if not response_assertions:
        return task

    criteria = (
        task.evaluation_criteria.model_copy(deep=True)
        if task.evaluation_criteria is not None
        else EvaluationCriteria()
    )
    existing_assertions = list(criteria.response_assertions or [])
    existing_ids = {assertion.id for assertion in existing_assertions}
    for assertion in response_assertions:
        if assertion.id not in existing_ids:
            existing_assertions.append(assertion)
            existing_ids.add(assertion.id)
    criteria.response_assertions = existing_assertions

    reward_basis = list(criteria.reward_basis)
    if RewardType.RESPONSE_ASSERTION not in reward_basis:
        reward_basis.append(RewardType.RESPONSE_ASSERTION)
    criteria.reward_basis = reward_basis

    return task.model_copy(update={"evaluation_criteria": criteria})


def apply_nl_assertions_to_task(
    task: Task,
    nl_assertions: list[str | NLAssertion],
) -> Task:
    if not nl_assertions:
        return task

    criteria = (
        task.evaluation_criteria.model_copy(deep=True)
        if task.evaluation_criteria is not None
        else EvaluationCriteria()
    )
    existing_assertions = list(criteria.nl_assertions or [])
    existing_keys = {_nl_assertion_key(assertion) for assertion in existing_assertions}
    for assertion in nl_assertions:
        assertion_key = _nl_assertion_key(assertion)
        if assertion_key not in existing_keys:
            existing_assertions.append(assertion)
            existing_keys.add(assertion_key)
    criteria.nl_assertions = existing_assertions

    reward_basis = list(criteria.reward_basis)
    if RewardType.NL_ASSERTION not in reward_basis:
        reward_basis.append(RewardType.NL_ASSERTION)
    criteria.reward_basis = reward_basis

    return task.model_copy(update={"evaluation_criteria": criteria})


def apply_response_phrasing_rule_pack_to_task(
    task: Task,
    pack: Optional[ResponsePhrasingRulePack],
) -> Task:
    if pack is None:
        return task
    task = apply_response_assertions_to_task(task, pack.response_assertions)
    return apply_nl_assertions_to_task(task, pack.nl_assertions)


def apply_response_phrasing_rule_pack_to_tasks(
    tasks: list[Task],
    pack: Optional[ResponsePhrasingRulePack],
) -> list[Task]:
    return [apply_response_phrasing_rule_pack_to_task(task, pack) for task in tasks]
