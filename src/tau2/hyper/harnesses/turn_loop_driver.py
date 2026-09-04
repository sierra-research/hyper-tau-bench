"""Run a single-turn coding harness in a bounded continuation loop.

OpenCode's ``run`` executes one conversational turn: the process exits as
soon as the model replies without tool calls. Construction builds instead
need the developer to keep working until it calls the hyper_tau ``submit``
MCP tool — at which point the host cancels the harness process from the
outside, so a submit never depends on this driver noticing anything. The
driver bridges the gap for models that end turns early: it sends the
developer prompt as the first turn, then keeps issuing continuation turns
until the host kills it (submit, step budget, or wall clock) or the
continuation allowance runs out. A non-zero exit from any turn ends the
loop rather than retrying into a broken harness.
"""

from __future__ import annotations

import os
import subprocess
import sys

MAX_CONTINUES = int(os.environ.get("TAU2_TURN_LOOP_MAX_CONTINUES", "60"))
CONTINUE_PROMPT = (
    "Continue. You have not called the hyper_tau submit tool yet, so your "
    "work is not saved. Keep working toward a submission: implement, "
    "validate with run_local_test, and call submit once you are confident "
    "in your workspace."
)


def main() -> None:
    command = sys.argv[1:]
    if not command:
        sys.stderr.write("turn_loop_driver: no harness command given\n")
        raise SystemExit(2)
    prompt = sys.stdin.read().strip()
    if not prompt:
        sys.stderr.write("turn_loop_driver: empty developer prompt on stdin\n")
        raise SystemExit(2)
    returncode = subprocess.call([*command, prompt])
    continues = 0
    while returncode == 0 and continues < MAX_CONTINUES:
        continues += 1
        returncode = subprocess.call([*command, "--continue", CONTINUE_PROMPT])
    raise SystemExit(returncode)


if __name__ == "__main__":
    main()
