"""Console script for unitysvc_services."""

import typer

from . import format_data, populate, publisher, query, scaffold, update, validator
from . import list as list_cmd

app = typer.Typer()

# Register command groups
# Init commands are defined in scaffold.py alongside their implementation
app.add_typer(scaffold.app, name="init")
app.add_typer(list_cmd.app, name="list")
app.add_typer(query.app, name="query")
app.add_typer(publisher.app, name="publish")
app.add_typer(update.app, name="update")

# Register standalone commands at root level
app.command("format")(format_data.format_data)
app.command("validate")(validator.validate)
app.command("populate")(populate.populate)
