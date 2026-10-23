"""The ``git`` adapter: DDL and text in a repository, any dialect sqlglot parses.

A git source names the repository (``location``, absolute or relative to the model root), the
files to parse (``include`` globs) and the dialect (``dialect``, or the default dialect of its
``engine``). ``revision`` is a commit, branch or tag (default ``HEAD``); ``worktree`` reads the
files as they are on disk.

``CREATE TABLE`` and ``CREATE VIEW`` statements become snapshot objects. Each object is pinned
``<source-id>@<sha>:<path>:<line>``, where the sha is the commit, or the file's blob hash for a
working-tree read (the blob hash names the same content in any later commit). Column types are
written in sqlglot's neutral spelling, so a type keeps its class whatever the dialect's writer
would do with it. The snapshot keeps the list of files read with their blob hashes under
``extensions.files``; it never stores the repository.
"""

import re
import subprocess
from pathlib import Path
from typing import Any

import sqlglot
from sqlglot import exp

from factmodel.adapters.base import AdapterError, dialect_for, enforces_foreign_keys, today
from factmodel.adapters.types import type_class
from factmodel.core.release import glob_match
from factmodel.model.types import Snapshot, Source

WORKTREE = "worktree"


def _git(repo: Path, *args: str) -> str:
    try:
        done = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
        )
    except FileNotFoundError as error:
        raise AdapterError("git is not installed") from error
    except subprocess.CalledProcessError as error:
        raise AdapterError(f"git {' '.join(args)} failed: {error.stderr.strip()}") from error
    return done.stdout


def repository(source: Source, model_root: Path) -> Path:
    if not source.location:
        raise AdapterError(f"git source {source.id!r} names no location")
    path = Path(source.location)
    return (path if path.is_absolute() else model_root / path).resolve()


class _Files:
    """The files of one revision: paths, blob hashes and text."""

    def __init__(self, repo: Path, revision: str) -> None:
        self.repo = repo
        self.revision = revision
        if revision == WORKTREE:
            self.commit: str | None = None
            listed = _git(repo, "ls-files", "--cached", "--others", "--exclude-standard")
            self.paths = sorted(p for p in listed.splitlines() if (repo / p).is_file())
        else:
            self.commit = _git(repo, "rev-parse", "--verify", f"{revision}^{{commit}}").strip()
            self.paths = sorted(
                _git(repo, "ls-tree", "-r", "--name-only", self.commit).splitlines()
            )

    def blob(self, path: str) -> str:
        if self.commit is None:
            return _git(self.repo, "hash-object", "--", path).strip()
        return _git(self.repo, "rev-parse", f"{self.commit}:{path}").strip()

    def text(self, path: str) -> str:
        if self.commit is None:
            return (self.repo / path).read_text(encoding="utf-8")
        return _git(self.repo, "show", f"{self.commit}:{path}")

    def version(self, path: str) -> str:
        return self.commit or self.blob(path)


def _name(node: exp.Expression | None) -> str:
    if isinstance(node, exp.Schema):
        node = node.this
    if isinstance(node, exp.Table):
        return node.name
    if isinstance(node, exp.Identifier):
        return str(node.this)
    raise AdapterError(f"cannot read a name from {node!r}")


def _columns(names: list[exp.Expression]) -> list[str]:
    return [n.name if isinstance(n, exp.Column) else _name(n) for n in names]


def _reference(ref: exp.Reference) -> dict[str, Any]:
    schema = ref.this
    fields = _columns(schema.expressions) if isinstance(schema, exp.Schema) else []
    return {"object": _name(schema), "fields": fields}


def _type(kind: exp.DataType | None) -> tuple[str, bool]:
    if kind is None:
        return "UNKNOWN", False
    if kind.is_type(exp.DataType.Type.ARRAY) and kind.expressions:
        element = kind.expressions[0]
        return element.sql(), True
    return kind.sql(), False


