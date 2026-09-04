from types import SimpleNamespace

import pytest

from tau2.data_model.message import (
    AssistantMessage,
    Message,
    SystemMessage,
    ToolMessage,
    UserMessage,
)
from tau2.environment.tool import Tool, as_tool
from tau2.utils import llm_utils
from tau2.utils.llm_utils import (
    EMPTY_COMPLETION_MAX_ATTEMPTS,
    EmptyCompletionError,
    generate,
)


@pytest.fixture
def model() -> str:
    return "gpt-4o-mini"


@pytest.fixture
def messages() -> list[Message]:
    messages = [
        SystemMessage(role="system", content="You are a helpful assistant."),
        UserMessage(role="user", content="What is the capital of the moon?"),
    ]
    return messages


@pytest.fixture
def tool() -> Tool:
    def calculate_square(x: int) -> int:
        """Calculate the square of a number.
            Args:
            x (int): The number to calculate the square of.
        Returns:
            int: The square of the number.
        """
        return x * x

    return as_tool(calculate_square)


@pytest.fixture
def tool_call_messages() -> list[Message]:
    messages = [
        SystemMessage(role="system", content="You are a helpful assistant."),
        UserMessage(
            role="user",
            content="What is the square of 5? Just give me the number, no explanation.",
        ),
    ]
    return messages


def test_generate_no_tool_call(model: str, messages: list[Message]):
    response = generate(model, messages)
    assert isinstance(response, AssistantMessage)
    assert response.content is not None


def test_generate_tool_call(model: str, tool_call_messages: list[Message], tool: Tool):
    response = generate(model, tool_call_messages, tools=[tool])
    assert isinstance(response, AssistantMessage)
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "calculate_square"
    assert response.tool_calls[0].arguments == {"x": 5}
    follow_up_messages = [
        response,
        ToolMessage(role="tool", id=response.tool_calls[0].id, content="25"),
    ]
    response = generate(
        model,
        tool_call_messages + follow_up_messages,
        tools=[tool],
    )
    assert isinstance(response, AssistantMessage)
    assert response.tool_calls is None
    assert response.content == "25"


