"""Data publisher module for posting service data to UnitySVC backend."""

import base64
import json
import os
import tomllib as toml
from pathlib import Path
from typing import Any

import httpx
import typer
from rich.console import Console

from .models.base import ProviderStatusEnum, SellerStatusEnum
from .utils import convert_convenience_fields_to_documents, find_files_by_schema
from .validator import DataValidator


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
            with open(full_path, encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # If it fails, read as binary and encode as base64
            with open(full_path, "rb") as f:
                return base64.b64encode(f.read()).decode("ascii")

    def resolve_file_references(
        self, data: dict[str, Any], base_path: Path
    ) -> dict[str, Any]:
        """Recursively resolve file references and include content in data."""
        result: dict[str, Any] = {}

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

            # Find provider directory to check status
            provider_dir = Path(*parts[:services_idx])
        except (ValueError, IndexError):
            raise ValueError(
                f"Cannot extract provider_name from path: {data_file}. "
                f"Expected path to contain .../{{provider_name}}/services/..."
            )

        # Check provider status - skip if incomplete
        provider_files = find_files_by_schema(provider_dir, "provider_v1")
        if provider_files:
            # Should only be one provider file in the directory
            _provider_file, _format, provider_data = provider_files[0]
            provider_status = provider_data.get("status", ProviderStatusEnum.active)
            if provider_status == ProviderStatusEnum.incomplete:
                return {
                    "skipped": True,
                    "reason": f"Provider status is '{provider_status}' - not publishing offering to backend",
                    "name": data.get("name", "unknown"),
                }

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
            service_files = find_files_by_schema(data_file.parent, "service_v1")

            if len(service_files) == 0:
                raise ValueError(
                    f"Cannot find any service_v1 files in {data_file.parent}. "
                    f"Listing files must be in the same directory as a service definition."
                )
            elif len(service_files) > 1:
                service_names = [
                    data.get("name", "unknown") for _, _, data in service_files
                ]
                raise ValueError(
                    f"Multiple services found in {data_file.parent}: {', '.join(service_names)}. "
                    f"Please add 'service_name' field to {data_file.name} to specify which "
                    f"service this listing belongs to."
                )
            else:
                # Exactly one service found - use it
                _service_file, _format, service_data = service_files[0]
                data_with_content["service_name"] = service_data.get("name")
                data_with_content["service_version"] = service_data.get("version")
        else:
            # service_name is provided in listing data, find the matching service to get version
            service_name = data_with_content["service_name"]
            service_files = find_files_by_schema(
                data_file.parent, "service_v1", field_filter=(("name", service_name),)
            )

            if not service_files:
                raise ValueError(
                    f"Service '{service_name}' specified in {data_file.name} not found in {data_file.parent}."
                )

            # Get version from the found service
            _service_file, _format, service_data = service_files[0]
            data_with_content["service_version"] = service_data.get("version")

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

        # Look for seller file in the data directory by checking schema field
        seller_files = find_files_by_schema(data_dir, "seller_v1")

        if not seller_files:
            raise ValueError(
                f"Cannot find seller_v1 file in {data_dir}. A seller definition is required in the data directory."
            )

        # Should only be one seller file in the data directory
        _seller_file, _format, seller_data = seller_files[0]

        # Check seller status - skip if incomplete
        seller_status = seller_data.get("status", SellerStatusEnum.active)
        if seller_status == SellerStatusEnum.incomplete:
            return {
                "skipped": True,
                "reason": f"Seller status is '{seller_status}' - not publishing listing to backend",
                "name": data.get("name", "unknown"),
            }

        seller_name = seller_data.get("name")
        if not seller_name:
            raise ValueError("Seller data missing 'name' field")

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

        # Check provider status - skip if incomplete
        provider_status = data.get("status", ProviderStatusEnum.active)
        if provider_status == ProviderStatusEnum.incomplete:
            # Return success without publishing - provider is incomplete
            return {
                "skipped": True,
                "reason": f"Provider status is '{provider_status}' - not publishing to backend",
                "name": data.get("name", "unknown"),
            }

        # Convert convenience fields (logo, terms_of_service) to documents
        base_path = data_file.parent
        data = convert_convenience_fields_to_documents(
            data, base_path, logo_field="logo", terms_field="terms_of_service"
        )

        # Resolve file references and include content
        data_with_content = self.resolve_file_references(data, base_path)

        # Remove status field before sending to backend (backend uses is_active)
        status = data_with_content.pop("status", ProviderStatusEnum.active)
        # Map status to is_active: active and disabled -> True (published), incomplete -> False (not published)
        data_with_content["is_active"] = status != ProviderStatusEnum.disabled

        # Post to the endpoint
        response = self.client.post(
            f"{self.base_url}/publish/provider",
            json=data_with_content,
        )
        response.raise_for_status()
        return response.json()

    def post_seller(self, data_file: Path) -> dict[str, Any]:
        """Post seller data to the backend."""

        # Load the data file
        data = self.load_data_file(data_file)

        # Check seller status - skip if incomplete
        seller_status = data.get("status", SellerStatusEnum.active)
        if seller_status == SellerStatusEnum.incomplete:
            # Return success without publishing - seller is incomplete
            return {
                "skipped": True,
                "reason": f"Seller status is '{seller_status}' - not publishing to backend",
                "name": data.get("name", "unknown"),
            }

        # Convert convenience fields (logo only for sellers, no terms_of_service)
        base_path = data_file.parent
        data = convert_convenience_fields_to_documents(
            data, base_path, logo_field="logo", terms_field=None
        )

        # Resolve file references and include content
        data_with_content = self.resolve_file_references(data, base_path)

        # Remove status field before sending to backend (backend uses is_active)
        status = data_with_content.pop("status", SellerStatusEnum.active)
        # Map status to is_active: active and disabled -> True (published), incomplete -> False (not published)
        data_with_content["is_active"] = status != SellerStatusEnum.disabled

        # Post to the endpoint
        response = self.client.post(
            f"{self.base_url}/publish/seller",
            json=data_with_content,
        )
        response.raise_for_status()
        return response.json()

    def find_offering_files(self, data_dir: Path) -> list[Path]:
        """Find all service offering files in a directory tree."""
        files = find_files_by_schema(data_dir, "service_v1")
        return sorted([f[0] for f in files])

    def find_listing_files(self, data_dir: Path) -> list[Path]:
        """Find all service listing files in a directory tree."""
        files = find_files_by_schema(data_dir, "listing_v1")
        return sorted([f[0] for f in files])

    def find_provider_files(self, data_dir: Path) -> list[Path]:
        """Find all provider files in a directory tree."""
        files = find_files_by_schema(data_dir, "provider_v1")
        return sorted([f[0] for f in files])

    def find_seller_files(self, data_dir: Path) -> list[Path]:
        """Find all seller files in a directory tree."""
        files = find_files_by_schema(data_dir, "seller_v1")
        return sorted([f[0] for f in files])

    def publish_all_offerings(self, data_dir: Path) -> dict[str, Any]:
        """
        Publish all service offerings found in a directory tree.

        Validates data consistency before publishing.
        Returns a summary of successes and failures.
        """

        # Validate all service directories first
        validator = DataValidator(data_dir, data_dir.parent / "schema")
        validation_errors = validator.validate_all_service_directories(data_dir)
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
        results: dict[str, Any] = {
            "total": len(offering_files),
            "success": 0,
            "failed": 0,
            "errors": [],
        }

        for offering_file in offering_files:
            try:
                self.post_service_offering(offering_file)
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
        validator = DataValidator(data_dir, data_dir.parent / "schema")
        validation_errors = validator.validate_all_service_directories(data_dir)
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
        results: dict[str, Any] = {
            "total": len(listing_files),
            "success": 0,
            "failed": 0,
            "errors": [],
        }

        for listing_file in listing_files:
            try:
                self.post_service_listing(listing_file)
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
        results: dict[str, Any] = {
            "total": len(provider_files),
            "success": 0,
            "failed": 0,
            "errors": [],
        }

        for provider_file in provider_files:
            try:
                self.post_provider(provider_file)
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
        results: dict[str, Any] = {
            "total": len(seller_files),
            "success": 0,
            "failed": 0,
            "errors": [],
        }

        for seller_file in seller_files:
            try:
                self.post_seller(seller_file)
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
app = typer.Typer(help="Publish data to backend")
console = Console()


@app.command("providers")
def publish_providers(
    data_path: Path | None = typer.Argument(
        None,
        help="Path to provider file or directory (default: ./data or UNITYSVC_DATA_DIR env var)",
    ),
    backend_url: str | None = typer.Option(
        None,
        "--backend-url",
        "-u",
        help="UnitySVC backend URL (default: from UNITYSVC_BACKEND_URL env var)",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key for authentication (default: from UNITYSVC_API_KEY env var)",
    ),
):
    """Publish provider(s) from a file or directory."""

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
                console.print("[green]✓[/green] Provider published successfully!")
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
    data_path: Path | None = typer.Argument(
        None,
        help="Path to seller file or directory (default: ./data or UNITYSVC_DATA_DIR env var)",
    ),
    backend_url: str | None = typer.Option(
        None,
        "--backend-url",
        "-u",
        help="UnitySVC backend URL (default: from UNITYSVC_BACKEND_URL env var)",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key for authentication (default: from UNITYSVC_API_KEY env var)",
    ),
):
    """Publish seller(s) from a file or directory."""
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
                console.print("[green]✓[/green] Seller published successfully!")
                console.print(f"[cyan]Response:[/cyan] {json.dumps(result, indent=2)}")
            # Handle directory
            else:
                console.print(f"[blue]Scanning for sellers in:[/blue] {data_path}")
                console.print(f"[blue]Backend URL:[/blue] {backend_url}\n")
                results = publisher.publish_all_sellers(data_path)

                console.print("\n[bold]Publishing Summary:[/bold]")
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
                        "\n[green]✓[/green] All sellers published successfully!"
                    )

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to publish sellers: {e}", style="bold red")
        raise typer.Exit(code=1)


