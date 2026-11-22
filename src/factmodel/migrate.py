"""``fact migrate``: which schema version a model uses, and whether this framework reads it.

A model records the framework release that created or last migrated it (``framework_version``)
and, since 1.0.0, the schema version its files were checked against (``schema_version``); the
installed schemas carry their own version (``spec/VERSIONING.md``). The model is compatible
when every file parses and validates against the installed schemas, whatever the versions say.
There are no migrations yet: they come with the first major schema change.

Since schemas 2.3.0 (D-023) a reviewed layer needs coverage in its accepted equivalence run; a
model from before validates, and the report names the layers to run and accept again.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from factmodel import __version__
from factmodel.gate.stages.layers import accepted_tested
from factmodel.model.loader import CONFIG_FILE, inspect_model
from factmodel.schemas.build import SCHEMA_VERSION

READ_STAGES = ("yaml", "schema")


@dataclass(frozen=True)
class Migration:
    """One schema step. ``apply`` rewrites a model's files from ``source`` to ``target``;
    None means no automatic step exists and the note says what a model needs."""

    source: str
    target: str
    note: str
    apply: Callable[[Path], list[Path]] | None = None


# The registry ``fact migrate`` reads, oldest first. No migration has been written yet: the
# slot below documents the one breaking change so far, and the first real migration goes here
# with its ``apply``.
MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        "1.0.0",
        "2.0.0",
        "layer contract v1 (D-019): flat filters, concept field and measure field/time_field "
        "were replaced; no model had a layer, so no automatic step was written",
    ),
)


def path(source: str | None, target: str) -> list[Migration]:
    """The registered steps from ``source`` towards ``target`` (major version changes)."""
    if source is None:
        return []
    start = int(source.split(".")[0])
    end = int(target.split(".")[0])
    return [m for m in MIGRATIONS if start <= int(m.source.split(".")[0]) < end]


@dataclass(frozen=True)
class MigrateReport:
    model_framework_version: str | None
    model_schema_version: str | None
    framework_version: str
    schema_version: str
    failing: tuple[str, ...]
    # reviewed layers whose accepted run holds no coverage (D-023): run and accept again
    reaccept: tuple[str, ...] = ()

    @property
    def compatible(self) -> bool:
        return not self.failing

    def difference(self) -> str:
        """How the model's schema version relates to the installed one."""
        model = self.model_schema_version
        if model is None:
            return "not recorded (the model was written before schemas 1.0.0)"
        if model == self.schema_version:
            return "same"
        installed = [int(part) for part in self.schema_version.split(".")]
        recorded = [int(part) for part in model.split(".")]
        if recorded > installed:
            return f"{model} is newer than the installed schemas"
        step = "major" if recorded[0] < installed[0] else "minor or patch"
        return f"{model} -> {self.schema_version} ({step})"

    def lines(self) -> list[str]:
        out = [
            f"model framework_version: {self.model_framework_version or 'unknown'}",
            f"model schema_version: {self.model_schema_version or 'not recorded'}",
            f"installed framework: {self.framework_version}",
            f"installed schemas: {self.schema_version}",
            f"schema difference: {self.difference()}",
        ]
        if self.compatible:
            out.append("compatible: every model file validates against the installed schemas")
        else:
            out.append(f"not compatible: {len(self.failing)} file(s) do not validate")
            out += [f"  {name}" for name in self.failing]
        steps = path(self.model_schema_version, self.schema_version)
        for step in steps:
            how = "automatic" if step.apply else "no automatic step"
            out.append(f"migration {step.source} -> {step.target} ({how}): {step.note}")
        if not steps:
            out.append(
                "migrations: none needed" if self.compatible else "migrations: none available"
            )
        for layer in self.reaccept:
            out.append(
                f"accept again (D-023): layer {layer} is reviewed and its accepted run holds no "
                "coverage; run fact equivalence run and fact equivalence accept"
            )
        return out


def _config(result: Any) -> dict[str, Any]:
    doc = next((f.document for f in result.model.files if f.path == CONFIG_FILE), None)
    return doc.data if doc is not None and isinstance(doc.data, dict) else {}


def report(root: Path) -> MigrateReport:
    result = inspect_model(root)
    failing = sorted({i.file for i in result.issues if i.stage in READ_STAGES})
    config = _config(result)
    versions = [config.get(key) for key in ("framework_version", "schema_version")]
    framework, schema = (str(v) if v is not None else None for v in versions)
    reaccept = tuple(
        sorted(
            layer.id
            for layer in result.model.layers.values()
            if layer.status == "reviewed" and accepted_tested(root, layer.id) is None
        )
    )
    return MigrateReport(framework, schema, __version__, SCHEMA_VERSION, tuple(failing), reaccept)
