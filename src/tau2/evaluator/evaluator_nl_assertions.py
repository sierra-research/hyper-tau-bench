import json
import re
from collections.abc import Callable
from typing import Any, ClassVar

from tau2.agent.base.streaming import (
    LinearizationStrategy,
    ParticipantTick,
    linearize_ticks,
)
from tau2.config import DEFAULT_LLM_NL_ASSERTIONS, DEFAULT_LLM_NL_ASSERTIONS_ARGS
from tau2.data_model.message import Message, SystemMessage, Tick, UserMessage
from tau2.data_model.simulation import NLAssertionCheck, RewardInfo
from tau2.data_model.tasks import NLAssertion, RewardType, Task
from tau2.evaluator.evaluator_base import EvaluatorBase
from tau2.utils.llm_utils import generate

NLAssertionInput = str | NLAssertion | dict[str, Any]
NLAssertionJudge = Callable[[list[Message], NLAssertion], NLAssertionCheck]

RESPONSE_OPENINGS_SYSTEM_PROMPT = """
You are a strict but precise evaluator for one customer-service response phrasing rule.

RULE
The assistant must not begin more than one customer-facing response with the same opening phrase template.

INPUT
You will see only assistant response openings, numbered in conversation order.

HOW TO DECIDE
- Compare only the opening wording shown for each assistant response.
- A violation requires repeated reusable opening wording, not merely the same broad discourse function.
- Ignore capitalization, punctuation, customer names, reservation/order/line IDs, phone numbers, dates, addresses, and other entity-specific values.
- Entity changes do not make the same frame meaningfully different. For example, "I found the tablet order" and "I found the sneaker order" repeat "I found the ...".
- Repeated refusal/apology frames count as repeated. For example, "I'm sorry, but passengers cannot..." and "I'm sorry, but I can't..." repeat "I'm sorry, but ...".
- Repeated completion frames count as repeated. For example, "Done. Your shipping address..." and "Done. Your default account address..." repeat "Done. Your ...".
- Repeated confirmation/request frames count as repeated when the reusable phrase is the same, such as "Please confirm..." appearing in multiple responses.
- Do not fail only because openings share one generic lead word such as "Yes", "No", "Thanks", "Great", "Please", "Next", "Now", or "Since".
- For those generic lead words, fail only if the phrase after the generic lead word is also substantially the same reusable template. For example, "Please turn Data Roaming ON" and "Please disconnect the VPN" are not the same opening template.
- Do not fail because multiple openings provide different sequential troubleshooting steps, even if each is imperative or starts with a transition word.

OUTPUT
Return only valid JSON:
{
  "metExpectation": true or false,
  "repeatedOpenings": [
    {
      "template": "short normalized repeated opening phrase",
      "responseNumbers": [1, 4],
      "evidence": ["opening text 1", "opening text 4"]
    }
  ],
  "reasoning": "brief explanation"
}

Set metExpectation to false if there is at least one repeated opening phrase template.
Set metExpectation to true only if no repeated opening phrase template appears.
"""


