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


@app.command("sellers")
def query_sellers(
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json",
    ),
    fields: str = typer.Option(
        "id,name,display_name,seller_type",
        "--fields",
        help=(
            "Comma-separated list of fields to display. Available fields: "
            "id, name, display_name, seller_type, contact_email, "
            "secondary_contact_email, homepage, description, "
            "business_registration, tax_id, account_manager_id, "
            "created_at, updated_at, status"
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
):
    """Query all sellers from the backend.

    Examples:
        # Use default fields
        unitysvc_services query sellers

        # Show only specific fields
        unitysvc_services query sellers --fields id,name,contact_email

        # Retrieve more than 100 records
        unitysvc_services query sellers --limit 500

        # Pagination: skip first 100, get next 100
        unitysvc_services query sellers --skip 100 --limit 100

        # Show all available fields
        unitysvc_services query sellers --fields \\
            id,name,display_name,seller_type,contact_email,homepage,created_at,updated_at
    """
    # Parse fields list
    field_list = [f.strip() for f in fields.split(",")]

    # Define allowed fields from SellerPublic model
    allowed_fields = {
        "id",
        "name",
        "display_name",
        "seller_type",
        "contact_email",
        "secondary_contact_email",
        "homepage",
        "description",
        "business_registration",
        "tax_id",
        "account_manager_id",
        "created_at",
        "updated_at",
        "status",
    }

    # Validate fields
    invalid_fields = [f for f in field_list if f not in allowed_fields]
    if invalid_fields:
        console.print(
            f"[red]✗[/red] Invalid field(s): {', '.join(invalid_fields)}",
            style="bold red",
        )
        console.print(f"[yellow]Allowed fields:[/yellow] {', '.join(sorted(allowed_fields))}")
        raise typer.Exit(code=1)

    async def _query_sellers_async():
        async with ServiceDataQuery() as query:
            sellers = await query.get("/publish/sellers", {"skip": skip, "limit": limit})
            return sellers.get("data", sellers) if isinstance(sellers, dict) else sellers

    try:
        sellers = asyncio.run(_query_sellers_async())

        if format == "json":
            # For JSON, filter fields if not all are requested
            if set(field_list) != allowed_fields:
                filtered_sellers = [{k: v for k, v in seller.items() if k in field_list} for seller in sellers]
                console.print(json.dumps(filtered_sellers, indent=2))
            else:
                console.print(json.dumps(sellers, indent=2))
        else:
            if not sellers:
                console.print("[yellow]No sellers found.[/yellow]")
            else:
                table = Table(title="Sellers")

                # Define column styles
                field_styles = {
                    "id": "cyan",
                    "name": "green",
                    "display_name": "blue",
                    "seller_type": "magenta",
                    "contact_email": "yellow",
                    "secondary_contact_email": "yellow",
                    "homepage": "blue",
                    "description": "white",
                    "business_registration": "white",
                    "tax_id": "white",
                    "account_manager_id": "cyan",
                    "created_at": "white",
                    "updated_at": "white",
                    "status": "green",
                }

                # Define column headers
                field_headers = {
                    "id": "ID",
                    "name": "Name",
                    "display_name": "Display Name",
                    "seller_type": "Type",
                    "contact_email": "Contact Email",
                    "secondary_contact_email": "Secondary Email",
                    "homepage": "Homepage",
                    "description": "Description",
                    "business_registration": "Business Reg",
                    "tax_id": "Tax ID",
                    "account_manager_id": "Account Manager ID",
                    "created_at": "Created At",
                    "updated_at": "Updated At",
                    "status": "Status",
                }

                # Add columns based on requested fields
                for field in field_list:
                    header = field_headers.get(field, field.title())
                    style = field_styles.get(field, "white")
                    table.add_column(header, style=style)

                # Add rows
                for seller in sellers:
                    row = []
                    for field in field_list:
                        value = seller.get(field)
                        if value is None:
                            row.append("N/A")
                        elif isinstance(value, dict | list):
                            row.append(str(value)[:50])  # Truncate complex types
                        else:
                            row.append(str(value))
                    table.add_row(*row)

                console.print(table)
                console.print(f"\n[green]Total:[/green] {len(sellers)} seller(s)")
    except ValueError as e:
        console.print(f"[red]✗[/red] {e}", style="bold red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to query sellers: {e}", style="bold red")
        raise typer.Exit(code=1)


@app.command("providers")
def query_providers(
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json",
    ),
    fields: str = typer.Option(
        "id,name,display_name,status",
        "--fields",
        help=(
            "Comma-separated list of fields to display. Available fields: "
            "id, name, display_name, contact_email, secondary_contact_email, "
            "homepage, description, status, created_at, updated_at"
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
):
    """Query all providers from the backend.

    Examples:
        # Use default fields
        unitysvc_services query providers

        # Retrieve more than 100 records
        unitysvc_services query providers --limit 500

        # Pagination: skip first 100, get next 100
        unitysvc_services query providers --skip 100 --limit 100

        # Show only specific fields
        unitysvc_services query providers --fields id,name,contact_email

        # Show all available fields
        unitysvc_services query providers --fields \\
            id,name,display_name,contact_email,homepage,status,created_at,updated_at
    """
    # Parse fields list
    field_list = [f.strip() for f in fields.split(",")]

    # Define allowed fields from ProviderPublic model
    allowed_fields = {
        "id",
        "name",
        "display_name",
        "contact_email",
        "secondary_contact_email",
        "homepage",
        "description",
        "status",
        "created_at",
        "updated_at",
    }

    # Validate fields
    invalid_fields = [f for f in field_list if f not in allowed_fields]
    if invalid_fields:
        console.print(
            f"[red]✗[/red] Invalid field(s): {', '.join(invalid_fields)}",
            style="bold red",
        )
        console.print(f"[yellow]Allowed fields:[/yellow] {', '.join(sorted(allowed_fields))}")
        raise typer.Exit(code=1)

    async def _query_providers_async():
        async with ServiceDataQuery() as query:
            providers = await query.get("/publish/providers", {"skip": skip, "limit": limit})
            return providers.get("data", providers) if isinstance(providers, dict) else providers

    try:
        providers = asyncio.run(_query_providers_async())

        if format == "json":
            # For JSON, filter fields if not all are requested
            if set(field_list) != allowed_fields:
                filtered_providers = [{k: v for k, v in provider.items() if k in field_list} for provider in providers]
                console.print(json.dumps(filtered_providers, indent=2))
            else:
                console.print(json.dumps(providers, indent=2))
        else:
            if not providers:
                console.print("[yellow]No providers found.[/yellow]")
            else:
                table = Table(title="Providers")

                # Define column styles
                field_styles = {
                    "id": "cyan",
                    "name": "green",
                    "display_name": "blue",
                    "contact_email": "yellow",
                    "secondary_contact_email": "yellow",
                    "homepage": "blue",
                    "description": "white",
                    "status": "green",
                    "created_at": "magenta",
                    "updated_at": "magenta",
                }

                # Define column headers
                field_headers = {
                    "id": "ID",
                    "name": "Name",
                    "display_name": "Display Name",
                    "contact_email": "Contact Email",
                    "secondary_contact_email": "Secondary Email",
                    "homepage": "Homepage",
                    "description": "Description",
                    "status": "Status",
                    "created_at": "Created At",
                    "updated_at": "Updated At",
                }

                # Add columns based on requested fields
                for field in field_list:
                    header = field_headers.get(field, field.title())
                    style = field_styles.get(field, "white")
                    table.add_column(header, style=style)

                # Add rows
                for provider in providers:
                    row = []
                    for field in field_list:
                        value = provider.get(field)
                        if value is None:
                            row.append("N/A")
                        elif isinstance(value, dict | list):
                            row.append(str(value)[:50])  # Truncate complex types
                        else:
                            row.append(str(value))
                    table.add_row(*row)

                console.print(table)
                console.print(f"\n[green]Total:[/green] {len(providers)} provider(s)")
    except ValueError as e:
        console.print(f"[red]✗[/red] {e}", style="bold red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to query providers: {e}", style="bold red")
        raise typer.Exit(code=1)


@app.command("offerings")
def query_offerings(
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json",
    ),
    fields: str = typer.Option(
        "id,name,service_type,provider_name,status",
        "--fields",
        help=(
            "Comma-separated list of fields to display. Available fields: "
            "id, provider_id, status, price, service_name, "
            "service_type, provider_name"
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
    provider_name: str | None = typer.Option(
        None,
        "--provider-name",
        help="Filter by provider name (case-insensitive partial match)",
    ),
    service_type: str | None = typer.Option(
        None,
        "--service-type",
        help="Filter by service type (exact match, e.g., llm, vectordb, embedding)",
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        help="Filter by service name (case-insensitive partial match)",
    ),
):
    """Query all service offerings from UnitySVC backend.

    Examples:
        # Use default fields
        unitysvc_services query offerings

        # Show only specific fields
        unitysvc_services query offerings --fields id,name,status

        # Filter by provider name
        unitysvc_services query offerings --provider-name openai

        # Filter by service type
        unitysvc_services query offerings --service-type llm

        # Filter by service name
        unitysvc_services query offerings --name llama

        # Combine multiple filters
        unitysvc_services query offerings --service-type llm --provider-name openai

        # Retrieve more than 100 records
        unitysvc_services query offerings --limit 500

        # Pagination: skip first 100, get next 100
        unitysvc_services query offerings --skip 100 --limit 100

        # Show all available fields
        unitysvc_services query offerings --fields \\
            id,service_name,service_type,provider_name,status,price,provider_id
    """
    # Parse fields list
    field_list = [f.strip() for f in fields.split(",")]

    # Define allowed fields from ServiceOfferingPublic model
    allowed_fields = {
        "id",
        "provider_id",
        "status",
        "price",
        "name",
        "service_type",
        "provider_name",
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

    async def _query_offerings_async():
        async with ServiceDataQuery() as query:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            if provider_name:
                params["provider_name"] = provider_name
            if service_type:
                params["service_type"] = service_type
            if name:
                params["name"] = name

            offerings = await query.get("/publish/offerings", params)
            return offerings.get("data", offerings) if isinstance(offerings, dict) else offerings

    try:
        offerings = asyncio.run(_query_offerings_async())

        if format == "json":
            # For JSON, filter fields if not all are requested
            if set(field_list) != allowed_fields:
                filtered_offerings = [{k: v for k, v in offering.items() if k in field_list} for offering in offerings]
                console.print(json.dumps(filtered_offerings, indent=2))
            else:
                console.print(json.dumps(offerings, indent=2))
        else:
            if not offerings:
                console.print("[yellow]No service offerings found.[/yellow]")
            else:
                table = Table(title="Service Offerings")

                # Add columns dynamically based on selected fields
                for field in field_list:
                    # Capitalize and format field names for display
                    column_name = field.replace("_", " ").title()
                    table.add_column(column_name)

                # Add rows
                for offering in offerings:
                    row = []
                    for field in field_list:
                        value = offering.get(field)
                        if value is None:
                            row.append("N/A")
                        elif isinstance(value, dict | list):
                            row.append(str(value)[:50])  # Truncate complex types
                        else:
                            row.append(str(value))
                    table.add_row(*row)

                console.print(table)
                console.print(f"\n[green]Total:[/green] {len(offerings)} service offering(s)")
    except ValueError as e:
        console.print(f"[red]✗[/red] {e}", style="bold red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to query service offerings: {e}", style="bold red")
        raise typer.Exit(code=1)


@app.command("listings")
def query_listings(
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json",
    ),
    fields: str = typer.Option(
        "id,service_name,service_type,seller_name,listing_type,status",
        "--fields",
        help=(
            "Comma-separated list of fields to display. Available fields: "
            "id, offering_id, offering_status, seller_id, status, created_at, updated_at, "
            "parameters_schema, parameters_ui_schema, tags, service_name, "
            "service_type, provider_name, seller_name, listing_type"
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
    seller_name: str | None = typer.Option(
        None,
        "--seller-name",
        help="Filter by seller name (case-insensitive partial match)",
    ),
    provider_name: str | None = typer.Option(
        None,
        "--provider-name",
        help="Filter by provider name (case-insensitive partial match)",
    ),
    service_name: str | None = typer.Option(
        None,
        "--service-name",
        help="Filter by service name (case-insensitive partial match)",
    ),
    service_type: str | None = typer.Option(
        None,
        "--service-type",
        help="Filter by service type (exact match, e.g., llm, vectordb, embedding)",
    ),
    listing_type: str | None = typer.Option(
        None,
        "--listing-type",
        help="Filter by listing type (exact match: regular, byop, self_hosted)",
    ),
):
    """Query all service listings from UnitySVC backend.

    Examples:
        # Use default fields
        unitysvc_services query listings

        # Show only specific fields
        unitysvc_services query listings --fields id,service_name,status

        # Filter by seller name
        unitysvc_services query listings --seller-name chutes

        # Filter by provider name
        unitysvc_services query listings --provider-name openai

        # Filter by service type
        unitysvc_services query listings --service-type llm

        # Filter by listing type
        unitysvc_services query listings --listing-type byop

        # Combine multiple filters
        unitysvc_services query listings --service-type llm --listing-type regular

        # Retrieve more than 100 records
        unitysvc_services query listings --limit 500

        # Pagination: skip first 100, get next 100
        unitysvc_services query listings --skip 100 --limit 100

        # Show all available fields
        unitysvc_services query listings --fields \\
            id,name,service_name,service_type,seller_name,listing_type,status,provider_name
    """
    # Parse fields list
    field_list = [f.strip() for f in fields.split(",")]

    # Define allowed fields from ServiceListingPublic model
    allowed_fields = {
        "id",
        "name",
        "offering_id",
        "offering_status",
        "seller_id",
        "status",
        "created_at",
        "updated_at",
        "parameters_schema",
        "parameters_ui_schema",
        "tags",
        "service_name",
        "service_type",
        "provider_name",
        "seller_name",
        "listing_type",
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

    async def _query_listings_async():
        async with ServiceDataQuery() as query:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            if seller_name:
                params["seller_name"] = seller_name
            if provider_name:
                params["provider_name"] = provider_name
            if service_name:
                params["service_name"] = service_name
            if service_type:
                params["service_type"] = service_type
            if listing_type:
                params["listing_type"] = listing_type

            listings = await query.get("/publish/listings", params)
            return listings.get("data", listings) if isinstance(listings, dict) else listings

    try:
        listings = asyncio.run(_query_listings_async())

        if format == "json":
            # For JSON, filter fields if not all are requested
            if set(field_list) != allowed_fields:
                filtered_listings = [{k: v for k, v in listing.items() if k in field_list} for listing in listings]
                console.print(json.dumps(filtered_listings, indent=2))
            else:
                console.print(json.dumps(listings, indent=2))
        else:
            if not listings:
                console.print("[yellow]No service listings found.[/yellow]")
            else:
                table = Table(title="Service Listings")

                # Add columns dynamically based on selected fields
                for field in field_list:
                    # Capitalize and format field names for display
                    column_name = field.replace("_", " ").title()
                    table.add_column(column_name)

                # Add rows
                for listing in listings:
                    row = []
                    for field in field_list:
                        value = listing.get(field)
                        if value is None:
                            row.append("N/A")
                        elif isinstance(value, dict | list):
                            row.append(str(value)[:50])  # Truncate complex types
                        else:
                            row.append(str(value))
                    table.add_row(*row)

                console.print(table)
                console.print(f"\n[green]Total:[/green] {len(listings)} service listing(s)")
    except ValueError as e:
        console.print(f"[red]✗[/red] {e}", style="bold red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to query service listings: {e}", style="bold red")
        raise typer.Exit(code=1)
