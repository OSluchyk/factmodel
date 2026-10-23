"""Run the gate: every stage from gate.yaml, one verdict line per stage, one exit code."""

import importlib
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from functools import cached_property
from importlib import resources
from pathlib import Path

from factmodel.core.derived import Derived, derive, render
from factmodel.io.yaml_strict import Document, loads
from factmodel.model.loader import LoadIssue, LoadResult, Model, inspect_model
from factmodel.model.types import Entity

# Loader stages after which the model is not safe to compute from.
BLOCKING_STAGES = ("yaml", "schema", "derived-not-authored", "references")

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"


@dataclass(frozen=True)
class StageSpec:
    name: str
    module: str
    enabled: bool


@dataclass(frozen=True)
class StageResult:
    name: str
    verdict: str
    issues: tuple[LoadIssue, ...]


@dataclass(frozen=True)
class GateReport:
    stages: tuple[StageResult, ...]

    @property
    def passed(self) -> bool:
        return all(stage.verdict == PASS for stage in self.stages)

    @property
    def failed(self) -> list[str]:
        return [stage.name for stage in self.stages if stage.verdict == FAIL]

    def lines(self) -> Iterator[str]:
        for stage in self.stages:
            count = f" ({len(stage.issues)})" if stage.issues else ""
            note = " (blocked by an earlier stage)" if stage.verdict == SKIP else ""
            yield f"{stage.verdict}  {stage.name}{count}{note}"
            for issue in stage.issues:
                yield f"      {issue}"
        yield "gate: pass" if self.passed else "gate: fail"


class GateContext:
    """What every stage reads: the loader result, and derived values when they are safe."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.result: LoadResult = inspect_model(self.root)

    @property
    def model(self) -> Model:
        return self.result.model

    @cached_property
    def blocked(self) -> bool:
        return any(issue.stage in BLOCKING_STAGES for issue in self.result.issues)

    @cached_property
    def derived(self) -> Derived | None:
        model = self.result.model
        if self.blocked or model.profile is None:
            return None
        return derive(model.entities, model.evidence, model.profile)

    @cached_property
    def generated(self) -> dict[str, str] | None:
        return render(self.derived) if self.derived is not None else None

    @cached_property
    def entity_files(self) -> dict[str, str]:
        """Entity ID to the path of its file, for entities that loaded."""
        return {f.obj.id: f.path for f in self.result.model.files if isinstance(f.obj, Entity)}

    def documents(self) -> Iterator[tuple[str, Document]]:
        for f in self.result.model.files:
            yield f.path, f.document

    def issue(
        self,
        stage: str,
        code: str,
        file: str,
        location: list[str | int],
        message: str,
        hint: str,
    ) -> LoadIssue:
        doc = next((d for name, d in self.documents() if name == file), None)
        line, column = doc.position(location) if doc else (1, 1)
        return LoadIssue(stage, code, file, line, column, message, hint)


def stage_specs() -> list[StageSpec]:
    text = resources.files("factmodel.gate").joinpath("gate.yaml").read_text(encoding="utf-8")
    data = loads(text, "gate.yaml").data
    return [StageSpec(s["name"], s["module"], bool(s["enabled"])) for s in data["stages"]]


def _runner(spec: StageSpec) -> Callable[[GateContext], list[LoadIssue] | None]:
    module = importlib.import_module(spec.module)
    run: Callable[[GateContext], list[LoadIssue] | None] = module.run
    return run


def run_gate(root: Path, only: str | None = None) -> GateReport:
    """Run every enabled stage, or only the named one."""
    specs = [s for s in stage_specs() if s.enabled]
    if only is not None:
        specs = [s for s in specs if s.name == only]
        if not specs:
            raise ValueError(f"unknown or disabled stage {only!r}")
    ctx = GateContext(root)
    results = []
    for spec in specs:
        issues = _runner(spec)(ctx)
        if issues is None:
            results.append(StageResult(spec.name, SKIP, ()))
        else:
            ordered = tuple(sorted(issues, key=lambda i: (i.file, i.line, i.column, i.message)))
            results.append(StageResult(spec.name, FAIL if ordered else PASS, ordered))
    return GateReport(tuple(results))
