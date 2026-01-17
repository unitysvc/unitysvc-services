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
        help="Output format: table, json",
    ),
    fields: str = typer.Option(
        "id,name,status,seller_id,provider_id,offering_id,listing_id",
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
        else:
            if not services:
                console.print("[yellow]No services found.[/yellow]")
            else:
                table = Table(title="Services")

                # Add columns dynamically based on selected fields
                for field in field_list:
                    # Capitalize and format field names for display
                    column_name = field.replace("_", " ").title()
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
    except ValueError as e:
        console.print(f"[red]✗[/red] {e}", style="bold red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to query services: {e}", style="bold red")
        raise typer.Exit(code=1)
