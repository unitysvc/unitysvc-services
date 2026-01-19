"""Console script for unitysvc_services."""

import typer

from . import data, services

app = typer.Typer()

# Register main command groups
app.add_typer(data.app, name="data")
app.add_typer(services.app, name="services")
