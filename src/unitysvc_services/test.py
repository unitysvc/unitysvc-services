"""Test command group - test code examples with upstream credentials."""

import fnmatch
import json
import os
import subprocess
import tempfile
import tomllib
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from .models.base import DocumentCategoryEnum
from .utils import find_files_by_schema, render_template_file

app = typer.Typer(help="Test code examples with upstream credentials")
console = Console()


def extract_service_directory_name(listing_file: Path) -> str | None:
    """Extract service directory name from listing file path.

    The service directory is the directory immediately after "services" directory.
    For example: .../services/llama-3-1-405b-instruct/listing-svcreseller.json
    Returns: "llama-3-1-405b-instruct"

    Args:
        listing_file: Path to the listing file

    Returns:
        Service directory name or None if not found
    """
    parts = listing_file.parts
    try:
        services_idx = parts.index("services")
        # Service directory is immediately after "services"
        if services_idx + 1 < len(parts):
            return parts[services_idx + 1]
    except (ValueError, IndexError):
        pass
    return None


def extract_code_examples_from_listing(listing_data: dict[str, Any], listing_file: Path) -> list[dict[str, Any]]:
    """Extract code example documents from a listing file.

    Args:
        listing_data: Parsed listing data
        listing_file: Path to the listing file for resolving relative paths

    Returns:
        List of code example documents with resolved file paths
    """
    code_examples = []

    # Get service name for display - use directory name as fallback
    service_name = listing_data.get("service_name")
    if not service_name:
        # Use service directory name as fallback
        service_name = extract_service_directory_name(listing_file) or "unknown"

    # Check user_access_interfaces
    interfaces = listing_data.get("user_access_interfaces", [])

    for interface in interfaces:
        documents = interface.get("documents", [])

        for doc in documents:
            # Match both "code_example" and "code_examples"
            category = doc.get("category", "")
            if category == DocumentCategoryEnum.code_examples:
                # Resolve file path relative to listing file
                file_path = doc.get("file_path")
                if file_path:
                    # Resolve relative path
                    absolute_path = (listing_file.parent / file_path).resolve()

                    code_example = {
                        "service_name": service_name,
                        "title": doc.get("title", "Untitled"),
                        "mime_type": doc.get("mime_type", "python"),
                        "file_path": str(absolute_path),
                        "listing_data": listing_data,  # Full listing data for templates
                        "listing_file": listing_file,  # Path to listing file for loading related data
                    }
                    code_examples.append(code_example)

    return code_examples


def load_related_data(listing_file: Path) -> dict[str, Any]:
    """Load offering, provider, and seller data related to a listing file.

    Args:
        listing_file: Path to the listing file

    Returns:
        Dictionary with offering, provider, and seller data (may be empty dicts if not found)
    """
    result: dict[str, Any] = {
        "offering": {},
        "provider": {},
        "seller": {},
    }

    try:
        # Find offering file (service.json in same directory as listing)
        offering_file = listing_file.parent / "service.json"
        if offering_file.exists():
            with open(offering_file) as f:
                result["offering"] = json.load(f)

        # Find provider file using find_files_by_schema
        # Structure: data/{provider}/services/{service}/listing.json
        # Go up to provider directory (2 levels up from listing)
        provider_dir = listing_file.parent.parent.parent
        provider_results = find_files_by_schema(provider_dir, "provider_v1")
        if provider_results:
            # Unpack tuple: (file_path, format, data)
            # Data is already loaded by find_files_by_schema
            _file_path, _format, provider_data = provider_results[0]
            result["provider"] = provider_data

        # Find seller file using find_files_by_schema
        # Go up to data directory (3 levels up from listing)
        data_dir = listing_file.parent.parent.parent.parent
        seller_results = find_files_by_schema(data_dir, "seller_v1")
        if seller_results:
            # Unpack tuple: (file_path, format, data)
            # Data is already loaded by find_files_by_schema
            _file_path, _format, seller_data = seller_results[0]
            result["seller"] = seller_data

    except Exception as e:
        console.print(f"[yellow]Warning: Failed to load some related data: {e}[/yellow]")

    return result


def load_provider_credentials(provider_file: Path) -> dict[str, str] | None:
    """Load API key and endpoint from provider file.

    Args:
        provider_file: Path to provider.toml or provider.json

    Returns:
        Dictionary with api_key and api_endpoint, or None if not found
    """
    try:
        if provider_file.suffix == ".toml":
            with open(provider_file, "rb") as f:
                provider_data = tomllib.load(f)
        else:
            with open(provider_file) as f:
                provider_data = json.load(f)

        access_info = provider_data.get("provider_access_info", {})
        api_key = access_info.get("api_key") or access_info.get("FIREWORKS_API_KEY")
        api_endpoint = access_info.get("api_endpoint") or access_info.get("FIREWORKS_API_BASE_URL")

        if api_key and api_endpoint:
            return {
                "api_key": str(api_key),
                "api_endpoint": str(api_endpoint),
            }
    except Exception as e:
        console.print(f"[yellow]Warning: Failed to load provider credentials: {e}[/yellow]")

    return None


