"""Run a harness CLI with the developer prompt appended as an argument.

Some native harnesses (OpenCode's ``run``, Prime Agent's ``--mode json``)
take the prompt as a positional argument instead of reading stdin. The
supervised runtime always delivers the prompt on stdin, so this driver
bridges the two: it reads stdin to EOF and replaces itself with the
requested command plus the prompt as the final argument.
"""

from __future__ import annotations

import os
import sys


def main() -> None:
    command = sys.argv[1:]
    if not command:
        sys.stderr.write("prompt_arg_driver: no harness command given\n")
        raise SystemExit(2)
    prompt = sys.stdin.read().strip()
    if not prompt:
        sys.stderr.write("prompt_arg_driver: empty developer prompt on stdin\n")
        raise SystemExit(2)
    os.execvp(command[0], [*command, prompt])


if __name__ == "__main__":
    main()
