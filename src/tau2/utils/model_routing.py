"""One file decides which credential and endpoint serve each model.

``model_routing.toml`` (repo root, or the path in ``TAU2_MODEL_ROUTING``) maps
every model id the benchmark uses — task-menu entries, simulator and judge
defaults — to a *provider*, and each provider to an API key environment
variable, a base URL, and a wire format. Model ids stay exactly as written in
task files and the registry; the rewrite to a concrete LiteLLM call happens
here, below credit metering and constraint checks, so routing never changes
what a run records.

Three consumers read the file:

* :func:`tau2.utils.llm_utils.generate` — every inner-loop model call.
* :class:`tau2.hyper.sandbox.model_gateway.ModelGatewaySpec` — the Developer
  sidecar's upstream origin and key.
* The ``banking_knowledge`` embedders and reranker (provider settings only).

Unlisted models fall back to LiteLLM's own prefix convention (bare id →
``openai``, ``openrouter/`` → ``openrouter``, ``anthropic/`` → ``anthropic``,
``gemini/`` → ``gemini``); anything else passes through untouched.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

ROUTING_PATH_ENV = "TAU2_MODEL_ROUTING"
ROUTING_FILENAME = "model_routing.toml"

WIRE_FORMATS = ("openai", "anthropic", "google")
API_MODES = ("auto", "chat", "responses")

# Providers the code knows how to reach without any manifest entry. A manifest
# ``[providers.<name>]`` table for one of these overrides its fields; a manifest
# table with a new name defines a new provider (OpenAI-compatible unless told
# otherwise), which is how a self-hosted vLLM/TGI endpoint gets wired in.
BUILTIN_PROVIDERS: dict[str, dict[str, str]] = {
    "openai": {
        "wire": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "litellm_prefix": "",
    },
    "openrouter": {
        "wire": "openai",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "litellm_prefix": "openrouter",
    },
    "anthropic": {
        "wire": "anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "api_key_env": "ANTHROPIC_API_KEY",
        "litellm_prefix": "anthropic",
    },
    "gemini": {
        "wire": "google",
        "base_url": "https://generativelanguage.googleapis.com",
        "api_key_env": "GEMINI_API_KEY",
        "litellm_prefix": "gemini",
    },
}

# LiteLLM prefix → built-in provider, for models the manifest does not list.
_PREFIX_TO_BUILTIN = {
    spec["litellm_prefix"]: name
    for name, spec in BUILTIN_PROVIDERS.items()
    if spec["litellm_prefix"]
}


class ModelRoutingError(ValueError):
    """The routing manifest is malformed or names something unknown."""


class MissingProviderKeyError(RuntimeError):
    """The environment variable a route needs is not set."""


@dataclass(frozen=True)
class ProviderRoute:
    """Where one provider lives and how to talk to it."""

    name: str
    wire: str
    base_url: str
    api_key_env: str
    litellm_prefix: str
    api: str = "auto"

    def __post_init__(self) -> None:
        if self.wire not in WIRE_FORMATS:
            raise ModelRoutingError(
                f"providers.{self.name}.wire must be one of {WIRE_FORMATS}, "
                f"got {self.wire!r}"
            )
        if self.api not in API_MODES:
            raise ModelRoutingError(
                f"providers.{self.name}.api must be one of {API_MODES}, "
                f"got {self.api!r}"
            )
        if not self.api_key_env:
            raise ModelRoutingError(f"providers.{self.name}.api_key_env is required")
        if not self.base_url:
            raise ModelRoutingError(f"providers.{self.name}.base_url is required")

    @property
    def is_builtin_endpoint(self) -> bool:
        """True when LiteLLM already knows this base URL for the prefix."""
        builtin = BUILTIN_PROVIDERS.get(self.name)
        return (
            builtin is not None
            and builtin["litellm_prefix"] == self.litellm_prefix
            and builtin["base_url"].rstrip("/") == self.base_url.rstrip("/")
        )

    @property
    def uses_builtin_key_env(self) -> bool:
        """True when LiteLLM would read this same variable on its own."""
        builtin = BUILTIN_PROVIDERS.get(self.name)
        return builtin is not None and builtin["api_key_env"] == self.api_key_env

    def api_key(self) -> Optional[str]:
        """The configured key, or ``None`` when its variable is unset."""
        return os.environ.get(self.api_key_env) or None

    def require_api_key(self, *, purpose: str) -> Optional[str]:
        """The key to hand LiteLLM, or ``None`` to let LiteLLM look it up.

        A built-in provider on its stock variable can be left to LiteLLM,
        which reads the same variable and raises its own authentication
        error. A custom provider or a renamed variable cannot: LiteLLM would
        silently try the wrong variable, so a missing key fails here with the
        variable named.
        """
        key = self.api_key()
        if key:
            return key
        if self.uses_builtin_key_env and self.is_builtin_endpoint:
            return None
        raise MissingProviderKeyError(
            f"{self.api_key_env} is not set, but {purpose} is routed to the "
            f"{self.name!r} provider. Export it in .env, or point "
            f"{ROUTING_FILENAME} at a provider whose key you have."
        )


@dataclass(frozen=True)
class ModelRoute:
    """How one model id, as written in tasks or config, is actually served."""

    model: str
    provider: Optional[ProviderRoute]
    upstream_model: str
    purpose: Optional[str] = None
    listed: bool = False

    @property
    def litellm_model(self) -> str:
        """The model string handed to LiteLLM."""
        if self.provider is None or not self.provider.litellm_prefix:
            return self.upstream_model
        return f"{self.provider.litellm_prefix}/{self.upstream_model}"

    @property
    def uses_responses_api(self) -> bool:
        """Whether the call goes through the OpenAI Responses API.

        gpt-5.x on an OpenAI endpoint needs ``/v1/responses`` (Chat Completions
        rejects function tools with reasoning there). Other endpoints that
        serve those ids — OpenRouter, a compatible proxy — translate on their
        side, so they stay on Chat Completions unless the provider pins ``api``.
        """
        if self.provider is None:
            return self.upstream_model.startswith("gpt-5")
        if self.provider.api == "responses":
            return True
        if self.provider.api == "chat":
            return False
        return (
            self.upstream_model.startswith("gpt-5")
            and self.provider.wire == "openai"
            and self.provider.litellm_prefix in ("", "openai")
        )

    def request_kwargs(self) -> dict[str, Any]:
        """Credential and endpoint kwargs to merge into the LiteLLM call."""
        if self.provider is None:
            return {}
        kwargs: dict[str, Any] = {}
        api_key = self.provider.require_api_key(purpose=f"model {self.model!r}")
        if api_key is not None:
            kwargs["api_key"] = api_key
        if not self.provider.is_builtin_endpoint:
            kwargs["api_base"] = self.provider.base_url
        return kwargs


@dataclass(frozen=True)
class ModelRouting:
    """The parsed manifest: providers plus explicit model routes."""

    providers: dict[str, ProviderRoute]
    models: dict[str, ModelRoute]
    source: Optional[Path] = None
    _passthrough_cache: dict = field(default_factory=dict, repr=False, compare=False)

    def provider(self, name: str) -> ProviderRoute:
        try:
            return self.providers[name]
        except KeyError:
            known = ", ".join(sorted(self.providers))
            raise ModelRoutingError(
                f"Unknown provider {name!r}; {ROUTING_FILENAME} defines: {known}"
            ) from None

    def resolve(self, model: str) -> ModelRoute:
        """Route one model id; unlisted ids follow LiteLLM's prefix rules."""
        listed = self.models.get(model)
        if listed is not None:
            return listed
        cached = self._passthrough_cache.get(model)
        if cached is not None:
            return cached
        prefix, sep, rest = model.partition("/")
        if not sep:
            route = ModelRoute(
                model=model, provider=self.provider("openai"), upstream_model=model
            )
        elif prefix in _PREFIX_TO_BUILTIN:
            route = ModelRoute(
                model=model,
                provider=self.provider(_PREFIX_TO_BUILTIN[prefix]),
                upstream_model=rest,
            )
        else:
            # An unfamiliar LiteLLM provider prefix (vertex_ai/, xai/, ...):
            # leave the string and credentials entirely to LiteLLM.
            route = ModelRoute(model=model, provider=None, upstream_model=model)
        self._passthrough_cache[model] = route
        return route

    def required_env(self, models: Iterable[str]) -> dict[str, list[str]]:
        """Map each API key variable to the models that need it."""
        needed: dict[str, list[str]] = {}
        for model in models:
            route = self.resolve(model)
            if route.provider is None:
                continue
            needed.setdefault(route.provider.api_key_env, []).append(model)
        return needed


