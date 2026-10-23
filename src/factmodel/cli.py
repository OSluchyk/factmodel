"""The `fact` command line."""

from pathlib import Path
from typing import Annotated

import typer

from factmodel import __version__
from factmodel.core import derived
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

# Loader stages that make a model unsafe to project.
BLOCKING_STAGES = ("yaml", "schema", "derived-not-authored", "references")


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
