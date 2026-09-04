"""
Task loader for Hyper-τ tasks.

Loads :class:`HyperTask` definitions from ``data/tau2/hyper/tasks/``, one JSON
file per task alongside the corpus ``MANIFEST.md``::

    data/tau2/hyper/tasks/
    ├── MANIFEST.md
    ├── 001_airline_plus_construction_core_evidence_....json
    ├── 002_airline_plus_construction_core_evidence_....json
    └── ...

A task's source domain comes from its ``source_domain`` field, not from its
location on disk.

The ``load_hyper_tau_*`` functions are low-level fixture loaders and include
frozen legacy baselines. Product-facing discovery and execution must use the
``load_active_hyper_tau_*`` functions, which exclude canonical airline/retail
unless an ablation opts in explicitly.
"""

import json
from pathlib import Path
from typing import Optional

from loguru import logger

from tau2.hyper.data_model import HyperTauTask
from tau2.utils.utils import DATA_DIR

HYPER_TAU_DATA_DIR = DATA_DIR / "tau2" / "hyper"
HYPER_TAU_TASKS_DIR = HYPER_TAU_DATA_DIR / "tasks"

# ``airline`` and ``retail`` remain on disk only as frozen memorization
# baselines. Product-facing Hyper-τ surfaces must use the standalone plus
# corpora unless an ablation explicitly opts into a legacy baseline.
LEGACY_HYPER_TAU_DOMAIN_REPLACEMENTS = {
    "airline": "airline_plus",
    "retail": "retail_plus",
}


class LegacyHyperTauDomainError(ValueError):
    """Raised when a maintained Hyper-τ surface targets a legacy corpus."""


def require_active_hyper_tau_domain(
    source_domain: str,
    *,
    allow_legacy: bool = False,
) -> None:
    """Reject frozen legacy baselines unless an ablation opts in explicitly."""
    replacement = LEGACY_HYPER_TAU_DOMAIN_REPLACEMENTS.get(source_domain)
    if replacement is None or allow_legacy:
        return
    raise LegacyHyperTauDomainError(
        f"Hyper-τ source domain {source_domain!r} is a frozen legacy baseline "
        f"and is disabled by default. Use {replacement!r}. Legacy airline/retail "
        "may be used only for an explicitly requested ablation; CLI users can "
        "opt in with --allow-legacy-domain."
    )


def load_hyper_tau_task(task_id: str) -> HyperTauTask:
    """Load a single Hyper-τ task by its ID.

    Searches all domain subdirectories under the tasks folder for a
    JSON file whose ``id`` field matches *task_id*.

    Args:
        task_id: The task ID to load.

    Returns:
        The loaded HyperTauTask.

    Raises:
        FileNotFoundError: If no task with the given ID is found.
    """
    all_tasks = load_all_hyper_tau_tasks()
    for task in all_tasks:
        if task.id == task_id:
            return task
    available = [t.id for t in all_tasks]
    raise FileNotFoundError(
        f"Hyper-τ task '{task_id}' not found. Available tasks: {available}"
    )


def load_active_hyper_tau_task(
    task_id: str,
    *,
    allow_legacy: bool = False,
) -> HyperTauTask:
    """Load a task that is available on maintained Hyper-τ surfaces."""
    try:
        task = load_hyper_tau_task(task_id)
    except FileNotFoundError:
        available = [task.id for task in load_active_hyper_tau_tasks()]
        raise FileNotFoundError(
            f"Hyper-τ task {task_id!r} not found. "
            f"Available maintained tasks: {available}"
        ) from None
    require_active_hyper_tau_domain(
        task.source_domain,
        allow_legacy=allow_legacy,
    )
    return task


def load_hyper_tau_tasks(source_domain: Optional[str] = None) -> list[HyperTauTask]:
    """Load Hyper-τ tasks, optionally filtered by source domain.

    Args:
        source_domain: If provided, only return tasks for this source domain.
            If None, returns all tasks.

    Returns:
        List of HyperTauTask objects.
    """
    all_tasks = load_all_hyper_tau_tasks()
    if source_domain is not None:
        return [t for t in all_tasks if t.source_domain == source_domain]
    return all_tasks


def load_active_hyper_tau_tasks(
    source_domain: Optional[str] = None,
    *,
    allow_legacy: bool = False,
) -> list[HyperTauTask]:
    """Load tasks exposed by maintained Hyper-τ discovery surfaces."""
    tasks = load_hyper_tau_tasks(source_domain=source_domain)
    if allow_legacy:
        return tasks
    return [
        task
        for task in tasks
        if task.source_domain not in LEGACY_HYPER_TAU_DOMAIN_REPLACEMENTS
    ]


def load_all_hyper_tau_tasks() -> list[HyperTauTask]:
    """Load all Hyper-τ tasks from the tasks directory.

    Returns:
        List of all HyperTauTask objects.
    """
    tasks: list[HyperTauTask] = []

    if not HYPER_TAU_TASKS_DIR.exists():
        logger.warning(f"Hyper-τ tasks directory does not exist: {HYPER_TAU_TASKS_DIR}")
        return tasks

    for task_file in sorted(HYPER_TAU_TASKS_DIR.glob("*.json")):
        try:
            task = _load_task_from_file(task_file)
            tasks.append(task)
        except Exception as e:
            logger.error(f"Error loading Hyper-τ task from {task_file}: {e}")

    logger.debug(f"Loaded {len(tasks)} Hyper-τ tasks")
    return tasks


def list_hyper_tau_task_ids(source_domain: Optional[str] = None) -> list[str]:
    """List available Hyper-τ task IDs.

    Args:
        source_domain: If provided, only list tasks for this source domain.

    Returns:
        List of task ID strings.
    """
    tasks = load_hyper_tau_tasks(source_domain=source_domain)
    return [t.id for t in tasks]


def _load_task_from_file(path: Path) -> HyperTauTask:
    """Load a single HyperTauTask from a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        The loaded HyperTauTask.
    """
    with open(path) as f:
        data = json.load(f)
    return HyperTauTask(**data)
