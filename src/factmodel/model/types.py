"""Typed models for every file kind.

The JSON Schemas in ``schemas/`` are normative; these models give typed access to files that
already passed them. ``tests/model/test_parity.py`` checks that each model accepts and rejects
the same schema fixtures as its schema. Enumerations and patterns are read from the
vocabulary and the shared schema definitions, never typed here.
"""

from functools import cache
from typing import Annotated, Any, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from factmodel import vocabulary
from factmodel.schemas.build import pattern


@cache
def _vocab(block: str) -> frozenset[str]:
    return frozenset(vocabulary.load()[block])


def _in(block: str) -> AfterValidator:
    def check(value: str) -> str:
        if value not in _vocab(block):
            raise ValueError(f"{value!r} is not in vocabulary block {block!r}")
        return value

    return AfterValidator(check)


def _matches(name: str) -> StringConstraints:
    return StringConstraints(pattern=pattern(name))


def _unique(items: list[Any]) -> list[Any]:
    seen: list[Any] = []
    for item in items:
        if item in seen:
            raise ValueError(f"duplicate item {item!r}")
        seen.append(item)
    return items


Unique = AfterValidator(_unique)

Slug = Annotated[str, _matches("slug")]
Text = Annotated[str, StringConstraints(min_length=1)]
Date = Annotated[str, _matches("date")]
FieldName = Annotated[str, _matches("field_name")]
FieldPath = Annotated[str, _matches("field_path")]
FieldAddress = Annotated[str, _matches("field_address")]
FieldRef = Annotated[str, _matches("field_ref")]
RelationshipRef = Annotated[str, _matches("relationship_ref")]
ModelRef = Annotated[str, _matches("model_ref")]
Join = Annotated[str, _matches("join")]
Pin = Annotated[str, _matches("pin")]
Quote = Annotated[str, _matches("quote")]
FindingId = Annotated[str, _matches("finding_id")]
EscalationId = Annotated[str, _matches("escalation_id")]
HazardId = Annotated[str, _matches("hazard_id")]
DecisionId = Annotated[str, _matches("decision_id")]

Slugs = Annotated[list[Slug], Unique]
EvidenceRefs = Annotated[list[Slug], Field(min_length=1), Unique]
HazardRefs = Annotated[list[HazardId], Field(min_length=1), Unique]
ModelRefs = Annotated[list[ModelRef], Field(min_length=1), Unique]
Measurement = Annotated[dict[Slug, float], Field(min_length=1)]
Extensions = dict[str, Any]


# Strings whose value must be in a vocabulary block.
AccessMode = Annotated[str, _in("access_mode")]
Cardinality = Annotated[str, _in("cardinality")]
ConstraintType = Annotated[str, _in("constraint_type")]
DataQuality = Annotated[str, _in("data_quality")]
DecisionStatus = Annotated[str, _in("decision_status")]
EntityClass = Annotated[str, _in("entity_class")]
EscalationStatus = Annotated[str, _in("escalation_status")]
EvidenceStatus = Annotated[str, _in("evidence_status")]
FileKind = Annotated[str, _in("file_kind")]
FindingStatus = Annotated[str, _in("finding_status")]
HazardStatus = Annotated[str, _in("hazard_status")]
Mechanism = Annotated[str, _in("mechanism")]
ObjectType = Annotated[str, _in("object_type")]
ProbeKind = Annotated[str, _in("probe_kind")]
ReleaseDisposition = Annotated[str, _in("release_disposition")]
ReviewStatus = Annotated[str, _in("review_status")]
ScopeBasis = Annotated[str, _in("scope_basis")]
ServiceKind = Annotated[str, _in("service_kind")]
SourceKind = Annotated[str, _in("source_kind")]
TriggerEvent = Annotated[str, _in("trigger_event")]
TypeClass = Annotated[str, _in("type_class")]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, populate_by_name=True)


# Evidence -------------------------------------------------------------------------------


