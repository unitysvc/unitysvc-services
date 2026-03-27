"""Console script for unitysvc_services."""

import importlib.metadata
from typing import Optional

import typer

from . import data, services


def version_callback(value: bool) -> None:
    if value:
        version = importlib.metadata.version("unitysvc-services")
        typer.echo(f"unitysvc-services {version}")
        raise typer.Exit()


app = typer.Typer()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(  # noqa: UP007
        None, "--version", "-V", help="Show version and exit.", callback=version_callback, is_eager=True
    ),
) -> None:
    """UnitySVC Services CLI."""


# Register main command groups
app.add_typer(data.app, name="data")
app.add_typer(services.app, name="services")
