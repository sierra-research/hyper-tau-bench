"""Tests for the journey-scoped banking subdomains.

Covers:
- Manifest freshness (committed manifest == recomputed manifest)
- Exact task partition (every banking task in exactly one subdomain)
- Document coverage (each member task's required docs are in its subdomain)
- Environment construction (embedded policy, plain toolkit, no placeholders)
- Task loaders and registry registration
- Retrieval-variant rejection and read_log_allowlist plumbing
"""

from __future__ import annotations

import json

import pytest

from tau2.domains.banking_knowledge.environment import get_knowledge_base, get_tasks
from tau2.domains.banking_knowledge.retrieval_toolkits import KnowledgeToolsPlain
from tau2.domains.banking_knowledge.subdomains import (
    MANIFEST_PATH,
    build_manifest,
    get_subdomain_environment,
    get_subdomain_keys,
    get_subdomain_tasks,
    is_banking_subdomain,
    load_manifest,
)


@pytest.fixture(scope="module")
def manifest() -> dict:
    return load_manifest()


@pytest.fixture(scope="module")
def base_task_ids() -> set:
    return {task.id for task in get_tasks()}


def test_manifest_is_fresh(manifest):
    """The committed manifest must match a recompute from current data.

    If this fails, call subdomains.write_manifest() — the banking tasks or
    hyper section schemas changed since the manifest was generated.
    """
    assert build_manifest() == manifest, (
        "Banking subdomain manifest is stale. "
        "Call tau2.domains.banking_knowledge.subdomains.write_manifest()."
    )


def test_manifest_file_is_normalized(manifest):
    """The committed file matches the generator's serialization exactly."""
    expected = json.dumps(build_manifest(), indent=2) + "\n"
    assert MANIFEST_PATH.read_text() == expected


def test_task_partition_complete_and_disjoint(manifest, base_task_ids):
    seen: dict[str, str] = {}
    for key, entry in manifest["subdomains"].items():
        for task_id in entry["task_ids"]:
            assert task_id not in seen, (
                f"Task {task_id} assigned to both {seen[task_id]} and {key}"
            )
            seen[task_id] = key
    assert set(seen) == base_task_ids


def test_member_task_docs_covered(manifest):
    tasks_by_id = {task.id: task for task in get_tasks()}
    for key, entry in manifest["subdomains"].items():
        doc_ids = set(entry["doc_ids"])
        for task_id in entry["task_ids"]:
            required = set(tasks_by_id[task_id].required_documents or [])
            missing = required - doc_ids
            assert not missing, (
                f"Subdomain {key} task {task_id} requires documents outside "
                f"the subdomain's document set: {sorted(missing)}"
            )


def test_manifest_docs_exist_in_kb(manifest):
    kb = get_knowledge_base()
    for key, entry in manifest["subdomains"].items():
        missing = [d for d in entry["doc_ids"] if kb.get_document(d) is None]
        assert not missing, f"Subdomain {key} lists unknown documents: {missing}"


def test_environments_build_with_embedded_policy(manifest):
    kb = get_knowledge_base()
    for key, entry in manifest["subdomains"].items():
        env = get_subdomain_environment(key)
        assert env.domain_name == entry["domain_name"]
        assert isinstance(env.tools, KnowledgeToolsPlain)
        policy = env.policy
        assert "{{" not in policy, f"Unsubstituted placeholder in {key} policy"
        # Every subdomain document is inlined under its title heading.
        for doc_id in entry["doc_ids"]:
            title = kb.get_document(doc_id).title
            assert f"## {title}" in policy, (
                f"Subdomain {key} policy is missing document {doc_id}"
            )
        # No retrieval or shell tools on the toolkit.
        tool_names = set(env.tools.get_tools().keys())
        for retrieval_tool in ("KB_search", "KB_search_bm25", "KB_search_dense"):
            assert retrieval_tool not in tool_names
        assert not any("shell" in name.lower() for name in tool_names)


def test_tasks_loaders_match_manifest(manifest):
    for key, entry in manifest["subdomains"].items():
        tasks = get_subdomain_tasks(key)
        assert sorted(task.id for task in tasks) == entry["task_ids"]


def test_registry_registration(manifest):
    from tau2.registry import registry

    domains = set(registry.get_domains())
    task_sets = set(registry.get_task_sets())
    for entry in manifest["subdomains"].values():
        assert entry["domain_name"] in domains
        assert entry["domain_name"] in task_sets
        loader = registry.get_tasks_loader(entry["domain_name"])
        assert sorted(task.id for task in loader()) == entry["task_ids"]


def test_retrieval_variant_rejected():
    key = get_subdomain_keys()[0]
    with pytest.raises(ValueError, match="retrieval variants"):
        get_subdomain_environment(key, retrieval_variant="alltools")
    with pytest.raises(ValueError, match="solo mode"):
        get_subdomain_environment(key, solo_mode=True)


