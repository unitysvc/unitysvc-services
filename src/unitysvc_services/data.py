"""Data command group - local data file operations."""

import typer

from . import format_data, list as list_cmd, populate, validator
from .example import list_code_examples, run_local

app = typer.Typer(help="Local data file operations (validate, format, test, etc.)")

# Register subcommands
app.command("validate")(validator.validate)
app.command("format")(format_data.format_data)
app.command("populate")(populate.populate)
app.command("test")(run_local)

# Create combined list subgroup
list_app = typer.Typer(help="List local data files")

# Add existing list commands from list.py
list_app.command("providers")(list_cmd.list_providers)
list_app.command("sellers")(list_cmd.list_sellers)
list_app.command("offerings")(list_cmd.list_offerings)
list_app.command("listings")(list_cmd.list_listings)

# Add examples list from example.py
list_app.command("examples")(list_code_examples)

app.add_typer(list_app, name="list")
