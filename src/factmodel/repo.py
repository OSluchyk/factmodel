"""Create a model repository and register sources (``fact init``, ``fact source add``)."""

import datetime
import io
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from factmodel import __version__
from factmodel.core import derived
from factmodel.core.drafts import EntityDraft
from factmodel.io.yaml_strict import loads
from factmodel.model.loader import CONFIG_FILE, bundled_profile, inspect_model, load_model
from factmodel.model.types import Snapshot, Source
from factmodel.resources import framework_file, framework_text
from factmodel.schemas.build import SCHEMA_VERSION, pattern, schema_for

LAYOUT = (
    "sources/snapshots",
    "physical/entities",
    "physical/services",
    "semantic",
    "registers/findings",
    "registers/escalations",
    "registers/hazards",
    "registers/decisions",
    "evidence",
    "probes",
    "drafts",
    "maintenance",
    "release",
)


class RepoError(ValueError):
    """The repository cannot be created or changed as asked."""


def dump_yaml(doc: dict[str, Any]) -> str:
    yaml = YAML(typ="safe", pure=True)
    yaml.default_flow_style = False
    yaml.sort_base_mapping_type_on_output = False  # type: ignore[assignment]
    buf = io.StringIO()
    yaml.dump(doc, buf)
    return buf.getvalue()


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "-", name.lower()).strip("-_")[:64] or "model"
    if not re.match(pattern("slug"), slug):
        raise RepoError(f"cannot make a model ID from {name!r}")
    return slug


def _check(kind: str, doc: dict[str, Any]) -> None:
    errors = [
        f"{e.json_path}: {e.message}"
        for e in Draft202012Validator(schema_for(kind)).iter_errors(doc)
    ]
    if errors:
        raise RepoError("; ".join(errors))


def init(
    target: Path, profile: str, model_id: str | None = None, anchor: str | None = None
) -> list[Path]:
    """Create a model repository in ``target`` and return the files written.

    The anchor entity defaults to the slug of the profile's subject (D-012). A profile without
    a subject gives a model without an anchor (D-015).
    """
    if (target / CONFIG_FILE).exists():
        raise RepoError(f"{target / CONFIG_FILE} already exists")
    profile_text = bundled_profile(profile)
    if profile_text is None:
        raise RepoError(f"unknown profile {profile!r}; see profiles/ in the framework")
    subject = loads(profile_text, profile).data.get("subject")
    if subject is None and anchor is not None:
        raise RepoError(f"profile {profile!r} names no subject, so the model has no anchor")
    config: dict[str, Any] = {
        "kind": "model-config",
        "id": model_id or _slug(target.resolve().name),
        "framework_version": __version__,
        "schema_version": SCHEMA_VERSION,
        "profile": profile,
    }
    if subject is not None:
        config["anchor_entity"] = anchor or _slug(str(subject))
    # written explicitly so the setting is visible; only example models set it true (D-014)
    config["treat_synthetic_as_representative"] = False
    _check("model-config", config)
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    def put(rel: str, text: str) -> None:
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(path)

    put(CONFIG_FILE, dump_yaml(config))
    for folder in LAYOUT:
        put(f"{folder}/.gitkeep", "")
    substitutions = {
        "{version}": __version__,
        "{profile}": profile,
        "{date}": datetime.date.today().isoformat(),
    }

    def template(*parts: str) -> str:
        text = framework_text("agent", *parts)
        if text is None:
            raise RepoError(f"framework template agent/{'/'.join(parts)} is missing")
        for key, value in substitutions.items():
            text = text.replace(key, value)
        return text

    put("AGENTS.md", template("AGENTS.md"))
    put("agent/brief.md", template("templates", "brief.md"))
    put("agent/report.md", template("templates", "report.md"))
    put("CHANGELOG.md", template("templates", "CHANGELOG.md"))
    put(".github/workflows/fact-check.yml", template("templates", "fact-check.yml"))
    skills = framework_file("agent", "skills")
    if skills is not None:
        for entry in sorted(skills.iterdir(), key=lambda e: e.name):
            if entry.is_file():
                put(f".claude/skills/{entry.name}", entry.read_text(encoding="utf-8"))
            elif entry.is_dir():
                for item in sorted(entry.iterdir(), key=lambda e: e.name):
                    if item.is_file():
                        put(
                            f".claude/skills/{entry.name}/{item.name}",
                            item.read_text(encoding="utf-8"),
                        )
    values = derived.derive_model(load_model(target))
    assert values is not None
    written += derived.write(target.resolve(), derived.render(values))
    return written


