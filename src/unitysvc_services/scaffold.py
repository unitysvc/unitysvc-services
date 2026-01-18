#!/usr/bin/env python3
"""
Initialize new provider or service data structure.

This module provides functions to create new directory structures for providers or services
by copying from existing examples or data directories and updating the name fields.
"""

import json
import shutil
import sys
import tomllib  # Built-in since Python 3.11
from datetime import datetime
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

try:
    import tomli_w

    TOML_WRITE_AVAILABLE = True
except ImportError:
    TOML_WRITE_AVAILABLE = False

TOML_AVAILABLE = TOML_WRITE_AVAILABLE  # For backward compatibility

# YAML support has been removed
YAML_AVAILABLE = False


# Constants
DATA_FILE_EXTENSIONS = [".json", ".toml"]
DEFAULT_FORMAT = "toml"


def find_source_directory(source_name: str, base_dirs: list[Path]) -> Path | None:
    """Find the source directory in the given base directories."""
    # Handle absolute paths (starting with /)
    if source_name.startswith("/"):
        # Remove leading slash and treat as relative path from base directories
        relative_path = source_name.lstrip("/")
        for base_dir in base_dirs:
            if not base_dir.exists():
                continue
            source_path = base_dir / relative_path
            if source_path.exists() and source_path.is_dir():
                return source_path
        return None

    # Handle relative paths (existing behavior)
    for base_dir in base_dirs:
        if not base_dir.exists():
            continue

        # Look for exact match first
        source_path = base_dir / source_name
        if source_path.exists() and source_path.is_dir():
            return source_path

        # Look for nested directories (e.g., provider1/service1)
        for provider_dir in base_dir.iterdir():
            if provider_dir.is_dir() and provider_dir.name != "README.md":
                nested_path = provider_dir / source_name
                if nested_path.exists() and nested_path.is_dir():
                    return nested_path

    return None


def load_data_file(file_path: Path) -> dict[str, Any]:
    """Load data from JSON or TOML file."""
    suffix = file_path.suffix.lower()

    if suffix == ".json":
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    elif suffix == ".toml":
        with open(file_path, "rb") as f:
            return tomllib.load(f)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")


def save_data_file(file_path: Path, data: dict[str, Any]) -> None:
    """Save data to JSON or TOML file."""
    suffix = file_path.suffix.lower()

    if suffix == ".json":
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    elif suffix == ".toml":
        if not TOML_WRITE_AVAILABLE:
            raise ImportError("tomli_w is required to write TOML files. Install with: pip install tomli-w")
        with open(file_path, "wb") as f:
            tomli_w.dump(data, f)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")


def detect_source_format(source_dir: Path) -> str:
    """Detect the primary format used in the source directory."""
    # Look for data files and determine the most common format
    format_counts = {"json": 0, "toml": 0}

    for file_path in source_dir.rglob("*"):
        if file_path.is_file():
            suffix = file_path.suffix.lower()
            if suffix == ".json":
                format_counts["json"] += 1
            elif suffix == ".toml":
                format_counts["toml"] += 1

    # Return the format with the highest count, default to toml if no data files found
    if max(format_counts.values()) == 0:
        return "toml"

    return max(format_counts, key=lambda x: format_counts[x])


def normalize_name(name: str) -> str:
    """Normalize a name to match the expected directory format (replace underscores with hyphens)."""
    return name.replace("_", "-")


def discover_schemas(schema_dir: Path) -> dict[str, dict[str, Any]]:
    """Discover available schemas by scanning the schema directory."""
    schemas: dict[str, dict[str, Any]] = {}
    if not schema_dir.exists():
        return schemas

    for schema_file in schema_dir.glob("*.json"):
        schema_name = schema_file.stem
        try:
            with open(schema_file, encoding="utf-8") as f:
                schema_data = json.load(f)
                schemas[schema_name] = schema_data
        except Exception as e:
            print(f"Warning: Could not load schema {schema_file}: {e}", file=sys.stderr)

    return schemas


