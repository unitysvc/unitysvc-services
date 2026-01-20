"""Service lifecycle module for managing service status on UnitySVC backend."""

import asyncio
from typing import Any

import typer
from rich.console import Console

from .api import UnitySvcAPI

console = Console()


class ServiceLifecycleAPI(UnitySvcAPI):
    """Manages service lifecycle operations on UnitySVC backend.

    Inherits base HTTP client with curl fallback from UnitySvcAPI.
    Provides methods for updating service status and deletion.
    """

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
            status: New status (e.g., "deprecated", "active", "suspended", "pending", "draft")

        Returns:
            Response from backend with update details

        Raises:
            httpx.HTTPStatusError: If update fails (404, 403, etc.)
        """
        return await self.patch(f"/seller/services/{service_id}", json_data={"status": status})


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
        api = ServiceLifecycleAPI()
        results = []
        for service_id in service_ids:
            try:
                result = await api.update_service_status(service_id, status="deprecated")
                results.append((service_id, result, None))
            except Exception as e:
                results.append((service_id, None, str(e)))
        return results

    results = asyncio.run(_deprecate_all())

    # Display results
    success_count = 0
    error_count = 0

    for service_id, _result, error in results:
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
        api = ServiceLifecycleAPI()
        results = []
        for service_id in service_ids:
            try:
                result = await api.update_service_status(service_id, status="pending")
                results.append((service_id, result, None))
            except Exception as e:
                results.append((service_id, None, str(e)))
        return results

    results = asyncio.run(_submit_all())

    # Display results
    success_count = 0
    error_count = 0

    for service_id, _result, error in results:
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
        api = ServiceLifecycleAPI()
        results = []
        for service_id in service_ids:
            try:
                result = await api.update_service_status(service_id, status="draft")
                results.append((service_id, result, None))
            except Exception as e:
                results.append((service_id, None, str(e)))
        return results

    results = asyncio.run(_withdraw_all())

    # Display results
    success_count = 0
    error_count = 0

    for service_id, _result, error in results:
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
        api = ServiceLifecycleAPI()
        results = []
        for service_id in service_ids:
            try:
                result = await api.delete_service(service_id, dryrun=dryrun, force=force)
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
            console.print("[yellow]Dry-run mode: No actual deletion performed[/yellow]")
        console.print(f"[green]✓ Success:[/green] {success_count}/{count}")
        if error_count > 0:
            console.print(f"[red]✗ Failed:[/red] {error_count}/{count}")
            raise typer.Exit(code=1)
    elif dryrun:
        console.print("\n[yellow]Dry-run mode: No actual deletion performed[/yellow]")
