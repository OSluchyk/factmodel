"""The `fact` command line."""

from pathlib import Path
from typing import Annotated

import typer

from factmodel import __version__, repo
from factmodel import status as status_module
from factmodel.core import derived
from factmodel.gate.runner import BLOCKING_STAGES, run_gate
from factmodel.model.loader import inspect_model

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
    if model.profile is None:
        typer.echo("no profile; set profile in factmodel.yaml", err=True)
        raise typer.Exit(1)
    files = derived.render(derived.derive(model.entities, model.evidence, model.profile))
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
) -> None:
    """Create a model repository: config, layout, agent files, CI and generated/."""
    try:
        written = repo.init(target, profile, model_id)
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
