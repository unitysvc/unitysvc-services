"""Data publisher module for posting service data to UnitySVC backend."""

import json
import tomllib as toml
from pathlib import Path
from typing import Any, Optional

import httpx
from pydantic import BaseModel


class DataValidationError(Exception):
    """Exception raised when data validation fails."""

    pass


class ServiceDataPublisher:
    """Publishes service data to UnitySVC backend endpoints."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.Client(
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def load_data_file(self, file_path: Path) -> dict[str, Any]:
        """Load data from JSON or TOML file."""
        if file_path.suffix == ".toml":
            with open(file_path, "rb") as f:
                return toml.load(f)
        elif file_path.suffix == ".json":
            with open(file_path, encoding="utf-8") as f:
                return json.load(f)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")

    def load_file_content(self, file_path: Path, base_path: Path) -> str:
        """Load content from a file (text or binary)."""
        full_path = base_path / file_path if not file_path.is_absolute() else file_path

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {full_path}")

        # Try to read as text first
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # If it fails, read as binary and encode as base64
            import base64

            with open(full_path, "rb") as f:
                return base64.b64encode(f.read()).decode("ascii")

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
        data_files = []
        for pattern in ["*.json", "*.toml"]:
            data_files.extend(directory.glob(pattern))

        # Load all files and categorize by schema
        services = {}  # name -> file_path
        listings = []  # list of (file_path, data)

        for file_path in data_files:
            try:
                data = self.load_data_file(file_path)
                schema = data.get("schema")

                if schema == "service_v1":
                    service_name = data.get("name")
                    if not service_name:
                        raise DataValidationError(
                            f"Service file {file_path} missing 'name' field"
                        )

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
                    available_services = (
                        ", ".join(services.keys()) if services else "none"
                    )
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

    def resolve_file_references(
        self, data: dict[str, Any], base_path: Path
    ) -> dict[str, Any]:
        """Recursively resolve file references and include content in data."""
        result = {}

        for key, value in data.items():
            if isinstance(value, dict):
                # Recursively process nested dictionaries
                result[key] = self.resolve_file_references(value, base_path)
            elif isinstance(value, list):
                # Process lists
                result[key] = [
                    (
                        self.resolve_file_references(item, base_path)
                        if isinstance(item, dict)
                        else item
                    )
                    for item in value
                ]
            elif key == "file_path" and isinstance(value, str):
                # This is a file reference - load the content
                # Store both the original path and the content
                result[key] = value
                # Add file_content field if not already present (for DocumentCreate compatibility)
                if "file_content" not in data:
                    try:
                        content = self.load_file_content(Path(value), base_path)
                        result["file_content"] = content
                    except Exception as e:
                        raise ValueError(
                            f"Failed to load file content from '{value}': {e}"
                        )
            else:
                result[key] = value

        return result

    def post_service_offering(self, data_file: Path) -> dict[str, Any]:
        """Post service offering data to the backend.

        Extracts provider_name from the directory structure.
        Expected path: .../{provider_name}/services/{service_name}/...
        """
        # Load the data file
        data = self.load_data_file(data_file)

        # Resolve file references and include content
        base_path = data_file.parent
        data_with_content = self.resolve_file_references(data, base_path)

        # Extract provider_name from directory structure
        # Find the 'services' directory and use its parent as provider_name
        parts = data_file.parts
        try:
            services_idx = parts.index("services")
            provider_name = parts[services_idx - 1]
            data_with_content["provider_name"] = provider_name
        except (ValueError, IndexError):
            raise ValueError(
                f"Cannot extract provider_name from path: {data_file}. "
                f"Expected path to contain .../{{provider_name}}/services/..."
            )

        # Post to the endpoint
        response = self.client.post(
            f"{self.base_url}/publish/service_offering",
            json=data_with_content,
        )
        response.raise_for_status()
        return response.json()

    def post_service_listing(self, data_file: Path) -> dict[str, Any]:
        """Post service listing data to the backend.

        Extracts provider_name from directory structure and service info from service.json.
        Expected path: .../{provider_name}/services/{service_name}/svcreseller.json
        """
        # Load the listing data file
        data = self.load_data_file(data_file)

        # Resolve file references and include content
        base_path = data_file.parent
        data_with_content = self.resolve_file_references(data, base_path)

        # Extract provider_name from directory structure
        parts = data_file.parts
        try:
            services_idx = parts.index("services")
            provider_name = parts[services_idx - 1]
            data_with_content["provider_name"] = provider_name
        except (ValueError, IndexError):
            raise ValueError(
                f"Cannot extract provider_name from path: {data_file}. "
                f"Expected path to contain .../{{provider_name}}/services/..."
            )

        # If service_name is not in listing data, find it from service files in the same directory
        if (
            "service_name" not in data_with_content
            or not data_with_content["service_name"]
        ):
            # Find all service files in the same directory
            service_files = []
            for pattern in ["*.json", "*.toml"]:
                for file_path in data_file.parent.glob(pattern):
                    try:
                        file_data = self.load_data_file(file_path)
                        if file_data.get("schema") == "service_v1":
                            service_files.append((file_path, file_data))
                    except Exception:
                        continue

            if len(service_files) == 0:
                raise ValueError(
                    f"Cannot find any service_v1 files in {data_file.parent}. "
                    f"Listing files must be in the same directory as a service definition."
                )
            elif len(service_files) > 1:
                service_names = [data.get("name") for _, data in service_files]
                raise ValueError(
                    f"Multiple services found in {data_file.parent}: {', '.join(service_names)}. "
                    f"Please add 'service_name' field to {data_file.name} to specify which service this listing belongs to."
                )
            else:
                # Exactly one service found - use it
                service_file, service_data = service_files[0]
                data_with_content["service_name"] = service_data.get("name")
                data_with_content["service_version"] = service_data.get("version")
        else:
            # service_name is provided in listing data, find the matching service to get version
            service_name = data_with_content["service_name"]
            service_found = False

            for pattern in ["*.json", "*.toml"]:
                for file_path in data_file.parent.glob(pattern):
                    try:
                        file_data = self.load_data_file(file_path)
                        if (
                            file_data.get("schema") == "service_v1"
                            and file_data.get("name") == service_name
                        ):
                            data_with_content["service_version"] = file_data.get(
                                "version"
                            )
                            service_found = True
                            break
                    except Exception:
                        continue
                if service_found:
                    break

            if not service_found:
                raise ValueError(
                    f"Service '{service_name}' specified in {data_file.name} not found in {data_file.parent}."
                )

        # Find seller_name from seller definition in the data directory
        # Navigate up to find the data directory and look for seller file
        data_dir = data_file.parent
        while data_dir.name != "data" and data_dir.parent != data_dir:
            data_dir = data_dir.parent

        if data_dir.name != "data":
            raise ValueError(
                f"Cannot find 'data' directory in path: {data_file}. "
                f"Expected path structure includes a 'data' directory."
            )

        # Look for seller file in the data directory
        seller_file = None
        for pattern in ["seller.json", "seller.toml"]:
            potential_seller = data_dir / pattern
            if potential_seller.exists():
                seller_file = potential_seller
                break

        if not seller_file:
            raise ValueError(
                f"Cannot find seller.json or seller.toml in {data_dir}. "
                f"A seller definition is required in the data directory."
            )

        # Load seller data and extract name
        seller_data = self.load_data_file(seller_file)
        if seller_data.get("schema") != "seller_v1":
            raise ValueError(
                f"Seller file {seller_file} does not have schema='seller_v1'"
            )

        seller_name = seller_data.get("name")
        if not seller_name:
            raise ValueError(f"Seller file {seller_file} missing 'name' field")

        data_with_content["seller_name"] = seller_name

        # Map listing_status to status if present
        if "listing_status" in data_with_content:
            data_with_content["status"] = data_with_content.pop("listing_status")

        # Post to the endpoint
        response = self.client.post(
            f"{self.base_url}/publish/service_listing",
            json=data_with_content,
        )
        response.raise_for_status()
        return response.json()

    def post_provider(self, data_file: Path) -> dict[str, Any]:
        """Post provider data to the backend."""
        # Load the data file
        data = self.load_data_file(data_file)

        # Resolve file references and include content
        base_path = data_file.parent
        data_with_content = self.resolve_file_references(data, base_path)

        # Post to the endpoint
        response = self.client.post(
            f"{self.base_url}/providers/",
            json=data_with_content,
        )
        response.raise_for_status()
        return response.json()

    def post_seller(self, data_file: Path) -> dict[str, Any]:
        """Post seller data to the backend."""
        # Load the data file
        data = self.load_data_file(data_file)

        # Resolve file references and include content
        base_path = data_file.parent
        data_with_content = self.resolve_file_references(data, base_path)

        # Post to the endpoint
        response = self.client.post(
            f"{self.base_url}/sellers/",
            json=data_with_content,
        )
        response.raise_for_status()
        return response.json()

    def list_service_offerings(self) -> list[dict[str, Any]]:
        """List all service offerings from the backend.

        Note: This endpoint doesn't exist yet in the backend.
        TODO: Add GET /publish/service_offering endpoint.
        """
        response = self.client.get(f"{self.base_url}/publish/service_offering")
        response.raise_for_status()
        result = response.json()
        # Backend returns {"data": [...], "count": N}
        return result.get("data", result) if isinstance(result, dict) else result

    def list_service_listings(self) -> list[dict[str, Any]]:
        """List all service listings from the backend."""
        response = self.client.get(f"{self.base_url}/services/")
        response.raise_for_status()
        result = response.json()
        # Backend returns {"data": [...], "count": N}
        return result.get("data", result) if isinstance(result, dict) else result

    def list_providers(self) -> list[dict[str, Any]]:
        """List all providers from the backend."""
        response = self.client.get(f"{self.base_url}/providers/")
        response.raise_for_status()
        result = response.json()
        # Backend returns {"data": [...], "count": N}
        return result.get("data", result) if isinstance(result, dict) else result

    def list_sellers(self) -> list[dict[str, Any]]:
        """List all sellers from the backend."""
        response = self.client.get(f"{self.base_url}/sellers/")
        response.raise_for_status()
        result = response.json()
        # Backend returns {"data": [...], "count": N}
        return result.get("data", result) if isinstance(result, dict) else result

    def update_service_offering_status(
        self, offering_id: int | str, status: str
    ) -> dict[str, Any]:
        """
        Update the status of a service offering.

        Allowed statuses (UpstreamStatusEnum):
        - uploading: Service is being uploaded (not ready)
        - ready: Service is ready to be used
        - deprecated: Service is deprecated from upstream
        """
        response = self.client.patch(
            f"{self.base_url}/service_offering/{offering_id}/",
            json={"upstream_status": status},
        )
        response.raise_for_status()
        return response.json()

    def update_service_listing_status(
        self, listing_id: int | str, status: str
    ) -> dict[str, Any]:
        """
        Update the status of a service listing.

        Allowed statuses (ListingStatusEnum):
        - unknown: Not yet determined
        - upstream_ready: Upstream is ready to be used
        - downstream_ready: Downstream is ready with proper routing, logging, and billing
        - ready: Operationally ready (with docs, metrics, and pricing)
        - in_service: Service is in service
        - upstream_deprecated: Service is deprecated from upstream
        - deprecated: Service is no longer offered to users
        """
        response = self.client.patch(
            f"{self.base_url}/service_listing/{listing_id}/",
            json={"listing_status": status},
        )
        response.raise_for_status()
        return response.json()

    def find_offering_files(self, data_dir: Path) -> list[Path]:
        """
        Find all service offering files in a directory tree.

        Searches all JSON and TOML files and checks for schema="service_v1".
        """
        offerings = []
        for pattern in ["*.json", "*.toml"]:
            for file_path in data_dir.rglob(pattern):
                try:
                    data = self.load_data_file(file_path)
                    if data.get("schema") == "service_v1":
                        offerings.append(file_path)
                except Exception:
                    # Skip files that can't be loaded or don't have schema field
                    pass
        return sorted(offerings)

    def find_listing_files(self, data_dir: Path) -> list[Path]:
        """
        Find all service listing files in a directory tree.

        Searches all JSON and TOML files and checks for schema="listing_v1".
        """
        listings = []
        for pattern in ["*.json", "*.toml"]:
            for file_path in data_dir.rglob(pattern):
                try:
                    data = self.load_data_file(file_path)
                    if data.get("schema") == "listing_v1":
                        listings.append(file_path)
                except Exception:
                    # Skip files that can't be loaded or don't have schema field
                    pass
        return sorted(listings)

    def find_provider_files(self, data_dir: Path) -> list[Path]:
        """
        Find all provider files in a directory tree.

        Searches all JSON and TOML files and checks for schema="provider_v1".
        """
        providers = []
        for pattern in ["*.json", "*.toml"]:
            for file_path in data_dir.rglob(pattern):
                try:
                    data = self.load_data_file(file_path)
                    if data.get("schema") == "provider_v1":
                        providers.append(file_path)
                except Exception:
                    # Skip files that can't be loaded or don't have schema field
                    pass
        return sorted(providers)

    def find_seller_files(self, data_dir: Path) -> list[Path]:
        """
        Find all seller files in a directory tree.

        Searches all JSON and TOML files and checks for schema="seller_v1".
        """
        sellers = []
        for pattern in ["*.json", "*.toml"]:
            for file_path in data_dir.rglob(pattern):
                try:
                    data = self.load_data_file(file_path)
                    if data.get("schema") == "seller_v1":
                        sellers.append(file_path)
                except Exception:
                    # Skip files that can't be loaded or don't have schema field
                    pass
        return sorted(sellers)

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
                try:
                    data = self.load_data_file(file_path)
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

    def publish_all_offerings(self, data_dir: Path) -> dict[str, Any]:
        """
        Publish all service offerings found in a directory tree.

        Validates data consistency before publishing.
        Returns a summary of successes and failures.
        """
        # Validate all service directories first
        validation_errors = self.validate_all_service_directories(data_dir)
        if validation_errors:
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "errors": [
                    {"file": "validation", "error": error}
                    for error in validation_errors
                ],
            }

        offering_files = self.find_offering_files(data_dir)
        results = {
            "total": len(offering_files),
            "success": 0,
            "failed": 0,
            "errors": [],
        }

        for offering_file in offering_files:
            try:
                result = self.post_service_offering(offering_file)
                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"file": str(offering_file), "error": str(e)})

        return results

    def publish_all_listings(self, data_dir: Path) -> dict[str, Any]:
        """
        Publish all service listings found in a directory tree.

        Validates data consistency before publishing.
        Returns a summary of successes and failures.
        """
        # Validate all service directories first
        validation_errors = self.validate_all_service_directories(data_dir)
        if validation_errors:
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "errors": [
                    {"file": "validation", "error": error}
                    for error in validation_errors
                ],
            }

        listing_files = self.find_listing_files(data_dir)
        results = {"total": len(listing_files), "success": 0, "failed": 0, "errors": []}

        for listing_file in listing_files:
            try:
                result = self.post_service_listing(listing_file)
                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"file": str(listing_file), "error": str(e)})

        return results

    def publish_all_providers(self, data_dir: Path) -> dict[str, Any]:
        """
        Publish all providers found in a directory tree.

        Returns a summary of successes and failures.
        """
        provider_files = self.find_provider_files(data_dir)
        results = {
            "total": len(provider_files),
            "success": 0,
            "failed": 0,
            "errors": [],
        }

        for provider_file in provider_files:
            try:
                result = self.post_provider(provider_file)
                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"file": str(provider_file), "error": str(e)})

        return results

    def publish_all_sellers(self, data_dir: Path) -> dict[str, Any]:
        """
        Publish all sellers found in a directory tree.

        Returns a summary of successes and failures.
        """
        seller_files = self.find_seller_files(data_dir)
        results = {
            "total": len(seller_files),
            "success": 0,
            "failed": 0,
            "errors": [],
        }

        for seller_file in seller_files:
            try:
                result = self.post_seller(seller_file)
                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"file": str(seller_file), "error": str(e)})

        return results

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# CLI commands for publishing
import typer
from rich.console import Console

app = typer.Typer(help="Publish data to backend")
console = Console()


@app.command("providers")
def publish_providers(
    data_path: Optional[Path] = typer.Argument(
        None,
        help="Path to provider file or directory (default: ./data or UNITYSVC_DATA_DIR env var)",
    ),
    backend_url: Optional[str] = typer.Option(
        None,
        "--backend-url",
        "-u",
        help="UnitySVC backend URL (default: from UNITYSVC_BACKEND_URL env var)",
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key for authentication (default: from UNITYSVC_API_KEY env var)",
    ),
):
    """Publish provider(s) from a file or directory."""
    import os

    # Set data path
    if data_path is None:
        data_path_str = os.getenv("UNITYSVC_DATA_DIR")
        if data_path_str:
            data_path = Path(data_path_str)
        else:
            data_path = Path.cwd() / "data"

    if not data_path.is_absolute():
        data_path = Path.cwd() / data_path

    if not data_path.exists():
        console.print(f"[red]✗[/red] Path not found: {data_path}", style="bold red")
        raise typer.Exit(code=1)

    # Get backend URL from argument or environment
    backend_url = backend_url or os.getenv("UNITYSVC_BACKEND_URL")
    if not backend_url:
        console.print(
            "[red]✗[/red] Backend URL not provided. Use --backend-url or set UNITYSVC_BACKEND_URL env var.",
            style="bold red",
        )
        raise typer.Exit(code=1)

    # Get API key from argument or environment
    api_key = api_key or os.getenv("UNITYSVC_API_KEY")
    if not api_key:
        console.print(
            "[red]✗[/red] API key not provided. Use --api-key or set UNITYSVC_API_KEY env var.",
            style="bold red",
        )
        raise typer.Exit(code=1)

    try:
        with ServiceDataPublisher(backend_url, api_key) as publisher:
            # Handle single file
            if data_path.is_file():
                console.print(f"[blue]Publishing provider:[/blue] {data_path}")
                console.print(f"[blue]Backend URL:[/blue] {backend_url}\n")
                result = publisher.post_provider(data_path)
                console.print(f"[green]✓[/green] Provider published successfully!")
                console.print(f"[cyan]Response:[/cyan] {json.dumps(result, indent=2)}")
            # Handle directory
            else:
                console.print(f"[blue]Scanning for providers in:[/blue] {data_path}")
                console.print(f"[blue]Backend URL:[/blue] {backend_url}\n")
                results = publisher.publish_all_providers(data_path)

                # Display summary
                console.print("\n[bold]Publishing Summary:[/bold]")
                console.print(f"  Total found: {results['total']}")
                console.print(f"  [green]✓ Success:[/green] {results['success']}")
                console.print(f"  [red]✗ Failed:[/red] {results['failed']}")

                # Display errors if any
                if results["errors"]:
                    console.print("\n[bold red]Errors:[/bold red]")
                    for error in results["errors"]:
                        console.print(f"  [red]✗[/red] {error['file']}")
                        console.print(f"    {error['error']}")

                if results["failed"] > 0:
                    raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(
            f"[red]✗[/red] Failed to publish providers: {e}", style="bold red"
        )
        raise typer.Exit(code=1)


@app.command("sellers")
def publish_sellers(
    data_path: Optional[Path] = typer.Argument(
        None,
        help="Path to seller file or directory (default: ./data or UNITYSVC_DATA_DIR env var)",
    ),
    backend_url: Optional[str] = typer.Option(
        None,
        "--backend-url",
        "-u",
        help="UnitySVC backend URL (default: from UNITYSVC_BACKEND_URL env var)",
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key for authentication (default: from UNITYSVC_API_KEY env var)",
    ),
):
    """Publish seller(s) from a file or directory."""
    import os

    # Set data path
    if data_path is None:
        data_path_str = os.getenv("UNITYSVC_DATA_DIR")
        if data_path_str:
            data_path = Path(data_path_str)
        else:
            data_path = Path.cwd() / "data"

    if not data_path.is_absolute():
        data_path = Path.cwd() / data_path

    if not data_path.exists():
        console.print(f"[red]✗[/red] Path not found: {data_path}", style="bold red")
        raise typer.Exit(code=1)

    # Get backend URL
    backend_url = backend_url or os.getenv("UNITYSVC_BACKEND_URL")
    if not backend_url:
        console.print(
            "[red]✗[/red] Backend URL not provided. Use --backend-url or set UNITYSVC_BACKEND_URL env var.",
            style="bold red",
        )
        raise typer.Exit(code=1)

    # Get API key
    api_key = api_key or os.getenv("UNITYSVC_API_KEY")
    if not api_key:
        console.print(
            "[red]✗[/red] API key not provided. Use --api-key or set UNITYSVC_API_KEY env var.",
            style="bold red",
        )
        raise typer.Exit(code=1)

    try:
        with ServiceDataPublisher(backend_url, api_key) as publisher:
            # Handle single file
            if data_path.is_file():
                console.print(f"[blue]Publishing seller:[/blue] {data_path}")
                console.print(f"[blue]Backend URL:[/blue] {backend_url}\n")
                result = publisher.post_seller(data_path)
                console.print(f"[green]✓[/green] Seller published successfully!")
                console.print(f"[cyan]Response:[/cyan] {json.dumps(result, indent=2)}")
            # Handle directory
            else:
                console.print(f"[blue]Scanning for sellers in:[/blue] {data_path}")
                console.print(f"[blue]Backend URL:[/blue] {backend_url}\n")
                results = publisher.publish_all_sellers(data_path)

                console.print(f"\n[bold]Publishing Summary:[/bold]")
                console.print(f"  Total found: {results['total']}")
                console.print(f"  [green]✓ Success: {results['success']}[/green]")
                console.print(f"  [red]✗ Failed: {results['failed']}[/red]")

                if results["errors"]:
                    console.print("\n[bold red]Errors:[/bold red]")
                    for error in results["errors"]:
                        console.print(f"  [red]✗[/red] {error['file']}")
                        console.print(f"    {error['error']}")
                    raise typer.Exit(code=1)
                else:
                    console.print(
                        f"\n[green]✓[/green] All sellers published successfully!"
                    )

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to publish sellers: {e}", style="bold red")
        raise typer.Exit(code=1)


@app.command("offerings")
def publish_offerings(
    data_path: Optional[Path] = typer.Argument(
        None,
        help="Path to service offering file or directory (default: ./data or UNITYSVC_DATA_DIR env var)",
    ),
    backend_url: Optional[str] = typer.Option(
        None,
        "--backend-url",
        "-u",
        help="UnitySVC backend URL (default: from UNITYSVC_BACKEND_URL env var)",
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key for authentication (default: from UNITYSVC_API_KEY env var)",
    ),
):
    """Publish service offering(s) from a file or directory."""
    import os

    # Set data path
    if data_path is None:
        data_path_str = os.getenv("UNITYSVC_DATA_DIR")
        if data_path_str:
            data_path = Path(data_path_str)
        else:
            data_path = Path.cwd() / "data"

    if not data_path.is_absolute():
        data_path = Path.cwd() / data_path

    if not data_path.exists():
        console.print(f"[red]✗[/red] Path not found: {data_path}", style="bold red")
        raise typer.Exit(code=1)

    # Get backend URL from argument or environment
    backend_url = backend_url or os.getenv("UNITYSVC_BACKEND_URL")
    if not backend_url:
        console.print(
            "[red]✗[/red] Backend URL not provided. Use --backend-url or set UNITYSVC_BACKEND_URL env var.",
            style="bold red",
        )
        raise typer.Exit(code=1)

    # Get API key from argument or environment
    api_key = api_key or os.getenv("UNITYSVC_API_KEY")
    if not api_key:
        console.print(
            "[red]✗[/red] API key not provided. Use --api-key or set UNITYSVC_API_KEY env var.",
            style="bold red",
        )
        raise typer.Exit(code=1)

    try:
        with ServiceDataPublisher(backend_url, api_key) as publisher:
            # Handle single file
            if data_path.is_file():
                console.print(f"[blue]Publishing service offering:[/blue] {data_path}")
                console.print(f"[blue]Backend URL:[/blue] {backend_url}\n")
                result = publisher.post_service_offering(data_path)
                console.print(
                    f"[green]✓[/green] Service offering published successfully!"
                )
                console.print(f"[cyan]Response:[/cyan] {json.dumps(result, indent=2)}")
            # Handle directory
            else:
                console.print(
                    f"[blue]Scanning for service offerings in:[/blue] {data_path}"
                )
                console.print(f"[blue]Backend URL:[/blue] {backend_url}\n")
                results = publisher.publish_all_offerings(data_path)

                console.print(f"\n[bold]Publishing Summary:[/bold]")
                console.print(f"  Total found: {results['total']}")
                console.print(f"  [green]✓ Success: {results['success']}[/green]")
                console.print(f"  [red]✗ Failed: {results['failed']}[/red]")

                if results["errors"]:
                    console.print("\n[bold red]Errors:[/bold red]")
                    for error in results["errors"]:
                        console.print(f"  [red]✗[/red] {error['file']}")
                        console.print(f"    {error['error']}")
                    raise typer.Exit(code=1)
                else:
                    console.print(
                        f"\n[green]✓[/green] All service offerings published successfully!"
                    )

    except typer.Exit:
        raise
    except Exception as e:
        console.print(
            f"[red]✗[/red] Failed to publish service offerings: {e}", style="bold red"
        )
        raise typer.Exit(code=1)


@app.command("listings")
def publish_listings(
    data_path: Optional[Path] = typer.Argument(
        None,
        help="Path to service listing file or directory (default: ./data or UNITYSVC_DATA_DIR env var)",
    ),
    backend_url: Optional[str] = typer.Option(
        None,
        "--backend-url",
        "-u",
        help="UnitySVC backend URL (default: from UNITYSVC_BACKEND_URL env var)",
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key for authentication (default: from UNITYSVC_API_KEY env var)",
    ),
):
    """Publish service listing(s) from a file or directory."""
    import os

    # Set data path
    if data_path is None:
        data_path_str = os.getenv("UNITYSVC_DATA_DIR")
        if data_path_str:
            data_path = Path(data_path_str)
        else:
            data_path = Path.cwd() / "data"

    if not data_path.is_absolute():
        data_path = Path.cwd() / data_path

    if not data_path.exists():
        console.print(f"[red]✗[/red] Path not found: {data_path}", style="bold red")
        raise typer.Exit(code=1)

    # Get backend URL from argument or environment
    backend_url = backend_url or os.getenv("UNITYSVC_BACKEND_URL")
    if not backend_url:
        console.print(
            "[red]✗[/red] Backend URL not provided. Use --backend-url or set UNITYSVC_BACKEND_URL env var.",
            style="bold red",
        )
        raise typer.Exit(code=1)

    # Get API key from argument or environment
    api_key = api_key or os.getenv("UNITYSVC_API_KEY")
    if not api_key:
        console.print(
            "[red]✗[/red] API key not provided. Use --api-key or set UNITYSVC_API_KEY env var.",
            style="bold red",
        )
        raise typer.Exit(code=1)

    try:
        with ServiceDataPublisher(backend_url, api_key) as publisher:
            # Handle single file
            if data_path.is_file():
                console.print(f"[blue]Publishing service listing:[/blue] {data_path}")
                console.print(f"[blue]Backend URL:[/blue] {backend_url}\n")
                result = publisher.post_service_listing(data_path)
                console.print(
                    f"[green]✓[/green] Service listing published successfully!"
                )
                console.print(f"[cyan]Response:[/cyan] {json.dumps(result, indent=2)}")
            # Handle directory
            else:
                console.print(
                    f"[blue]Scanning for service listings in:[/blue] {data_path}"
                )
                console.print(f"[blue]Backend URL:[/blue] {backend_url}\n")
                results = publisher.publish_all_listings(data_path)

                console.print(f"\n[bold]Publishing Summary:[/bold]")
                console.print(f"  Total found: {results['total']}")
                console.print(f"  [green]✓ Success: {results['success']}[/green]")
                console.print(f"  [red]✗ Failed: {results['failed']}[/red]")

                if results["errors"]:
                    console.print("\n[bold red]Errors:[/bold red]")
                    for error in results["errors"]:
                        console.print(f"  [red]✗[/red] {error['file']}")
                        console.print(f"    {error['error']}")
                    raise typer.Exit(code=1)
                else:
                    console.print(
                        f"\n[green]✓[/green] All service listings published successfully!"
                    )

    except typer.Exit:
        raise
    except Exception as e:
        console.print(
            f"[red]✗[/red] Failed to publish service listings: {e}", style="bold red"
        )
        raise typer.Exit(code=1)
