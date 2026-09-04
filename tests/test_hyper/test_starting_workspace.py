"""Tests for authored starting workspaces (brownfield construction kits)."""

import importlib.util
import inspect
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tau2.hyper.client_api import ClientAPI, ClientAPIToolKitBase
from tau2.hyper.client_api.runtime import create_domain_client_api_runtime
from tau2.hyper.data_model import HyperTask
from tau2.hyper.sandbox.kit import build_kit
from tau2.hyper.sandbox.orchestrator import (
    _build_artifact_manifest,
    _build_contamination_report,
    initialize_kit_repository,
)
from tau2.hyper.sandbox.starting_workspace import (
    compute_workspace_pins,
    verify_workspace_pins,
)
from tau2.utils.utils import DATA_DIR

DEMO_WORKSPACE_REL = "tau2/hyper/workspaces/mock/demo_brownfield_001"
DEMO_WORKSPACE = DATA_DIR / DEMO_WORKSPACE_REL
REPO_ROOT = Path(__file__).resolve().parents[2]
RELEASE_TASKS_DIR = DATA_DIR / "tau2" / "hyper" / "tasks"
# Every seeded release task, keyed by task id: (task_id, seed tree).
SEEDED_RELEASE_TASKS = tuple(
    (path.stem, payload["starting_workspace_path"])
    for path in sorted(RELEASE_TASKS_DIR.glob("*.json"))
    for payload in [json.loads(path.read_text())]
    if payload.get("starting_workspace_path")
)
# Every seed tree shipped with the release set, deduplicated (tasks share trees).
RELEASE_SEED_TREES = tuple(dict.fromkeys(rel for _, rel in SEEDED_RELEASE_TASKS))


def _workspace_domain(workspace_rel: str) -> str:
    return Path(workspace_rel).parent.name


def _tree_id(workspace_rel: str) -> str:
    return workspace_rel.removeprefix("tau2/hyper/workspaces/")


def _seeded_kit_cases() -> tuple[tuple[str, str], ...]:
    """One (release task id, seed tree) pairing per domain, from the task set."""
    cases: dict[str, tuple[str, str]] = {}
    for task_id, tree in SEEDED_RELEASE_TASKS:
        cases.setdefault(_workspace_domain(tree), (task_id, tree))
    return tuple(cases.values())


API_SEEDED_READ_SMOKES = (
    (
        "tau2/hyper/workspaces/airline_plus/gen_luna_stateless_medium_001",
        "get_customer",
        lambda snapshot: {"customer_id": next(iter(snapshot["users"]))},
    ),
    (
        "tau2/hyper/workspaces/airline_plus/gen_luna_playbook_hard_001",
        "get_customer",
        lambda snapshot: {"customer_id": next(iter(snapshot["users"]))},
    ),
    (
        "tau2/hyper/workspaces/retail_plus/gen_luna_guardrail_easy_001",
        "get_customer",
        lambda snapshot: {"customer_id": next(iter(snapshot["users"]))},
    ),
    (
        "tau2/hyper/workspaces/retail_plus/gen_luna_stateless_medium_001",
        "get_customer",
        lambda snapshot: {"customer_id": next(iter(snapshot["users"]))},
    ),
    (
        "tau2/hyper/workspaces/telecom/gen_luna_stateless_medium_001",
        "get_customer",
        lambda snapshot: {"customer_id": snapshot["customers"][0]["customer_id"]},
    ),
    (
        "tau2/hyper/workspaces/telecom/gen_luna_playbook_hard_001",
        "get_customer",
        lambda snapshot: {"customer_id": snapshot["customers"][0]["customer_id"]},
    ),
)


@pytest.fixture(autouse=True)
def _mock_development_seed(monkeypatch):
    """The mock fixture domain ships no client-API development seed."""
    from tau2.hyper.client_api.development import development_seed_manifest
    from tau2.hyper.sandbox import kit as kit_module

    def seed(domain: str):
        if domain == "mock":
            return {}
        return development_seed_manifest(domain)

    monkeypatch.setattr(kit_module, "development_seed_manifest", seed)


def _construction_task(tmp_path: Path, **hyper_overrides) -> HyperTask:
    sop_path = tmp_path / "sop.md"
    if not sop_path.exists():
        sop_path.write_text(
            "# Task Board SOP\n\nHelp teammates manage the task board.\n"
        )
    payload = {
        "id": "mock_construction_starting_workspace_test",
        "source_domain": "mock",
        "task_description": "starting-workspace test fixture",
        "client_instructions": "",
        "training_task_ids": [],
        "test_task_ids": [],
        "sop_document_path": str(sop_path),
        "client_api_mode": "rest",
    }
    payload.update(hyper_overrides)
    return HyperTask.model_validate(payload)


