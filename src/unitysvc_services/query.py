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

    def __init__(self, base_url: str, api_key: str):
        """Initialize query client with backend URL and API key.

        Args:
            base_url: UnitySVC backend URL
            api_key: API key for authentication

        Raises:
            ValueError: If base_url or api_key is not provided
        """
        if not base_url:
            raise ValueError(
                "Backend URL not provided. Use --backend-url or set UNITYSVC_BACKEND_URL env var."
            )
        if not api_key:
            raise ValueError(
                "API key not provided. Use --api-key or set UNITYSVC_API_KEY env var."
            )

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.Client(
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def list_service_offerings(self) -> list[dict[str, Any]]:
        """List all service offerings from the backend."""
        response = self.client.get(f"{self.base_url}/publish/service_offerings")
        response.raise_for_status()
        result = response.json()
        return result.get("data", result) if isinstance(result, dict) else result

    def list_service_listings(self) -> list[dict[str, Any]]:
        """List all service listings from the backend."""
        response = self.client.get(f"{self.base_url}/publish/services")
        response.raise_for_status()
        result = response.json()
        return result.get("data", result) if isinstance(result, dict) else result

    def list_providers(self) -> list[dict[str, Any]]:
        """List all providers from the backend."""
        response = self.client.get(f"{self.base_url}/publish/providers")
        response.raise_for_status()
        result = response.json()
        return result.get("data", result) if isinstance(result, dict) else result

    def list_sellers(self) -> list[dict[str, Any]]:
        """List all sellers from the backend."""
        response = self.client.get(f"{self.base_url}/publish/sellers")
        response.raise_for_status()
        result = response.json()
        return result.get("data", result) if isinstance(result, dict) else result

    def list_access_interfaces(self) -> dict[str, Any]:
        """List all access interfaces from the backend (private endpoint)."""
        response = self.client.get(f"{self.base_url}/private/access_interfaces")
        response.raise_for_status()
        return response.json()

    def list_documents(self) -> dict[str, Any]:
        """List all documents from the backend (private endpoint)."""
        response = self.client.get(f"{self.base_url}/private/documents")
        response.raise_for_status()
        return response.json()

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    @staticmethod
    def from_env(
        backend_url: str | None = None, api_key: str | None = None
    ) -> "ServiceDataQuery":
        """Create ServiceDataQuery from environment variables or arguments.

        Args:
            backend_url: Optional backend URL (falls back to UNITYSVC_BACKEND_URL env var)
            api_key: Optional API key (falls back to UNITYSVC_API_KEY env var)

        Returns:
            ServiceDataQuery instance

        Raises:
            ValueError: If required credentials are not provided
        """
        resolved_backend_url = backend_url or os.getenv("UNITYSVC_BACKEND_URL") or ""
        resolved_api_key = api_key or os.getenv("UNITYSVC_API_KEY") or ""
        return ServiceDataQuery(base_url=resolved_backend_url, api_key=resolved_api_key)


@app.command("sellers")
def query_sellers(
    backend_url: str | None = typer.Option(
        None,
        "--backend-url",
        "-u",
        help="UnitySVC backend URL (default: from UNITYSVC_BACKEND_URL env var)",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key for authentication (default: from UNITYSVC_API_KEY env var)",
    ),
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json",
    ),
):
    """Query all sellers from the backend."""
    try:
        with ServiceDataQuery.from_env(backend_url, api_key) as query:
            sellers = query.list_sellers()

            if format == "json":
                console.print(json.dumps(sellers, indent=2))
            else:
                if not sellers:
                    console.print("[yellow]No sellers found.[/yellow]")
                else:
                    table = Table(title="Sellers")
                    table.add_column("ID", style="cyan")
                    table.add_column("Name", style="green")
                    table.add_column("Display Name", style="blue")
                    table.add_column("Type", style="magenta")
                    table.add_column("Contact Email", style="yellow")
                    table.add_column("Active", style="white")

                    for seller in sellers:
                        table.add_row(
                            str(seller.get("id", "N/A")),
                            seller.get("name", "N/A"),
                            seller.get("display_name", "N/A"),
                            seller.get("seller_type", "N/A"),
                            seller.get("contact_email", "N/A"),
                            "✓" if seller.get("is_active") else "✗",
                        )

                    console.print(table)
    except ValueError as e:
        console.print(f"[red]✗[/red] {e}", style="bold red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to query sellers: {e}", style="bold red")
        raise typer.Exit(code=1)


