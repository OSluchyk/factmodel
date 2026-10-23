"""Map an engine's type text to a neutral type class (D-013).

The mapping works on type names, not engine names, so one table serves every adapter. An
adapter may map a type itself first (for example an engine-specific array notation); anything
unknown is ``other``.
"""

import re

_CLASSES: dict[str, tuple[str, ...]] = {
    "integer": (
        "INT",
        "INTEGER",
        "INT2",
        "INT4",
        "INT8",
        "INT64",
        "SMALLINT",
        "BIGINT",
        "TINYINT",
        "MEDIUMINT",
        "SERIAL",
        "BIGSERIAL",
        "SMALLSERIAL",
        "BYTEINT",
    ),
    "decimal": ("NUMERIC", "DECIMAL", "BIGNUMERIC", "BIGDECIMAL", "NUMBER", "MONEY", "SMALLMONEY"),
    "float": ("FLOAT", "FLOAT4", "FLOAT8", "FLOAT64", "REAL", "DOUBLE"),
    "boolean": ("BOOL", "BOOLEAN", "BIT"),
    "text": (
        "STRING",
        "TEXT",
        "VARCHAR",
        "CHAR",
        "CHARACTER",
        "NVARCHAR",
        "NCHAR",
        "CLOB",
        "NCLOB",
        "NTEXT",
        "CITEXT",
        "VARCHAR2",
        "NVARCHAR2",
        "TINYTEXT",
        "MEDIUMTEXT",
        "LONGTEXT",
    ),
    "date": ("DATE",),
    "time": ("TIME", "TIMETZ"),
    "timestamp": (
        "TIMESTAMP",
        "TIMESTAMPTZ",
        "TIMESTAMP_NTZ",
        "TIMESTAMP_LTZ",
        "TIMESTAMP_TZ",
        "DATETIME",
        "DATETIME2",
        "DATETIMEOFFSET",
        "SMALLDATETIME",
    ),
    "interval": ("INTERVAL",),
    "binary": ("BYTES", "BYTEA", "BLOB", "BINARY", "VARBINARY", "IMAGE", "LONGBLOB", "RAW"),
    "json": ("JSON", "JSONB", "VARIANT", "OBJECT", "SUPER"),
    "geography": ("GEOGRAPHY", "GEOMETRY", "POINT", "POLYGON"),
    "struct": ("STRUCT", "RECORD", "ROW"),
    "array": ("ARRAY",),
}
_BY_NAME = {name: cls for cls, names in _CLASSES.items() for name in names}


def type_class(type_text: str) -> str:
    """The neutral class of an engine type, from its text."""
    text = type_text.strip().upper()
    if text.endswith("[]") or text.startswith("ARRAY<"):
        return "array"
    if text.startswith("STRUCT<") or text.startswith("ROW("):
        return "struct"
    base = re.split(r"[\s(<]", text, maxsplit=1)[0]
    return _BY_NAME.get(base, "other")
