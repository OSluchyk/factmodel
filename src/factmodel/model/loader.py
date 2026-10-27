"""Load a model repository into memory.

``inspect_model`` reads every model file, validates it against its schema, checks references
between files and returns the typed ``Model`` with every issue found. ``load_model`` does the
same and raises when there is any issue. Each issue names the gate stage it belongs to, so the
gate can run the loader once and report per stage.
"""

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator
from pydantic import ValidationError

from factmodel import vocabulary
from factmodel.io.yaml_strict import Document, YamlLoadError, load, loads
from factmodel.model import joins
from factmodel.model import types as t
from factmodel.resources import framework_text
from factmodel.schemas.build import schema_for

CONFIG_FILE = "factmodel.yaml"
# Folders whose YAML files are not model files: proposals, generated output, adapter input,
# equivalence corpora.
SKIPPED_DIRS = frozenset({"drafts", "generated", "snapshots", "corpus", "node_modules"})
REGISTER_KINDS = frozenset({"finding", "escalation", "hazard", "decision"})

HINTS = {
    "yaml": "fix the YAML at this position",
    "unknown_kind": "set kind to one of the file kinds in spec/VOCABULARY.md",
    "missing_config": "create factmodel.yaml with kind: model-config (fact init does this)",
    "schema": "make the value match schemas/<kind>.schema.json",
    "derived_key": "remove the key; derived values are computed by fact project",
    "path_name_mismatch": "set name to the last segment of path",
    "duplicate_id": "give each file of this kind its own id",
    "duplicate_evidence": "evidence IDs are unique across the model; rename one",
    "duplicate_relationship_key": "relationship keys are unique within their entity",
    "missing_entity": "add the entity or fix the ID",
    "missing_relationship": "use <entity-id>.<relationship-key> of an existing relationship",
    "missing_field": "name a field of the entity (its name, or its path when nested)",
    "missing_evidence": "add the evidence record (inline under records:, or in evidence/)",
    "unregistered_source": "register the source in sources/ (fact source add)",
    "missing_profile": "add profiles/<id>/profile.yaml or fix profile in factmodel.yaml",
    "missing_register": "add the register entry or fix the ID",
    "unknown_label": "add the label to the profile's labels",
    "anchor_class": "bind anchor_entity to the entity of class data that holds the subjects",
    "missing_dialect": "set dialect on the source to a sqlglot dialect name",
    "bad_join": (
        "write <source>.<field> = <target>.<field>, or a condition whose columns are all "
        "<entity>.<field> of the two ends (D-017)"
    ),
    "missing_anchor": "set anchor_entity to the entity that holds the profile's subjects (D-012)",
    "anchor_without_subject": "remove anchor_entity; the profile names no subject (D-015)",
    "no_subject": "remove it; the profile names no subject, so nothing is scoped (D-015)",
    "subject_facet": "remove the facet; the profile names no subject (D-015)",
}


@dataclass(frozen=True)
class LoadIssue:
    stage: str
    code: str
    file: str
    line: int
    column: int
    message: str
    hint: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line}:{self.column}: {self.message} (fix: {self.hint})"


class ModelLoadError(ValueError):
    def __init__(self, issues: Sequence[LoadIssue]) -> None:
        self.issues = list(issues)
        super().__init__("\n".join(str(issue) for issue in self.issues))


@dataclass(frozen=True)
class ModelFile:
    path: str
    kind: str
    document: Document
    obj: t.Strict | None


@dataclass(frozen=True)
class Model:
    root: Path
    config: t.ModelConfig | None
    profile: t.Profile | None
    files: tuple[ModelFile, ...]
    sources: Mapping[str, t.Source]
    entities: Mapping[str, t.Entity]
    evidence: Mapping[str, t.EvidenceRecord]
    services: Mapping[str, t.Service] = field(default_factory=dict)
    findings: Mapping[str, t.Finding] = field(default_factory=dict)
    escalations: Mapping[str, t.Escalation] = field(default_factory=dict)
    hazards: Mapping[str, t.Hazard] = field(default_factory=dict)
    decisions: Mapping[str, t.Decision] = field(default_factory=dict)
    layers: Mapping[str, t.Layer] = field(default_factory=dict)
    consumers: Mapping[str, t.Consumer] = field(default_factory=dict)
    probes: Mapping[str, t.Probe] = field(default_factory=dict)
    probe_results: tuple[t.ProbeResult, ...] = ()
    triggers: Mapping[str, t.Trigger] = field(default_factory=dict)
    tenants: t.Tenants | None = None
    allowlist: t.ReleaseAllowlist | None = None

    @property
    def relationships(self) -> dict[str, tuple[t.Entity, t.Relationship]]:
        return {
            f"{entity.id}.{rel.key}": (entity, rel)
            for entity in self.entities.values()
            for rel in entity.relationships
        }