def generate_example_value(property_def: dict, property_name: str, schema_name: str) -> Any:
    """Generate an example value based on JSON schema property definition."""
    # Handle default values first
    if "default" in property_def:
        return property_def["default"]

    # Handle anyOf (union types)
    if "anyOf" in property_def:
        # Find the first non-null type
        for option in property_def["anyOf"]:
            if option.get("type") != "null":
                return generate_example_value(option, property_name, schema_name)
        return None

    # Handle $ref (references to definitions)
    if "$ref" in property_def and property_def["$ref"].startswith("#/$defs/"):
        # For now, handle simple enum references
        # This would need the full schema context to resolve properly
        # For CategoryEnum, return "AI" as default
        if "Category" in property_def["$ref"]:
            return "AI"
        return "reference_value"

    prop_type = property_def.get("type", "string")

    if prop_type == "string":
        format_type = property_def.get("format")
        if format_type == "email":
            return "contact@example.com"
        elif format_type == "uri":
            return "https://example.com"
        elif format_type == "date-time":
            return datetime.now().isoformat() + "Z"
        elif property_name in [
            "terms_of_service",
            "documentation",
            "api_documentation",
            "code_example",
        ]:
            # These are likely file references or URLs
            file_mappings = {
                "terms_of_service": "terms-of-service.md",
                "code_example": "code-example.md",
                "api_documentation": "api-docs.md",
            }
            return file_mappings.get(property_name, "https://docs.example.com")
        else:
            # Generate meaningful example based on property name
            if property_name == "name":
                return "placeholder_name"  # Will be replaced with actual name
            elif property_name == "description":
                return f"Description for {schema_name.replace('_', ' ')}"
            elif "email" in property_name.lower():
                return "contact@example.com"
            elif "homepage" in property_name.lower():
                return "https://example.com"
            else:
                return f"Example {property_name}"

    elif prop_type == "object":
        # Handle object properties
        additional_props = property_def.get("additionalProperties")
        if additional_props is True:
            # additionalProperties: true - create example object based on property name
            if property_name == "access_method":
                return {
                    "type": "REST_API",
                    "authentication": "API_KEY",
                    "endpoint": "https://api.example.com",
                }
            else:
                return {"example_key": "example_value"}
        elif isinstance(additional_props, dict) and additional_props.get("type") == "string":
            # additionalProperties with string type - create example key-value pairs
            return {
                "feature1": "Feature description 1",
                "feature2": "Feature description 2",
            }
        return {}

    elif prop_type == "array":
        items_def = property_def.get("items", {})
        if items_def.get("type") == "object":
            # Generate example array with one object
            example_obj = {}
            if "properties" in items_def:
                for item_prop, item_def in items_def["properties"].items():
                    example_obj[item_prop] = generate_example_value(item_def, item_prop, schema_name)
            return [example_obj]
        return []

    elif prop_type == "number" or prop_type == "integer":
        return 1

    elif prop_type == "boolean":
        return True

    return None


def generate_data_from_schema(schema_def: dict, schema_name: str, dir_name: str) -> dict[str, Any]:
    """Generate example data based on JSON schema definition."""
    data = {}

    properties = schema_def.get("properties", {})
    required = schema_def.get("required", [])

    for prop_name, prop_def in properties.items():
        # Generate value for this property
        value = generate_example_value(prop_def, prop_name, schema_name)

        # Special handling for certain fields
        if prop_name == "name":
            if "service" in schema_name:
                data[prop_name] = normalize_name(dir_name)
            else:
                data[prop_name] = dir_name
        elif prop_name == "schema":
            data[prop_name] = schema_name
        elif value is not None:  # Only add non-None values to avoid TOML serialization issues
            data[prop_name] = value
        # Skip None values unless they're required
        elif prop_name in required:
            # For required fields that would be None, provide a placeholder
            data[prop_name] = f"placeholder_{prop_name}"

    return data


