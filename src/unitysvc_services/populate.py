"""Populate command - populate services by executing provider scripts."""

import json
import os
import subprocess
import tomllib
from pathlib import Path

import typer
from rich.console import Console

from .utils import find_files_by_schema

app = typer.Typer(help="Populate services")
console = Console()


@app.command()
def populate(
    data_dir: Path | None = typer.Argument(
        None,
        help="Directory containing provider data files (default: current directory)",
    ),
    provider_name: str | None = typer.Option(
        None,
        "--provider",
        "-p",
        help="Only populate services for a specific provider",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be executed without actually running commands",
    ),
):
    """
    Populate services by executing provider-specific update scripts.

    This command scans provider files for 'services_populator' configuration and executes
    the specified commands with environment variables from 'provider_access_info'.
    """
    # Set data directory
    if data_dir is None:
        data_dir = Path.cwd()

    if not data_dir.is_absolute():
        data_dir = Path.cwd() / data_dir

    if not data_dir.exists():
        console.print(f"[red]✗[/red] Data directory not found: {data_dir}", style="bold red")
        raise typer.Exit(code=1)

    console.print(f"[blue]Scanning for provider configurations in:[/blue] {data_dir}\n")

    # Find all provider files by schema
    provider_results = find_files_by_schema(data_dir, "provider_v1")
    provider_files = [file_path for file_path, _, _ in provider_results]

    if not provider_files:
        console.print("[yellow]No provider files found.[/yellow]")
        raise typer.Exit(code=0)

    console.print(f"[cyan]Found {len(provider_files)} provider file(s)[/cyan]\n")

    # Process each provider
    total_executed = 0
    total_skipped = 0
    total_failed = 0

    for provider_file in provider_files:
        try:
            # Load provider configuration
            if provider_file.suffix == ".toml":
                with open(provider_file, "rb") as f:
                    provider_config = tomllib.load(f)
            else:
                with open(provider_file) as f:
                    provider_config = json.load(f)

            provider_name_in_file = provider_config.get("name", "unknown")

            # Skip if provider filter is set and doesn't match
            if provider_name and provider_name_in_file != provider_name:
                console.print(f"[dim]Skipping provider: {provider_name_in_file} (filter: {provider_name})[/dim]")
                total_skipped += 1
                continue

            # Check if services_populator is configured
            services_populator = provider_config.get("services_populator")
            if not services_populator:
                console.print(f"[yellow]⏭️  Skipping {provider_name_in_file}: No services_populator configured[/yellow]")
                total_skipped += 1
                continue

            command = services_populator.get("command")
            if not command:
                console.print(
                    f"[yellow]⏭️  Skipping {provider_name_in_file}: No command specified in services_populator[/yellow]"
                )
                total_skipped += 1
                continue

            console.print(f"[bold cyan]Processing provider:[/bold cyan] {provider_name_in_file}")

            # Prepare environment variables from provider_access_info
            env = os.environ.copy()
            provider_access_info = provider_config.get("provider_access_info", {})
            if provider_access_info:
                for key, value in provider_access_info.items():
                    env[key] = str(value)
                console.print(
                    f"[dim]  Set {len(provider_access_info)} environment variable(s) from provider_access_info[/dim]"
                )

            # Get the provider directory (parent of provider file)
            provider_dir = provider_file.parent

            # Build command - handle both string and list formats
            if isinstance(command, str):
                cmd_parts = command.split()
            else:
                cmd_parts = command

            # Resolve script path relative to provider directory
            script_path = provider_dir / cmd_parts[0]
            if script_path.exists():
                cmd_parts[0] = str(script_path)

            full_command = ["python3"] + cmd_parts

            console.print(f"[blue]  Command:[/blue] {' '.join(full_command)}")
            console.print(f"[blue]  Working directory:[/blue] {provider_dir}")

            if dry_run:
                console.print("[yellow]  [DRY-RUN] Would execute command[/yellow]\n")
                total_skipped += 1
                continue

            # Execute the command
            try:
                result = subprocess.run(
                    full_command,
                    cwd=provider_dir,
                    env=env,
                    capture_output=False,
                    text=True,
                )

                if result.returncode == 0:
                    console.print(f"[green]✓[/green] Successfully populated services for {provider_name_in_file}\n")
                    total_executed += 1
                else:
                    console.print(
                        f"[red]✗[/red] Command failed for {provider_name_in_file} (exit code: {result.returncode})\n",
                        style="bold red",
                    )
                    total_failed += 1

            except subprocess.SubprocessError as e:
                console.print(
                    f"[red]✗[/red] Failed to execute command for {provider_name_in_file}: {e}\n",
                    style="bold red",
                )
                total_failed += 1

        except Exception as e:
            console.print(
                f"[red]✗[/red] Error processing {provider_file}: {e}\n",
                style="bold red",
            )
            total_failed += 1

    # Print summary
    console.print("\n" + "=" * 50)
    console.print("[bold]Populate Services Summary:[/bold]")
    console.print(f"  Total providers found: {len(provider_files)}")
    console.print(f"  [green]✓ Successfully executed: {total_executed}[/green]")
    console.print(f"  [yellow]⏭️  Skipped: {total_skipped}[/yellow]")
    console.print(f"  [red]✗ Failed: {total_failed}[/red]")

    if total_failed > 0:
        raise typer.Exit(code=1)
