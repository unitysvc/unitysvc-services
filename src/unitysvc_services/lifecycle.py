"""Service lifecycle module for managing service status on UnitySVC backend."""

import asyncio
import json
from typing import Any

import typer
from rich.console import Console

from .api import UnitySvcAPI

console = Console()


async def fetch_service_ids_by_status(
    statuses: list[str],
    provider: str | None = None,
) -> list[str]:
    """Fetch all service IDs matching the given status(es).

    Args:
        statuses: List of status values to filter by (e.g., ["draft"], ["pending", "rejected"])
        provider: Optional provider name to filter by (case-insensitive partial match)

    Returns:
        List of service IDs matching any of the given statuses (and provider if specified)
    """
    api = UnitySvcAPI()
    all_ids: list[str] = []
    provider_lower = provider.lower() if provider else None

    for status in statuses:
        try:
            # Fetch with high limit to get all services
            services = await api.get("/seller/services", params={"status": status, "limit": 1000})
            data = services.get("data", services) if isinstance(services, dict) else services
            for svc in data:
                if svc.get("id"):
                    if provider_lower:
                        svc_provider = svc.get("provider_name", "")
                        if provider_lower not in svc_provider.lower():
                            continue
                    all_ids.append(svc["id"])
        except Exception:
            # If a status query fails, continue with others
            pass

    return all_ids


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
        run_tests: bool = True,
    ) -> dict[str, Any]:
        """Update a service's status.

        Args:
            service_id: UUID of the service to update
            status: New status (e.g., "deprecated", "active", "suspended", "pending", "draft")
            run_tests: Whether to trigger server-side tests (default True).
                Set to False to change status without running tests.

        Returns:
            Response from backend with update details

        Raises:
            httpx.HTTPStatusError: If update fails (404, 403, etc.)
        """
        data: dict[str, Any] = {"status": status}
        if not run_tests:
            data["run_tests"] = False
        return await self.patch(f"/seller/services/{service_id}", json_data=data)

    async def dedup_services(self) -> dict[str, Any]:
        """Remove duplicate draft services.

        Finds draft services that have identical content (provider_id, offering_id,
        listing_id) to another non-deprecated service and removes them.

        Returns:
            Response with deleted services info and counts

        Raises:
            httpx.HTTPStatusError: If dedup fails
        """
        return await self.post("/seller/services/dedup")


