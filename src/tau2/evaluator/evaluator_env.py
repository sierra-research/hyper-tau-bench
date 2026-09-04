from typing import Callable

from loguru import logger

from tau2.data_model.message import (
    AssistantMessage,
    Message,
    Tick,
    UserMessage,
)
from tau2.data_model.simulation import DBCheck, EnvAssertionCheck, RewardInfo
from tau2.data_model.tasks import (
    EnvAssertion,
    EnvFunctionCall,
    InitializationData,
    RewardType,
    Task,
)
from tau2.environment.environment import Environment
from tau2.evaluator.db_projection import (
    dump_db_for_projection,
    project_db_state_to_target_schema,
)
from tau2.evaluator.evaluator_base import EvaluatorBase
from tau2.utils.utils import canonicalize_new_ids, get_dict_hash_normalized


def _project_db_state_to_reference(source_db, reference_db) -> dict:
    """Dump *source_db* through the reference DB schema, ignoring extra fields.

    Construction submissions may add internal helper fields that are meaningful
    only inside the generated toolkit. Reference assertions and DB hashes should
    compare the reference-visible state, so fields the reference schema does not
    know about are discarded before projection.
    """

    try:
        return project_db_state_to_target_schema(source_db, reference_db)
    except Exception as e:
        source_state = dump_db_for_projection(source_db)
        logger.warning(f"Error projecting generated DB to reference schema: {e}")
        return source_state


def _drop_construction_agent_audit_tables(state: dict | None) -> dict | None:
    """Ignore agent-side discoverable wrapper audit logs in construction scoring."""

    if not isinstance(state, dict):
        return state
    state = dict(state)
    state.pop("agent_discoverable_tools", None)
    return state


def _hashes_for_compare(
    predicted_env: Environment, gold_env: Environment, *, normalize: bool
) -> tuple[str, str, str, str]:
    """Compute (agent_db, predicted_agent_db, user_db, predicted_user_db)
    hashes for comparing two environments, optionally normalizing
    scalar lists before hashing.

    When ``normalize`` is True, lists of plain scalars (item IDs, tracking
    IDs, reservation IDs, etc.) are sorted before hashing. This is the
    construction-task scoring mode: the developer's toolkit may not match
    the reference's exact list-ordering conventions (the reference
    ``sorted()``'s some fields, the developer might not), and that should
    not affect scoring as long as the set of elements is identical.

    Additionally in ``normalize`` mode, newly-created entity IDs (keys
    that appear in only one side's top-level tables) are canonicalized:
    pred's "RSV0001" and gold's "HATHAT" both become e.g.
    "__NEW_RESERVATIONS_0__" before hashing, with the rename propagated
    through cross-references. Without this, ID-generation conventions
    (which no source — SOP, DB, policy — can communicate) cause hash
    mismatches on functionally-equivalent bookings.
    """

    if normalize:
        # Pair-and-canonicalize new IDs in both sides simultaneously so
        # the same "new entity" gets the same canonical name on both.
        if predicted_env.tools is not None and gold_env.tools is not None:
            pred_agent_state = _project_db_state_to_reference(
                predicted_env.tools.db, gold_env.tools.db
            )
            gold_agent_state = gold_env.tools.db.model_dump(mode="json")
            pred_agent_state = _drop_construction_agent_audit_tables(pred_agent_state)
            gold_agent_state = _drop_construction_agent_audit_tables(gold_agent_state)
            pred_agent_state, gold_agent_state = canonicalize_new_ids(
                pred_agent_state,
                gold_agent_state,
            )
        else:
            pred_agent_state = (
                predicted_env.tools.db.model_dump()
                if predicted_env.tools is not None
                else None
            )
            gold_agent_state = (
                gold_env.tools.db.model_dump() if gold_env.tools is not None else None
            )
        if predicted_env.user_tools is not None and gold_env.user_tools is not None:
            pred_user_state = _project_db_state_to_reference(
                predicted_env.user_tools.db, gold_env.user_tools.db
            )
            gold_user_state = gold_env.user_tools.db.model_dump(mode="json")
            pred_user_state, gold_user_state = canonicalize_new_ids(
                pred_user_state,
                gold_user_state,
            )
        else:
            pred_user_state = (
                predicted_env.user_tools.db.model_dump()
                if predicted_env.user_tools is not None
                else None
            )
            gold_user_state = (
                gold_env.user_tools.db.model_dump()
                if gold_env.user_tools is not None
                else None
            )

        agent_db_hash = (
            get_dict_hash_normalized(gold_agent_state)
            if gold_agent_state is not None
            else None
        )
        predicted_agent_db_hash = (
            get_dict_hash_normalized(pred_agent_state)
            if pred_agent_state is not None
            else None
        )
        user_db_hash = (
            get_dict_hash_normalized(gold_user_state)
            if gold_user_state is not None
            else None
        )
        predicted_user_db_hash = (
            get_dict_hash_normalized(pred_user_state)
            if pred_user_state is not None
            else None
        )
    else:
        agent_db_hash = gold_env.get_db_hash()
        user_db_hash = gold_env.get_user_db_hash()
        predicted_agent_db_hash = predicted_env.get_db_hash()
        predicted_user_db_hash = predicted_env.get_user_db_hash()
    return (
        agent_db_hash,
        predicted_agent_db_hash,
        user_db_hash,
        predicted_user_db_hash,
    )