def execute_code_example(code_example: dict[str, Any], credentials: dict[str, str]) -> dict[str, Any]:
    """Execute a code example script with upstream credentials.

    Args:
        code_example: Code example metadata with file_path and listing_data
        credentials: Dictionary with api_key and api_endpoint

    Returns:
        Result dictionary with success, exit_code, stdout, stderr
    """
    result: dict[str, Any] = {
        "success": False,
        "exit_code": None,
        "error": None,
        "stdout": None,
        "stderr": None,
    }

    file_path = code_example.get("file_path")
    if not file_path or not Path(file_path).exists():
        result["error"] = f"File not found: {file_path}"
        return result

    try:
        # Get original file extension
        original_path = Path(file_path)

        # Load related data for template rendering (if needed)
        listing_data = code_example.get("listing_data", {})
        listing_file = code_example.get("listing_file")
        related_data = {}
        if listing_file:
            related_data = load_related_data(Path(listing_file))

        # Render template if applicable (handles both .j2 and non-.j2 files)
        try:
            file_content, actual_filename = render_template_file(
                original_path,
                listing=listing_data,
                offering=related_data.get("offering", {}),
                provider=related_data.get("provider", {}),
                seller=related_data.get("seller", {}),
            )
        except Exception as e:
            result["error"] = f"Template rendering failed: {str(e)}"
            return result

        # Get file suffix from the actual filename (after .j2 stripping if applicable)
        file_suffix = Path(actual_filename).suffix or ".txt"

        # Parse shebang to get interpreter
        lines = file_content.split("\n")
        interpreter_cmd = None

        if lines and lines[0].startswith("#!"):
            shebang = lines[0][2:].strip()
            if "/env " in shebang:
                interpreter_cmd = shebang.split("/env ", 1)[1].strip().split()[0]
            else:
                interpreter_cmd = shebang.split("/")[-1].split()[0]

        if not interpreter_cmd:
            interpreter_cmd = "python"

        # Prepare environment variables
        env = os.environ.copy()
        env["API_KEY"] = credentials["api_key"]
        env["API_ENDPOINT"] = credentials["api_endpoint"]

        # Write script to temporary file with original extension
        with tempfile.NamedTemporaryFile(mode="w", suffix=file_suffix, delete=False) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        try:
            # Execute the script
            process = subprocess.run(
                [interpreter_cmd, temp_file_path],
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )

            result["exit_code"] = process.returncode
            result["stdout"] = process.stdout
            result["stderr"] = process.stderr

            if process.returncode == 0:
                result["success"] = True
            else:
                result["error"] = f"Script exited with code {process.returncode}. stderr: {process.stderr[:200]}"

        finally:
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass

    except subprocess.TimeoutExpired:
        result["error"] = "Script execution timeout (30 seconds)"
    except FileNotFoundError:
        result["error"] = f"Interpreter '{interpreter_cmd}' not found"
    except Exception as e:
        result["error"] = f"Error executing script: {str(e)}"

    return result


