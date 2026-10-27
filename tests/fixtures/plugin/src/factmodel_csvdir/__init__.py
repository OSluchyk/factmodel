"""Example third-party adapter: each ``*.csv`` file in a folder is a table.

Only the header row is read (never a data row): every column is a nullable text field. The
folder is ``source.location``, relative to the model root. The adapter knows one engine,
``csvdir``, whose files DuckDB can query, so probes render in the ``duckdb`` dialect.
"""

import csv
import datetime
from pathlib import Path

from factmodel.model.types import Snapshot, Source


class CsvDirAdapter:
    name = "csvdir"

    def engines(self) -> list[str]:
        return ["csvdir"]

    def default_dialect(self, engine: str) -> str:
        return "duckdb"

    def snapshot(self, source: Source, model_root: Path) -> Snapshot:
        folder = model_root / (source.location or source.id)
        objects = []
        for path in sorted(folder.glob("*.csv")):
            with path.open(newline="", encoding="utf-8") as handle:
                header = next(csv.reader(handle), [])
            fields = [
                {"name": name, "type": "TEXT", "type_class": "text", "nullable": True}
                for name in header
            ]
            objects.append({"name": path.stem, "object_type": "table", "fields": fields})
        day = datetime.date.today().isoformat()
        return Snapshot.model_validate(
            {
                "kind": "snapshot",
                "source": source.id,
                "engine": "csvdir",
                "target": folder.name,
                "taken_on": day,
                "pin": f"csvdir:{folder.name}@{day}",
                "objects": objects,
            }
        )
