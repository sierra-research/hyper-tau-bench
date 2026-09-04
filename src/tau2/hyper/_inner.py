"""
Shared inner-loop simulation runner for Hyper-τ.

Collapses the near-identical "build env + agent + user + orchestrator,
run, extract reward" blocks that used to live inline in callers into a
single helper pair:

- :func:`run_inner_simulation` — evaluate a single inner-loop τ-bench task
  against a candidate policy.
- :func:`run_inner_simulations` — parallel wrapper over a list of tasks with
  optional stop-event and display-event plumbing.

These helpers are internal to the hyper package.
"""

from __future__ import annotations

import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING, Any, Callable, Optional

from loguru import logger

from tau2.data_model.tasks import EnvFunctionCall, InitializationData, Task
from tau2.environment.environment import Environment
from tau2.environment.tool import Tool
from tau2.evaluator.evaluator import EvaluationType
from tau2.hyper.agent_context import (
    ModelGateway,
    activate_agent_context,
    build_agent_context,
    collect_message_constraint_violations,
    collect_message_credit_usage,
)
from tau2.hyper.data_model import EvaluationResult
from tau2.orchestrator.orchestrator import Orchestrator
from tau2.runner.build import build_agent, build_environment, build_user
from tau2.runner.simulation import run_simulation

if TYPE_CHECKING:
    from tau2.hyper.visualizer import HyperTauDisplay

_DEFAULT_INNER_MAX_WORKERS = 32
_INNER_MAX_WORKERS_ENV = "TAU2_HYPER_INNER_MAX_WORKERS"

# Transient provider failures (503s, rate limits, socket resets) must not be
# scored as task failures: the 2026-08-27 final-12 construction batch zeroed
# four tasks across three runs on litellm ServiceUnavailableError before the
# conversation ever started. Retry them with backoff; only exhausted retries
# (or genuine task-execution exceptions) synthesize a zero-reward result.
_TRANSIENT_ERROR_MAX_ATTEMPTS = 3
_TRANSIENT_ERROR_BACKOFF_SECONDS = (5.0, 15.0)

# Matched against every class name in the exception's MRO, so litellm and
# openai/httpx variants classify without importing either library here.
# openai's base APIError is deliberately absent: it is also the ancestor of
# non-retryable errors (e.g. BadRequestError).
_TRANSIENT_PROVIDER_ERROR_TYPE_NAMES = frozenset(
    {
        "ServiceUnavailableError",
        "InternalServerError",
        "RateLimitError",
        "APIConnectionError",
        "APITimeoutError",
        "Timeout",
        "ReadTimeout",
        "ConnectTimeout",
        "ConnectError",
        "RemoteProtocolError",
    }
)

# Message fallback for provider errors that surface re-wrapped in generic
# exception types. Matched case-insensitively; mirrors the sandbox builder's
# `_TRANSIENT_LLM_ERROR_KEYWORDS`.
_TRANSIENT_PROVIDER_ERROR_KEYWORDS = (
    "overloaded",
    "rate limit",
    "ratelimit",
    "rate_limit",
    "timeout",
    "timed out",
    "temporarily unavailable",
    "service unavailable",
    "serviceunavailable",
    "internalservererror",
    "bad gateway",
    "econnreset",
    "connection reset",
    "temporary failure in name resolution",
)


def _is_transient_provider_error(error: BaseException) -> bool:
    """Whether an exception is a retryable provider/network failure."""
    seen: set[int] = set()
    current: Optional[BaseException] = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if any(
            cls.__name__ in _TRANSIENT_PROVIDER_ERROR_TYPE_NAMES
            for cls in type(current).__mro__
        ):
            return True
        message = str(current).lower()
        if any(keyword in message for keyword in _TRANSIENT_PROVIDER_ERROR_KEYWORDS):
            return True
        current = current.__cause__ or current.__context__
    return False


def _format_eval_error(kind: str, error: Exception) -> str:
    """Render an exception into the ``EvaluationResult.error`` tag."""
    message = str(error) or type(error).__name__
    if len(message) > 500:
        message = message[:500] + "..."
    return f"{kind}: {type(error).__name__}: {message}"