def _build_assertion_environment(
    environment_constructor: Callable[..., Environment] | None,
    *,
    predicted_environment: Environment,
    solo_mode: bool,
    env_kwargs: dict,
) -> Environment:
    """Build a reference env by projecting the predicted final DB state.

    Construction tasks evaluate Developer-generated toolkits against reference
    assertion helpers. Replaying the generated trajectory through the reference
    toolkit would make public tool names part of the score (for example
    ``reboot_phone`` vs ``reboot_device``), so project final state instead.
    """
    environment = environment_constructor(solo_mode=solo_mode, **env_kwargs)
    if (
        predicted_environment.tools is not None
        and predicted_environment.tools.db is not None
        and environment.tools is not None
        and environment.tools.db is not None
    ):
        environment.tools.update_db(
            _project_db_state_to_reference(
                predicted_environment.tools.db, environment.tools.db
            )
        )
    if (
        predicted_environment.user_tools is not None
        and predicted_environment.user_tools.db is not None
        and environment.user_tools is not None
        and environment.user_tools.db is not None
    ):
        environment.user_tools.update_db(
            _project_db_state_to_reference(
                predicted_environment.user_tools.db, environment.user_tools.db
            )
        )
    environment.sync_tools()
    return environment


def _run_env_assertions(
    *,
    predicted_environment: Environment,
    env_assertions: list[EnvAssertion],
    environment_constructor: Callable[..., Environment] | None,
    initialization_data: InitializationData | None,
    initialization_actions: list[EnvFunctionCall] | None,
    message_history: list[Message],
    solo_mode: bool,
    env_kwargs: dict,
) -> tuple[list[EnvAssertionCheck], float]:
    """Run env assertions, optionally using reference-domain semantics.

    For construction tasks the predicted environment uses the Developer's
    generated toolkit. In that mode, project the predicted final DB state onto
    the reference environment and run reference assertion helpers there. This
    keeps assertion semantics reference-based without requiring generated tool
    names to match reference tool names.
    """
    assertion_environment = predicted_environment
    try:
        if environment_constructor is not None:
            assertion_environment = _build_assertion_environment(
                environment_constructor,
                predicted_environment=predicted_environment,
                solo_mode=solo_mode,
                env_kwargs=env_kwargs,
            )
    except Exception as e:
        logger.warning(f"Error building assertion environment: {e}")
        assertion_environment = None

    env_assertion_checks = []
    env_assertion_reward = 1.0
    for env_assertion in env_assertions:
        success = False
        if assertion_environment is not None:
            success = assertion_environment.run_env_assertion(
                env_assertion,
                raise_assertion_error=False,
            )
        res = EnvAssertionCheck(
            env_assertion=env_assertion,
            met=success,
            reward=1.0 if success else 0.0,
        )
        env_assertion_checks.append(res)
        env_assertion_reward *= res.reward
    return env_assertion_checks, env_assertion_reward