@dataclass(frozen=True)
class LoadResult:
    model: Model
    issues: tuple[LoadIssue, ...]

    def stage(self, name: str) -> list[LoadIssue]:
        return [issue for issue in self.issues if issue.stage == name]


class _Issues:
    def __init__(self) -> None:
        self.items: list[LoadIssue] = []

    def add(
        self,
        stage: str,
        code: str,
        doc: Document | None,
        file: str,
        location: Sequence[str | int],
        message: str,
    ) -> None:
        line, column = doc.position(location) if doc else (1, 1)
        self.items.append(LoadIssue(stage, code, file, line, column, message, HINTS[code]))


def bundled_profile(profile_id: str) -> str | None:
    """Return the text of a profile shipped with the framework, if there is one."""
    return framework_text("profiles", profile_id, "profile.yaml")


def discover(root: Path) -> list[Path]:
    """Return every YAML model file under ``root``, sorted, skipping non-model folders."""
    found = []
    for path in root.rglob("*"):
        if path.suffix not in (".yaml", ".yml") or not path.is_file():
            continue
        parts = path.relative_to(root).parts[:-1]
        if any(part.startswith(".") or part in SKIPPED_DIRS for part in parts):
            continue
        found.append(path)
    return sorted(found, key=lambda p: p.relative_to(root).as_posix())


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _read(root: Path, issues: _Issues) -> list[tuple[str, Document]]:
    docs = []
    for path in discover(root):
        name = _rel(root, path)
        try:
            doc = load(path)
        except YamlLoadError as error:
            issues.items.append(
                LoadIssue("yaml", "yaml", name, error.line, error.column, error.message, error.hint)
            )
            continue
        docs.append((name, doc))
    return docs


def _check_schema(name: str, doc: Document, issues: _Issues) -> bool:
    kinds = set(vocabulary.load()["file_kind"])
    data = doc.data
    kind = data.get("kind") if isinstance(data, dict) else None
    if kind not in kinds:
        issues.add("schema", "unknown_kind", doc, name, ["kind"], f"unknown file kind {kind!r}")
        return False
    derived = set(vocabulary.load()["derived_value"])
    ok = True
    for error in Draft202012Validator(schema_for(kind)).iter_errors(data):
        location = list(error.absolute_path)
        if error.validator == "not" and location and location[-1] in derived:
            issues.add(
                "derived-not-authored",
                "derived_key",
                doc,
                name,
                location,
                f"derived key {location[-1]!r} is authored",
            )
        else:
            issues.add("schema", "schema", doc, name, location, error.message)
        ok = False
    if ok and kind == "entity":
        for i, fld in enumerate(data.get("fields", [])):
            path = fld.get("path")
            if path and path.split(".")[-1] != fld.get("name"):
                issues.add(
                    "schema",
                    "path_name_mismatch",
                    doc,
                    name,
                    ["fields", i, "name"],
                    f"field name {fld.get('name')!r} is not the last segment of {path!r}",
                )
                ok = False
    return ok


