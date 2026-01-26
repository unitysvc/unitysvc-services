"""Query command group - query backend API for data."""

import asyncio
import json
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from .api import UnitySvcAPI

app = typer.Typer(help="Query backend API for data")
console = Console()


class ServiceDataQuery(UnitySvcAPI):
    """Query service data from UnitySVC backend endpoints.

    Inherits HTTP methods with automatic curl fallback from UnitySvcAPI.
    Provides async methods for querying public service data.
    Use with async context manager for proper resource cleanup.
    """

    pass


@app.callback(invoke_without_command=True)
def query_services(
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json, tsv, csv",
    ),
    fields: str = typer.Option(
        "id,name,status,provider_id,offering_id,listing_id",
        "--fields",
        help=(
            "Comma-separated list of fields to display. Available fields: "
            "id, name, display_name, status, seller_id, provider_id, offering_id, "
            "listing_id, revision_of, created_by_id, updated_by_id, created_at, updated_at"
        ),
    ),
    skip: int = typer.Option(
        0,
        "--skip",
        help="Number of records to skip (for pagination)",
    ),
    limit: int = typer.Option(
        100,
        "--limit",
        help="Maximum number of records to return (default: 100)",
    ),
    status: str | None = typer.Option(
        None,
        "--status",
        help="Filter by status (draft, pending, testing, active, rejected, suspended)",
    ),
):
    """Query services for the current seller.

    Services are the identity layer that connects sellers to content versions
    (Provider, ServiceOffering, ServiceListing).

    Examples:
        # Use default fields
        usvc query

        # Show only specific fields
        usvc query --fields id,name,status

        # Filter by status
        usvc query --status active

        # Output as JSON
        usvc query --format json

        # Pagination
        usvc query --skip 100 --limit 100
    """
    # Parse fields list
    field_list = [f.strip() for f in fields.split(",")]

    # Define allowed fields from ServicePublic model
    allowed_fields = {
        "id",
        "name",
        "display_name",
        "status",
        "seller_id",
        "provider_id",
        "offering_id",
        "listing_id",
        "revision_of",
        "created_by_id",
        "updated_by_id",
        "created_at",
        "updated_at",
    }

    # Validate fields
    invalid_fields = [f for f in field_list if f not in allowed_fields]
    if invalid_fields:
        console.print(
            f"[red]Error:[/red] Invalid field(s): {', '.join(invalid_fields)}",
            style="bold red",
        )
        console.print(f"[yellow]Available fields:[/yellow] {', '.join(sorted(allowed_fields))}")
        raise typer.Exit(code=1)

    async def _query_services_async():
        async with ServiceDataQuery() as query:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            if status:
                params["status"] = status

            services = await query.get("/seller/services", params)
            return services.get("data", services) if isinstance(services, dict) else services

    try:
        services = asyncio.run(_query_services_async())

        if format == "json":
            # For JSON, filter fields if not all are requested
            if set(field_list) != allowed_fields:
                filtered_services = [{k: v for k, v in svc.items() if k in field_list} for svc in services]
                console.print(json.dumps(filtered_services, indent=2))
            else:
                console.print(json.dumps(services, indent=2))
        elif format in ("tsv", "csv"):
            # Tab or comma-separated output
            sep = "\t" if format == "tsv" else ","

            def escape_value(value: Any) -> str:
                """Escape value for CSV/TSV output."""
                if value is None:
                    return ""
                s = str(value)
                # For CSV, quote fields containing comma, quote, or newline
                if format == "csv" and (sep in s or '"' in s or "\n" in s):
                    return '"' + s.replace('"', '""') + '"'
                return s

            # Print header
            print(sep.join(field_list))
            # Print rows
            for svc in services:
                row = [escape_value(svc.get(field)) for field in field_list]
                print(sep.join(row))
        elif format == "table":
            if not services:
                console.print("[yellow]No services found.[/yellow]")
            else:
                table = Table(title="Services")

                # Add columns dynamically based on selected fields
                for field in field_list:
                    # Capitalize and format field names for display
                    column_name = field.replace("_", " ").title()
                    # Show id field in full without wrapping
                    if field == "id":
                        table.add_column(column_name, no_wrap=True)
                    else:
                        table.add_column(column_name)

                # Add rows
                for svc in services:
                    row = []
                    for field in field_list:
                        value = svc.get(field)
                        if value is None:
                            row.append("N/A")
                        elif isinstance(value, dict | list):
                            row.append(str(value)[:50])  # Truncate complex types
                        else:
                            row.append(str(value))
                    table.add_row(*row)

                console.print(table)
                console.print(f"\n[green]Total:[/green] {len(services)} service(s)")
        else:
            console.print(f"[red]Unknown format: {format}[/red]")
            raise typer.Exit(code=1)
    except ValueError as e:
        console.print(f"[red]✗[/red] {e}", style="bold red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to query services: {e}", style="bold red")
        raise typer.Exit(code=1)


def show_service(
    service_id: str = typer.Argument(..., help="Service ID to show (supports partial IDs, minimum 8 chars)"),
    format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: json, table, tsv, csv",
    ),
):
    """Show details of a service by ID.

    Supports partial ID matching (minimum 8 characters, like git).

    Examples:
        # Show service by full ID
        usvc services show 297040cd-c676-48d7-9a06-9b2a1d713496

        # Show service by partial ID
        usvc services show 297040cd
    """
    async def _show_service():
        async with ServiceDataQuery() as query:
            # Pass partial ID directly to backend - it handles resolution
            service = await query.get(f"/seller/services/{service_id}/data")
            return service

    try:
        service = asyncio.run(_show_service())

        if format == "json":
            console.print(json.dumps(service, indent=2, default=str))
        elif format in ("tsv", "csv"):
            sep = "\t" if format == "tsv" else ","

            def escape_value(value: Any) -> str:
                if value is None:
                    return ""
                if isinstance(value, dict | list):
                    s = json.dumps(value, default=str)
                else:
                    s = str(value)
                if format == "csv" and ("," in s or '"' in s or "\n" in s):
                    return '"' + s.replace('"', '""') + '"'
                return s

            # Output as key-value pairs
            print(sep.join(["field", "value"]))
            for key, value in service.items():
                print(sep.join([key, escape_value(value)]))
        elif format == "table":
            # Display service metadata first
            name = service.get("service_name", service_id)
            table = Table(title=f"Service: {name}")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")

            # Show metadata fields first
            metadata_fields = ["service_id", "service_name", "status", "provider_name"]
            for field in metadata_fields:
                if field in service:
                    table.add_row(field, str(service[field]) if service[field] is not None else "-")

            # Show content sections
            for key in ["provider", "offering", "listing"]:
                if key in service and isinstance(service[key], dict):
                    table.add_row(f"[bold]{key}[/bold]", "")
                    for k, v in service[key].items():
                        if isinstance(v, dict | list):
                            v_str = json.dumps(v, indent=2, default=str)
                            display = v_str[:100] + "..." if len(v_str) > 100 else v_str
                            table.add_row(f"  {k}", display)
                        else:
                            table.add_row(f"  {k}", str(v) if v is not None else "-")

            console.print(table)
        else:
            console.print(f"[red]Unknown format: {format}[/red]")
            raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except ValueError as e:
        console.print(f"[red]✗[/red] {e}", style="bold red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to show service: {e}", style="bold red")
        raise typer.Exit(code=1)