def test_responses_api_retries_transient_errors(monkeypatch, messages: list[Message]):
    calls = 0

    def fake_responses(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("OpenAIException - [Errno 54] Connection reset by peer")
        return SimpleNamespace(
            output=[
                SimpleNamespace(
                    type="message",
                    content=[
                        SimpleNamespace(type="output_text", text="retry succeeded")
                    ],
                )
            ],
            usage=SimpleNamespace(input_tokens=7, output_tokens=3),
            model_dump=lambda: {"ok": True},
        )

    monkeypatch.setattr(llm_utils.litellm, "responses", fake_responses)
    monkeypatch.setattr(llm_utils.time, "sleep", lambda _delay: None)

    response = generate("gpt-5.5", messages, num_retries=2)

    assert response.content == "retry succeeded"
    assert response.usage == {"prompt_tokens": 7, "completion_tokens": 3}
    assert calls == 2


def _reasoning_only_response():
    """Responses API payload containing only reasoning items — the quirk that
    produced 'AssistantMessage must have either content or tool_calls' aborts."""
    return SimpleNamespace(
        output=[SimpleNamespace(type="reasoning", summary=[])],
        usage=SimpleNamespace(input_tokens=7, output_tokens=3),
        model_dump=lambda: {"ok": True},
    )


def test_responses_api_retries_empty_completion(monkeypatch, messages: list[Message]):
    """A reasoning-only completion is re-requested for that single turn."""
    calls = 0

    def fake_responses(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return _reasoning_only_response()
        return SimpleNamespace(
            output=[
                SimpleNamespace(
                    type="message",
                    content=[
                        SimpleNamespace(type="output_text", text="recovered turn")
                    ],
                )
            ],
            usage=SimpleNamespace(input_tokens=7, output_tokens=3),
            model_dump=lambda: {"ok": True},
        )

    monkeypatch.setattr(llm_utils.litellm, "responses", fake_responses)

    response = generate("gpt-5.6-sol", messages, num_retries=2)

    assert response.content == "recovered turn"
    assert calls == 2
    # The regression: this used to raise for the reasoning-only completion.
    response.validate()


def test_responses_api_empty_completion_exhausts_bounded_retries(
    monkeypatch, messages: list[Message]
):
    """A persistently empty completion raises after the bounded retries,
    leaving runner-level retry as the last resort."""
    calls = 0

    def fake_responses(**kwargs):
        nonlocal calls
        calls += 1
        return _reasoning_only_response()

    monkeypatch.setattr(llm_utils.litellm, "responses", fake_responses)

    with pytest.raises(EmptyCompletionError):
        generate("gpt-5.6-sol", messages, num_retries=2)

    assert calls == EMPTY_COMPLETION_MAX_ATTEMPTS


class _FakeChatResponse(SimpleNamespace):
    """Duck-typed litellm ModelResponse: attribute access plus .get()/.to_dict()."""

    def get(self, key, default=None):
        return getattr(self, key, default)

    def to_dict(self):
        return {"ok": True}


def _chat_response(content, tool_calls=None):
    return _FakeChatResponse(
        model="gpt-4o-mini",
        choices=[
            SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(
                    role="assistant", content=content, tool_calls=tool_calls
                ),
            )
        ],
        usage=None,
    )


def test_chat_completions_retries_empty_completion(
    monkeypatch, messages: list[Message]
):
    """Chat Completions path: whitespace-only content counts as empty, the turn
    is re-requested, and retries skip the litellm cache read."""
    captured_kwargs: list[dict] = []

    def fake_completion(**kwargs):
        captured_kwargs.append(kwargs)
        if len(captured_kwargs) == 1:
            return _chat_response(content="   ")
        return _chat_response(content="recovered turn")

    monkeypatch.setattr(llm_utils, "completion", fake_completion)

    response = generate("gpt-4o-mini", messages)

    assert response.content == "recovered turn"
    assert len(captured_kwargs) == 2
    assert "cache" not in captured_kwargs[0]
    assert captured_kwargs[1]["cache"] == {"no-cache": True}
    response.validate()


def test_chat_completions_empty_completion_exhausts_bounded_retries(
    monkeypatch, messages: list[Message]
):
    calls = 0

    def fake_completion(**kwargs):
        nonlocal calls
        calls += 1
        return _chat_response(content=None)

    monkeypatch.setattr(llm_utils, "completion", fake_completion)

    with pytest.raises(EmptyCompletionError):
        generate("gpt-4o-mini", messages)

    assert calls == EMPTY_COMPLETION_MAX_ATTEMPTS


def test_generate_applies_default_request_timeout(
    monkeypatch,
    messages: list[Message],
):
    captured_kwargs = {}

    def fake_responses(**kwargs):
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            output=[
                SimpleNamespace(
                    type="message",
                    content=[
                        SimpleNamespace(type="output_text", text="timeout applied")
                    ],
                )
            ],
            usage=SimpleNamespace(input_tokens=7, output_tokens=3),
            model_dump=lambda: {"ok": True},
        )

    monkeypatch.delenv("LITELLM_REQUEST_TIMEOUT", raising=False)
    monkeypatch.setattr(llm_utils.litellm, "responses", fake_responses)

    response = generate("gpt-5.5", messages, num_retries=1)

    assert response.content == "timeout applied"
    assert captured_kwargs["timeout"] == 600.0


def test_generate_honors_litellm_request_timeout_env(
    monkeypatch,
    messages: list[Message],
):
    captured_kwargs = {}

    def fake_responses(**kwargs):
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            output=[
                SimpleNamespace(
                    type="message",
                    content=[
                        SimpleNamespace(type="output_text", text="custom timeout")
                    ],
                )
            ],
            usage=SimpleNamespace(input_tokens=7, output_tokens=3),
            model_dump=lambda: {"ok": True},
        )

    monkeypatch.setenv("LITELLM_REQUEST_TIMEOUT", "42.5")
    monkeypatch.setattr(llm_utils.litellm, "responses", fake_responses)

    response = generate("gpt-5.5", messages, num_retries=1)

    assert response.content == "custom timeout"
    assert captured_kwargs["timeout"] == 42.5


# --- Model routing -------------------------------------------------------------


def _route_through(monkeypatch, tmp_path, text: str) -> None:
    from tau2.utils import model_routing

    path = tmp_path / "routing.toml"
    path.write_text(text)
    monkeypatch.setenv("TAU2_MODEL_ROUTING", str(path))
    model_routing.reset_routing_cache()