def _walk_refs(node: Any, location: list[str | int]) -> Iterator[tuple[list[str | int], str]]:
    """Yield (location, evidence ID) for every evidence reference list in ``node``."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("extensions", "records"):
                continue
            if key in ("evidence", "retirement_evidence", "retracts") and isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, str):
                        yield [*location, key, i], item
            else:
                yield from _walk_refs(value, [*location, key])
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from _walk_refs(item, [*location, i])


class _Checker:
    """Reference checks over the raw data of every file that has a known kind."""

    def __init__(self, docs: list[tuple[str, Document]], issues: _Issues) -> None:
        self.docs = docs
        self.issues = issues
        self.by_kind: dict[str, list[tuple[str, Document]]] = {}
        for name, doc in docs:
            if isinstance(doc.data, dict):
                self.by_kind.setdefault(str(doc.data.get("kind")), []).append((name, doc))
        self.entities = self._index("entity", "id")
        self.sources = self._index("source", "id")
        self.hazards = self._index("hazard", "id")
        self.decisions = self._index("decision", "id")
        for kind in ("service", "finding", "escalation", "probe", "trigger", "layer", "consumer"):
            self._index(kind, "id")
        self.fields = {
            entity_id: {f.get("path") or f.get("name") for f in doc.data.get("fields", [])}
            for entity_id, (_, doc) in self.entities.items()
        }
        self.relationships = {
            f"{entity_id}.{r.get('key')}"
            for entity_id, (_, doc) in self.entities.items()
            for r in doc.data.get("relationships", [])
        }
        self.evidence = self._evidence_index()

    def add(self, code: str, name: str, doc: Document, loc: list[str | int], msg: str) -> None:
        self.issues.add("references", code, doc, name, loc, msg)

    def _index(self, kind: str, key: str) -> dict[str, tuple[str, Document]]:
        index: dict[str, tuple[str, Document]] = {}
        # A reused register ID is a register problem, reported by the registers stage.
        stage = "registers" if kind in REGISTER_KINDS else "references"
        for name, doc in self.by_kind.get(kind, []):
            value = doc.data.get(key)
            if not isinstance(value, str):
                continue
            if value in index:
                first = index[value][0]
                message = f"{kind} {value!r} also in {first}"
                self.issues.add(stage, "duplicate_id", doc, name, [key], message)
            else:
                index[value] = (name, doc)
        return index

    def _evidence_index(self) -> dict[str, tuple[str, Document, list[str | int]]]:
        index: dict[str, tuple[str, Document, list[str | int]]] = {}
        for name, doc in self.docs:
            records = doc.data.get("records") if isinstance(doc.data, dict) else None
            for i, record in enumerate(records if isinstance(records, list) else []):
                rid = record.get("id") if isinstance(record, dict) else None
                if not isinstance(rid, str):
                    continue
                loc: list[str | int] = ["records", i, "id"]
                if rid in index:
                    first = index[rid][0]
                    self.add(
                        "duplicate_evidence", name, doc, loc, f"evidence {rid!r} also in {first}"
                    )
                else:
                    index[rid] = (name, doc, loc)
        return index

    def run(self, profile: dict[str, Any] | None) -> None:
        # Whether the profile names a subject (D-015); unknown without a profile.
        self.has_subject: bool | None = None
        if profile is not None and isinstance(profile["doc"].data, dict):
            self.has_subject = profile["doc"].data.get("subject") is not None
        for name, doc in self.docs:
            if not isinstance(doc.data, dict) or doc.data.get("kind") == "profile":
                continue
            data = doc.data
            for loc, ref in _walk_refs(data, []):
                if ref not in self.evidence:
                    self.add("missing_evidence", name, doc, loc, f"evidence {ref!r} not found")
            self._records(name, doc)
            self._sources(name, doc)
            self._registers(name, doc)
            kind = data.get("kind")
            if kind == "model-config":
                self._anchor(name, doc)
            elif kind == "source":
                self._dialect(name, doc)
            if kind == "entity":
                self._entity(name, doc)
            elif kind == "service":
                for key in ("reads", "writes"):
                    for i, ref in enumerate(data.get(key, [])):
                        self._need_entity(name, doc, [key, i], ref)
            elif kind == "tenants":
                self._tenants(name, doc)
            elif kind == "layer":
                self._layer(name, doc)
        if profile is not None:
            self._profile(profile)

    def _need_entity(self, name: str, doc: Document, loc: list[str | int], ref: Any) -> bool:
        if isinstance(ref, str) and ref not in self.entities:
            self.add("missing_entity", name, doc, loc, f"entity {ref!r} not found")
            return False
        return True

    def _need_field(
        self, name: str, doc: Document, loc: list[str | int], entity: str, addr: str
    ) -> None:
        if entity in self.fields and addr not in self.fields[entity]:
            self.add("missing_field", name, doc, loc, f"entity {entity!r} has no field {addr!r}")

    def _records(self, name: str, doc: Document) -> None:
        for i, record in enumerate(doc.data.get("records", []) or []):
            successor = record.get("superseded_by") if isinstance(record, dict) else None
            if isinstance(successor, str) and successor not in self.evidence:
                loc: list[str | int] = ["records", i, "superseded_by"]
                self.add("missing_evidence", name, doc, loc, f"evidence {successor!r} not found")

    def _sources(self, name: str, doc: Document) -> None:
        data = doc.data
        found: list[tuple[list[str | int], Any]] = []
        if data.get("kind") in ("entity", "probe-result"):
            found.append((["source"], data.get("source")))
        if isinstance(data.get("answer"), dict):
            found.append((["answer", "source"], data["answer"].get("source")))
        for i, record in enumerate(data.get("records", []) or []):
            if isinstance(record, dict):
                found.append((["records", i, "source"], record.get("source")))
        for loc, ref in found:
            if isinstance(ref, str) and ref not in self.sources:
                self.add("unregistered_source", name, doc, loc, f"source {ref!r} is not registered")

    def _registers(self, name: str, doc: Document) -> None:
        data = doc.data

        def hazards(node: Any, loc: list[str | int]) -> None:
            for i, ref in enumerate(node.get("hazards", []) if isinstance(node, dict) else []):
                if ref not in self.hazards:
                    self.add(
                        "missing_register",
                        name,
                        doc,
                        [*loc, "hazards", i],
                        f"hazard {ref!r} not found",
                    )

        hazards(data, [])
        for key in ("fields", "relationships"):
            for i, item in enumerate(data.get(key, []) or []):
                hazards(item, [key, i])
        kind = data.get("kind")
        refs: list[tuple[str, Any]] = []
        if kind == "finding":
            refs.append(("decision", data.get("decision")))
        if kind == "decision":
            refs.append(("superseded_by", data.get("superseded_by")))
        for key, ref in refs:
            if isinstance(ref, str) and ref not in self.decisions:
                self.add("missing_register", name, doc, [key], f"decision {ref!r} not found")
        for key in ("about", "applies_to"):
            for i, ref in enumerate(data.get(key, []) or []):
                if not isinstance(ref, str):
                    continue
                if "." in ref and ref not in self.relationships:
                    self.add(
                        "missing_relationship",
                        name,
                        doc,
                        [key, i],
                        f"relationship {ref!r} not found",
                    )
                elif "." not in ref:
                    self._need_entity(name, doc, [key, i], ref)

    def _entity(self, name: str, doc: Document) -> None:
        data = doc.data
        entity_id = data.get("id")
        anchor = data.get("anchor_reference")
        if isinstance(anchor, dict) and isinstance(anchor.get("field"), str):
            self._need_field(name, doc, ["anchor_reference", "field"], entity_id, anchor["field"])
        if anchor is not None and self.has_subject is False:
            message = "anchor_reference in a model whose profile names no subject"
            self.add("no_subject", name, doc, ["anchor_reference"], message)
        seen: set[str] = set()
        for i, rel in enumerate(data.get("relationships", []) or []):
            key = rel.get("key")
            if key in seen:
                self.add(
                    "duplicate_relationship_key",
                    name,
                    doc,
                    ["relationships", i, "key"],
                    f"relationship key {key!r} repeats in {entity_id!r}",
                )
            seen.add(key)
            if rel.get("scope_admission") is not None and self.has_subject is False:
                message = "scope_admission in a model whose profile names no subject"
                self.add("no_subject", name, doc, ["relationships", i, "scope_admission"], message)
            to = rel.get("to")
            targets = [to] if isinstance(to, str) else list(to or [])
            joins = rel.get("join")
            for j, target in enumerate(targets):
                loc: list[str | int] = ["relationships", i, "to"]
                if not self._need_entity(
                    name, doc, loc if isinstance(to, str) else [*loc, j], target
                ):
                    continue
                if joins is None and rel.get("status") is not None:
                    continue  # an unresolved link may omit its join; `to` is still checked
                join = joins if isinstance(joins, str) else (joins or {}).get(target)
                join_loc: list[str | int] = ["relationships", i, "join"]
                if isinstance(to, list):
                    join_loc.append(target)
                if not isinstance(join, str):
                    self.add("bad_join", name, doc, join_loc, f"no join for target {target!r}")
                    continue
                self._join(name, doc, join_loc, join, entity_id, target)
            if rel.get("discriminator"):
                self._need_field(
                    name,
                    doc,
                    ["relationships", i, "discriminator"],
                    entity_id,
                    rel["discriminator"],
                )

    def _join(
        self, name: str, doc: Document, loc: list[str | int], join: str, source: str, target: str
    ) -> None:
        try:
            parsed = joins.parse(join)
            if source == target and parsed.expression:
                joins.condition(join, source, target, "s", "t")
        except joins.JoinError as error:
            self.add("bad_join", name, doc, loc, f"join {join!r}: {error}")
            return
        used = parsed.entities
        if not used <= {source, target} or (source != target and used != {source, target}):
            self.add(
                "bad_join", name, doc, loc, f"join {join!r} must use {source!r} and {target!r}"
            )
            return
        for entity, address in dict.fromkeys(parsed.columns):
            self._need_field(name, doc, loc, entity, address)

    def _tenants(self, name: str, doc: Document) -> None:
        for i, tenant in enumerate(doc.data.get("tenants", []) or []):
            for axis in ("ingest", "presence"):
                for env, fact in (tenant.get(axis) or {}).items():
                    for j, ref in enumerate(
                        fact.get("entities", []) if isinstance(fact, dict) else []
                    ):
                        self._need_entity(name, doc, ["tenants", i, axis, env, "entities", j], ref)

    def _layer(self, name: str, doc: Document) -> None:
        data = doc.data
        for i, ref in enumerate(data.get("joins", []) or []):
            if ref not in self.relationships:
                self.add(
                    "missing_relationship",
                    name,
                    doc,
                    ["joins", i],
                    f"relationship {ref!r} not found",
                )
        for i, flt in enumerate(data.get("filters", []) or []):
            self._need_entity(name, doc, ["filters", i, "entity"], flt.get("entity"))
        for key in ("concepts", "measures"):
            for i, item in enumerate(data.get(key, []) or []):
                for fkey in ("field", "time_field"):
                    ref = item.get(fkey)
                    if isinstance(ref, str):
                        entity, _, address = ref.partition(".")
                        if self._need_entity(name, doc, [key, i, fkey], entity):
                            self._need_field(name, doc, [key, i, fkey], entity, address)

    def _anchor(self, name: str, doc: Document) -> None:
        """The model binds an anchor exactly when its profile names a subject (D-012, D-015);
        the anchor names an existing data entity, once there are entities."""
        anchor = doc.data.get("anchor_entity")
        if self.has_subject is True and anchor is None:
            message = "the profile names a subject; bind anchor_entity"
            self.add("missing_anchor", name, doc, [], message)
        elif self.has_subject is False and anchor is not None:
            message = "the profile names no subject; anchor_entity must be absent"
            self.add("anchor_without_subject", name, doc, ["anchor_entity"], message)
            return
        if not self.entities or not isinstance(anchor, str):
            return
        if anchor not in self.entities:
            self.add("missing_entity", name, doc, ["anchor_entity"], f"anchor {anchor!r} not found")
            return
        entity_class = self.entities[anchor][1].data.get("class")
        if entity_class != "data":
            message = f"anchor {anchor!r} has class {entity_class!r}; it must be data"
            self.add("anchor_class", name, doc, ["anchor_entity"], message)

    def _dialect(self, name: str, doc: Document) -> None:
        """An engine without a default dialect needs an explicit one."""
        engine = doc.data.get("engine")
        known = vocabulary.text_map("engine_dialect")
        if isinstance(engine, str) and engine not in known and not doc.data.get("dialect"):
            message = f"engine {engine!r} has no default dialect"
            self.add("missing_dialect", name, doc, ["engine"], message)

    def _profile(self, profile: dict[str, Any]) -> None:
        name, doc = profile["file"], profile["doc"]
        data = doc.data
        labels = set(data.get("labels", []))
        for i, rule in enumerate(data.get("rules", [])):
            if self.has_subject is False:
                self._subject_facets(name, doc, i, rule.get("when") or {})
            if rule.get("label") not in labels:
                self.add(
                    "unknown_label",
                    name,
                    doc,
                    ["rules", i, "label"],
                    f"label {rule.get('label')!r} is not in the profile's labels",
                )

    def _subject_facets(self, name: str, doc: Document, i: int, when: dict[str, Any]) -> None:
        """A profile without a subject cannot test subject scope (D-015)."""
        loc: list[str | int] = ["rules", i, "when"]
        for facet in ("any_end_subject_scoped", "all_ends_subject_scoped"):
            if facet in when:
                self.add("subject_facet", name, doc, [*loc, facet], f"{facet} needs a subject")
        for j, pattern in enumerate(when.get("all_ends_match") or []):
            if isinstance(pattern, dict) and "subject_scoped" in pattern:
                message = "subject_scoped needs a subject"
                self.add(
                    "subject_facet",
                    name,
                    doc,
                    [*loc, "all_ends_match", j, "subject_scoped"],
                    message,
                )


def _resolve_profile(
    config: Document | None, docs: list[tuple[str, Document]], issues: _Issues
) -> tuple[str, Document] | None:
    if config is None or not isinstance(config.data, dict):
        return None
    wanted = config.data.get("profile")
    for name, doc in docs:
        data = doc.data
        if isinstance(data, dict) and data.get("kind") == "profile" and data.get("id") == wanted:
            return name, doc
    text = bundled_profile(str(wanted))
    name = f"<profile {wanted}>"
    if text is None:
        issues.add(
            "references",
            "missing_profile",
            config,
            CONFIG_FILE,
            ["profile"],
            f"profile {wanted!r} not found",
        )
        return None
    doc = loads(text, name)
    if not _check_schema(name, doc, issues):
        return None
    return name, doc


def _typed(name: str, doc: Document, issues: _Issues) -> t.Strict | None:
    kind = doc.data["kind"]
    try:
        return t.FILE_MODELS[kind].model_validate(doc.data)
    except ValidationError as error:
        first = error.errors()[0]
        issues.add("schema", "schema", doc, name, list(first["loc"]), first["msg"])
        return None


def _by_id(files: Iterable[ModelFile], kind: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for f in files:
        if f.kind == kind and f.obj is not None:
            out.setdefault(cast(Any, f.obj).id, f.obj)
    return out


def inspect_model(root: Path) -> LoadResult:
    """Load the model under ``root`` and return it with every issue found."""
    root = root.resolve()
    issues = _Issues()
    docs = _read(root, issues)
    config_doc = next((doc for name, doc in docs if name == CONFIG_FILE), None)
    if config_doc is None and not any(i.file == CONFIG_FILE for i in issues.items):
        issues.add("schema", "missing_config", None, CONFIG_FILE, [], f"{CONFIG_FILE} not found")
    valid = {name: _check_schema(name, doc, issues) for name, doc in docs}
    profile = _resolve_profile(config_doc, docs, issues)
    checker = _Checker(docs, issues)
    checker.run({"file": profile[0], "doc": profile[1]} if profile else None)

    files = []
    for name, doc in docs:
        kind = str(doc.data.get("kind")) if isinstance(doc.data, dict) else ""
        obj = _typed(name, doc, issues) if valid[name] else None
        files.append(ModelFile(name, kind, doc, obj))
    typed_profile = None
    if profile is not None:
        local = next((f.obj for f in files if f.document is profile[1]), None)
        typed_profile = local if isinstance(local, t.Profile) else _typed(*profile, issues)
    evidence: dict[str, t.EvidenceRecord] = {}
    for f in files:
        for record in getattr(f.obj, "records", None) or []:
            evidence.setdefault(record.id, record)
    singles = {f.kind: f.obj for f in files if f.obj is not None}
    config = singles.get("model-config") if CONFIG_FILE in {f.path for f in files} else None
    model = Model(
        root=root,
        config=config if isinstance(config, t.ModelConfig) else None,
        profile=typed_profile if isinstance(typed_profile, t.Profile) else None,
        files=tuple(files),
        sources=_by_id(files, "source"),
        entities=_by_id(files, "entity"),
        evidence=evidence,
        services=_by_id(files, "service"),
        findings=_by_id(files, "finding"),
        escalations=_by_id(files, "escalation"),
        hazards=_by_id(files, "hazard"),
        decisions=_by_id(files, "decision"),
        layers=_by_id(files, "layer"),
        consumers=_by_id(files, "consumer"),
        probes=_by_id(files, "probe"),
        probe_results=tuple(f.obj for f in files if isinstance(f.obj, t.ProbeResult)),
        triggers=_by_id(files, "trigger"),
        tenants=next((f.obj for f in files if isinstance(f.obj, t.Tenants)), None),
        allowlist=next((f.obj for f in files if isinstance(f.obj, t.ReleaseAllowlist)), None),
    )
    return LoadResult(model, tuple(issues.items))


def load_model(root: Path) -> Model:
    """Load the model under ``root``; raise ModelLoadError when there is any issue."""
    result = inspect_model(root)
    if result.issues:
        raise ModelLoadError(result.issues)
    return result.model