def deprecate_service(
    service_ids: list[str] = typer.Argument(None, help="Service ID(s) to deprecate (supports partial IDs)"),
    all_active: bool = typer.Option(
        False,
        "--all",
        help="Deprecate all active services",
    ),
    provider: str = typer.Option(
        None,
        "--provider",
        help="Filter by provider name when using --all (case-insensitive partial match)",
    ),
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

        # Deprecate all active services
        usvc services deprecate --all

        # Deprecate all active services for a specific provider
        usvc services deprecate --all --provider "My Company"

        # Skip confirmation
        usvc services deprecate 297040cd --yes
    """
    # Validate --provider usage
    if provider and not all_active:
        console.print("[red]Error:[/red] --provider can only be used with --all flag")
        raise typer.Exit(code=1)

    # Handle --all flag
    if all_active:
        if service_ids:
            console.print("[red]Error:[/red] Cannot specify both service IDs and --all flag")
            raise typer.Exit(code=1)
        msg = "[cyan]Fetching all active services"
        if provider:
            msg += f" for provider '{provider}'"
        msg += "...[/cyan]"
        console.print(msg)
        service_ids = asyncio.run(fetch_service_ids_by_status(["active"], provider=provider))
        if not service_ids:
            console.print("[yellow]No active services found.[/yellow]")
            raise typer.Exit(code=0)
        console.print(f"[green]Found {len(service_ids)} active service(s)[/green]\n")
    elif not service_ids:
        console.print("[red]Error:[/red] Either provide service IDs or use --all flag")
        raise typer.Exit(code=1)

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
        None, help="Service ID(s) to submit (supports partial IDs, minimum 8 chars)"
    ),
    all_drafts: bool = typer.Option(
        False,
        "--all",
        help="Submit all draft and rejected services",
    ),
    provider: str = typer.Option(
        None,
        "--provider",
        help="Filter by provider name when using --all (case-insensitive partial match)",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
    no_test: bool = typer.Option(
        False,
        "--no-test",
        help="Submit without running server-side tests. Use this to temporarily "
        "set services to 'pending' so they are testable by external scripts "
        "(e.g. 'usvc services run-tests'). Withdraw with 'usvc services withdraw' "
        "when done to return services to draft.",
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

        # Submit all draft services
        usvc services submit --all

        # Submit all draft services for a specific provider
        usvc services submit --all --provider "My Company"

        # Skip confirmation
        usvc services submit 297040cd --yes

        # Submit without tests (for external testing, withdraw when done)
        usvc services submit 297040cd --no-test
        usvc services run-tests 297040cd    # run external tests
        usvc services withdraw 297040cd     # return to draft
    """
    # Validate --provider usage
    if provider and not all_drafts:
        console.print("[red]Error:[/red] --provider can only be used with --all flag")
        raise typer.Exit(code=1)

    # Handle --all flag
    if all_drafts:
        if service_ids:
            console.print("[red]Error:[/red] Cannot specify both service IDs and --all flag")
            raise typer.Exit(code=1)
        msg = "[cyan]Fetching all draft and rejected services"
        if provider:
            msg += f" for provider '{provider}'"
        msg += "...[/cyan]"
        console.print(msg)
        service_ids = asyncio.run(fetch_service_ids_by_status(["draft", "rejected"], provider=provider))
        if not service_ids:
            console.print("[yellow]No draft or rejected services found.[/yellow]")
            raise typer.Exit(code=0)
        console.print(f"[green]Found {len(service_ids)} service(s)[/green]\n")
    elif not service_ids:
        console.print("[red]Error:[/red] Either provide service IDs or use --all flag")
        raise typer.Exit(code=1)

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
                result = await api.update_service_status(
                    service_id, status="pending", run_tests=not no_test
                )
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
        None, help="Service ID(s) to withdraw (supports partial IDs, minimum 8 chars)"
    ),
    all_pending: bool = typer.Option(
        False,
        "--all",
        help="Withdraw all pending and rejected services",
    ),
    provider: str = typer.Option(
        None,
        "--provider",
        help="Filter by provider name when using --all (case-insensitive partial match)",
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

        # Withdraw all pending/rejected services
        usvc services withdraw --all

        # Withdraw all pending/rejected services for a specific provider
        usvc services withdraw --all --provider "My Company"

        # Skip confirmation
        usvc services withdraw 297040cd --yes
    """
    # Validate --provider usage
    if provider and not all_pending:
        console.print("[red]Error:[/red] --provider can only be used with --all flag")
        raise typer.Exit(code=1)

    # Handle --all flag
    if all_pending:
        if service_ids:
            console.print("[red]Error:[/red] Cannot specify both service IDs and --all flag")
            raise typer.Exit(code=1)
        msg = "[cyan]Fetching all pending and rejected services"
        if provider:
            msg += f" for provider '{provider}'"
        msg += "...[/cyan]"
        console.print(msg)
        service_ids = asyncio.run(fetch_service_ids_by_status(["pending", "rejected"], provider=provider))
        if not service_ids:
            console.print("[yellow]No pending or rejected services found.[/yellow]")
            raise typer.Exit(code=0)
        console.print(f"[green]Found {len(service_ids)} service(s)[/green]\n")
    elif not service_ids:
        console.print("[red]Error:[/red] Either provide service IDs or use --all flag")
        raise typer.Exit(code=1)

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


def dedup_services(
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
):
    """Remove duplicate draft services.

    Finds draft services that have identical content (provider_id, offering_id,
    listing_id) to another non-deprecated service and removes them.

    Duplicate drafts are identified when:
    - A draft has the same provider/offering/listing IDs as another active/pending/etc. service
    - Multiple drafts have the same provider/offering/listing IDs (only one is kept)

    Examples:
        # Check for and remove duplicate drafts
        usvc services dedup

        # Skip confirmation
        usvc services dedup --yes
    """
    console.print("[cyan]Checking for duplicate draft services...[/cyan]\n")

    if not yes:
        confirm = typer.confirm("Remove duplicate draft services?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(code=0)

    async def _dedup():
        api = ServiceLifecycleAPI()
        return await api.dedup_services()

    try:
        result = asyncio.run(_dedup())
    except Exception as e:
        console.print(f"[red]✗ Dedup failed:[/red] {e}")
        raise typer.Exit(code=1)

    deleted_count = result.get("deleted_count", 0)
    kept_count = result.get("kept_count", 0)
    total_drafts = result.get("total_drafts", 0)
    deleted = result.get("deleted", [])

    if deleted_count > 0:
        console.print(f"[green]✓ Removed {deleted_count} duplicate draft(s):[/green]")
        for item in deleted:
            console.print(f"  • {item.get('id', 'unknown')}")
    else:
        console.print("[green]✓ No duplicate drafts found[/green]")

    console.print()
    console.print(f"[dim]Total drafts examined: {total_drafts}[/dim]")
    console.print(f"[dim]Drafts kept: {kept_count}[/dim]")
    console.print(f"[dim]Duplicates removed: {deleted_count}[/dim]")


def delete_service(
    service_ids: list[str] = typer.Argument(None, help="Service ID(s) to delete (supports partial IDs)"),
    all_deletable: bool = typer.Option(
        False,
        "--all",
        help="Delete all deletable services (draft, pending, testing, rejected, suspended, deprecated)",
    ),
    status: str = typer.Option(
        None,
        "--status",
        help="Filter by status when using --all (e.g., --all --status draft)",
    ),
    provider: str = typer.Option(
        None,
        "--provider",
        help="Filter by provider name when using --all (case-insensitive partial match)",
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

        # Delete all draft services
        usvc services delete --all --status draft

        # Delete all draft services for a specific provider
        usvc services delete --all --status draft --provider "My Company"

        # Delete all deletable services (use with caution!)
        usvc services delete --all

        # Force delete without confirmation
        usvc services delete 297040cd def45678 --force --yes
    """
    # Validate --provider and --status usage
    if provider and not all_deletable:
        console.print("[red]Error:[/red] --provider can only be used with --all flag")
        raise typer.Exit(code=1)

    # Handle --all flag
    if all_deletable:
        if service_ids:
            console.print("[red]Error:[/red] Cannot specify both service IDs and --all flag")
            raise typer.Exit(code=1)
        # Deletable statuses (not active - those require deprecation first)
        deletable_statuses = ["draft", "pending", "testing", "rejected", "suspended", "deprecated"]
        if status:
            if status not in deletable_statuses:
                valid = ", ".join(deletable_statuses)
                console.print(f"[red]Error:[/red] Status '{status}' is not deletable. Use one of: {valid}")
                raise typer.Exit(code=1)
            deletable_statuses = [status]
        msg = f"[cyan]Fetching services with status: {', '.join(deletable_statuses)}"
        if provider:
            msg += f" for provider '{provider}'"
        msg += "...[/cyan]"
        console.print(msg)
        service_ids = asyncio.run(fetch_service_ids_by_status(deletable_statuses, provider=provider))
        if not service_ids:
            console.print("[yellow]No deletable services found.[/yellow]")
            raise typer.Exit(code=0)
        console.print(f"[green]Found {len(service_ids)} service(s)[/green]\n")
    elif not service_ids:
        console.print("[red]Error:[/red] Either provide service IDs or use --all flag")
        raise typer.Exit(code=1)

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


def update_service(
    service_id: str = typer.Argument(..., help="Service ID (supports partial IDs)"),
    set_routing_var: list[str] = typer.Option(
        None,
        "--set-routing-var",
        help="Set routing var(s): key=value or JSON object '{...}'; values are JSON-decoded when possible (repeatable)",
    ),
    remove_routing_var: list[str] = typer.Option(
        None,
        "--remove-routing-var",
        help="Remove a routing var by key (repeatable)",
    ),
    load_routing_vars: str = typer.Option(
        None,
        "--load-routing-vars",
        help="Merge routing vars from a JSON file; combines with --set-routing-var",
    ),
) -> None:
    """Update a live service (no approval needed).

    Routing vars let sellers change operational values within the boundaries
    the admin-approved template defines. All operations merge with existing
    vars — keys not mentioned are left unchanged.

    To batch-edit, dump current vars with show --format json, edit the file,
    and reload:

        usvc services show myservice --format json | jq '.routing_vars' > vars.json
        # edit vars.json
        usvc services update myservice --load-routing-vars vars.json

    Examples:
        usvc services update myservice --set-routing-var code1=clients/smith
        usvc services update myservice --set-routing-var k1=v1 --set-routing-var k2=v2
        usvc services update myservice --set-routing-var count=42
        usvc services update myservice --set-routing-var '{"region": "us-east", "users": {"alice": "admin"}}'
        usvc services update myservice --remove-routing-var code1
        usvc services update myservice --load-routing-vars vars.json
        usvc services update myservice --load-routing-vars vars.json --set-routing-var extra=val
    """
    set_dict: dict[str, Any] = {}
    remove_list: list[str] = list(remove_routing_var) if remove_routing_var else []

    # Parse --set-routing-var: try JSON object first, fall back to key=value.
    # JSON object: '{"k1": "v1", "k2": 42}' sets multiple keys at once.
    # key=value: value is JSON-decoded when possible, otherwise kept as string.
    if set_routing_var:
        for item in set_routing_var:
            try:
                parsed = json.loads(item)
                if isinstance(parsed, dict):
                    set_dict.update(parsed)
                    continue
            except (json.JSONDecodeError, ValueError):
                pass
            if "=" not in item:
                console.print(f"[red]Error:[/red] Invalid --set-routing-var format: '{item}' (expected key=value or JSON object)")
                raise typer.Exit(code=1)
            key, raw = item.split("=", 1)
            try:
                value = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                value = raw
            set_dict[key] = value

    # Load from JSON file
    if load_routing_vars:
        try:
            with open(load_routing_vars, encoding="utf-8") as f:
                loaded = json.load(f)
            if not isinstance(loaded, dict):
                console.print("[red]Error:[/red] JSON file must contain an object (dict)")
                raise typer.Exit(code=1)
            set_dict.update(loaded)
        except (OSError, json.JSONDecodeError) as e:
            console.print(f"[red]Error:[/red] Failed to load {load_routing_vars}: {e}")
            raise typer.Exit(code=1)

    if not set_dict and not remove_list:
        console.print("[yellow]Nothing to do:[/yellow] provide --set-routing-var, --remove-routing-var, or --load-routing-vars")
        raise typer.Exit(code=0)

    body: dict[str, Any] = {}
    if set_dict:
        body["set"] = set_dict
    if remove_list:
        body["remove"] = remove_list

    async def _update() -> dict[str, Any]:
        api = UnitySvcAPI()
        return await api.patch(f"/seller/services/{service_id}/routing-vars", json_data=body)

    try:
        result = asyncio.run(_update())
        console.print(f"[green]✓[/green] routing_vars updated for service {result.get('id', service_id)}")
        if result.get("routing_vars"):
            console.print(json.dumps(result["routing_vars"], indent=2))
        else:
            console.print("[dim](empty)[/dim]")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to update routing_vars: {e}")
        raise typer.Exit(code=1)
