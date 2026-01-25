"""Utility functions for file handling and data operations.

This module contains shared utilities used by both unitysvc-services SDK
and unitysvc backend, including:
- Content hashing and content-addressable storage key generation
- File extension and MIME type utilities
- Data file loading and merging
"""

import hashlib
import json
import os
import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Any

import json5
import tomli_w
from jinja2 import Template

# =============================================================================
# Content Hashing and File Utilities
# These functions are shared with unitysvc backend for content-addressable storage
# =============================================================================


def compute_file_hash(content: bytes) -> str:
    """Compute SHA256 hash of file content.

    Args:
        content: File content as bytes

    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(content).hexdigest()


def generate_content_based_key(content: bytes, extension: str | None = None) -> str:
    """Generate content-based object key using file hash.

    This creates a content-addressable storage key that ensures:
    - Automatic deduplication (same content = same object_key)
    - Optimal caching (content-addressable URLs)

    Args:
        content: File content as bytes
        extension: File extension (without dot)

    Returns:
        Content-based object key (hash.extension or just hash)
    """
    file_hash = compute_file_hash(content)

    if extension:
        # Remove leading dot if present
        extension = extension.lstrip(".")
        return f"{file_hash}.{extension}"

    return file_hash


def get_file_extension(filename: str) -> str | None:
    """Extract file extension from filename.

    Args:
        filename: Filename with or without path

    Returns:
        Extension without dot, or None if no extension
    """
    if not filename:
        return None

    # Get basename first (remove path)
    basename = os.path.basename(filename)

    # Split extension
    _, ext = os.path.splitext(basename)

    # Return without the dot
    return ext.lstrip(".") if ext else None


def get_basename(filename: str) -> str:
    """Get basename from filename (removes path).

    Args:
        filename: Filename with or without path

    Returns:
        Basename without path
    """
    return os.path.basename(filename) if filename else ""


def mime_type_to_extension(mime_type: str) -> str:
    """Convert MIME type to file extension.

    Args:
        mime_type: MIME type string

    Returns:
        File extension without dot
    """
    # Common MIME type to extension mappings
    mime_map = {
        "text": "txt",
        "plain": "txt",
        "text/plain": "txt",
        "text/html": "html",
        "text/markdown": "md",
        "text/csv": "csv",
        "application/json": "json",
        "application/pdf": "pdf",
        "application/xml": "xml",
        "application/x-yaml": "yaml",
        "application/octet-stream": "bin",
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/gif": "gif",
        "markdown": "md",
        "html": "html",
        "json": "json",
        "pdf": "pdf",
        "xml": "xml",
        "yaml": "yaml",
        "csv": "csv",
        "url": "url",
    }

    # Try exact match first
    mime_lower = mime_type.lower()
    if mime_lower in mime_map:
        return mime_map[mime_lower]

    # Try to extract from mime type parts
    if "/" in mime_lower:
        _, subtype = mime_lower.split("/", 1)
        if subtype in mime_map:
            return mime_map[subtype]

    # Default to txt
    return "txt"


# =============================================================================
# Data File Operations
# =============================================================================


def deep_merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    Deep merge two dictionaries, with override values taking precedence.

    For nested dictionaries, performs recursive merge. For all other types
    (lists, primitives), the override value completely replaces the base value.

    Args:
        base: Base dictionary
        override: Override dictionary (values take precedence)

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = deep_merge_dicts(result[key], value)
        else:
            # For all other types (lists, primitives, etc.), override completely
            result[key] = value

    return result


def load_data_file(
    file_path: Path, *, skip_override: bool = False
) -> tuple[dict[str, Any], str]:
    """
    Load a data file (JSON or TOML) and return (data, format).

    Automatically checks for and merges override files with the pattern:
    <base_name>.override.<extension>

    For example:
    - offering.json -> service.override.json
    - provider.toml -> provider.override.toml

    If an override file exists, it will be deep-merged with the base file,
    with override values taking precedence.

    Args:
        file_path: Path to the data file
        skip_override: If True, skip loading and merging override files.
            Useful for commands that need the original local data without
            server-synced overrides (e.g., example list/run commands).

    Returns:
        Tuple of (data dict, format string "json" or "toml")

    Raises:
        ValueError: If file format is not supported
    """
    # Load the base file
    if file_path.suffix == ".json":
        with open(file_path, encoding="utf-8") as f:
            data = json5.load(f)
        file_format = "json"
    elif file_path.suffix == ".toml":
        with open(file_path, "rb") as f:
            data = tomllib.load(f)
        file_format = "toml"
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")

    # Check for override file (unless skip_override is True)
    # Pattern: <stem>.override.<suffix>
    # Example: offering.json -> offering.override.json
    if not skip_override:
        override_path = file_path.with_stem(f"{file_path.stem}.override")

        if override_path.exists():
            # Load the override file (same format as base file)
            if override_path.suffix == ".json":
                with open(override_path, encoding="utf-8") as f:
                    override_data = json5.load(f)
            elif override_path.suffix == ".toml":
                with open(override_path, "rb") as f:
                    override_data = tomllib.load(f)
            else:
                # This shouldn't happen since we're using the same suffix as base
                # But handle it gracefully
                override_data = {}

            # Deep merge the override data into the base data
            data = deep_merge_dicts(data, override_data)

    return data, file_format


def write_data_file(file_path: Path, data: dict[str, Any], format: str) -> None:
    """
    Write data back to file in the specified format.

    Args:
        file_path: Path to the data file
        data: Data dictionary to write
        format: Format string ("json" or "toml")

    Raises:
        ValueError: If format is not supported
    """
    if format == "json":
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
    elif format == "toml":
        with open(file_path, "wb") as f:
            tomli_w.dump(data, f)
    else:
        raise ValueError(f"Unsupported format: {format}")


def write_override_file(
    base_file: Path,
    override_data: dict[str, Any],
    delete_if_empty: bool = False,
) -> Path | None:
    """
    Write or update an override file for a data file.

    Override files follow the pattern: <stem>.override.<suffix>
    For example: listing.json -> listing.override.json

    If the override file exists, the new data is deep-merged with existing data.
    If it doesn't exist, a new file is created.

    Args:
        base_file: Path to the base data file (e.g., listing.json)
        override_data: Data to write/merge into the override file
        delete_if_empty: If True, delete the override file when data is empty

    Returns:
        Path to the override file, or None if deleted

    Example:
        >>> write_override_file(Path("listing.json"), {"service_id": "abc-123"})
        PosixPath('listing.override.json')
    """
    # Determine override file path
    override_path = base_file.with_stem(f"{base_file.stem}.override")

    # Determine format from base file extension
    if base_file.suffix == ".json":
        file_format = "json"
    elif base_file.suffix == ".toml":
        file_format = "toml"
    else:
        # Default to JSON for unknown formats
        file_format = "json"
        override_path = base_file.parent / f"{base_file.stem}.override.json"

    # Load existing override data if file exists
    if override_path.exists():
        if file_format == "json":
            with open(override_path, encoding="utf-8") as f:
                existing_data = json5.load(f)
        else:
            with open(override_path, "rb") as f:
                existing_data = tomllib.load(f)

        # Deep merge new data into existing
        merged_data = deep_merge_dicts(existing_data, override_data)
    else:
        merged_data = override_data

    # Handle empty data case
    if delete_if_empty and not merged_data:
        if override_path.exists():
            override_path.unlink()
        return None

    # Write the override file
    write_data_file(override_path, merged_data, file_format)

    return override_path


def read_override_file(base_file: Path) -> dict[str, Any]:
    """
    Read an override file for a data file if it exists.

    Args:
        base_file: Path to the base data file (e.g., listing.json)

    Returns:
        Override data dict, or empty dict if no override file exists
    """
    # Determine override file path
    override_path = base_file.with_stem(f"{base_file.stem}.override")

    if not override_path.exists():
        return {}

    # Determine format from base file extension
    if base_file.suffix == ".json":
        with open(override_path, encoding="utf-8") as f:
            return json5.load(f)
    elif base_file.suffix == ".toml":
        with open(override_path, "rb") as f:
            return tomllib.load(f)
    else:
        # Try JSON first for unknown formats
        try:
            with open(override_path, encoding="utf-8") as f:
                return json5.load(f)
        except Exception:
            return {}


@lru_cache(maxsize=128)
def find_data_files(data_dir: Path, extensions: tuple[str, ...] | None = None) -> list[Path]:
    """
    Find all data files in a directory with specified extensions.

    Args:
        data_dir: Directory to search
        extensions: Tuple of extensions to search for (default: ("json", "toml"))

    Returns:
        List of Path objects for matching files
    """
    if extensions is None:
        extensions = ("json", "toml")

    data_files: list[Path] = []
    for ext in extensions:
        data_files.extend(data_dir.rglob(f"*.{ext}"))

    return data_files


def find_file_by_schema_and_name(
    data_dir: Path, schema: str, name_field: str, name_value: str
) -> tuple[Path, str, dict[str, Any]] | None:
    """
    Find a data file by schema type and name field value.

    Args:
        data_dir: Directory to search
        schema: Schema identifier (e.g., "offering_v1", "listing_v1")
        name_field: Field name to match (e.g., "name", "seller_name")
        name_value: Value to match in the name field

    Returns:
        Tuple of (file_path, format, data) if found, None otherwise
    """
    data_files = find_data_files(data_dir)

    for data_file in data_files:
        try:
            data, file_format = load_data_file(data_file)
            if data.get("schema") == schema and data.get(name_field) == name_value:
                return data_file, file_format, data
        except Exception:
            # Skip files that can't be loaded
            continue

    return None


@lru_cache(maxsize=256)
def find_files_by_schema(
    data_dir: Path,
    schema: str,
    path_filter: str | None = None,
    field_filter: tuple[tuple[str, Any], ...] | None = None,
    skip_override: bool = False,
) -> list[tuple[Path, str, dict[str, Any]]]:
    """
    Find all data files matching a schema with optional filters.

    Args:
        data_dir: Directory to search
        schema: Schema identifier (e.g., "offering_v1", "listing_v1")
        path_filter: Optional string that must be in the file path
        field_filter: Optional tuple of (key, value) pairs to filter by
        skip_override: If True, skip loading override files (use base data only)

    Returns:
        List of tuples (file_path, format, data) for matching files
    """
    data_files = find_data_files(data_dir)
    matching_files: list[tuple[Path, str, dict[str, Any]]] = []

    # Convert field_filter tuple back to dict for filtering
    field_filter_dict = dict(field_filter) if field_filter else None

    for data_file in data_files:
        try:
            # Apply path filter
            if path_filter and path_filter not in str(data_file):
                continue

            data, file_format = load_data_file(data_file, skip_override=skip_override)

            # Check schema
            if data.get("schema") != schema:
                continue

            # Apply field filters
            if field_filter_dict:
                if not all(data.get(k) == v for k, v in field_filter_dict.items()):
                    continue

            matching_files.append((data_file, file_format, data))

        except Exception:
            # Skip files that can't be loaded
            continue

    return matching_files


def resolve_provider_name(file_path: Path) -> str | None:
    """
    Resolve the provider name from the file path.

    The provider name is determined by the directory structure:
    - For service offerings: <provider_name>/services/<service_name>/service.{json,toml}
    - For service listings: <provider_name>/services/<service_name>/listing-*.{json,toml}

    Args:
        file_path: Path to the service offering or listing file

    Returns:
        Provider name if found in directory structure, None otherwise
    """
    # Check if file is under a "services" directory
    parts = file_path.parts

    try:
        # Find the "services" directory in the path
        services_idx = parts.index("services")

        # Provider name is the directory before "services"
        if services_idx > 0:
            provider_dir = parts[services_idx - 1]

            # The provider directory should contain a provider data file
            # Get the full path to the provider directory
            provider_path = Path(*parts[:services_idx])

            # Look for provider data file to validate and get the actual provider name
            for data_file in find_data_files(provider_path):
                try:
                    # Only check files in the provider directory itself, not subdirectories
                    if data_file.parent == provider_path:
                        data, _file_format = load_data_file(data_file)
                        if data.get("schema") == "provider_v1":
                            return data.get("name")
                except Exception:
                    continue

            # Fallback to directory name if no provider file found
            return provider_dir
    except (ValueError, IndexError):
        # "services" not in path or invalid structure
        pass

    return None


def resolve_service_name_for_listing(listing_file: Path, listing_data: dict[str, Any] | None = None) -> str | None:
    """
    Resolve the service name for a listing file.

    Finds the offering file in the same directory and returns its name.
    Each service directory must have exactly one offering file.

    Args:
        listing_file: Path to the listing file
        listing_data: Unused, kept for backwards compatibility

    Returns:
        Service name if found, None otherwise
    """
    listing_dir = listing_file.parent

    # Find the service offering file in the same directory
    for data_file in find_data_files(listing_dir):
        try:
            data, _file_format = load_data_file(data_file)
            if data.get("schema") == "offering_v1":
                return data.get("name")
        except Exception:
            continue

    # No offering file found
    return None


def convert_convenience_fields_to_documents(
    data: dict[str, Any],
    base_path: Path,
    *,
    logo_field: str = "logo",
    terms_field: str | None = "terms_of_service",
) -> dict[str, Any]:
    """
    Convert convenience fields (logo, terms_of_service) to Document objects.

    This utility function converts file paths or URLs in convenience fields
    to proper Document structures that can be stored in the backend.

    Args:
        data: Data dictionary containing potential convenience fields
        base_path: Base path for resolving relative file paths
        logo_field: Name of the logo field (default: "logo")
        terms_field: Name of the terms of service field (default: "terms_of_service", None to skip)

    Returns:
        Updated data dictionary with convenience fields converted to documents dict

    Example:
        >>> data = {"logo": "assets/logo.png", "documents": {}}
        >>> result = convert_convenience_fields_to_documents(data, Path("/data/provider"))
        >>> # Result will have logo removed and added to documents dict
    """
    # Initialize documents dict if not present
    if "documents" not in data or data["documents"] is None:
        data["documents"] = {}

    # Helper to determine MIME type from file path/URL
    def get_mime_type(path_or_url: str) -> str:
        path_lower = path_or_url.lower()
        if path_lower.endswith((".png", ".jpg", ".jpeg")):
            return "png" if ".png" in path_lower else "jpeg"
        elif path_lower.endswith(".svg"):
            return "svg"
        elif path_lower.endswith(".pdf"):
            return "pdf"
        elif path_lower.endswith(".md"):
            return "markdown"
        else:
            # Default to URL if it looks like a URL, otherwise markdown
            return "url" if path_or_url.startswith("http") else "markdown"

    # Convert logo field
    if logo_field in data and data[logo_field]:
        logo_value = data[logo_field]
        logo_doc: dict[str, Any] = {
            "category": "logo",
            "mime_type": get_mime_type(str(logo_value)),
            "is_public": True,
        }

        # Check if it's a URL or file path
        if str(logo_value).startswith("http"):
            logo_doc["external_url"] = str(logo_value)
        else:
            # It's a file path - will be resolved by resolve_file_references
            logo_doc["file_path"] = str(logo_value)

        data["documents"]["Company Logo"] = logo_doc
        # Remove the convenience field
        del data[logo_field]

    # Convert terms_of_service field if specified
    if terms_field and terms_field in data and data[terms_field]:
        terms_value = data[terms_field]
        terms_doc: dict[str, Any] = {
            "category": "terms_of_service",
            "mime_type": get_mime_type(str(terms_value)),
            "is_public": True,
        }

        # Check if it's a URL or file path
        if str(terms_value).startswith("http"):
            terms_doc["external_url"] = str(terms_value)
        else:
            # It's a file path - will be resolved by resolve_file_references
            terms_doc["file_path"] = str(terms_value)

        data["documents"]["Terms of Service"] = terms_doc
        # Remove the convenience field
        del data[terms_field]

    return data


def render_template_file(
    file_path: Path,
    listing: dict[str, Any] | None = None,
    offering: dict[str, Any] | None = None,
    provider: dict[str, Any] | None = None,
    seller: dict[str, Any] | None = None,
    interface: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Render a Jinja2 template file and return content and new filename.

    If the file is not a template (.j2 extension), returns the file content as-is
    and the original filename.

    Args:
        file_path: Path to the file (may or may not be a .j2 template)
        listing: Listing data for template rendering (optional)
        offering: Offering data for template rendering (optional)
        provider: Provider data for template rendering (optional)
        seller: Seller data for template rendering (optional)
        interface: AccessInterface data for template rendering (optional, contains base_url, routing_key, etc.)

    Returns:
        Tuple of (rendered_content, new_filename_without_j2)

    Raises:
        Exception: If template rendering fails
    """
    # Read file content
    with open(file_path, encoding="utf-8") as f:
        file_content = f.read()

    # Check if this is a Jinja2 template
    is_template = file_path.name.endswith(".j2")

    if is_template:
        # Render the template
        template = Template(file_content)
        rendered_content = template.render(
            listing=listing or {},
            offering=offering or {},
            provider=provider or {},
            seller=seller or {},
            interface=interface or {},
        )

        # Strip .j2 from filename
        # Example: test.py.j2 -> test.py
        new_filename = file_path.name[:-3]  # Remove last 3 characters (.j2)

        return rendered_content, new_filename
    else:
        # Not a template - return as-is
        return file_content, file_path.name