def _description(node: exp.Expr | None) -> str | None:
    """A comment or description carried by a column constraint or a table property."""
    if isinstance(node, exp.CommentColumnConstraint | exp.SchemaCommentProperty):
        return node.this.name if node.this is not None else None
    if isinstance(node, exp.Properties):
        for prop in node.expressions:
            found = _description(prop)
            if found:
                return found
    if isinstance(node, exp.Property) and node.name.lower() == "description":
        value = node.args.get("value")
        return value.name if value is not None else None
    return None


def _table_description(create: exp.Create) -> str | None:
    props = create.args.get("properties")
    return _description(props) if isinstance(props, exp.Properties) else None


def _table(create: exp.Create, enforced: bool) -> dict[str, Any]:
    schema = create.this
    name = _name(schema)
    fields: list[dict[str, Any]] = []
    constraints: list[dict[str, Any]] = []

    def add(
        kind: str, cols: list[str], cname: str | None, ref: dict[str, Any] | None = None
    ) -> None:
        item: dict[str, Any] = {
            "constraint_type": kind,
            "name": cname or f"{kind}_{name}_{'_'.join(cols)}",
            "fields": cols,
        }
        if ref is not None:
            item["references"] = ref
        item["enforced"] = enforced
        constraints.append(item)

    for node in schema.expressions:
        if isinstance(node, exp.ColumnDef):
            type_text, repeated = _type(node.args.get("kind"))
            nullable = True
            described: str | None = None
            for constraint in node.args.get("constraints", []):
                kind = constraint.args.get("kind")
                if isinstance(kind, exp.NotNullColumnConstraint) and not kind.args.get(
                    "allow_null"
                ):
                    nullable = False
                elif isinstance(kind, exp.PrimaryKeyColumnConstraint):
                    nullable = False
                    add("primary_key", [node.name], None)
                elif isinstance(kind, exp.UniqueColumnConstraint):
                    add("unique", [node.name], None)
                elif isinstance(kind, exp.Reference):
                    add("foreign_key", [node.name], None, _reference(kind))
                elif _description(kind):
                    described = _description(kind)
            field: dict[str, Any] = {
                "name": node.name,
                "type": type_text,
                "type_class": type_class(type_text),
                "nullable": nullable,
            }
            if repeated:
                field["repeated"] = True
            if described:
                field["description"] = described
            fields.append(field)
            continue
        cname = _name(node.this) if isinstance(node, exp.Constraint) and node.this else None
        inner = node.expressions if isinstance(node, exp.Constraint) else [node]
        for item in inner:
            if isinstance(item, exp.PrimaryKey):
                add("primary_key", _columns(item.expressions), cname)
            elif isinstance(item, exp.UniqueColumnConstraint) and isinstance(item.this, exp.Schema):
                add("unique", _columns(item.this.expressions), cname)
            elif isinstance(item, exp.ForeignKey):
                ref = item.args.get("reference")
                if isinstance(ref, exp.Reference):
                    add("foreign_key", _columns(item.expressions), cname, _reference(ref))
    primary = {c for k in constraints if k["constraint_type"] == "primary_key" for c in k["fields"]}
    for field in fields:
        if field["name"] in primary:
            field["nullable"] = False
    obj: dict[str, Any] = {"name": name, "object_type": "table", "fields": fields}
    if _table_description(create):
        obj["description"] = _table_description(create)
    if constraints:
        obj["constraints"] = sorted(constraints, key=lambda c: (c["constraint_type"], c["name"]))
    return obj


def _view(create: exp.Create) -> dict[str, Any]:
    query = create.expression
    names = [p.alias_or_name for p in query.selects] if isinstance(query, exp.Query) else []
    fields = [
        {"name": n, "type": "UNKNOWN", "type_class": "other", "nullable": True} for n in names if n
    ]
    return {"name": _name(create.this), "object_type": "view", "fields": fields}