def _first_sentence_or_opening(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return text

    pieces = re.split(r"(?<=[.!?])\s+", text)
    opening = pieces[0].strip()
    token_count = len(re.findall(r"[A-Za-z0-9']+", opening))
    if token_count <= 2 and len(pieces) > 1:
        opening = f"{opening} {pieces[1].strip()}"

    words = opening.split()
    if len(words) > 32:
        opening = " ".join(words[:32]) + " ..."
    return opening


def _assistant_response_openings(trajectory: list[Message]) -> list[str]:
    openings = []
    for message in trajectory:
        if message.role != "assistant":
            continue
        if getattr(message, "tool_calls", None):
            continue
        content = message.content or ""
        if content.strip():
            openings.append(_first_sentence_or_opening(content))
    return openings


def _evaluate_response_openings_assertion(
    trajectory: list[Message],
    assertion: NLAssertion,
) -> NLAssertionCheck:
    openings = _assistant_response_openings(trajectory)
    openings_text = "\n".join(
        f"{idx}. {opening}" for idx, opening in enumerate(openings, start=1)
    )
    user_prompt = f"""
Assertion:
{assertion.assertion}

Assistant response openings:
{openings_text}
"""

    assistant_message = generate(
        model=DEFAULT_LLM_NL_ASSERTIONS,
        messages=[
            SystemMessage(role="system", content=RESPONSE_OPENINGS_SYSTEM_PROMPT),
            UserMessage(role="user", content=user_prompt),
        ],
        call_name="nl_assertions_response_openings_eval",
        **DEFAULT_LLM_NL_ASSERTIONS_ARGS,
    )
    result = json.loads(assistant_message.content)
    return NLAssertionCheck(
        id=assertion.id,
        judge=assertion.judge,
        nl_assertion=assertion.assertion,
        met=result["metExpectation"],
        justification=result["reasoning"],
    )


class NLAssertionsEvaluator(EvaluatorBase[Message]):
    """
    Judge that evaluates whether a trajectory adheres to all the natural-language assertions.
    """

    CUSTOM_JUDGES: ClassVar[dict[str, NLAssertionJudge]] = {}

    @classmethod
    def register_judge(cls, name: str, judge: NLAssertionJudge) -> None:
        """Register a custom NL assertion evaluator by stable judge name."""
        if name == "generic":
            raise ValueError("The generic NL assertion judge cannot be overridden")
        cls.CUSTOM_JUDGES[name] = judge

    @classmethod
    def calculate_reward(
        cls,
        task: Task,
        full_trajectory: list[Message],
    ) -> RewardInfo:
        """
        Calculate the reward for the simulation by using an LLM to evaluate whether the trajectory adheres to all the natural-language assertions
        """
        if task.evaluation_criteria is None:
            return RewardInfo(
                reward=1.0,
                nl_assertions=[],
                info={"note": "No evaluation criteria"},
                reward_breakdown={RewardType.NL_ASSERTION: 1.0},
            )
        nl_assertions = task.evaluation_criteria.nl_assertions
        if not nl_assertions:
            return RewardInfo(
                reward=1.0,
                nl_assertions=[],
                info={"note": "No nl_assertions to evaluate"},
                reward_breakdown={RewardType.NL_ASSERTION: 1.0},
            )

        nl_assertions_checks = cls.evaluate_nl_assertions(
            full_trajectory, nl_assertions
        )

        # Calculate reward: 1 if all expectations are met, 0 otherwise
        all_expectations_met = all(result.met for result in nl_assertions_checks)
        reward = 1.0 if all_expectations_met else 0.0

        return RewardInfo(
            reward=reward,
            nl_assertions=nl_assertions_checks,
            reward_breakdown={RewardType.NL_ASSERTION: reward},
        )

    @classmethod
    def evaluate_nl_assertions(
        cls,
        trajectory: list[Message],
        nl_assertions: list[NLAssertionInput],
    ) -> list[NLAssertionCheck]:
        """
        Evaluate whether the trajectory meets each expected outcome.

        Args:
            trajectory: List of messages from the conversation
            nl_assertions: List of natural-language assertions to evaluate

        Returns:
            List of evaluation results for each NL assertion, containing:
            - nl_assertion: The NL assertion being evaluated
            - metExpectation: Boolean indicating if the assertion was met
            - reasoning: Explanation for the evaluation
        """
        assertions = [cls._coerce_nl_assertion(item) for item in nl_assertions]
        results: list[NLAssertionCheck | None] = [None] * len(assertions)

        generic_indices = [
            idx
            for idx, assertion in enumerate(assertions)
            if assertion.judge == "generic"
        ]
        if generic_indices:
            generic_checks = cls._evaluate_generic_nl_assertions(
                trajectory,
                [assertions[idx].assertion for idx in generic_indices],
            )
            if len(generic_checks) != len(generic_indices):
                raise ValueError(
                    "Generic NL assertion judge returned "
                    f"{len(generic_checks)} result(s) for "
                    f"{len(generic_indices)} assertion(s)"
                )
            for idx, check in zip(generic_indices, generic_checks):
                assertion = assertions[idx]
                results[idx] = check.model_copy(
                    update={"id": assertion.id, "judge": assertion.judge}
                )

        for idx, assertion in enumerate(assertions):
            if assertion.judge == "generic":
                continue
            judge = cls.CUSTOM_JUDGES.get(assertion.judge)
            if judge is None:
                raise ValueError(f"Unknown NL assertion judge: {assertion.judge}")
            results[idx] = judge(trajectory, assertion)

        return [result for result in results if result is not None]

    @staticmethod
    def _coerce_nl_assertion(assertion: NLAssertionInput) -> NLAssertion:
        if isinstance(assertion, NLAssertion):
            return assertion
        if isinstance(assertion, str):
            return NLAssertion(assertion=assertion)
        return NLAssertion.model_validate(assertion)

    @classmethod
    def _evaluate_generic_nl_assertions(
        cls,
        trajectory: list[Message],
        nl_assertions: list[str],
    ) -> list[NLAssertionCheck]:
        trajectory_str = "\n".join(
            [f"{message.role}: {message.content}" for message in trajectory]
        )
        # System prompt similar to the TypeScript implementation
        system_prompt = """
        TASK
        - You will be given a list of expected outcomes and a conversation that was collected during a test case run.
        - The conversation is between an agent and a customer.
        - Your job is to evaluate whether the agent satisfies each of the expected outcomes.
        - Grade each expected outcome individually.

        FORMAT
        - Your response should be a JSON object with the following fields:
        - `reasoning`: a short explanation for your classification
        - `metExpectation`: `true` if the agent satisfies the expected outcomes, `false` otherwise
        - `expectedOutcome`: repeat the expectation from the input that you are grading
        
        Example response structure:
        {
            "results": [
                {
                    "expectedOutcome": "<one of the expected outcomes from the input>",
                    "reasoning": "<reasoning trace>",
                    "metExpectation": <false or true>,
                }
            ]
        }
        """

        user_prompt = f"""
        conversation:
        {trajectory_str}
        
        expectedOutcomes:
        {nl_assertions}
        """

        messages = [
            SystemMessage(role="system", content=system_prompt),
            UserMessage(role="user", content=user_prompt),
        ]

        assistant_message = generate(
            model=DEFAULT_LLM_NL_ASSERTIONS,
            messages=messages,
            call_name="nl_assertions_eval",
            **DEFAULT_LLM_NL_ASSERTIONS_ARGS,
        )
        result_data = json.loads(assistant_message.content)
        return [
            NLAssertionCheck(
                nl_assertion=result["expectedOutcome"],
                met=result["metExpectation"],
                justification=result["reasoning"],
            )
            for result in result_data.get("results", [])
        ]


class FullDuplexNLAssertionsEvaluator(EvaluatorBase[Tick]):
    """
    Judge that evaluates whether a full-duplex trajectory adheres to all the
    natural-language assertions.
    """

    @classmethod
    def ticks_to_message_history(cls, ticks: list[Tick]) -> list[Message]:
        """
        Convert a list of Ticks to a linearized message history suitable for NL evaluation.

        This converts orchestrator Ticks to ParticipantTicks (from the agent's perspective),
        then uses containment-aware linearization to create a sequential message list.
        Only speech content is included (tool calls are ignored for NL evaluation).

        Args:
            ticks: List of Tick objects from full-duplex simulation.

        Returns:
            List of Messages linearized using containment-aware strategy.
        """
        # Convert orchestrator Ticks to ParticipantTicks from agent's perspective
        # self_chunk = agent_chunk, other_chunk = user_chunk
        # We only care about speech content, not tool calls
        participant_ticks: list[ParticipantTick] = []

        for tick in ticks:
            # Only include chunks that have content (not tool calls)
            agent_chunk = tick.agent_chunk
            user_chunk = tick.user_chunk

            # Skip tool call messages - we only want speech content
            if agent_chunk is not None and agent_chunk.is_tool_call():
                agent_chunk = None
            if user_chunk is not None and user_chunk.is_tool_call():
                user_chunk = None

            participant_tick = ParticipantTick(
                tick_id=tick.tick_id,
                timestamp=tick.timestamp,
                self_chunk=agent_chunk,
                other_chunk=user_chunk,
            )
            participant_ticks.append(participant_tick)

        # Linearize using containment-aware strategy
        messages = linearize_ticks(
            participant_ticks,
            strategy=LinearizationStrategy.CONTAINMENT_AWARE,
        )

        return messages

    @classmethod
    def calculate_reward(
        cls,
        task: Task,
        full_trajectory: list[Tick],
    ) -> RewardInfo:
        """
        Calculate the reward for the simulation by using an LLM to evaluate whether
        the trajectory adheres to all the natural-language assertions.
        """
        if task.evaluation_criteria is None:
            return RewardInfo(
                reward=1.0,
                nl_assertions=[],
                info={"note": "No evaluation criteria"},
                reward_breakdown={RewardType.NL_ASSERTION: 1.0},
            )
        nl_assertions = task.evaluation_criteria.nl_assertions
        if not nl_assertions:
            return RewardInfo(
                reward=1.0,
                nl_assertions=[],
                info={"note": "No nl_assertions to evaluate"},
                reward_breakdown={RewardType.NL_ASSERTION: 1.0},
            )

        # Convert ticks to linearized message history
        messages = cls.ticks_to_message_history(full_trajectory)

        nl_assertions_checks = cls.evaluate_nl_assertions(messages, nl_assertions)

        # Calculate reward: 1 if all expectations are met, 0 otherwise
        all_expectations_met = all(result.met for result in nl_assertions_checks)
        reward = 1.0 if all_expectations_met else 0.0

        return RewardInfo(
            reward=reward,
            nl_assertions=nl_assertions_checks,
            reward_breakdown={RewardType.NL_ASSERTION: reward},
        )

    @classmethod
    def evaluate_nl_assertions(
        cls,
        trajectory: list[Message],
        nl_assertions: list[NLAssertionInput],
    ) -> list[NLAssertionCheck]:
        """
        Evaluate whether the trajectory meets each expected outcome.

        Delegates to NLAssertionsEvaluator.evaluate_nl_assertions.
        """
        return NLAssertionsEvaluator.evaluate_nl_assertions(trajectory, nl_assertions)


NLAssertionsEvaluator.register_judge(
    "response_openings",
    _evaluate_response_openings_assertion,
)