def get_data_filename_from_schema(schema_name: str, format_type: str) -> str:
    """Get the appropriate filename based on schema name and format."""
    if "provider" in schema_name:
        return f"provider.{format_type}"
    elif "service" in schema_name:
        return f"service.{format_type}"
    else:
        # For unknown schemas, use the schema name as filename
        base_name = schema_name.replace("_v", "").replace("_", "-")
        return f"{base_name}.{format_type}"


def create_additional_files_from_schema(dest_dir: Path, schema_def: dict, schema_name: str, dir_name: str) -> list[str]:
    """Create additional files based on schema requirements (like terms-of-service.md)."""
    created_files = []

    properties = schema_def.get("properties", {})

    for prop_name, prop_def in properties.items():
        # Look for properties that reference markdown files
        # Check both direct type and anyOf types for string properties
        is_string_type = False
        if prop_def.get("type") == "string":
            is_string_type = True
        elif "anyOf" in prop_def:
            # Check if any of the anyOf options is a string type
            for option in prop_def["anyOf"]:
                if option.get("type") == "string":
                    is_string_type = True
                    break

        if is_string_type and prop_name in [
            "terms_of_service",
            "code_example",
            "api_documentation",
        ]:
            filename = generate_example_value(prop_def, prop_name, schema_name)

            # Only create file if it's a .md reference (not a URL)
            if filename and ".md" in str(filename) and not filename.startswith("http"):
                file_path = dest_dir / filename

                if prop_name == "terms_of_service":
                    content = f"# Terms of Service for {dir_name}\n\nPlaceholder terms of service document.\n"
                elif prop_name == "code_example":
                    content = f"# Code Example for {dir_name}\n\nPlaceholder code example.\n"
                elif prop_name == "api_documentation":
                    content = f"# API Documentation for {dir_name}\n\nPlaceholder API documentation.\n"
                else:
                    content = f"# {prop_name.replace('_', ' ').title()} for {dir_name}\n\nPlaceholder content.\n"

                file_path.write_text(content, encoding="utf-8")
                created_files.append(filename)

    return created_files


def handle_destination_directory(dest_dir: Path, force: bool = False) -> None:
    """Handle destination directory creation, removing existing if force is True, otherwise ignore if exists."""
    if dest_dir.exists():
        if force:
            print(f"Removing existing directory: {dest_dir}")
            shutil.rmtree(dest_dir)
        else:
            print(f"Skipping existing directory: {dest_dir}")
            return

    dest_dir.mkdir(parents=True, exist_ok=True)


def update_string_references(obj, old_values: set[str], new_values: dict[str, str], context: str = "") -> bool:
    """Recursively update string references in nested data structures.

    Args:
        obj: The object to update (dict or list)
        old_values: Set of old values to look for
        new_values: Dict mapping old values to new values
        context: Context for logging (optional)

    Returns:
        True if any updates were made
    """
    updated = False

    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, str) and value in old_values:
                new_value = new_values[value]
                print(f"  Converting{context}: '{value}' -> '{new_value}'")
                obj[key] = new_value
                updated = True
            else:
                if update_string_references(value, old_values, new_values, context):
                    updated = True
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, str) and item in old_values:
                new_value = new_values[item]
                print(f"  Converting{context}: '{item}' -> '{new_value}'")
                obj[i] = new_value
                updated = True
            else:
                if update_string_references(item, old_values, new_values, context):
                    updated = True

    return updated


