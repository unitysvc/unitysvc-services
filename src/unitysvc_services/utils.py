"""Utility functions for file handling and data operations."""

import json
from pathlib import Path
from typing import Any

import tomli
import tomli_w


def load_data_file(file_path: Path) -> tuple[dict[str, Any], str]:
    """
    Load a data file (JSON or TOML) and return (data, format).

    Args:
        file_path: Path to the data file

    Returns:
        Tuple of (data dict, format string "json" or "toml")

    Raises:
        ValueError: If file format is not supported
    """
    if file_path.suffix == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f), "json"
    elif file_path.suffix == ".toml":
        with open(file_path, "rb") as f:
            return tomli.load(f), "toml"
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")


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


def find_data_files(data_dir: Path, extensions: list[str] | None = None) -> list[Path]:
    """
    Find all data files in a directory with specified extensions.

    Args:
        data_dir: Directory to search
        extensions: List of extensions to search for (default: ["json", "toml"])

    Returns:
        List of Path objects for matching files
    """
    if extensions is None:
        extensions = ["json", "toml"]

    data_files = []
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


def find_files_by_schema(
    data_dir: Path,
    schema: str,
    path_filter: str | None = None,
    field_filter: dict[str, Any] | None = None,
) -> list[tuple[Path, str, dict[str, Any]]]:
    """
    Find all data files matching a schema with optional filters.

    Args:
        data_dir: Directory to search
        schema: Schema identifier (e.g., "service_v1", "listing_v1")
        path_filter: Optional string that must be in the file path
        field_filter: Optional dict of field:value pairs to filter by

    Returns:
        List of tuples (file_path, format, data) for matching files
    """
    data_files = find_data_files(data_dir)
    matching_files = []

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
            if field_filter:
                if not all(data.get(k) == v for k, v in field_filter.items()):
                    continue

            matching_files.append((data_file, file_format, data))

        except Exception:
            # Skip files that can't be loaded
            continue

    return matching_files
