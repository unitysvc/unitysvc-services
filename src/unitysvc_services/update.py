"""Update command group - update local data files."""

from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from .utils import find_file_by_schema_and_name, find_files_by_schema, write_data_file

app = typer.Typer(help="Update local data files")
console = Console()


@app.command("offering")
def update_offering(
    name: str = typer.Option(
        ...,
        "--name",
        "-n",
        help="Name of the service offering to update (matches 'name' field in service file)",
    ),
    status: str | None = typer.Option(
        None,
        "--status",
        "-s",
        help="New upstream_status (uploading, ready, deprecated)",
    ),
    display_name: str | None = typer.Option(
        None,
        "--display-name",
        help="New display name for the offering",
    ),
    description: str | None = typer.Option(
        None,
        "--description",
        help="New description for the offering",
    ),
    version: str | None = typer.Option(
        None,
        "--version",
        help="New version for the offering",
    ),
    data_dir: Path | None = typer.Option(
        None,
        "--data-dir",
        "-d",
        help="Directory containing data files (default: current directory)",
    ),
):
    """
    Update fields in a service offering's local data file.

    Searches for files with schema 'service_v1' by offering name and updates the specified fields.

    Allowed upstream_status values:
      - uploading: Service is being uploaded (not ready)
      - ready: Service is ready to be used
      - deprecated: Service is deprecated from upstream
    """
    # Validate status if provided
    if status:
        valid_statuses = ["uploading", "ready", "deprecated"]
        if status not in valid_statuses:
            console.print(
                f"[red]✗[/red] Invalid status: {status}",
                style="bold red",
            )
            console.print(f"[yellow]Allowed statuses:[/yellow] {', '.join(valid_statuses)}")
            raise typer.Exit(code=1)

    # Check if any update field is provided
    if not any([status, display_name, description, version]):
        console.print(
            (
                "[red]✗[/red] No fields to update. Provide at least one of: "
                "--status, --display-name, --description, --version"
            ),
            style="bold red",
        )
        raise typer.Exit(code=1)

    # Set data directory
    if data_dir is None:
        data_dir = Path.cwd()

    if not data_dir.is_absolute():
        data_dir = Path.cwd() / data_dir

    if not data_dir.exists():
        console.print(f"[red]✗[/red] Data directory not found: {data_dir}", style="bold red")
        raise typer.Exit(code=1)

    console.print(f"[blue]Searching for offering:[/blue] {name}")
    console.print(f"[blue]In directory:[/blue] {data_dir}\n")

    # Find the matching offering file
    result = find_file_by_schema_and_name(data_dir, "service_v1", "name", name)

    if not result:
        console.print(
            f"[red]✗[/red] No offering found with name: {name}",
            style="bold red",
        )
        raise typer.Exit(code=1)

    matching_file, matching_format, data = result

    # Update the fields
    try:
        updates: dict[str, tuple[Any, Any]] = {}  # field: (old_value, new_value)

        if status:
            updates["upstream_status"] = (data.get("upstream_status", "unknown"), status)
            data["upstream_status"] = status

        if display_name:
            updates["display_name"] = (data.get("display_name", ""), display_name)
            data["display_name"] = display_name

        if description:
            updates["description"] = (data.get("description", ""), description)
            data["description"] = description

        if version:
            updates["version"] = (data.get("version", ""), version)
            data["version"] = version

        # Write back in same format
        write_data_file(matching_file, data, matching_format)

        console.print("[green]✓[/green] Updated offering successfully!")
        console.print(f"[cyan]File:[/cyan] {matching_file.relative_to(data_dir)}")
        console.print(f"[cyan]Format:[/cyan] {matching_format.upper()}\n")

        for field, (old, new) in updates.items():
            console.print(f"[cyan]{field}:[/cyan]")
            if len(str(old)) > 60 or len(str(new)) > 60:
                console.print(f"  [dim]Old:[/dim] {str(old)[:60]}...")
                console.print(f"  [dim]New:[/dim] {str(new)[:60]}...")
            else:
                console.print(f"  [dim]Old:[/dim] {old}")
                console.print(f"  [dim]New:[/dim] {new}")

    except Exception as e:
        console.print(
            f"[red]✗[/red] Failed to update offering: {e}",
            style="bold red",
        )
        raise typer.Exit(code=1)


