"""The sealed candidate runtime must import without tau2.domains.

The construction image (docker/hyper-construction/Dockerfile) deletes
``src/tau2/domains`` and replaces the package ``__init__`` with a minimal
one; ``candidate_server`` is then imported inside that image. Any module in
its import closure that pulls ``tau2.domains`` at import time breaks sealed
scoring for every construction task (observed 2026-08-21 when
``client_api.catalog`` grew top-level domain imports).
"""

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_MINIMAL_INIT = '"""Minimal tau2 package init for construction sandbox runtime."""\n'


def test_candidate_server_imports_in_a_domainless_runtime(tmp_path):
    stripped_src = tmp_path / "src"
    shutil.copytree(
        REPO_ROOT / "src" / "tau2",
        stripped_src / "tau2",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.md"),
    )
    shutil.rmtree(stripped_src / "tau2" / "domains")
    (stripped_src / "tau2" / "__init__.py").write_text(_MINIMAL_INIT)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import tau2.hyper.sandbox.candidate_server; print('import ok')",
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={
            "PATH": "/usr/bin:/bin",
            "PYTHONPATH": str(stripped_src),
            # Keep the interpreter from resolving the repo's real data dir;
            # importing must not need any data at all.
            "TAU2_DATA_DIR": str(tmp_path / "no-data"),
        },
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    assert "import ok" in result.stdout
