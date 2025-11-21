"""Utility functions for file handling and data operations."""

import json
import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Any

import tomli_w
from jinja2 import Template


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


def load_data_file(file_path: Path) -> tuple[dict[str, Any], str]:
    """
    Load a data file (JSON or TOML) and return (data, format).

    Automatically checks for and merges override files with the pattern:
    <base_name>.override.<extension>

    For example:
    - service.json -> service.override.json
    - provider.toml -> provider.override.toml

    If an override file exists, it will be deep-merged with the base file,
    with override values taking precedence.

    Args:
        file_path: Path to the data file

    Returns:
        Tuple of (data dict, format string "json" or "toml")

    Raises:
        ValueError: If file format is not supported
    """
    # Load the base file
    if file_path.suffix == ".json":
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        file_format = "json"
    elif file_path.suffix == ".toml":
        with open(file_path, "rb") as f:
            data = tomllib.load(f)
        file_format = "toml"
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")

    # Check for override file
    # Pattern: <stem>.override.<suffix>
    # Example: service.json -> service.override.json
    override_path = file_path.with_stem(f"{file_path.stem}.override")

    if override_path.exists():
        # Load the override file (same format as base file)
        if override_path.suffix == ".json":
            with open(override_path, encoding="utf-8") as f:
                override_data = json.load(f)
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
        schema: Schema identifier (e.g., "service_v1", "listing_v1")
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
) -> list[tuple[Path, str, dict[str, Any]]]:
    """
    Find all data files matching a schema with optional filters.

    Args:
        data_dir: Directory to search
        schema: Schema identifier (e.g., "service_v1", "listing_v1")
        path_filter: Optional string that must be in the file path
        field_filter: Optional tuple of (key, value) pairs to filter by

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

            data, file_format = load_data_file(data_file)

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


def resolve_service_name_for_listing(listing_file: Path, listing_data: dict[str, Any]) -> str | None:
    """
    Resolve the service name for a listing file.

    Rules:
    1. If service_name is defined in listing_data, return it
    2. Otherwise, find the only service offering in the same directory and return its name

    Args:
        listing_file: Path to the listing file
        listing_data: Listing data dictionary

    Returns:
        Service name if found, None otherwise
    """
    # Rule 1: If service_name is already defined, use it
    if "service_name" in listing_data and listing_data["service_name"]:
        return listing_data["service_name"]

    # Rule 2: Find the only service offering in the same directory
    listing_dir = listing_file.parent

    # Find all service offering files in the same directory
    service_files: list[tuple[Path, str, dict[str, Any]]] = []
    for data_file in find_data_files(listing_dir):
        try:
            data, file_format = load_data_file(data_file)
            if data.get("schema") == "service_v1":
                service_files.append((data_file, file_format, data))
        except Exception:
            continue

    # If there's exactly one service file, use its name
    if len(service_files) == 1:
        _service_file, _service_format, service_data = service_files[0]
        return service_data.get("name")

    # Otherwise, return None (either no service files or multiple service files)
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
        Updated data dictionary with convenience fields converted to documents list

    Example:
        >>> data = {"logo": "assets/logo.png", "documents": []}
        >>> result = convert_convenience_fields_to_documents(data, Path("/data/provider"))
        >>> # Result will have logo removed and added to documents list
    """
    # Initialize documents list if not present
    if "documents" not in data or data["documents"] is None:
        data["documents"] = []

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
            "title": "Company Logo",
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

        data["documents"].append(logo_doc)
        # Remove the convenience field
        del data[logo_field]

    # Convert terms_of_service field if specified
    if terms_field and terms_field in data and data[terms_field]:
        terms_value = data[terms_field]
        terms_doc: dict[str, Any] = {
            "title": "Terms of Service",
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

        data["documents"].append(terms_doc)
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


def determine_interpreter(file_content: str, file_suffix: str) -> tuple[str | None, str | None]:
    """
    Determine the interpreter command for executing a script file.

    Checks for shebang line first, then falls back to file extension-based detection.

    Args:
        file_content: The content of the script file
        file_suffix: The file extension (e.g., ".py", ".js", ".sh")

    Returns:
        Tuple of (interpreter_cmd, error_message). If successful, returns (interpreter_cmd, None).
        If failed, returns (None, error_message).

    Examples:
        >>> determine_interpreter("#!/usr/bin/env python3\\nprint('hello')", ".py")
        ('python3', None)
        >>> determine_interpreter("console.log('hello')", ".js")
        ('node', None)
        >>> determine_interpreter("curl http://example.com", ".sh")
        ('bash', None)
    """
    import shutil

    # Parse shebang to get interpreter
    lines = file_content.split("\n")
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

    # If no shebang found, determine interpreter based on file extension
    if not interpreter_cmd:
        if file_suffix == ".py":
            # Try python3 first, fallback to python
            if shutil.which("python3"):
                interpreter_cmd = "python3"
            elif shutil.which("python"):
                interpreter_cmd = "python"
            else:
                return None, "Neither 'python3' nor 'python' found. Please install Python to run this test."
        elif file_suffix == ".js":
            # JavaScript files need Node.js
            if shutil.which("node"):
                interpreter_cmd = "node"
            else:
                return None, "'node' not found. Please install Node.js to run JavaScript tests."
        elif file_suffix == ".sh":
            # Shell scripts use bash
            if shutil.which("bash"):
                interpreter_cmd = "bash"
            else:
                return None, "'bash' not found. Please install bash to run shell script tests."
        else:
            # Unknown file type - try python3/python as fallback
            if shutil.which("python3"):
                interpreter_cmd = "python3"
            elif shutil.which("python"):
                interpreter_cmd = "python"
            else:
                return None, f"Unknown file type '{file_suffix}' and no Python interpreter found."
    else:
        # Shebang was found - verify the interpreter exists
        if not shutil.which(interpreter_cmd):
            return None, f"Interpreter '{interpreter_cmd}' from shebang not found. Please install it to run this test."

    return interpreter_cmd, None
