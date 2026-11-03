"""docs/article-support.md, the commands and outputs Part 2 of the article shows, cannot drift
from the repository: every command is a line of ``examples/tpch/scripts/reproduce.sh``, every
copied block is verbatim in a file its section names, and every output line is rebuilt from
the committed artifacts of ``examples/tpch`` (seconds dropped)."""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from factmodel.io.yaml_strict import load
from tests.docs.blocks import FENCE, timeless

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "docs" / "article-support.md"
EXAMPLE = ROOT / "examples" / "tpch"
SOURCE = "tpch-duckdb"
DAY = "2026-11-02"
SCRIPT_VALUES = {"$M": "examples/tpch", "$S": SOURCE, "$DAY": DAY}
TEXT_SUFFIXES = (".md", ".yaml", ".jsonl", ".sql", ".sh", ".py")


def _sections(text: str) -> list[tuple[str, list[tuple[str, str]], list[str]]]:
    """(heading, [(language, body)], files named on the From line) per numbered section."""
    out = []
    for part in re.split(r"^## ", text, flags=re.MULTILINE)[1:]:
        heading = part.splitlines()[0]
        blocks = [(m.group(1), m.group(2).rstrip("\n")) for m in FENCE.finditer(part)]
        froms = re.findall(r"^From: (.*)$", part, flags=re.MULTILINE)
        assert len(froms) == 1, f"section {heading!r} needs one From line"
        out.append((heading, blocks, re.findall(r"`([^`]+)`", froms[0])))
    return out


def _script() -> str:
    """reproduce.sh with its variables filled in and the shell quotes dropped."""
    text = (EXAMPLE / "scripts" / "reproduce.sh").read_text(encoding="utf-8")
    for var, value in SCRIPT_VALUES.items():
        text = text.replace(var, value)
    return text.replace('"', "")


def _summary() -> str:
    done = subprocess.run(
        [sys.executable, str(EXAMPLE / "scripts" / "summary.py"), str(EXAMPLE), DAY],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


def _data(path: Path) -> Any:
    return load(path).data


def _run_lines() -> list[str]:
    """The lines the run prints, rebuilt from what it wrote; a duration is ``_ s``."""
    snapshots = EXAMPLE / "sources" / "snapshots"
    a = _data(snapshots / f"{SOURCE}@{DAY}.yaml")
    b = _data(snapshots / f"{SOURCE}@{DAY}_2.yaml")
    keys = _data(EXAMPLE / "drafts" / SOURCE / "keys.yaml")
    joins = _data(EXAMPLE / "drafts" / SOURCE / "joins.yaml")
    drift = (EXAMPLE / "generated" / f"drift-{SOURCE}.md").read_text(encoding="utf-8")
    results = EXAMPLE / "probes" / "results" / f"{SOURCE}@{DAY}.jsonl"
    probes = list((EXAMPLE / "probes").glob("*.yaml"))
    evidence = list((EXAMPLE / "evidence" / "probes").glob("*.yaml"))
    constraints = [c for o in b["objects"] for c in o.get("constraints") or []]
    kinds = {
        k: sum(c["constraint_type"] == k for c in constraints)
        for k in ("foreign_key", "primary_key")
    }
    not_null = sum(1 for o in b["objects"] for f in o["fields"] if f["nullable"] is False)
    measured = [
        json.loads(line)
        for line in results.read_text(encoding="utf-8").splitlines()
        if '"probe"' in line
    ]
    assert all("measurement" in m for m in measured)
    key_count = sum(len(o["candidates"]) for o in keys["objects"])
    return [
        f"wrote sources/snapshots/{SOURCE}@{DAY}.yaml ({len(a['objects'])} objects)",
        f"{len(keys['objects'])} tables, {key_count} key candidates, {keys['queries']} queries,"
        f" _ s: wrote drafts/{SOURCE}/keys.yaml",
        f"{len(a['objects'])} tables, {len(joins['candidates'])} join candidates,"
        f" {joins['queries']} queries, _ s: wrote drafts/{SOURCE}/joins.yaml",
        f"[('FOREIGN KEY', {kinds['foreign_key']}), ('NOT NULL', {not_null}),"
        f" ('PRIMARY KEY', {kinds['primary_key']})]",
        f"wrote sources/snapshots/{SOURCE}@{DAY}_2.yaml ({len(b['objects'])} objects)",
        f"changed_fact {drift.count('| changed_fact |')}; 1 files written",
        f"  generated/drift-{SOURCE}.md",
        f"{len(probes)} probes, {len(probes)} written, 0 facts skipped",
        f"{len(measured)} probes run, 0 failed: probes/results/{SOURCE}@{DAY}.jsonl",
        f"{len(evidence)} in range, 0 out of range, 0 failed, 0 rejected;"
        f" {len(probes) + len(evidence)} files written",
    ]


def test_every_block_is_what_the_repository_holds() -> None:
    sections = _sections(PAGE.read_text(encoding="utf-8"))
    assert [s[0][:2] for s in sections] == ["1.", "2.", "3.", "4.", "5.", "6."]
    script = _script()
    shared = "\n".join(_run_lines()) + "\n" + _summary()
    for heading, blocks, files in sections:
        assert blocks, heading
        corpus = shared
        for name in files:
            path = ROOT / name
            assert path.is_file(), f"{heading}: {name} is not in the repository"
            if path.suffix in TEXT_SUFFIXES:
                corpus += "\n" + path.read_text(encoding="utf-8")
        for language, body in blocks:
            if language == "bash":
                for line in body.splitlines():
                    assert line in script, f"{heading}: not a line of reproduce.sh: {line!r}"
            elif language == "yaml":
                assert body in corpus, f"{heading}: the yaml block is not verbatim in its file"
            else:
                for line in body.splitlines():
                    assert timeless(line) in timeless(corpus), f"{heading}: {line!r}"


def test_page_is_outside_the_navigation_and_unlinked() -> None:
    assert "article-support" not in (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    link = re.compile(r"\]\([^)]*article-support[^)]*\)")
    linked = [
        p.relative_to(ROOT).as_posix()
        for p in ROOT.rglob("*.md")
        if not {".venv", "site", "_work", ".claude"} & set(p.parts)
        and p != PAGE
        and link.search(p.read_text(encoding="utf-8"))
    ]
    assert linked == []
