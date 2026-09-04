import json
import logging
import os
import re
import time
import uuid
import warnings
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx
import litellm
from litellm import completion, completion_cost
from litellm.caching.caching import Cache
from litellm.main import ModelResponse, Usage
from loguru import logger

from tau2.config import (
    DEFAULT_LLM_CACHE_TYPE,
    DEFAULT_MAX_RETRIES,
    LLM_CACHE_ENABLED,
    REDIS_CACHE_TTL,
    REDIS_CACHE_VERSION,
    REDIS_HOST,
    REDIS_PASSWORD,
    REDIS_PORT,
    REDIS_PREFIX,
    USE_LANGFUSE,
)
from tau2.data_model.message import (
    AssistantMessage,
    Message,
    MultiToolMessage,
    ParticipantMessageBase,
    SystemMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from tau2.environment.tool import Tool
from tau2.utils.model_routing import ModelRoute, resolve_model

# Suppress Pydantic serialization warnings from LiteLLM
# These occur due to type mismatches between streaming and non-streaming response types
warnings.filterwarnings(
    "ignore",
    message="Pydantic serializer warnings:",
    category=UserWarning,
)

# Configure httpx connection limits for LiteLLM
httpx_limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
litellm.client_session = httpx.Client(limits=httpx_limits)
litellm.aclient_session = httpx.AsyncClient(limits=httpx_limits)

# Context variable to store the directory where LLM debug logs should be written
llm_log_dir: ContextVar[Optional[Path]] = ContextVar("llm_log_dir", default=None)

# Context variable to store the LLM logging mode ("all" or "latest")
llm_log_mode: ContextVar[str] = ContextVar("llm_log_mode", default="latest")

# litellm._turn_on_debug()

logging.getLogger("LiteLLM").setLevel(logging.WARNING)

if USE_LANGFUSE:
    litellm.success_callback = ["langfuse"]
else:
    litellm.success_callback = []

litellm.drop_params = True

warnings.filterwarnings(
    "ignore",
    message="Pydantic serializer warnings:",
    category=UserWarning,
)

_TRANSIENT_LLM_ERROR_KEYWORDS = (
    "bad gateway",
    "connection aborted",
    "connection reset by peer",
    "econnreset",
    "gateway timeout",
    "internal server error",
    "internalservererror",
    "overloaded",
    "overloaded_error",
    "rate limit",
    "rate_limit",
    "ratelimit",
    "remote end closed connection",
    "server disconnected",
    "service unavailable",
    "temporarily unavailable",
    "temporary failure in name resolution",
    "timed out",
    "timeout",
)

_DEFAULT_LITELLM_REQUEST_TIMEOUT_SECONDS = 600.0

# Reasoning models at high efforts occasionally return a completion with only
# reasoning tokens — no visible content and no tool calls. Such a message
# fails AssistantMessage.validate() downstream and would abort the whole
# simulation, so the single turn is re-requested up to this many total
# attempts before giving up.
EMPTY_COMPLETION_MAX_ATTEMPTS = 4


class EmptyCompletionError(RuntimeError):
    """The model returned no visible content or tool calls after bounded retries."""


def _is_transient_llm_error(exc: Exception) -> bool:
    """Return True for provider/network errors that are worth retrying."""
    error_text = f"{type(exc).__name__}: {exc}".lower()
    return any(keyword in error_text for keyword in _TRANSIENT_LLM_ERROR_KEYWORDS)


def _is_empty_completion(
    content: Optional[str], tool_calls: Optional[list[ToolCall]]
) -> bool:
    """Return True when a completion has neither visible content nor tool calls.

    Mirrors AssistantMessage.validate(): whitespace-only content counts as empty.
    """
    has_text = content is not None and bool(content.strip())
    return not has_text and not tool_calls


def _request_timeout_seconds_from_env() -> float | None:
    """Return the LiteLLM request timeout, or None when explicitly disabled."""
    raw_timeout = os.environ.get("LITELLM_REQUEST_TIMEOUT")
    if raw_timeout is None or raw_timeout == "":
        return _DEFAULT_LITELLM_REQUEST_TIMEOUT_SECONDS
    try:
        timeout_seconds = float(raw_timeout)
    except ValueError:
        logger.warning(
            "Ignoring invalid LITELLM_REQUEST_TIMEOUT value "
            f"{raw_timeout!r}; using "
            f"{_DEFAULT_LITELLM_REQUEST_TIMEOUT_SECONDS:g}s"
        )
        return _DEFAULT_LITELLM_REQUEST_TIMEOUT_SECONDS
    if timeout_seconds <= 0:
        return None
    return timeout_seconds


def _apply_default_request_timeout(kwargs: dict[str, Any]) -> None:
    """Apply the default LiteLLM timeout unless the caller supplied one."""
    if "timeout" in kwargs or "request_timeout" in kwargs:
        return
    timeout_seconds = _request_timeout_seconds_from_env()
    if timeout_seconds is not None:
        kwargs["timeout"] = timeout_seconds


if LLM_CACHE_ENABLED:
    if DEFAULT_LLM_CACHE_TYPE == "redis":
        logger.info(f"LiteLLM: Using Redis cache at {REDIS_HOST}:{REDIS_PORT}")
        litellm.cache = Cache(
            type=DEFAULT_LLM_CACHE_TYPE,
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            namespace=f"{REDIS_PREFIX}:{REDIS_CACHE_VERSION}:litellm",
            ttl=REDIS_CACHE_TTL,
        )
    elif DEFAULT_LLM_CACHE_TYPE == "local":
        logger.info("LiteLLM: Using local cache")
        litellm.cache = Cache(
            type="local",
            ttl=REDIS_CACHE_TTL,
        )
    else:
        raise ValueError(
            f"Invalid cache type: {DEFAULT_LLM_CACHE_TYPE}. Should be 'redis' or 'local'"
        )
    litellm.enable_cache()
else:
    logger.info("LiteLLM: Cache is disabled")
    litellm.disable_cache()

# LiteLLM prints a red "Provider List: ..." banner to stdout whenever its
# price table has no entry for a model (every OpenRouter-served id, for one).
# It is not an error for us: Hyper-τ credits are metered from the task's
# bucket rates, and get_response_cost() already falls back to 0.0.
litellm.suppress_debug_info = True


def _parse_ft_model_name(model: str) -> str:
    """
    Parse the ft model name from the litellm model name.
    e.g: "ft:gpt-4.1-mini-2025-04-14:sierra::BSQA2TFg" -> "gpt-4.1-mini-2025-04-14"
    """
    pattern = r"ft:(?P<model>[^:]+):(?P<provider>\w+)::(?P<id>\w+)"
    match = re.match(pattern, model)
    if match:
        return match.group("model")
    else:
        return model


_UNPRICED_MODELS_REPORTED: set[str] = set()


def get_response_cost(response: ModelResponse) -> float:
    """
    Get the cost of the response from the litellm completion.

    Returns 0.0 when LiteLLM has no price entry for the served model. That is
    routine for OpenRouter-served ids, so it is reported once per model at
    debug level rather than as an error on every call.
    """
    response.model = _parse_ft_model_name(
        response.model
    )  # FIXME: Check Litellm, passing the model to completion_cost doesn't work.
    try:
        cost = completion_cost(completion_response=response)
    except Exception as e:
        model = str(getattr(response, "model", "") or "")
        if model not in _UNPRICED_MODELS_REPORTED:
            _UNPRICED_MODELS_REPORTED.add(model)
            logger.debug(
                f"LiteLLM has no price entry for {model!r}; recording cost 0.0 "
                f"for this and later calls ({type(e).__name__})"
            )
        return 0.0
    return cost


def get_response_usage(response: ModelResponse) -> Optional[dict]:
    usage: Optional[Usage] = response.get("usage")
    if usage is None:
        return None
    return {
        "completion_tokens": usage.completion_tokens,
        "prompt_tokens": usage.prompt_tokens,
    }


def to_tau2_messages(
    messages: list[dict], ignore_roles: set[str] = set()
) -> list[Message]:
    """
    Convert a list of messages from a dictionary to a list of Tau2 messages.
    """
    tau2_messages = []
    for message in messages:
        role = message["role"]
        if role in ignore_roles:
            continue
        if role == "user":
            tau2_messages.append(UserMessage(**message))
        elif role == "assistant":
            tau2_messages.append(AssistantMessage(**message))
        elif role == "tool":
            tau2_messages.append(ToolMessage(**message))
        elif role == "system":
            tau2_messages.append(SystemMessage(**message))
        else:
            raise ValueError(f"Unknown message type: {role}")
    return tau2_messages


def to_litellm_messages(messages: list[Message]) -> list[dict]:
    """
    Convert a list of Tau2 messages to a list of litellm messages.
    """
    litellm_messages = []
    for message in messages:
        if isinstance(message, UserMessage):
            litellm_messages.append({"role": "user", "content": message.content})
        elif isinstance(message, AssistantMessage):
            tool_calls = None
            if message.is_tool_call():
                tool_calls = [
                    {
                        "id": tc.id,
                        "name": tc.name,
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                        "type": "function",
                    }
                    for tc in message.tool_calls
                ]
            litellm_messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": tool_calls,
                }
            )
        elif isinstance(message, ToolMessage):
            litellm_messages.append(
                {
                    "role": "tool",
                    "content": message.content,
                    "tool_call_id": message.id,
                }
            )
        elif isinstance(message, SystemMessage):
            litellm_messages.append({"role": "system", "content": message.content})
    return litellm_messages


