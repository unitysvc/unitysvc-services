"""Data unpublisher module for deleting service data from UnitySVC backend."""

import asyncio
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from .api import UnitySvcAPI
from .utils import find_files_by_schema, load_data_file

app = typer.Typer(help="Unpublish (delete) data from backend")
console = Console()


class ServiceDataUnpublisher(UnitySvcAPI):
    """Unpublishes (deletes) service data from UnitySVC backend endpoints.

    Inherits base HTTP client with curl fallback from UnitySvcAPI.
    Provides methods for deleting offerings, listings, providers, and sellers.
    """

    async def delete_service_offering(
        self,
        offering_id: str,
        dryrun: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        """Delete a service offering from backend.

        Args:
            offering_id: UUID of the offering to delete
            dryrun: If True, show what would be deleted without actually deleting
            force: If True, force deletion even with active subscriptions

        Returns:
            Response from backend with deletion details

        Raises:
            httpx.HTTPStatusError: If deletion fails (404, 403, etc.)
        """
        params = {}
        if dryrun:
            params["dryrun"] = "true"
        if force:
            params["force"] = "true"

        return await self.delete(f"/publish/offering/{offering_id}", params=params)

    async def delete_service_listing(
        self,
        listing_id: str,
        dryrun: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        """Delete a service listing from backend.

        Args:
            listing_id: UUID of the listing to delete
            dryrun: If True, show what would be deleted without actually deleting
            force: If True, force deletion even with active subscriptions

        Returns:
            Response from backend with deletion details

        Raises:
            httpx.HTTPStatusError: If deletion fails (404, 403, etc.)
        """
        params = {}
        if dryrun:
            params["dryrun"] = "true"
        if force:
            params["force"] = "true"

        return await self.delete(f"/publish/listing/{listing_id}", params=params)

    async def delete_provider(
        self,
        provider_name: str,
        dryrun: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        """Delete a provider from backend.

        Args:
            provider_name: Name of the provider to delete
            dryrun: If True, show what would be deleted without actually deleting
            force: If True, force deletion even with active subscriptions

        Returns:
            Response from backend with deletion details

        Raises:
            httpx.HTTPStatusError: If deletion fails (404, 403, etc.)
        """
        params = {}
        if dryrun:
            params["dryrun"] = "true"
        if force:
            params["force"] = "true"

        return await self.delete(f"/publish/provider/{provider_name}", params=params)

    async def delete_seller(
        self,
        seller_name: str,
        dryrun: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        """Delete a seller from backend.

        Args:
            seller_name: Name of the seller to delete
            dryrun: If True, show what would be deleted without actually deleting
            force: If True, force deletion even with active subscriptions

        Returns:
            Response from backend with deletion details

        Raises:
            httpx.HTTPStatusError: If deletion fails (404, 403, etc.)
        """
        params = {}
        if dryrun:
            params["dryrun"] = "true"
        if force:
            params["force"] = "true"

        return await self.delete(f"/publish/seller/{seller_name}", params=params)


@app.command("offerings")
def unpublish_offerings(
    data_dir: Path | None = typer.Argument(
        None,
        help="Directory containing service offering files (default: current directory)",
    ),
    services: str | None = typer.Option(
        None,
        "--services",
        "-s",
        help="Comma-separated list of service names to unpublish",
    ),
    provider_name: str | None = typer.Option(
        None,
        "--provider",
        "-p",
        help="Unpublish offerings from specific provider",
    ),
    dryrun: bool = typer.Option(
        False,
        "--dryrun",
        help="Show what would be deleted without actually deleting",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force deletion even with active subscriptions",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
):
    """Unpublish (delete) service offerings from backend.

    This command reads offering files to get offering IDs, then deletes them from the backend.

    Examples:
        # Dry-run to see what would be deleted
        usvc unpublish offerings --services "gpt-4" --dryrun

        # Delete specific offering
        usvc unpublish offerings --services "gpt-4"

        # Delete all offerings from a provider
        usvc unpublish offerings --provider openai

        # Force delete (ignore active subscriptions)
        usvc unpublish offerings --services "gpt-4" --force --yes
    """
    if data_dir is None:
        data_dir = Path.cwd()

    console.print(f"[cyan]Searching for offering files in {data_dir}...[/cyan]\n")

    # Find all offering files
    offering_files = []
    for result in find_files_by_schema(data_dir, "service_v1"):
        file_path, _format, _data = result
        offering_files.append((file_path, _format))

    if not offering_files:
        console.print("[yellow]No offering files found[/yellow]")
        raise typer.Exit(code=0)

    # Load offerings and filter
    offerings_to_delete = []
    for file_path, _format in offering_files:
        data, _ = load_data_file(file_path)
        service_name = data.get("name", "Unknown")
        offering_id = data.get("id")
        provider = data.get("provider_name", "Unknown")

        # Apply filters
        if services:
            service_list = [s.strip() for s in services.split(",")]
            if service_name not in service_list:
                continue

        if provider_name and provider_name.lower() not in provider.lower():
            continue

        if not offering_id:
            console.print(f"[yellow]⚠ No offering ID found in {file_path}, skipping[/yellow]")
            continue

        offerings_to_delete.append(
            {
                "id": offering_id,
                "name": service_name,
                "provider": provider,
                "file_path": str(file_path),
            }
        )

    if not offerings_to_delete:
        console.print("[yellow]No offerings found matching filters[/yellow]")
        raise typer.Exit(code=0)

    # Display what will be deleted
    table = Table(title="Offerings to Unpublish")
    table.add_column("Service Name", style="cyan")
    table.add_column("Provider", style="blue")
    table.add_column("Offering ID", style="white")

    for offering in offerings_to_delete:
        table.add_row(offering["name"], offering["provider"], offering["id"])

    console.print(table)
    console.print()

    if dryrun:
        console.print("[yellow]Dry-run mode: No actual deletion performed[/yellow]")
        raise typer.Exit(code=0)

    # Confirmation prompt
    if not yes:
        confirm = typer.confirm(
            f"⚠️  Delete {len(offerings_to_delete)} offering(s) and all associated listings/subscriptions?"
        )
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(code=0)

    # Delete offerings
    async def _delete_all():
        unpublisher = ServiceDataUnpublisher()
        results = []
        for offering in offerings_to_delete:
            try:
                result = await unpublisher.delete_service_offering(
                    offering["id"],
                    dryrun=dryrun,
                    force=force,
                )
                results.append((offering, result, None))
            except Exception as e:
                results.append((offering, None, str(e)))
        return results

    results = asyncio.run(_delete_all())

    # Display results
    console.print("\n[cyan]Results:[/cyan]\n")
    success_count = 0
    error_count = 0

    for offering, result, error in results:
        if error:
            console.print(f"[red]✗ {offering['name']}:[/red] {error}")
            error_count += 1
        else:
            console.print(f"[green]✓ {offering['name']}:[/green] Deleted")
            if result and result.get("cascade_deleted"):
                cascade = result["cascade_deleted"]
                if cascade.get("listings"):
                    console.print(f"  [dim]→ Deleted {cascade['listings']} listing(s)[/dim]")
                if cascade.get("subscriptions"):
                    console.print(f"  [dim]→ Deleted {cascade['subscriptions']} subscription(s)[/dim]")
            success_count += 1

    console.print()
    console.print(f"[green]✓ Success:[/green] {success_count}/{len(results)}")
    if error_count > 0:
        console.print(f"[red]✗ Failed:[/red] {error_count}/{len(results)}")
        raise typer.Exit(code=1)


@app.command("listings")
def unpublish_listings(
    listing_id: str = typer.Argument(..., help="Listing ID to unpublish"),
    dryrun: bool = typer.Option(
        False,
        "--dryrun",
        help="Show what would be deleted without actually deleting",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force deletion even with active subscriptions",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
):
    """Unpublish (delete) a service listing from backend.

    Examples:
        # Dry-run
        usvc unpublish listings abc-123 --dryrun

        # Delete listing
        usvc unpublish listings abc-123

        # Force delete
        usvc unpublish listings abc-123 --force --yes
    """
    console.print(f"[cyan]Unpublishing listing {listing_id}...[/cyan]\n")

    if not yes and not dryrun:
        confirm = typer.confirm("⚠️  Delete this listing and all associated subscriptions?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(code=0)

    async def _delete():
        unpublisher = ServiceDataUnpublisher()
        return await unpublisher.delete_service_listing(listing_id, dryrun=dryrun, force=force)

    try:
        result = asyncio.run(_delete())

        if dryrun:
            console.print("[yellow]Dry-run mode: No actual deletion performed[/yellow]")
            console.print(f"[dim]Would delete: {result}[/dim]")
        else:
            console.print(f"[green]✓ Successfully deleted listing {listing_id}[/green]")
            if result.get("cascade_deleted"):
                cascade = result["cascade_deleted"]
                if cascade.get("subscriptions"):
                    console.print(f"  [dim]→ Deleted {cascade['subscriptions']} subscription(s)[/dim]")

    except Exception as e:
        console.print(f"[red]✗ Failed to delete listing:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("providers")
def unpublish_providers(
    provider_name: str = typer.Argument(..., help="Provider name to unpublish"),
    dryrun: bool = typer.Option(
        False,
        "--dryrun",
        help="Show what would be deleted without actually deleting",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force deletion even with active subscriptions",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
):
    """Unpublish (delete) a provider from backend.

    This will delete the provider and ALL associated offerings, listings, and subscriptions.

    Examples:
        # Dry-run
        usvc unpublish providers openai --dryrun

        # Delete provider
        usvc unpublish providers openai

        # Force delete
        usvc unpublish providers openai --force --yes
    """
    console.print(f"[cyan]Unpublishing provider {provider_name}...[/cyan]\n")

    if not yes and not dryrun:
        confirm = typer.confirm(
            f"⚠️  Delete provider '{provider_name}' and ALL associated offerings/listings/subscriptions?"
        )
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(code=0)

    async def _delete():
        unpublisher = ServiceDataUnpublisher()
        return await unpublisher.delete_provider(provider_name, dryrun=dryrun, force=force)

    try:
        result = asyncio.run(_delete())

        if dryrun:
            console.print("[yellow]Dry-run mode: No actual deletion performed[/yellow]")
            console.print(f"[dim]Would delete: {result}[/dim]")
        else:
            console.print(f"[green]✓ Successfully deleted provider {provider_name}[/green]")
            if result.get("cascade_deleted"):
                cascade = result["cascade_deleted"]
                if cascade.get("offerings"):
                    console.print(f"  [dim]→ Deleted {cascade['offerings']} offering(s)[/dim]")
                if cascade.get("listings"):
                    console.print(f"  [dim]→ Deleted {cascade['listings']} listing(s)[/dim]")
                if cascade.get("subscriptions"):
                    console.print(f"  [dim]→ Deleted {cascade['subscriptions']} subscription(s)[/dim]")

    except Exception as e:
        console.print(f"[red]✗ Failed to delete provider:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("sellers")
def unpublish_sellers(
    seller_name: str = typer.Argument(..., help="Seller name to unpublish"),
    dryrun: bool = typer.Option(
        False,
        "--dryrun",
        help="Show what would be deleted without actually deleting",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force deletion even with active subscriptions",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
):
    """Unpublish (delete) a seller from backend.

    This will delete the seller and ALL associated providers, offerings, listings, and subscriptions.

    Examples:
        # Dry-run
        usvc unpublish sellers my-company --dryrun

        # Delete seller
        usvc unpublish sellers my-company

        # Force delete
        usvc unpublish sellers my-company --force --yes
    """
    console.print(f"[cyan]Unpublishing seller {seller_name}...[/cyan]\n")

    if not yes and not dryrun:
        confirm = typer.confirm(
            f"⚠️  Delete seller '{seller_name}' and ALL associated providers/offerings/listings/subscriptions?"
        )
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(code=0)

    async def _delete():
        unpublisher = ServiceDataUnpublisher()
        return await unpublisher.delete_seller(seller_name, dryrun=dryrun, force=force)

    try:
        result = asyncio.run(_delete())

        if dryrun:
            console.print("[yellow]Dry-run mode: No actual deletion performed[/yellow]")
            console.print(f"[dim]Would delete: {result}[/dim]")
        else:
            console.print(f"[green]✓ Successfully deleted seller {seller_name}[/green]")
            if result.get("cascade_deleted"):
                cascade = result["cascade_deleted"]
                if cascade.get("providers"):
                    console.print(f"  [dim]→ Deleted {cascade['providers']} provider(s)[/dim]")
                if cascade.get("offerings"):
                    console.print(f"  [dim]→ Deleted {cascade['offerings']} offering(s)[/dim]")
                if cascade.get("listings"):
                    console.print(f"  [dim]→ Deleted {cascade['listings']} listing(s)[/dim]")
                if cascade.get("subscriptions"):
                    console.print(f"  [dim]→ Deleted {cascade['subscriptions']} subscription(s)[/dim]")

    except Exception as e:
        console.print(f"[red]✗ Failed to delete seller:[/red] {e}")
        raise typer.Exit(code=1)