class EnvironmentEvaluator(EvaluatorBase[Message]):
    """
    Evaluator focuses on endstate of the simulation environment.
    """

    @classmethod
    def calculate_reward(
        cls,
        environment_constructor: Callable[[], Environment],
        task: Task,
        full_trajectory: list[
            Message
        ],  # FIXME: It would be better to be able to get only the messages that are after the initial state
        solo_mode: bool = False,
        env_kwargs: dict = None,
        gold_environment_constructor: Callable[[], Environment] | None = None,
        strict_replay: bool = True,
    ) -> RewardInfo:
        """
        Calculate the reward for the simulation.
        Args:
            environment_constructor: Callable[[], Environment]
            task: Task
            full_trajectory: list[Message] (Must include the message history from task initial state)
            solo_mode: bool
            gold_environment_constructor: Optional separate factory for the
                gold environment used to replay golden actions. Used in
                construction-task evaluation, where the developer's toolkit
                may use different tool names than the reference's golden
                actions; we replay the golden actions through the reference
                toolkit instead, then compare DB hashes.
            strict_replay: forwarded to Environment.set_state(strict=...). Set
                False when re-grading historical trajectories whose recorded
                tool outputs may cosmetically differ from current tool code.
        Returns:
            RewardInfo
        """
        if task.evaluation_criteria is None:
            return RewardInfo(
                reward=1.0,
                info={"note": "No evaluation criteria"},
            )
        expected_actions = task.evaluation_criteria.actions
        env_assertions = task.evaluation_criteria.env_assertions
        if expected_actions is None and env_assertions is None:
            return RewardInfo(
                reward=1.0,
                db_check=DBCheck(db_match=True, db_reward=1.0),
                info={"note": "No expected actions or env assertions"},
            )

        initialization_data = None
        if (
            task.initial_state is not None
            and task.initial_state.initialization_data is not None
        ):
            initialization_data = task.initial_state.initialization_data

        initialization_actions = None
        if (
            task.initial_state is not None
            and task.initial_state.initialization_actions is not None
        ):
            initialization_actions = task.initial_state.initialization_actions

        message_history = []
        if (
            task.initial_state is not None
            and task.initial_state.message_history is not None
        ):
            message_history = task.initial_state.message_history

        if env_kwargs is None:
            env_kwargs = {}

        predicted_environment = environment_constructor(
            solo_mode=solo_mode, **env_kwargs
        )

        predicted_environment.set_state(
            initialization_data=initialization_data,
            initialization_actions=initialization_actions,
            message_history=list(full_trajectory),
            strict=strict_replay,
        )

        # Setting up gold environment.
        # Use the dedicated gold constructor if provided (construction tasks).
        gold_constructor = gold_environment_constructor or environment_constructor
        gold_environment = gold_constructor(**env_kwargs)
        gold_environment.set_state(
            initialization_data=initialization_data,
            initialization_actions=initialization_actions,
            message_history=message_history,
            strict=strict_replay,
        )
        golden_actions = task.evaluation_criteria.actions or []
        for action in golden_actions:
            try:
                gold_environment.make_tool_call(
                    action.name,
                    requestor=action.requestor,
                    **action.arguments,
                )
            except Exception as e:
                logger.warning(
                    f"Error in golden actions {action.name}({action.arguments}): {e}"
                )

        # Comparing the environments. When the gold environment uses a
        # different toolkit from the predicted environment (construction
        # tasks), normalize scalar lists before hashing so byte-equality
        # corresponds to semantic equivalence.
        normalize = gold_environment_constructor is not None
        (
            agent_db_hash,
            predicted_agent_db_hash,
            user_db_hash,
            predicted_user_db_hash,
        ) = _hashes_for_compare(
            predicted_environment, gold_environment, normalize=normalize
        )
        agent_db_match = agent_db_hash == predicted_agent_db_hash
        user_db_match = user_db_hash == predicted_user_db_hash
        if agent_db_match and user_db_match:
            db_reward = 1.0
            db_match = True
        else:
            db_reward = 0.0
            db_match = False

        db_check = DBCheck(db_match=db_match, db_reward=db_reward)

        # Run env assertions
        env_assertions = task.evaluation_criteria.env_assertions or []
        env_assertion_checks, env_assertion_reward = _run_env_assertions(
            predicted_environment=predicted_environment,
            env_assertions=env_assertions,
            environment_constructor=gold_environment_constructor,
            initialization_data=initialization_data,
            initialization_actions=initialization_actions,
            message_history=list(full_trajectory),
            solo_mode=solo_mode,
            env_kwargs=env_kwargs,
        )

        reward = 1.0
        reward_breakdown = {}
        if RewardType.DB in task.evaluation_criteria.reward_basis:
            reward_breakdown[RewardType.DB] = db_reward
            reward *= db_reward
        if RewardType.ENV_ASSERTION in task.evaluation_criteria.reward_basis:
            reward_breakdown[RewardType.ENV_ASSERTION] = env_assertion_reward
            reward *= env_assertion_reward

        return RewardInfo(
            reward=reward,
            db_check=db_check,
            env_assertions=env_assertion_checks,
            reward_basis=task.evaluation_criteria.reward_basis,
            reward_breakdown=reward_breakdown,
        )


