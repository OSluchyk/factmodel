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
from factmodel.model.loader import CONFIG_FILE, bundled_profile, load_model
from factmodel.resources import framework_file, framework_text
from factmodel.schemas.build import pattern, schema_for

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


def init(target: Path, profile: str, model_id: str | None = None) -> list[Path]:
    """Create a model repository in ``target`` and return the files written."""
    if (target / CONFIG_FILE).exists():
        raise RepoError(f"{target / CONFIG_FILE} already exists")
    if bundled_profile(profile) is None:
        raise RepoError(f"unknown profile {profile!r}; see profiles/ in the framework")
    config = {
        "kind": "model-config",
        "id": model_id or _slug(target.resolve().name),
        "framework_version": __version__,
        "profile": profile,
    }
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
    put("CHANGELOG.md", template("templates", "CHANGELOG.md"))
    put(".github/workflows/fact-check.yml", template("templates", "fact-check.yml"))
    skills = framework_file("agent", "skills")
    if skills is not None:
        for entry in sorted(skills.iterdir(), key=lambda e: e.name):
            if entry.is_file():
                put(f".claude/skills/{entry.name}", entry.read_text(encoding="utf-8"))
    model = load_model(target)
    assert model.profile is not None
    for path in derived.write(
        model.root, derived.render(derived.derive(model.entities, model.evidence, model.profile))
    ):
        written.append(path)
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