class EvidenceRecord(Strict):
    id: Slug
    source: Slug
    pin: Pin
    quote: Quote | None = None
    measurement: Measurement | None = None
    status: EvidenceStatus
    read_on: Date
    probe: Slug | None = None
    environment: Slug | None = None
    data_quality: DataQuality | None = None
    named_error: Text | None = None
    superseded_by: Slug | None = None
    note: Text | None = None

    @model_validator(mode="after")
    def _rules(self) -> Self:
        if (self.quote is None) == (self.measurement is None):
            raise ValueError("an evidence record has a quote or a measurement, not both")
        if self.status == "retracted" and (self.named_error is None or self.superseded_by is None):
            raise ValueError("a retracted record needs named_error and superseded_by")
        if self.probe is not None and (self.environment is None or self.data_quality is None):
            raise ValueError("probe evidence needs environment and data_quality")
        return self


EvidenceRecords = Annotated[list[EvidenceRecord], Field(min_length=1)]


class Evidence(Strict):
    kind: Literal["evidence"]
    records: EvidenceRecords
    extensions: Extensions | None = None


# Model config and sources -----------------------------------------------------------------


class ModelConfig(Strict):
    kind: Literal["model-config"]
    id: Slug
    title: Text | None = None
    framework_version: Annotated[str, StringConstraints(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")]
    schema_version: (
        Annotated[str, StringConstraints(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")] | None
    ) = None
    profile: Slug
    anchor_entity: Slug | None = None
    adapters: Slugs | None = None
    consumers: Slugs | None = None
    environments: Slugs | None = None
    treat_synthetic_as_representative: bool | None = None
    ranks: dict[SourceKind, Annotated[int, Field(ge=0)]] | None = None
    extensions: Extensions | None = None


class Source(Strict):
    kind: Literal["source"]
    id: Slug
    title: Text
    source_kind: SourceKind
    access_mode: AccessMode
    rank: Annotated[int, Field(ge=0)] | None = None
    adapter: Slug | None = None
    engine: Slug | None = None
    dialect: Slug | None = None
    dsn_env: Annotated[str, StringConstraints(pattern=r"^[A-Z_][A-Z0-9_]*$")] | None = None
    revision: Text | None = None
    include: Annotated[list[Text], Field(min_length=1), Unique] | None = None
    location: Text | None = None
    current_pin: Pin | None = None
    access: Text | None = None
    meaning: Text | None = None
    extensions: Extensions | None = None

    @model_validator(mode="after")
    def _engine(self) -> Self:
        if self.source_kind == "warehouse" and self.engine is None:
            raise ValueError("a warehouse source needs engine")
        return self


# Entities ---------------------------------------------------------------------------------


class Keys(Strict):
    primary: Annotated[list[FieldName], Unique]
    unique: list[Annotated[list[FieldName], Field(min_length=1), Unique]] | None = None
    current_row_rule: Text | None = None


class AnchorReference(Strict):
    field: FieldAddress
    evidence: EvidenceRefs


class EntityField(Strict):
    name: FieldName
    path: FieldPath | None = None
    type: Text
    nullable: bool
    repeated: bool | None = None
    meaning: Text
    values: Annotated[list[Text | float], Field(min_length=1), Unique] | None = None
    hazards: HazardRefs | None = None
    evidence: EvidenceRefs | None = None

    @property
    def address(self) -> str:
        """The name of a top-level field, or the dotted path of a nested one."""
        return self.path or self.name


class ScopeAdmission(Strict):
    basis: ScopeBasis
    evidence: EvidenceRefs


class Relationship(Strict):
    key: Slug
    to: Slug | Annotated[list[Slug], Field(min_length=2), Unique]
    discriminator: FieldName | None = None
    # absent only on an unresolved relationship
    join: Join | Annotated[dict[Slug, Join], Field(min_length=1)] | None = None
    meaning: Text
    mechanism: Mechanism
    cardinality: Cardinality
    scope_admission: ScopeAdmission | None = None
    status: Literal["unresolved"] | None = None
    missing: Text | None = None
    hazards: HazardRefs | None = None
    evidence: EvidenceRefs | None = None

    @model_validator(mode="after")
    def _rules(self) -> Self:
        if self.join is None:
            if self.status is None:
                raise ValueError("a relationship needs a join unless it is unresolved")
        elif isinstance(self.to, str):
            if not isinstance(self.join, str):
                raise ValueError("a single target has one join")
        elif not isinstance(self.join, dict):
            raise ValueError("a target set has a join per target")
        if self.status is None and self.evidence is None:
            raise ValueError("a relationship needs evidence unless it is unresolved")
        return self

    @property
    def targets(self) -> tuple[str, ...]:
        return (self.to,) if isinstance(self.to, str) else tuple(self.to)

    @property
    def is_target_set(self) -> bool:
        return not isinstance(self.to, str)


class Entity(Strict):
    kind: Literal["entity"]
    id: Slug
    physical_name: Text
    source: Slug | None = None
    grain: Text
    class_: EntityClass = Field(alias="class")
    status: ReviewStatus
    meaning: Text | None = None
    keys: Keys
    anchor_reference: AnchorReference | None = None
    evidence: EvidenceRefs
    fields: Annotated[list[EntityField], Field(min_length=1)]
    relationships: list[Relationship] = []
    hazards: HazardRefs | None = None
    records: EvidenceRecords | None = None
    extensions: Extensions | None = None


class Service(Strict):
    kind: Literal["service"]
    id: Slug
    service_kind: ServiceKind
    meaning: Text
    reads: Slugs | None = None
    writes: Slugs | None = None
    schedule: Text | None = None
    status: ReviewStatus | None = None
    hazards: HazardRefs | None = None
    evidence: EvidenceRefs
    records: EvidenceRecords | None = None
    extensions: Extensions | None = None


class EnvironmentFact(Strict):
    entities: Slugs
    evidence: EvidenceRefs


class Tenant(Strict):
    id: Slug
    meaning: Text | None = None
    ingest: dict[Slug, EnvironmentFact] | None = None
    presence: dict[Slug, EnvironmentFact] | None = None


class Tenants(Strict):
    kind: Literal["tenants"]
    environments: Annotated[list[Slug], Field(min_length=1), Unique]
    tenants: Annotated[list[Tenant], Field(min_length=1)]
    records: EvidenceRecords | None = None
    extensions: Extensions | None = None


# Registers --------------------------------------------------------------------------------


class Finding(Strict):
    kind: Literal["finding"]
    id: FindingId
    title: Text
    status: FindingStatus
    opened_on: Date
    closed_on: Date | None = None
    about: ModelRefs | None = None
    description: Text
    resolution: Text | None = None
    decision: DecisionId | None = None
    evidence: EvidenceRefs | None = None
    records: EvidenceRecords | None = None
    extensions: Extensions | None = None

    @model_validator(mode="after")
    def _closing(self) -> Self:
        if self.status == "resolved" and None in (self.resolution, self.evidence, self.closed_on):
            raise ValueError("a resolved finding needs resolution, evidence and closed_on")
        if self.status == "wont_fix" and None in (self.decision, self.closed_on):
            raise ValueError("a wont_fix finding needs decision and closed_on")
        return self


class Answer(Strict):
    text: Text
    source: Slug
    answered_on: Date
    evidence: EvidenceRefs


class Escalation(Strict):
    kind: Literal["escalation"]
    id: EscalationId
    question: Text
    asked_to: Slugs | None = None
    status: EscalationStatus
    asked_on: Date
    about: ModelRefs | None = None
    answer: Answer | None = None
    withdrawn_reason: Text | None = None
    records: EvidenceRecords | None = None
    extensions: Extensions | None = None

    @model_validator(mode="after")
    def _closing(self) -> Self:
        if self.status == "answered" and self.answer is None:
            raise ValueError("an answered escalation needs an answer")
        if self.status == "withdrawn" and self.withdrawn_reason is None:
            raise ValueError("a withdrawn escalation needs withdrawn_reason")
        return self


class Hazard(Strict):
    kind: Literal["hazard"]
    id: HazardId
    title: Text
    status: HazardStatus
    description: Text
    applies_to: ModelRefs
    evidence: EvidenceRefs
    retired_on: Date | None = None
    retirement_evidence: EvidenceRefs | None = None
    records: EvidenceRecords | None = None
    extensions: Extensions | None = None

    @model_validator(mode="after")
    def _closing(self) -> Self:
        if self.status == "retired" and None in (self.retired_on, self.retirement_evidence):
            raise ValueError("a retired hazard needs retired_on and retirement_evidence")
        return self


class Decision(Strict):
    kind: Literal["decision"]
    id: DecisionId
    title: Text
    status: DecisionStatus
    date: Date
    context: Text
    decision: Text
    consequences: Text | None = None
    superseded_by: DecisionId | None = None
    retracts: EvidenceRefs | None = None
    about: ModelRefs | None = None
    evidence: EvidenceRefs | None = None
    records: EvidenceRecords | None = None
    extensions: Extensions | None = None

    @model_validator(mode="after")
    def _closing(self) -> Self:
        if self.status == "superseded" and self.superseded_by is None:
            raise ValueError("a superseded decision needs superseded_by")
        return self


# Profile ----------------------------------------------------------------------------------


class EndPattern(Strict):
    class_: EntityClass | None = Field(default=None, alias="class")
    subject_scoped: bool | None = None

    @model_validator(mode="after")
    def _not_empty(self) -> Self:
        if self.class_ is None and self.subject_scoped is None:
            raise ValueError("an end pattern needs at least one key")
        return self


class Facets(Strict):
    evidence_status: EvidenceStatus | None = None
    mechanism: Mechanism | None = None
    cardinality: Cardinality | None = None
    any_end_class: EntityClass | None = None
    all_ends_class: EntityClass | None = None
    any_end_subject_scoped: bool | None = None
    all_ends_subject_scoped: bool | None = None
    all_ends_match: Annotated[list[EndPattern], Field(min_length=1)] | None = None

    @model_validator(mode="after")
    def _not_empty(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("a rule needs at least one facet")
        return self


class Rule(Strict):
    when: Facets
    label: Slug
    note: Text | None = None


def _no_withheld(labels: list[str]) -> list[str]:
    if "withheld" in labels:
        raise ValueError("withheld is reserved by the core")
    return labels


class Profile(Strict):
    kind: Literal["profile"]
    id: Slug
    meaning: Text | None = None
    subject: Text | None = None
    labels: Annotated[list[Slug], Field(min_length=1), Unique, AfterValidator(_no_withheld)]
    vocabularies: dict[Slug, Annotated[list[Slug], Field(min_length=1), Unique]] | None = None
    rules: Annotated[list[Rule], Field(min_length=1)]
    extensions: Extensions | None = None


# Layers, consumers, release ---------------------------------------------------------------


class LayerFilter(Strict):
    entity: Slug
    rule: Text
    reason: Text | None = None


class Concept(Strict):
    id: Slug
    meaning: Text
    field: FieldRef
    values: Annotated[list[Text], Unique] | None = None


class Measure(Strict):
    id: Slug
    meaning: Text
    aggregation: Slug
    field: FieldRef
    time_field: FieldRef | None = None


class Layer(Strict):
    kind: Literal["layer"]
    id: Slug
    purpose: Text
    consumer: Slug
    status: ReviewStatus
    joins: Annotated[list[RelationshipRef], Unique] | None = None
    filters: list[LayerFilter] | None = None
    concepts: list[Concept] | None = None
    measures: list[Measure] | None = None
    hazards: HazardRefs | None = None
    evidence: EvidenceRefs | None = None
    records: EvidenceRecords | None = None
    extensions: Extensions | None = None


class Corpus(Strict):
    location: Text
    pin: Pin | None = None
    synthetic: bool | None = None


class Consumer(Strict):
    kind: Literal["consumer"]
    id: Slug
    meaning: Text
    layers: Annotated[list[Slug], Field(min_length=1), Unique]
    corpus: Corpus | None = None
    threshold: Annotated[float, Field(ge=0, le=1)] | None = None
    extensions: Extensions | None = None


class FileRule(Strict):
    pattern: Text
    disposition: ReleaseDisposition
    reason: Text | None = None


class KeyList(Strict):
    keep: Annotated[list[Text], Field(min_length=1), Unique]
    drop: Annotated[list[Text], Unique] | None = None


class ReleaseAllowlist(Strict):
    kind: Literal["release-allowlist"]
    files: Annotated[list[FileRule], Field(min_length=1)]
    keys: dict[FileKind, KeyList] | None = None
    extensions: Extensions | None = None


# Probes and triggers ----------------------------------------------------------------------


class Range(Strict):
    min: float | None = None
    max: float | None = None

    @model_validator(mode="after")
    def _not_empty(self) -> Self:
        if self.min is None and self.max is None:
            raise ValueError("a range needs min or max")
        return self


class Probe(Strict):
    kind: Literal["probe"]
    id: Slug
    probe_kind: ProbeKind
    entity: Slug | None = None
    fact: Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}(\.[^\s]+)?$")]
    expected: Annotated[dict[Slug, Range], Field(min_length=1)] | None = None
    dialect: Slug
    sql: Text
    volatile: bool | None = None
    unsupported_on_dialect: Slugs | None = None
    note: Text | None = None
    extensions: Extensions | None = None


class ProbeResult(Strict):
    kind: Literal["probe-result"]
    probe: Slug
    source: Slug
    pin: Pin
    environment: Slug
    data_quality: DataQuality
    ran_on: Date
    measurement: Measurement | None = None
    error: Text | None = None
    extensions: Extensions | None = None

    @model_validator(mode="after")
    def _one_outcome(self) -> Self:
        if (self.measurement is None) == (self.error is None):
            raise ValueError("a probe result has a measurement or an error, not both")
        return self


class Firing(Strict):
    on: Date
    detail: Text | None = None
    follow_up_ref: Text | None = None


class Trigger(Strict):
    kind: Literal["trigger"]
    id: Slug
    event: TriggerEvent
    meaning: Text | None = None
    follow_up: Text
    fired: list[Firing] | None = None
    extensions: Extensions | None = None


# Snapshot ---------------------------------------------------------------------------------


class SnapshotField(Strict):
    name: FieldName
    path: FieldPath | None = None
    type: Text
    type_class: TypeClass | None = None
    nullable: bool
    repeated: bool | None = None
    description: Text | None = None


class ConstraintReference(Strict):
    object: Text
    fields: Annotated[list[FieldName], Field(min_length=1)]


class Constraint(Strict):
    constraint_type: ConstraintType
    name: Text | None = None
    fields: Annotated[list[FieldName], Field(min_length=1)]
    references: ConstraintReference | None = None
    enforced: bool

    @model_validator(mode="after")
    def _references(self) -> Self:
        if self.constraint_type == "foreign_key" and self.references is None:
            raise ValueError("a foreign key needs references")
        return self


class Partitioning(Strict):
    field: FieldName
    granularity: Text | None = None


class SnapshotObject(Strict):
    name: Text
    object_type: ObjectType
    pin: Pin | None = None
    description: Text | None = None
    fields: list[SnapshotField]
    constraints: list[Constraint] | None = None
    partitioning: Partitioning | None = None
    clustering: Annotated[list[FieldName], Unique] | None = None
    options: dict[str, str | float | bool | None] | None = None


class Snapshot(Strict):
    kind: Literal["snapshot"]
    source: Slug | None = None
    engine: Slug
    target: Text
    taken_on: Date
    pin: Pin | None = None
    objects: list[SnapshotObject]
    extensions: Extensions | None = None


FILE_MODELS: dict[str, type[Strict]] = {
    "model-config": ModelConfig,
    "source": Source,
    "entity": Entity,
    "service": Service,
    "tenants": Tenants,
    "evidence": Evidence,
    "finding": Finding,
    "escalation": Escalation,
    "hazard": Hazard,
    "decision": Decision,
    "profile": Profile,
    "layer": Layer,
    "consumer": Consumer,
    "release-allowlist": ReleaseAllowlist,
    "probe": Probe,
    "probe-result": ProbeResult,
    "trigger": Trigger,
    "snapshot": Snapshot,
}
