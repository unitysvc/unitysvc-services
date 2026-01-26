"""Data command group - local data file operations."""

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from . import example, format_data, populate, validator
from . import list as list_cmd
from .utils import find_files_by_schema, resolve_service_name_for_listing

app = typer.Typer(help="Local data file operations (validate, format, test, etc.)")
console = Console()


# Show command group
show_app = typer.Typer(help="Show details of local data objects")


@show_app.command("provider")
def show_provider(
    name: str = typer.Argument(..., help="Provider name to show"),
    data_dir: Path | None = typer.Option(
        None,
        "--data-dir",
        "-d",
        help="Directory containing data files (default: current directory)",
    ),
    output_format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: json, table, tsv, csv",
    ),
):
    """Show details of a provider by name."""
    if data_dir is None:
        data_dir = Path.cwd()

    if not data_dir.is_absolute():
        data_dir = Path.cwd() / data_dir

    # Find all provider files
    provider_results = find_files_by_schema(data_dir, "provider_v1")

    for provider_file, _fmt, provider_data in provider_results:
        if provider_data.get("name") == name:
            _display_data(provider_data, provider_file, output_format)
            return

    console.print(f"[red]Provider not found: {name}[/red]")
    raise typer.Exit(code=1)


@show_app.command("offering")
def show_offering(
    name: str = typer.Argument(..., help="Offering name to show"),
    data_dir: Path | None = typer.Option(
        None,
        "--data-dir",
        "-d",
        help="Directory containing data files (default: current directory)",
    ),
    output_format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: json, table, tsv, csv",
    ),
):
    """Show details of an offering by name."""
    if data_dir is None:
        data_dir = Path.cwd()

    if not data_dir.is_absolute():
        data_dir = Path.cwd() / data_dir

    # Find all offering files
    offering_results = find_files_by_schema(data_dir, "offering_v1")

    for offering_file, _fmt, offering_data in offering_results:
        if offering_data.get("name") == name:
            _display_data(offering_data, offering_file, output_format)
            return

    console.print(f"[red]Offering not found: {name}[/red]")
    raise typer.Exit(code=1)


@show_app.command("listing")
def show_listing(
    name: str = typer.Argument(..., help="Listing name to show"),
    data_dir: Path | None = typer.Option(
        None,
        "--data-dir",
        "-d",
        help="Directory containing data files (default: current directory)",
    ),
    output_format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: json, table, tsv, csv",
    ),
):
    """Show details of a listing by name."""
    if data_dir is None:
        data_dir = Path.cwd()

    if not data_dir.is_absolute():
        data_dir = Path.cwd() / data_dir

    # Find all listing files
    listing_results = find_files_by_schema(data_dir, "listing_v1")

    for listing_file, _fmt, listing_data in listing_results:
        # Get listing name, fall back to offering name if not specified
        listing_name = listing_data.get("name", "")
        if not listing_name:
            listing_name = resolve_service_name_for_listing(listing_file, listing_data) or ""

        if listing_name == name:
            _display_data(listing_data, listing_file, output_format)
            return

    console.print(f"[red]Listing not found: {name}[/red]")
    raise typer.Exit(code=1)


@show_app.command("service")
def show_service(
    name: str = typer.Argument(..., help="Service name to show (listing name or offering name)"),
    data_dir: Path | None = typer.Option(
        None,
        "--data-dir",
        "-d",
        help="Directory containing data files (default: current directory)",
    ),
    output_format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: json, table, tsv, csv",
    ),
):
    """Show details of a service by name (combines listing and offering data)."""
    if data_dir is None:
        data_dir = Path.cwd()

    if not data_dir.is_absolute():
        data_dir = Path.cwd() / data_dir

    # Find all listing files
    listing_results = find_files_by_schema(data_dir, "listing_v1")

    for listing_file, _fmt, listing_data in listing_results:
        listing_name = listing_data.get("name", "")
        listing_status = listing_data.get("status", "")

        # Find corresponding offering
        offering_results = find_files_by_schema(listing_file.parent, "offering_v1")
        offering_data: dict[str, Any] = {}
        offering_status = ""
        if offering_results:
            _, _fmt, offering_data = offering_results[0]
            offering_status = offering_data.get("status", "")

        offering_name = offering_data.get("name", "")
        service_name = listing_name or offering_name

        if service_name == name:
            # Find provider status
            provider_data: dict[str, Any] = {}
            provider_status = ""
            try:
                provider_dir = listing_file.parent.parent.parent
                provider_results = find_files_by_schema(provider_dir, "provider_v1")
                if provider_results:
                    _, _fmt, provider_data = provider_results[0]
                    provider_status = provider_data.get("status", "")
            except Exception:
                pass

            # Compute service status: draft > deprecated > ready
            statuses = [s for s in [provider_status, offering_status, listing_status] if s]
            if "draft" in statuses:
                service_status = "draft"
            elif "deprecated" in statuses:
                service_status = "deprecated"
            elif statuses and all(s == "ready" for s in statuses):
                service_status = "ready"
            else:
                service_status = statuses[0] if statuses else ""

            # Combine listing and offering data
            service_data = {
                "service_name": service_name,
                "status": service_status,
                "listing": listing_data,
                "offering": offering_data,
                "provider": provider_data,
            }
            _display_data(service_data, listing_file, output_format)
            return

    console.print(f"[red]Service not found: {name}[/red]")
    raise typer.Exit(code=1)