@app.command("providers")
def query_providers(
    backend_url: str | None = typer.Option(
        None,
        "--backend-url",
        "-u",
        help="UnitySVC backend URL (default: from UNITYSVC_BACKEND_URL env var)",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key for authentication (default: from UNITYSVC_API_KEY env var)",
    ),
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json",
    ),
):
    """Query all providers from the backend."""
    try:
        with ServiceDataQuery.from_env(backend_url, api_key) as query:
            providers = query.list_providers()

            if format == "json":
                console.print(json.dumps(providers, indent=2))
            else:
                if not providers:
                    console.print("[yellow]No providers found.[/yellow]")
                else:
                    table = Table(title="Providers")
                    table.add_column("ID", style="cyan")
                    table.add_column("Name", style="green")
                    table.add_column("Display Name", style="blue")
                    table.add_column("Time Created", style="magenta")

                    for provider in providers:
                        table.add_row(
                            str(provider.get("id", "N/A")),
                            provider.get("name", "N/A"),
                            provider.get("display_name", "N/A"),
                            str(provider.get("time_created", "N/A")),
                        )

                    console.print(table)
    except ValueError as e:
        console.print(f"[red]✗[/red] {e}", style="bold red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to query providers: {e}", style="bold red")
        raise typer.Exit(code=1)


@app.command("offerings")
def query_offerings(
    backend_url: str | None = typer.Option(
        None,
        "--backend-url",
        "-u",
        help="UnitySVC backend URL (default: from UNITYSVC_BACKEND_URL env var)",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key for authentication (default: from UNITYSVC_API_KEY env var)",
    ),
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json",
    ),
):
    """Query all service offerings from UnitySVC backend."""
    try:
        with ServiceDataQuery.from_env(backend_url, api_key) as query:
            offerings = query.list_service_offerings()

            if format == "json":
                console.print(json.dumps(offerings, indent=2))
            else:
                if not offerings:
                    console.print("[yellow]No service offerings found.[/yellow]")
                else:
                    table = Table(title="Service Offerings", show_lines=True)
                    table.add_column("ID", style="cyan")
                    table.add_column("Name", style="green")
                    table.add_column("Display Name", style="blue")
                    table.add_column("Type", style="magenta")
                    table.add_column("Status", style="yellow")
                    table.add_column("Version")

                    for offering in offerings:
                        table.add_row(
                            str(offering.get("id", "N/A")),
                            offering.get("name", "N/A"),
                            offering.get("display_name", "N/A"),
                            offering.get("service_type", "N/A"),
                            offering.get("upstream_status", "N/A"),
                            offering.get("version", "N/A"),
                        )

                    console.print(table)
                    console.print(
                        f"\n[green]Total:[/green] {len(offerings)} service offering(s)"
                    )
    except ValueError as e:
        console.print(f"[red]✗[/red] {e}", style="bold red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(
            f"[red]✗[/red] Failed to query service offerings: {e}", style="bold red"
        )
        raise typer.Exit(code=1)


@app.command("listings")
def query_listings(
    backend_url: str | None = typer.Option(
        None,
        "--backend-url",
        "-u",
        help="UnitySVC backend URL (default: from UNITYSVC_BACKEND_URL env var)",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key for authentication (default: from UNITYSVC_API_KEY env var)",
    ),
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json",
    ),
):
    """Query all service listings from UnitySVC backend."""
    try:
        with ServiceDataQuery.from_env(backend_url, api_key) as query:
            listings = query.list_service_listings()

            if format == "json":
                console.print(json.dumps(listings, indent=2))
            else:
                if not listings:
                    console.print("[yellow]No service listings found.[/yellow]")
                else:
                    table = Table(title="Service Listings", show_lines=True)
                    table.add_column("ID", style="cyan")
                    table.add_column("Service ID", style="blue")
                    table.add_column("Seller", style="green")
                    table.add_column("Status", style="yellow")
                    table.add_column("Interfaces")

                    for listing in listings:
                        interfaces_count = len(
                            listing.get("user_access_interfaces", [])
                        )
                        table.add_row(
                            str(listing.get("id", "N/A")),
                            str(listing.get("service_id", "N/A")),
                            listing.get("seller_name", "N/A"),
                            listing.get("listing_status", "N/A"),
                            str(interfaces_count),
                        )

                    console.print(table)
                    console.print(
                        f"\n[green]Total:[/green] {len(listings)} service listing(s)"
                    )
    except ValueError as e:
        console.print(f"[red]✗[/red] {e}", style="bold red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(
            f"[red]✗[/red] Failed to query service listings: {e}", style="bold red"
        )
        raise typer.Exit(code=1)