def _resolve_inner_max_workers(
    total: int, requested_max_workers: Optional[int] = None
) -> int:
    """Resolve inner-loop evaluation concurrency from args or environment."""
    if total <= 0:
        return 0

    resolved = requested_max_workers
    if resolved is None:
        raw_value = os.environ.get(_INNER_MAX_WORKERS_ENV)
        if raw_value:
            try:
                resolved = int(raw_value)
            except ValueError:
                logger.warning(
                    f"Ignoring invalid {_INNER_MAX_WORKERS_ENV}={raw_value!r}; "
                    f"using default {_DEFAULT_INNER_MAX_WORKERS}"
                )
                resolved = _DEFAULT_INNER_MAX_WORKERS
        else:
            resolved = _DEFAULT_INNER_MAX_WORKERS

    return min(total, max(1, resolved))


def _instantiate_custom_agent(
    agent_factory: Callable,
    *,
    domain: str,
    tools: list[Tool],
    resource_root: Optional[Path] = None,
    model_configs: list[dict],
) -> tuple[Any, ModelGateway]:
    """Call a zero-argument custom factory with run-scoped facilities."""
    resolved_resource_root = resource_root or getattr(
        agent_factory, "__tau2_resource_root__", None
    )
    if resolved_resource_root is None:
        source_file = agent_factory.__globals__.get("__file__")
        resolved_resource_root = Path(source_file).parent if source_file else Path.cwd()
    context = build_agent_context(
        domain=domain,
        tools=tools,
        resource_root=Path(resolved_resource_root),
        model_configs=model_configs,
    )
    with activate_agent_context(context):
        agent = agent_factory()
    if not callable(getattr(agent, "get_init_state", None)) or not callable(
        getattr(agent, "generate_next_message", None)
    ):
        raise TypeError(
            "create_agent() must return an object with get_init_state() and "
            "generate_next_message()"
        )
    return agent, context.model_gateway


def _extract_eval_result(
    task_id: str,
    sim,
    *,
    agent_credit_usage: Optional[dict] = None,
    agent_constraint_violations: Optional[dict] = None,
) -> EvaluationResult:
    """Project a ``SimulationResult`` into a hyper ``EvaluationResult``."""
    reward = sim.reward_info.reward if sim.reward_info else 0.0
    reward_breakdown = None
    nl_assertion_details = None
    response_assertion_details = None
    if sim.reward_info:
        if sim.reward_info.reward_breakdown:
            reward_breakdown = {
                str(k): v for k, v in sim.reward_info.reward_breakdown.items()
            }
        if sim.reward_info.nl_assertions:
            nl_assertion_details = [
                {
                    "assertion": nla.nl_assertion,
                    "met": nla.met,
                    "justification": nla.justification,
                }
                for nla in sim.reward_info.nl_assertions
            ]
        if sim.reward_info.response_assertions:
            response_assertion_details = [
                {
                    "assertion": check.response_assertion.model_dump(mode="json"),
                    "met": check.met,
                    "justification": check.justification,
                }
                for check in sim.reward_info.response_assertions
            ]
    return EvaluationResult(
        task_id=task_id,
        reward=reward,
        messages=sim.messages or [],
        reward_breakdown=reward_breakdown,
        nl_assertion_details=nl_assertion_details,
        response_assertion_details=response_assertion_details,
        agent_credit_usage=agent_credit_usage,
        agent_constraint_violations=agent_constraint_violations,
    )


def _apply_client_api_mock_report(
    result: EvaluationResult,
    report: Optional[dict[str, Any]],
) -> None:
    """Attach a local mock report and fail the result on mock-side errors."""
    result.client_api_mock_report = report
    report = report or {}
    verification_failed = report.get("verification", {}).get("status") == "failed"
    request_failed = any("error" in entry for entry in report.get("trace", []))
    if verification_failed or request_failed:
        result.reward = 0.0
        result.reward_breakdown = {
            **(result.reward_breakdown or {}),
            "CLIENT_API_MOCK": 0.0,
        }


