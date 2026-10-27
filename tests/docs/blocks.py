"""Run the command blocks of a Markdown page and check the outputs it promises.

Every fenced ``bash`` block runs, in order, in one shell session started in a working folder.
A fenced ``text`` block right after a line ``Output:`` lists lines that must appear in the
output of the ``bash`` blocks since the previous check.
"""

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

FENCE = re.compile(r"^```(\w+)\n(.*?)^```", re.MULTILINE | re.DOTALL)


@dataclass
class Step:
    commands: list[str] = field(default_factory=list)
    expected: list[str] = field(default_factory=list)


def steps(markdown: str) -> list[Step]:
    out: list[Step] = [Step()]
    for match in FENCE.finditer(markdown):
        kind, body = match.group(1), match.group(2)
        before = markdown[: match.start()].rstrip().splitlines()
        if kind == "bash":
            if out[-1].expected:
                out.append(Step())
            out[-1].commands.append(body)
        elif kind == "text" and before and before[-1].strip() == "Output:":
            out[-1].expected += [line for line in body.splitlines() if line.strip()]
    return [s for s in out if s.commands]


def run(markdown: str, cwd: Path, env: dict[str, str]) -> list[str]:
    """Run every step; return the output per step. Raises on a failed command or a promised
    line that did not appear."""
    plan = steps(markdown)
    script = ["set -euo pipefail"]
    for i, step in enumerate(plan):
        script.append(f"echo '@@STEP {i}@@'")
        script += step.commands
    done = subprocess.run(
        ["bash", "-c", "\n".join(script)], cwd=cwd, env=env, capture_output=True, text=True
    )
    if done.returncode != 0:
        raise AssertionError(f"a command failed:\n{done.stdout}\n{done.stderr}")
    parts = re.split(r"^@@STEP \d+@@$", done.stdout, flags=re.MULTILINE)[1:]
    for step, output in zip(plan, parts, strict=True):
        for line in step.expected:
            if line.strip() not in output:
                raise AssertionError(f"promised output missing: {line!r}\n--- got ---\n{output}")
    return parts
