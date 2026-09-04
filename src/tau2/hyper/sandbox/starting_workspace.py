"""Runtime loading and copying for authored starting workspaces.

A starting workspace's ``tree/`` is copied into a brownfield construction
kit only after its recorded hashes are verified. Workspaces ship with their
pins already generated and gated at authoring time.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Optional

from loguru import logger

from tau2.utils.utils import DATA_DIR

TREE_DIRNAME = "tree"
PINS_FILENAME = "workspace_pins.json"


def contamination_patterns(domain: Optional[str] = None) -> list[str]:
    """Canonical reference-implementation leakage patterns.

    Shared by the authoring gate and runtime submission extraction so the two
    scans cannot drift.
    """
    patterns = [
        "tau2.domains.",
        "data/tau2/domains",
        "src/tau2/domains",
        "framework_reference/example_domain",
    ]
    if domain:
        patterns.extend(
            [
                f"tau2.domains.{domain}",
                f"domains/{domain}",
                f"domains.{domain}",
            ]
        )
    return list(dict.fromkeys(patterns))


def resolve_starting_workspace_path(path: str | Path) -> Path:
    """Resolve a task's starting_workspace_path (absolute or data-relative)."""
    workspace_path = Path(path)
    if workspace_path.is_absolute():
        return workspace_path
    return DATA_DIR / workspace_path


_IGNORED_DIRNAMES = {"__pycache__"}
_IGNORED_FILENAMES = {".DS_Store"}
_IGNORED_SUFFIXES = {".pyc"}


def iter_workspace_tree_files(tree_dir: Path) -> list[Path]:
    """Return the content files in ``tree/``, excluding tooling byproducts."""
    return sorted(
        path
        for path in tree_dir.rglob("*")
        if path.is_file()
        and path.name not in _IGNORED_FILENAMES
        and path.suffix not in _IGNORED_SUFFIXES
        and not _IGNORED_DIRNAMES.intersection(path.relative_to(tree_dir).parts[:-1])
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_workspace_pins(workspace_dir: Path) -> dict[str, str]:
    """Compute {tree-relative path: sha256} for every file under tree/."""
    tree_dir = Path(workspace_dir) / TREE_DIRNAME
    if not tree_dir.is_dir():
        raise FileNotFoundError(f"Starting workspace has no tree/: {workspace_dir}")
    return {
        path.relative_to(tree_dir).as_posix(): _sha256(path)
        for path in iter_workspace_tree_files(tree_dir)
    }


def load_workspace_pins(workspace_dir: Path) -> dict[str, str]:
    """Load the recorded tree pins for a starting workspace."""
    pins_path = Path(workspace_dir) / PINS_FILENAME
    if not pins_path.exists():
        raise FileNotFoundError(
            f"Starting workspace has no {PINS_FILENAME}: {workspace_dir}. "
            "Shipped workspaces must carry their authored pins file."
        )
    payload = json.loads(pins_path.read_text())
    files = payload.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError(f"{pins_path} has no 'files' pin map.")
    return {str(path): str(digest) for path, digest in files.items()}


def verify_workspace_pins(workspace_dir: Path) -> list[str]:
    """Return pin-drift failures for a starting workspace (empty = fresh)."""
    workspace_dir = Path(workspace_dir)
    failures: list[str] = []
    try:
        recorded = load_workspace_pins(workspace_dir)
        actual = compute_workspace_pins(workspace_dir)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        return [str(e)]

    for path in sorted(set(recorded) - set(actual)):
        failures.append(f"pinned file missing from tree/: {path}")
    for path in sorted(set(actual) - set(recorded)):
        failures.append(f"unpinned file in tree/: {path}")
    for path in sorted(set(recorded) & set(actual)):
        if recorded[path] != actual[path]:
            failures.append(f"pin drift (edit without re-pin): {path}")
    return failures


def copy_starting_workspace_tree(
    workspace_dir: Path, kit_workspace_dir: Path
) -> list[str]:
    """Verify pins, then copy tree/ into a kit's workspace/ directory."""
    workspace_dir = Path(workspace_dir)
    failures = verify_workspace_pins(workspace_dir)
    if failures:
        raise ValueError(
            f"Starting workspace {workspace_dir} failed pin verification:\n"
            + "\n".join(f"  - {failure}" for failure in failures)
        )

    tree_dir = workspace_dir / TREE_DIRNAME
    kit_workspace_dir = Path(kit_workspace_dir)
    kit_workspace_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for source in iter_workspace_tree_files(tree_dir):
        relative = source.relative_to(tree_dir)
        destination = kit_workspace_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(relative.as_posix())
    logger.debug(f"  Seeded workspace/ with {len(copied)} files from {workspace_dir}")
    return copied
