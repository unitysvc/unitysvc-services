"""Run code examples locally with upstream credentials.

This is a local development tool to help sellers test code examples
using upstream API credentials. It does NOT modify seller data files.

Test results are written to .out and .err files alongside the code example,
making it easy to track results in version control.
"""

import fnmatch
import os
import random
import re
import string
from pathlib import Path
from typing import Any

import jinja2
import typer
from rich.console import Console
from rich.table import Table

from .models.base import DocumentCategoryEnum
from .output import format_output
from .utils import execute_script_content, find_files_by_schema, render_template_file

app = typer.Typer(help="List and run code examples locally with upstream credentials")
console = Console()

_jinja_env = jinja2.Environment()

# Fixed test code reused across a single run so all templates resolve consistently
_test_enrollment_code: str | None = None


def _get_test_enrollment_code(length: int = 6) -> str:
    """Return a fixed random code for local testing (no real enrollment)."""
    global _test_enrollment_code
    if _test_enrollment_code is None:
        _test_enrollment_code = "".join(random.choices(string.ascii_uppercase, k=length))
    return _test_enrollment_code


def expand_template_strings(data: dict[str, Any]) -> dict[str, Any]:
    """Expand Jinja2 template syntax in string values of a dict.

    Uses a fake enrollment_code() for local testing. Only processes
    values that contain {{ or {%.
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, str) and ("{{" in value or "{%" in value):
            try:
                template = _jinja_env.from_string(value)
                value = template.render(enrollment_code=_get_test_enrollment_code)
            except jinja2.TemplateError:
                pass
        result[key] = value
    return result


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


def extract_upstream_interfaces_from_offering(
    listing_file: Path,
) -> dict[str, dict[str, Any]]:
    """Load upstream_access_interfaces from the offering file for a listing.

    Returns the raw interface data (secrets are NOT resolved here).

    Args:
        listing_file: Path to the listing file (offering is in the same directory)

    Returns:
        Dict keyed by interface name, or empty dict if not found.
    """
    try:
        offering_results = find_files_by_schema(listing_file.parent, "offering_v1")
        if not offering_results:
            return {}
        _file_path, _format, offering_data = offering_results[0]
        return offering_data.get("upstream_access_interfaces", {}) or {}
    except Exception:
        return {}


def discover_code_examples(
    data_dir: Path,
    *,
    provider_name: str | None = None,
    service_patterns: list[str] | None = None,
) -> list[tuple[dict[str, Any], str]]:
    """Discover code examples by scanning listing files.

    Shared discovery logic used by list, show, and run commands.
    Returns one entry per (document × upstream_interface) pair.
    Each example dict includes ``upstream_interface_name`` and
    ``upstream_interface`` (raw data, secrets not resolved).

    Args:
        data_dir: Root directory to scan for listing files.
        provider_name: Only include examples from this provider (exact match).
        service_patterns: Glob patterns for service directory names
            (supports wildcards via fnmatch). Pass a literal name for exact match.

    Returns:
        List of (code_example_dict, provider_name) tuples.
    """
    listing_results = find_files_by_schema(data_dir, "listing_v1")

    results: list[tuple[dict[str, Any], str]] = []

    for listing_file, _format, listing_data in listing_results:
        # Determine provider from directory structure
        parts = listing_file.parts
        prov_name = "unknown"
        try:
            services_idx = parts.index("services")
            if services_idx > 0:
                prov_name = parts[services_idx - 1]
        except (ValueError, IndexError):
            pass

        # Filter by provider
        if provider_name and prov_name != provider_name:
            continue

        # Filter by service patterns
        if service_patterns:
            service_dir = extract_service_directory_name(listing_file)
            if not service_dir:
                continue
            if not any(fnmatch.fnmatch(service_dir, p) for p in service_patterns):
                continue

        # Load upstream interfaces from offering (cross-product with documents)
        upstream_interfaces = extract_upstream_interfaces_from_offering(listing_file)

        # For byok services, ops_testing_parameters provides upstream credentials
        service_options = listing_data.get("service_options", {}) or {}
        default_params = service_options.get("ops_testing_parameters", {}) or {}

        if not upstream_interfaces and default_params:
            # No upstream interfaces defined — create one from ops_testing_parameters
            upstream_interfaces = {"default": dict(default_params)}
        elif upstream_interfaces and default_params:
            # Override api_key/base_url with ops_testing_parameters
            for _name, iface_data in upstream_interfaces.items():
                for field in ("api_key", "base_url"):
                    if field in default_params:
                        iface_data[field] = default_params[field]

        # Validate that each upstream interface has required fields
        for iface_name, iface_data in upstream_interfaces.items():
            if not iface_data.get("base_url"):
                service_dir = extract_service_directory_name(listing_file) or str(listing_file)
                raise ValueError(
                    f"Upstream interface '{iface_name}' in {service_dir} is missing: "
                    f"base_url. Add it to offering upstream_access_interfaces "
                    f"or listing service_options.ops_testing_parameters."
                )
            if not iface_data.get("api_key"):
                service_dir = extract_service_directory_name(listing_file) or str(listing_file)
                console.print(
                    f"[yellow]⚠ Upstream interface '{iface_name}' in {service_dir} has no api_key. "
                    f"If this service requires authentication, add api_key to offering "
                    f"upstream_access_interfaces or listing service_options.ops_testing_parameters.[/yellow]"
                )

        # Extract code examples × upstream interfaces
        for example in extract_code_examples_from_listing(listing_data, listing_file):
            if upstream_interfaces:
                for iface_name, iface_data in upstream_interfaces.items():
                    ex = {
                        **example,
                        "upstream_interface_name": iface_name,
                        "upstream_interface": iface_data,
                    }
                    results.append((ex, prov_name))
            else:
                example["upstream_interface_name"] = "default"
                example["upstream_interface"] = {}
                results.append((example, prov_name))

    return results


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


_SECRETS_RE = re.compile(r"^\$\{\s*secrets\.([A-Za-z_][A-Za-z0-9_]*)\s*\}$")


def resolve_secret_ref(value: str, field_name: str) -> str:
    """Resolve a ``${ secrets.VAR_NAME }`` reference from the environment.

    If *value* is a literal string (not a secrets reference) it is returned
    as-is.  If it matches the ``${ secrets.VAR_NAME }`` pattern the
    corresponding environment variable is looked up and returned.

    Raises:
        typer.Exit: When the environment variable is not set.
    """
    m = _SECRETS_RE.match(value)
    if not m:
        return value

    var_name = m.group(1)
    env_value = os.environ.get(var_name)
    if not env_value:
        console.print(
            f"[red]Error:[/red] {field_name} references secret [bold]{var_name}[/bold] "
            f"but the environment variable is not set.\n"
            f"  Set it with: [cyan]export {var_name}=<value>[/cyan]",
        )
        raise typer.Exit(code=1)
    return env_value


def load_upstream_access_interface(listing_file: Path) -> dict[str, str] | None:
    """Load API key and endpoint from service offering file.

    Secrets references (``${ secrets.VAR_NAME }``) are resolved from the
    current environment.

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
        first_interface = expand_template_strings(first_interface)
        api_key = first_interface.get("api_key")
        base_url = first_interface.get("base_url")

        if base_url:
            return {
                "api_key": resolve_secret_ref(str(api_key), "api_key") if api_key else "",
                "base_url": resolve_secret_ref(str(base_url), "base_url"),
            }
    except typer.Exit:
        raise
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
            "UNITYSVC_API_KEY": credentials["api_key"],
            "SERVICE_BASE_URL": credentials["base_url"],
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
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: json, table, tsv, csv",
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

        # List as JSON
        usvc data list examples --format json
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
    service_patterns: list[str] | None = None
    if services:
        service_patterns = [s.strip() for s in services.split(",") if s.strip()]

    console.print(f"[blue]Scanning for code examples in:[/blue] {data_dir}\n")

    all_code_examples = discover_code_examples(
        data_dir,
        provider_name=provider_name,
        service_patterns=service_patterns,
    )

    if not all_code_examples:
        console.print("[yellow]No code examples found.[/yellow]")
        raise typer.Exit(code=0)

    # Build rows as dicts for all output formats
    rows: list[dict[str, str]] = []
    for example, _prov_name in all_code_examples:
        file_path = example.get("file_path", "N/A")
        category = example.get("category", "unknown")

        # Get file extension (strip .j2 if present to show actual type)
        path = Path(file_path)
        if path.suffix == ".j2":
            file_ext = Path(path.stem).suffix or "unknown"
        else:
            file_ext = path.suffix or "unknown"

        # Show path relative to data directory
        if file_path != "N/A":
            try:
                abs_path = Path(file_path).resolve()
                rel_path = abs_path.relative_to(data_dir.resolve())
                file_path = str(rel_path)
            except ValueError:
                file_path = str(file_path)

        rows.append(
            {
                "service": example["service_name"],
                "title": example["title"],
                "category": category,
                "interface": example.get("upstream_interface_name", "default"),
                "type": file_ext,
                "file_path": file_path,
            }
        )

    format_output(
        rows,
        output_format=output_format,
        columns=["service", "title", "category", "interface", "type", "file_path"],
        column_styles={
            "service": "cyan",
            "title": "white",
            "category": "green",
            "interface": "magenta",
            "type": "magenta",
            "file_path": "dim",
        },
        title="Available Code Examples",
        console=console,
    )