def create_schema_based_structure(
    dest_dir: Path,
    dir_name: str,
    schema_name: str,
    format_type: str = DEFAULT_FORMAT,
    force: bool = False,
) -> None:
    """Create a directory structure with minimal valid data based on the specified schema."""
    # Check if directory already exists before processing
    if dest_dir.exists() and not force:
        print(f"Skipping existing directory: {dest_dir}")
        return

    handle_destination_directory(dest_dir, force)

    # Discover available schemas
    project_root = Path(__file__).parent.parent
    schema_dir = project_root / "schema"
    available_schemas = discover_schemas(schema_dir)

    if schema_name not in available_schemas:
        schema_list = ", ".join(available_schemas.keys()) if available_schemas else "none"
        print(
            f"Error: Unknown schema '{schema_name}'. Available schemas: {schema_list}",
            file=sys.stderr,
        )
        sys.exit(1)

    schema_def = available_schemas[schema_name]

    # Generate data based on schema definition
    try:
        data = generate_data_from_schema(schema_def, schema_name, dir_name)

        # Create additional files based on schema requirements
        created_files = create_additional_files_from_schema(dest_dir, schema_def, schema_name, dir_name)

        # Save the data file
        data_filename = get_data_filename_from_schema(schema_name, format_type)
        data_path = dest_dir / data_filename
        save_data_file(data_path, data)

        # Print summary
        print(f"Created {schema_name} dataset: {dest_dir}")
        for created_file in created_files:
            print(f"  Added: {created_file}")
        print(f"  Added: {data_path.name}")

    except Exception as e:
        print(f"Error generating data from schema: {e}", file=sys.stderr)
        sys.exit(1)


def create_empty_structure(
    dest_dir: Path,
    dir_name: str,
    format_type: str = DEFAULT_FORMAT,
    force: bool = False,
) -> None:
    """Create an empty directory structure with README.md and data file in specified format."""
    # Check if directory already exists before processing
    if dest_dir.exists() and not force:
        print(f"Skipping existing directory: {dest_dir}")
        return

    handle_destination_directory(dest_dir, force)

    # Create data file with name and schema fields in the specified format
    data_path = dest_dir / f"data.{format_type}"
    data_content = {"name": dir_name, "schema": "scheme"}

    # Save using the appropriate format
    save_data_file(data_path, data_content)

    print(f"Created empty directory: {dest_dir}")
    print(f"  Added: {data_path.name}")


