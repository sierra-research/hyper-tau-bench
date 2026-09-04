"""The routing manifest: one file decides which key and endpoint serve a model."""

import json
from pathlib import Path

import pytest

from tau2.hyper.performance_profiles import MODEL_BUCKETS
from tau2.utils import model_routing
from tau2.utils.model_routing import (
    BUILTIN_PROVIDERS,
    MissingProviderKeyError,
    ModelRoutingError,
    load_routing,
    load_routing_file,
    parse_routing,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SHIPPED_MANIFEST = REPO_ROOT / "model_routing.toml"
RELEASE_TASKS = REPO_ROOT / "data" / "tau2" / "hyper" / "tasks"


@pytest.fixture(autouse=True)
def _fresh_cache():
    model_routing.reset_routing_cache()
    yield
    model_routing.reset_routing_cache()


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "routing.toml"
    path.write_text(text)
    return path


# --- Parsing ------------------------------------------------------------------


def test_empty_manifest_is_litellm_prefix_convention(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k-openai")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k-or")
    monkeypatch.setenv("GEMINI_API_KEY", "k-gem")
    routing = parse_routing({})

    assert set(routing.providers) == set(BUILTIN_PROVIDERS)
    bare = routing.resolve("gpt-5.6-sol")
    assert bare.provider.name == "openai"
    assert bare.litellm_model == "gpt-5.6-sol"
    assert bare.uses_responses_api
    assert bare.request_kwargs() == {"api_key": "k-openai"}

    prefixed = routing.resolve("openrouter/some-vendor/some-model")
    assert prefixed.provider.name == "openrouter"
    assert prefixed.upstream_model == "some-vendor/some-model"
    assert prefixed.litellm_model == "openrouter/some-vendor/some-model"
    assert prefixed.request_kwargs() == {"api_key": "k-or"}

    gemini = routing.resolve("gemini/gemini-2.5-pro")
    assert gemini.provider.name == "gemini"
    assert gemini.request_kwargs() == {"api_key": "k-gem"}


def test_unknown_litellm_prefix_passes_through_untouched():
    route = parse_routing({}).resolve("vertex_ai/gemini-3-pro")
    assert route.provider is None
    assert route.litellm_model == "vertex_ai/gemini-3-pro"
    assert route.request_kwargs() == {}
    assert not route.uses_responses_api


def test_vendor_ids_route_only_through_the_manifest():
    """Menu ids are provider-neutral (``moonshotai/kimi-k3``); without a
    manifest entry they are not silently sent anywhere."""
    route = parse_routing({}).resolve("moonshotai/kimi-k3")
    assert route.provider is None
    assert not route.listed


def test_listed_model_is_rewritten_to_its_provider(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k-or")
    path = _write(
        tmp_path,
        """
[models."google/gemini-3.1-pro-preview"]
provider = "openrouter"
upstream_model = "google/gemini-3.1-pro-preview"
purpose = "Easy tier"
""",
    )
    route = load_routing_file(path).resolve("google/gemini-3.1-pro-preview")
    assert route.listed
    assert route.model == "google/gemini-3.1-pro-preview"
    assert route.litellm_model == "openrouter/google/gemini-3.1-pro-preview"
    assert route.provider.api_key_env == "OPENROUTER_API_KEY"
    assert route.purpose == "Easy tier"
    assert route.request_kwargs() == {"api_key": "k-or"}


def test_custom_provider_is_openai_compatible_with_explicit_endpoint(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("MY_VLLM_API_KEY", "anything")
    path = _write(
        tmp_path,
        """
[providers.my_vllm]
base_url = "http://localhost:8000/v1"
api_key_env = "MY_VLLM_API_KEY"
api = "chat"

[models."gpt-5.6-luna"]
provider = "my_vllm"
upstream_model = "meta-llama/Llama-4-70B"
""",
    )
    routing = load_routing_file(path)
    provider = routing.provider("my_vllm")
    assert provider.wire == "openai"
    assert provider.litellm_prefix == "openai"
    assert not provider.is_builtin_endpoint

    route = routing.resolve("gpt-5.6-luna")
    assert route.litellm_model == "openai/meta-llama/Llama-4-70B"
    assert route.request_kwargs() == {
        "api_key": "anything",
        "api_base": "http://localhost:8000/v1",
    }
    # api = "chat" keeps a gpt-5 id off the Responses API on a foreign server.
    assert not route.uses_responses_api


def test_gpt5_via_openrouter_uses_chat_completions(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    path = _write(
        tmp_path,
        """
[models."gpt-5.6-sol"]
provider = "openrouter"
upstream_model = "openai/gpt-5.6-sol"
""",
    )
    route = load_routing_file(path).resolve("gpt-5.6-sol")
    assert route.litellm_model == "openrouter/openai/gpt-5.6-sol"
    assert not route.uses_responses_api


def test_provider_override_changes_key_variable_and_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("TEAM_OPENAI_KEY", "team")
    path = _write(
        tmp_path,
        """
[providers.openai]
base_url = "https://proxy.example.com/v1"
api_key_env = "TEAM_OPENAI_KEY"
""",
    )
    route = load_routing_file(path).resolve("gpt-5.5")
    assert route.provider.api_key_env == "TEAM_OPENAI_KEY"
    # Still a bare OpenAI id (Responses API stays on), but at the proxy.
    assert route.litellm_model == "gpt-5.5"
    assert route.uses_responses_api
    assert route.request_kwargs() == {
        "api_key": "team",
        "api_base": "https://proxy.example.com/v1",
    }


def test_missing_stock_key_is_left_to_litellm(monkeypatch):
    """A built-in provider on its stock variable keeps LiteLLM's own lookup
    and error, so keyless runs that fake the provider call still work."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    route = parse_routing({}).resolve("openrouter/some-vendor/some-model")
    assert route.request_kwargs() == {}


def test_missing_custom_key_names_variable_model_and_provider(monkeypatch, tmp_path):
    monkeypatch.delenv("TEAM_OR_KEY", raising=False)
    routing = load_routing_file(
        _write(
            tmp_path,
            '[providers.openrouter]\napi_key_env = "TEAM_OR_KEY"\n',
        )
    )
    route = routing.resolve("openrouter/some-vendor/some-model")
    with pytest.raises(MissingProviderKeyError) as excinfo:
        route.request_kwargs()
    message = str(excinfo.value)
    assert "TEAM_OR_KEY" in message
    assert "openrouter/some-vendor/some-model" in message
    assert "'openrouter'" in message


@pytest.mark.parametrize(
    ("text", "match"),
    [
        ('[models."x"]\nprovider = "nope"\n', "names provider 'nope'"),
        ('[models."x"]\nupstream_model = "y"\n', "provider is required"),
        ('[models."x"]\nprovider = "openai"\nkey = "z"\n', "unknown keys: key"),
        ('[providers.p]\napi_key_env = "K"\n', "base_url is required"),
        ('[providers.p]\nbase_url = "u"\n', "api_key_env is required"),
        (
            '[providers.p]\nbase_url = "u"\napi_key_env = "K"\nwire = "grpc"\n',
            "wire must be one of",
        ),
        (
            '[providers.p]\nbase_url = "u"\napi_key_env = "K"\napi = "sse"\n',
            "api must be one of",
        ),
        ("providers = 3\n", r"\[providers\] must be a table"),
        ("models = [1]\n", r"\[models\] must be a table"),
        ("not toml ===\n", "routing.toml"),
    ],
)
def test_malformed_manifest_is_rejected_with_location(tmp_path, text, match):
    with pytest.raises(ModelRoutingError, match=match):
        load_routing_file(_write(tmp_path, text))


def test_required_env_groups_models_by_key_variable(tmp_path):
    routing = load_routing_file(
        _write(
            tmp_path,
            """
[models."gemini/g"]
provider = "openrouter"
upstream_model = "google/g"
""",
        )
    )
    needed = routing.required_env(
        ["gpt-5.5", "gemini/g", "openrouter/x/y", "vertex_ai/z"]
    )
    assert needed == {
        "OPENAI_API_KEY": ["gpt-5.5"],
        "OPENROUTER_API_KEY": ["gemini/g", "openrouter/x/y"],
    }


# --- Discovery ----------------------------------------------------------------


def test_env_override_selects_manifest_and_must_exist(monkeypatch, tmp_path):
    path = _write(tmp_path, '[models."m"]\nprovider = "openrouter"\n')
    monkeypatch.setenv("TAU2_MODEL_ROUTING", str(path))
    assert model_routing.routing_path() == path
    assert load_routing().resolve("m").listed

    model_routing.reset_routing_cache()
    monkeypatch.setenv("TAU2_MODEL_ROUTING", str(tmp_path / "missing.toml"))
    with pytest.raises(ModelRoutingError, match="does not point at a file"):
        load_routing()


def test_load_routing_caches_per_path(tmp_path):
    path = _write(tmp_path, "")
    assert load_routing(path) is load_routing(path)
    model_routing.reset_routing_cache()
    assert load_routing(path) is not None


# --- The shipped manifest -----------------------------------------------------


def _release_menu_models() -> set[str]:
    models: set[str] = set()

    def walk(node):
        if isinstance(node, str):
            models.add(node)
        elif isinstance(node, dict):
            if "model" in node and isinstance(node["model"], str):
                models.add(node["model"])
            for value in node.values():
                if isinstance(value, (dict, list)):
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for path in sorted(RELEASE_TASKS.glob("*.json")):
        task = json.loads(path.read_text())
        profile = task.get("performance_profile")
        if isinstance(profile, dict):
            for tier in profile.values():
                walk(tier.get("models", []))
        if task.get("user_llm"):
            models.add(task["user_llm"])
    return models


def test_shipped_manifest_lists_every_registry_model():
    routing = load_routing_file(SHIPPED_MANIFEST)
    missing = sorted(set(MODEL_BUCKETS) - set(routing.models))
    assert not missing, f"registry models absent from model_routing.toml: {missing}"


def test_shipped_manifest_needs_only_two_keys_for_every_release_task():
    """The README promise: OPENAI_API_KEY + OPENROUTER_API_KEY cover release runs."""
    from tau2.config import DEFAULT_LLM_NL_ASSERTIONS
    from tau2.hyper.run_defaults import (
        DEFAULT_CLIENT_LLM,
        DEFAULT_DEVELOPER_LLM,
        DEFAULT_USER_LLM,
    )

    routing = load_routing_file(SHIPPED_MANIFEST)
    models = _release_menu_models() | {
        DEFAULT_CLIENT_LLM,
        DEFAULT_USER_LLM,
        DEFAULT_DEVELOPER_LLM,
        DEFAULT_LLM_NL_ASSERTIONS,
    }
    assert models, "no release task menus found"
    needed = routing.required_env(models)
    assert set(needed) == {"OPENAI_API_KEY", "OPENROUTER_API_KEY"}, needed


def test_release_menus_use_provider_neutral_ids_that_the_manifest_lists():
    """Task files name vendor ids, never a route; the manifest lists each one."""
    routing = load_routing_file(SHIPPED_MANIFEST)
    menu_models = _release_menu_models()
    prefixed = sorted(
        m for m in menu_models if m.split("/")[0] in {"openrouter", "gemini"}
    )
    assert not prefixed, f"provider-routed ids in task menus: {prefixed}"
    unlisted = sorted(m for m in menu_models if not routing.resolve(m).listed)
    assert not unlisted, f"menu ids absent from model_routing.toml: {unlisted}"
    for model in menu_models:
        if model.startswith("google/gemini-"):
            route = routing.resolve(model)
            assert route.provider.name == "openrouter"
            assert route.litellm_model == f"openrouter/{model}"


def test_shipped_manifest_keeps_registry_ids_as_written():
    routing = load_routing_file(SHIPPED_MANIFEST)
    for model, route in routing.models.items():
        assert route.model == model
        # Bare OpenAI ids stay bare so the Responses API gate still fires.
        if route.provider.name == "openai":
            assert route.litellm_model == model
