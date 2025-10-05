"""Data validation module for unitysvc_services."""

import json
import re
import tomllib as toml
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jinja2 import Environment, TemplateSyntaxError
from jsonschema.validators import Draft7Validator


class DataValidator:
    """Validates data files against JSON schemas."""

    def __init__(self, data_dir: Path, schema_dir: Path):
        self.data_dir = data_dir
        self.schema_dir = schema_dir
        self.schemas: dict[str, dict[str, Any]] = {}
        self.load_schemas()

    def load_schemas(self) -> None:
        """Load all JSON schemas from the schema directory."""
        for schema_file in self.schema_dir.glob("*.json"):
            schema_name = schema_file.stem
            try:
                with open(schema_file, encoding="utf-8") as f:
                    schema = json.load(f)
                    self.schemas[schema_name] = schema
            except Exception as e:
                print(f"Error loading schema {schema_file}: {e}")

    def is_url(self, value: str) -> bool:
        """Check if a string is a valid URL."""
        try:
            result = urlparse(value)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def find_union_fields(self, schema: dict[str, Any]) -> set[str]:
        """Find fields that are Union[str, HttpUrl] types in the schema."""
        union_fields: set[str] = set()

        def traverse_schema(obj: Any, path: str = "") -> None:
            if isinstance(obj, dict):
                # Check for Union type with string and URL format
                if "anyOf" in obj:
                    any_of = obj["anyOf"]
                    # Count non-null items for the check
                    non_null_items = [item for item in any_of if item.get("type") != "null"]
                    has_plain_string = any(
                        item.get("type") == "string" and "format" not in item for item in non_null_items
                    )
                    has_uri_string = any(
                        item.get("type") == "string" and item.get("format") == "uri" for item in non_null_items
                    )

                    # Check for Union[str, HttpUrl] or Union[str, HttpUrl, None]
                    if len(non_null_items) == 2 and has_plain_string and has_uri_string:
                        union_fields.add(path)

                # Recursively check properties
                if "properties" in obj:
                    for prop_name, prop_schema in obj["properties"].items():
                        new_path = f"{path}.{prop_name}" if path else prop_name
                        traverse_schema(prop_schema, new_path)

                # Check other schema structures
                for key, value in obj.items():
                    if key not in ["properties", "anyOf"] and isinstance(value, dict | list):
                        traverse_schema(value, path)

            elif isinstance(obj, list):
                for item in obj:
                    traverse_schema(item, path)

        traverse_schema(schema)
        return union_fields

    def validate_file_references(self, data: dict[str, Any], file_path: Path, union_fields: set[str]) -> list[str]:
        """
        Validate that file references in Union[str, HttpUrl] fields exist.

        Also validates that all file_path fields use relative paths.
        """
        errors: list[str] = []

        def check_field(obj: Any, field_path: str, current_path: str = "") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{current_path}.{key}" if current_path else key

                    # Check if this field is a Union[str, HttpUrl] field
                    if (
                        new_path in union_fields
                        and value is not None
                        and isinstance(value, str)
                        and not self.is_url(value)
                    ):
                        # Empty string is not a valid file reference
                        if value == "":
                            errors.append(f"Empty string in field '{new_path}' is not a valid file reference or URL")
                        # It's a file reference, must be relative path
                        elif Path(value).is_absolute():
                            errors.append(
                                f"File reference '{value}' in field '{new_path}' "
                                f"must be a relative path, not an absolute path"
                            )
                        else:
                            referenced_file = file_path.parent / value
                            if not referenced_file.exists():
                                errors.append(
                                    f"File reference '{value}' in field '{new_path}' "
                                    f"does not exist at {referenced_file}"
                                )

                    # Check if this is a file_path field (regardless of schema type)
                    if key == "file_path" and isinstance(value, str):
                        # file_path fields must not be URLs (use external_url instead)
                        if self.is_url(value):
                            errors.append(
                                f"File path '{value}' in field '{new_path}' "
                                f"must not be a URL. Use 'external_url' field for URLs instead."
                            )
                        # All file_path fields must use relative paths
                        elif Path(value).is_absolute():
                            errors.append(
                                f"File path '{value}' in field '{new_path}' "
                                f"must be a relative path, not an absolute path"
                            )

                    # Recurse into nested objects
                    if isinstance(value, dict | list):
                        check_field(value, field_path, new_path)

            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    if isinstance(item, dict | list):
                        check_field(item, field_path, f"{current_path}[{i}]")

        check_field(data, str(file_path))
        return errors

    def validate_name_consistency(self, data: dict[str, Any], file_path: Path, schema_name: str) -> list[str]:
        """Validate that the name field matches the directory name."""
        errors: list[str] = []

        # Only validate files with a 'name' field
        if "name" not in data:
            return errors

        name_value = data["name"]
        if not isinstance(name_value, str):
            return errors

        # Determine expected directory name based on file type
        if file_path.name in ["provider.json", "provider.toml"]:
            # For provider.json, the directory should match the provider name
            directory_name = file_path.parent.name
            if self._normalize_name(name_value) != self._normalize_name(directory_name):
                errors.append(
                    f"Provider name '{name_value}' does not match directory name '{directory_name}'. "
                    f"Expected directory name to match normalized provider name: '{self._normalize_name(name_value)}'"
                )

        elif file_path.name in ["service.json", "service.toml"]:
            # For service.json, the service directory should match the service name
            service_directory_name = file_path.parent.name
            if self._normalize_name(name_value) != self._normalize_name(service_directory_name):
                normalized_name = self._normalize_name(name_value)
                errors.append(
                    f"Service name '{name_value}' does not match "
                    f"service directory name '{service_directory_name}'. "
                    f"Expected service directory name to match "
                    f"normalized service name: '{normalized_name}'"
                )

        return errors

    def _normalize_name(self, name: str) -> str:
        """Normalize a name for directory comparison."""
        # Convert to lowercase and replace spaces/special chars with hyphens
        normalized = re.sub(r"[^a-zA-Z0-9]+", "-", name.lower())
        # Remove leading/trailing hyphens
        normalized = normalized.strip("-")
        return normalized

    def load_data_file(self, file_path: Path) -> tuple[dict[str, Any] | None, list[str]]:
        """Load data from JSON or TOML file."""
        errors: list[str] = []

        try:
            if file_path.suffix == ".toml":
                with open(file_path, "rb") as f:
                    data = toml.load(f)
            elif file_path.suffix == ".json":
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
            else:
                return None, [f"Unsupported file format: {file_path.suffix}"]
            return data, errors
        except Exception as e:
            format_name = {".json": "JSON", ".toml": "TOML"}.get(file_path.suffix, "data")
            return None, [f"Failed to parse {format_name}: {e}"]

    def validate_data_file(self, file_path: Path) -> tuple[bool, list[str]]:
        """Validate a single data file (JSON or TOML)."""
        errors: list[str] = []

        data, load_errors = self.load_data_file(file_path)
        if load_errors:
            return False, load_errors

        # data could be None if loading failed
        if data is None:
            return False, ["Failed to load data file"]

        # Check for schema field
        if "schema" not in data:
            return False, ["Missing 'schema' field in data file"]

        schema_name = data["schema"]

        # Check if schema exists
        if schema_name not in self.schemas:
            return False, [f"Schema '{schema_name}' not found in schema directory"]

        schema = self.schemas[schema_name]

        # Validate against schema with format checking enabled
        try:
            validator = Draft7Validator(schema, format_checker=Draft7Validator.FORMAT_CHECKER)
            validator.check_schema(schema)  # Validate the schema itself
            validation_errors = list(validator.iter_errors(data))
            for error in validation_errors:
                errors.append(f"Schema validation error: {error.message}")
                if error.absolute_path:
                    errors.append(f"  Path: {'.'.join(str(p) for p in error.absolute_path)}")
        except Exception as e:
            errors.append(f"Validation error: {e}")

        # Find Union[str, HttpUrl] fields and validate file references
        union_fields = self.find_union_fields(schema)
        file_ref_errors = self.validate_file_references(data, file_path, union_fields)
        errors.extend(file_ref_errors)

        # Validate name consistency with directory name
        name_errors = self.validate_name_consistency(data, file_path, schema_name)
        errors.extend(name_errors)

        return len(errors) == 0, errors

    def validate_md_file(self, file_path: Path) -> tuple[bool, list[str]]:
        """Validate a markdown file (basic existence check and Jinja2 syntax)."""
        errors: list[str] = []

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                return True, []

            # Validate Jinja2 syntax
            try:
                env = Environment()
                env.parse(content)
            except TemplateSyntaxError as e:
                errors.append(f"Jinja2 syntax error: {e.message} at line {e.lineno}")
            except Exception as e:
                errors.append(f"Jinja2 validation error: {e}")

            return len(errors) == 0, errors
        except Exception as e:
            return False, [f"Failed to read markdown file: {e}"]

    def validate_seller_uniqueness(self) -> tuple[bool, list[str]]:
        """
        Validate that there is exactly one seller_v1 file in the data directory.

        Each repository should have one and only one seller.json file using the seller_v1 schema.
        """
        errors: list[str] = []
        seller_files: list[Path] = []

        if not self.data_dir.exists():
            return True, []

        # Find all data files with seller_v1 schema
        for file_path in self.data_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in [".json", ".toml"]:
                try:
                    data, load_errors = self.load_data_file(file_path)
                    if data and "schema" in data and data["schema"] == "seller_v1":
                        seller_files.append(file_path.relative_to(self.data_dir))
                except Exception:
                    # Skip files that can't be loaded (they'll be caught by other validation)
                    continue

        # Check count
        if len(seller_files) == 0:
            errors.append(
                "No seller file found. Each repository must have exactly one data file using the 'seller_v1' schema."
            )
        elif len(seller_files) > 1:
            errors.append(f"Found {len(seller_files)} seller files, but only one is allowed per repository:")
            for seller_file in seller_files:
                errors.append(f"  - {seller_file}")

        return len(errors) == 0, errors

    def validate_all(self) -> dict[str, tuple[bool, list[str]]]:
        """Validate all files in the data directory."""
        results: dict[str, tuple[bool, list[str]]] = {}

        if not self.data_dir.exists():
            return results

        # First, validate seller uniqueness (repository-level validation)
        seller_valid, seller_errors = self.validate_seller_uniqueness()
        if not seller_valid:
            results["_seller_uniqueness"] = (False, seller_errors)

        # Find all data and MD files recursively
        for file_path in self.data_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in [".json", ".toml", ".md"]:
                relative_path = file_path.relative_to(self.data_dir)

                if file_path.suffix in [".json", ".toml"]:
                    is_valid, errors = self.validate_data_file(file_path)
                elif file_path.suffix == ".md":
                    is_valid, errors = self.validate_md_file(file_path)
                else:
                    continue

                results[str(relative_path)] = (is_valid, errors)

        return results