def test_is_banking_subdomain(manifest):
    for entry in manifest["subdomains"].values():
        assert is_banking_subdomain(entry["domain_name"])
    assert not is_banking_subdomain("banking_knowledge")
    assert not is_banking_subdomain("retail_plus")
    assert not is_banking_subdomain(None)


def test_read_log_allowlist_plumbed_for_subdomains(manifest):
    """The runner derives the per-task read allowlist for subdomains too."""
    from tau2.data_model.simulation import TextRunConfig
    from tau2.runner.build import _build_env_kwargs

    domain_name = next(iter(manifest["subdomains"].values()))["domain_name"]
    key = next(iter(manifest["subdomains"]))
    task = get_subdomain_tasks(key)[0]
    config = TextRunConfig(domain=domain_name)
    env_kwargs = _build_env_kwargs(config, task)
    assert "read_log_allowlist" in env_kwargs
    # Subdomains never default a retrieval config.
    assert config.retrieval_config is None
    assert "retrieval_variant" not in env_kwargs


def _client_api_task_files() -> list:
    """Every banking client-API task in the release corpus.

    Some tasks scope a single subdomain and some ("super" bundles) scope
    several, so the subdomain set is derived from each task's distributed
    sections rather than hardcoded per file.
    """
    from tau2.utils.utils import DATA_DIR

    paths = sorted(
        (DATA_DIR / "tau2" / "hyper" / "tasks").glob("*client_api*.json"),
        key=lambda path: path.name,
    )
    assert paths, "No banking client-API tasks found in the release corpus"
    return [path.name for path in paths]


def _rest_removed_action_task_ids() -> set:
    """Banking tasks that cannot be scored in client_api_mode=rest.

    A task is unscorable when its reward basis includes ACTION and its golden
    actions name the unlock/call_discoverable_agent_tool wrappers, which rest
    mode removes (the same criterion behind the 93-task full rest bundle).
    """
    from tau2.utils.utils import DATA_DIR

    wrappers = {"unlock_discoverable_agent_tool", "call_discoverable_agent_tool"}
    tasks = json.loads(
        (DATA_DIR / "tau2/domains/banking_knowledge/tasks.json").read_text()
    )
    removed = set()
    for task in tasks:
        criteria = task.get("evaluation_criteria") or {}
        if "ACTION" not in (criteria.get("reward_basis") or []):
            continue
        names = {action.get("name") for action in criteria.get("actions") or []}
        if names & wrappers:
            removed.add(task["id"])
    return removed


@pytest.mark.parametrize("task_file", _client_api_task_files())
def test_client_api_task_matches_manifest(manifest, task_file):
    """Every client-API release task is manifest-derived.

    Its test-task partition (minus the tasks rest mode cannot score), its
    knowledge-base document scope, and its section list must match the union
    of the subdomains it distributes. If this fails after a manifest
    regeneration, update the bundle task JSON to the new partition
    (test_task_ids, knowledge_base_documents, transformed_sections).
    """
    from tau2.utils.utils import DATA_DIR

    task_path = DATA_DIR / "tau2" / "hyper" / "tasks" / task_file
    task = json.loads(task_path.read_text())
    documents = set(task["knowledge_base_documents"])

    # A client-API task must scope whole subdomains, never part of one. The
    # document list is the one field every variant carries, including the
    # kb-only bundles that ship without a composition pipeline.
    scoped = {
        key: entry
        for key, entry in manifest["subdomains"].items()
        if {f"{doc_id}.json" for doc_id in entry["doc_ids"]} <= documents
    }
    assert scoped, f"{task_file} covers no complete subdomain"
    assert sorted(documents) == sorted(
        {f"{doc_id}.json" for entry in scoped.values() for doc_id in entry["doc_ids"]}
    ), f"{task_file} lists documents outside its subdomains"

    task_ids = {task_id for entry in scoped.values() for task_id in entry["task_ids"]}
    removed = _rest_removed_action_task_ids()
    assert task["test_task_ids"] == sorted(task_ids - removed)

    # Single-subdomain bundles document the tasks rest mode drops; the super
    # bundles spanning several subdomains do not carry the note.
    dropped = task_ids & removed
    if dropped and len(scoped) == 1:
        note = task["test_task_ids_note"]
        assert all(task_id.removeprefix("task_") in note for task_id in dropped)

    stages = {stage["stage"]: stage for stage in task.get("composition_pipeline") or []}
    if "information_distribution" in stages:
        assert sorted(stages["information_distribution"]["transformed_sections"]) == (
            sorted({s for entry in scoped.values() for s in entry["sections"]})
        )
