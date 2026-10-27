"""``fact migrate``: which schema version a model uses, and whether this framework reads it.

A model records the framework release that created or last migrated it (``framework_version``)
and, since 1.0.0, the schema version its files were checked against (``schema_version``); the
installed schemas carry their own version (``spec/VERSIONING.md``). The model is compatible
when every file parses and validates against the installed schemas, whatever the versions say.
There are no migrations yet: they come with the first major schema change.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from factmodel import __version__
from factmodel.model.loader import CONFIG_FILE, inspect_model
from factmodel.schemas.build import SCHEMA_VERSION

READ_STAGES = ("yaml", "schema")


@dataclass(frozen=True)
class MigrateReport:
    model_framework_version: str | None
    model_schema_version: str | None
    framework_version: str
    schema_version: str
    failing: tuple[str, ...]

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
        out.append("migrations: none needed" if self.compatible else "migrations: none available")
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
    return MigrateReport(framework, schema, __version__, SCHEMA_VERSION, tuple(failing))
