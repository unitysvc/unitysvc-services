"""Console script for unitysvc_services."""

import typer

from . import example, format_data, populate, query, unpublisher, upload, validator
from . import list as list_cmd

app = typer.Typer()

# Register command groups
app.add_typer(list_cmd.app, name="list")
app.add_typer(query.app, name="query")
app.add_typer(upload.app, name="upload")
app.add_typer(unpublisher.app, name="unpublish")
app.add_typer(example.app, name="example")

# Register standalone commands at root level
app.command("format")(format_data.format_data)
app.command("validate")(validator.validate)
app.command("populate")(populate.populate)