def _line(text: str, name: str) -> int:
    pattern = re.compile(
        rf"create\s+(?:or\s+replace\s+)?(?:temp\w*\s+)?(?:table|view)\s+(?:if\s+not\s+exists\s+)?"
        rf"(?:[\w\"`\[\].]*\.)?[\"`\[]?{re.escape(name)}[\"`\]]?",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    return text.count("\n", 0, match.start()) + 1 if match else 1


def _apply_comment(objects: dict[str, dict[str, Any]], statement: exp.Comment) -> None:
    """``COMMENT ON TABLE|VIEW|COLUMN ... IS '...'`` sets a description."""
    text = statement.expression.name if statement.expression is not None else ""
    target = statement.this
    if not text:
        return
    if isinstance(target, exp.Column) and target.table in objects:
        for field in objects[target.table]["fields"]:
            if field["name"] == target.name and "path" not in field:
                field["description"] = text
    elif isinstance(target, exp.Table) and target.name in objects:
        objects[target.name]["description"] = text


def parse_ddl(text: str, dialect: str, enforced: bool) -> list[dict[str, Any]]:
    """Snapshot objects for every CREATE TABLE and CREATE VIEW in ``text``.

    Descriptions come from ``COMMENT ON`` statements, inline column comments and description
    properties, where the dialect has them.
    """
    objects: dict[str, dict[str, Any]] = {}
    comments = []
    for statement in sqlglot.parse(text, read=dialect):
        if isinstance(statement, exp.Comment):
            comments.append(statement)
            continue
        if not isinstance(statement, exp.Create):
            continue
        kind = str(statement.args.get("kind") or "").upper()
        if kind == "TABLE" and isinstance(statement.this, exp.Schema):
            obj = _table(statement, enforced)
        elif kind == "VIEW":
            obj = _view(statement)
        else:
            continue
        objects[obj["name"]] = obj
    for comment in comments:
        _apply_comment(objects, comment)
    return list(objects.values())


class GitAdapter:
    name = "git"

    def engines(self) -> list[str]:
        return ["*"]

    def default_dialect(self, engine: str) -> str:
        return dialect_for(engine)

    def snapshot(self, source: Source, model_root: Path) -> Snapshot:
        repo = repository(source, model_root)
        files = _Files(repo, source.revision or "HEAD")
        dialect = dialect_for(source.engine, source.dialect)
        enforced = enforces_foreign_keys(source.engine)
        patterns = source.include or ["**/*.sql"]
        objects: list[dict[str, Any]] = []
        listed = []
        for path in files.paths:
            if not any(glob_match(p, path) for p in patterns):
                continue
            text = files.text(path)
            version = files.version(path)
            listed.append({"path": path, "blob": files.blob(path)})
            for obj in parse_ddl(text, dialect, enforced):
                obj["pin"] = f"{source.id}@{version}:{path}:{_line(text, obj['name'])}"
                objects.append(obj)
        if not listed:
            raise AdapterError(f"no file in {repo} matches {patterns}")
        document: dict[str, Any] = {
            "kind": "snapshot",
            "source": source.id,
            "engine": source.engine or dialect,
            "target": source.location or source.id,
            "taken_on": today(),
        }
        if files.commit is not None:
            document["pin"] = f"{source.id}@{files.commit}"
        document["objects"] = sorted(objects, key=lambda o: o["name"])
        document["extensions"] = {"files": listed, "revision": files.revision}
        return Snapshot.model_validate(document)

    def quote(
        self, source: Source, model_root: Path, path: str, line: int, lines: int = 1
    ) -> dict[str, Any]:
        """An evidence record quoting ``lines`` lines of a text file, pinned to its version."""
        files = _Files(repository(source, model_root), source.revision or "HEAD")
        if path not in files.paths:
            raise AdapterError(f"{path} is not in {source.id} at {files.revision}")
        text = files.text(path).splitlines()[line - 1 : line - 1 + lines]
        words = " ".join(" ".join(text).split()[:40])
        return {
            "source": source.id,
            "pin": f"{source.id}@{files.version(path)}:{path}:{line}",
            "quote": words,
            "status": "inferred",
            "read_on": today(),
        }
