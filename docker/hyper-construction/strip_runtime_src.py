#!/usr/bin/env python3
"""Strip evaluation-design source from the construction runtime image.

Builder agents can read everything under /opt/tau2, so the image may ship
only the modules the in-container runtime actually executes:

- ``candidate_server`` (sealed scoring / local-test candidate process),
- ``callback_mcp`` (in-container MCP stub proxying to the host broker),
- ``model_gateway`` (sidecar entrypoint),
- the Developer-facing contract surface the kit documents
  (``agent_context``, ``client_api/__init__.py``), and
- ``runtime_contract`` (host<->image contract check), and
- the in-container harness drivers (codex/opencode/prime).

Everything else under ``tau2/hyper`` is host-only machinery — client-defect
implementations, graders, client-simulator internals, task construction —
and is deleted fail-closed: a module added to ``tau2/hyper`` later does NOT
ship unless it is added to ``KEEP_HYPER`` here (and the mirror test in
``tests/test_hyper/test_runtime_image_surface.py`` passes).

Run from the tau2 project root (the directory containing ``src``).
"""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

# Relative to src/tau2/hyper. Fail-closed allowlist of shipped runtime source.
KEEP_HYPER = [
    "__init__.py",
    "action_catalog.py",
    "agent_context.py",
    "client_api/__init__.py",
    "runtime_contract.py",
    "sandbox/__init__.py",
    "sandbox/candidate_server.py",
    "sandbox/callback_mcp.py",
    "sandbox/model_gateway.py",
    # In-container harness drivers (executed via `python -m` inside the
    # builder container; self-contained — no tau2 imports). A branch that
    # adds a new driver must allowlist it here or its image build fails
    # at the keep-list check.
    "harnesses/__init__.py",
    "harnesses/codex_driver.py",
    "harnesses/prompt_arg_driver.py",
    "harnesses/turn_loop_driver.py",
]

# Strings that must not survive in shipped source after the strip.
# ("live_experiment" is NOT a marker: run_live_experiment is a
# Developer-facing MCP tool name in callback_mcp.) These
# catch a future re-export or inlined copy of host-only machinery inside a
# shipped module.
FORBIDDEN_MARKERS = [
    "client_api.defects",
    "client_api.runtime",
    "apply_response_defect",
    "policy_coverage",
    "client_lever_gate",
    "held_fact",
    "client_instructions",
]

# Host-only trees outside tau2/hyper that carry evaluation vocabulary or
# results tooling and are never imported by the in-container runtime.
REMOVE_OUTSIDE_HYPER = [
    "cli.py",
    "scripts",
]

# Project-root files needed only to build the venv (uv sync runs before this
# script). The repo README and package metadata name the benchmark, its
# paper, and the private repo — a Developer reading /opt/tau2 must not learn
# which benchmark it is in.
REMOVE_PROJECT_ROOT = [
    "README.md",
    "pyproject.toml",
    "uv.lock",
]

MINIMAL_PACKAGE_INIT = (
    '"""Minimal tau2 package init for construction sandbox runtime."""\n'
)


def main() -> int:
    root = Path.cwd()
    src = root / "src" / "tau2"
    hyper = src / "hyper"
    if not hyper.is_dir():
        print(f"error: {hyper} is not a directory (run from the project root)")
        return 1

    keep = {hyper / rel for rel in KEEP_HYPER}
    missing = sorted(str(p) for p in keep if not p.is_file())
    if missing:
        print("error: keep-listed runtime files are missing:")
        for path in missing:
            print(f"  {path}")
        return 1

    # 1. Canonical domains and host-only trees outside hyper never ship.
    shutil.rmtree(src / "domains", ignore_errors=True)
    for rel in REMOVE_OUTSIDE_HYPER:
        target = src / rel
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
    for rel in REMOVE_PROJECT_ROOT:
        target = root / rel
        if target.exists():
            target.unlink()

    # 2. Fail-closed sweep of tau2/hyper.
    removed = 0
    for path in sorted(hyper.rglob("*"), reverse=True):
        if path.is_file() and path not in keep:
            path.unlink()
            removed += 1
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()

    # 3. Replace the eager package init so importing framework modules does
    #    not pull in the domain registry.
    (src / "__init__.py").write_text(MINIMAL_PACKAGE_INIT)

    # 4. Nothing outside the keep list may remain under hyper.
    leftovers = [p for p in hyper.rglob("*") if p.is_file() and p not in keep]
    if leftovers:
        print("error: files survived the strip:")
        for path in leftovers:
            print(f"  {path}")
        return 1

    # 5. No shipped source may reference host-only machinery.
    violations = []
    for path in sorted((root / "src").rglob("*.py")):
        text = path.read_text(errors="replace")
        for marker in FORBIDDEN_MARKERS:
            if marker in text:
                violations.append(f"{path}: {marker}")
    if violations:
        print("error: forbidden markers in shipped source:")
        for line in violations:
            print(f"  {line}")
        return 1

    print(f"stripped tau2/hyper to {len(keep)} files (removed {removed}):")
    for path in sorted(keep):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        print(f"  {digest}  {path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
