from typer.testing import CliRunner

import plumbline
from plumbline.cli import app


def test_package_imports() -> None:
    assert plumbline.__version__ == "0.0.1"


def test_cli_version() -> None:
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == f"plb {plumbline.__version__}"