def _apply_client_api_defect_report(
    result: EvaluationResult,
    report: Optional[dict[str, Any]],
) -> None:
    """Attach trusted defect telemetry and enforce configured ordering checks."""

    result.client_api_defect_report = report
    if (report or {}).get("verification", {}).get("status") == "failed":
        result.reward = 0.0
        result.reward_breakdown = {
            **(result.reward_breakdown or {}),
            "CLIENT_API_DEFECT": 0.0,
        }


def _apply_discoverable_grounding(
    result: EvaluationResult,
    task: Task,
    classification: tuple[frozenset[str], frozenset[str]],
) -> None:
    """Fold the discoverable-call grounding check into one sim's reward.

    Mirrors how the reference domain graded the same behavior: the audit
    rows lived in the agent DB, so a row-set mismatch zeroed the DB
    component and with it the whole product. The check therefore only
    gates tasks whose ``reward_basis`` includes ``RewardType.DB``.
    """
    from tau2.data_model.tasks import RewardType
    from tau2.hyper.grounding import grounding_check_for_simulation

    discoverable_names, mutating_names = classification
    check = grounding_check_for_simulation(
        task,
        result.messages,
        discoverable_names=discoverable_names,
        mutating_names=mutating_names,
    )
    if check is None:
        return
    result.grounding_details = check.model_dump(mode="json")
    criteria = task.evaluation_criteria
    if criteria is None or RewardType.DB not in criteria.reward_basis:
        return
    breakdown = dict(result.reward_breakdown or {})
    breakdown["GROUNDING"] = 1.0 if check.passed else 0.0
    result.reward_breakdown = breakdown
    if not check.passed:
        result.reward = 0.0
        logger.debug(
            f"Grounding check failed for {task.id}: "
            f"missing={check.missing} extra_mutating={check.extra_mutating}"
        )


def _dump_environment_state(environment: "Environment") -> InitializationData:
    """Return full JSON-compatible DB state for both sides of an environment."""
    agent_data = None
    user_data = None
    if environment.tools is not None and environment.tools.db is not None:
        agent_data = environment.tools.db.model_dump(mode="json")
    if environment.user_tools is not None and environment.user_tools.db is not None:
        user_data = environment.user_tools.db.model_dump(mode="json")
    return InitializationData(agent_data=agent_data, user_data=user_data)


def _clone_environment(environment: Environment, *, solo_mode: bool) -> Environment:
    """Clone an environment, honoring sealed remote environment factories."""
    clone = getattr(environment, "clone", None)
    if callable(clone):
        return clone(solo_mode=solo_mode)
    copied = deepcopy(environment)
    copied.solo_mode = solo_mode
    return copied


def _materialize_reference_setup(
    *,
    task: Task,
    reference_environment_constructor: Callable[..., "Environment"],
    solo_mode: bool,
    env_kwargs: dict,
) -> Task:
    """Rewrite private setup actions into concrete DB initialization data.

    Construction tasks should evaluate the developer's visible runtime tools and
    policy, not whether their private setup helper signatures match the
    canonical implementation. We therefore apply task initialization
    data/actions through the canonical domain once, serialize the resulting DBs,
    and run the
    developer environment from that materialized state.

    Message history is intentionally not replayed here. It remains on the task
    and is replayed by the orchestrator/evaluator as usual.
    """
    initial_state = task.initial_state
    if initial_state is None:
        return task

    initialization_data = initial_state.initialization_data
    initialization_actions = initial_state.initialization_actions
    if initialization_data is None and not initialization_actions:
        return task

    reference_environment = reference_environment_constructor(
        solo_mode=solo_mode, **env_kwargs
    )
    reference_environment.set_state(
        initialization_data=initialization_data,
        initialization_actions=initialization_actions,
        message_history=[],
    )
    materialized_initial_state = initial_state.model_copy(
        update={
            "initialization_data": _dump_environment_state(reference_environment),
            "initialization_actions": None,
        }
    )
    return task.model_copy(update={"initial_state": materialized_initial_state})


