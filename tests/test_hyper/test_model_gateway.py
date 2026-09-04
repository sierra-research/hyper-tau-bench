"""Security-contract tests for the native harness model gateway."""

import json
import time

import pytest

from tau2.hyper.sandbox.model_gateway import (
    MODEL_GATEWAY_HOST,
    ModelGatewaySpec,
    _allowed_upstream_path,
    _model_in_scope,
    _streaming_response,
)


@pytest.mark.parametrize(
    ("provider", "method", "path"),
    [
        ("openai", "POST", "responses"),
        ("openai", "POST", "responses/compact"),
        ("openai", "GET", "responses/response_123"),
        ("openai", "DELETE", "responses/response_123"),
        ("openai", "POST", "responses/response_123/cancel"),
        ("openai", "GET", "responses/response_123/input_items"),
        ("openai", "POST", "chat/completions"),
        ("openai", "GET", "models"),
        ("anthropic", "POST", "messages"),
        ("anthropic", "POST", "messages/count_tokens"),
        ("anthropic", "GET", "models/claude-opus-4-6"),
    ],
)
def test_gateway_allows_only_native_inference_routes(provider, method, path):
    assert _allowed_upstream_path(provider, method, path)


@pytest.mark.parametrize(
    ("provider", "method", "path"),
    [
        ("openai", "POST", "files"),
        ("openai", "POST", "batches"),
        ("openai", "GET", "chat/completions"),
        ("openai", "POST", "chat/completions/extra"),
        ("openai", "POST", "completions"),
        ("openai", "POST", "responses/response_123/input_items"),
        ("openai", "POST", "responses/../files"),
        ("anthropic", "POST", "files"),
        ("anthropic", "POST", "messages/batches"),
        ("anthropic", "GET", "messages"),
        ("anthropic", "POST", "../messages"),
    ],
)
def test_gateway_rejects_non_inference_and_traversal_routes(provider, method, path):
    assert not _allowed_upstream_path(provider, method, path)


@pytest.mark.parametrize(
    ("provider", "path"),
    [
        ("openai", "responses"),
        ("openai", "responses/compact"),
        ("openai", "chat/completions"),
        ("anthropic", "messages"),
        ("anthropic", "messages/count_tokens"),
    ],
)
def test_gateway_inference_is_scoped_to_selected_model(provider, path):
    assert _model_in_scope(
        provider, path, b'{"model":"selected-model"}', "selected-model"
    )
    assert not _model_in_scope(
        provider, path, b'{"model":"other-model"}', "selected-model"
    )
    assert not _model_in_scope(provider, path, b"not-json", "selected-model")


def test_gateway_spec_uses_per_run_token_without_recording_raw_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "raw-provider-secret")

    first = ModelGatewaySpec.from_host_environment(
        "openai",
        model="gpt-5.4",
        lifetime_seconds=60,
    )
    second = ModelGatewaySpec.from_host_environment(
        "openai",
        model="gpt-5.4",
        lifetime_seconds=60,
    )

    assert first.token != second.token
    assert first.token != first.upstream_api_key
    assert first.expires_at > time.time()
    assert first.base_url == f"http://{MODEL_GATEWAY_HOST}:8143/openai"
    assert first.metadata() == {
        "protocol_version": "1",
        "provider": "openai",
        "model": "gpt-5.4",
        "upstream_origin": "https://api.openai.com/v1",
        "allowed_api_families": ["responses", "models"],
        "expires_at_unix": first.expires_at,
        "credential": "random-per-run-bearer",
        "raw_provider_credential_in_agent": False,
    }
    assert "raw-provider-secret" not in repr(first)
    assert "raw-provider-secret" not in str(first.metadata())


def test_gateway_requires_the_selected_provider_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(
        "tau2.hyper.sandbox.model_gateway.load_dotenv",
        lambda: None,
    )

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY is required"):
        ModelGatewaySpec.from_host_environment(
            "anthropic",
            model="claude-opus-4-6",
            lifetime_seconds=60,
        )


def test_gateway_closes_streaming_response_without_context_manager_protocol():
    class FakeResponse:
        closed = False

        def close(self):
            self.closed = True

    response = FakeResponse()

    class FakeClient:
        def send(self, request, *, stream):
            assert request == "request"
            assert stream is True
            return response

    with _streaming_response(FakeClient(), "request") as yielded:
        assert yielded is response
        assert not response.closed

    assert response.closed


