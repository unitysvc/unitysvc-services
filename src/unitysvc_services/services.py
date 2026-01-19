"""Services command group - remote service operations."""

import typer

from . import query, unpublisher, upload

app = typer.Typer(help="Remote service operations (upload, list, deprecate, etc.)")

# Register subcommands
# upload already has subcommands, register as group
app.add_typer(upload.app, name="upload")

# query becomes 'list' under services
app.add_typer(query.app, name="list")

# unpublish becomes 'deprecate' under services
app.add_typer(unpublisher.app, name="deprecate")
