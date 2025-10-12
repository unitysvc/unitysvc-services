"""Query command group - query backend API for data."""

import json
import os
from typing import Any

import httpx
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Query backend API for data")
console = Console()


class ServiceDataQuery:
    """Query service data from UnitySVC backend endpoints."""

    def __init__(self) -> None:
        """Initialize query client from environment variables.

        Raises:
            ValueError: If required environment variables are not set
        """
        self.base_url = os.environ.get("UNITYSVC_BASE_URL")
        if not self.base_url:
            raise ValueError("UNITYSVC_BASE_URL environment variable not set")

        self.api_key = os.environ.get("UNITYSVC_API_KEY")
        if not self.api_key:
            raise ValueError("UNITYSVC_API_KEY environment variable not set")

        self.base_url = self.base_url.rstrip("/")
        self.client = httpx.Client(
            headers={
                "X-API-Key": self.api_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def list_service_offerings(self, skip: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        """List all service offerings from the backend.

        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
        """
        response = self.client.get(f"{self.base_url}/publish/offerings", params={"skip": skip, "limit": limit})
        response.raise_for_status()
        result = response.json()
        return result.get("data", result) if isinstance(result, dict) else result

    def list_service_listings(self, skip: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        """List all service listings from the backend.

        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
        """
        response = self.client.get(f"{self.base_url}/publish/listings", params={"skip": skip, "limit": limit})
        response.raise_for_status()
        result = response.json()
        return result.get("data", result) if isinstance(result, dict) else result

    def list_providers(self, skip: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        """List all providers from the backend.

        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
        """
        response = self.client.get(f"{self.base_url}/publish/providers", params={"skip": skip, "limit": limit})
        response.raise_for_status()
        result = response.json()
        return result.get("data", result) if isinstance(result, dict) else result

    def list_sellers(self, skip: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        """List all sellers from the backend.

        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
        """
        response = self.client.get(f"{self.base_url}/publish/sellers", params={"skip": skip, "limit": limit})
        response.raise_for_status()
        result = response.json()
        return result.get("data", result) if isinstance(result, dict) else result

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


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

    try:
        with ServiceDataQuery() as query:
            sellers = query.list_sellers(skip=skip, limit=limit)

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

    try:
        with ServiceDataQuery() as query:
            providers = query.list_providers(skip=skip, limit=limit)

            if format == "json":
                # For JSON, filter fields if not all are requested
                if set(field_list) != allowed_fields:
                    filtered_providers = [
                        {k: v for k, v in provider.items() if k in field_list} for provider in providers
                    ]
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
            "id, definition_id, provider_id, status, price, service_name, "
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
):
    """Query all service offerings from UnitySVC backend.

    Examples:
        # Use default fields
        unitysvc_services query offerings

        # Show only specific fields
        unitysvc_services query offerings --fields id,name,status

        # Retrieve more than 100 records
        unitysvc_services query offerings --limit 500

        # Pagination: skip first 100, get next 100
        unitysvc_services query offerings --skip 100 --limit 100

        # Show all available fields
        unitysvc_services query offerings --fields \\
            id,service_name,service_type,provider_name,status,price,definition_id,provider_id
    """
    # Parse fields list
    field_list = [f.strip() for f in fields.split(",")]

    # Define allowed fields from ServiceOfferingPublic model
    allowed_fields = {
        "id",
        "definition_id",
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

    try:
        with ServiceDataQuery() as query:
            offerings = query.list_service_offerings(skip=skip, limit=limit)

            if format == "json":
                # For JSON, filter fields if not all are requested
                if set(field_list) != allowed_fields:
                    filtered_offerings = [
                        {k: v for k, v in offering.items() if k in field_list} for offering in offerings
                    ]
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
):
    """Query all service listings from UnitySVC backend.

    Examples:
        # Use default fields
        unitysvc_services query listings

        # Show only specific fields
        unitysvc_services query listings --fields id,service_name,status

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

    try:
        with ServiceDataQuery() as query:
            listings = query.list_service_listings(skip=skip, limit=limit)

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
