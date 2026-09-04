"""Scoped, per-run model gateway for native coding harnesses.

The construction container has no internet route. A separate sidecar joins
both its internal network and Docker's external bridge, but this server is not
a general HTTP proxy: it forwards only the selected provider's inference and
model-discovery endpoints to a fixed upstream origin.
"""

from __future__ import annotations

import hmac
import json
import os
import secrets
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import ClassVar
from urllib.parse import unquote, urlsplit

import httpx
from dotenv import load_dotenv

MODEL_GATEWAY_HOST = "tau2-model-gateway"
MODEL_GATEWAY_PORT = 8143
MODEL_GATEWAY_PROTOCOL_VERSION = "1"
MAX_REQUEST_BYTES = 64 * 1024 * 1024

# Built-in gateway providers. ``model_routing.toml`` (see
# ``tau2.utils.model_routing``) may override a provider's origin and key
# variable; the host resolves that and hands the sidecar the result through
# its environment, so the sidecar itself never reads the manifest.
_PROVIDER_ORIGINS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}
_PROVIDER_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}
# Wire format each provider speaks: which request paths are inference, and
# how the upstream credential is attached.
_PROVIDER_WIRE = {
    "openai": "openai",
    "anthropic": "anthropic",
    "openrouter": "openai",
}
_GATEWAY_WIRES = ("openai", "anthropic")


def _wire_for(provider: str) -> str:
    """Wire format for a built-in provider name, or the name itself as a wire."""
    return _PROVIDER_WIRE.get(provider, provider)


_HOP_BY_HOP_HEADERS = {
    "connection",
    "content-length",
    "host",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}
_REQUEST_HEADERS = {
    "accept",
    "accept-encoding",
    "anthropic-beta",
    "anthropic-version",
    "content-type",
    "openai-beta",
    "traceparent",
    "tracestate",
    "user-agent",
    "x-client-request-id",
}


@contextmanager
def _streaming_response(client, request):
    """Yield an httpx streaming response and always release its connection."""
    response = client.send(request, stream=True)
    try:
        yield response
    finally:
        response.close()


def _allowed_upstream_path(provider: str, method: str, path: str) -> bool:
    """Return whether one normalized path is inside the inference scope."""
    parts = path.strip("/").split("/")
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return False
    if parts[0] == "models":
        return method == "GET"
    wire = _wire_for(provider)
    if wire == "openai":
        # OpenRouter mirrors the OpenAI surface, including the Responses
        # API (which @ai-sdk/openai-based harnesses speak by default).
        if parts == ["responses"] or parts == ["responses", "compact"]:
            return method == "POST"
        # OpenAI-compatible harnesses (OpenCode, Prime Agent) speak the
        # chat-completions wire format instead of the Responses API.
        if parts == ["chat", "completions"]:
            return method == "POST"
        if len(parts) == 2 and parts[0] == "responses":
            return method in {"GET", "DELETE"}
        if len(parts) == 3 and parts[0] == "responses":
            return (parts[2] == "cancel" and method == "POST") or (
                parts[2] == "input_items" and method == "GET"
            )
        return False
    return (
        wire == "anthropic"
        and parts[0] == "messages"
        and method == "POST"
        and (len(parts) == 1 or parts[1:] == ["count_tokens"])
    )


_MODEL_SCOPED_PATHS = {
    "openai": {"responses", "responses/compact", "chat/completions"},
    "anthropic": {"messages", "messages/count_tokens"},
}


def _model_in_scope(provider: str, path: str, body: bytes, model: str) -> bool:
    """Require inference requests to use the run's selected model."""
    if path not in _MODEL_SCOPED_PATHS[_wire_for(provider)]:
        return True
    try:
        return json.loads(body).get("model") == model
    except (AttributeError, json.JSONDecodeError):
        return False


def _drop_orphan_tool_outputs(payload: dict) -> None:
    """Remove tool results whose originating tool call is not in the history.

    Coding harnesses occasionally trim or compact session history so that a
    tool result survives without the assistant tool call that produced it.
    Open-weight chat templates (verified across every OpenRouter kimi-k3
    endpoint) reject such orphans with a non-retryable 400, killing the run
    at a random depth. The pairing context is already lost when the orphan
    forms, so dropping the orphan is strictly less destructive than the 400.
    """
    items = payload.get("input")
    if isinstance(items, list):  # Responses API
        seen_calls: set = set()
        kept = []
        for item in items:
            if isinstance(item, dict):
                call_id = item.get("call_id")
                if item.get("type") == "function_call" and call_id:
                    seen_calls.add(call_id)
                elif item.get("type") == "function_call_output" and (
                    not call_id or call_id not in seen_calls
                ):
                    # Id-less outputs are unpairable downstream: OpenRouter's
                    # chat translation would emit a tool message with no
                    # tool_call_id, which providers fail to even deserialize.
                    continue
            kept.append(item)
        payload["input"] = kept
    messages = payload.get("messages")
    if isinstance(messages, list):  # chat-completions API
        seen_calls = set()
        kept = []
        for message in messages:
            if isinstance(message, dict):
                if message.get("role") == "assistant":
                    for call in message.get("tool_calls") or []:
                        if isinstance(call, dict) and call.get("id"):
                            seen_calls.add(call["id"])
                elif message.get("role") == "tool":
                    tool_call_id = message.get("tool_call_id")
                    if not tool_call_id or tool_call_id not in seen_calls:
                        continue
            kept.append(message)
        payload["messages"] = kept