def _tamperable_workspace(tmp_path: Path) -> Path:
    """A private copy of the demo workspace that tests may mutate."""
    workspace = tmp_path / "demo_brownfield_copy"
    shutil.copytree(DEMO_WORKSPACE, workspace)
    return workspace


def test_seeded_kit_ships_tree_instead_of_stubs(tmp_path):
    task = _construction_task(tmp_path, starting_workspace_path=DEMO_WORKSPACE_REL)
    kit_path = build_kit(task, tmp_path / "kit")

    workspace = kit_path / "workspace"
    kit_files = sorted(
        p.relative_to(workspace).as_posix() for p in workspace.rglob("*") if p.is_file()
    )
    tree = DEMO_WORKSPACE / "tree"
    tree_files = sorted(
        p.relative_to(tree).as_posix() for p in tree.rglob("*") if p.is_file()
    )
    # Substitution, never overlay: the kit workspace is exactly the authored
    # tree — no generated stubs mixed in, byte-identical content.
    assert kit_files == tree_files
    for rel in tree_files:
        assert (workspace / rel).read_bytes() == (tree / rel).read_bytes()
    assert "TaskBoardToolkit" in (workspace / "tools.py").read_text()
    assert "raise NotImplementedError" not in (workspace / "agent.py").read_text()

    readme = (kit_path / "README.md").read_text()
    assert "already contains the organization's existing" in readme
    assert "interface-only scaffold" not in readme
    # Sidecars are author-side only and must never ship.
    assert not (workspace / "workspace_facts.json").exists()
    assert not list(kit_path.rglob("workspace_pins.json"))


def test_unseeded_kit_still_writes_stubs(tmp_path):
    task = _construction_task(tmp_path)
    kit_path = build_kit(task, tmp_path / "kit")

    tools_stub = (kit_path / "workspace" / "tools.py").read_text()
    assert "class Tools(ClientAPIToolKitBase)" in tools_stub
    assert (
        "raise NotImplementedError" in (kit_path / "workspace" / "agent.py").read_text()
    )
    readme = (kit_path / "README.md").read_text()
    assert "`workspace/` is the implementation area." in readme
    assert "already contains the organization's existing" not in readme


def test_pin_drift_blocks_kit_build(tmp_path):
    workspace = _tamperable_workspace(tmp_path)
    tools_path = workspace / "tree" / "tools.py"
    tools_path.write_text(tools_path.read_text() + "\n# drifted\n")

    task = _construction_task(tmp_path, starting_workspace_path=str(workspace))
    with pytest.raises(ValueError, match="pin"):
        build_kit(task, tmp_path / "kit")


def test_missing_pins_block_kit_build(tmp_path):
    workspace = _tamperable_workspace(tmp_path)
    (workspace / "workspace_pins.json").unlink()

    task = _construction_task(tmp_path, starting_workspace_path=str(workspace))
    with pytest.raises(ValueError, match="workspace_pins.json"):
        build_kit(task, tmp_path / "kit")


def test_unpinned_extra_file_blocks_kit_build(tmp_path):
    workspace = _tamperable_workspace(tmp_path)
    (workspace / "tree" / "scratch.py").write_text("# unpinned\n")

    task = _construction_task(tmp_path, starting_workspace_path=str(workspace))
    with pytest.raises(ValueError, match="unpinned"):
        build_kit(task, tmp_path / "kit")


def test_demo_workspace_pins_are_fresh():
    # Shipped workspaces commit tree/ and workspace_pins.json together.
    assert verify_workspace_pins(DEMO_WORKSPACE) == []


def test_release_seed_trees_pass_pin_verification():
    # Every seed tree shipped with the release task set carries fresh pins.
    assert RELEASE_SEED_TREES
    for workspace_rel in RELEASE_SEED_TREES:
        assert verify_workspace_pins(DATA_DIR / workspace_rel) == [], workspace_rel


@pytest.mark.parametrize(
    ("task_id", "workspace_rel"),
    _seeded_kit_cases(),
    ids=[task_id for task_id, _ in _seeded_kit_cases()],
)
def test_release_seeded_rest_kit_builds(tmp_path, task_id, workspace_rel):
    # Smoke, one seeded release task per domain: the task builds a REST kit
    # directly from its task file, the seed tree passes its pin verification
    # inside the build, and the kit workspace is exactly the seed tree
    # (substitution, never overlay; __pycache__ is ignored by the pin
    # machinery).
    task = HyperTask.model_validate(
        json.loads((RELEASE_TASKS_DIR / f"{task_id}.json").read_text())
    )
    assert task.starting_workspace_path == workspace_rel
    assert task.client_api_mode == "rest"

    kit = build_kit(task, tmp_path / task_id)
    workspace = kit / "workspace"
    assert (kit / "client_api" / "openapi.yaml").is_file()
    assert (kit / "framework" / "client_api_contract.md").is_file()
    assert not (kit / "database").exists()
    assert "ClientAPIToolKitBase" in (workspace / "tools.py").read_text()

    tree = DATA_DIR / workspace_rel / "tree"
    kit_files = sorted(
        p.relative_to(workspace).as_posix()
        for p in workspace.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    )
    tree_files = sorted(
        p.relative_to(tree).as_posix()
        for p in tree.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    )
    assert kit_files == tree_files


