import re

from tau2.agent.base.streaming import (
    LinearizationStrategy,
    ParticipantTick,
    linearize_ticks,
)
from tau2.data_model.message import AssistantMessage, Message, Tick
from tau2.data_model.simulation import ResponseAssertionCheck, RewardInfo
from tau2.data_model.tasks import ResponseAssertion, RewardType, Task
from tau2.evaluator.evaluator_base import EvaluatorBase


def _assistant_text_messages(trajectory: list[Message]) -> list[AssistantMessage]:
    messages = []
    for message in trajectory:
        if not isinstance(message, AssistantMessage):
            continue
        if not message.has_text_content():
            continue
        messages.append(message)
    return messages


def _contains_forbidden_value(text: str, assertion: ResponseAssertion) -> bool:
    return _count_value_matches(text, assertion) > 0


def _count_value_matches(text: str, assertion: ResponseAssertion) -> int:
    value = assertion.value
    if not value:
        raise ValueError("Response assertion value cannot be empty")
    if assertion.match == "whole_word_case_insensitive":
        pattern = rf"(?<!\w){re.escape(value)}(?!\w)"
        return len(re.findall(pattern, text, flags=re.IGNORECASE))
    if assertion.match == "substring_case_insensitive":
        return text.casefold().count(value.casefold())
    if assertion.match == "substring_case_sensitive":
        return text.count(value)
    if assertion.match == "regex_case_insensitive":
        return len(re.findall(value, text, flags=re.IGNORECASE))
    raise ValueError(f"Unsupported response assertion match mode: {assertion.match!r}")


def _matching_response_snippets(
    assistant_messages: list[AssistantMessage],
    assertion: ResponseAssertion,
) -> list[str]:
    return [
        message.content or ""
        for message in assistant_messages
        if _count_value_matches(message.content or "", assertion) > 0
    ]