@app.command("show")
def show_test(
    service: str = typer.Argument(..., help="Service name to show test results for"),
    title: str = typer.Option(None, "--title", "-t", help="Only show results for specific test title"),
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

    examples = discover_code_examples(data_dir, service_patterns=[service])

    if not examples:
        console.print(f"[red]Service not found: {service}[/red]")
        raise typer.Exit(code=1)

    # Filter by title if specified
    if title:
        examples = [(e, p) for e, p in examples if e.get("title") == title]
        if not examples:
            console.print(f"[yellow]No test found with title: {title}[/yellow]")
            raise typer.Exit(code=0)

    for example, _prov_name in examples:
        example_title = example.get("title", "Unknown")
        file_path = Path(example.get("file_path", ""))
        listing_file = Path(example["listing_file"])

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
    5. Executes each code example with UNITYSVC_API_KEY and SERVICE_BASE_URL set to upstream values
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
    service_patterns: list[str] | None = None
    if services:
        service_patterns = [s.strip() for s in services.split(",") if s.strip()]
        console.print(f"[blue]Service filter patterns:[/blue] {', '.join(service_patterns)}\n")

    # Display test file filter if provided
    if test_file:
        console.print(f"[blue]Test file filter:[/blue] {test_file}\n")

    console.print(f"[blue]Scanning for listing files in:[/blue] {data_dir}\n")

    discovered = discover_code_examples(
        data_dir,
        provider_name=provider_name,
        service_patterns=service_patterns,
    )

    # Filter by test file name if provided
    if test_file:
        discovered = [(e, p) for e, p in discovered if e.get("file_path", "").endswith(test_file)]

    # Resolve credentials from upstream_interface in each discovered example
    all_code_examples: list[tuple[dict[str, Any], str, dict[str, str]]] = []
    warned_listings: set[str] = set()

    for example, prov_name in discovered:
        iface = expand_template_strings(example.get("upstream_interface", {}))
        api_key = iface.get("api_key")
        base_url = iface.get("base_url")
        if base_url:
            iface_name = example.get("upstream_interface_name", "default")
            credentials = {
                "api_key": resolve_secret_ref(str(api_key), f"{iface_name}.api_key") if api_key else "",
                "base_url": resolve_secret_ref(str(base_url), f"{iface_name}.base_url"),
            }
            all_code_examples.append((example, prov_name, credentials))
        else:
            listing_file_str = str(example.get("listing_file", ""))
            if listing_file_str not in warned_listings:
                console.print(f"[yellow]⚠ No credentials found for listing: {listing_file_str}[/yellow]")
                warned_listings.add(listing_file_str)

    if not all_code_examples:
        console.print("[yellow]No code examples found in listings.[/yellow]")
        raise typer.Exit(code=0)

    console.print(f"[cyan]Found {len(all_code_examples)} test case(s)[/cyan]\n")

    # Execute each test case (one entry per document × upstream interface)
    results = []

    for example, prov_name, credentials in all_code_examples:
        service_name = example["service_name"]
        example_title = example["title"]
        iface_name = example.get("upstream_interface_name", "default")
        example_listing_file = example.get("listing_file")
        code_example_path = Path(example.get("file_path", ""))

        label = f"{service_name} - {example_title} [{iface_name}]"

        # Check if test previously passed (skip if not forcing)
        if (
            not force
            and example_listing_file
            and has_passing_output_files(code_example_path, Path(example_listing_file))
        ):
            console.print(f"[bold]Testing:[/bold] {label}")
            console.print("  [yellow]⊘ Skipped[/yellow] (previously passed)")
            console.print()
            results.append(
                {
                    "service_name": service_name,
                    "provider": prov_name,
                    "title": example_title,
                    "interface": iface_name,
                    "result": {
                        "success": True,
                        "exit_code": None,
                        "skipped": True,
                    },
                }
            )
            continue

        console.print(f"[bold]Testing:[/bold] {label}")

        result = execute_code_example(example, credentials)
        result["skipped"] = False

        results.append(
            {
                "service_name": service_name,
                "provider": prov_name,
                "title": example_title,
                "interface": iface_name,
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

                # Include interface name for disambiguation
                safe_iface = iface_name.replace(" ", "_").replace("/", "_")
                failed_filename = f"failed_{service_name}_{result_listing_stem}_{safe_iface}_{result_actual_filename}"

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
                        f.write(f"UNITYSVC_API_KEY={credentials['api_key']}\n")
                        f.write(f"SERVICE_BASE_URL={credentials['base_url']}\n")
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
    table.add_column("Interface", style="magenta")
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
            test.get("interface", ""),
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