@app.command("list")
def list_code_examples(
    data_dir: Path | None = typer.Argument(
        None,
        help="Directory containing provider data files (default: current directory)",
    ),
    provider_name: str | None = typer.Option(
        None,
        "--provider",
        "-p",
        help="Only list code examples for a specific provider",
    ),
    services: str | None = typer.Option(
        None,
        "--services",
        "-s",
        help="Comma-separated list of service patterns (supports wildcards, e.g., 'llama*,gpt-4*')",
    ),
    show_paths: bool = typer.Option(
        False,
        "--show-paths",
        help="Show full file paths",
    ),
):
    """List available code examples without running them.

    This command scans for code examples in listing files and displays them in a table.
    Useful for exploring available examples before running tests.

    Examples:
        # List all code examples
        usvc test list

        # List for specific provider
        usvc test list --provider fireworks

        # List for specific services
        usvc test list --services "llama*,gpt-4*"

        # Show full file paths
        usvc test list --show-paths
    """
    # Set data directory
    if data_dir is None:
        data_dir = Path.cwd()

    if not data_dir.is_absolute():
        data_dir = Path.cwd() / data_dir

    if not data_dir.exists():
        console.print(
            f"[red]✗[/red] Data directory not found: {data_dir}",
            style="bold red",
        )
        raise typer.Exit(code=1)

    # Parse service patterns if provided
    service_patterns: list[str] = []
    if services:
        service_patterns = [s.strip() for s in services.split(",") if s.strip()]

    console.print(f"[blue]Scanning for code examples in:[/blue] {data_dir}\n")

    # Find all provider files
    provider_results = find_files_by_schema(data_dir, "provider_v1")
    provider_names: set[str] = set()

    for _provider_file, _format, provider_data in provider_results:
        prov_name = provider_data.get("name", "unknown")
        if not provider_name or prov_name == provider_name:
            provider_names.add(prov_name)

    if not provider_names:
        console.print("[yellow]No providers found.[/yellow]")
        raise typer.Exit(code=0)

    # Find all listing files
    listing_results = find_files_by_schema(data_dir, "listing_v1")

    if not listing_results:
        console.print("[yellow]No listing files found.[/yellow]")
        raise typer.Exit(code=0)

    # Extract code examples from all listings
    all_code_examples: list[tuple[dict[str, Any], str, str]] = []

    for listing_file, _format, listing_data in listing_results:
        # Determine provider for this listing
        parts = listing_file.parts
        prov_name = "unknown"

        try:
            services_idx = parts.index("services")
            if services_idx > 0:
                prov_name = parts[services_idx - 1]
        except (ValueError, IndexError):
            pass

        # Skip if provider filter is set and doesn't match
        if provider_name and prov_name != provider_name:
            continue

        # Skip if provider not in our list
        if prov_name not in provider_names:
            continue

        # Filter by service directory name if patterns are provided
        if service_patterns:
            service_dir = extract_service_directory_name(listing_file)
            if not service_dir:
                continue

            # Check if service matches any of the patterns
            matches = any(fnmatch.fnmatch(service_dir, pattern) for pattern in service_patterns)
            if not matches:
                continue

        code_examples = extract_code_examples_from_listing(listing_data, listing_file)

        for example in code_examples:
            # Get file extension
            file_path = example.get("file_path", "")
            file_ext = Path(file_path).suffix or "unknown"
            all_code_examples.append((example, prov_name, file_ext))

    if not all_code_examples:
        console.print("[yellow]No code examples found.[/yellow]")
        raise typer.Exit(code=0)

    # Display results in table
    table = Table(title="Available Code Examples")
    table.add_column("Service", style="cyan")
    table.add_column("Provider", style="blue")
    table.add_column("Title", style="white")
    table.add_column("Type", style="magenta")

    if show_paths:
        table.add_column("File Path", style="dim")

    for example, prov_name, file_ext in all_code_examples:
        row = [
            example["service_name"],
            prov_name,
            example["title"],
            file_ext,
        ]

        if show_paths:
            row.append(example.get("file_path", "N/A"))

        table.add_row(*row)

    console.print(table)
    console.print(f"\n[green]Total:[/green] {len(all_code_examples)} code example(s)")