def execute_script_content(
    script: str,
    mime_type: str,
    env_vars: dict[str, str],
    output_contains: str | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Execute script content and return results.

    This is a shared utility function used by both the SDK's example runner
    and the backend's Celery task for consistent execution behavior.

    Args:
        script: The script content to execute (expanded, not a template)
        mime_type: Document MIME type ("python", "javascript", "bash")
        env_vars: Environment variables to set (e.g., {"API_KEY": "...", "BASE_URL": "..."})
        output_contains: Optional substring that must appear in stdout for success
        timeout: Execution timeout in seconds (default: 30)

    Returns:
        Result dictionary with:
        - status: "success" | "task_failed" | "script_failed" | "unexpected_output"
        - error: Error message (None if success)
        - exit_code: Script exit code (None if script didn't run)
        - stdout: Standard output (truncated to 1KB)
        - stderr: Standard error (truncated to 1KB)
    """
    import subprocess
    import tempfile

    # Output truncation limit (1KB)
    MAX_OUTPUT_SIZE = 1000

    result: dict[str, Any] = {
        "status": "task_failed",
        "error": None,
        "exit_code": None,
        "stdout": None,
        "stderr": None,
    }

    # Determine interpreter from mime_type
    interpreter_cmd, file_suffix, error = determine_interpreter(script, mime_type)
    if error:
        result["status"] = "task_failed"
        result["error"] = error
        return result

    assert interpreter_cmd is not None, "interpreter_cmd should not be None after error check"

    # Prepare environment
    env = os.environ.copy()
    env.update(env_vars)

    # Write script to temporary file
    temp_file = None
    try:
        temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=file_suffix,
            delete=False,
        )
        temp_file.write(script)
        temp_file.close()
        os.chmod(temp_file.name, 0o755)

        # Execute script
        process = subprocess.run(
            [interpreter_cmd, temp_file.name],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        result["exit_code"] = process.returncode
        result["stdout"] = process.stdout[:MAX_OUTPUT_SIZE] if process.stdout else None
        result["stderr"] = process.stderr[:MAX_OUTPUT_SIZE] if process.stderr else None

        # Determine status
        if process.returncode != 0:
            result["status"] = "script_failed"
            result["error"] = f"Script exited with code {process.returncode}"
        elif output_contains and (not process.stdout or output_contains not in process.stdout):
            result["status"] = "unexpected_output"
            result["error"] = f"Output does not contain: {output_contains}"
        else:
            result["status"] = "success"
            result["error"] = None

    except subprocess.TimeoutExpired:
        result["error"] = f"Script execution timeout ({timeout} seconds)"
    except FileNotFoundError as e:
        result["error"] = f"Interpreter not found: {e}"
    except Exception as e:
        result["error"] = str(e)
    finally:
        if temp_file and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

    return result


def determine_interpreter(
    script: str, mime_type: str
) -> tuple[str | None, str, str | None]:
    """
    Determine the interpreter command for executing a script.

    Checks for shebang line first, then falls back to MIME type-based detection.
    Supported MIME types: "python", "javascript", "bash"

    Args:
        script: The content of the script (used for shebang parsing)
        mime_type: Document MIME type ("python", "javascript", "bash")

    Returns:
        Tuple of (interpreter_cmd, file_suffix, error_message).
        If successful, returns (interpreter_cmd, file_suffix, None).
        If failed, returns (None, "", error_message).

    Examples:
        >>> determine_interpreter("print('hello')", "python")
        ('python3', '.py', None)
        >>> determine_interpreter("console.log('hello')", "javascript")
        ('node', '.js', None)
        >>> determine_interpreter("curl http://example.com", "bash")
        ('bash', '.sh', None)
    """
    import shutil

    # Map MIME type to file suffix
    mime_to_suffix = {
        "python": ".py",
        "javascript": ".js",
        "bash": ".sh",
    }

    file_suffix = mime_to_suffix.get(mime_type, "")
    if not file_suffix:
        return None, "", f"Unsupported MIME type: {mime_type}. Supported: python, javascript, bash"

    # Parse shebang to get interpreter
    lines = script.split("\n")
    interpreter_cmd = None

    # First, try to parse shebang
    if lines and lines[0].startswith("#!"):
        shebang = lines[0][2:].strip()
        if "/env " in shebang:
            # e.g., #!/usr/bin/env python3
            interpreter_cmd = shebang.split("/env ", 1)[1].strip().split()[0]
        else:
            # e.g., #!/usr/bin/python3
            interpreter_cmd = shebang.split("/")[-1].split()[0]

    # If no shebang found, determine interpreter based on MIME type
    if not interpreter_cmd:
        if mime_type == "python":
            # Try python3 first, fallback to python
            if shutil.which("python3"):
                interpreter_cmd = "python3"
            elif shutil.which("python"):
                interpreter_cmd = "python"
            else:
                return None, file_suffix, "Neither 'python3' nor 'python' found."
        elif mime_type == "javascript":
            # JavaScript files need Node.js
            if shutil.which("node"):
                interpreter_cmd = "node"
            else:
                return None, file_suffix, "'node' not found. Please install Node.js."
        elif mime_type == "bash":
            # Shell scripts use bash
            if shutil.which("bash"):
                interpreter_cmd = "bash"
            else:
                return None, file_suffix, "'bash' not found."
    else:
        # Shebang was found - verify the interpreter exists
        if not shutil.which(interpreter_cmd):
            return None, file_suffix, f"Interpreter '{interpreter_cmd}' from shebang not found."

    return interpreter_cmd, file_suffix, None
