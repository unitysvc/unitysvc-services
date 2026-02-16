"""Query command group - query backend API for data."""

import asyncio
import json
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from .api import UnitySvcAPI
from .output import format_output

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
        "id,name,provider_name,service_type,status",
        "--fields",
        help=(
            "Comma-separated list of fields to display. Available fields: "
            "id, name, display_name, status, service_type, provider_name, listing_type, "
            "seller_id, provider_id, offering_id, listing_id, revision_of, pending_revision_id, "
            "is_featured, review_count, average_rating, created_at, updated_at"
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
        "service_type",
        "provider_name",
        "listing_type",
        "seller_id",
        "provider_id",
        "offering_id",
        "listing_id",
        "revision_of",
        "pending_revision_id",
        "is_featured",
        "review_count",
        "average_rating",
        "ops_subscription_id",
        "ops_customer_id",
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

        format_output(
            services,
            output_format=format,
            columns=field_list,
            title="Services",
            console=console,
        )
    except ValueError as e:
        console.print(f"[red]✗[/red] {e}", style="bold red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to query services: {e}", style="bold red")
        raise typer.Exit(code=1)


def show_service(
    service_id: str = typer.Argument(..., help="Service ID to show (supports partial IDs, minimum 8 chars)"),
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json",
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
        elif format == "table":
            # Service Identity
            console.print("\n[bold]Service Identity[/bold]")
            id_table = Table(show_header=False, box=None)
            id_table.add_column("Field", style="cyan")
            id_table.add_column("Value")

            id_table.add_row("ID", str(service.get("service_id", "N/A")))
            id_table.add_row("Name", str(service.get("service_name", "N/A")))
            id_table.add_row("Status", str(service.get("status", "N/A")))
            if service.get("status_message"):
                id_table.add_row("Status Message", str(service["status_message"]))
            id_table.add_row("Provider Name", str(service.get("provider_name", "N/A")))

            console.print(id_table)

            # Provider Information
            provider = service.get("provider")
            if provider and isinstance(provider, dict):
                console.print("\n[bold]Provider (Content)[/bold]")
                provider_table = Table(show_header=False, box=None)
                provider_table.add_column("Field", style="cyan")
                provider_table.add_column("Value")

                provider_table.add_row("ID", str(provider.get("id", "N/A")))
                provider_table.add_row("Name", str(provider.get("name", "N/A")))
                provider_table.add_row("Display Name", str(provider.get("display_name", "N/A")))
                provider_table.add_row("Status", str(provider.get("status", "N/A")))
                if provider.get("contact_email"):
                    provider_table.add_row("Contact Email", str(provider["contact_email"]))
                if provider.get("homepage"):
                    provider_table.add_row("Homepage", str(provider["homepage"]))
                if provider.get("description"):
                    desc = str(provider["description"])
                    provider_table.add_row("Description", desc[:80] + "..." if len(desc) > 80 else desc)

                console.print(provider_table)

            # Offering Information
            offering = service.get("offering")
            if offering and isinstance(offering, dict):
                console.print("\n[bold]Service Offering (Content)[/bold]")
                offering_table = Table(show_header=False, box=None)
                offering_table.add_column("Field", style="cyan")
                offering_table.add_column("Value")

                offering_table.add_row("ID", str(offering.get("id", "N/A")))
                offering_table.add_row("Name", str(offering.get("name", "N/A")))
                offering_table.add_row("Display Name", str(offering.get("display_name", "N/A")))
                offering_table.add_row("Service Type", str(offering.get("service_type", "N/A")))
                offering_table.add_row("Status", str(offering.get("status", "N/A")))
                if offering.get("tagline"):
                    offering_table.add_row("Tagline", str(offering["tagline"]))
                if offering.get("payout_price"):
                    offering_table.add_row("Payout Price", json.dumps(offering["payout_price"]))
                if offering.get("description"):
                    desc = str(offering["description"])
                    offering_table.add_row("Description", desc[:80] + "..." if len(desc) > 80 else desc)

                console.print(offering_table)

            # Listing Information
            listing = service.get("listing")
            if listing and isinstance(listing, dict):
                console.print("\n[bold]Service Listing (Content)[/bold]")
                listing_table = Table(show_header=False, box=None)
                listing_table.add_column("Field", style="cyan")
                listing_table.add_column("Value")

                listing_table.add_row("ID", str(listing.get("id", "N/A")))
                listing_table.add_row("Name", str(listing.get("name", "N/A")))
                listing_table.add_row("Display Name", str(listing.get("display_name", "N/A")))
                listing_table.add_row("Status", str(listing.get("status", "N/A")))
                if listing.get("list_price"):
                    listing_table.add_row("List Price", json.dumps(listing["list_price"]))
                if listing.get("currency"):
                    listing_table.add_row("Currency", str(listing["currency"]))
                if listing.get("tags"):
                    listing_table.add_row("Tags", str(listing["tags"]))
                if listing.get("parameters_schema"):
                    required = listing["parameters_schema"].get("required", [])
                    listing_table.add_row("Required Params", ", ".join(required) if required else "None")

                console.print(listing_table)

            console.print()
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