@app.command("interfaces")
def query_interfaces(
    backend_url: str | None = typer.Option(
        None,
        "--backend-url",
        "-u",
        help="UnitySVC backend URL (default: from UNITYSVC_BACKEND_URL env var)",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key for authentication (default: from UNITYSVC_API_KEY env var)",
    ),
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json",
    ),
):
    """Query all access interfaces from UnitySVC backend (private endpoint)."""
    try:
        with ServiceDataQuery.from_env(backend_url, api_key) as query:
            data = query.list_access_interfaces()

            if format == "json":
                console.print(json.dumps(data, indent=2))
            else:
                interfaces = data.get("data", [])
                if not interfaces:
                    console.print("[yellow]No access interfaces found.[/yellow]")
                else:
                    table = Table(title="Access Interfaces", show_lines=True)
                    table.add_column("ID", style="cyan")
                    table.add_column("Name", style="green")
                    table.add_column("Context", style="blue")
                    table.add_column("Entity ID", style="yellow")
                    table.add_column("Method", style="magenta")
                    table.add_column("Active", style="green")

                    for interface in interfaces:
                        table.add_row(
                            str(interface.get("id", "N/A"))[:8] + "...",
                            interface.get("name", "N/A"),
                            interface.get("context_type", "N/A"),
                            str(interface.get("entity_id", "N/A"))[:8] + "...",
                            interface.get("access_method", "N/A"),
                            "✓" if interface.get("is_active") else "✗",
                        )

                    console.print(table)
                    console.print(
                        f"\n[green]Total:[/green] {data.get('count', 0)} access interface(s)"
                    )
    except ValueError as e:
        console.print(f"[red]✗[/red] {e}", style="bold red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(
            f"[red]✗[/red] Failed to query access interfaces: {e}", style="bold red"
        )
        raise typer.Exit(code=1)


@app.command("documents")
def query_documents(
    backend_url: str | None = typer.Option(
        None,
        "--backend-url",
        "-u",
        help="UnitySVC backend URL (default: from UNITYSVC_BACKEND_URL env var)",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key for authentication (default: from UNITYSVC_API_KEY env var)",
    ),
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json",
    ),
):
    """Query all documents from UnitySVC backend (private endpoint)."""
    try:
        with ServiceDataQuery.from_env(backend_url, api_key) as query:
            data = query.list_documents()

            if format == "json":
                console.print(json.dumps(data, indent=2))
            else:
                documents = data.get("data", [])
                if not documents:
                    console.print("[yellow]No documents found.[/yellow]")
                else:
                    table = Table(title="Documents", show_lines=True)
                    table.add_column("ID", style="cyan")
                    table.add_column("Title", style="green")
                    table.add_column("Category", style="blue")
                    table.add_column("MIME Type", style="yellow")
                    table.add_column("Context", style="magenta")
                    table.add_column("Public", style="red")

                    for doc in documents:
                        table.add_row(
                            str(doc.get("id", "N/A"))[:8] + "...",
                            doc.get("title", "N/A")[:40],
                            doc.get("category", "N/A"),
                            doc.get("mime_type", "N/A"),
                            doc.get("context_type", "N/A"),
                            "✓" if doc.get("is_public") else "✗",
                        )

                    console.print(table)
                    console.print(
                        f"\n[green]Total:[/green] {data.get('count', 0)} document(s)"
                    )
    except ValueError as e:
        console.print(f"[red]✗[/red] {e}", style="bold red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to query documents: {e}", style="bold red")
        raise typer.Exit(code=1)