def copy_and_update_structure(
    source_dir: Path,
    dest_dir: Path,
    new_name: str,
    copy_data: bool = True,
    project_root: Path | None = None,
    format_type: str = DEFAULT_FORMAT,
    force: bool = False,
) -> None:
    """Copy source directory to destination and update names."""
    # Check if directory already exists before processing
    if dest_dir.exists() and not force:
        print(f"Skipping existing directory: {dest_dir}")
        return

    handle_destination_directory(dest_dir, force)

    print(f"Copying from: {source_dir}")
    print(f"Creating: {dest_dir}")

    def process_directory(source_path: Path, dest_path: Path, relative_path: str = ""):
        """Recursively process directory contents."""
        dest_path.mkdir(parents=True, exist_ok=True)

        # Collect .md files in current source directory for reference conversion
        md_files_in_dir = {f.name for f in source_path.iterdir() if f.is_file() and f.suffix == ".md"}

        for item in source_path.iterdir():
            source_file = source_path / item.name
            dest_file = dest_path / item.name

            if source_file.is_dir():
                # Recursively process subdirectory
                new_relative = f"{relative_path}/{item.name}" if relative_path else item.name
                process_directory(source_file, dest_file, new_relative)
            elif source_file.is_file():
                # Handle files based on type
                if source_file.suffix == ".md":
                    # 1. Copy .md files only if copy_data is True
                    if copy_data:
                        shutil.copy2(source_file, dest_file)
                elif source_file.suffix.lower() in DATA_FILE_EXTENSIONS:
                    # 2. Process data files
                    try:
                        data = load_data_file(source_file)

                        # Update name field to match directory name
                        if "name" in data:
                            if source_file.name.startswith("service."):
                                # Service file - use normalized name (matches the directory it will be in)
                                data["name"] = normalize_name(new_name)
                            else:
                                # Provider file - use the new_name
                                data["name"] = new_name

                        # Convert file references to absolute paths if not copying data
                        if not copy_data:
                            # Create mapping of file references to absolute paths
                            # Use source directory path, not destination path
                            # Calculate the path relative to the data directory
                            if project_root and "example_data" in str(source_dir):
                                # Source is in example_data, get relative path from example_data
                                source_relative_to_base = source_dir.relative_to(project_root / "example_data")
                            elif project_root and "data" in str(source_dir):
                                # Source is in data directory, get relative path from data
                                source_relative_to_base = source_dir.relative_to(project_root / "data")
                            else:
                                # Fallback: use the source directory name
                                source_relative_to_base = Path(source_dir.name)

                            if relative_path:
                                # For nested directories, append the relative path
                                source_path_with_relative = source_relative_to_base / relative_path
                            else:
                                # For root level, use just the source path
                                source_path_with_relative = source_relative_to_base

                            path_prefix = f"/{source_path_with_relative}"
                            new_values = {md_file: f"{path_prefix}/{md_file}" for md_file in md_files_in_dir}

                            update_string_references(data, md_files_in_dir, new_values, " file reference")

                        # Save the updated data file in the specified format
                        # Determine the new file path with the correct extension
                        if format_type != "json" or dest_file.suffix.lower() != ".json":
                            # Change extension to match the format
                            dest_file_with_format = dest_file.parent / f"{dest_file.stem}.{format_type}"
                            print(f"  Converting format: {dest_file.name} -> {dest_file_with_format.name}")
                        else:
                            dest_file_with_format = dest_file

                        save_data_file(dest_file_with_format, data)

                    except Exception as e:
                        print(
                            f"  Warning: Could not process {source_file}: {e}",
                            file=sys.stderr,
                        )
                        # Copy the file as-is if we can't process it
                        shutil.copy2(source_file, dest_file)
                else:
                    # Copy other files as-is
                    shutil.copy2(source_file, dest_file)

    # Process the entire directory structure
    process_directory(source_dir, dest_dir)

    # Rename service directories to match normalized names and update any absolute paths
    normalized_name = normalize_name(new_name)
    for item in dest_dir.iterdir():
        if (
            item.is_dir()
            and any((item / f"service{ext}").exists() for ext in DATA_FILE_EXTENSIONS)
            and item.name != normalized_name
        ):
            old_name = item.name
            new_path = dest_dir / normalized_name
            print(f"  Renaming service directory: {old_name} -> {normalized_name}")
            item.rename(new_path)

            # Update the name field in the service data file to match the new directory name
            for ext_with_dot in DATA_FILE_EXTENSIONS:
                ext = ext_with_dot.lstrip(".")
                service_file = new_path / f"service.{ext}"
                if service_file.exists():
                    try:
                        data = load_data_file(service_file)
                        if "name" in data:
                            print(
                                f"  Updating service name to match directory: '{data['name']}' -> '{normalized_name}'"
                            )
                            data["name"] = normalized_name
                            save_data_file(service_file, data)
                    except Exception as e:
                        print(
                            f"  Warning: Could not update service name in {service_file}: {e}",
                            file=sys.stderr,
                        )

            # Update any absolute paths that reference the old directory name
            if not copy_data:

                def fix_renamed_paths_in_files(old_dir_name: str, new_dir_name: str):
                    data_files = [file for ext in DATA_FILE_EXTENSIONS for file in dest_dir.glob(f"**/*{ext}")]
                    for data_file in data_files:
                        try:
                            data = load_data_file(data_file)

                            # Find all strings that start with the old directory path
                            def collect_old_paths(obj, old_paths, new_path_mappings):
                                if isinstance(obj, dict):
                                    for value in obj.values():
                                        if isinstance(value, str) and value.startswith(f"/{old_dir_name}/"):
                                            old_paths.add(value)
                                            new_path_mappings[value] = value.replace(
                                                f"/{old_dir_name}/",
                                                f"/{new_dir_name}/",
                                                1,
                                            )
                                        else:
                                            collect_old_paths(value, old_paths, new_path_mappings)
                                elif isinstance(obj, list):
                                    for item in obj:
                                        if isinstance(item, str) and item.startswith(f"/{old_dir_name}/"):
                                            old_paths.add(item)
                                            new_path_mappings[item] = item.replace(
                                                f"/{old_dir_name}/",
                                                f"/{new_dir_name}/",
                                                1,
                                            )
                                        else:
                                            collect_old_paths(item, old_paths, new_path_mappings)

                            old_paths: set[str] = set()
                            new_path_mappings: dict[str, str] = {}
                            collect_old_paths(data, old_paths, new_path_mappings)

                            if old_paths:
                                updated = update_string_references(
                                    data,
                                    old_paths,
                                    new_path_mappings,
                                    " path after rename",
                                )
                                if updated:
                                    save_data_file(data_file, data)

                        except Exception as e:
                            print(
                                f"  Warning: Could not update paths in {data_file}: {e}",
                                file=sys.stderr,
                            )

                fix_renamed_paths_in_files(old_name, normalized_name)

    print(f"✓ Successfully created '{dest_dir}' from '{source_dir}'")


