"""The `fact` command line."""

from pathlib import Path
from typing import Annotated

import typer

from factmodel import __version__, repo, vocabulary
from factmodel import status as status_module
from factmodel import sync as sync_module
from factmodel.adapters import registry
from factmodel.adapters.base import AdapterError, with_date
from factmodel.adapters.export import ExportAdapter
from factmodel.adapters.git import GitAdapter
from factmodel.core import derived
from factmodel.core.drafts import to_facts
from factmodel.gate.runner import BLOCKING_STAGES, run_gate
from factmodel.io.yaml_strict import load
from factmodel.model.loader import inspect_model
from factmodel.model.types import Snapshot, Source

app = typer.Typer(
    name="fact",
    help="Build, check and keep current an evidence-grounded model of a data platform.",
    no_args_is_help=True,
    add_completion=False,
)


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"fact {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Print the version and exit.",
            callback=_print_version,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Build, check and keep current an evidence-grounded model of a data platform."""


RootOption = Annotated[
    Path,
    typer.Option("--root", help="The model repository.", file_okay=False, exists=True),
]


@app.command()
def project(root: RootOption = Path(".")) -> None:
    """Recompute derived values (labels, scope, residue) into generated/."""
    result = inspect_model(root)
    blocking = [issue for issue in result.issues if issue.stage in BLOCKING_STAGES]
    for issue in blocking:
        typer.echo(str(issue), err=True)
    if blocking:
        typer.echo(f"{len(blocking)} issue(s); run fact check for details", err=True)
        raise typer.Exit(1)
    model = result.model
    values = derived.derive_model(model)
    if values is None:
        typer.echo("no profile or model config; see factmodel.yaml", err=True)
        raise typer.Exit(1)
    files = derived.render(values)
    changed = derived.write(model.root, files)
    for path in changed:
        typer.echo(f"wrote {path.relative_to(model.root).as_posix()}")
    if not changed:
        typer.echo("generated/ is up to date")


@app.command()
def check(
    root: RootOption = Path("."),
    stage: Annotated[str | None, typer.Option("--stage", help="Run one stage only.")] = None,
) -> None:
    """Run the gate; exit 0 only when every stage passes."""
    try:
        report = run_gate(root, stage)
    except ValueError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(2) from error
    for line in report.lines():
        typer.echo(line)
    if not report.passed:
        raise typer.Exit(1)


@app.command()
def init(
    target: Annotated[Path, typer.Argument(help="Folder for the new model repository.")],
    profile: Annotated[str, typer.Option("--profile", help="Profile ID, for example retail.")],
    model_id: Annotated[str | None, typer.Option("--id", help="Model ID (a slug).")] = None,
    anchor: Annotated[
        str | None,
        typer.Option("--anchor", help="Anchor entity ID; default: the profile's subject."),
    ] = None,
) -> None:
    """Create a model repository: config, layout, agent files, CI and generated/."""
    try:
        written = repo.init(target, profile, model_id, anchor)
    except repo.RepoError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    typer.echo(f"created {target} with {len(written)} files (profile {profile})")


source_app = typer.Typer(help="Manage the source registry.", no_args_is_help=True)
app.add_typer(source_app, name="source")


@source_app.command("add")
def source_add(
    source_id: Annotated[str, typer.Option("--id", help="Source ID (a slug).")],
    title: Annotated[str, typer.Option("--title")],
    source_kind: Annotated[str, typer.Option("--kind", help="git, warehouse, api, ...")],
    access_mode: Annotated[str, typer.Option("--access-mode")],
    engine: Annotated[str | None, typer.Option("--engine", help="Warehouse engine.")] = None,
    location: Annotated[str | None, typer.Option("--location")] = None,
    access: Annotated[str | None, typer.Option("--access", help="How access is obtained.")] = None,
    rank: Annotated[int | None, typer.Option("--rank")] = None,
    root: RootOption = Path("."),
) -> None:
    """Register a source: kind, access mode, rank. Records how to get access, never a secret."""
    fields = {
        "id": source_id,
        "title": title,
        "source_kind": source_kind,
        "access_mode": access_mode,
        "rank": rank,
        "engine": engine,
        "location": location,
        "access": access,
    }
    try:
        path = repo.add_source(root, fields)
    except repo.RepoError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    typer.echo(f"wrote {path.relative_to(root).as_posix()}")


@app.command("status")
def status_command(root: RootOption = Path(".")) -> None:
    """Open findings, open escalations, fired triggers, stale evidence, next actions."""
    for line in status_module.status(root).lines():
        typer.echo(line)


@app.command("adapters")
def adapters_command() -> None:
    """List installed adapters, the engines they read and their default dialects."""
    installed = registry.adapters()
    defaults = vocabulary.load_maps()["engine_dialect"]
    for name in sorted({*installed, *registry.BUILT_IN}):
        adapter = installed.get(name)
        if adapter is None:
            typer.echo(f"{name}  not installed")
            continue
        engines = adapter.engines()
        listed = sorted(defaults) if engines == ["*"] else engines
        dialects = ", ".join(f"{e}={adapter.default_dialect(e)}" for e in listed)
        typer.echo(f"{name}  engines: {', '.join(engines)}  default dialects: {dialects}")


def _source(root: Path, source_id: str) -> Source:
    try:
        return repo.source_of(root, source_id)
    except repo.RepoError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error


@app.command("export-sql")
def export_sql(
    source_id: Annotated[str, typer.Option("--source", help="Source ID.")],
    root: RootOption = Path("."),
) -> None:
    """Print the SQL the owner runs to export a source's metadata (agents read, people run)."""
    source = _source(root, source_id)
    typer.echo(ExportAdapter().export_sql(source))