@pytest.mark.parametrize(
    ("workspace_rel", "tool_name", "make_arguments"),
    API_SEEDED_READ_SMOKES,
    ids=[f"{_tree_id(rel)}-{tool}" for rel, tool, _ in API_SEEDED_READ_SMOKES],
)
def test_api_seeded_workspace_executes_client_read(
    workspace_rel, tool_name, make_arguments
):
    runtime = create_domain_client_api_runtime(_workspace_domain(workspace_rel))
    snapshot = runtime.snapshot()
    assert snapshot is not None
    arguments = make_arguments(snapshot)

    module_name = f"seeded_tools_{_tree_id(workspace_rel).replace('/', '_')}"
    spec = importlib.util.spec_from_file_location(
        module_name, DATA_DIR / workspace_rel / "tree" / "tools.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    # Keep bytecode caches out of the authored trees; they are unpinned and
    # would dirty the checkout.
    dont_write_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
        toolkit_cls = next(
            value
            for _, value in inspect.getmembers(module, inspect.isclass)
            if value.__module__ == module_name
            and issubclass(value, ClientAPIToolKitBase)
        )
        toolkit = toolkit_cls(ClientAPI(runtime.dispatch, context=runtime.context))
        assert toolkit.get_tools()
        assert getattr(toolkit, tool_name)(**arguments)
        assert runtime.operation_calls
    finally:
        sys.dont_write_bytecode = dont_write_bytecode
        sys.modules.pop(module_name, None)


def _seeded_git_kit(tmp_path: Path) -> tuple[Path, str]:
    task = _construction_task(tmp_path, starting_workspace_path=DEMO_WORKSPACE_REL)
    kit_path = build_kit(task, tmp_path / "kit")
    baseline_commit = initialize_kit_repository(kit_path)
    return kit_path, baseline_commit


def test_baseline_commit_contains_starting_tree(tmp_path):
    kit_path, _ = _seeded_git_kit(tmp_path)
    listed = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"],
        cwd=kit_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert "workspace/tools.py" in listed
    assert "workspace/agent.py" in listed


def test_artifact_manifest_tags_provenance(tmp_path):
    kit_path, baseline_commit = _seeded_git_kit(tmp_path)
    workspace = kit_path / "workspace"

    tools_path = workspace / "tools.py"
    tools_path.write_text(tools_path.read_text() + "\n# developer edit\n")
    (workspace / "notes.md").write_text("developer scratch notes\n")
    (workspace / "agent.py").unlink()

    manifest = _build_artifact_manifest(kit_path, baseline_commit)
    provenance = {entry["path"]: entry.get("provenance") for entry in manifest}
    assert provenance["workspace/tools.py"] == "modified"
    assert provenance["workspace/notes.md"] == "new"
    assert provenance["workspace/data_model.py"] == "baseline"
    assert provenance["workspace/agent.py"] == "deleted"

    # Without a baseline commit the manifest keeps its legacy shape.
    legacy = _build_artifact_manifest(kit_path)
    assert all("provenance" not in entry for entry in legacy)


def test_contamination_scan_scopes_to_developer_delta(tmp_path):
    kit_path, baseline_commit = _seeded_git_kit(tmp_path)
    workspace = kit_path / "workspace"
    (workspace / "notes.md").write_text("peeked at data/tau2/domains for reference\n")

    report = _build_contamination_report(kit_path, "mock", baseline_commit)
    assert report["scope"] == "delta"
    assert report["skipped_baseline_files"] >= 2
    assert report["status"] == "matches_found"
    assert {match["path"] for match in report["matches"]} == {"workspace/notes.md"}

    full_report = _build_contamination_report(kit_path, "mock")
    assert full_report["scope"] == "full"
    assert full_report["skipped_baseline_files"] == 0


def test_compute_pins_matches_committed_pins():
    committed = json.loads((DEMO_WORKSPACE / "workspace_pins.json").read_text())
    assert compute_workspace_pins(DEMO_WORKSPACE) == committed["files"]