# Typer CLI app for init commands
app = typer.Typer(help="Initialize new data files from schemas")
console = Console()


@app.command("offering")
def init_offering(
    name: str = typer.Argument(..., help="Name for the new service offering"),
    output_dir: Path = typer.Option(
        Path.cwd() / "data",
        "--output-dir",
        "-o",
        help="Output directory (default: ./data)",
    ),
    format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: json or toml",
    ),
    source: str | None = typer.Option(
        None,
        "--source",
        "-s",
        help="Copy from existing service offering directory",
    ),
):
    """Create a new service offering skeleton."""
    # Prepare arguments for scaffold
    if source:
        # Copy mode
        base_dirs = [Path.cwd() / "data", Path.cwd()]
        source_dir = find_source_directory(source, base_dirs)
        if not source_dir:
            console.print(
                f"[red]✗[/red] Source directory not found: {source}",
                style="bold red",
            )
            raise typer.Exit(code=1)

        console.print(f"[blue]Copying from:[/blue] {source_dir}")
        console.print(f"[blue]Creating:[/blue] {name}")
        console.print(f"[blue]Format:[/blue] {format}\n")

        try:
            copy_and_update_structure(
                source_dir=source_dir,
                dest_dir=output_dir / name,
                new_name=name,
                copy_data=False,
                project_root=None,
                format_type=format,
                force=False,
            )
            console.print(f"[green]✓[/green] Service offering created: {output_dir / name}")
        except Exception as e:
            console.print(
                f"[red]✗[/red] Failed to create service offering: {e}",
                style="bold red",
            )
            raise typer.Exit(code=1)
    else:
        # Generate from schema
        console.print(f"[blue]Creating service offering:[/blue] {name}")
        console.print(f"[blue]Output directory:[/blue] {output_dir}")
        console.print(f"[blue]Format:[/blue] {format}\n")

        try:
            create_schema_based_structure(
                dest_dir=output_dir / name,
                dir_name=name,
                schema_name="service_v1",
                format_type=format,
                force=False,
            )
            console.print(f"[green]✓[/green] Service offering created: {output_dir / name}")
        except Exception as e:
            console.print(
                f"[red]✗[/red] Failed to create service offering: {e}",
                style="bold red",
            )
            raise typer.Exit(code=1)


