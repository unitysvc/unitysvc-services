"""Data validation module for unitysvc_services."""

import json
import re
import tomllib as toml
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import typer
from jinja2 import Environment, TemplateSyntaxError
from jsonschema.validators import Draft7Validator
from rich.console import Console

import unitysvc_services


class DataValidationError(Exception):
    """Exception raised when data validation fails."""

    pass


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
                        # Check that the file exists
                        else:
                            referenced_file = file_path.parent / value
                            if not referenced_file.exists():
                                errors.append(
                                    f"File reference '{value}' in field '{new_path}' "
                                    f"does not exist at {referenced_file}"
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

    def validate_with_pydantic_model(self, data: dict[str, Any], schema_name: str) -> list[str]:
        """
        Validate data using Pydantic models for additional validation rules.

        This complements JSON schema validation with Pydantic field validators
        like name format validation.

        Args:
            data: The data to validate
            schema_name: The schema name (e.g., 'provider_v1', 'seller_v1')

        Returns:
            List of validation error messages
        """
        from pydantic import BaseModel

        from unitysvc_services.models import ListingV1, ProviderV1, SellerV1, ServiceV1

        errors: list[str] = []

        # Map schema names to Pydantic model classes
        model_map: dict[str, type[BaseModel]] = {
            "provider_v1": ProviderV1,
            "seller_v1": SellerV1,
            "service_v1": ServiceV1,
            "listing_v1": ListingV1,
        }

        if schema_name not in model_map:
            return errors  # No Pydantic model for this schema

        model_class = model_map[schema_name]

        try:
            # Validate using the Pydantic model
            model_class.model_validate(data)

        except Exception as e:
            # Extract meaningful error message from Pydantic ValidationError
            error_msg = str(e)
            # Pydantic errors can be verbose, try to extract just the relevant part
            if "validation error" in error_msg.lower():
                errors.append(f"Pydantic validation error: {error_msg}")
            else:
                errors.append(error_msg)

        return errors

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

        # Also validate using Pydantic models for additional validation rules
        pydantic_errors = self.validate_with_pydantic_model(data, schema_name)
        errors.extend(pydantic_errors)

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
            # Skip hidden directories (those starting with .)
            if any(part.startswith(".") for part in file_path.parts):
                continue

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

    def validate_provider_status(self) -> tuple[bool, list[str]]:
        """
        Validate provider status and warn about services under disabled/incomplete providers.

        Returns tuple of (is_valid, warnings) where warnings indicate services
        that will be affected by provider status.
        """
        from unitysvc_services.models.base import ProviderStatusEnum
        from unitysvc_services.models.provider_v1 import ProviderV1

        warnings: list[str] = []

        # Find all provider files (skip hidden directories)
        provider_files = [
            f for f in self.data_dir.glob("*/provider.*") if not any(part.startswith(".") for part in f.parts)
        ]

        for provider_file in provider_files:
            try:
                # Load provider data using existing helper method
                data, load_errors = self.load_data_file(provider_file)
                if load_errors or data is None:
                    warnings.append(f"Failed to load provider file {provider_file}: {load_errors}")
                    continue

                # Parse as ProviderV1
                provider = ProviderV1.model_validate(data)
                provider_dir = provider_file.parent
                provider_name = provider.name

                # Check if provider is not active
                if provider.status != ProviderStatusEnum.active:
                    # Find all services under this provider
                    services_dir = provider_dir / "services"
                    if services_dir.exists():
                        service_count = len(list(services_dir.iterdir()))
                        if service_count > 0:
                            warnings.append(
                                f"Provider '{provider_name}' has status '{provider.status}' but has {service_count} "
                                f"service(s). All services under this provider will be affected."
                            )

            except Exception as e:
                warnings.append(f"Error checking provider status in {provider_file}: {e}")

        # Return True (valid) but with warnings
        return True, warnings

    def validate_seller_status(self) -> tuple[bool, list[str]]:
        """
        Validate seller status and warn if seller is disabled/incomplete.

        Returns tuple of (is_valid, warnings) where warnings indicate seller issues.
        """
        from unitysvc_services.models.base import SellerStatusEnum
        from unitysvc_services.models.seller_v1 import SellerV1

        warnings: list[str] = []

        # Find all seller files (skip hidden files)
        seller_files = [f for f in self.data_dir.glob("seller.*") if not f.name.startswith(".")]

        for seller_file in seller_files:
            try:
                # Load seller data using existing helper method
                data, load_errors = self.load_data_file(seller_file)
                if load_errors or data is None:
                    warnings.append(f"Failed to load seller file {seller_file}: {load_errors}")
                    continue

                # Parse as SellerV1
                seller = SellerV1.model_validate(data)
                seller_name = seller.name

                # Check if seller is not active
                if seller.status != SellerStatusEnum.active:
                    warnings.append(
                        f"Seller '{seller_name}' has status '{seller.status}'. Seller will not be published to backend."
                    )

            except Exception as e:
                warnings.append(f"Error checking seller status in {seller_file}: {e}")

        # Return True (valid) but with warnings
        return True, warnings

    def validate_all(self) -> dict[str, tuple[bool, list[str]]]:
        """Validate all files in the data directory."""
        results: dict[str, tuple[bool, list[str]]] = {}

        if not self.data_dir.exists():
            return results

        # First, validate seller uniqueness (repository-level validation)
        seller_valid, seller_errors = self.validate_seller_uniqueness()
        if not seller_valid:
            results["_seller_uniqueness"] = (False, seller_errors)

        # Validate seller status
        seller_status_valid, seller_warnings = self.validate_seller_status()
        if seller_warnings:
            results["_seller_status"] = (True, seller_warnings)  # Warnings, not errors

        # Validate provider status and check for affected services
        provider_status_valid, provider_warnings = self.validate_provider_status()
        if provider_warnings:
            results["_provider_status"] = (
                True,
                provider_warnings,
            )  # Warnings, not errors

        # Find all data and MD files recursively, skipping hidden directories
        for file_path in self.data_dir.rglob("*"):
            # Skip hidden directories (those starting with .)
            if any(part.startswith(".") for part in file_path.parts):
                continue

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

    def validate_directory_data(self, directory: Path) -> None:
        """Validate data files in a directory for consistency.

        Validation rules:
        1. All service_v1 files in same directory must have unique names
        2. All listing_v1 files must reference a service name that exists in the same directory
        3. If service_name is defined in listing_v1, it must match a service in the directory

        Args:
            directory: Directory containing data files to validate

        Raises:
            DataValidationError: If validation fails
        """
        # Find all JSON and TOML files in the directory (not recursive)
        data_files: list[Path] = []
        for pattern in ["*.json", "*.toml"]:
            data_files.extend(directory.glob(pattern))

        # Load all files and categorize by schema
        services: dict[str, Path] = {}  # name -> file_path
        listings: list[tuple[Path, dict[str, Any]]] = []  # list of (file_path, data)

        for file_path in data_files:
            try:
                data, load_errors = self.load_data_file(file_path)
                if load_errors or data is None:
                    continue

                schema = data.get("schema")

                if schema == "service_v1":
                    service_name = data.get("name")
                    if not service_name:
                        raise DataValidationError(f"Service file {file_path} missing 'name' field")

                    # Check for duplicate service names in same directory
                    if service_name in services:
                        raise DataValidationError(
                            f"Duplicate service name '{service_name}' found in directory {directory}:\n"
                            f"  - {services[service_name]}\n"
                            f"  - {file_path}"
                        )

                    services[service_name] = file_path

                elif schema == "listing_v1":
                    listings.append((file_path, data))

            except Exception as e:
                # Skip files that can't be loaded or don't have schema
                if isinstance(e, DataValidationError):
                    raise
                continue

        # Validate listings reference valid services
        for listing_file, listing_data in listings:
            service_name = listing_data.get("service_name")

            if service_name:
                # If service_name is explicitly defined, it must match a service in the directory
                if service_name not in services:
                    available_services = ", ".join(services.keys()) if services else "none"
                    raise DataValidationError(
                        f"Listing file {listing_file} references service_name '{service_name}' "
                        f"which does not exist in the same directory.\n"
                        f"Available services: {available_services}"
                    )
            else:
                # If service_name not defined, there should be exactly one service in the directory
                if len(services) == 0:
                    raise DataValidationError(
                        f"Listing file {listing_file} does not specify 'service_name' "
                        f"and no service files found in the same directory."
                    )
                elif len(services) > 1:
                    available_services = ", ".join(services.keys())
                    raise DataValidationError(
                        f"Listing file {listing_file} does not specify 'service_name' "
                        f"but multiple services exist in the same directory: {available_services}. "
                        f"Please add 'service_name' field to the listing to specify which service it belongs to."
                    )

    def validate_all_service_directories(self, data_dir: Path) -> list[str]:
        """
        Validate all service directories in a directory tree.

        Returns a list of validation error messages (empty if all valid).
        """
        errors = []

        # Find all directories containing service or listing files
        directories_to_validate = set()

        for pattern in ["*.json", "*.toml"]:
            for file_path in data_dir.rglob(pattern):
                # Skip hidden directories (those starting with .)
                if any(part.startswith(".") for part in file_path.parts):
                    continue

                try:
                    data, load_errors = self.load_data_file(file_path)
                    if load_errors or data is None:
                        continue

                    schema = data.get("schema")
                    if schema in ["service_v1", "listing_v1"]:
                        directories_to_validate.add(file_path.parent)
                except Exception:
                    continue

        # Validate each directory
        for directory in sorted(directories_to_validate):
            try:
                self.validate_directory_data(directory)
            except DataValidationError as e:
                errors.append(str(e))

        return errors


# CLI command
app = typer.Typer(help="Validate data files")
console = Console()


@app.command()
def validate(
    data_dir: Path | None = typer.Argument(
        None,
        help="Directory containing data files to validate (default: current directory)",
    ),
):
    """
    Validate data consistency in service and listing files.

    Checks:
    1. Service names are unique within each directory
    2. Listing files reference valid service names
    3. Multiple services in a directory require explicit service_name in listings
    """
    # Determine data directory
    if data_dir is None:
        data_dir = Path.cwd()

    if not data_dir.exists():
        console.print(f"[red]✗[/red] Data directory not found: {data_dir}")
        raise typer.Exit(1)

    console.print(f"[cyan]Validating data files in:[/cyan] {data_dir}")
    console.print()

    # Get schema directory from installed package
    schema_dir = Path(unitysvc_services.__file__).parent / "schema"

    # Create validator and run validation
    validator = DataValidator(data_dir, schema_dir)

    # Run comprehensive validation (schema, file references, etc.)
    all_results = validator.validate_all()
    validation_errors = []

    # Collect all errors from validate_all()
    for file_path, (is_valid, errors) in all_results.items():
        if not is_valid and errors:
            for error in errors:
                validation_errors.append(f"{file_path}: {error}")

    # Also run service directory validation (service/listing relationships)
    directory_errors = validator.validate_all_service_directories(data_dir)
    validation_errors.extend(directory_errors)

    if validation_errors:
        console.print(f"[red]✗ Validation failed with {len(validation_errors)} error(s):[/red]")
        console.print()
        for i, error in enumerate(validation_errors, 1):
            console.print(f"[red]{i}.[/red] {error}")
            console.print()
        raise typer.Exit(1)
    else:
        console.print("[green]✓ All data files are valid![/green]")
