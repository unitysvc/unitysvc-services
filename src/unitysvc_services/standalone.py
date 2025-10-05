"""Standalone commands - utility commands."""

import json
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

app = typer.Typer(help="Standalone utility commands")
console = Console()


@app.command()
def format_data(
    data_dir: Optional[Path] = typer.Argument(
        None,
        help="Directory containing data files to format (default: ./data or UNITYSVC_DATA_DIR env var)",
    ),
    check_only: bool = typer.Option(
        False,
        "--check",
        help="Check if files are formatted without modifying them",
    ),
):
    """
    Format data files (JSON, TOML, MD) to match pre-commit requirements.

    This command:
    - Formats JSON files with 2-space indentation
    - Removes trailing whitespace
    - Ensures files end with a newline
    - Validates TOML syntax
    """
    import json as json_lib

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

    console.print(
        f"[blue]{'Checking' if check_only else 'Formatting'} files in:[/blue] {data_dir}\n"
    )

    # Find all JSON, TOML, and MD files
    all_files = []
    for ext in ["json", "toml", "md"]:
        all_files.extend(data_dir.rglob(f"*.{ext}"))

    if not all_files:
        console.print("[yellow]No files found to format.[/yellow]")
        return

    console.print(f"[cyan]Found {len(all_files)} file(s) to process[/cyan]\n")

    files_formatted = 0
    files_with_issues = []
    files_failed = []

    for file_path in sorted(all_files):
        try:
            # Read file content
            with open(file_path, "r", encoding="utf-8") as f:
                original_content = f.read()

            modified_content = original_content
            changes = []

            # Format based on file type
            if file_path.suffix == ".json":
                # Parse and reformat JSON
                try:
                    data = json_lib.loads(original_content)
                    formatted_json = json_lib.dumps(
                        data, indent=2, sort_keys=True, separators=(",", ": ")
                    )
                    modified_content = formatted_json
                    if modified_content != original_content.rstrip("\n"):
                        changes.append("reformatted JSON")
                except json_lib.JSONDecodeError as e:
                    console.print(f"[red]✗[/red] Invalid JSON in {file_path}: {e}")
                    files_failed.append(str(file_path.relative_to(data_dir)))
                    continue

            # Remove trailing whitespace from each line
            lines = modified_content.split("\n")
            stripped_lines = [line.rstrip() for line in lines]
            modified_content = "\n".join(stripped_lines)
            if (
                "\n".join([line.rstrip() for line in original_content.split("\n")])
                != modified_content
            ):
                if "reformatted JSON" not in changes:
                    changes.append("removed trailing whitespace")

            # Ensure file ends with single newline
            if not modified_content.endswith("\n"):
                modified_content += "\n"
                changes.append("added end-of-file newline")
            elif modified_content.endswith("\n\n"):
                # Remove extra newlines at end
                modified_content = modified_content.rstrip("\n") + "\n"
                changes.append("fixed multiple end-of-file newlines")

            # Check if file was modified
            if modified_content != original_content:
                files_with_issues.append(str(file_path.relative_to(data_dir)))

                if check_only:
                    console.print(
                        f"[yellow]✗ Would format:[/yellow] {file_path.relative_to(data_dir)}"
                    )
                    if changes:
                        console.print(f"  [dim]Changes: {', '.join(changes)}[/dim]")
                else:
                    # Write formatted content
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(modified_content)
                    console.print(
                        f"[green]✓ Formatted:[/green] {file_path.relative_to(data_dir)}"
                    )
                    if changes:
                        console.print(f"  [dim]Changes: {', '.join(changes)}[/dim]")
                    files_formatted += 1
            else:
                if not check_only:
                    console.print(
                        f"[dim]✓ Already formatted:[/dim] {file_path.relative_to(data_dir)}"
                    )

        except Exception as e:
            console.print(
                f"[red]✗ Error processing {file_path.relative_to(data_dir)}: {e}[/red]"
            )
            files_failed.append(str(file_path.relative_to(data_dir)))

    # Print summary
    console.print("\n" + "=" * 50)
    console.print("[bold]Format Summary:[/bold]")
    console.print(f"  Total files: {len(all_files)}")
    if check_only:
        console.print(
            f"  [yellow]Files needing formatting: {len(files_with_issues)}[/yellow]"
        )
    else:
        console.print(f"  [green]✓ Files formatted: {files_formatted}[/green]")
        console.print(
            f"  [dim]Already formatted: {len(all_files) - files_formatted - len(files_failed)}[/dim]"
        )
    if files_failed:
        console.print(f"  [red]✗ Failed: {len(files_failed)}[/red]")

    if files_failed or (check_only and files_with_issues):
        raise typer.Exit(code=1)