@app.command()
def run(
    data_dir: Path | None = typer.Argument(
        None,
        help="Directory containing provider data files (default: current directory)",
    ),
    provider_name: str | None = typer.Option(
        None,
        "--provider",
        "-p",
        help="Only test code examples for a specific provider",
    ),
    services: str | None = typer.Option(
        None,
        "--services",
        "-s",
        help="Comma-separated list of service patterns (supports wildcards, e.g., 'llama*,gpt-4*')",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output including stdout/stderr from scripts",
    ),
):
    """Test code examples with upstream API credentials.

    This command:
    1. Scans for all listing files (schema: listing_v1)
    2. Extracts code example documents
    3. Loads provider credentials from provider.toml
    4. Executes each code example with API_KEY and API_ENDPOINT set to upstream values
    5. Displays test results

    Examples:
        # Test all code examples
        unitysvc_services test run

        # Test specific provider
        unitysvc_services test run --provider fireworks

        # Test specific services (with wildcards)
        unitysvc_services test run --services "llama*,gpt-4*"

        # Test single service
        unitysvc_services test run --services "llama-3-1-405b-instruct"

        # Combine filters
        unitysvc_services test run --provider fireworks --services "llama*"

        # Show detailed output
        unitysvc_services test run --verbose
    """
    # Set data directory
    if data_dir is None:
        data_dir = Path.cwd()

    if not data_dir.is_absolute():
        data_dir = Path.cwd() / data_dir

    if not data_dir.exists():
        console.print(
            f"[red]✗[/red] Data directory not found: {data_dir}",
            style="bold red",
        )
        raise typer.Exit(code=1)

    # Parse service patterns if provided
    service_patterns: list[str] = []
    if services:
        service_patterns = [s.strip() for s in services.split(",") if s.strip()]
        console.print(f"[blue]Service filter patterns:[/blue] {', '.join(service_patterns)}\n")

    console.print(f"[blue]Scanning for listing files in:[/blue] {data_dir}\n")

    # Find all provider files first to get credentials
    provider_results = find_files_by_schema(data_dir, "provider_v1")
    provider_credentials: dict[str, dict[str, str]] = {}

    for provider_file, _format, provider_data in provider_results:
        prov_name = provider_data.get("name", "unknown")

        # Skip if provider filter is set and doesn't match
        if provider_name and prov_name != provider_name:
            continue

        credentials = load_provider_credentials(provider_file)
        if credentials:
            provider_credentials[prov_name] = credentials
            console.print(f"[green]✓[/green] Loaded credentials for provider: {prov_name}")

    if not provider_credentials:
        console.print("[yellow]No provider credentials found.[/yellow]")
        raise typer.Exit(code=0)

    console.print()

    # Find all listing files
    listing_results = find_files_by_schema(data_dir, "listing_v1")

    if not listing_results:
        console.print("[yellow]No listing files found.[/yellow]")
        raise typer.Exit(code=0)

    console.print(f"[cyan]Found {len(listing_results)} listing file(s)[/cyan]\n")

    # Extract code examples from all listings
    all_code_examples: list[tuple[dict[str, Any], str]] = []

    for listing_file, _format, listing_data in listing_results:
        # Determine provider for this listing
        # Provider is the directory name before "services"
        parts = listing_file.parts
        prov_name = "unknown"

        try:
            services_idx = parts.index("services")
            if services_idx > 0:
                prov_name = parts[services_idx - 1]
        except (ValueError, IndexError):
            pass

        # Skip if provider filter is set and doesn't match
        if provider_name and prov_name != provider_name:
            continue

        # Skip if we don't have credentials for this provider
        if prov_name not in provider_credentials:
            continue

        # Filter by service directory name if patterns are provided
        if service_patterns:
            service_dir = extract_service_directory_name(listing_file)
            if not service_dir:
                continue

            # Check if service matches any of the patterns
            matches = any(fnmatch.fnmatch(service_dir, pattern) for pattern in service_patterns)
            if not matches:
                continue

        code_examples = extract_code_examples_from_listing(listing_data, listing_file)

        for example in code_examples:
            all_code_examples.append((example, prov_name))

    if not all_code_examples:
        console.print("[yellow]No code examples found in listings.[/yellow]")
        raise typer.Exit(code=0)

    console.print(f"[cyan]Found {len(all_code_examples)} code example(s)[/cyan]\n")

    # Execute each code example
    results = []

    for example, prov_name in all_code_examples:
        service_name = example["service_name"]
        title = example["title"]

        console.print(f"[bold]Testing:[/bold] {service_name} - {title}")

        credentials = provider_credentials[prov_name]
        result = execute_code_example(example, credentials)

        results.append(
            {
                "service_name": service_name,
                "provider": prov_name,
                "title": title,
                "result": result,
            }
        )

        if result["success"]:
            console.print(f"  [green]✓ Success[/green] (exit code: {result['exit_code']})")
            if verbose and result["stdout"]:
                console.print(f"  [dim]stdout:[/dim] {result['stdout'][:200]}")
        else:
            console.print(f"  [red]✗ Failed[/red] - {result['error']}")
            if verbose:
                if result["stdout"]:
                    console.print(f"  [dim]stdout:[/dim] {result['stdout'][:200]}")
                if result["stderr"]:
                    console.print(f"  [dim]stderr:[/dim] {result['stderr'][:200]}")

        console.print()

    # Print summary table
    console.print("\n" + "=" * 70)
    console.print("[bold]Test Results Summary:[/bold]\n")

    table = Table(title="Code Example Tests")
    table.add_column("Service", style="cyan")
    table.add_column("Provider", style="blue")
    table.add_column("Example", style="white")
    table.add_column("Status", style="green")
    table.add_column("Exit Code", style="white")

    total_tests = len(results)
    passed = sum(1 for r in results if r["result"]["success"])
    failed = total_tests - passed

    for test in results:
        status = "[green]✓ Pass[/green]" if test["result"]["success"] else "[red]✗ Fail[/red]"
        exit_code = str(test["result"]["exit_code"] or "N/A")

        table.add_row(
            test["service_name"],
            test["provider"],
            test["title"],
            status,
            exit_code,
        )

    console.print(table)
    console.print(f"\n[green]✓ Passed: {passed}/{total_tests}[/green]")
    console.print(f"[red]✗ Failed: {failed}/{total_tests}[/red]")

    if failed > 0:
        raise typer.Exit(code=1)