def add_source(root: Path, source: dict[str, Any]) -> Path:
    """Write ``sources/<id>.yaml`` after checking it against the source schema."""
    if not (root / CONFIG_FILE).is_file():
        raise RepoError(f"{root} is not a model repository (no {CONFIG_FILE})")
    doc = {"kind": "source", **{k: v for k, v in source.items() if v is not None}}
    _check("source", doc)
    path = root / "sources" / f"{doc['id']}.yaml"
    if path.exists():
        raise RepoError(f"source {doc['id']!r} already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_yaml(doc), encoding="utf-8")
    return path


def source_of(root: Path, source_id: str) -> Source:
    """The registered source with this ID, as loaded."""
    model = inspect_model(root).model
    source = model.sources.get(source_id)
    if source is None:
        raise RepoError(f"source {source_id!r} is not registered (or its file is invalid)")
    return source


def _source_path(root: Path, source_id: str) -> Path:
    for f in inspect_model(root).model.files:
        if isinstance(f.obj, Source) and f.obj.id == source_id:
            return root / f.path
    raise RepoError(f"source {source_id!r} is not registered")


def set_current_pin(root: Path, source_id: str, pin: str) -> None:
    """Record the version last read on the source file, keeping its layout and comments."""
    path = _source_path(root, source_id)
    yaml = YAML(typ="rt")
    yaml.width = 4096  # keep the author's line breaks; never re-wrap text
    doc = yaml.load(path.read_text(encoding="utf-8"))
    if doc.get("current_pin") == pin:
        return
    doc["current_pin"] = pin
    buf = io.StringIO()
    yaml.dump(doc, buf)
    path.write_text(buf.getvalue(), encoding="utf-8")


def write_text_if_changed(path: Path, text: str) -> bool:
    """Write ``text`` unless the file already holds it; return whether it changed."""
    return _write_if_changed(path, text)


def _write_if_changed(path: Path, text: str) -> bool:
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


SNAPSHOT_NAME = re.compile(
    r"^(?P<source>.+)@(?P<date>\d{4}-\d{2}-\d{2})(?:_(?P<seq>[2-9]|[1-9]\d+))?\.yaml$"
)


def snapshot_sequence(path: Path) -> tuple[str, int]:
    """The (date, sequence) a snapshot file name carries: ``<source>@<date>.yaml`` is the
    first read of that day, ``<source>@<date>_<n>.yaml`` the n-th."""
    match = SNAPSHOT_NAME.match(path.name)
    if match is None:
        raise RepoError(f"{path.name} is not a snapshot file name (<source>@<date>[_n].yaml)")
    return match.group("date"), int(match.group("seq") or 1)


def snapshot_files(root: Path, source_id: str) -> list[Path]:
    """A source's snapshot files, oldest first: by date, then by sequence within the day."""
    found = (root / "sources" / "snapshots").glob(f"{source_id}@*.yaml")
    return sorted(found, key=snapshot_sequence)


def _sequenced(snap: Snapshot, seq: int) -> Snapshot:
    """The snapshot with the day's sequence on its pin: ``<pin>_<n>`` from the second read on."""
    if snap.pin is None or seq == 1:
        return snap
    return snap.model_copy(update={"pin": f"{snap.pin}_{seq}"})


def write_snapshot(root: Path, snap: Snapshot) -> tuple[Path, bool, Snapshot]:
    """Write the snapshot as ``sources/snapshots/<source-id>@<date>.yaml``, or as
    ``<source-id>@<date>_<n>.yaml`` when that day already holds a different read; a file whose
    content matches is kept. Returns the file, whether it changed and the snapshot as written
    (its pin carries the sequence, so two reads of one day never share a pin)."""
    folder = root / "sources" / "snapshots"
    seq = 1
    while True:
        suffix = "" if seq == 1 else f"_{seq}"
        path = folder / f"{snap.source}@{snap.taken_on}{suffix}.yaml"
        written = _sequenced(snap, seq)
        text = dump_yaml(written.model_dump(mode="json", exclude_none=True, by_alias=True))
        if not path.is_file():
            return path, _write_if_changed(path, text), written
        if path.read_text(encoding="utf-8") == text:
            return path, False, written
        seq += 1


def latest_snapshot(root: Path, source_id: str) -> Path:
    found = snapshot_files(root, source_id)
    if not found:
        raise RepoError(f"no snapshot for source {source_id!r}; run fact snapshot first")
    return found[-1]


def write_drafts(root: Path, drafts: list[EntityDraft]) -> list[Path]:
    """Write drafts under ``drafts/``; return the files that changed."""
    changed = []
    for draft in drafts:
        if not draft.path.startswith("drafts/"):
            raise RepoError(f"drafts go to drafts/, never to {draft.path}")
        path = root / draft.path
        if _write_if_changed(path, dump_yaml(draft.document)):
            changed.append(path)
    return changed