def validate_message(message: Message) -> None:
    """
    Validate the message.
    """

    def has_text_content(message: Message) -> bool:
        """
        Check if the message has text content.
        """
        return message.content is not None and bool(message.content.strip())

    def has_content_or_tool_calls(message: ParticipantMessageBase) -> bool:
        """
        Check if the message has content or tool calls.
        """
        return message.has_content() or message.is_tool_call()

    if isinstance(message, SystemMessage):
        assert has_text_content(message), (
            f"System message must have content. got {message}"
        )
    if isinstance(message, ParticipantMessageBase):
        assert has_content_or_tool_calls(message), (
            f"Message must have content or tool calls. got {message}"
        )


def validate_message_history(messages: list[Message]) -> None:
    """
    Validate the message history.
    """
    for message in messages:
        validate_message(message)


def set_llm_log_dir(log_dir: Optional[Path | str]) -> None:
    """
    Set the directory where LLM debug logs should be written.

    Args:
        log_dir: Path to the directory where logs should be saved, or None to disable file logging
    """
    if isinstance(log_dir, str):
        log_dir = Path(log_dir)
    llm_log_dir.set(log_dir)


def set_llm_log_mode(mode: str) -> None:
    """
    Set the LLM debug logging mode.

    Args:
        mode: Logging mode - "all" to save every LLM call, "latest" to keep only the most recent call of each type
    """
    if mode not in ("all", "latest"):
        raise ValueError(f"Invalid LLM log mode: {mode}. Must be 'all' or 'latest'")
    llm_log_mode.set(mode)


