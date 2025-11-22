"""Test command group - test code examples with upstream credentials."""

import fnmatch
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from .models.base import DocumentCategoryEnum, UpstreamStatusEnum
from .utils import determine_interpreter, find_files_by_schema, render_template_file

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
            # Check if this is a code example document
            category = doc.get("category", "")
            if category == DocumentCategoryEnum.code_example:
                # Resolve file path relative to listing file
                file_path = doc.get("file_path")
                if file_path:
                    # Resolve relative path
                    absolute_path = (listing_file.parent / file_path).resolve()

                    # Extract meta fields for code examples (expect, requirements, etc.)
                    meta = doc.get("meta", {}) or {}

                    code_example = {
                        "service_name": service_name,
                        "title": doc.get("title", "Untitled"),
                        "mime_type": doc.get("mime_type", "python"),
                        "file_path": str(absolute_path),
                        "listing_data": listing_data,  # Full listing data for templates
                        "listing_file": listing_file,  # Path to listing file for loading related data
                        "interface": interface,  # Interface data for templates (base_url, routing_key, etc.)
                        "expect": meta.get("expect"),  # Expected output substring for validation (from meta)
                        "requirements": meta.get("requirements"),  # Required packages (from meta)
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
        # Find offering file (service.json in same directory as listing) using find_files_by_schema
        offering_results = find_files_by_schema(listing_file.parent, "service_v1")
        if offering_results:
            # Unpack tuple: (file_path, format, data)
            # Data is already loaded by find_files_by_schema
            _file_path, _format, offering_data = offering_results[0]
            result["offering"] = offering_data
        else:
            console.print(f"[yellow]Warning: No service_v1 file found in {listing_file.parent}[/yellow]")

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

        # Find seller file using find_files_by_schema
        # Go up to data directory (3 levels up from listing)
        data_dir = listing_file.parent.parent.parent.parent
        seller_results = find_files_by_schema(data_dir, "seller_v1")
        if seller_results:
            # Unpack tuple: (file_path, format, data)
            # Data is already loaded by find_files_by_schema
            _file_path, _format, seller_data = seller_results[0]
            result["seller"] = seller_data
        else:
            console.print(f"[yellow]Warning: No seller_v1 file found in {data_dir}[/yellow]")

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

        # Extract credentials from upstream_access_interface
        upstream_access = offering.get("upstream_access_interface", {})
        api_key = upstream_access.get("api_key")
        base_url = upstream_access.get("base_url")

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
        "file_suffix": None,
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

        # Get file suffix from the actual filename (after .j2 stripping if applicable)
        file_suffix = Path(actual_filename).suffix or ".txt"

        # Store rendered content and file suffix for later use (e.g., writing failed tests)
        result["rendered_content"] = file_content
        result["file_suffix"] = file_suffix
        result["listing_file"] = listing_file
        result["actual_filename"] = actual_filename

        # Determine interpreter to use (using shared utility function)
        interpreter_cmd, error = determine_interpreter(file_content, file_suffix)
        if error:
            result["error"] = error
            return result

        # At this point, interpreter_cmd is guaranteed to be a string (error check above)
        assert interpreter_cmd is not None, "interpreter_cmd should not be None after error check"

        # Prepare environment variables
        env = os.environ.copy()
        env["API_KEY"] = credentials["api_key"]
        env["BASE_URL"] = credentials["base_url"]

        # Write script to temporary file with original extension
        with tempfile.NamedTemporaryFile(mode="w", suffix=file_suffix, delete=False) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        try:
            # Execute the script (interpreter availability already verified)
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

            # Determine if test passed
            # Test passes if: exit_code == 0 AND (expect is None OR expect in stdout)
            expected_output = code_example.get("expect")

            if process.returncode != 0:
                # Failed: non-zero exit code
                result["success"] = False
                result["error"] = f"Script exited with code {process.returncode}. stderr: {process.stderr[:200]}"
            elif expected_output and expected_output not in process.stdout:
                # Failed: exit code is 0 but expected string not found in output
                result["success"] = False
                result["error"] = (
                    f"Output validation failed: expected substring '{expected_output}' "
                    f"not found in stdout. stdout: {process.stdout[:200]}"
                )
            else:
                # Passed: exit code is 0 AND (no expect field OR expected string found)
                result["success"] = True

        finally:
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass

    except subprocess.TimeoutExpired:
        result["error"] = "Script execution timeout (30 seconds)"
    except Exception as e:
        result["error"] = f"Error executing script: {str(e)}"

    return result


def update_offering_override_status(listing_file: Path, status: UpstreamStatusEnum | None) -> None:
    """Update or remove the status field in the offering override file.

    Args:
        listing_file: Path to the listing file (offering is in same directory)
        status: Status to set (e.g., UpstreamStatusEnum.deprecated), or None to remove status field
    """
    import json

    try:
        # Find the offering file (service.json) in the same directory
        offering_results = find_files_by_schema(listing_file.parent, "service_v1")
        if not offering_results:
            console.print(f"[yellow]⚠ No service offering file found in {listing_file.parent}[/yellow]")
            return

        # Get the base offering file path
        offering_file_path, offering_format, _offering_data = offering_results[0]

        # Construct override file path
        override_path = offering_file_path.with_stem(f"{offering_file_path.stem}.override")

        # Load existing override file if it exists
        if override_path.exists():
            try:
                with open(override_path, encoding="utf-8") as f:
                    if offering_format == "json":
                        override_data = json.load(f)
                    else:  # toml
                        import tomli

                        override_data = tomli.loads(f.read())
            except Exception as e:
                console.print(f"[yellow]⚠ Failed to read override file {override_path}: {e}[/yellow]")
                override_data = {}
        else:
            override_data = {}

        # Update or remove upstream_status field
        if status is None:
            # Remove upstream_status field if it exists and equals deprecated
            if override_data.get("upstream_status") == UpstreamStatusEnum.deprecated:
                del override_data["upstream_status"]
                console.print("  [dim]→ Removed deprecated upstream_status from override file[/dim]")
        else:
            # Set upstream_status field
            override_data["upstream_status"] = status.value
            console.print(f"  [dim]→ Set upstream_status to {status.value} in override file[/dim]")

        # Write override file (or delete if empty)
        if override_data:
            # Write the override file
            with open(override_path, "w", encoding="utf-8") as f:
                if offering_format == "json":
                    json.dump(override_data, f, indent=2)
                    f.write("\n")  # Add trailing newline
                else:  # toml
                    import tomli_w

                    f.write(tomli_w.dumps(override_data))
            console.print(f"  [dim]→ Updated override file: {override_path}[/dim]")
        else:
            # Delete override file if it's now empty
            if override_path.exists():
                override_path.unlink()
                console.print(f"  [dim]→ Removed empty override file: {override_path}[/dim]")

    except Exception as e:
        console.print(f"[yellow]⚠ Failed to update override file: {e}[/yellow]")


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
        usvc test list

        # List for specific provider
        usvc test list --provider fireworks

        # List for specific services
        usvc test list --services "llama*,gpt-4*"
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
    table.add_column("Provider", style="blue")
    table.add_column("Title", style="white")
    table.add_column("Type", style="magenta")
    table.add_column("File Path", style="dim")

    for example, prov_name, file_ext in all_code_examples:
        file_path = example.get("file_path", "N/A")

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
            prov_name,
            example["title"],
            file_ext,
            file_path,
        ]

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
    """Test code examples with upstream API credentials.

    This command:
    1. Scans for all listing files (schema: listing_v1)
    2. Extracts code example documents
    3. Loads provider credentials from provider.toml
    4. Skips tests that have existing .out and .err files (unless --force is used)
    5. Executes each code example with API_KEY and BASE_URL set to upstream values
    6. Displays test results

    Examples:
        # Test all code examples
        unitysvc_services test run

        # Test specific provider
        unitysvc_services test run --provider fireworks

        # Test specific services (with wildcards)
        unitysvc_services test run --services "llama*,gpt-4*"

        # Test single service
        unitysvc_services test run --services "llama-3-1-405b-instruct"

        # Test specific file
        unitysvc_services test run --test-file "code-example.py.j2"

        # Combine filters
        unitysvc_services test run --provider fireworks --services "llama*"

        # Show detailed output
        unitysvc_services test run --verbose

        # Force rerun all tests (ignore existing results)
        unitysvc_services test run --force

        # Stop on first failure
        unitysvc_services test run --fail-fast
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

    # Find all listing files
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
    skipped_count = 0

    # Track test results per service offering (for status updates)
    # Key: offering directory path, Value: {"passed": int, "failed": int, "listing_file": Path}
    offering_test_results: dict[str, dict[str, Any]] = {}

    for example, prov_name, credentials in all_code_examples:
        service_name = example["service_name"]
        title = example["title"]
        example_listing_file = example.get("listing_file")

        # Determine actual filename (strip .j2 if it's a template)
        file_path = example.get("file_path")
        if file_path:
            original_path = Path(file_path)
            # If it's a .j2 template, the actual filename is without .j2
            if original_path.suffix == ".j2":
                actual_filename = original_path.stem
            else:
                actual_filename = original_path.name
        else:
            actual_filename = None

        # Prepare output file paths if we have the necessary information
        out_path = None
        err_path = None
        if example_listing_file and actual_filename:
            listing_path = Path(example_listing_file)
            listing_stem = listing_path.stem

            # Create filename pattern: {service_name}_{listing_stem}_{actual_filename}.out/.err
            # e.g., "llama-3-1-405b-instruct_svclisting_test.py.out"
            base_filename = f"{service_name}_{listing_stem}_{actual_filename}"
            out_filename = f"{base_filename}.out"
            err_filename = f"{base_filename}.err"

            # Output paths in the listing directory
            out_path = listing_path.parent / out_filename
            err_path = listing_path.parent / err_filename

        # Check if test results already exist (skip if not forcing)
        if not force and out_path and err_path and out_path.exists() and err_path.exists():
            console.print(f"[bold]Testing:[/bold] {service_name} - {title}")
            console.print("  [yellow]⊘ Skipped[/yellow] (results already exist)")
            console.print()
            skipped_count += 1
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

            # Save successful test output to .out and .err files (if paths were determined)
            if out_path and err_path:
                # Write stdout to .out file
                try:
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(result["stdout"] or "")
                    console.print(f"  [dim]→ Output saved to:[/dim] {out_path}")
                except Exception as e:
                    console.print(f"  [yellow]⚠ Failed to save output: {e}[/yellow]")

                # Write stderr to .err file
                try:
                    with open(err_path, "w", encoding="utf-8") as f:
                        f.write(result["stderr"] or "")
                    if result["stderr"]:
                        console.print(f"  [dim]→ Error output saved to:[/dim] {err_path}")
                except Exception as e:
                    console.print(f"  [yellow]⚠ Failed to save error output: {e}[/yellow]")

            # Track test result for this offering (don't update status yet)
            if example_listing_file and not test_file:
                offering_dir = str(example_listing_file.parent)
                if offering_dir not in offering_test_results:
                    offering_test_results[offering_dir] = {
                        "passed": 0,
                        "failed": 0,
                        "listing_file": example_listing_file,
                    }
                offering_test_results[offering_dir]["passed"] += 1
        else:
            console.print(f"  [red]✗ Failed[/red] - {result['error']}")
            if verbose:
                if result["stdout"]:
                    console.print(f"  [dim]stdout:[/dim] {result['stdout'][:200]}")
                if result["stderr"]:
                    console.print(f"  [dim]stderr:[/dim] {result['stderr'][:200]}")

            # Write failed test outputs and script to current directory
            # Use actual_filename from result in case template rendering modified it
            if result.get("listing_file") and result.get("actual_filename"):
                result_listing_file = Path(result["listing_file"])
                result_actual_filename = result["actual_filename"]
                result_listing_stem = result_listing_file.stem

                # Create filename: failed_{service_name}_{listing_stem}_{actual_filename}
                # This will be the base name for .out, .err, and the script file
                failed_filename = f"failed_{service_name}_{result_listing_stem}_{result_actual_filename}"

                # Write stdout to .out file in current directory
                out_filename = f"{failed_filename}.out"
                try:
                    with open(out_filename, "w", encoding="utf-8") as f:
                        f.write(result["stdout"] or "")
                    console.print(f"  [yellow]→ Output saved to:[/yellow] {out_filename}")
                except Exception as e:
                    console.print(f"  [yellow]⚠ Failed to save output: {e}[/yellow]")

                # Write stderr to .err file in current directory
                err_filename = f"{failed_filename}.err"
                try:
                    with open(err_filename, "w", encoding="utf-8") as f:
                        f.write(result["stderr"] or "")
                    console.print(f"  [yellow]→ Error output saved to:[/yellow] {err_filename}")
                except Exception as e:
                    console.print(f"  [yellow]⚠ Failed to save error output: {e}[/yellow]")

                # Write failed test script content to current directory (for debugging)
                # rendered_content is always set if we got here (set during template rendering)
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

            # Track test result for this offering (don't update status yet)
            if example_listing_file and not test_file:
                offering_dir = str(example_listing_file.parent)
                if offering_dir not in offering_test_results:
                    offering_test_results[offering_dir] = {
                        "passed": 0,
                        "failed": 0,
                        "listing_file": example_listing_file,
                    }
                offering_test_results[offering_dir]["failed"] += 1

            # Stop testing if fail-fast is enabled
            if fail_fast:
                console.print()
                console.print("[yellow]⚠ Stopping tests due to --fail-fast[/yellow]")
                break

        console.print()

    # Update offering status based on test results (only if not using --test-file)
    if not test_file and offering_test_results:
        console.print("\n[cyan]Updating service offering status...[/cyan]")
        for _offering_dir, test_stats in offering_test_results.items():
            listing_file = test_stats["listing_file"]
            passed = test_stats["passed"]
            failed = test_stats["failed"]

            # If any test failed, set to deprecated
            if failed > 0:
                update_offering_override_status(listing_file, UpstreamStatusEnum.deprecated)
            # If all tests passed, remove deprecated status
            elif passed > 0 and failed == 0:
                update_offering_override_status(listing_file, None)

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
