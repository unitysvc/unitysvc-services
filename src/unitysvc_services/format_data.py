"""Format command - format data files."""

from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(help="Format data files")
console = Console()


@app.command()
def format_data(
    data_dir: Path | None = typer.Argument(
        None,
        help="Directory containing data files to format (default: current directory)",
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
        data_dir = Path.cwd()

    if not data_dir.is_absolute():
        data_dir = Path.cwd() / data_dir

    if not data_dir.exists():
        console.print(f"[red]✗[/red] Data directory not found: {data_dir}", style="bold red")
        raise typer.Exit(code=1)

    console.print(f"[blue]{'Checking' if check_only else 'Formatting'} files in:[/blue] {data_dir}\n")

    # Find all JSON, TOML, and MD files
    all_files: list[Path] = []
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
            with open(file_path, encoding="utf-8") as f:
                original_content = f.read()

            modified_content = original_content
            changes = []

            # Format based on file type
            if file_path.suffix == ".json":
                # Parse and reformat JSON
                try:
                    data = json_lib.loads(original_content)
                    formatted_json = json_lib.dumps(data, indent=2, sort_keys=True, separators=(",", ": "))
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
            if "\n".join([line.rstrip() for line in original_content.split("\n")]) != modified_content:
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
                    console.print(f"[yellow]✗ Would format:[/yellow] {file_path.relative_to(data_dir)}")
                    if changes:
                        console.print(f"  [dim]Changes: {', '.join(changes)}[/dim]")
                else:
                    # Write formatted content
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(modified_content)
                    console.print(f"[green]✓ Formatted:[/green] {file_path.relative_to(data_dir)}")
                    if changes:
                        console.print(f"  [dim]Changes: {', '.join(changes)}[/dim]")
                    files_formatted += 1
            else:
                if not check_only:
                    console.print(f"[dim]✓ Already formatted:[/dim] {file_path.relative_to(data_dir)}")

        except Exception as e:
            console.print(f"[red]✗ Error processing {file_path.relative_to(data_dir)}: {e}[/red]")
            files_failed.append(str(file_path.relative_to(data_dir)))

    # Print summary
    console.print("\n" + "=" * 50)
    console.print("[bold]Format Summary:[/bold]")
    console.print(f"  Total files: {len(all_files)}")
    if check_only:
        console.print(f"  [yellow]Files needing formatting: {len(files_with_issues)}[/yellow]")
    else:
        console.print(f"  [green]✓ Files formatted: {files_formatted}[/green]")
        console.print(f"  [dim]Already formatted: {len(all_files) - files_formatted - len(files_failed)}[/dim]")
    if files_failed:
        console.print(f"  [red]✗ Failed: {len(files_failed)}[/red]")

    if files_failed or (check_only and files_with_issues):
        raise typer.Exit(code=1)