@app.command("snapshot")
def snapshot_command(
    source_id: Annotated[str, typer.Option("--source", help="Source ID.")],
    from_export: Annotated[
        Path | None, typer.Option("--from-export", help="Folder with exported views.")
    ] = None,
    date: Annotated[str | None, typer.Option("--date", help="Date read, YYYY-MM-DD.")] = None,
    root: RootOption = Path("."),
) -> None:
    """Read a source's metadata through its adapter into sources/snapshots/; set current_pin."""
    source = _source(root, source_id)
    try:
        if from_export is not None:
            snap = ExportAdapter().read(from_export, source)
        else:
            snap = registry.get(source.adapter).snapshot(source, root.resolve())
        if date is not None:
            snap = with_date(snap, date)
        path, changed = repo.write_snapshot(root, snap)
        if snap.pin is not None:
            repo.set_current_pin(root, source.id, snap.pin)
    except (AdapterError, repo.RepoError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    rel = path.relative_to(root).as_posix()
    typer.echo(f"{'wrote' if changed else 'unchanged'} {rel} ({len(snap.objects)} objects)")


@app.command("draft")
def draft_command(
    source_id: Annotated[str, typer.Option("--source", help="Source ID.")],
    snapshot: Annotated[
        Path | None, typer.Option("--snapshot", help="Snapshot file; default: the latest.")
    ] = None,
    root: RootOption = Path("."),
) -> None:
    """Turn a snapshot into entity drafts under drafts/ (never physical/)."""
    _source(root, source_id)
    try:
        path = snapshot or repo.latest_snapshot(root, source_id)
        snap = Snapshot.model_validate(load(path).data)
        drafts = to_facts(snap)
        changed = repo.write_drafts(root, drafts)
    except (ValueError, repo.RepoError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    typer.echo(f"{len(drafts)} drafts, {len(changed)} written")


@app.command("quote")
def quote_command(
    source_id: Annotated[str, typer.Option("--source", help="A git source ID.")],
    path: Annotated[str, typer.Option("--path", help="File path in the repository.")],
    line: Annotated[int, typer.Option("--line", min=1, help="First line to quote.")],
    lines: Annotated[int, typer.Option("--lines", min=1, help="Number of lines.")] = 1,
    root: RootOption = Path("."),
) -> None:
    """Print an evidence record that quotes a text file in a git source, pinned to its version."""
    source = _source(root, source_id)
    try:
        record = GitAdapter().quote(source, root.resolve(), path, line, lines)
    except AdapterError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    typer.echo(repo.dump_yaml({"id": "ev-<name>", **record}).rstrip())


@app.command("sync")
def sync_command(
    source_id: Annotated[str, typer.Option("--source", help="Source ID.")],
    root: RootOption = Path("."),
) -> None:
    """Compare the latest snapshot with the previous one and the model; draft, open, fire."""
    _source(root, source_id)
    try:
        result = sync_module.sync(root.resolve(), source_id)
    except ValueError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    counts: dict[str, int] = {}
    for item in result.items:
        counts[item.drift_class] = counts.get(item.drift_class, 0) + 1
    summary = ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "no drift"
    typer.echo(f"{summary}; {len(result.written)} files written")
    for path in result.written:
        typer.echo(f"  {path.relative_to(root.resolve()).as_posix()}")