def _builtin_provider_routes() -> dict[str, ProviderRoute]:
    return {
        name: ProviderRoute(name=name, **spec)
        for name, spec in BUILTIN_PROVIDERS.items()
    }


def parse_routing(
    data: Mapping[str, Any], *, source: Optional[Path] = None
) -> ModelRouting:
    """Build a :class:`ModelRouting` from decoded TOML."""
    providers = _builtin_provider_routes()
    raw_providers = data.get("providers", {})
    if not isinstance(raw_providers, Mapping):
        raise ModelRoutingError("[providers] must be a table")
    for name, raw in raw_providers.items():
        if not isinstance(raw, Mapping):
            raise ModelRoutingError(f"providers.{name} must be a table")
        unknown = set(raw) - {
            "wire",
            "base_url",
            "api_key_env",
            "litellm_prefix",
            "api",
        }
        if unknown:
            raise ModelRoutingError(
                f"providers.{name} has unknown keys: {', '.join(sorted(unknown))}"
            )
        base = dict(BUILTIN_PROVIDERS.get(name, {}))
        if name not in BUILTIN_PROVIDERS:
            # New providers are OpenAI-compatible endpoints unless told
            # otherwise, and LiteLLM reaches those through its ``openai/``
            # prefix plus an explicit ``api_base``.
            base.setdefault("wire", "openai")
            base.setdefault("litellm_prefix", "openai")
        base.update(raw)
        providers[name] = ProviderRoute(
            name=name,
            wire=str(base.get("wire", "")),
            base_url=str(base.get("base_url", "")),
            api_key_env=str(base.get("api_key_env", "")),
            litellm_prefix=str(base.get("litellm_prefix", "")),
            api=str(base.get("api", "auto")),
        )

    models: dict[str, ModelRoute] = {}
    raw_models = data.get("models", {})
    if not isinstance(raw_models, Mapping):
        raise ModelRoutingError("[models] must be a table")
    for model, raw in raw_models.items():
        if not isinstance(raw, Mapping):
            raise ModelRoutingError(f'models."{model}" must be a table')
        unknown = set(raw) - {"provider", "upstream_model", "purpose"}
        if unknown:
            raise ModelRoutingError(
                f'models."{model}" has unknown keys: {", ".join(sorted(unknown))}'
            )
        provider_name = raw.get("provider")
        if not provider_name:
            raise ModelRoutingError(f'models."{model}".provider is required')
        if provider_name not in providers:
            known = ", ".join(sorted(providers))
            raise ModelRoutingError(
                f'models."{model}" names provider {provider_name!r}; '
                f"{ROUTING_FILENAME} defines: {known}"
            )
        models[model] = ModelRoute(
            model=model,
            provider=providers[provider_name],
            upstream_model=str(raw.get("upstream_model") or model),
            purpose=raw.get("purpose"),
            listed=True,
        )
    return ModelRouting(providers=providers, models=models, source=source)


