"""Data command group - local data file operations."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import format_data, list as list_cmd, populate, validator
from .example import list_code_examples, run_local
from .utils import find_files_by_schema, load_data_file

app = typer.Typer(help="Local data file operations (validate, format, test, etc.)")
console = Console()

# Register subcommands
app.command("validate")(validator.validate)
app.command("format")(format_data.format_data)
app.command("populate")(populate.populate)
app.command("test")(run_local)

# Create combined list subgroup
list_app = typer.Typer(help="List local data files")


@list_app.callback(invoke_without_command=True)
def list_services(
    ctx: typer.Context,
    data_dir: Path = typer.Option(
        None,
        "--data-dir",
        "-d",
        help="Directory containing data files (default: current directory)",
    ),
):
    """List all services with their provider, offering, and listing files.

    Service name is taken from listing name, or offering name if listing name is not specified.
    """
    # Only run if no subcommand was invoked
    if ctx.invoked_subcommand is not None:
        return

    # Set data directory
    if data_dir is None:
        data_dir = Path.cwd()

    if not data_dir.is_absolute():
        data_dir = Path.cwd() / data_dir

    if not data_dir.exists():
        console.print(f"[red]Data directory not found: {data_dir}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[blue]Scanning for services in:[/blue] {data_dir}\n")

    # Find all listing files
    listing_results = find_files_by_schema(data_dir, "listing_v1")

    if not listing_results:
        console.print("[yellow]No services found.[/yellow]")
        raise typer.Exit(code=0)

    # Build service information
    services = []

    for listing_file, _format, listing_data in listing_results:
        # Get listing name
        listing_name = listing_data.get("name", "")

        # Find corresponding offering file (same directory)
        offering_results = find_files_by_schema(listing_file.parent, "offering_v1")
        offering_name = ""
        offering_file = None
        if offering_results:
            offering_file, _fmt, offering_data = offering_results[0]
            offering_name = offering_data.get("name", "")

        # Service name: listing name, or offering name if listing name not specified
        service_name = listing_name or offering_name or "unknown"

        # Find provider (parent directory of services)
        provider_name = ""
        provider_file = None
        try:
            # Structure: data/{provider}/services/{service}/listing.json
            provider_dir = listing_file.parent.parent.parent
            provider_results = find_files_by_schema(provider_dir, "provider_v1")
            if provider_results:
                provider_file, _fmt, provider_data = provider_results[0]
                provider_name = provider_data.get("name", "")
        except Exception:
            pass

        # Get service_id from override file if it exists
        service_id = listing_data.get("service_id", "")

        # Get relative paths
        try:
            listing_rel = listing_file.relative_to(data_dir)
        except ValueError:
            listing_rel = listing_file

        services.append({
            "service_name": service_name,
            "provider_name": provider_name,
            "listing_file": str(listing_rel),
            "service_id": service_id,
        })

    # Display results in table
    table = Table(title="Services")
    table.add_column("Service", style="cyan")
    table.add_column("Provider", style="blue")
    table.add_column("Service ID", style="yellow")
    table.add_column("Listing File", style="dim")

    for svc in services:
        service_id = svc["service_id"][:8] + "..." if svc["service_id"] else "-"
        table.add_row(
            svc["service_name"],
            svc["provider_name"] or "-",
            service_id,
            svc["listing_file"],
        )

    console.print(table)
    console.print(f"\n[green]Total:[/green] {len(services)} service(s)")


# Add existing list commands from list.py
list_app.command("providers")(list_cmd.list_providers)
list_app.command("sellers")(list_cmd.list_sellers)
list_app.command("offerings")(list_cmd.list_offerings)
list_app.command("listings")(list_cmd.list_listings)

# Add examples list from example.py
list_app.command("examples")(list_code_examples)

app.add_typer(list_app, name="list")