def _rewrite_openrouter_body(body: bytes, prefs: dict | None) -> bytes:
    """Apply host-owned routing preferences and history hygiene.

    The host, not the harness, owns which upstream serves the run and what
    reaches it: routing preferences are forced onto the body, and orphaned
    tool outputs are dropped before any strict chat template can 400 on them.
    """
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return body
    if not isinstance(payload, dict):
        return body
    if prefs:
        payload["provider"] = prefs
    _drop_orphan_tool_outputs(payload)
    return json.dumps(payload).encode()


@dataclass(frozen=True)
class ModelGatewaySpec:
    """Secret-bearing host configuration for one short-lived sidecar."""

    provider: str
    model: str
    token: str = field(repr=False)
    upstream_api_key: str = field(repr=False)
    expires_at: float
    upstream_organization: str | None = field(default=None, repr=False)
    upstream_project: str | None = field(default=None, repr=False)
    # OpenRouter routing preferences (https://openrouter.ai/docs/provider-routing),
    # injected into every inference request body. Host-owned, non-secret.
    provider_prefs: dict | None = None
    # Resolved from model_routing.toml on the host; ``None`` means the
    # built-in origin / wire for ``provider``.
    upstream_origin: str | None = None
    wire: str | None = None

    @classmethod
    def from_host_environment(
        cls, provider: str, *, model: str, lifetime_seconds: float
    ) -> ModelGatewaySpec:
        """Create a scoped credential without exposing the provider key.

        The provider's origin and key variable come from ``model_routing.toml``
        when it defines the provider, so pointing e.g. ``providers.openai`` at
        a self-hosted OpenAI-compatible server reroutes the Developer seat.
        """
        if lifetime_seconds <= 0:
            raise ValueError("Model gateway lifetime must be positive")
        load_dotenv()
        # Imported lazily: this module is also the sidecar entrypoint inside
        # the construction image, which only reads its environment.
        from tau2.utils.model_routing import ModelRoutingError, provider_settings

        try:
            route = provider_settings(provider)
        except ModelRoutingError:
            if provider not in _PROVIDER_ORIGINS:
                raise ValueError(f"Unsupported native model provider: {provider}")
            route = None
        if route is not None and route.wire not in _GATEWAY_WIRES:
            raise ValueError(
                f"Provider {provider!r} speaks the {route.wire!r} wire format; "
                f"the Developer gateway supports {list(_GATEWAY_WIRES)}"
            )
        key_env = route.api_key_env if route else _PROVIDER_KEY_ENV[provider]
        upstream_origin = (
            route.base_url.rstrip("/") if route else _PROVIDER_ORIGINS[provider]
        )
        wire = route.wire if route else _wire_for(provider)
        upstream_key = os.environ.get(key_env)
        if not upstream_key:
            raise RuntimeError(
                f"{key_env} is required on the host for the {provider} "
                "native developer harness"
            )
        provider_prefs = None
        if provider == "openrouter":
            prefs_raw = os.environ.get("TAU2_OPENROUTER_PROVIDER_PREFS")
            if prefs_raw:
                try:
                    provider_prefs = json.loads(prefs_raw)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        "TAU2_OPENROUTER_PROVIDER_PREFS must be valid JSON"
                    ) from exc
                if not isinstance(provider_prefs, dict):
                    raise ValueError(
                        "TAU2_OPENROUTER_PROVIDER_PREFS must be a JSON object"
                    )
        return cls(
            provider=provider,
            model=model,
            token=secrets.token_urlsafe(32),
            upstream_api_key=upstream_key,
            expires_at=time.time() + lifetime_seconds,
            provider_prefs=provider_prefs,
            upstream_origin=upstream_origin,
            wire=wire,
            upstream_organization=(
                (
                    os.environ.get("OPENAI_ORGANIZATION")
                    or os.environ.get("OPENAI_ORG_ID")
                )
                if provider == "openai"
                else None
            ),
            upstream_project=(
                (
                    os.environ.get("OPENAI_PROJECT")
                    or os.environ.get("OPENAI_PROJECT_ID")
                )
                if provider == "openai"
                else None
            ),
        )

    @property
    def base_url(self) -> str:
        """Internal URL visible to the selected native harness."""
        return f"http://{MODEL_GATEWAY_HOST}:{MODEL_GATEWAY_PORT}/{self.provider}"

    def sidecar_environment(self) -> dict[str, str]:
        """Return environment passed only to the gateway sidecar."""
        environment = {
            "TAU2_MODEL_GATEWAY_PROVIDER": self.provider,
            "TAU2_MODEL_GATEWAY_MODEL": self.model,
            "TAU2_MODEL_GATEWAY_TOKEN": self.token,
            "TAU2_MODEL_GATEWAY_UPSTREAM_KEY": self.upstream_api_key,
            "TAU2_MODEL_GATEWAY_EXPIRES_AT": str(self.expires_at),
        }
        if self.upstream_organization:
            environment["TAU2_MODEL_GATEWAY_OPENAI_ORGANIZATION"] = (
                self.upstream_organization
            )
        if self.upstream_project:
            environment["TAU2_MODEL_GATEWAY_OPENAI_PROJECT"] = self.upstream_project
        if self.provider_prefs:
            environment["TAU2_MODEL_GATEWAY_PROVIDER_PREFS"] = json.dumps(
                self.provider_prefs
            )
        if self.upstream_origin:
            environment["TAU2_MODEL_GATEWAY_UPSTREAM_ORIGIN"] = self.upstream_origin
        if self.wire:
            environment["TAU2_MODEL_GATEWAY_WIRE"] = self.wire
        return environment

    @property
    def resolved_origin(self) -> str:
        return self.upstream_origin or _PROVIDER_ORIGINS[self.provider]

    @property
    def resolved_wire(self) -> str:
        return self.wire or _wire_for(self.provider)

    def metadata(self) -> dict:
        """Return the non-secret gateway contract stored with a run."""
        families = {
            "openai": ["responses", "models"],
            "openrouter": ["responses", "chat/completions", "models"],
            "anthropic": ["messages", "messages/count_tokens", "models"],
        }.get(self.provider) or {
            "openai": ["responses", "chat/completions", "models"],
            "anthropic": ["messages", "messages/count_tokens", "models"],
        }[self.resolved_wire]
        return {
            "protocol_version": MODEL_GATEWAY_PROTOCOL_VERSION,
            "provider": self.provider,
            "model": self.model,
            "upstream_origin": self.resolved_origin,
            "allowed_api_families": families,
            "expires_at_unix": self.expires_at,
            "credential": "random-per-run-bearer",
            "raw_provider_credential_in_agent": False,
            **(
                {"openrouter_provider_prefs": self.provider_prefs}
                if self.provider_prefs
                else {}
            ),
        }


