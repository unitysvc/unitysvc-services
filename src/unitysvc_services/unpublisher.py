"""Data unpublisher module for deleting service data from UnitySVC backend."""

import asyncio
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from .api import UnitySvcAPI
from .utils import find_files_by_schema, load_data_file, resolve_provider_name

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

        return await self.delete(f"/seller/offerings/{offering_id}", params=params)

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

        return await self.delete(f"/seller/listings/{listing_id}", params=params)

    async def delete_service(
        self,
        service_id: str,
        dryrun: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        """Delete a service by its service ID.

        Args:
            service_id: UUID of the service to delete
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

        return await self.delete(f"/seller/services/{service_id}", params=params)

    async def update_service_status(
        self,
        service_id: str,
        status: str,
    ) -> dict[str, Any]:
        """Update a service's status.

        Args:
            service_id: UUID of the service to update
            status: New status (e.g., "deprecated", "active", "suspended")

        Returns:
            Response from backend with update details

        Raises:
            httpx.HTTPStatusError: If update fails (404, 403, etc.)
        """
        return await self.patch(f"/seller/services/{service_id}", json_data={"status": status})

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

        return await self.delete(f"/seller/providers/{provider_name}", params=params)

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

        return await self.delete(f"/seller/sellers/{seller_name}", params=params)


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
    for result in find_files_by_schema(data_dir, "offering_v1"):
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
        provider = resolve_provider_name(file_path) or "Unknown"

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


def deprecate_service(
    service_ids: list[str] = typer.Argument(..., help="Service ID(s) to deprecate (supports partial IDs)"),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
):
    """Mark one or more services as deprecated.

    Deprecated services remain in the system but are no longer available for
    new subscriptions. Existing subscriptions are not affected.

    Supports partial ID matching (minimum 8 characters, like git).

    Examples:
        # Deprecate single service (full or partial ID)
        usvc services deprecate 297040cd

        # Deprecate multiple services
        usvc services deprecate 297040cd def-456 ghi-789

        # Skip confirmation
        usvc services deprecate 297040cd --yes
    """
    count = len(service_ids)
    if count == 1:
        console.print(f"[cyan]Deprecating service {service_ids[0]}...[/cyan]\n")
    else:
        console.print(f"[cyan]Deprecating {count} services...[/cyan]\n")
        for sid in service_ids:
            console.print(f"  • {sid}")
        console.print()

    if not yes:
        if count == 1:
            confirm = typer.confirm(f"Mark service '{service_ids[0]}' as deprecated?")
        else:
            confirm = typer.confirm(f"Mark {count} services as deprecated?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(code=0)

    async def _deprecate_all():
        unpublisher = ServiceDataUnpublisher()
        results = []
        for service_id in service_ids:
            try:
                result = await unpublisher.update_service_status(service_id, status="deprecated")
                results.append((service_id, result, None))
            except Exception as e:
                results.append((service_id, None, str(e)))
        return results

    results = asyncio.run(_deprecate_all())

    # Display results
    success_count = 0
    error_count = 0

    for service_id, result, error in results:
        if error:
            console.print(f"[red]✗ {service_id}:[/red] {error}")
            error_count += 1
        else:
            console.print(f"[green]✓ {service_id}:[/green] Marked as deprecated")
            success_count += 1

    # Summary
    if count > 1:
        console.print()
        console.print(f"[green]✓ Success:[/green] {success_count}/{count}")
        if error_count > 0:
            console.print(f"[red]✗ Failed:[/red] {error_count}/{count}")
            raise typer.Exit(code=1)


def submit_service(
    service_ids: list[str] = typer.Argument(
        ..., help="Service ID(s) to submit (supports partial IDs, minimum 8 chars)"
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
):
    """Submit one or more services for review (draft → pending).

    Supports partial ID matching (minimum 8 characters, like git).

    Examples:
        # Submit specific service (full ID)
        usvc services submit 297040cd-c676-48d7-9a06-9b2a1d713496

        # Submit with partial ID (first 8+ chars)
        usvc services submit 297040cd

        # Submit multiple services
        usvc services submit 297040cd 112b499d

        # Skip confirmation
        usvc services submit 297040cd --yes
    """
    count = len(service_ids)
    console.print(f"[cyan]Submitting {count} service(s) for review...[/cyan]\n")
    for sid in service_ids:
        console.print(f"  • {sid}")
    console.print()

    if not yes:
        confirm = typer.confirm(f"Submit {count} service(s) for admin review?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(code=0)

    async def _submit_all():
        unpublisher = ServiceDataUnpublisher()
        results = []
        for service_id in service_ids:
            try:
                result = await unpublisher.update_service_status(service_id, status="pending")
                results.append((service_id, result, None))
            except Exception as e:
                results.append((service_id, None, str(e)))
        return results

    results = asyncio.run(_submit_all())

    # Display results
    success_count = 0
    error_count = 0

    for service_id, result, error in results:
        if error:
            console.print(f"[red]✗ {service_id}:[/red] {error}")
            error_count += 1
        else:
            console.print(f"[green]✓ {service_id}:[/green] Submitted for review")
            success_count += 1

    # Summary
    if count > 1:
        console.print()
        console.print(f"[green]✓ Success:[/green] {success_count}/{count}")
        if error_count > 0:
            console.print(f"[red]✗ Failed:[/red] {error_count}/{count}")
            raise typer.Exit(code=1)


def withdraw_service(
    service_ids: list[str] = typer.Argument(
        ..., help="Service ID(s) to withdraw (supports partial IDs, minimum 8 chars)"
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
):
    """Withdraw one or more services back to draft (pending/rejected → draft).

    Use this to:
    - Withdraw a pending submission before admin reviews it
    - Acknowledge a rejection and prepare for edits

    The service returns to draft status. Re-submit with 'usvc services submit'
    after making any changes.

    Supports partial ID matching (minimum 8 characters, like git).

    Examples:
        # Withdraw specific service
        usvc services withdraw 297040cd

        # Withdraw multiple services
        usvc services withdraw 297040cd 112b499d

        # Skip confirmation
        usvc services withdraw 297040cd --yes
    """
    count = len(service_ids)
    console.print(f"[cyan]Withdrawing {count} service(s) to draft...[/cyan]\n")
    for sid in service_ids:
        console.print(f"  • {sid}")
    console.print()

    if not yes:
        confirm = typer.confirm(f"Withdraw {count} service(s) to draft status?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(code=0)

    async def _withdraw_all():
        unpublisher = ServiceDataUnpublisher()
        results = []
        for service_id in service_ids:
            try:
                result = await unpublisher.update_service_status(service_id, status="draft")
                results.append((service_id, result, None))
            except Exception as e:
                results.append((service_id, None, str(e)))
        return results

    results = asyncio.run(_withdraw_all())

    # Display results
    success_count = 0
    error_count = 0

    for service_id, result, error in results:
        if error:
            console.print(f"[red]✗ {service_id}:[/red] {error}")
            error_count += 1
        else:
            console.print(f"[green]✓ {service_id}:[/green] Withdrawn to draft")
            success_count += 1

    # Summary
    if count > 1:
        console.print()
        console.print(f"[green]✓ Success:[/green] {success_count}/{count}")
        if error_count > 0:
            console.print(f"[red]✗ Failed:[/red] {error_count}/{count}")
            raise typer.Exit(code=1)


def delete_service(
    service_ids: list[str] = typer.Argument(..., help="Service ID(s) to delete (supports partial IDs)"),
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
    """Permanently delete one or more services.

    This will remove the service(s) and all associated data from the backend.
    This action cannot be undone.

    Supports partial ID matching (minimum 8 characters, like git).

    Examples:
        # Dry-run to see what would be deleted
        usvc services delete 297040cd --dryrun

        # Delete single service (full or partial ID)
        usvc services delete 297040cd

        # Delete multiple services
        usvc services delete 297040cd def45678 ghi78901

        # Force delete without confirmation
        usvc services delete 297040cd def45678 --force --yes
    """
    count = len(service_ids)
    if count == 1:
        console.print(f"[cyan]Deleting service {service_ids[0]}...[/cyan]\n")
    else:
        console.print(f"[cyan]Deleting {count} services...[/cyan]\n")
        for sid in service_ids:
            console.print(f"  • {sid}")
        console.print()

    if not yes and not dryrun:
        if count == 1:
            confirm = typer.confirm(f"⚠️  Permanently delete service '{service_ids[0]}' and all associated data?")
        else:
            confirm = typer.confirm(f"⚠️  Permanently delete {count} services and all associated data?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(code=0)

    async def _delete_all():
        unpublisher = ServiceDataUnpublisher()
        results = []
        for service_id in service_ids:
            try:
                result = await unpublisher.delete_service(service_id, dryrun=dryrun, force=force)
                results.append((service_id, result, None))
            except Exception as e:
                results.append((service_id, None, str(e)))
        return results

    results = asyncio.run(_delete_all())

    # Display results
    success_count = 0
    error_count = 0

    for service_id, result, error in results:
        if error:
            console.print(f"[red]✗ {service_id}:[/red] {error}")
            error_count += 1
        elif dryrun:
            console.print(f"[yellow]? {service_id}:[/yellow] Would be deleted")
            success_count += 1
        else:
            console.print(f"[green]✓ {service_id}:[/green] Deleted")
            if result and result.get("cascade_deleted"):
                cascade = result["cascade_deleted"]
                if cascade.get("subscriptions"):
                    console.print(f"  [dim]→ Deleted {cascade['subscriptions']} subscription(s)[/dim]")
            success_count += 1

    # Summary
    if count > 1:
        console.print()
        if dryrun:
            console.print(f"[yellow]Dry-run mode: No actual deletion performed[/yellow]")
        console.print(f"[green]✓ Success:[/green] {success_count}/{count}")
        if error_count > 0:
            console.print(f"[red]✗ Failed:[/red] {error_count}/{count}")
            raise typer.Exit(code=1)
    elif dryrun:
        console.print(f"\n[yellow]Dry-run mode: No actual deletion performed[/yellow]")
