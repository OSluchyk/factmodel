"""Render the JSON Schemas from templates plus the vocabulary.

Templates live in ``templates/`` as YAML. Three placeholders keep every enumeration tied
to ``spec/VOCABULARY.md``:

- ``{$vocab: <block>}`` becomes ``{enum: [...]}`` with the block's values.
- ``{$const: "<block>:<value>"}`` becomes ``{const: <value>}``; the value must be in the block.
- ``$forbid: <block>`` inside an object schema adds a property that never validates for
  every value of the block, so those keys are rejected by name at their own path.

``$ref: "#/$defs/<name>"`` may point to a definition in ``templates/_common.yaml``; the
renderer copies every common definition a schema uses into its own ``$defs``, so each
rendered schema is self-contained.

Run ``python -m factmodel.schemas.build [out_dir]`` to write the schemas (default
``schemas/``), or ``--check`` to fail when the committed files differ from a fresh render.
"""

import copy
import json
import sys
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any

from factmodel import vocabulary
from factmodel.io.yaml_strict import loads

DIALECT = "https://json-schema.org/draft/2020-12/schema"
SCHEMA_VERSION = "2.2.0"
COMMON = "_common"
REF_PREFIX = "#/$defs/"
# A key that must not appear. ``not: {}`` instead of ``false`` so validators report the
# error at the key's own path.
FORBIDDEN = {"description": "Derived value; computed by fact project, never authored.", "not": {}}


class SchemaBuildError(ValueError):
    """A template is malformed or names a vocabulary value that does not exist."""


def _templates() -> dict[str, dict[str, Any]]:
    folder = resources.files("factmodel.schemas").joinpath("templates")
    out: dict[str, dict[str, Any]] = {}
    for entry in sorted(folder.iterdir(), key=lambda item: item.name):
        if entry.name.endswith(".yaml"):
            name = entry.name.removesuffix(".yaml")
            data = loads(entry.read_text(encoding="utf-8"), entry.name).data
            if not isinstance(data, dict):
                raise SchemaBuildError(f"{entry.name}: a template must be a mapping")
            out[name] = data
    return out


def _expand(node: Any, vocab: dict[str, tuple[str, ...]], where: str) -> Any:
    if isinstance(node, list):
        return [_expand(item, vocab, where) for item in node]
    if not isinstance(node, dict):
        return node
    if "$vocab" in node:
        block = node["$vocab"]
        if block not in vocab:
            raise SchemaBuildError(f"{where}: unknown vocabulary block {block!r}")
        rest = {k: _expand(v, vocab, where) for k, v in node.items() if k != "$vocab"}
        return {"enum": list(vocab[block]), **rest}
    if "$const" in node:
        block, _, value = str(node["$const"]).partition(":")
        if value not in vocab.get(block, ()):
            raise SchemaBuildError(f"{where}: {value!r} is not in vocabulary block {block!r}")
        rest = {k: _expand(v, vocab, where) for k, v in node.items() if k != "$const"}
        return {"const": value, **rest}
    out = {k: _expand(v, vocab, where) for k, v in node.items() if k != "$forbid"}
    if "$forbid" in node:
        block = node["$forbid"]
        if block not in vocab:
            raise SchemaBuildError(f"{where}: unknown vocabulary block {block!r}")
        properties = dict(out.get("properties", {}))
        for value in vocab[block]:
            if value in properties:
                raise SchemaBuildError(f"{where}: forbidden key {value!r} is also allowed")
            properties[value] = dict(FORBIDDEN)
        out["properties"] = properties
    return out


def _refs(node: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith(REF_PREFIX):
            found.add(ref.removeprefix(REF_PREFIX))
        for value in node.values():
            found |= _refs(value)
    elif isinstance(node, list):
        for value in node:
            found |= _refs(value)
    return found


def _render(name: str, template: dict[str, Any], common: dict[str, Any]) -> dict[str, Any]:
    body = copy.deepcopy(template)
    local_defs: dict[str, Any] = body.pop("$defs", {})
    defs: dict[str, Any] = dict(local_defs)
    pending = _refs(body) | _refs(local_defs)
    while pending:
        ref = pending.pop()
        if ref in defs:
            continue
        if ref not in common:
            raise SchemaBuildError(f"{name}: $ref to unknown definition {ref!r}")
        defs[ref] = common[ref]
        pending |= _refs(common[ref]) - defs.keys()
    schema: dict[str, Any] = {
        "$schema": DIALECT,
        "$id": f"urn:factmodel:schema:{name}:{SCHEMA_VERSION}",
    }
    schema.update(body)
    if defs:
        schema["$defs"] = {key: defs[key] for key in sorted(defs)}
    return schema


@cache
def common_definitions() -> dict[str, Any]:
    """Return the shared definitions of ``_common.yaml`` with placeholders rendered."""
    common_template = _templates().get(COMMON, {})
    defs: dict[str, Any] = _expand(
        common_template.get("$defs", {}), vocabulary.load(), f"{COMMON}.yaml"
    )
    return defs


def pattern(name: str) -> str:
    """Return the regex of a shared string definition, for code that checks the same rule."""
    value = common_definitions()[name]["pattern"]
    assert isinstance(value, str)
    return value


@cache
def render_all() -> dict[str, dict[str, Any]]:
    """Return every schema, keyed by name (the file kind, or ``snapshot``)."""
    vocab = vocabulary.load()
    raw = _templates()
    raw.pop(COMMON, None)
    common = common_definitions()
    schemas = {
        name: _render(name, _expand(t, vocab, f"{name}.yaml"), common) for name, t in raw.items()
    }
    missing = set(vocab["file_kind"]) - schemas.keys()
    if missing:
        raise SchemaBuildError(f"no template for file kinds: {sorted(missing)}")
    return schemas


def schema_for(name: str) -> dict[str, Any]:
    """Return the rendered schema for one file kind (or ``snapshot``)."""
    schemas = render_all()
    if name not in schemas:
        raise KeyError(f"no schema for {name!r}")
    return schemas[name]


def dump(schema: dict[str, Any]) -> str:
    """Serialize a schema the way it is committed."""
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def file_name(name: str) -> str:
    return f"{name}.schema.json"


def stale_files(out_dir: Path) -> list[str]:
    """Return the schema files in ``out_dir`` that are missing, changed or unexpected."""
    schemas = render_all()
    stale = [
        file_name(name)
        for name, schema in schemas.items()
        if not (out_dir / file_name(name)).is_file()
        or (out_dir / file_name(name)).read_text(encoding="utf-8") != dump(schema)
    ]
    expected = {file_name(name) for name in schemas}
    stale += sorted(p.name for p in out_dir.glob("*.schema.json") if p.name not in expected)
    return sorted(stale)


def write(out_dir: Path) -> list[Path]:
    """Write every schema to ``out_dir`` and remove schema files no template produces."""
    out_dir.mkdir(parents=True, exist_ok=True)
    schemas = render_all()
    written = []
    for name, schema in schemas.items():
        path = out_dir / file_name(name)
        path.write_text(dump(schema), encoding="utf-8")
        written.append(path)
    expected = {file_name(name) for name in schemas}
    for path in out_dir.glob("*.schema.json"):
        if path.name not in expected:
            path.unlink()
    return written


def main(argv: list[str]) -> int:
    check = "--check" in argv
    args = [a for a in argv if a != "--check"]
    out_dir = Path(args[0]) if args else Path("schemas")
    if check:
        stale = stale_files(out_dir)
        for name in stale:
            print(f"stale: {out_dir / name}")
        return 1 if stale else 0
    for path in write(out_dir):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