def _format_messages_for_logging(messages: list[dict]) -> list[dict]:
    """
    Format messages for debug logging by splitting content on newlines.

    Args:
        messages: List of litellm message dictionaries

    Returns:
        Modified message list with content split into lines for readability
    """
    formatted = []
    for msg in messages:
        msg_copy = msg.copy()
        if "content" in msg_copy and isinstance(msg_copy["content"], str):
            # Split content on newlines for better readability
            content_lines = msg_copy["content"].split("\n")
            if len(content_lines) > 1:
                msg_copy["content"] = content_lines
        formatted.append(msg_copy)
    return formatted


def _write_llm_log(
    request_data: dict, response_data: dict, call_name: Optional[str] = None
) -> None:
    """
    Write LLM call log to file if a log directory is set.
    Behavior depends on the current log mode:
    - "all": Saves every LLM call
    - "latest": Only keeps the most recent call of each call_name type

    Args:
        request_data: Dictionary containing request information
        response_data: Dictionary containing response information
        call_name: Optional name identifying the purpose of this LLM call
                   (e.g., "detect_interrupt", "generate_agent_message")
    """
    log_dir = llm_log_dir.get()

    if log_dir is None:
        # No log directory set, skip logging
        return

    # Ensure log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)

    # Get current logging mode
    current_log_mode = llm_log_mode.get()

    # If mode is "latest" and call_name is provided, remove existing files with the same call_name
    if current_log_mode == "latest" and call_name:
        # Find and remove existing files with this call_name
        pattern = f"*_{call_name}_*.json"
        existing_files = list(log_dir.glob(pattern))
        for existing_file in existing_files:
            try:
                existing_file.unlink()
            except FileNotFoundError:
                # File might have been removed by another thread, ignore
                pass

    # Create a new file for this LLM call
    call_id = str(uuid.uuid4())[:8]  # Use short UUID for readability
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds

    # Include call_name in filename if provided
    if call_name:
        log_file = log_dir / f"{timestamp}_{call_name}_{call_id}.json"
    else:
        log_file = log_dir / f"{timestamp}_{call_id}.json"

    # Create complete JSON structure with both request and response
    call_data = {
        "call_id": call_id,
        "call_name": call_name,
        "timestamp": datetime.now().isoformat(),
        "request": request_data,
        "response": response_data,
    }

    # Write to file with indentation
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(call_data, f, indent=2)