def run_inner_simulation(
    *,
    domain: str,
    task: Task,
    policy: str,
    agent_llm: str,
    user_llm: str,
    agent_llm_args: Optional[dict] = None,
    allowed_agent_models: Optional[list[dict]] = None,
    user_llm_args: Optional[dict] = None,
    max_steps: int = 200,
    max_errors: int = 5,
    agent_factory: Optional[Callable] = None,
    custom_environment: Optional["Environment"] = None,
    use_reference_gold_environment: bool = False,
    developer_setup_actions: Optional[list[EnvFunctionCall]] = None,
    development_fixture: Optional[str | list[str]] = None,
    client_api_execution_mode: str = "final_evaluation",
    client_api_developer_test_scenario_id: Optional[str] = None,
) -> EvaluationResult:
    """Run a single inner-loop τ-bench simulation.

    Builds a fresh environment for ``domain`` with the candidate ``policy``,
    instantiates an LLM agent and user simulator, runs the half-duplex
    orchestrator, and extracts an :class:`EvaluationResult`.

    Args:
        domain: τ-bench domain name (e.g. ``"retail"``).
        task: The inner-loop task to evaluate on.
        policy: Candidate policy text; overrides the environment's default.
        agent_llm: LLM model for the inner-loop Agent.
        user_llm: LLM model for the inner-loop User simulator.
        agent_llm_args: Optional LLM kwargs for the Agent.
        allowed_agent_models: Model-specific constraints available to a custom
            Agent.
        user_llm_args: Optional LLM kwargs for the User simulator.
        max_steps: Max orchestrator steps.
        max_errors: Max tool errors before aborting.
        agent_factory: Optional callable ``(context)`` that returns a
            ``HalfDuplexAgent``. The context contains the available actions,
            kit resources, model gateway, and runtime configuration. When
            provided, used instead of the stock ``LLMAgent``. This is how
            sandbox mode loads a developer's custom agent implementation.
        custom_environment: Optional pre-built :class:`Environment` to use
            instead of building from the domain registry. Used by
            construction tasks where the Developer provides the toolkit.
        use_reference_gold_environment: If ``True``, replay golden actions
            during scoring against the canonical domain environment
            (loaded via the registry from ``domain``) rather than against
            ``custom_environment``. This decouples scoring from the
            developer's tool naming — the developer can call their
            ``modify_pending_order_payment`` function ``update_payment``
            without losing reward, since the gold DB state is computed by
            running the canonical golden actions through the internal
            toolkit. Only meaningful when ``custom_environment`` is set;
            ignored otherwise.
        developer_setup_actions: Optional local-test-only assistant setup calls.
            These execute through the Developer's candidate toolkit after its
            Client API context is initialized, never through the private Client
            environment.
        development_fixture: Optional named host-owned local fixture(s). The
            fixtures are applied to the fresh Client environment in listed
            order without exposing its private state shape or setup functions
            to the Developer.
        client_api_execution_mode: Explicit host-only activation mode for the
            Client API runtime. Final scoring uses ``final_evaluation``;
            Developer-authored scenarios use ``developer_test``.
        client_api_developer_test_scenario_id: Host-computed stable digest used
            to sample a Developer-test deployment cohort. Never enters the kit.
    """
    if custom_environment is not None:
        env_kwargs: dict = {}
        gold_environment_constructor = None
        if use_reference_gold_environment:
            from tau2.registry import registry

            reference_environment_constructor = registry.get_env_constructor(domain)
            task = _materialize_reference_setup(
                task=task,
                reference_environment_constructor=reference_environment_constructor,
                solo_mode=False,
                env_kwargs=env_kwargs,
            )

            def gold_environment_constructor(solo_mode=False, **_kwargs):
                return reference_environment_constructor(solo_mode=solo_mode)

        base_environment = custom_environment

        def build_runtime_environment(solo_mode=False) -> Environment:
            copied = _clone_environment(base_environment, solo_mode=solo_mode)
            copied.policy = policy
            configure_trial = getattr(
                copied,
                "configure_client_api_trial_context",
                None,
            )
            if callable(configure_trial):
                configure_trial(
                    task_id=task.id,
                    execution_mode=client_api_execution_mode,
                    developer_test_scenario_id=(
                        client_api_developer_test_scenario_id
                        if client_api_execution_mode == "developer_test"
                        else None
                    ),
                )
            if development_fixture:
                configure_fixture = getattr(
                    copied, "configure_development_fixture", None
                )
                if not callable(configure_fixture):
                    raise RuntimeError(
                        "Development fixtures require a sealed candidate environment"
                    )
                configure_fixture(development_fixture)
            if developer_setup_actions:
                configure_setup = getattr(
                    copied, "configure_developer_setup_actions", None
                )
                if not callable(configure_setup):
                    raise RuntimeError(
                        "Developer setup actions require a sealed candidate environment"
                    )
                configure_setup(developer_setup_actions)
            return copied

        environment = build_runtime_environment(solo_mode=False)

        def evaluation_environment_constructor(solo_mode=False, **_kwargs):
            return build_runtime_environment(solo_mode=solo_mode)

    else:
        environment = build_environment(domain)
        environment.policy = policy
        evaluation_environment_constructor = None
        gold_environment_constructor = None

    tools = environment.get_tools()
    model_gateway = None
    if agent_factory:
        model_configs = allowed_agent_models or [
            {
                "model": agent_llm,
                "constraints": dict(agent_llm_args or {}),
            }
        ]
        agent, model_gateway = _instantiate_custom_agent(
            agent_factory,
            domain=domain,
            tools=tools,
            model_configs=model_configs,
        )
    else:
        agent = build_agent(
            "llm_agent",
            environment,
            llm=agent_llm,
            llm_args=agent_llm_args,
        )
    user = build_user(
        "user_simulator",
        environment,
        task,
        llm=user_llm,
        llm_args=user_llm_args or {},
    )

    orchestrator = Orchestrator(
        domain=domain,
        agent=agent,
        user=user,
        environment=environment,
        task=task,
        max_steps=max_steps,
        max_errors=max_errors,
    )

    try:
        sim = run_simulation(
            orchestrator,
            evaluation_type=EvaluationType.ALL_WITH_NL_ASSERTIONS,
            environment_constructor=evaluation_environment_constructor,
            gold_environment_constructor=gold_environment_constructor,
        )
    except Exception as error:
        collect_mock_report = getattr(
            environment,
            "collect_client_api_mock_report",
            None,
        )
        if callable(collect_mock_report):
            try:
                error.client_api_mock_report = collect_mock_report()
            except Exception:
                pass
        raise

    agent_constraint_violations = None
    if model_gateway is not None:
        agent_credit_usage = model_gateway.credit_usage
        agent_constraint_violations = model_gateway.constraint_violations
    elif allowed_agent_models:
        stock_config = next(
            (config for config in allowed_agent_models if config["model"] == agent_llm),
            allowed_agent_models[0],
        )
        agent_credit_usage = collect_message_credit_usage(
            sim.messages or [],
            stock_config,
        )
        agent_constraint_violations = collect_message_constraint_violations(
            sim.messages or [],
            stock_config,
        )
    else:
        agent_credit_usage = None
    result = _extract_eval_result(
        task.id,
        sim,
        agent_credit_usage=agent_credit_usage,
        agent_constraint_violations=agent_constraint_violations,
    )
    collect_mock_report = getattr(
        environment,
        "collect_client_api_mock_report",
        None,
    )
    if callable(collect_mock_report):
        _apply_client_api_mock_report(result, collect_mock_report())
    collect_defect_report = getattr(
        environment,
        "collect_client_api_defect_report",
        None,
    )
    if callable(collect_defect_report):
        _apply_client_api_defect_report(result, collect_defect_report())
    return result