@app.command("listing")
def update_listing(
    service_name: str = typer.Option(
        ...,
        "--service-name",
        "-n",
        help="Name of the service (to search for listing files in service directory)",
    ),
    status: str | None = typer.Option(
        None,
        "--status",
        "-s",
        help=(
            "New listing_status (unknown, upstream_ready, downstream_ready, "
            "ready, in_service, upstream_deprecated, deprecated)"
        ),
    ),
    seller_name: str | None = typer.Option(
        None,
        "--seller",
        help="Seller name to filter listings (updates only matching seller's listing)",
    ),
    data_dir: Path | None = typer.Option(
        None,
        "--data-dir",
        "-d",
        help="Directory containing data files (default: current directory)",
    ),
):
    """
    Update fields in service listing(s) local data files.

    Searches for files with schema 'listing_v1' in the service directory and updates the specified fields.

    Allowed listing_status values:
      - unknown: Not yet determined
      - upstream_ready: Upstream is ready to be used
      - downstream_ready: Downstream is ready with proper routing, logging, and billing
      - ready: Operationally ready (with docs, metrics, and pricing)
      - in_service: Service is in service
      - upstream_deprecated: Service is deprecated from upstream
      - deprecated: Service is no longer offered to users
    """
    # Validate status if provided
    if status:
        valid_statuses = [
            "unknown",
            "upstream_ready",
            "downstream_ready",
            "ready",
            "in_service",
            "upstream_deprecated",
            "deprecated",
        ]
        if status not in valid_statuses:
            console.print(
                f"[red]✗[/red] Invalid status: {status}",
                style="bold red",
            )
            console.print(f"[yellow]Allowed statuses:[/yellow] {', '.join(valid_statuses)}")
            raise typer.Exit(code=1)

    # Check if any update field is provided
    if not status:
        console.print(
            "[red]✗[/red] No fields to update. Provide at least one of: --status",
            style="bold red",
        )
        raise typer.Exit(code=1)

    # Set data directory
    if data_dir is None:
        data_dir = Path.cwd()

    if not data_dir.is_absolute():
        data_dir = Path.cwd() / data_dir

    if not data_dir.exists():
        console.print(f"[red]✗[/red] Data directory not found: {data_dir}", style="bold red")
        raise typer.Exit(code=1)

    console.print(f"[blue]Searching for service:[/blue] {service_name}")
    console.print(f"[blue]In directory:[/blue] {data_dir}")
    if seller_name:
        console.print(f"[blue]Filtering by seller:[/blue] {seller_name}")
    console.print()

    # Build field filter
    field_filter = {}
    if seller_name:
        field_filter["seller_name"] = seller_name

    # Convert field_filter dict to tuple for caching
    field_filter_tuple = tuple(sorted(field_filter.items())) if field_filter else None

    # Find listing files matching criteria
    listing_files = find_files_by_schema(
        data_dir, "listing_v1", path_filter=service_name, field_filter=field_filter_tuple
    )

    if not listing_files:
        console.print(
            "[red]✗[/red] No listing files found matching criteria",
            style="bold red",
        )
        raise typer.Exit(code=1)

    # Update all matching listings
    updated_count = 0
    for listing_file, file_format, data in listing_files:
        try:
            old_status = data.get("listing_status", "unknown")
            if status:
                data["listing_status"] = status

            # Write back in same format
            write_data_file(listing_file, data, file_format)

            console.print(f"[green]✓[/green] Updated: {listing_file.relative_to(data_dir)}")
            console.print(f"  [dim]Seller: {data.get('seller_name', 'N/A')}[/dim]")
            console.print(f"  [dim]Format: {file_format.upper()}[/dim]")
            if status:
                console.print(f"  [dim]Old status: {old_status} → New status: {status}[/dim]")
            console.print()
            updated_count += 1

        except Exception as e:
            console.print(
                f"[red]✗[/red] Failed to update {listing_file.relative_to(data_dir)}: {e}",
                style="bold red",
            )

    if updated_count > 0:
        console.print(f"[green]✓[/green] Successfully updated {updated_count} listing(s)")
    else:
        console.print("[red]✗[/red] No listings were updated", style="bold red")
        raise typer.Exit(code=1)
