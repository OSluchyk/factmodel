"""The `fact` command line."""

from typing import Annotated

import typer

from factmodel import __version__

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