def _candidate_paths() -> list[Path]:
    override = os.environ.get(ROUTING_PATH_ENV)
    if override:
        return [Path(override).expanduser()]
    source_root = Path(__file__).resolve().parents[3]
    candidates = [source_root / ROUTING_FILENAME]
    data_dir = os.environ.get("TAU2_DATA_DIR")
    if data_dir:
        candidates.append(Path(data_dir) / ROUTING_FILENAME)
    return candidates


def routing_path() -> Optional[Path]:
    """The manifest that :func:`load_routing` will read, if one exists."""
    for candidate in _candidate_paths():
        if candidate.is_file():
            return candidate
    return None


def load_routing_file(path: Path) -> ModelRouting:
    with open(path, "rb") as handle:
        try:
            data = tomllib.load(handle)
        except tomllib.TOMLDecodeError as exc:
            raise ModelRoutingError(f"{path}: {exc}") from exc
    return parse_routing(data, source=path)


_CACHE: dict[Optional[Path], ModelRouting] = {}


def load_routing(path: Optional[Path] = None) -> ModelRouting:
    """Load (and cache) the active manifest.

    With no manifest on disk, routing is the built-in provider table alone:
    every model follows LiteLLM's prefix convention, which is exactly what the
    code did before the manifest existed.
    """
    if path is None:
        override = os.environ.get(ROUTING_PATH_ENV)
        if override and not Path(override).expanduser().is_file():
            raise ModelRoutingError(
                f"{ROUTING_PATH_ENV}={override} does not point at a file"
            )
    resolved = Path(path) if path is not None else routing_path()
    cached = _CACHE.get(resolved)
    if cached is None:
        cached = parse_routing({}) if resolved is None else load_routing_file(resolved)
        _CACHE[resolved] = cached
    return cached


def reset_routing_cache() -> None:
    """Forget cached manifests (tests, or after editing the file in-process)."""
    _CACHE.clear()


def resolve_model(model: str) -> ModelRoute:
    """Route one model id through the active manifest."""
    return load_routing().resolve(model)


def provider_settings(name: str) -> ProviderRoute:
    """Provider entry for direct SDK clients (embedders, rerankers, sidecar)."""
    return load_routing().provider(name)
