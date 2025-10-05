"""List command group - list local data files."""

import json
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="List data files in directory")
console = Console()


@app.command("providers")
def list_providers(
    data_dir: Optional[Path] = typer.Argument(
        None,
        help="Directory containing provider files (default: ./data or UNITYSVC_DATA_DIR env var)",
    ),
):
    """List all provider files found in the data directory."""
    # Set data directory
    if data_dir is None:
        data_dir_str = os.getenv("UNITYSVC_DATA_DIR")
        if data_dir_str:
            data_dir = Path(data_dir_str)
        else:
            data_dir = Path.cwd() / "data"

    if not data_dir.is_absolute():
        data_dir = Path.cwd() / data_dir

    if not data_dir.exists():
        console.print(
            f"[red]✗[/red] Data directory not found: {data_dir}", style="bold red"
        )
        raise typer.Exit(code=1)

    console.print(f"[blue]Searching for providers in:[/blue] {data_dir}\n")

    # Find provider files
    provider_files = []
    for ext in ["json", "toml"]:
        provider_files.extend(data_dir.rglob(f"provider.{ext}"))

    if not provider_files:
        console.print("[yellow]No provider files found.[/yellow]")
        return

    # Create table
    table = Table(title="Provider Files", show_lines=True)
    table.add_column("File", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Display Name", style="blue")

    for provider_file in sorted(provider_files):
        try:
            if provider_file.suffix == ".json":
                with open(provider_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                import tomli

                with open(provider_file, "rb") as f:
                    data = tomli.load(f)

            table.add_row(
                str(provider_file.relative_to(data_dir)),
                data.get("name", "N/A"),
                data.get("display_name", "N/A"),
            )
        except Exception as e:
            table.add_row(
                str(provider_file.relative_to(data_dir)),
                f"[red]Error: {e}[/red]",
                "",
            )

    console.print(table)
    console.print(f"\n[green]Total:[/green] {len(provider_files)} provider file(s)")


@app.command("sellers")
def list_sellers(
    data_dir: Optional[Path] = typer.Argument(
        None,
        help="Directory containing seller files (default: ./data or UNITYSVC_DATA_DIR env var)",
    ),
):
    """List all seller files found in the data directory."""
    # Set data directory
    if data_dir is None:
        data_dir_str = os.getenv("UNITYSVC_DATA_DIR")
        if data_dir_str:
            data_dir = Path(data_dir_str)
        else:
            data_dir = Path.cwd() / "data"

    if not data_dir.is_absolute():
        data_dir = Path.cwd() / data_dir

    if not data_dir.exists():
        console.print(
            f"[red]✗[/red] Data directory not found: {data_dir}", style="bold red"
        )
        raise typer.Exit(code=1)

    console.print(f"[blue]Searching for sellers in:[/blue] {data_dir}\n")

    # Find seller files
    seller_files = []
    for ext in ["json", "toml"]:
        seller_files.extend(data_dir.rglob(f"seller.{ext}"))

    if not seller_files:
        console.print("[yellow]No seller files found.[/yellow]")
        return

    # Create table
    table = Table(title="Seller Files", show_lines=True)
    table.add_column("File", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Display Name", style="blue")

    for seller_file in sorted(seller_files):
        try:
            if seller_file.suffix == ".json":
                with open(seller_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                import tomli

                with open(seller_file, "rb") as f:
                    data = tomli.load(f)

            table.add_row(
                str(seller_file.relative_to(data_dir)),
                data.get("name", "N/A"),
                data.get("display_name", "N/A"),
            )
        except Exception as e:
            table.add_row(
                str(seller_file.relative_to(data_dir)),
                f"[red]Error: {e}[/red]",
                "",
            )

    console.print(table)
    console.print(f"\n[green]Total:[/green] {len(seller_files)} seller file(s)")


@app.command("offerings")
def list_offerings(
    data_dir: Optional[Path] = typer.Argument(
        None,
        help="Directory containing service files (default: ./data or UNITYSVC_DATA_DIR env var)",
    ),
):
    """List all service offering files found in the data directory."""
    # Set data directory
    if data_dir is None:
        data_dir_str = os.getenv("UNITYSVC_DATA_DIR")
        if data_dir_str:
            data_dir = Path(data_dir_str)
        else:
            data_dir = Path.cwd() / "data"

    if not data_dir.is_absolute():
        data_dir = Path.cwd() / data_dir

    if not data_dir.exists():
        console.print(
            f"[red]✗[/red] Data directory not found: {data_dir}", style="bold red"
        )
        raise typer.Exit(code=1)

    console.print(f"[blue]Searching for service offerings in:[/blue] {data_dir}\n")

    # Find service files with schema service_v1
    service_files = []
    for ext in ["json", "toml"]:
        for file_path in data_dir.rglob(f"*.{ext}"):
            try:
                if file_path.suffix == ".json":
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    import tomli

                    with open(file_path, "rb") as f:
                        data = tomli.load(f)

                if data.get("schema") == "service_v1":
                    service_files.append((file_path, data))
            except Exception:
                continue

    if not service_files:
        console.print("[yellow]No service offering files found.[/yellow]")
        return

    # Create table
    table = Table(title="Service Offering Files", show_lines=True)
    table.add_column("File", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Display Name", style="blue")
    table.add_column("Status", style="magenta")

    for service_file, data in sorted(service_files, key=lambda x: x[0]):
        table.add_row(
            str(service_file.relative_to(data_dir)),
            data.get("name", "N/A"),
            data.get("display_name", "N/A"),
            data.get("upstream_status", "N/A"),
        )

    console.print(table)
    console.print(
        f"\n[green]Total:[/green] {len(service_files)} service offering file(s)"
    )


@app.command("listings")
def list_listings(
    data_dir: Optional[Path] = typer.Argument(
        None,
        help="Directory containing listing files (default: ./data or UNITYSVC_DATA_DIR env var)",
    ),
):
    """List all service listing files found in the data directory."""
    # Set data directory
    if data_dir is None:
        data_dir_str = os.getenv("UNITYSVC_DATA_DIR")
        if data_dir_str:
            data_dir = Path(data_dir_str)
        else:
            data_dir = Path.cwd() / "data"

    if not data_dir.is_absolute():
        data_dir = Path.cwd() / data_dir

    if not data_dir.exists():
        console.print(
            f"[red]✗[/red] Data directory not found: {data_dir}", style="bold red"
        )
        raise typer.Exit(code=1)

    console.print(f"[blue]Searching for service listings in:[/blue] {data_dir}\n")

    # Find listing files with schema listing_v1
    listing_files = []
    for ext in ["json", "toml"]:
        for file_path in data_dir.rglob(f"*.{ext}"):
            try:
                if file_path.suffix == ".json":
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    import tomli

                    with open(file_path, "rb") as f:
                        data = tomli.load(f)

                if data.get("schema") == "listing_v1":
                    listing_files.append((file_path, data))
            except Exception:
                continue

    if not listing_files:
        console.print("[yellow]No service listing files found.[/yellow]")
        return

    # Create table
    table = Table(title="Service Listing Files", show_lines=True)
    table.add_column("File", style="cyan")
    table.add_column("Seller", style="green")
    table.add_column("Status", style="magenta")

    for listing_file, data in sorted(listing_files, key=lambda x: x[0]):
        table.add_row(
            str(listing_file.relative_to(data_dir)),
            data.get("seller_name", "N/A"),
            data.get("listing_status", "N/A"),
        )

    console.print(table)
    console.print(
        f"\n[green]Total:[/green] {len(listing_files)} service listing file(s)"
    )