def _display_data(data: dict, file_path: Path, output_format: str):
    """Display data in the specified format."""
    if output_format not in ("tsv", "csv"):
        console.print(f"[dim]File: {file_path}[/dim]\n")

    if output_format == "json":
        json_str = json.dumps(data, indent=2, default=str)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
        console.print(syntax)
    elif output_format in ("tsv", "csv"):
        sep = "\t" if output_format == "tsv" else ","

        def escape_value(value: Any) -> str:
            if value is None:
                return ""
            if isinstance(value, dict | list):
                s = json.dumps(value, default=str)
            else:
                s = str(value)
            if output_format == "csv" and ("," in s or '"' in s or "\n" in s):
                return '"' + s.replace('"', '""') + '"'
            return s

        # Output as key-value pairs
        print(sep.join(["field", "value"]))
        for key, value in data.items():
            print(sep.join([key, escape_value(value)]))
    elif output_format == "table":
        _display_as_table(data)
    else:
        console.print(f"[red]Unknown format: {output_format}[/red]")
        raise typer.Exit(code=1)


def _display_as_table(data: dict, prefix: str = ""):
    """Display dict as a table (flat key-value pairs)."""
    table = Table(show_header=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    for key, value in data.items():
        if isinstance(value, dict):
            # Show nested dict as JSON
            table.add_row(f"{prefix}{key}", json.dumps(value, indent=2, default=str))
        elif isinstance(value, list):
            table.add_row(f"{prefix}{key}", json.dumps(value, indent=2, default=str))
        else:
            table.add_row(f"{prefix}{key}", str(value) if value is not None else "-")

    console.print(table)


app.add_typer(show_app, name="show")

# Register subcommands
app.command("validate")(validator.validate)
app.command("format")(format_data.format_data)
app.command("populate")(populate.populate)

# Test commands - hyphenated for clarity (verb-noun)
app.command("list-tests")(example.list_code_examples)
app.command("run-tests")(example.run_local)
app.command("show-test")(example.show_test)

# Create combined list subgroup
list_app = typer.Typer(help="List local data files")


def _list_services_impl(data_dir: Path | None):
    """Implementation of services listing."""
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
        # Get listing name and status
        listing_name = listing_data.get("name", "")
        listing_status = listing_data.get("status", "")

        # Find corresponding offering file (same directory)
        offering_results = find_files_by_schema(listing_file.parent, "offering_v1")
        offering_name = ""
        offering_status = ""
        offering_data: dict[str, Any] = {}
        if offering_results:
            _, _fmt, offering_data = offering_results[0]
            offering_name = offering_data.get("name", "")
            offering_status = offering_data.get("status", "")

        # Service name: listing name, or offering name if listing name not specified
        service_name = listing_name or offering_name or "unknown"

        # Find provider (parent directory of services)
        provider_name = ""
        provider_status = ""
        try:
            # Structure: data/{provider}/services/{service}/listing.json
            provider_dir = listing_file.parent.parent.parent
            provider_results = find_files_by_schema(provider_dir, "provider_v1")
            if provider_results:
                _, _fmt, provider_data = provider_results[0]
                provider_name = provider_data.get("name", "")
                provider_status = provider_data.get("status", "")
        except Exception:
            pass

        # Compute service status: draft > deprecated > ready
        statuses = [s for s in [provider_status, offering_status, listing_status] if s]
        if "draft" in statuses:
            service_status = "draft"
        elif "deprecated" in statuses:
            service_status = "deprecated"
        elif statuses and all(s == "ready" for s in statuses):
            service_status = "ready"
        else:
            service_status = statuses[0] if statuses else ""

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
            "status": service_status,
            "listing_file": str(listing_rel),
            "service_id": service_id,
        })

    # Display results in table
    table = Table(title="Services")
    table.add_column("Name", style="cyan")
    table.add_column("Provider", style="blue")
    table.add_column("Status", style="magenta")
    table.add_column("Service ID", style="yellow")
    table.add_column("File", style="dim")

    for svc in services:
        service_id = svc["service_id"][:8] + "..." if svc["service_id"] else "-"
        table.add_row(
            svc["service_name"],
            svc["provider_name"] or "-",
            svc["status"] or "-",
            service_id,
            svc["listing_file"],
        )

    console.print(table)
    console.print(f"\n[green]Total:[/green] {len(services)} service(s)")


@list_app.callback(invoke_without_command=True)
def list_callback(
    ctx: typer.Context,
    data_dir: Path = typer.Option(
        None,
        "--data-dir",
        "-d",
        help="Directory containing data files (default: current directory)",
    ),
):
    """List local data files. Without a subcommand, lists all services."""
    if ctx.invoked_subcommand is None:
        _list_services_impl(data_dir)


@list_app.command("services")
def list_services_cmd(
    data_dir: Path | None = typer.Argument(
        None,
        help="Directory containing data files (default: current directory)",
    ),
):
    """List all services with their provider, offering, and listing files."""
    _list_services_impl(data_dir)


# Add existing list commands from list.py
list_app.command("providers")(list_cmd.list_providers)
list_app.command("sellers")(list_cmd.list_sellers)
list_app.command("offerings")(list_cmd.list_offerings)
list_app.command("listings")(list_cmd.list_listings)

app.add_typer(list_app, name="list")