def _normalized_opening_key(text: str, token_count: int) -> str | None:
    text = re.sub(r"\*\*|`", " ", text)
    text = re.sub(r"#[A-Za-z]?\d+", "ID", text)
    text = re.sub(r"\b[A-Z0-9]{5,8}\b", "ID", text)
    text = re.sub(r"\b\d{3}[- .]?\d{3}[- .]?\d{4}\b", "ID", text)
    text = re.sub(r"\b[a-z]+_[a-z0-9_]+\b", "ID", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d{3,}\b", "NUM", text)
    text = re.sub(r"[’']", "'", text)
    text = text.lower().strip()
    text = re.sub(r"^[^a-z0-9]+", "", text)
    tokens = re.findall(r"[a-z0-9']+", text)
    if len(tokens) < token_count:
        return None
    return " ".join(tokens[:token_count])


def _opening_token_count(assertion: ResponseAssertion) -> int:
    try:
        token_count = int(assertion.value)
    except ValueError as exc:
        raise ValueError(
            "no_repeated_opening_phrase response assertions require "
            "an integer token count value"
        ) from exc
    if token_count <= 0:
        raise ValueError(
            "no_repeated_opening_phrase response assertions require "
            "a positive token count value"
        )
    return token_count


class ResponseAssertionsEvaluator(EvaluatorBase[Message]):
    """
    Deterministically evaluate assistant response phrasing assertions.
    """

    @classmethod
    def calculate_reward(
        cls,
        task: Task,
        full_trajectory: list[Message],
    ) -> RewardInfo:
        if task.evaluation_criteria is None:
            return RewardInfo(
                reward=1.0,
                response_assertions=[],
                info={"note": "No evaluation criteria"},
                reward_breakdown={RewardType.RESPONSE_ASSERTION: 1.0},
            )
        response_assertions = task.evaluation_criteria.response_assertions
        if not response_assertions:
            return RewardInfo(
                reward=1.0,
                response_assertions=[],
                info={"note": "No response_assertions to evaluate"},
                reward_breakdown={RewardType.RESPONSE_ASSERTION: 1.0},
            )

        checks = cls.evaluate_response_assertions(
            full_trajectory,
            response_assertions,
        )
        reward = 1.0 if all(check.met for check in checks) else 0.0
        return RewardInfo(
            reward=reward,
            response_assertions=checks,
            reward_breakdown={RewardType.RESPONSE_ASSERTION: reward},
        )

    @classmethod
    def evaluate_response_assertions(
        cls,
        trajectory: list[Message],
        response_assertions: list[ResponseAssertion],
    ) -> list[ResponseAssertionCheck]:
        assistant_messages = _assistant_text_messages(trajectory)
        checks = []
        for assertion in response_assertions:
            if assertion.scope != "assistant_customer_responses":
                raise ValueError(
                    f"Unsupported response assertion scope: {assertion.scope!r}"
                )

            if assertion.type == "forbidden_word":
                violating_message = next(
                    (
                        message
                        for message in assistant_messages
                        if _contains_forbidden_value(message.content or "", assertion)
                    ),
                    None,
                )
                if violating_message is None:
                    checks.append(
                        ResponseAssertionCheck(
                            response_assertion=assertion,
                            met=True,
                            justification=(
                                f"No assistant response contained {assertion.value!r}."
                            ),
                        )
                    )
                else:
                    checks.append(
                        ResponseAssertionCheck(
                            response_assertion=assertion,
                            met=False,
                            justification=(
                                f"Assistant response contained {assertion.value!r}: "
                                f"{violating_message.content}"
                            ),
                        )
                    )
                continue

            if assertion.type == "max_occurrences":
                if assertion.max_count is None:
                    raise ValueError(
                        "max_occurrences response assertions require max_count"
                    )
                match_count = sum(
                    _count_value_matches(message.content or "", assertion)
                    for message in assistant_messages
                )
                if match_count <= assertion.max_count:
                    checks.append(
                        ResponseAssertionCheck(
                            response_assertion=assertion,
                            met=True,
                            justification=(
                                f"Found {match_count} matches for "
                                f"{assertion.value!r}; maximum allowed is "
                                f"{assertion.max_count}."
                            ),
                        )
                    )
                else:
                    snippets = _matching_response_snippets(
                        assistant_messages,
                        assertion,
                    )
                    excerpt = " | ".join(snippets[:3])
                    checks.append(
                        ResponseAssertionCheck(
                            response_assertion=assertion,
                            met=False,
                            justification=(
                                f"Found {match_count} matches for "
                                f"{assertion.value!r}; maximum allowed is "
                                f"{assertion.max_count}. Matching responses: "
                                f"{excerpt}"
                            ),
                        )
                    )
                continue

            if assertion.type == "no_repeated_opening_phrase":
                token_count = _opening_token_count(assertion)
                seen_openings: dict[str, AssistantMessage] = {}
                repeated_key = None
                first_message = None
                second_message = None
                for message in assistant_messages:
                    key = _normalized_opening_key(message.content or "", token_count)
                    if key is None:
                        continue
                    if key in seen_openings:
                        repeated_key = key
                        first_message = seen_openings[key]
                        second_message = message
                        break
                    seen_openings[key] = message

                if repeated_key is None:
                    checks.append(
                        ResponseAssertionCheck(
                            response_assertion=assertion,
                            met=True,
                            justification=(
                                "No assistant response reused the same normalized "
                                f"{token_count}-token opening phrase."
                            ),
                        )
                    )
                else:
                    checks.append(
                        ResponseAssertionCheck(
                            response_assertion=assertion,
                            met=False,
                            justification=(
                                "Assistant responses reused normalized opening "
                                f"{repeated_key!r}: {first_message.content} | "
                                f"{second_message.content}"
                            ),
                        )
                    )
                continue

            raise ValueError(f"Unsupported response assertion type: {assertion.type!r}")
        return checks


class FullDuplexResponseAssertionsEvaluator(EvaluatorBase[Tick]):
    @classmethod
    def ticks_to_message_history(cls, ticks: list[Tick]) -> list[Message]:
        participant_ticks: list[ParticipantTick] = []
        for tick in ticks:
            agent_chunk = tick.agent_chunk
            user_chunk = tick.user_chunk
            if agent_chunk is not None and agent_chunk.is_tool_call():
                agent_chunk = None
            if user_chunk is not None and user_chunk.is_tool_call():
                user_chunk = None
            participant_ticks.append(
                ParticipantTick(
                    tick_id=tick.tick_id,
                    timestamp=tick.timestamp,
                    self_chunk=agent_chunk,
                    other_chunk=user_chunk,
                )
            )
        return linearize_ticks(
            participant_ticks,
            strategy=LinearizationStrategy.CONTAINMENT_AWARE,
        )

    @classmethod
    def calculate_reward(
        cls,
        task: Task,
        full_trajectory: list[Tick],
    ) -> RewardInfo:
        messages = cls.ticks_to_message_history(full_trajectory)
        return ResponseAssertionsEvaluator.calculate_reward(task, messages)