class FullDuplexEnvironmentEvaluator(EvaluatorBase[Tick]):
    """
    Evaluator focuses on endstate of the simulation environment.
    """

    @classmethod
    def ticks_to_message_history(cls, ticks: list[Tick]) -> list[Message]:
        """
        Convert a list of Ticks to a message history suitable for Environment.set_state().

        The order follows the execution order in FullDuplexOrchestrator:
        - User tool calls are processed before agent tool calls within each tick
        - Each tool call message is followed by its corresponding tool results

        Args:
            ticks: List of Tick objects from full-duplex simulation.

        Returns:
            List of Messages in the format expected by Environment.set_state():
            [UserMessage with tool_calls, ToolMessage results, AssistantMessage with tool_calls, ToolMessage results, ...]
        """
        messages: list[Message] = []

        for tick in ticks:
            # 1. User tool calls first (processed before agent in orchestrator)
            if tick.user_tool_calls:
                user_msg = UserMessage(
                    role="user",
                    content=tick.user_chunk.content if tick.user_chunk else None,
                    tool_calls=tick.user_tool_calls,
                    timestamp=(
                        tick.user_chunk.timestamp if tick.user_chunk else tick.timestamp
                    ),
                    contains_speech=(
                        tick.user_chunk.contains_speech if tick.user_chunk else False
                    ),
                )
                messages.append(user_msg)
                messages.extend(tick.user_tool_results)

            # 2. Agent tool calls second
            if tick.agent_tool_calls:
                agent_msg = AssistantMessage(
                    role="assistant",
                    content=tick.agent_chunk.content if tick.agent_chunk else None,
                    tool_calls=tick.agent_tool_calls,
                    timestamp=(
                        tick.agent_chunk.timestamp
                        if tick.agent_chunk
                        else tick.timestamp
                    ),
                    contains_speech=(
                        tick.agent_chunk.contains_speech if tick.agent_chunk else False
                    ),
                )
                messages.append(agent_msg)
                messages.extend(tick.agent_tool_results)

        return messages

    @classmethod
    def calculate_reward(
        cls,
        environment_constructor: Callable[[], Environment],
        task: Task,
        full_trajectory: list[Tick],
        solo_mode: bool = False,
        env_kwargs: dict = None,
        gold_environment_constructor: Callable[[], Environment] | None = None,
        strict_replay: bool = True,
    ) -> RewardInfo:
        """
        Calculate the reward for the simulation.
        Args:
            environment_constructor: Callable[[], Environment]
            task: Task
            full_trajectory: list[Tick]
            solo_mode: bool
            env_kwargs: dict
            gold_environment_constructor: Optional separate factory for
                replaying golden actions; see the text-mode evaluator.
            strict_replay: forwarded to Environment.set_state(strict=...). Set
                False when re-grading historical trajectories whose recorded
                tool outputs may cosmetically differ from current tool code.
        Returns:
            RewardInfo
        """
        if env_kwargs is None:
            env_kwargs = {}
        if task.evaluation_criteria is None:
            return RewardInfo(
                reward=1.0,
                info={"note": "No evaluation criteria"},
            )
        expected_actions = task.evaluation_criteria.actions
        env_assertions = task.evaluation_criteria.env_assertions
        if expected_actions is None and env_assertions is None:
            return RewardInfo(
                reward=1.0,
                db_check=DBCheck(db_match=True, db_reward=1.0),
                info={"note": "No expected actions or env assertions"},
            )

        initialization_data = None
        if (
            task.initial_state is not None
            and task.initial_state.initialization_data is not None
        ):
            initialization_data = task.initial_state.initialization_data

        initialization_actions = None
        if (
            task.initial_state is not None
            and task.initial_state.initialization_actions is not None
        ):
            initialization_actions = task.initial_state.initialization_actions

        message_history = []
        if (
            task.initial_state is not None
            and task.initial_state.message_history is not None
        ):
            message_history = task.initial_state.message_history

        # Convert ticks to message history for set_state
        # Note: Audio native does not support task history, so we only use the simulation trajectory
        predicted_message_history = cls.ticks_to_message_history(full_trajectory)

        predicted_environment = environment_constructor(
            solo_mode=solo_mode, **env_kwargs
        )
        predicted_environment.set_state(
            initialization_data=initialization_data,
            initialization_actions=initialization_actions,
            message_history=predicted_message_history,
            strict=strict_replay,
        )

        # Setting up gold environment.
        gold_constructor = gold_environment_constructor or environment_constructor
        gold_environment = gold_constructor(**env_kwargs)
        gold_environment.set_state(
            initialization_data=initialization_data,
            initialization_actions=initialization_actions,
            message_history=message_history,
            strict=strict_replay,
        )
        golden_actions = task.evaluation_criteria.actions or []
        for action in golden_actions:
            try:
                gold_environment.make_tool_call(
                    action.name,
                    requestor=action.requestor,
                    **action.arguments,
                )
            except Exception as e:
                logger.warning(
                    f"Error in golden actions {action.name}({action.arguments}): {e}"
                )

        # Comparing the environments. When the gold environment uses a
        # different toolkit from the predicted (construction tasks),
        # normalize scalar lists before hashing.
        normalize = gold_environment_constructor is not None
        (
            agent_db_hash,
            predicted_agent_db_hash,
            user_db_hash,
            predicted_user_db_hash,
        ) = _hashes_for_compare(
            predicted_environment, gold_environment, normalize=normalize
        )
        agent_db_match = agent_db_hash == predicted_agent_db_hash
        user_db_match = user_db_hash == predicted_user_db_hash
        if agent_db_match and user_db_match:
            db_reward = 1.0
            db_match = True
        else:
            db_reward = 0.0
            db_match = False

        db_check = DBCheck(db_match=db_match, db_reward=db_reward)

        # Run env assertions
        env_assertions = task.evaluation_criteria.env_assertions or []
        env_assertion_checks, env_assertion_reward = _run_env_assertions(
            predicted_environment=predicted_environment,
            env_assertions=env_assertions,
            environment_constructor=gold_environment_constructor,
            initialization_data=initialization_data,
            initialization_actions=initialization_actions,
            message_history=predicted_message_history,
            solo_mode=solo_mode,
            env_kwargs=env_kwargs,
        )

        reward = 1.0
        reward_breakdown = {}
        if RewardType.DB in task.evaluation_criteria.reward_basis:
            reward_breakdown[RewardType.DB] = db_reward
            reward *= db_reward
        if RewardType.ENV_ASSERTION in task.evaluation_criteria.reward_basis:
            reward_breakdown[RewardType.ENV_ASSERTION] = env_assertion_reward
            reward *= env_assertion_reward

        return RewardInfo(
            reward=reward,
            db_check=db_check,
            env_assertions=env_assertion_checks,
            reward_basis=task.evaluation_criteria.reward_basis,
            reward_breakdown=reward_breakdown,
        )