def _needs_responses_api(model: str) -> bool:
    """Check if a model requires the OpenAI Responses API.

    gpt-5.x on a native OpenAI endpoint goes through ``litellm.responses()``
    because the Chat Completions API does not support function tools with
    reasoning for these models there. The routing manifest decides which
    endpoint serves a model id, so the decision is made on the resolved route
    (see :mod:`tau2.utils.model_routing`).
    """
    return resolve_model(model).uses_responses_api


def _to_responses_input(messages: list[Message]) -> tuple[list[dict], Optional[str]]:
    """Convert τ2 messages to Responses API ``input`` format.

    Returns ``(input_items, instructions)`` where *instructions* is the
    system-message content (if any) and *input_items* is a list of
    Responses-API–compatible dicts.
    """
    instructions: Optional[str] = None
    items: list[dict] = []

    for msg in messages:
        if isinstance(msg, SystemMessage):
            # System messages become the ``instructions`` parameter
            instructions = msg.content

        elif isinstance(msg, UserMessage):
            items.append({"role": "user", "content": msg.content, "type": "message"})

        elif isinstance(msg, AssistantMessage):
            # Content and tool calls can coexist — emit both.
            if msg.content:
                items.append(
                    {"role": "assistant", "content": msg.content, "type": "message"}
                )
            if msg.is_tool_call():
                for tc in msg.tool_calls:
                    items.append(
                        {
                            "type": "function_call",
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                            "call_id": tc.id,
                        }
                    )

        elif isinstance(msg, ToolMessage):
            items.append(
                {
                    "type": "function_call_output",
                    "call_id": msg.id,
                    "output": msg.content,
                }
            )

        elif isinstance(msg, MultiToolMessage):
            for tm in msg.tool_messages:
                items.append(
                    {
                        "type": "function_call_output",
                        "call_id": tm.id,
                        "output": tm.content,
                    }
                )

    # The Responses API requires a non-empty ``input``.  When the only
    # message is a SystemMessage (which maps to ``instructions``), we
    # synthesise a minimal user turn so the model still generates.
    if not items:
        items.append({"role": "user", "content": "Begin.", "type": "message"})

    return items, instructions


def _to_responses_tools(tools_schema: list[dict]) -> list[dict]:
    """Convert Chat-Completions tool schema to Responses API tool format.

    Chat Completions:  ``{"type": "function", "function": {"name": …, "description": …, "parameters": …}}``
    Responses API:     ``{"type": "function", "name": …, "description": …, "parameters": …}``
    """
    converted = []
    for tool in tools_schema:
        func = tool.get("function", {})
        converted.append(
            {
                "type": "function",
                "name": func.get("name"),
                "description": func.get("description", ""),
                "parameters": func.get("parameters", {}),
            }
        )
    return converted


def _parse_responses_output(response) -> tuple[Optional[str], Optional[list[ToolCall]]]:
    """Parse a Responses API response into content and tool calls."""
    content_parts: list[str] = []
    tool_calls: list[ToolCall] = []

    for item in response.output:
        item_type = getattr(item, "type", None)

        if item_type == "message":
            # ResponseOutputMessage — extract text from content list
            for part in item.content:
                part_type = getattr(part, "type", None)
                if part_type == "output_text":
                    content_parts.append(part.text)

        elif item_type == "function_call":
            # ResponseFunctionToolCall
            arguments_str = getattr(item, "arguments", "{}")
            tool_calls.append(
                ToolCall(
                    id=getattr(item, "call_id", str(uuid.uuid4())),
                    name=item.name,
                    arguments=json.loads(arguments_str),
                )
            )

    content = "\n".join(content_parts) if content_parts else None
    return content, tool_calls or None