def test_generate_rewrites_routed_model_and_injects_credentials(
    monkeypatch, tmp_path, messages: list[Message]
):
    """A menu id is sent to LiteLLM as its routed target with that provider's
    key, while the call log keeps the id as requested."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-secret")
    _route_through(
        monkeypatch,
        tmp_path,
        '[models."google/gemini-3-flash-preview"]\n'
        'provider = "openrouter"\n'
        'upstream_model = "google/gemini-3-flash-preview"\n',
    )
    captured: list[dict] = []
    logged: list[dict] = []

    def fake_completion(**kwargs):
        captured.append(kwargs)
        return _chat_response(content="routed")

    monkeypatch.setattr(llm_utils, "completion", fake_completion)
    monkeypatch.setattr(
        llm_utils,
        "_write_llm_log",
        lambda req, resp, call_name=None: logged.append(req),
    )

    response = generate(
        "google/gemini-3-flash-preview", messages, reasoning_effort="minimal"
    )

    assert response.content == "routed"
    assert captured[0]["model"] == "openrouter/google/gemini-3-flash-preview"
    assert captured[0]["api_key"] == "or-secret"
    assert "api_base" not in captured[0]
    assert captured[0]["reasoning_effort"] == "minimal"
    assert logged[0]["model"] == "google/gemini-3-flash-preview"
    assert logged[0]["resolved_model"] == "openrouter/google/gemini-3-flash-preview"
    assert "api_key" not in logged[0]["kwargs"]


def test_generate_sends_custom_provider_to_its_endpoint(
    monkeypatch, tmp_path, messages: list[Message]
):
    monkeypatch.setenv("VLLM_KEY", "x")
    _route_through(
        monkeypatch,
        tmp_path,
        "[providers.vllm]\n"
        'base_url = "http://vllm.local:8000/v1"\n'
        'api_key_env = "VLLM_KEY"\n'
        'api = "chat"\n'
        '[models."gpt-5.6-luna"]\n'
        'provider = "vllm"\n'
        'upstream_model = "my-org/served-model"\n',
    )
    captured: list[dict] = []

    def fake_completion(**kwargs):
        captured.append(kwargs)
        return _chat_response(content="ok")

    monkeypatch.setattr(llm_utils, "completion", fake_completion)
    responses_called = []
    monkeypatch.setattr(
        llm_utils.litellm, "responses", lambda **kw: responses_called.append(kw)
    )

    generate("gpt-5.6-luna", messages)

    # gpt-5.x on a foreign chat-only server does not take the Responses path.
    assert not responses_called
    assert captured[0]["model"] == "openai/my-org/served-model"
    assert captured[0]["api_base"] == "http://vllm.local:8000/v1"
    assert captured[0]["api_key"] == "x"


def test_generate_fails_fast_when_routed_key_is_missing(
    monkeypatch, tmp_path, messages: list[Message]
):
    from tau2.utils.model_routing import MissingProviderKeyError

    monkeypatch.delenv("TEAM_OR_KEY", raising=False)
    _route_through(
        monkeypatch, tmp_path, '[providers.openrouter]\napi_key_env = "TEAM_OR_KEY"\n'
    )
    monkeypatch.setattr(
        llm_utils, "completion", lambda **kw: pytest.fail("should not call provider")
    )

    with pytest.raises(MissingProviderKeyError, match="TEAM_OR_KEY"):
        generate("openrouter/some-vendor/some-model", messages)


def test_responses_api_keeps_native_openai_route(
    monkeypatch, tmp_path, messages: list[Message]
):
    monkeypatch.setenv("OPENAI_API_KEY", "oa")
    _route_through(monkeypatch, tmp_path, "")
    captured: list[dict] = []

    def fake_responses(**kwargs):
        captured.append(kwargs)
        return SimpleNamespace(
            output=[
                SimpleNamespace(
                    type="message",
                    content=[SimpleNamespace(type="output_text", text="hi")],
                )
            ],
            usage=None,
        )

    monkeypatch.setattr(llm_utils.litellm, "responses", fake_responses)

    response = generate("gpt-5.6-sol", messages)

    assert response.content == "hi"
    assert captured[0]["model"] == "gpt-5.6-sol"
    assert captured[0]["api_key"] == "oa"
    assert "api_base" not in captured[0]


# --- Cost lookup noise ----------------------------------------------------------


def test_litellm_provider_banner_is_suppressed():
    """The red 'Provider List' stdout banner is off for the whole process."""
    assert llm_utils.litellm.suppress_debug_info is True


def test_unpriced_model_cost_is_zero_and_reported_once(monkeypatch, capsys):
    from litellm import ModelResponse

    def failing_cost(**kwargs):
        raise ValueError("no price entry")

    monkeypatch.setattr(llm_utils, "completion_cost", failing_cost)
    llm_utils._UNPRICED_MODELS_REPORTED.clear()
    debug_lines: list[str] = []
    monkeypatch.setattr(
        llm_utils.logger, "debug", lambda msg, *a, **k: debug_lines.append(str(msg))
    )
    monkeypatch.setattr(
        llm_utils.logger,
        "error",
        lambda *a, **k: pytest.fail("cost miss logged as error"),
    )

    response = ModelResponse(model="openrouter/some-vendor/some-model")
    assert llm_utils.get_response_cost(response) == 0.0
    assert llm_utils.get_response_cost(response) == 0.0

    assert len(debug_lines) == 1
    assert "openrouter/some-vendor/some-model" in debug_lines[0]
    assert "Provider List" not in capsys.readouterr().out