@app.command("listing")
def init_listing(
    name: str = typer.Argument(..., help="Name for the new service listing"),
    output_dir: Path = typer.Option(
        Path.cwd() / "data",
        "--output-dir",
        "-o",
        help="Output directory (default: ./data)",
    ),
    format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: json or toml",
    ),
    source: str | None = typer.Option(
        None,
        "--source",
        "-s",
        help="Copy from existing service listing directory",
    ),
):
    """Create a new service listing skeleton."""
    # Prepare arguments for scaffold
    if source:
        # Copy mode
        base_dirs = [Path.cwd() / "data", Path.cwd()]
        source_dir = find_source_directory(source, base_dirs)
        if not source_dir:
            console.print(
                f"[red]✗[/red] Source directory not found: {source}",
                style="bold red",
            )
            raise typer.Exit(code=1)

        console.print(f"[blue]Copying from:[/blue] {source_dir}")
        console.print(f"[blue]Creating:[/blue] {name}")
        console.print(f"[blue]Format:[/blue] {format}\n")

        try:
            copy_and_update_structure(
                source_dir=source_dir,
                dest_dir=output_dir / name,
                new_name=name,
                copy_data=False,
                project_root=None,
                format_type=format,
                force=False,
            )
            console.print(f"[green]✓[/green] Service listing created: {output_dir / name}")
        except Exception as e:
            console.print(
                f"[red]✗[/red] Failed to create service listing: {e}",
                style="bold red",
            )
            raise typer.Exit(code=1)
    else:
        # Generate from schema
        console.print(f"[blue]Creating service listing:[/blue] {name}")
        console.print(f"[blue]Output directory:[/blue] {output_dir}")
        console.print(f"[blue]Format:[/blue] {format}\n")

        try:
            create_schema_based_structure(
                dest_dir=output_dir / name,
                dir_name=name,
                schema_name="listing_v1",
                format_type=format,
                force=False,
            )
            console.print(f"[green]✓[/green] Service listing created: {output_dir / name}")
        except Exception as e:
            console.print(
                f"[red]✗[/red] Failed to create service listing: {e}",
                style="bold red",
            )
            raise typer.Exit(code=1)


@app.command("provider")
def init_provider(
    name: str = typer.Argument(..., help="Name for the new provider"),
    output_dir: Path = typer.Option(
        Path.cwd() / "data",
        "--output-dir",
        "-o",
        help="Output directory (default: ./data)",
    ),
    format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: json or toml",
    ),
    source: str | None = typer.Option(
        None,
        "--source",
        "-s",
        help="Copy from existing provider directory",
    ),
):
    """Create a new provider skeleton."""
    # Prepare arguments for scaffold
    if source:
        # Copy mode
        base_dirs = [Path.cwd() / "data", Path.cwd()]
        source_dir = find_source_directory(source, base_dirs)
        if not source_dir:
            console.print(
                f"[red]✗[/red] Source directory not found: {source}",
                style="bold red",
            )
            raise typer.Exit(code=1)

        console.print(f"[blue]Copying from:[/blue] {source_dir}")
        console.print(f"[blue]Creating:[/blue] {name}")
        console.print(f"[blue]Format:[/blue] {format}\n")

        try:
            copy_and_update_structure(
                source_dir=source_dir,
                dest_dir=output_dir / name,
                new_name=name,
                copy_data=False,
                project_root=None,
                format_type=format,
                force=False,
            )
            console.print(f"[green]✓[/green] Provider created: {output_dir / name}")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to create provider: {e}", style="bold red")
            raise typer.Exit(code=1)
    else:
        # Generate from schema
        console.print(f"[blue]Creating provider:[/blue] {name}")
        console.print(f"[blue]Output directory:[/blue] {output_dir}")
        console.print(f"[blue]Format:[/blue] {format}\n")

        try:
            create_schema_based_structure(
                dest_dir=output_dir / name,
                dir_name=name,
                schema_name="provider_v1",
                format_type=format,
                force=False,
            )
            console.print(f"[green]✓[/green] Provider created: {output_dir / name}")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to create provider: {e}", style="bold red")
            raise typer.Exit(code=1)