def _get_responses_usage(response) -> Optional[dict]:
    """Extract usage from a Responses API response."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    return {
        "completion_tokens": getattr(usage, "output_tokens", 0),
        "prompt_tokens": getattr(usage, "input_tokens", 0),
    }


def generate(
    model: str,
    messages: list[Message],
    tools: Optional[list[Tool]] = None,
    tool_choice: Optional[str] = None,
    call_name: Optional[str] = None,
    **kwargs: Any,
) -> UserMessage | AssistantMessage:
    """
    Generate a response from the model.

    Automatically routes to the OpenAI Responses API (``litellm.responses``)
    when the model requires it (e.g. gpt-5.x with ``reasoning_effort`` and
    function tools).  Otherwise uses the standard Chat Completions API.

    Args:
        model: The model to use.
        messages: The messages to send to the model.
        tools: The tools to use.
        tool_choice: The tool choice to use.
        call_name: Optional name identifying the purpose of this LLM call
                   (e.g., "detect_interrupt", "generate_agent_message").
                   Used for logging and debugging.
        **kwargs: Additional arguments to pass to the model.

    Returns: A tuple containing the message and the cost.
    """
    validate_message_history(messages)
    if kwargs.get("num_retries") is None:
        kwargs["num_retries"] = DEFAULT_MAX_RETRIES
    _apply_default_request_timeout(kwargs)

    # Resolve the model id as written (task menu, run default) to the
    # provider that actually serves it. Everything recorded about the call —
    # credits, constraints, logs — keeps the original id; only the LiteLLM
    # target and credentials change here.
    route: ModelRoute = resolve_model(model)
    requested_model = model
    model = route.litellm_model
    for key, value in route.request_kwargs().items():
        kwargs.setdefault(key, value)

    # Vertex AI Gemini 3 models require VERTEXAI_LOCATION="global"
    if model.startswith("vertex_ai/gemini-3") and not os.environ.get(
        "VERTEXAI_LOCATION"
    ):
        os.environ["VERTEXAI_LOCATION"] = "global"

    # ------------------------------------------------------------------
    # Route: Responses API (gpt-5.x on a native OpenAI endpoint)
    # ------------------------------------------------------------------
    if route.uses_responses_api:
        return _generate_via_responses_api(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            call_name=call_name,
            requested_model=requested_model,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Route: Standard Chat Completions API
    # ------------------------------------------------------------------
    litellm_messages = to_litellm_messages(messages)
    tools_schema = [tool.openai_schema for tool in tools] if tools else None
    if tools_schema and tool_choice is None:
        tool_choice = "auto"

    # Prepare request data for logging
    formatted_messages = _format_messages_for_logging(litellm_messages)
    request_data = {
        "model": requested_model,
        "resolved_model": model,
        "messages": formatted_messages,
        "tools": tools_schema,
        "tool_choice": tool_choice,
        "kwargs": {
            k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
            for k, v in kwargs.items()
            if k != "api_key"
        },
    }
    request_timestamp = datetime.now().isoformat()

    start_time = time.perf_counter()
    for empty_attempt in range(1, EMPTY_COMPLETION_MAX_ATTEMPTS + 1):
        request_kwargs = dict(kwargs)
        if empty_attempt > 1:
            # Skip the cache read on retries so the turn is re-sampled instead
            # of re-reading a cached empty completion.
            request_kwargs["cache"] = {"no-cache": True}
        try:
            response = completion(
                model=model,
                messages=litellm_messages,
                tools=tools_schema,
                tool_choice=tool_choice,
                **request_kwargs,
            )
        except Exception as e:
            logger.error(e)
            raise e

        response_choice = response.choices[0]
        try:
            finish_reason = response_choice.finish_reason
            if finish_reason == "length":
                logger.warning("Output might be incomplete due to token limit!")
        except Exception as e:
            logger.error(e)
            raise e
        assert response_choice.message.role == "assistant", (
            "The response should be an assistant message"
        )
        content = response_choice.message.content
        raw_tool_calls = response_choice.message.tool_calls or []
        tool_calls = [
            ToolCall(
                id=tool_call.id,
                name=tool_call.function.name,
                arguments=json.loads(tool_call.function.arguments),
            )
            for tool_call in raw_tool_calls
        ]
        tool_calls = tool_calls or None

        if not _is_empty_completion(content, tool_calls):
            break
        if empty_attempt < EMPTY_COMPLETION_MAX_ATTEMPTS:
            logger.warning(
                f"Model {model} returned an empty completion (no content or "
                f"tool calls) on attempt {empty_attempt}/"
                f"{EMPTY_COMPLETION_MAX_ATTEMPTS}; re-requesting the turn."
            )
            continue
        raise EmptyCompletionError(
            f"Model {model} returned an empty completion (no content or tool "
            f"calls) on all {EMPTY_COMPLETION_MAX_ATTEMPTS} attempts."
        )
    generation_time_seconds = time.perf_counter() - start_time
    cost = get_response_cost(response)
    usage = get_response_usage(response)

    message = AssistantMessage(
        role="assistant",
        content=content,
        tool_calls=tool_calls,
        cost=cost,
        usage=usage,
        raw_data=response.to_dict(),
        generation_time_seconds=generation_time_seconds,
    )

    # Log complete LLM call (request + response)
    response_data = {
        "timestamp": datetime.now().isoformat(),
        "content": content,
        "tool_calls": [tc.model_dump() for tc in tool_calls] if tool_calls else None,
        "cost": cost,
        "usage": usage,
        "generation_time_seconds": generation_time_seconds,
    }
    # Add timestamp to request data
    request_data["timestamp"] = request_timestamp
    _write_llm_log(request_data, response_data, call_name=call_name)

    return message


def _generate_via_responses_api(
    model: str,
    messages: list[Message],
    tools: Optional[list[Tool]] = None,
    tool_choice: Optional[str] = None,
    call_name: Optional[str] = None,
    requested_model: Optional[str] = None,
    **kwargs: Any,
) -> AssistantMessage:
    """Generate using the OpenAI Responses API (``/v1/responses``).

    gpt-5.x models on a native OpenAI endpoint are routed here.  The Chat
    Completions API does not support function tools with reasoning for these
    models. ``model`` is the resolved LiteLLM target; ``requested_model`` is
    the id as written by the caller, kept for the call log.
    """
    # Build Responses-API input from the message history
    input_items, instructions = _to_responses_input(messages)

    # Convert tool schemas
    tools_schema = None
    if tools:
        cc_schema = [tool.openai_schema for tool in tools]
        tools_schema = _to_responses_tools(cc_schema)
    if tools_schema and tool_choice is None:
        tool_choice = "auto"

    # Extract reasoning_effort from kwargs → reasoning dict
    reasoning_effort = kwargs.pop("reasoning_effort", None)
    reasoning = {"effort": reasoning_effort} if reasoning_effort else None

    # Remove kwargs that don't apply to the Responses API
    num_retries = kwargs.pop("num_retries", DEFAULT_MAX_RETRIES)
    kwargs.pop("seed", None)
    temperature = kwargs.pop("temperature", None)
    try:
        max_attempts = max(1, int(num_retries))
    except (TypeError, ValueError):
        max_attempts = DEFAULT_MAX_RETRIES

    # Prepare request data for logging
    request_data = {
        "model": requested_model or model,
        "resolved_model": model,
        "api": "responses",
        "input": input_items[:3] if len(input_items) > 3 else input_items,
        "instructions": instructions[:200] if instructions else None,
        "tools": tools_schema,
        "tool_choice": tool_choice,
        "reasoning": reasoning,
    }
    request_timestamp = datetime.now().isoformat()

    def _request_once():
        for attempt in range(1, max_attempts + 1):
            try:
                return litellm.responses(
                    model=model,
                    input=input_items,
                    instructions=instructions,
                    tools=tools_schema,
                    tool_choice=tool_choice,
                    reasoning=reasoning,
                    temperature=temperature,
                    **kwargs,
                )
            except Exception as e:
                if attempt < max_attempts and _is_transient_llm_error(e):
                    delay_seconds = min(30, 2**attempt)
                    logger.warning(
                        "Responses API transient error on attempt "
                        f"{attempt}/{max_attempts}; retrying in "
                        f"{delay_seconds}s: {e}"
                    )
                    time.sleep(delay_seconds)
                    continue
                logger.error(f"Responses API error: {e}")
                raise e

    start_time = time.perf_counter()
    for empty_attempt in range(1, EMPTY_COMPLETION_MAX_ATTEMPTS + 1):
        response = _request_once()
        content, tool_calls = _parse_responses_output(response)
        if not _is_empty_completion(content, tool_calls):
            break
        if empty_attempt < EMPTY_COMPLETION_MAX_ATTEMPTS:
            logger.warning(
                f"Model {model} returned an empty completion (reasoning-only "
                f"output, no content or tool calls) on attempt "
                f"{empty_attempt}/{EMPTY_COMPLETION_MAX_ATTEMPTS}; "
                "re-requesting the turn."
            )
            continue
        raise EmptyCompletionError(
            f"Model {model} returned an empty completion (no content or tool "
            f"calls) on all {EMPTY_COMPLETION_MAX_ATTEMPTS} attempts."
        )
    generation_time_seconds = time.perf_counter() - start_time

    usage = _get_responses_usage(response)

    # Cost — try to compute, fall back to 0
    cost = 0.0

    message = AssistantMessage(
        role="assistant",
        content=content,
        tool_calls=tool_calls,
        cost=cost,
        usage=usage,
        raw_data=response.model_dump() if hasattr(response, "model_dump") else {},
        generation_time_seconds=generation_time_seconds,
    )

    # Log
    response_data = {
        "timestamp": datetime.now().isoformat(),
        "content": content,
        "tool_calls": [tc.model_dump() for tc in tool_calls] if tool_calls else None,
        "cost": cost,
        "usage": usage,
        "generation_time_seconds": generation_time_seconds,
    }
    request_data["timestamp"] = request_timestamp
    _write_llm_log(request_data, response_data, call_name=call_name)

    return message


def get_cost(messages: list[Message]) -> tuple[float | None, float | None]:
    """
    Get the (agent_cost, user_cost) of the interaction.

    Each side is computed independently: a side is None if any of its
    messages has no cost. This way an uncosted agent message (e.g. an
    audio-native provider without usage reporting) doesn't discard the
    user side's cost, and vice versa.
    """
    agent_cost: float | None = 0.0
    user_cost: float | None = 0.0
    for message in messages:
        if isinstance(message, ToolMessage):
            continue
        if isinstance(message, AssistantMessage):
            if message.cost is None:
                logger.warning(f"Agent message has no cost: {message.content}")
                agent_cost = None
            elif agent_cost is not None:
                agent_cost += message.cost
        elif isinstance(message, UserMessage):
            if message.cost is None:
                logger.warning(f"User message has no cost: {message.content}")
                user_cost = None
            elif user_cost is not None:
                user_cost += message.cost
    return agent_cost, user_cost


def get_token_usage(messages: list[Message]) -> dict:
    """
    Get the token usage of the interaction between the agent and the user.
    """
    usage = {"completion_tokens": 0, "prompt_tokens": 0}
    for message in messages:
        if isinstance(message, ToolMessage):
            continue
        if message.usage is None:
            logger.warning(f"Message {message.role}: {message.content} has no usage")
            continue
        usage["completion_tokens"] += message.usage["completion_tokens"]
        usage["prompt_tokens"] += message.usage["prompt_tokens"]
    return usage


def extract_json_from_llm_response(response: str) -> str:
    """
    Extract JSON from an LLM response, handling markdown code blocks.
    """
    # Try to extract JSON from markdown code blocks
    # Match ```json ... ``` or ``` ... ```
    pattern = r"```(?:json)?\s*([\s\S]*?)```"
    match = re.search(pattern, response)
    if match:
        return match.group(1).strip()

    # If no code block, try to find JSON object directly
    # Look for content between first { and last }
    start = response.find("{")
    end = response.rfind("}")
    if start != -1 and end != -1 and end > start:
        return response[start : end + 1]

    # Return original response as fallback
    return response