def test_openrouter_provider_scope(monkeypatch):
    from tau2.hyper.sandbox.model_gateway import (
        ModelGatewaySpec,
        _allowed_upstream_path,
        _model_in_scope,
    )

    assert _allowed_upstream_path("openrouter", "POST", "chat/completions")
    assert _allowed_upstream_path("openrouter", "GET", "models")
    assert _allowed_upstream_path("openrouter", "POST", "responses")
    assert not _allowed_upstream_path("openrouter", "POST", "messages")

    body = json.dumps({"model": "moonshotai/kimi-k3"}).encode()
    assert _model_in_scope("openrouter", "chat/completions", body, "moonshotai/kimi-k3")
    assert not _model_in_scope("openrouter", "chat/completions", body, "other-model")

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    spec = ModelGatewaySpec.from_host_environment(
        "openrouter", model="moonshotai/kimi-k3", lifetime_seconds=60
    )
    assert spec.base_url.endswith("/openrouter")
    metadata = spec.metadata()
    assert metadata["upstream_origin"] == "https://openrouter.ai/api/v1"
    assert metadata["allowed_api_families"] == [
        "responses",
        "chat/completions",
        "models",
    ]
    assert spec.upstream_organization is None


def test_openrouter_provider_prefs_flow_from_env_to_sidecar(monkeypatch):
    from tau2.hyper.sandbox.model_gateway import _rewrite_openrouter_body

    prefs = {"order": ["deepinfra"], "allow_fallbacks": False}
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    monkeypatch.setenv("TAU2_OPENROUTER_PROVIDER_PREFS", json.dumps(prefs))
    spec = ModelGatewaySpec.from_host_environment(
        "openrouter", model="moonshotai/kimi-k3", lifetime_seconds=60
    )
    assert spec.provider_prefs == prefs
    sidecar_env = spec.sidecar_environment()
    assert json.loads(sidecar_env["TAU2_MODEL_GATEWAY_PROVIDER_PREFS"]) == prefs
    assert spec.metadata()["openrouter_provider_prefs"] == prefs

    # The prefs never apply to other providers, and openai ignores the env.
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    openai_spec = ModelGatewaySpec.from_host_environment(
        "openai", model="gpt-5.6-sol", lifetime_seconds=60
    )
    assert openai_spec.provider_prefs is None
    assert "TAU2_MODEL_GATEWAY_PROVIDER_PREFS" not in openai_spec.sidecar_environment()
    assert "openrouter_provider_prefs" not in openai_spec.metadata()

    # Body injection overrides any harness-chosen routing preference.
    body = json.dumps(
        {"model": "moonshotai/kimi-k3", "provider": {"order": ["moonshotai"]}}
    ).encode()
    injected = json.loads(_rewrite_openrouter_body(body, prefs))
    assert injected["provider"] == prefs
    assert injected["model"] == "moonshotai/kimi-k3"

    # Non-JSON and non-object bodies pass through untouched.
    assert _rewrite_openrouter_body(b"not json", prefs) == b"not json"
    assert _rewrite_openrouter_body(b"[1, 2]", prefs) == b"[1, 2]"


def test_openrouter_provider_prefs_env_must_be_a_json_object(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    monkeypatch.setenv("TAU2_OPENROUTER_PROVIDER_PREFS", "not json")
    with pytest.raises(ValueError, match="valid JSON"):
        ModelGatewaySpec.from_host_environment(
            "openrouter", model="moonshotai/kimi-k3", lifetime_seconds=60
        )
    monkeypatch.setenv("TAU2_OPENROUTER_PROVIDER_PREFS", '["deepinfra"]')
    with pytest.raises(ValueError, match="JSON object"):
        ModelGatewaySpec.from_host_environment(
            "openrouter", model="moonshotai/kimi-k3", lifetime_seconds=60
        )


def test_openrouter_body_rewrite_drops_orphan_tool_outputs():
    from tau2.hyper.sandbox.model_gateway import _rewrite_openrouter_body

    # Responses API: an output whose function_call was compacted away is
    # dropped; paired outputs and non-tool items survive untouched.
    responses_body = json.dumps(
        {
            "model": "moonshotai/kimi-k3",
            "input": [
                {"role": "user", "content": "hi"},
                {"type": "function_call", "call_id": "call_1", "name": "f"},
                {"type": "function_call_output", "call_id": "call_1", "output": "ok"},
                {"type": "function_call_output", "call_id": "call_gone", "output": "x"},
                {"type": "function_call_output", "output": "no id at all"},
            ],
        }
    ).encode()
    rewritten = json.loads(_rewrite_openrouter_body(responses_body, None))
    call_ids = [
        item.get("call_id")
        for item in rewritten["input"]
        if item.get("type") == "function_call_output"
    ]
    assert call_ids == ["call_1"]
    assert rewritten["input"][0] == {"role": "user", "content": "hi"}
    # No prefs configured: the provider field stays absent.
    assert "provider" not in rewritten

    # Chat-completions API: a tool message with an unmatched tool_call_id is
    # dropped; the matched one survives.
    chat_body = json.dumps(
        {
            "model": "moonshotai/kimi-k3",
            "messages": [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "tool_calls": [{"id": "call_1"}]},
                {"role": "tool", "tool_call_id": "call_1", "content": "ok"},
                {"role": "tool", "tool_call_id": "call_gone", "content": "x"},
                {"role": "tool", "content": "no id at all"},
            ],
        }
    ).encode()
    rewritten = json.loads(
        _rewrite_openrouter_body(chat_body, {"order": ["deepinfra"]})
    )
    tool_ids = [
        message.get("tool_call_id")
        for message in rewritten["messages"]
        if message.get("role") == "tool"
    ]
    assert tool_ids == ["call_1"]
    assert rewritten["provider"] == {"order": ["deepinfra"]}