class ModelGatewayRequestHandler(BaseHTTPRequestHandler):
    """Authenticated fixed-origin streaming reverse proxy."""

    protocol_version = "HTTP/1.1"
    server_version = "tau2-model-gateway/1"
    sys_version = ""
    provider: ClassVar[str]
    model: ClassVar[str]
    token: ClassVar[str]
    upstream_api_key: ClassVar[str]
    expires_at: ClassVar[float]
    upstream_organization: ClassVar[str | None]
    upstream_project: ClassVar[str | None]
    provider_prefs: ClassVar[dict | None]
    upstream_origin: ClassVar[str]
    wire: ClassVar[str]
    client: ClassVar[httpx.Client]

    def log_message(self, format: str, *args) -> None:
        """Avoid request/body/header logs in benchmark artifacts."""

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._handle_request()

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._handle_request()

    def do_DELETE(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._handle_request()

    def _authorized(self) -> bool:
        if time.time() >= self.expires_at:
            return False
        authorization = self.headers.get("Authorization", "")
        bearer = authorization.removeprefix("Bearer ")
        api_key = self.headers.get("x-api-key", "")
        return bool(self.token) and (
            hmac.compare_digest(bearer, self.token)
            or hmac.compare_digest(api_key, self.token)
        )

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def _handle_request(self) -> None:
        if not self._authorized():
            self._send_json(401, {"error": "invalid or expired gateway credential"})
            return

        parsed = urlsplit(self.path)
        normalized_path = unquote(parsed.path)
        prefix = f"/{self.provider}/v1/"
        if normalized_path == "/health":
            self._send_json(200, {"status": "ok", "provider": self.provider})
            return
        if not normalized_path.startswith(prefix):
            self._send_json(404, {"error": "endpoint outside gateway scope"})
            return
        upstream_path = normalized_path.removeprefix(prefix)
        if not _allowed_upstream_path(self.wire, self.command, upstream_path):
            self._send_json(403, {"error": "endpoint outside inference scope"})
            return

        raw_length = self.headers.get("Content-Length", "0")
        response_started = False
        try:
            length = int(raw_length)
        except ValueError:
            self._send_json(400, {"error": "invalid content length"})
            return
        if length < 0 or length > MAX_REQUEST_BYTES:
            self._send_json(413, {"error": "request body too large"})
            return
        body = self.rfile.read(length) if length else b""
        if self.command == "POST" and not _model_in_scope(
            self.wire,
            upstream_path,
            body,
            self.model,
        ):
            self._send_json(403, {"error": "model outside credential scope"})
            return
        if (
            self.command == "POST"
            and self.provider == "openrouter"
            and upstream_path in _MODEL_SCOPED_PATHS["openai"]
        ):
            body = _rewrite_openrouter_body(body, self.provider_prefs)

        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() in _REQUEST_HEADERS or key.lower().startswith("x-stainless-")
        }
        if self.wire == "openai":
            headers["Authorization"] = f"Bearer {self.upstream_api_key}"
            if self.upstream_organization:
                headers["OpenAI-Organization"] = self.upstream_organization
            if self.upstream_project:
                headers["OpenAI-Project"] = self.upstream_project
        else:
            headers["x-api-key"] = self.upstream_api_key

        upstream_url = f"{self.upstream_origin}/{upstream_path}"
        if parsed.query:
            upstream_url += f"?{parsed.query}"
        try:
            request = self.client.build_request(
                self.command,
                upstream_url,
                headers=headers,
                content=body,
            )
            with _streaming_response(self.client, request) as response:
                self.send_response(response.status_code)
                response_started = True
                for key, value in response.headers.items():
                    if key.lower() not in _HOP_BY_HOP_HEADERS:
                        self.send_header(key, value)
                self.send_header("Connection", "close")
                self.end_headers()
                for chunk in response.iter_raw():
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except httpx.HTTPError as exc:
            if not response_started and not self.wfile.closed:
                try:
                    self._send_json(
                        502,
                        {
                            "error": "provider gateway request failed",
                            "type": type(exc).__name__,
                        },
                    )
                except (BrokenPipeError, ConnectionError):
                    pass
        except BrokenPipeError:
            pass
        finally:
            self.close_connection = True


