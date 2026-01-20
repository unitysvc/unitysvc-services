"""Services command group - remote service operations."""

import typer

from . import query, test_runner, upload
from .lifecycle import delete_service, deprecate_service, submit_service, withdraw_service
from .query import show_service

app = typer.Typer(help="Remote service operations (upload, submit, list, show, deprecate, delete, etc.)")

# Register subcommands
# upload already has subcommands, register as group
app.add_typer(upload.app, name="upload")

# query becomes 'list' under services
app.add_typer(query.app, name="list")

# show displays details of a single service
app.command("show")(show_service)

# submit changes draft → pending (for review)
app.command("submit")(submit_service)

# withdraw returns pending/rejected → draft
app.command("withdraw")(withdraw_service)

# deprecate marks service as deprecated (status change)
app.command("deprecate")(deprecate_service)

# delete permanently removes service
app.command("delete")(delete_service)

# test commands - hyphenated for clarity (verb-noun)
app.command("list-tests")(test_runner.list_tests)
app.command("show-test")(test_runner.show_test)
app.command("run-tests")(test_runner.run_test)
app.command("skip-test")(test_runner.skip_test)
app.command("unskip-test")(test_runner.unskip_test)