@app.command()
def validate(
    data_dir: Optional[Path] = typer.Argument(
        None,
        help="Directory containing data files to validate (default: ./data or UNITYSVC_DATA_DIR env var)",
    ),
):
    """
    Validate data consistency in service and listing files.

    Checks:
    1. Service names are unique within each directory
    2. Listing files reference valid service names
    3. Multiple services in a directory require explicit service_name in listings
    """
    from unitysvc_services.publisher import ServiceDataPublisher

    # Determine data directory
    if data_dir is None:
        data_dir_str = os.environ.get("UNITYSVC_DATA_DIR")
        if data_dir_str:
            data_dir = Path(data_dir_str)
        else:
            data_dir = Path.cwd() / "data"

    if not data_dir.exists():
        console.print(f"[red]✗[/red] Data directory not found: {data_dir}")
        raise typer.Exit(1)

    console.print(f"[cyan]Validating data files in:[/cyan] {data_dir}")
    console.print()

    # Create publisher and run validation
    publisher = ServiceDataPublisher(base_url="", api_key="")
    validation_errors = publisher.validate_all_service_directories(data_dir)

    if validation_errors:
        console.print(
            f"[red]✗ Validation failed with {len(validation_errors)} error(s):[/red]"
        )
        console.print()
        for i, error in enumerate(validation_errors, 1):
            console.print(f"[red]{i}.[/red] {error}")
            console.print()
        raise typer.Exit(1)
    else:
        console.print("[green]✓ All data files are valid![/green]")


@app.command()
def populate(
    data_dir: Optional[Path] = typer.Argument(
        None,
        help="Directory containing provider data files (default: ./data or UNITYSVC_DATA_DIR env var)",
    ),
    provider_name: Optional[str] = typer.Option(
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
    import subprocess

    import tomli

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

    console.print(f"[blue]Scanning for provider configurations in:[/blue] {data_dir}\n")

    # Find all provider files
    provider_files = []
    for ext in ["toml", "json"]:
        provider_files.extend(data_dir.rglob(f"provider.{ext}"))

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
                    provider_config = tomli.load(f)
            else:
                with open(provider_file, "r") as f:
                    provider_config = json.load(f)

            provider_name_in_file = provider_config.get("name", "unknown")

            # Skip if provider filter is set and doesn't match
            if provider_name and provider_name_in_file != provider_name:
                console.print(
                    f"[dim]Skipping provider: {provider_name_in_file} (filter: {provider_name})[/dim]"
                )
                total_skipped += 1
                continue

            # Check if services_populator is configured
            services_populator = provider_config.get("services_populator")
            if not services_populator:
                console.print(
                    f"[yellow]⏭️  Skipping {provider_name_in_file}: No services_populator configured[/yellow]"
                )
                total_skipped += 1
                continue

            command = services_populator.get("command")
            if not command:
                console.print(
                    f"[yellow]⏭️  Skipping {provider_name_in_file}: No command specified in services_populator[/yellow]"
                )
                total_skipped += 1
                continue

            console.print(
                f"[bold cyan]Processing provider:[/bold cyan] {provider_name_in_file}"
            )

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
                console.print(f"[yellow]  [DRY-RUN] Would execute command[/yellow]\n")
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
                    console.print(
                        f"[green]✓[/green] Successfully populated services for {provider_name_in_file}\n"
                    )
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