# --- Routing manifest ----------------------------------------------------------


def _use_manifest(monkeypatch, tmp_path, text: str) -> None:
    from tau2.utils import model_routing

    path = tmp_path / "routing.toml"
    path.write_text(text)
    monkeypatch.setenv("TAU2_MODEL_ROUTING", str(path))
    model_routing.reset_routing_cache()


def test_gateway_spec_takes_origin_and_key_variable_from_manifest(
    monkeypatch, tmp_path
):
    monkeypatch.setattr("tau2.hyper.sandbox.model_gateway.load_dotenv", lambda: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("TEAM_OPENAI_KEY", "team-secret")
    _use_manifest(
        monkeypatch,
        tmp_path,
        "[providers.openai]\n"
        'base_url = "https://proxy.example.com/v1/"\n'
        'api_key_env = "TEAM_OPENAI_KEY"\n',
    )

    spec = ModelGatewaySpec.from_host_environment(
        "openai", model="gpt-5.4", lifetime_seconds=60
    )

    assert spec.upstream_api_key == "team-secret"
    assert spec.metadata()["upstream_origin"] == "https://proxy.example.com/v1"
    assert spec.metadata()["allowed_api_families"] == ["responses", "models"]
    env = spec.sidecar_environment()
    assert env["TAU2_MODEL_GATEWAY_UPSTREAM_ORIGIN"] == "https://proxy.example.com/v1"
    assert env["TAU2_MODEL_GATEWAY_WIRE"] == "openai"
    assert "team-secret" not in str(spec.metadata())


def test_gateway_spec_without_manifest_matches_builtin_table(monkeypatch, tmp_path):
    monkeypatch.setattr("tau2.hyper.sandbox.model_gateway.load_dotenv", lambda: None)
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    _use_manifest(monkeypatch, tmp_path, "")

    spec = ModelGatewaySpec.from_host_environment(
        "openrouter", model="moonshotai/kimi-k3", lifetime_seconds=60
    )

    assert spec.resolved_origin == "https://openrouter.ai/api/v1"
    assert spec.resolved_wire == "openai"
    assert spec.metadata()["upstream_origin"] == "https://openrouter.ai/api/v1"


def test_gateway_rejects_provider_on_unsupported_wire(monkeypatch, tmp_path):
    monkeypatch.setattr("tau2.hyper.sandbox.model_gateway.load_dotenv", lambda: None)
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    _use_manifest(monkeypatch, tmp_path, "")

    with pytest.raises(ValueError, match="wire format"):
        ModelGatewaySpec.from_host_environment(
            "gemini", model="gemini-3-flash-preview", lifetime_seconds=60
        )


def test_gateway_rejects_unknown_provider_name(monkeypatch, tmp_path):
    monkeypatch.setattr("tau2.hyper.sandbox.model_gateway.load_dotenv", lambda: None)
    _use_manifest(monkeypatch, tmp_path, "")

    with pytest.raises((ValueError,), match="Unknown provider|Unsupported"):
        ModelGatewaySpec.from_host_environment("nope", model="m", lifetime_seconds=60)


def test_sidecar_handler_reads_origin_and_wire_from_environment(monkeypatch):
    from tau2.hyper.sandbox.model_gateway import _handler_from_environment

    monkeypatch.setenv("TAU2_MODEL_GATEWAY_PROVIDER", "openai")
    monkeypatch.setenv("TAU2_MODEL_GATEWAY_MODEL", "gpt-5.4")
    monkeypatch.setenv("TAU2_MODEL_GATEWAY_TOKEN", "t")
    monkeypatch.setenv("TAU2_MODEL_GATEWAY_UPSTREAM_KEY", "k")
    monkeypatch.setenv("TAU2_MODEL_GATEWAY_EXPIRES_AT", str(time.time() + 60))
    monkeypatch.setenv("TAU2_MODEL_GATEWAY_UPSTREAM_ORIGIN", "http://vllm:8000/v1/")
    monkeypatch.setenv("TAU2_MODEL_GATEWAY_WIRE", "openai")

    handler = _handler_from_environment()
    try:
        assert handler.upstream_origin == "http://vllm:8000/v1"
        assert handler.wire == "openai"
    finally:
        handler.client.close()

    # Older images without the new variables keep the built-in origin.
    monkeypatch.delenv("TAU2_MODEL_GATEWAY_UPSTREAM_ORIGIN")
    monkeypatch.delenv("TAU2_MODEL_GATEWAY_WIRE")
    handler = _handler_from_environment()
    try:
        assert handler.upstream_origin == "https://api.openai.com/v1"
        assert handler.wire == "openai"
    finally:
        handler.client.close()