def run_inner_simulations(
    tasks: list[Task],
    *,
    domain: str,
    policy: str,
    agent_llm: str,
    user_llm: str,
    agent_llm_args: Optional[dict] = None,
    allowed_agent_models: Optional[list[dict]] = None,
    user_llm_args: Optional[dict] = None,
    max_steps: int = 200,
    max_errors: int = 5,
    agent_factory: Optional[Callable] = None,
    custom_environment: Optional["Environment"] = None,
    use_reference_gold_environment: bool = False,
    client_api_mode: Optional[str] = None,
    stop_event: Optional[Event] = None,
    display: Optional["HyperTauDisplay"] = None,
    eval_kind: str = "train",
    max_workers: Optional[int] = None,
) -> list[EvaluationResult]:
    """Run :func:`run_inner_simulation` for each task in parallel.

    Preserves input task order in the returned list. Transient provider
    errors (5xx, rate limits, connection/timeout failures) are retried with
    backoff up to ``_TRANSIENT_ERROR_MAX_ATTEMPTS`` attempts; a task that
    still fails — or raises a genuine task-execution exception, which is
    never retried — returns a zero-reward :class:`EvaluationResult` whose
    ``error`` field distinguishes ``infrastructure_error`` zeros from
    ``task_error`` zeros (logged via ``loguru``).

    Args:
        tasks: Tasks to evaluate. Must be non-empty.
        domain, policy, agent_llm, user_llm, agent_llm_args, user_llm_args,
            max_steps, max_errors: Passed through to
            :func:`run_inner_simulation`.
        client_api_mode: The scored task's Client API mode. When ``"rest"``
            (and a ``custom_environment`` is being scored), each simulation
            additionally runs the discoverable-call grounding check — the
            trace-level restatement of the reference domain's
            ``agent_discoverable_tools`` row-set grading, which construction
            DB comparison strips (see :mod:`tau2.hyper.grounding`).
        stop_event: When set, pending tasks return zero-reward without
            running.
        display: Optional ``HyperTauDisplay`` that receives
            ``show_eval_task_start`` / ``show_eval_task_complete`` events.
        eval_kind: Label passed to display events; one of ``"train"``,
            ``"test"``, or ``"regression"``.
        max_workers: Optional per-call concurrency cap. When omitted,
            ``TAU2_HYPER_INNER_MAX_WORKERS`` can override the default of 32.
    """
    if not tasks:
        return []

    grounding_classification = None
    if client_api_mode == "rest" and custom_environment is not None:
        from tau2.hyper.grounding import reference_discoverable_classification

        try:
            grounding_classification = reference_discoverable_classification(domain)
        except Exception as error:
            # A domain without discoverable tools (or without a registry
            # entry visible here) simply has nothing to ground-check.
            logger.warning(
                f"Discoverable grounding disabled for domain {domain!r}: {error}"
            )
        if grounding_classification is not None and not grounding_classification[0]:
            grounding_classification = None

    total = len(tasks)

    if display is not None and hasattr(display, "show_eval_task_start"):
        for i, t in enumerate(tasks):
            display.show_eval_task_start(t.id, eval_kind, i, total)

    def _run_one(task: Task) -> EvaluationResult:
        if stop_event is not None and stop_event.is_set():
            return EvaluationResult(task_id=task.id, reward=0.0, messages=[])
        for attempt in range(1, _TRANSIENT_ERROR_MAX_ATTEMPTS + 1):
            try:
                result = run_inner_simulation(
                    domain=domain,
                    task=task,
                    policy=policy,
                    agent_llm=agent_llm,
                    user_llm=user_llm,
                    agent_llm_args=agent_llm_args,
                    allowed_agent_models=allowed_agent_models,
                    user_llm_args=user_llm_args,
                    max_steps=max_steps,
                    max_errors=max_errors,
                    agent_factory=agent_factory,
                    custom_environment=custom_environment,
                    use_reference_gold_environment=use_reference_gold_environment,
                )
                if grounding_classification is not None:
                    _apply_discoverable_grounding(
                        result, task, grounding_classification
                    )
                return result
            except Exception as e:
                transient = _is_transient_provider_error(e)
                if transient and attempt < _TRANSIENT_ERROR_MAX_ATTEMPTS:
                    delay = _TRANSIENT_ERROR_BACKOFF_SECONDS[
                        min(attempt - 1, len(_TRANSIENT_ERROR_BACKOFF_SECONDS) - 1)
                    ]
                    logger.warning(
                        f"Transient provider error on {eval_kind} task {task.id} "
                        f"(attempt {attempt}/{_TRANSIENT_ERROR_MAX_ATTEMPTS}), "
                        f"retrying in {delay:.0f}s: {e}"
                    )
                    if stop_event is not None:
                        if stop_event.wait(delay):
                            # Cancelled mid-backoff: match the pre-start stop
                            # path (untagged zero) rather than recording the
                            # cancellation as an exhausted-retries infra zero.
                            return EvaluationResult(
                                task_id=task.id, reward=0.0, messages=[]
                            )
                    else:
                        time.sleep(delay)
                    continue
                logger.error(f"Error evaluating {eval_kind} task {task.id}: {e}")
                logger.error(traceback.format_exc())
                kind = "infrastructure_error" if transient else "task_error"
                return EvaluationResult(
                    task_id=task.id,
                    reward=0.0,
                    messages=[],
                    error=_format_eval_error(kind, e),
                )
        raise AssertionError("unreachable: retry loop always returns")

    # Cap concurrency: spawning one thread per task can exhaust file
    # descriptors / sockets under LiteLLM, producing "Bad file descriptor"
    # errors and hung futures that wedge the whole run (we've observed this
    # on the 114-task retail eval). The environment override lets long GPT-5.x
    # scoring runs trade wall-clock time for fewer provider/socket resets.
    max_workers = _resolve_inner_max_workers(total, max_workers)
    results: list[EvaluationResult] = []
    passed = 0
    reward_sum = 0.0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_run_one, t): t for t in tasks}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            passed += int(result.reward >= 1.0)
            reward_sum += result.reward
            completed = len(results)
            logger.info(
                f"{eval_kind.capitalize()} progress: {completed}/{total} completed, "
                f"{passed} passed ({passed / completed:.1%}), "
                f"mean reward={reward_sum / completed:.3f}"
            )
            if display is not None and hasattr(display, "show_eval_task_complete"):
                try:
                    display.show_eval_task_complete(
                        result.task_id,
                        eval_kind,
                        result.reward,
                        result.reward >= 1.0,
                    )
                except Exception as exc:
                    logger.error(
                        f"Failed to record {eval_kind} task {result.task_id}: {exc}"
                    )

    order = {t.id: i for i, t in enumerate(tasks)}
    results.sort(key=lambda r: order.get(r.task_id, 999))
    return results