@app.command("seller")
def init_seller(
    name: str = typer.Argument(..., help="Name for the new seller"),
    output_dir: Path = typer.Option(
        Path.cwd() / "data",
        "--output-dir",
        "-o",
        help="Output directory (default: ./data)",
    ),
    format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: json or toml",
    ),
    source: str | None = typer.Option(
        None,
        "--source",
        "-s",
        help="Copy from existing seller file",
    ),
):
    """Create a new seller skeleton."""
    # Prepare arguments for scaffold
    if source:
        # Copy mode - for seller, source is a file not a directory
        base_dirs = [Path.cwd() / "data", Path.cwd()]
        source_path = None

        # Try to find the source file
        for base_dir in base_dirs:
            potential_path = base_dir / source
            if potential_path.exists() and potential_path.is_file():
                source_path = potential_path
                break
            # Also try with common seller filenames
            for filename in ["seller.json", "seller.toml"]:
                potential_file = base_dir / source / filename
                if potential_file.exists():
                    source_path = potential_file
                    break
            if source_path:
                break

        if not source_path:
            console.print(
                f"[red]✗[/red] Source seller file not found: {source}",
                style="bold red",
            )
            raise typer.Exit(code=1)

        console.print(f"[blue]Copying from:[/blue] {source_path}")
        console.print(f"[blue]Creating:[/blue] seller.{format}")
        console.print(f"[blue]Output directory:[/blue] {output_dir}\n")

        try:
            # Load source file
            if source_path.suffix == ".json":
                with open(source_path) as f:
                    data = json.load(f)
            else:  # .toml
                with open(source_path, "rb") as f:
                    data = tomllib.load(f)

            # Update name
            data["name"] = name

            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)

            # Write to output format
            output_file = output_dir / f"seller.{format}"
            if format == "json":
                with open(output_file, "w") as f:
                    json.dump(data, f, indent=2)
                    f.write("\n")
            else:  # toml
                if not TOML_WRITE_AVAILABLE:
                    console.print(
                        "[red]✗[/red] TOML write support not available. Install tomli_w.",
                        style="bold red",
                    )
                    raise typer.Exit(code=1)
                with open(output_file, "wb") as f:
                    tomli_w.dump(data, f)

            console.print(f"[green]✓[/green] Seller created: {output_file}")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to create seller: {e}", style="bold red")
            raise typer.Exit(code=1)
    else:
        # Generate from schema
        console.print(f"[blue]Creating seller:[/blue] {name}")
        console.print(f"[blue]Output directory:[/blue] {output_dir}")
        console.print(f"[blue]Format:[/blue] {format}\n")

        try:
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)

            # Get schema directory
            pkg_path = Path(__file__).parent
            schema_dir = pkg_path / "schema"

            # Load schema to generate example
            schema_file = schema_dir / "seller_v1.json"
            if not schema_file.exists():
                raise FileNotFoundError(f"Schema file not found: {schema_file}")

            with open(schema_file) as f:
                json.load(f)

            # Create basic seller data from schema
            seller_data = {
                "schema": "seller_v1",
                "time_created": datetime.utcnow().isoformat() + "Z",
                "name": name,
                "display_name": name.replace("-", " ").replace("_", " ").title(),
                "seller_type": "individual",
                "contact_email": "contact@example.com",
                "description": f"{name} seller",
                "is_active": True,
                "is_verified": False,
            }

            # Write to file
            output_file = output_dir / f"seller.{format}"
            if format == "json":
                with open(output_file, "w") as f:
                    json.dump(seller_data, f, indent=2)
                    f.write("\n")
            else:  # toml
                if not TOML_WRITE_AVAILABLE:
                    console.print(
                        "[red]✗[/red] TOML write support not available. Install tomli_w.",
                        style="bold red",
                    )
                    raise typer.Exit(code=1)
                with open(output_file, "wb") as f:
                    tomli_w.dump(seller_data, f)

            console.print(f"[green]✓[/green] Seller created: {output_file}")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to create seller: {e}", style="bold red")
            raise typer.Exit(code=1)
