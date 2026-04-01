"""Console script for unitysvc_services."""

import importlib.metadata

import typer

from . import data, promotions, services


def version_callback(value: bool) -> None:
    if value:
        version = importlib.metadata.version("unitysvc-services")
        typer.echo(f"unitysvc-services {version}")
        raise typer.Exit()


app = typer.Typer()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None, "--version", "-V", help="Show version and exit.", callback=version_callback, is_eager=True
    ),
) -> None:
    """UnitySVC Services CLI."""


# Register main command groups
app.add_typer(data.app, name="data")
app.add_typer(services.app, name="services")
app.add_typer(promotions.app, name="promotions")