def _handler_from_environment() -> type[ModelGatewayRequestHandler]:
    provider = os.environ["TAU2_MODEL_GATEWAY_PROVIDER"]
    upstream_origin = os.environ.get("TAU2_MODEL_GATEWAY_UPSTREAM_ORIGIN")
    wire = os.environ.get("TAU2_MODEL_GATEWAY_WIRE")
    if provider in _PROVIDER_ORIGINS:
        upstream_origin = upstream_origin or _PROVIDER_ORIGINS[provider]
        wire = wire or _wire_for(provider)
    elif not (upstream_origin and wire):
        raise ValueError(f"Unsupported gateway provider: {provider}")
    if wire not in _GATEWAY_WIRES:
        raise ValueError(f"Unsupported gateway wire format: {wire}")

    class ConfiguredHandler(ModelGatewayRequestHandler):
        pass

    ConfiguredHandler.provider = provider
    ConfiguredHandler.upstream_origin = upstream_origin.rstrip("/")
    ConfiguredHandler.wire = wire
    ConfiguredHandler.model = os.environ["TAU2_MODEL_GATEWAY_MODEL"]
    ConfiguredHandler.token = os.environ["TAU2_MODEL_GATEWAY_TOKEN"]
    ConfiguredHandler.upstream_api_key = os.environ["TAU2_MODEL_GATEWAY_UPSTREAM_KEY"]
    ConfiguredHandler.expires_at = float(os.environ["TAU2_MODEL_GATEWAY_EXPIRES_AT"])
    ConfiguredHandler.upstream_organization = os.environ.get(
        "TAU2_MODEL_GATEWAY_OPENAI_ORGANIZATION"
    )
    ConfiguredHandler.upstream_project = os.environ.get(
        "TAU2_MODEL_GATEWAY_OPENAI_PROJECT"
    )
    prefs_raw = os.environ.get("TAU2_MODEL_GATEWAY_PROVIDER_PREFS")
    ConfiguredHandler.provider_prefs = json.loads(prefs_raw) if prefs_raw else None
    ConfiguredHandler.client = httpx.Client(
        timeout=httpx.Timeout(connect=30, read=None, write=60, pool=30),
        follow_redirects=False,
    )
    return ConfiguredHandler


def main() -> None:
    """Run the sidecar until Docker removes its per-run container."""
    handler = _handler_from_environment()
    server = ThreadingHTTPServer(("0.0.0.0", MODEL_GATEWAY_PORT), handler)
    server.daemon_threads = True
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        handler.client.close()
        server.server_close()


if __name__ == "__main__":
    main()
