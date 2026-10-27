"""Build a release folder: complete partition, internal notes stripped, VERSION, notes.

``release/RELEASE_NOTES.md`` in the model repository is the append-only log: ``fact release``
adds a section for a new version (a version's section is written once, never edited), and the
release folder gets a copy."""

import datetime
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from factmodel import __version__
from factmodel.core.release import Disposition, ReleaseInput, partition
from factmodel.equivalence.harness import drops
from factmodel.gate.runner import run_gate
from factmodel.io.yaml_strict import YamlLoadError, load
from factmodel.model.loader import inspect_model
from factmodel.repo import dump_yaml
from factmodel.schemas.build import SCHEMA_VERSION

# Internal notes sit between two marker lines; everything from the begin line to the end line
# leaves the release. Markers are explicit; prose is never pattern-matched (spec/SPEC.md).
BEGIN = "internal:begin"
END = "internal:end"
SKIP_PARTS = frozenset({".git", "__pycache__", ".venv"})
NOTES = "RELEASE_NOTES.md"
VERSION_FILE = "VERSION"


class ReleaseError(ValueError):
    """A release that must not be built; the message says why."""


@dataclass
class ReleaseResult:
    out: Path
    version: str
    files: list[Disposition] = field(default_factory=list)

    def count(self, disposition: str) -> int:
        return sum(1 for f in self.files if f.disposition == disposition)


def _skipped(rel: Path) -> bool:
    return bool(SKIP_PARTS & set(rel.parts)) or rel.parts[:2] == ("release", "out")


def inputs(root: Path) -> list[ReleaseInput]:
    """Every file of the repository, with kind and top-level keys for YAML model files."""
    out = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root)
        if _skipped(rel):
            continue
        kind: str | None = None
        keys: tuple[str, ...] = ()
        if path.suffix in (".yaml", ".yml"):
            try:
                data = load(path).data
            except YamlLoadError:
                data = None
            if isinstance(data, dict) and isinstance(data.get("kind"), str):
                kind, keys = data["kind"], tuple(str(k) for k in data)
        out.append(ReleaseInput(rel.as_posix(), kind, keys))
    return out


def strip_internal(text: str, name: str) -> str:
    kept, inside = [], False
    for line in text.splitlines(keepends=True):
        if BEGIN in line:
            if inside:
                raise ReleaseError(f"{name}: {BEGIN} inside an internal block")
            inside = True
        elif END in line:
            if not inside:
                raise ReleaseError(f"{name}: {END} without {BEGIN}")
            inside = False
        elif not inside:
            kept.append(line)
    if inside:
        raise ReleaseError(f"{name}: {BEGIN} is never closed")
    return "".join(kept)


def _commit(root: Path) -> str:
    try:
        done = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return done.stdout.strip() or "unknown"


def _section(version: str, day: str, result: ReleaseResult, commit: str, layers: Any) -> str:
    lines = [
        f"## {version} - {day}",
        "",
        f"- Files: {result.count('export')} exported, {result.count('project')} projected, "
        f"{result.count('refuse')} refused.",
        f"- Schema {SCHEMA_VERSION}, framework {__version__}, source commit {commit}.",
    ]
    for layer in sorted(layers.values(), key=lambda la: la.id):
        lines.append(f"- Layer {layer.id}: {layer.status}.")
    return "\n".join(lines) + "\n"


def build(root: Path, out: Path, version: str, day: str | None = None) -> ReleaseResult:
    """Build the release in ``out``. Refuses on a failing gate, an equivalence drop of a
    reviewed layer, a partition failure or an unclosed internal block."""
    root, out = root.resolve(), out.resolve()
    day = day or datetime.date.today().isoformat()
    report = run_gate(root)
    if not report.passed:
        raise ReleaseError(f"the gate fails ({', '.join(report.failed)}); run fact check")
    model = inspect_model(root).model
    for layer in model.layers.values():
        if layer.status == "reviewed" and (dropped := drops(root, layer.id)):
            message = f"layer {layer.id} dropped against its accepted run: {', '.join(dropped)}"
            raise ReleaseError(message)
    if model.allowlist is None:
        raise ReleaseError("no release allowlist (release/allowlist.yaml)")
    plan = partition(model.allowlist, inputs(root))
    if plan.failures:
        listed = "; ".join(" ".join(filter(None, (f.path, f.reason, f.key))) for f in plan.failures)
        raise ReleaseError(f"the partition fails: {listed}")
    # the notes live in the model repository (committed) and are copied into the release
    notes_path = root / "release" / NOTES
    previous = notes_path.read_text(encoding="utf-8") if notes_path.is_file() else ""
    if out.exists():
        if any(out.iterdir()) and not (out / VERSION_FILE).is_file():
            raise ReleaseError(f"{out} is not empty and holds no release; choose another folder")
        shutil.rmtree(out)
    result = ReleaseResult(out, version, list(plan.files))
    for item in plan.files:
        if item.disposition == "refuse":
            continue
        source, target = root / item.path, out / item.path
        target.parent.mkdir(parents=True, exist_ok=True)
        if item.disposition == "project":
            data = load(source).data
            text = dump_yaml({k: v for k, v in data.items() if k in item.keep})
            target.write_text(text, encoding="utf-8")
            continue
        raw = source.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            target.write_bytes(raw)
            continue
        if BEGIN in text or END in text:
            target.write_text(strip_internal(text, item.path), encoding="utf-8")
        else:
            target.write_bytes(raw)
    commit = _commit(root)
    (out / VERSION_FILE).write_text(
        f"release: {version}\nsource_commit: {commit}\nschema_version: {SCHEMA_VERSION}\n"
        f"framework_version: {__version__}\n",
        encoding="utf-8",
    )
    if f"## {version} - " in previous:
        notes = previous  # a version's section is written once and never edited
    else:
        notes = (
            previous or "# Release notes\n\nOne section per release, newest last; never edited.\n"
        )
        notes = notes.rstrip("\n") + "\n\n" + _section(version, day, result, commit, model.layers)
    if notes != previous:
        notes_path.parent.mkdir(parents=True, exist_ok=True)
        notes_path.write_text(notes, encoding="utf-8")
    (out / NOTES).write_text(notes, encoding="utf-8")
    return result
