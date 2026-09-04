"""Guard the construction runtime image's shipped source surface.

The image build strips ``src/tau2/hyper`` down to the fail-closed allowlist
in ``docker/hyper-construction/strip_runtime_src.py``. Builder agents can
read everything under ``/opt/tau2``, so host-only machinery — client-defect
implementations, graders, client-simulator internals, task construction —
must never be reachable from a shipped module. These tests mirror the strip
at review time: a PR that adds a host-only import to a shipped module, or
host-only vocabulary to its source, fails here before an image is ever
built.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
HYPER = SRC / "tau2" / "hyper"
STRIP_SCRIPT = REPO_ROOT / "docker" / "hyper-construction" / "strip_runtime_src.py"

# Host-only machinery that must never be allowlisted for the image.
SENSITIVE_HYPER_MODULES = [
    "_inner.py",
    "client.py",
    "client_api/banking_docs.py",
    "client_api/capabilities.py",
    "client_api/catalog.py",
    "client_api/catalogs/__init__.py",
    "client_api/catalogs/airline.py",
    "client_api/catalogs/banking.py",
    "client_api/catalogs/retail.py",
    "client_api/catalogs/telecom.py",
    "client_api/defects.py",
    "client_api/development.py",
    "client_api/runtime.py",
    "transformations/fact_hierarchy.py",
    "grounding.py",
    "live_experiment.py",
    "recording.py",
    "response_phrasing.py",
    "task_loader.py",
    "harnesses/claude.py",
    "harnesses/codex.py",
    "harnesses/factory.py",
    "harnesses/opencode.py",
    "harnesses/prime.py",
    "sandbox/builder.py",
    "sandbox/kit.py",
    "sandbox/orchestrator.py",
    "sandbox/sealed_runner.py",
]


def _load_strip_module():
    spec = importlib.util.spec_from_file_location("strip_runtime_src", STRIP_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


strip = _load_strip_module()


def _import_time_imports(path: Path) -> set[str]:
    """tau2 modules imported when ``path`` is imported (skips lazy/typing)."""

    tree = ast.parse(path.read_text())
    found: set[str] = set()

    def is_type_checking(node: ast.If) -> bool:
        test = node.test
        return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
            isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
        )

    def walk(body) -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if isinstance(node, ast.If):
                if is_type_checking(node):
                    continue
                walk(node.body)
                walk(node.orelse)
                continue
            if isinstance(node, (ast.ClassDef, ast.Try, ast.With)):
                walk(getattr(node, "body", []))
                for handler in getattr(node, "handlers", []):
                    walk(handler.body)
                walk(getattr(node, "orelse", []))
                walk(getattr(node, "finalbody", []))
                continue
            if isinstance(node, ast.Import):
                found.update(
                    alias.name for alias in node.names if alias.name.startswith("tau2")
                )
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                if node.module and node.module.startswith("tau2"):
                    found.add(node.module)

    walk(tree.body)
    return found


def test_runtime_packages_do_not_import_authoring():
    """Benchmark execution must not depend on experimenter-only modules."""
    offenders: list[str] = []
    for package in ("harnesses", "sandbox", "transformations", "web"):
        for path in sorted((HYPER / package).rglob("*.py")):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports = [node.module]
                else:
                    continue
                if any(
                    imported.startswith("tau2.hyper.authoring") for imported in imports
                ):
                    offenders.append(str(path.relative_to(HYPER)))
                    break
    assert not offenders, f"runtime modules import authoring code: {offenders}"


def test_keep_list_files_exist():
    for rel in strip.KEEP_HYPER:
        assert (HYPER / rel).is_file(), f"keep-listed file missing: {rel}"


def test_sensitive_modules_are_not_keep_listed():
    keep = set(strip.KEEP_HYPER)
    for rel in SENSITIVE_HYPER_MODULES:
        assert rel not in keep, f"host-only module allowlisted: {rel}"


def test_sensitive_modules_still_tracked():
    """The sensitive list should track reality so renames don't blind us."""
    missing = [rel for rel in SENSITIVE_HYPER_MODULES if not (HYPER / rel).is_file()]
    assert not missing, (
        "sensitive modules were renamed or removed; update "
        f"SENSITIVE_HYPER_MODULES: {missing}"
    )


@pytest.mark.parametrize("rel", sorted(strip.KEEP_HYPER))
def test_shipped_modules_import_only_shipped_hyper_modules(rel):
    keep_modules = set()
    for keep_rel in strip.KEEP_HYPER:
        dotted = "tau2.hyper." + keep_rel[: -len(".py")].replace("/", ".")
        keep_modules.add(dotted.removesuffix(".__init__"))

    removed_prefixes = tuple(
        "tau2." + entry.removesuffix(".py").replace("/", ".")
        for entry in strip.REMOVE_OUTSIDE_HYPER
    ) + ("tau2.domains",)

    for imported in sorted(_import_time_imports(HYPER / rel)):
        if imported.startswith("tau2.hyper"):
            assert imported in keep_modules, (
                f"{rel} imports {imported} at import time, which the image "
                "strips; keep the import lazy/host-side or allowlist the "
                "module in strip_runtime_src.py"
            )
        else:
            assert not imported.startswith(removed_prefixes), (
                f"{rel} imports {imported}, which the image strips"
            )


@pytest.mark.parametrize("rel", sorted(strip.KEEP_HYPER))
def test_shipped_modules_carry_no_forbidden_markers(rel):
    text = (HYPER / rel).read_text()
    hits = [marker for marker in strip.FORBIDDEN_MARKERS if marker in text]
    assert not hits, f"{rel} mentions host-only machinery: {hits}"


def test_strip_removes_benchmark_naming_project_root_files():
    """/opt/tau2's root must not tell a Developer which benchmark this is.

    The repo README names the benchmark lineage; pyproject.toml names the
    public repo, homepage, and authors. They are needed only for uv sync,
    which runs before the strip.
    """
    root = set(strip.REMOVE_PROJECT_ROOT)
    assert {"README.md", "pyproject.toml", "uv.lock"} <= root


def test_kit_git_identity_is_neutral():
    """Kit git metadata is Developer-visible and must not name the harness."""
    orchestrator = SRC / "tau2" / "hyper" / "sandbox" / "orchestrator.py"
    text = orchestrator.read_text()
    assert "Hyper-tau kit baseline" not in text
    assert 'user.name", "Hyper-tau"' not in text
    dockerfile = (
        REPO_ROOT / "docker" / "hyper-construction" / "Dockerfile"
    ).read_text()
    assert "Hyper-tau Developer" not in dockerfile
    assert "hyper-tau.local" not in dockerfile


def test_dockerfile_runs_strip_and_ships_pdf_tooling():
    dockerfile = (
        REPO_ROOT / "docker" / "hyper-construction" / "Dockerfile"
    ).read_text()
    assert "strip_runtime_src.py" in dockerfile
    assert "poppler-utils" in dockerfile
    assert "qpdf" in dockerfile
    assert "pypdf" in dockerfile
    assert "openpyxl" in dockerfile
    assert "python-docx" in dockerfile
    assert "python-pptx" in dockerfile
