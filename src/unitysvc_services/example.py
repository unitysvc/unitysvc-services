"""Run code examples locally with upstream credentials.

This is a local development tool to help sellers test code examples
using upstream API credentials. It does NOT modify seller data files.

Test results are written to .out and .err files alongside the code example,
making it easy to track results in version control.
"""

import fnmatch
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from .models.base import DocumentCategoryEnum
from .utils import (
    execute_script_content,
    find_files_by_schema,
    render_template_file,
)

app = typer.Typer(help="List and run code examples locally with upstream credentials")
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
    """Extract code example and connectivity test documents from a listing file.

    Args:
        listing_data: Parsed listing data (documents is a dict keyed by title)
        listing_file: Path to the listing file for resolving relative paths

    Returns:
        List of code example/test documents with resolved file paths
    """
    code_examples = []

    # Get service name from directory structure
    service_name = extract_service_directory_name(listing_file) or "unknown"

    # Categories that are testable (executable code)
    testable_categories = {
        DocumentCategoryEnum.code_example,
        DocumentCategoryEnum.connectivity_test,
    }

    # Get documents from listing level (now a dict keyed by title)
    documents = listing_data.get("documents", {}) or {}

    # Get first interface for template context (if any)
    # user_access_interfaces is now a dict keyed by name
    interfaces = listing_data.get("user_access_interfaces", {}) or {}
    first_interface: dict[str, Any] = next(iter(interfaces.values()), {}) if interfaces else {}

    for title, doc in documents.items():
        # Check if this is a testable document (code_example or connectivity_test)
        category = doc.get("category", "")
        if category in testable_categories:
            # Resolve file path relative to listing file
            file_path = doc.get("file_path")
            if file_path:
                # Resolve relative path
                absolute_path = (listing_file.parent / file_path).resolve()

                # Extract meta fields for code examples (expect, requirements, etc.)
                meta = doc.get("meta", {}) or {}

                code_example = {
                    "service_name": service_name,
                    "title": title,  # Title is now the dict key
                    "mime_type": doc.get("mime_type", "python"),
                    "file_path": str(absolute_path),
                    "listing_data": listing_data,  # Full listing data for templates
                    "listing_file": listing_file,  # Path to listing file for loading related data
                    "interface": first_interface,  # First interface for templates (base_url, routing_key, etc.)
                    "output_contains": meta.get("output_contains"),  # Substring to check in output (from meta)
                    "requirements": meta.get("requirements"),  # Required packages (from meta)
                    "category": category,  # Track which category this is
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
        # Find offering file (offering.json in same directory as listing) using find_files_by_schema
        offering_results = find_files_by_schema(listing_file.parent, "offering_v1")
        if offering_results:
            # Unpack tuple: (file_path, format, data)
            # Data is already loaded by find_files_by_schema
            _file_path, _format, offering_data = offering_results[0]
            result["offering"] = offering_data
        else:
            console.print(f"[yellow]Warning: No offering_v1 file found in {listing_file.parent}[/yellow]")

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
        else:
            console.print(f"[yellow]Warning: No provider_v1 file found in {provider_dir}[/yellow]")

        # Find seller file using find_files_by_schema (optional - seller files are not always present)
        # Go up to data directory (3 levels up from listing)
        data_dir = listing_file.parent.parent.parent.parent
        seller_results = find_files_by_schema(data_dir, "seller_v1")
        if seller_results:
            # Unpack tuple: (file_path, format, data)
            # Data is already loaded by find_files_by_schema
            _file_path, _format, seller_data = seller_results[0]
            result["seller"] = seller_data
        # No warning if seller file not found - seller data is optional

    except Exception as e:
        console.print(f"[yellow]Warning: Failed to load related data: {e}[/yellow]")

    return result


def load_provider_credentials(listing_file: Path) -> dict[str, str] | None:
    """Load API key and endpoint from service offering file.

    Args:
        listing_file: Path to the listing file (used to locate the service offering)

    Returns:
        Dictionary with api_key and base_url, or None if not found
    """
    try:
        # Load related data including the offering
        related_data = load_related_data(listing_file)
        offering = related_data.get("offering", {})

        if not offering:
            return None

        # Extract credentials from upstream_access_interfaces (dict keyed by name)
        # Use first interface for credentials
        upstream_interfaces = offering.get("upstream_access_interfaces", {})
        first_interface: dict[str, Any] = next(iter(upstream_interfaces.values()), {}) if upstream_interfaces else {}
        api_key = first_interface.get("api_key")
        base_url = first_interface.get("base_url")

        if api_key and base_url:
            return {
                "api_key": str(api_key),
                "base_url": str(base_url),
            }
    except Exception as e:
        console.print(f"[yellow]Warning: Failed to load service credentials: {e}[/yellow]")

    return None


def execute_code_example(code_example: dict[str, Any], credentials: dict[str, str]) -> dict[str, Any]:
    """Execute a code example script with upstream credentials.

    Args:
        code_example: Code example metadata with file_path and listing_data
        credentials: Dictionary with api_key and base_url

    Returns:
        Result dictionary with success, exit_code, stdout, stderr, rendered_content, file_suffix
    """
    result: dict[str, Any] = {
        "success": False,
        "exit_code": None,
        "error": None,
        "stdout": None,
        "stderr": None,
        "rendered_content": None,
        "mime_type": None,
        "listing_file": None,
        "actual_filename": None,
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
                interface=code_example.get("interface", {}),
            )
        except Exception as e:
            result["error"] = f"Template rendering failed: {str(e)}"
            return result

        # Get mime_type from code_example
        mime_type = code_example.get("mime_type", "python")

        # Store rendered content for later use (e.g., writing failed tests)
        result["rendered_content"] = file_content
        result["mime_type"] = mime_type
        result["listing_file"] = listing_file
        result["actual_filename"] = actual_filename

        # Prepare environment variables
        env_vars = {
            "API_KEY": credentials["api_key"],
            "BASE_URL": credentials["base_url"],
        }

        # Execute script using shared utility
        output_contains = code_example.get("output_contains")
        exec_result = execute_script_content(
            script=file_content,
            mime_type=mime_type,
            env_vars=env_vars,
            output_contains=output_contains,
            timeout=30,
        )

        # Map shared result to SDK result format
        result["exit_code"] = exec_result["exit_code"]
        result["stdout"] = exec_result["stdout"]
        result["stderr"] = exec_result["stderr"]
        result["error"] = exec_result["error"]
        result["success"] = exec_result["status"] == "success"

    except Exception as e:
        result["error"] = f"Error executing script: {str(e)}"

    return result


def get_output_file_paths(code_example_path: Path, listing_file: Path) -> tuple[Path, Path]:
    """Get the .out and .err file paths for a code example.

    Output files are named: {listing_stem}_{code_example_filename}.out/.err
    and are placed in the same directory as the listing file.

    Args:
        code_example_path: Path to the code example file
        listing_file: Path to the listing file

    Returns:
        Tuple of (out_file_path, err_file_path)
    """
    listing_stem = listing_file.stem
    # Remove .j2 extension if present to get the actual filename
    code_filename = code_example_path.name
    if code_filename.endswith(".j2"):
        code_filename = code_filename[:-3]

    out_filename = f"{listing_stem}_{code_filename}.out"
    err_filename = f"{listing_stem}_{code_filename}.err"

    out_path = listing_file.parent / out_filename
    err_path = listing_file.parent / err_filename

    return out_path, err_path


def has_passing_output_files(code_example_path: Path, listing_file: Path) -> bool:
    """Check if a passing test result exists for a code example.

    Only returns True if the test previously passed. Failed tests should be re-run.

    Args:
        code_example_path: Path to the code example file
        listing_file: Path to the listing file

    Returns:
        True if .out, .err, and .status files exist AND status is "pass"
    """
    out_path, err_path = get_output_file_paths(code_example_path, listing_file)
    status_path = out_path.with_suffix(".status")

    if not (out_path.exists() and err_path.exists() and status_path.exists()):
        return False

    # Check if status is "pass"
    try:
        status = status_path.read_text().strip()
        return status == "pass"
    except Exception:
        return False


def save_output_files(
    code_example_path: Path,
    listing_file: Path,
    stdout: str,
    stderr: str,
    passed: bool,
) -> tuple[Path, Path]:
    """Save stdout, stderr, and status to .out, .err, and .status files.

    Args:
        code_example_path: Path to the code example file
        listing_file: Path to the listing file
        stdout: Standard output from execution
        stderr: Standard error from execution
        passed: Whether the test passed

    Returns:
        Tuple of (out_file_path, err_file_path)
    """
    out_path, err_path = get_output_file_paths(code_example_path, listing_file)
    status_path = out_path.with_suffix(".status")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(stdout or "")

    with open(err_path, "w", encoding="utf-8") as f:
        f.write(stderr or "")

    with open(status_path, "w", encoding="utf-8") as f:
        f.write("pass" if passed else "fail")

    return out_path, err_path


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
):
    """List available code examples without running them.

    This command scans for code examples in listing files and displays them in a table
    with file paths shown relative to the data directory.

    Useful for exploring available examples before running tests.

    Examples:
        # List all code examples
        usvc data list examples

        # List for specific provider
        usvc data list examples --provider fireworks

        # List for specific services
        usvc data list examples --services "llama*,gpt-4*"
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

    # Find all listing files (override files are merged to include document IDs)
    listing_results = find_files_by_schema(data_dir, "listing_v1")

    if not listing_results:
        console.print("[yellow]No listing files found.[/yellow]")
        raise typer.Exit(code=0)

    # Extract code examples from all listings
    # Tuple: (example, provider_name, file_ext)
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
            # Get file extension (strip .j2 if present to show actual type)
            file_path = example.get("file_path", "")
            path = Path(file_path)
            # If it's a .j2 template, get the extension before .j2
            if path.suffix == ".j2":
                file_ext = Path(path.stem).suffix or "unknown"
            else:
                file_ext = path.suffix or "unknown"

            all_code_examples.append((example, prov_name, file_ext))

    if not all_code_examples:
        console.print("[yellow]No code examples found.[/yellow]")
        raise typer.Exit(code=0)

    # Display results in table
    table = Table(title="Available Code Examples")
    table.add_column("Service", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Category", style="green")
    table.add_column("Type", style="magenta")
    table.add_column("File Path", style="dim")

    for example, _prov_name, file_ext in all_code_examples:
        file_path = example.get("file_path", "N/A")
        category = example.get("category", "unknown")

        # Show path relative to data directory
        if file_path != "N/A":
            try:
                abs_path = Path(file_path).resolve()
                rel_path = abs_path.relative_to(data_dir.resolve())
                file_path = str(rel_path)
            except ValueError:
                # If relative_to fails, just show the path as-is
                file_path = str(file_path)

        row = [
            example["service_name"],
            example["title"],
            category,
            file_ext,
            file_path,
        ]

        table.add_row(*row)

    console.print(table)
    console.print(f"\n[green]Total:[/green] {len(all_code_examples)} code example(s)")


@app.command("show")
def show_test(
    service: str = typer.Argument(..., help="Service name to show test results for"),
    title: str = typer.Option(
        None, "--title", "-t", help="Only show results for specific test title"
    ),
    data_dir: Path | None = typer.Option(
        None,
        "--data-dir",
        "-d",
        help="Directory containing provider data files (default: current directory)",
    ),
):
    """Show test results for a service's code examples.

    Displays the status (.status), stdout (.out), and stderr (.err) files
    for previously executed tests.

    Examples:
        usvc data test show llama-3-1-405b-instruct
        usvc data test show llama-3-1-405b-instruct --title "Quick Start"
    """
    # Set data directory
    if data_dir is None:
        data_dir = Path.cwd()

    if not data_dir.is_absolute():
        data_dir = Path.cwd() / data_dir

    if not data_dir.exists():
        console.print(f"[red]Data directory not found: {data_dir}[/red]")
        raise typer.Exit(code=1)

    # Find listing files for the service
    listing_results = find_files_by_schema(data_dir, "listing_v1")

    found = False
    for listing_file, _format, listing_data in listing_results:
        # Check if this listing is for the requested service
        service_dir = extract_service_directory_name(listing_file)
        if service_dir != service:
            continue

        found = True
        code_examples = extract_code_examples_from_listing(listing_data, listing_file)

        if not code_examples:
            console.print(f"[yellow]No code examples found for service: {service}[/yellow]")
            continue

        # Filter by title if specified
        if title:
            code_examples = [e for e in code_examples if e.get("title") == title]
            if not code_examples:
                console.print(f"[yellow]No test found with title: {title}[/yellow]")
                continue

        for example in code_examples:
            example_title = example.get("title", "Unknown")
            file_path = Path(example.get("file_path", ""))

            console.print(f"\n[bold cyan]{example_title}[/bold cyan]")
            console.print(f"[dim]File: {file_path.name}[/dim]")

            # Get output file paths
            out_path, err_path = get_output_file_paths(file_path, listing_file)
            status_path = out_path.with_suffix(".status")

            # Show status
            if status_path.exists():
                status = status_path.read_text().strip()
                if status == "pass":
                    console.print("[green]Status: PASS[/green]")
                else:
                    console.print("[red]Status: FAIL[/red]")
            else:
                console.print("[yellow]Status: NOT RUN[/yellow]")
                continue

            # Show stdout
            if out_path.exists():
                stdout = out_path.read_text()
                if stdout.strip():
                    console.print("\n[bold]stdout:[/bold]")
                    console.print(stdout[:1000] if len(stdout) > 1000 else stdout)

            # Show stderr
            if err_path.exists():
                stderr = err_path.read_text()
                if stderr.strip():
                    console.print("\n[bold]stderr:[/bold]")
                    console.print(stderr[:1000] if len(stderr) > 1000 else stderr)

    if not found:
        console.print(f"[red]Service not found: {service}[/red]")
        raise typer.Exit(code=1)


@app.command("run")
def run_local(
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
    test_file: str | None = typer.Option(
        None,
        "--test-file",
        "-t",
        help="Only run a specific test file by filename (e.g., 'code-example.py.j2')",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output including stdout/stderr from scripts",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force rerun all tests, ignoring existing .out and .err files",
    ),
    fail_fast: bool = typer.Option(
        False,
        "--fail-fast",
        "-x",
        help="Stop testing on first failure",
    ),
):
    """Run code examples locally with upstream API credentials.

    This command:
    1. Scans for all listing files (schema: listing_v1)
    2. Extracts code example documents
    3. Loads provider credentials from offering file
    4. Skips tests that previously passed (unless --force is used)
    5. Executes each code example with API_KEY and BASE_URL set to upstream values
    6. Saves output to .out and .err files for tracking
    7. Displays test results

    Examples:
        # Run all code examples
        usvc data test

        # Run for specific provider
        usvc data test --provider fireworks

        # Run for specific services (with wildcards)
        usvc data test --services "llama*,gpt-4*"

        # Run single service
        usvc data test --services "llama-3-1-405b-instruct"

        # Run specific file
        usvc data test --test-file "code-example.py.j2"

        # Combine filters
        usvc data test --provider fireworks --services "llama*"

        # Show detailed output
        usvc data test --verbose

        # Force rerun all tests (ignore existing results)
        usvc data test --force

        # Stop on first failure
        usvc data test --fail-fast
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

    # Display test file filter if provided
    if test_file:
        console.print(f"[blue]Test file filter:[/blue] {test_file}\n")

    console.print(f"[blue]Scanning for listing files in:[/blue] {data_dir}\n")

    # Find all listing files (override files are merged to include document IDs)
    listing_results = find_files_by_schema(data_dir, "listing_v1")

    if not listing_results:
        console.print("[yellow]No listing files found.[/yellow]")
        raise typer.Exit(code=0)

    console.print(f"[cyan]Found {len(listing_results)} listing file(s)[/cyan]\n")

    # Extract code examples from all listings
    all_code_examples: list[tuple[dict[str, Any], str, dict[str, str]]] = []

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

        # Load credentials from service offering for this listing
        credentials = load_provider_credentials(listing_file)
        if not credentials:
            console.print(f"[yellow]⚠ No credentials found for listing: {listing_file}[/yellow]")
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
            # Filter by test file name if provided
            if test_file:
                file_path = example.get("file_path", "")
                # Check if the file path ends with the test file name
                if not file_path.endswith(test_file):
                    continue

            all_code_examples.append((example, prov_name, credentials))

    if not all_code_examples:
        console.print("[yellow]No code examples found in listings.[/yellow]")
        raise typer.Exit(code=0)

    console.print(f"[cyan]Found {len(all_code_examples)} code example(s)[/cyan]\n")

    # Execute each code example
    results = []

    for example, prov_name, credentials in all_code_examples:
        service_name = example["service_name"]
        title = example["title"]
        example_listing_file = example.get("listing_file")

        # Check if test previously passed (skip if not forcing)
        code_example_path = Path(example.get("file_path", ""))
        if not force and example_listing_file and has_passing_output_files(
            code_example_path, Path(example_listing_file)
        ):
            console.print(f"[bold]Testing:[/bold] {service_name} - {title}")
            console.print("  [yellow]⊘ Skipped[/yellow] (previously passed)")
            console.print()
            # Add a skipped result for the summary
            results.append(
                {
                    "service_name": service_name,
                    "provider": prov_name,
                    "title": title,
                    "result": {
                        "success": True,
                        "exit_code": None,
                        "skipped": True,
                    },
                }
            )
            continue

        console.print(f"[bold]Testing:[/bold] {service_name} - {title}")

        result = execute_code_example(example, credentials)
        result["skipped"] = False

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

            # Save output to .out, .err, and .status files
            if example_listing_file:
                out_path, err_path = save_output_files(
                    code_example_path,
                    Path(example_listing_file),
                    result.get("stdout", "") or "",
                    result.get("stderr", "") or "",
                    passed=True,
                )
                console.print(f"  [dim]Output saved to: {out_path.name}, {err_path.name}[/dim]")
        else:
            console.print(f"  [red]✗ Failed[/red] - {result['error']}")
            if verbose:
                if result["stdout"]:
                    console.print(f"  [dim]stdout:[/dim] {result['stdout'][:200]}")
                if result["stderr"]:
                    console.print(f"  [dim]stderr:[/dim] {result['stderr'][:200]}")

            # Save output to .out, .err, and .status files (even for failures)
            if example_listing_file:
                out_path, err_path = save_output_files(
                    code_example_path,
                    Path(example_listing_file),
                    result.get("stdout", "") or "",
                    result.get("stderr", "") or "",
                    passed=False,
                )
                console.print(f"  [dim]Output saved to: {out_path.name}, {err_path.name}[/dim]")

            # Write failed test script and env to current directory (for debugging)
            if result.get("listing_file") and result.get("actual_filename"):
                result_listing_file = Path(result["listing_file"])
                result_actual_filename = result["actual_filename"]
                result_listing_stem = result_listing_file.stem

                # Create filename: failed_{service_name}_{listing_stem}_{actual_filename}
                failed_filename = f"failed_{service_name}_{result_listing_stem}_{result_actual_filename}"

                # Write failed test script content to current directory (for debugging)
                try:
                    with open(failed_filename, "w", encoding="utf-8") as f:
                        f.write(result["rendered_content"])
                    console.print(f"  [yellow]→ Test script saved to:[/yellow] {failed_filename}")
                except Exception as e:
                    console.print(f"  [yellow]⚠ Failed to save test script: {e}[/yellow]")

                # Write environment variables to .env file
                env_filename = f"{failed_filename}.env"
                try:
                    with open(env_filename, "w", encoding="utf-8") as f:
                        f.write(f"API_KEY={credentials['api_key']}\n")
                        f.write(f"BASE_URL={credentials['base_url']}\n")
                    console.print(f"  [yellow]→ Environment variables saved to:[/yellow] {env_filename}")
                    console.print(f"  [dim]  (source this file to reproduce: source {env_filename})[/dim]")
                except Exception as e:
                    console.print(f"  [yellow]⚠ Failed to save environment file: {e}[/yellow]")

            # Stop testing if fail-fast is enabled
            if fail_fast:
                console.print()
                console.print("[yellow]⚠ Stopping tests due to --fail-fast[/yellow]")
                break

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
    skipped = sum(1 for r in results if r["result"].get("skipped", False))
    passed = sum(1 for r in results if r["result"]["success"] and not r["result"].get("skipped", False))
    failed = total_tests - passed - skipped

    for test in results:
        result = test["result"]
        if result.get("skipped", False):
            status = "[yellow]⊘ Skipped[/yellow]"
        elif result["success"]:
            status = "[green]✓ Pass[/green]"
        else:
            status = "[red]✗ Fail[/red]"

        # Use 'is not None' to properly handle exit_code of 0 (success)
        exit_code = str(result["exit_code"]) if result["exit_code"] is not None else "N/A"

        table.add_row(
            test["service_name"],
            test["provider"],
            test["title"],
            status,
            exit_code,
        )

    console.print(table)
    console.print(f"\n[green]✓ Passed: {passed}/{total_tests}[/green]")
    if skipped > 0:
        console.print(f"[yellow]⊘ Skipped: {skipped}/{total_tests}[/yellow]")
    console.print(f"[red]✗ Failed: {failed}/{total_tests}[/red]")

    if failed > 0:
        raise typer.Exit(code=1)
