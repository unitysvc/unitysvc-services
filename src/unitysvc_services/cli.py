"""Console script for unitysvc_services."""

import typer

from . import format_data, populate, publisher, query, test, unpublisher, validator
from . import list as list_cmd

app = typer.Typer()

# Register command groups
app.add_typer(list_cmd.app, name="list")
app.add_typer(query.app, name="query")
app.add_typer(publisher.app, name="publish")
app.add_typer(unpublisher.app, name="unpublish")
app.add_typer(test.app, name="test")

# Register standalone commands at root level
app.command("format")(format_data.format_data)
app.command("validate")(validator.validate)
app.command("populate")(populate.populate)