def project_messages(messages: list) -> list[dict]:
    """Serialize trajectory messages into the compact recording format.

    Each entry has ``role``, ``content``, and (for assistant tool-call
    messages) ``tool_calls`` with ``name`` / ``arguments`` per call.

    Equivalent to the legacy ``_serialize_trajectory`` but expressed as a
    projection over ``Message.model_dump(exclude_none=True)``.
    """
    trajectory: list[dict] = []
    for msg in messages:
        dumped = msg.model_dump(exclude_none=True) if hasattr(msg, "model_dump") else {}
        role = dumped.get("role") or getattr(msg, "role", "")
        content = dumped.get("content") or getattr(msg, "content", None)
        tool_calls = dumped.get("tool_calls") or getattr(msg, "tool_calls", None)

        entry: dict = {"role": role}
        if role == "assistant" and tool_calls:
            entry["tool_calls"] = [
                {
                    "name": (
                        tc.get("name")
                        if isinstance(tc, dict)
                        else getattr(tc, "name", "unknown")
                    ),
                    "arguments": (
                        tc.get("arguments")
                        if isinstance(tc, dict)
                        else getattr(tc, "arguments", {})
                    ),
                }
                for tc in tool_calls
            ]
            if content:
                entry["content"] = content
        else:
            entry["content"] = content or ""
        trajectory.append(entry)
    return trajectory
