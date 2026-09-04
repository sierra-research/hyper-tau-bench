"""Tests for the developer-visible sandbox Git baseline."""

import subprocess

from tau2.hyper.sandbox.orchestrator import initialize_kit_repository


def _git(kit_path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=kit_path,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def test_initialize_kit_repository_creates_one_visible_baseline(tmp_path):
    (tmp_path / "README.md").write_text("Visible instructions\n")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "agent.py").write_text("# starter\n")

    commit = initialize_kit_repository(tmp_path)

    assert commit == _git(tmp_path, "rev-parse", "HEAD")
    assert _git(tmp_path, "rev-list", "--count", "HEAD") == "1"
    assert _git(tmp_path, "status", "--porcelain") == ""
    assert _git(tmp_path, "branch", "--show-current") == "main"
    assert _git(tmp_path, "log", "-1", "--pretty=%s") == "Initial import"


def test_initialize_kit_repository_replaces_no_existing_history(tmp_path):
    """An explicit kit with history is rejected instead of overwritten."""
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)

    try:
        initialize_kit_repository(tmp_path)
    except ValueError as exc:
        assert "already contains Git metadata" in str(exc)
    else:
        raise AssertionError("expected an existing repository to be rejected")
