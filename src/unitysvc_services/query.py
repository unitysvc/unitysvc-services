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
        "id,name,provider_name,service_type,status,revision_of",
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
    name: str | None = typer.Option(
        None,
        "--name",
        "-n",
        help="Search by name, display name, or provider name (case-insensitive partial match)",
    ),
    provider: str | None = typer.Option(
        None,
        "--provider",
        help="Filter by provider name (case-insensitive partial match)",
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

        # Search by name
        usvc query --name "my-service"

        # Filter by provider
        usvc query --provider "My Company"

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
            # When filtering by provider (client-side), fetch all results
            # first so the limit applies after filtering, not before.
            fetch_limit = 1000 if provider else limit
            params: dict[str, Any] = {"skip": skip, "limit": fetch_limit}
            if status:
                params["status"] = status
            if name:
                params["name"] = name

            services = await query.get("/seller/services", params)
            data = services.get("data", services) if isinstance(services, dict) else services

            # Client-side provider filtering
            if provider:
                provider_lower = provider.lower()
                data = [
                    svc for svc in data
                    if provider_lower in svc.get("provider_name", "").lower()
                ]
                data = data[:limit]

            # Group active services with their revisions:
            # active service followed by its revision(s), then remaining services
            revision_of_map: dict[str, list[dict]] = {}
            active_ids: set[str] = set()
            non_revision: list[dict] = []

            for svc in data:
                rev_of = svc.get("revision_of")
                if rev_of:
                    revision_of_map.setdefault(rev_of, []).append(svc)
                else:
                    non_revision.append(svc)
                    if svc.get("status") == "active":
                        active_ids.add(svc.get("id", ""))

            ordered: list[dict] = []
            for svc in non_revision:
                ordered.append(svc)
                svc_id = svc.get("id", "")
                if svc_id in revision_of_map:
                    ordered.extend(revision_of_map.pop(svc_id))

            # Append any orphan revisions whose parent wasn't in results
            for revisions in revision_of_map.values():
                ordered.extend(revisions)

            return ordered

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
            id_table.add_row("Seller Name", str(service.get("provider_name", "N/A")))

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
                capabilities = offering.get("capabilities")
                if capabilities:
                    offering_table.add_row("Capabilities", ", ".join(capabilities))
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

                svc_options = listing.get("service_options") or {}
                enrollment_vars = svc_options.get("enrollment_vars", {})
                has_required_params = bool(listing.get("parameters_schema", {}).get("required"))
                listing_table.add_row("Enrollment Required", str(has_required_params or bool(enrollment_vars)))

                # Collect customer secrets from user_access_interfaces
                user_ifaces = listing.get("user_access_interfaces") or {}
                all_secrets: list[str] = []
                for iface_data in user_ifaces.values():
                    if isinstance(iface_data, dict):
                        secrets = iface_data.get("customer_secrets_needed") or []
                        all_secrets.extend(s for s in secrets if s not in all_secrets)
                if all_secrets:
                    listing_table.add_row("Required Secrets", ", ".join(all_secrets))

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
