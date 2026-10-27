"""``fact migrate``: which schema version a model uses, and whether this framework reads it.

A model records the framework release that created or last migrated it (``framework_version``
in ``factmodel.yaml``); the schemas carry their own version (``spec/VERSIONING.md``). The
model is compatible when every file parses and validates against the installed schemas. There
are no migrations yet: they come with the first major schema change.
"""

from dataclasses import dataclass
from pathlib import Path

from factmodel import __version__
from factmodel.model.loader import CONFIG_FILE, inspect_model
from factmodel.schemas.build import SCHEMA_VERSION

READ_STAGES = ("yaml", "schema")


@dataclass(frozen=True)
class MigrateReport:
    model_framework_version: str | None
    framework_version: str
    schema_version: str
    failing: tuple[str, ...]

    @property
    def compatible(self) -> bool:
        return not self.failing

    def lines(self) -> list[str]:
        out = [
            f"model framework_version: {self.model_framework_version or 'unknown'}",
            f"installed framework: {self.framework_version}",
            f"installed schemas: {self.schema_version}",
        ]
        if self.compatible:
            out.append("compatible: every model file validates against the installed schemas")
        else:
            out.append(f"not compatible: {len(self.failing)} file(s) do not validate")
            out += [f"  {name}" for name in self.failing]
        out.append("migrations: none needed" if self.compatible else "migrations: none available")
        return out


def report(root: Path) -> MigrateReport:
    result = inspect_model(root)
    failing = sorted({i.file for i in result.issues if i.stage in READ_STAGES})
    config = result.model.config
    version = config.framework_version if config is not None else None
    if version is None:
        doc = next((f.document for f in result.model.files if f.path == CONFIG_FILE), None)
        data = doc.data if doc is not None and isinstance(doc.data, dict) else {}
        raw = data.get("framework_version")
        version = str(raw) if raw is not None else None
    return MigrateReport(version, __version__, SCHEMA_VERSION, tuple(failing))
