"""The reduced gate for a release folder (``fact check --release``).

A release is read, not computed from: yaml, schema, references and privacy run as in the full
gate, plus a ``release`` stage: VERSION and RELEASE_NOTES.md are present, no derived key leaked
into a released file, and the notes keep every section of the previous release byte for byte.
"""

from pathlib import Path

from factmodel.gate.runner import FAIL, PASS, GateContext, GateReport, StageResult, run_gate
from factmodel.gate.stages import derived_not_authored
from factmodel.model.loader import LoadIssue
from factmodel.release.build import NOTES, VERSION_FILE

RELEASE_STAGES = ("yaml", "schema", "references", "privacy")
VERSION_KEYS = ("release", "source_commit", "schema_version", "framework_version")


def _issue(file: str, code: str, message: str, hint: str) -> LoadIssue:
    return LoadIssue("release", code, file, 1, 1, message, hint)


def release_issues(root: Path, previous: Path | None = None) -> list[LoadIssue]:
    issues: list[LoadIssue] = []
    version = root / VERSION_FILE
    if not version.is_file():
        issues.append(
            _issue(VERSION_FILE, "missing", "VERSION is missing", "rebuild with fact release")
        )
    else:
        keys = {line.partition(":")[0] for line in version.read_text(encoding="utf-8").splitlines()}
        for key in VERSION_KEYS:
            if key not in keys:
                message = f"VERSION has no {key}"
                issues.append(
                    _issue(VERSION_FILE, "version_key", message, "rebuild with fact release")
                )
    notes = root / NOTES
    if not notes.is_file():
        issues.append(
            _issue(NOTES, "missing", "RELEASE_NOTES.md is missing", "rebuild with fact release")
        )
    elif previous is not None:
        before = previous / NOTES
        if before.is_file() and not notes.read_text(encoding="utf-8").startswith(
            before.read_text(encoding="utf-8").rstrip("\n")
        ):
            message = "an earlier section of RELEASE_NOTES.md changed"
            hint = "release notes are append-only; restore the earlier sections"
            issues.append(_issue(NOTES, "notes_edited", message, hint))
    leaked = derived_not_authored.run(GateContext(root)) or []
    issues += [
        LoadIssue("release", "derived_leak", i.file, i.line, i.column, i.message, i.hint)
        for i in leaked
    ]
    return issues


def check(root: Path, previous: Path | None = None) -> GateReport:
    report = run_gate(root, stages=RELEASE_STAGES)
    issues = tuple(release_issues(root, previous))
    stage = StageResult("release", FAIL if issues else PASS, issues)
    return GateReport((*report.stages, stage), report.warnings)