@app.command("offerings")
def publish_offerings(
    data_path: Path | None = typer.Argument(
        None,
        help="Path to service offering file or directory (default: ./data or UNITYSVC_DATA_DIR env var)",
    ),
    backend_url: str | None = typer.Option(
        None,
        "--backend-url",
        "-u",
        help="UnitySVC backend URL (default: from UNITYSVC_BACKEND_URL env var)",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key for authentication (default: from UNITYSVC_API_KEY env var)",
    ),
):
    """Publish service offering(s) from a file or directory."""
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
                    "[green]✓[/green] Service offering published successfully!"
                )
                console.print(f"[cyan]Response:[/cyan] {json.dumps(result, indent=2)}")
            # Handle directory
            else:
                console.print(
                    f"[blue]Scanning for service offerings in:[/blue] {data_path}"
                )
                console.print(f"[blue]Backend URL:[/blue] {backend_url}\n")
                results = publisher.publish_all_offerings(data_path)

                console.print("\n[bold]Publishing Summary:[/bold]")
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
                        "\n[green]✓[/green] All service offerings published successfully!"
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
    data_path: Path | None = typer.Argument(
        None,
        help="Path to service listing file or directory (default: ./data or UNITYSVC_DATA_DIR env var)",
    ),
    backend_url: str | None = typer.Option(
        None,
        "--backend-url",
        "-u",
        help="UnitySVC backend URL (default: from UNITYSVC_BACKEND_URL env var)",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key for authentication (default: from UNITYSVC_API_KEY env var)",
    ),
):
    """Publish service listing(s) from a file or directory."""

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
                    "[green]✓[/green] Service listing published successfully!"
                )
                console.print(f"[cyan]Response:[/cyan] {json.dumps(result, indent=2)}")
            # Handle directory
            else:
                console.print(
                    f"[blue]Scanning for service listings in:[/blue] {data_path}"
                )
                console.print(f"[blue]Backend URL:[/blue] {backend_url}\n")
                results = publisher.publish_all_listings(data_path)

                console.print("\n[bold]Publishing Summary:[/bold]")
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
                        "\n[green]✓[/green] All service listings published successfully!"
                    )

    except typer.Exit:
        raise
    except Exception as e:
        console.print(
            f"[red]✗[/red] Failed to publish service listings: {e}", style="bold red"
        )
        raise typer.Exit(code=1)
