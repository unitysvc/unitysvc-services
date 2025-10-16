"""Data publisher module for posting service data to UnitySVC backend."""

import asyncio
import base64
import json
import os
import tomllib as toml
from pathlib import Path
from typing import Any

import httpx
import typer
from rich.console import Console

from .api import UnitySvcAPI
from .models.base import ProviderStatusEnum, SellerStatusEnum
from .utils import convert_convenience_fields_to_documents, find_files_by_schema
from .validator import DataValidator


class ServiceDataPublisher(UnitySvcAPI):
    """Publishes service data to UnitySVC backend endpoints.

    Inherits base HTTP client with curl fallback from UnitySvcAPI.
    Extends with async operations for concurrent publishing.
    """

    def __init__(self) -> None:
        # Initialize base class (provides self.client as AsyncClient with curl fallback)
        super().__init__()

        # Semaphore to limit concurrent requests and prevent connection pool exhaustion
        self.max_concurrent_requests = 15

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

    def resolve_file_references(self, data: dict[str, Any], base_path: Path) -> dict[str, Any]:
        """Recursively resolve file references and include content in data."""
        result: dict[str, Any] = {}

        for key, value in data.items():
            if isinstance(value, dict):
                # Recursively process nested dictionaries
                result[key] = self.resolve_file_references(value, base_path)
            elif isinstance(value, list):
                # Process lists
                result[key] = [
                    (self.resolve_file_references(item, base_path) if isinstance(item, dict) else item)
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
                        raise ValueError(f"Failed to load file content from '{value}': {e}")
            else:
                result[key] = value

        return result

    async def post(  # type: ignore[override]
        self, endpoint: str, data: dict[str, Any], check_status: bool = True
    ) -> tuple[dict[str, Any], int]:
        """Make a POST request to the backend API with automatic curl fallback.

        Override of base class post() that returns both JSON and status code.
        Uses base class client with automatic curl fallback.

        Args:
            endpoint: API endpoint path (e.g., "/publish/seller")
            data: JSON data to post
            check_status: Whether to raise on non-2xx status codes (default: True)

        Returns:
            Tuple of (JSON response, HTTP status code)

        Raises:
            RuntimeError: If both httpx and curl fail
        """
        # Use base class client (self.client from UnitySvcQuery) with automatic curl fallback
        # If we already know curl is needed, use it directly
        if self.use_curl_fallback:
            # Use base class curl fallback method
            response_json = await super().post(endpoint, json_data=data)
            # Curl POST doesn't return status code separately, assume 2xx if no exception
            status_code = 200
        else:
            try:
                response = await self.client.post(f"{self.base_url}{endpoint}", json=data)
                status_code = response.status_code

                if check_status:
                    response.raise_for_status()

                response_json = response.json()
            except (httpx.ConnectError, OSError):
                # Connection failed - switch to curl fallback and retry
                self.use_curl_fallback = True
                response_json = await super().post(endpoint, json_data=data)
                status_code = 200  # Assume success if curl didn't raise

        return (response_json, status_code)

    async def _post_with_retry(
        self,
        endpoint: str,
        data: dict[str, Any],
        entity_type: str,
        entity_name: str,
        context_info: str = "",
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """
        Generic retry wrapper for posting data to backend API with task polling.

        The backend now returns HTTP 202 with a task_id. This method:
        1. Submits the publish request
        2. Gets the task_id from the response
        3. Polls /tasks/{task_id} until completion
        4. Returns the final result

        Args:
            endpoint: API endpoint path (e.g., "/publish/listing")
            data: JSON data to post
            entity_type: Type of entity being published (for error messages)
            entity_name: Name of the entity being published (for error messages)
            context_info: Additional context for error messages (e.g., provider, service info)
            max_retries: Maximum number of retry attempts

        Returns:
            Response JSON from successful API call

        Raises:
            ValueError: On client errors (4xx) or after exhausting retries
        """
        last_exception = None
        for attempt in range(max_retries):
            try:
                # Use the public post() method with automatic curl fallback
                response_json, status_code = await self.post(endpoint, data, check_status=False)

                # Handle task-based response (HTTP 202)
                if status_code == 202:
                    # Backend returns task_id - poll for completion
                    task_id = response_json.get("task_id")

                    if not task_id:
                        context_msg = f" ({context_info})" if context_info else ""
                        raise ValueError(f"No task_id in response for {entity_type} '{entity_name}'{context_msg}")

                    # Poll task status until completion using check_task utility
                    try:
                        result = await self.check_task(task_id)
                        return result
                    except ValueError as e:
                        # Add context to task errors
                        context_msg = f" ({context_info})" if context_info else ""
                        raise ValueError(f"Task failed for {entity_type} '{entity_name}'{context_msg}: {e}")

                # Check for errors
                if status_code >= 400:
                    # Don't retry on 4xx errors (client errors) - they won't succeed on retry
                    if 400 <= status_code < 500:
                        error_detail = response_json.get("detail", str(response_json))
                        context_msg = f" ({context_info})" if context_info else ""
                        raise ValueError(
                            f"Failed to publish {entity_type} '{entity_name}'{context_msg}: {error_detail}"
                        )

                    # 5xx errors - retry with exponential backoff
                    if attempt < max_retries - 1:
                        wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        # Last attempt failed
                        error_detail = response_json.get("detail", str(response_json))
                        context_msg = f" ({context_info})" if context_info else ""
                        raise ValueError(
                            f"Failed to publish {entity_type} after {max_retries} attempts: "
                            f"'{entity_name}'{context_msg}: {error_detail}"
                        )

                # Success response (2xx)
                return response_json

            except (httpx.NetworkError, httpx.TimeoutException, RuntimeError) as e:
                # Network/connection errors - the post() method should have tried curl fallback
                # If we're here, both httpx and curl failed
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise ValueError(
                        f"Network error after {max_retries} attempts for {entity_type} '{entity_name}': {str(e)}"
                    )

        # Should never reach here, but just in case
        if last_exception:
            raise last_exception
        raise ValueError("Unexpected error in retry logic")

    async def post_service_listing_async(self, listing_file: Path, max_retries: int = 3) -> dict[str, Any]:
        """Async version of post_service_listing for concurrent publishing with retry logic."""
        # Load the listing data file
        data = self.load_data_file(listing_file)

        # If name is not provided, use filename (without extension)
        if "name" not in data or not data.get("name"):
            data["name"] = listing_file.stem

        # Resolve file references and include content
        base_path = listing_file.parent
        data_with_content = self.resolve_file_references(data, base_path)

        # Extract provider_name from directory structure
        parts = listing_file.parts
        try:
            services_idx = parts.index("services")
            provider_name = parts[services_idx - 1]
            data_with_content["provider_name"] = provider_name
        except (ValueError, IndexError):
            raise ValueError(
                f"Cannot extract provider_name from path: {listing_file}. "
                f"Expected path to contain .../{{provider_name}}/services/..."
            )

        # If service_name is not in listing data, find it from service files in the same directory
        if "service_name" not in data_with_content or not data_with_content["service_name"]:
            # Find all service files in the same directory
            service_files = find_files_by_schema(listing_file.parent, "service_v1")

            if len(service_files) == 0:
                raise ValueError(
                    f"Cannot find any service_v1 files in {listing_file.parent}. "
                    f"Listing files must be in the same directory as a service definition."
                )
            elif len(service_files) > 1:
                service_names = [data.get("name", "unknown") for _, _, data in service_files]
                raise ValueError(
                    f"Multiple services found in {listing_file.parent}: {', '.join(service_names)}. "
                    f"Please add 'service_name' field to {listing_file.name} to specify which "
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
                listing_file.parent, "service_v1", field_filter=(("name", service_name),)
            )

            if not service_files:
                raise ValueError(
                    f"Service '{service_name}' specified in {listing_file.name} not found in {listing_file.parent}."
                )

            # Get version from the found service
            _service_file, _format, service_data = service_files[0]
            data_with_content["service_version"] = service_data.get("version")

        # Find seller_name from seller definition in the data directory
        # Navigate up to find the data directory and look for seller file
        data_dir = listing_file.parent
        while data_dir.name != "data" and data_dir.parent != data_dir:
            data_dir = data_dir.parent

        if data_dir.name != "data":
            raise ValueError(
                f"Cannot find 'data' directory in path: {listing_file}. "
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

        # Post to the endpoint using retry helper
        context_info = (
            f"service: {data_with_content.get('service_name')}, "
            f"provider: {data_with_content.get('provider_name')}, "
            f"seller: {data_with_content.get('seller_name')}"
        )
        return await self._post_with_retry(
            endpoint="/publish/listing",
            data=data_with_content,
            entity_type="listing",
            entity_name=data.get("name", "unknown"),
            context_info=context_info,
            max_retries=max_retries,
        )

    async def post_service_offering_async(self, data_file: Path, max_retries: int = 3) -> dict[str, Any]:
        """Async version of post_service_offering for concurrent publishing with retry logic."""
        # Load the data file
        data = self.load_data_file(data_file)

        # Resolve file references and include content
        base_path = data_file.parent
        data = convert_convenience_fields_to_documents(
            data, base_path, logo_field="logo", terms_field="terms_of_service"
        )

        # Resolve file references and include content
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

        # Post to the endpoint using retry helper
        context_info = f"provider: {data_with_content.get('provider_name')}"
        return await self._post_with_retry(
            endpoint="/publish/offering",
            data=data_with_content,
            entity_type="offering",
            entity_name=data.get("name", "unknown"),
            context_info=context_info,
            max_retries=max_retries,
        )

    async def post_provider_async(self, data_file: Path, max_retries: int = 3) -> dict[str, Any]:
        """Async version of post_provider for concurrent publishing with retry logic."""
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

        # Post to the endpoint using retry helper
        return await self._post_with_retry(
            endpoint="/publish/provider",
            data=data_with_content,
            entity_type="provider",
            entity_name=data.get("name", "unknown"),
            max_retries=max_retries,
        )

    async def post_seller_async(self, data_file: Path, max_retries: int = 3) -> dict[str, Any]:
        """Async version of post_seller for concurrent publishing with retry logic."""
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
        data = convert_convenience_fields_to_documents(data, base_path, logo_field="logo", terms_field=None)

        # Resolve file references and include content
        data_with_content = self.resolve_file_references(data, base_path)

        # Post to the endpoint using retry helper
        return await self._post_with_retry(
            endpoint="/publish/seller",
            data=data_with_content,
            entity_type="seller",
            entity_name=data.get("name", "unknown"),
            max_retries=max_retries,
        )

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

    async def _publish_offering_task(
        self, offering_file: Path, console: Console, semaphore: asyncio.Semaphore
    ) -> tuple[Path, dict[str, Any] | Exception]:
        """
        Async task to publish a single offering with concurrency control.

        Returns tuple of (offering_file, result_or_exception).
        """
        async with semaphore:  # Limit concurrent requests
            try:
                # Load offering data to get the name
                data = self.load_data_file(offering_file)
                offering_name = data.get("name", offering_file.stem)

                # Publish the offering
                result = await self.post_service_offering_async(offering_file)

                # Print complete statement after publication
                if result.get("skipped"):
                    reason = result.get("reason", "unknown")
                    console.print(f"  [yellow]⊘[/yellow] Skipped offering: [cyan]{offering_name}[/cyan] - {reason}")
                else:
                    provider_name = result.get("provider_name")
                    console.print(
                        f"  [green]✓[/green] Published offering: [cyan]{offering_name}[/cyan] "
                        f"(provider: {provider_name})"
                    )

                return (offering_file, result)
            except Exception as e:
                data = self.load_data_file(offering_file)
                offering_name = data.get("name", offering_file.stem)
                console.print(f"  [red]✗[/red] Failed to publish offering: [cyan]{offering_name}[/cyan] - {str(e)}")
                return (offering_file, e)

    async def publish_all_offerings(self, data_dir: Path) -> dict[str, Any]:
        """
        Publish all service offerings found in a directory tree concurrently.

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
                "errors": [{"file": "validation", "error": error} for error in validation_errors],
            }

        offering_files = self.find_offering_files(data_dir)
        results: dict[str, Any] = {
            "total": len(offering_files),
            "success": 0,
            "failed": 0,
            "errors": [],
        }

        if not offering_files:
            return results

        console = Console()

        # Run all offering publications concurrently with rate limiting
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        tasks = [self._publish_offering_task(offering_file, console, semaphore) for offering_file in offering_files]
        task_results = await asyncio.gather(*tasks)

        # Process results
        for offering_file, result in task_results:
            if isinstance(result, Exception):
                results["failed"] += 1
                results["errors"].append({"file": str(offering_file), "error": str(result)})
            else:
                results["success"] += 1

        return results

    async def _publish_listing_task(
        self, listing_file: Path, console: Console, semaphore: asyncio.Semaphore
    ) -> tuple[Path, dict[str, Any] | Exception]:
        """
        Async task to publish a single listing with concurrency control.

        Returns tuple of (listing_file, result_or_exception).
        """
        async with semaphore:  # Limit concurrent requests
            try:
                # Load listing data to get the name
                data = self.load_data_file(listing_file)
                listing_name = data.get("name", listing_file.stem)

                # Publish the listing
                result = await self.post_service_listing_async(listing_file)

                # Print complete statement after publication
                if result.get("skipped"):
                    reason = result.get("reason", "unknown")
                    console.print(f"  [yellow]⊘[/yellow] Skipped listing: [cyan]{listing_name}[/cyan] - {reason}")
                else:
                    service_name = result.get("service_name")
                    provider_name = result.get("provider_name")
                    console.print(
                        f"  [green]✓[/green] Published listing: [cyan]{listing_name}[/cyan] "
                        f"(service: {service_name}, provider: {provider_name})"
                    )

                return (listing_file, result)
            except Exception as e:
                data = self.load_data_file(listing_file)
                listing_name = data.get("name", listing_file.stem)
                console.print(f"  [red]✗[/red] Failed to publish listing: [cyan]{listing_file}[/cyan] - {str(e)}")
                return (listing_file, e)

    async def publish_all_listings(self, data_dir: Path) -> dict[str, Any]:
        """
        Publish all service listings found in a directory tree concurrently.

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
                "errors": [{"file": "validation", "error": error} for error in validation_errors],
            }

        listing_files = self.find_listing_files(data_dir)
        results: dict[str, Any] = {
            "total": len(listing_files),
            "success": 0,
            "failed": 0,
            "errors": [],
        }

        if not listing_files:
            return results

        console = Console()

        # Run all listing publications concurrently with rate limiting
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        tasks = [self._publish_listing_task(listing_file, console, semaphore) for listing_file in listing_files]
        task_results = await asyncio.gather(*tasks)

        # Process results
        for listing_file, result in task_results:
            if isinstance(result, Exception):
                results["failed"] += 1
                results["errors"].append({"file": str(listing_file), "error": str(result)})
            else:
                results["success"] += 1

        return results

    async def _publish_provider_task(
        self, provider_file: Path, console: Console, semaphore: asyncio.Semaphore
    ) -> tuple[Path, dict[str, Any] | Exception]:
        """
        Async task to publish a single provider with concurrency control.

        Returns tuple of (provider_file, result_or_exception).
        """
        async with semaphore:  # Limit concurrent requests
            try:
                # Load provider data to get the name
                data = self.load_data_file(provider_file)
                provider_name = data.get("name", provider_file.stem)

                # Publish the provider
                result = await self.post_provider_async(provider_file)

                # Print complete statement after publication
                if result.get("skipped"):
                    reason = result.get("reason", "unknown")
                    console.print(f"  [yellow]⊘[/yellow] Skipped provider: [cyan]{provider_name}[/cyan] - {reason}")
                else:
                    console.print(f"  [green]✓[/green] Published provider: [cyan]{provider_name}[/cyan]")

                return (provider_file, result)
            except Exception as e:
                data = self.load_data_file(provider_file)
                provider_name = data.get("name", provider_file.stem)
                console.print(f"  [red]✗[/red] Failed to publish provider: [cyan]{provider_name}[/cyan] - {str(e)}")
                return (provider_file, e)

    async def publish_all_providers(self, data_dir: Path) -> dict[str, Any]:
        """
        Publish all providers found in a directory tree concurrently.

        Returns a summary of successes and failures.
        """
        provider_files = self.find_provider_files(data_dir)
        results: dict[str, Any] = {
            "total": len(provider_files),
            "success": 0,
            "failed": 0,
            "errors": [],
        }

        if not provider_files:
            return results

        console = Console()

        # Run all provider publications concurrently with rate limiting
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        tasks = [self._publish_provider_task(provider_file, console, semaphore) for provider_file in provider_files]
        task_results = await asyncio.gather(*tasks)

        # Process results
        for provider_file, result in task_results:
            if isinstance(result, Exception):
                results["failed"] += 1
                results["errors"].append({"file": str(provider_file), "error": str(result)})
            else:
                results["success"] += 1

        return results

    async def _publish_seller_task(
        self, seller_file: Path, console: Console, semaphore: asyncio.Semaphore
    ) -> tuple[Path, dict[str, Any] | Exception]:
        """
        Async task to publish a single seller with concurrency control.

        Returns tuple of (seller_file, result_or_exception).
        """
        async with semaphore:  # Limit concurrent requests
            try:
                # Load seller data to get the name
                data = self.load_data_file(seller_file)
                seller_name = data.get("name", seller_file.stem)

                # Publish the seller
                result = await self.post_seller_async(seller_file)

                # Print complete statement after publication
                if result.get("skipped"):
                    reason = result.get("reason", "unknown")
                    console.print(f"  [yellow]⊘[/yellow] Skipped seller: [cyan]{seller_name}[/cyan] - {reason}")
                else:
                    console.print(f"  [green]✓[/green] Published seller: [cyan]{seller_name}[/cyan]")

                return (seller_file, result)
            except Exception as e:
                data = self.load_data_file(seller_file)
                seller_name = data.get("name", seller_file.stem)
                console.print(f"  [red]✗[/red] Failed to publish seller: [cyan]{seller_name}[/cyan] - {str(e)}")
                return (seller_file, e)

    async def publish_all_sellers(self, data_dir: Path) -> dict[str, Any]:
        """
        Publish all sellers found in a directory tree concurrently.

        Returns a summary of successes and failures.
        """
        seller_files = self.find_seller_files(data_dir)
        results: dict[str, Any] = {
            "total": len(seller_files),
            "success": 0,
            "failed": 0,
            "errors": [],
        }

        if not seller_files:
            return results

        console = Console()

        # Run all seller publications concurrently with rate limiting
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        tasks = [self._publish_seller_task(seller_file, console, semaphore) for seller_file in seller_files]
        task_results = await asyncio.gather(*tasks)

        # Process results
        for seller_file, result in task_results:
            if isinstance(result, Exception):
                results["failed"] += 1
                results["errors"].append({"file": str(seller_file), "error": str(result)})
            else:
                results["success"] += 1

        return results

    async def publish_all_models(self, data_dir: Path) -> dict[str, Any]:
        """
        Publish all data types in the correct order.

        Publishing order:
        1. Sellers - Must exist before listings
        2. Providers - Must exist before offerings
        3. Service Offerings - Must exist before listings
        4. Service Listings - Depends on sellers, providers, and offerings

        Returns a dict with results for each data type and overall summary.
        """
        all_results: dict[str, Any] = {
            "sellers": {},
            "providers": {},
            "offerings": {},
            "listings": {},
            "total_success": 0,
            "total_failed": 0,
            "total_found": 0,
        }

        # Publish in order: sellers -> providers -> offerings -> listings
        publish_order = [
            ("sellers", self.publish_all_sellers),
            ("providers", self.publish_all_providers),
            ("offerings", self.publish_all_offerings),
            ("listings", self.publish_all_listings),
        ]

        for data_type, publish_method in publish_order:
            try:
                results = await publish_method(data_dir)
                all_results[data_type] = results
                all_results["total_success"] += results["success"]
                all_results["total_failed"] += results["failed"]
                all_results["total_found"] += results["total"]
            except Exception as e:
                # If a publish method fails catastrophically, record the error
                all_results[data_type] = {
                    "total": 0,
                    "success": 0,
                    "failed": 1,
                    "errors": [{"file": "N/A", "error": str(e)}],
                }
                all_results["total_failed"] += 1

        return all_results


# CLI commands for publishing
app = typer.Typer(help="Publish data to backend")
console = Console()


@app.callback(invoke_without_command=True)
def publish_callback(
    ctx: typer.Context,
    data_path: Path | None = typer.Option(
        None,
        "--data-path",
        "-d",
        help="Path to data directory (default: current directory)",
    ),
):
    """
    Publish data to backend.

    When called without a subcommand, publishes all data types in order:
    sellers → providers → offerings → listings.

    Use subcommands to publish specific data types:
    - providers: Publish only providers
    - sellers: Publish only sellers
    - offerings: Publish only service offerings
    - listings: Publish only service listings

    Required environment variables:
    - UNITYSVC_BASE_URL: Backend API URL
    - UNITYSVC_API_KEY: API key for authentication
    """
    # If a subcommand was invoked, skip this callback logic
    if ctx.invoked_subcommand is not None:
        return

    # No subcommand - publish all
    # Set data path
    if data_path is None:
        data_path = Path.cwd()

    if not data_path.is_absolute():
        data_path = Path.cwd() / data_path

    if not data_path.exists():
        console.print(f"[red]✗[/red] Path not found: {data_path}", style="bold red")
        raise typer.Exit(code=1)

    console.print(f"[bold blue]Publishing all data from:[/bold blue] {data_path}")
    console.print(f"[bold blue]Backend URL:[/bold blue] {os.getenv('UNITYSVC_BASE_URL', 'N/A')}\n")

    async def _publish_all_async():
        async with ServiceDataPublisher() as publisher:
            return await publisher.publish_all_models(data_path)

    try:
        all_results = asyncio.run(_publish_all_async())

        # Display results for each data type
        data_type_display_names = {
            "sellers": "Sellers",
            "providers": "Providers",
            "offerings": "Service Offerings",
            "listings": "Service Listings",
        }

        for data_type in ["sellers", "providers", "offerings", "listings"]:
            display_name = data_type_display_names[data_type]
            results = all_results[data_type]

            console.print(f"\n[bold cyan]{'=' * 60}[/bold cyan]")
            console.print(f"[bold cyan]{display_name}[/bold cyan]")
            console.print(f"[bold cyan]{'=' * 60}[/bold cyan]\n")

            console.print(f"  Total found: {results['total']}")
            console.print(f"  [green]✓ Success:[/green] {results['success']}")
            console.print(f"  [red]✗ Failed:[/red] {results['failed']}")

            # Display errors if any
            if results.get("errors"):
                console.print(f"\n[bold red]Errors in {display_name}:[/bold red]")
                for error in results["errors"]:
                    # Check if this is a skipped item
                    if isinstance(error, dict) and error.get("error", "").startswith("skipped"):
                        continue
                    console.print(f"  [red]✗[/red] {error.get('file', 'unknown')}")
                    console.print(f"    {error.get('error', 'unknown error')}")

        # Final summary
        console.print(f"\n[bold cyan]{'=' * 60}[/bold cyan]")
        console.print("[bold]Final Publishing Summary[/bold]")
        console.print(f"[bold cyan]{'=' * 60}[/bold cyan]\n")
        console.print(f"  Total found: {all_results['total_found']}")
        console.print(f"  [green]✓ Success:[/green] {all_results['total_success']}")
        console.print(f"  [red]✗ Failed:[/red] {all_results['total_failed']}")

        if all_results["total_failed"] > 0:
            console.print(
                f"\n[yellow]⚠[/yellow]  Completed with {all_results['total_failed']} failure(s)",
                style="bold yellow",
            )
            raise typer.Exit(code=1)
        else:
            console.print(
                "\n[green]✓[/green] All data published successfully!",
                style="bold green",
            )

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to publish all data: {e}", style="bold red")
        raise typer.Exit(code=1)


@app.command("providers")
def publish_providers(
    data_path: Path | None = typer.Option(
        None,
        "--data-path",
        "-d",
        help="Path to provider file or directory (default: current directory)",
    ),
):
    """Publish provider(s) from a file or directory."""

    # Set data path
    if data_path is None:
        data_path = Path.cwd()

    if not data_path.is_absolute():
        data_path = Path.cwd() / data_path

    if not data_path.exists():
        console.print(f"[red]✗[/red] Path not found: {data_path}", style="bold red")
        raise typer.Exit(code=1)

    # Handle single file
    if data_path.is_file():
        console.print(f"[blue]Publishing provider:[/blue] {data_path}")
        console.print(f"[blue]Backend URL:[/blue] {os.getenv('UNITYSVC_BASE_URL', 'N/A')}\n")
    else:
        console.print(f"[blue]Scanning for providers in:[/blue] {data_path}")
        console.print(f"[blue]Backend URL:[/blue] {os.getenv('UNITYSVC_BASE_URL', 'N/A')}\n")

    async def _publish_providers_async():
        async with ServiceDataPublisher() as publisher:
            # Handle single file
            if data_path.is_file():
                return await publisher.post_provider_async(data_path), True
            # Handle directory
            else:
                return await publisher.publish_all_providers(data_path), False

    try:
        result, is_single = asyncio.run(_publish_providers_async())

        if is_single:
            console.print("[green]✓[/green] Provider published successfully!")
            console.print(f"[cyan]Response:[/cyan] {json.dumps(result, indent=2)}")
        else:
            # Display summary
            console.print("\n[bold]Publishing Summary:[/bold]")
            console.print(f"  Total found: {result['total']}")
            console.print(f"  [green]✓ Success:[/green] {result['success']}")
            console.print(f"  [red]✗ Failed:[/red] {result['failed']}")

            # Display errors if any
            if result["errors"]:
                console.print("\n[bold red]Errors:[/bold red]")
                for error in result["errors"]:
                    console.print(f"  [red]✗[/red] {error['file']}")
                    console.print(f"    {error['error']}")

            if result["failed"] > 0:
                raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to publish providers: {e}", style="bold red")
        raise typer.Exit(code=1)


@app.command("sellers")
def publish_sellers(
    data_path: Path | None = typer.Option(
        None,
        "--data-path",
        "-d",
        help="Path to seller file or directory (default: current directory)",
    ),
):
    """Publish seller(s) from a file or directory."""
    # Set data path
    if data_path is None:
        data_path = Path.cwd()

    if not data_path.is_absolute():
        data_path = Path.cwd() / data_path

    if not data_path.exists():
        console.print(f"[red]✗[/red] Path not found: {data_path}", style="bold red")
        raise typer.Exit(code=1)

    # Handle single file
    if data_path.is_file():
        console.print(f"[blue]Publishing seller:[/blue] {data_path}")
        console.print(f"[blue]Backend URL:[/blue] {os.getenv('UNITYSVC_BASE_URL', 'N/A')}\n")
    else:
        console.print(f"[blue]Scanning for sellers in:[/blue] {data_path}")
        console.print(f"[blue]Backend URL:[/blue] {os.getenv('UNITYSVC_BASE_URL', 'N/A')}\n")

    async def _publish_sellers_async():
        async with ServiceDataPublisher() as publisher:
            # Handle single file
            if data_path.is_file():
                return await publisher.post_seller_async(data_path), True
            # Handle directory
            else:
                return await publisher.publish_all_sellers(data_path), False

    try:
        result, is_single = asyncio.run(_publish_sellers_async())

        if is_single:
            console.print("[green]✓[/green] Seller published successfully!")
            console.print(f"[cyan]Response:[/cyan] {json.dumps(result, indent=2)}")
        else:
            console.print("\n[bold]Publishing Summary:[/bold]")
            console.print(f"  Total found: {result['total']}")
            console.print(f"  [green]✓ Success: {result['success']}[/green]")
            console.print(f"  [red]✗ Failed: {result['failed']}[/red]")

            if result["errors"]:
                console.print("\n[bold red]Errors:[/bold red]")
                for error in result["errors"]:
                    console.print(f"  [red]✗[/red] {error['file']}")
                    console.print(f"    {error['error']}")
                raise typer.Exit(code=1)
            else:
                console.print("\n[green]✓[/green] All sellers published successfully!")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to publish sellers: {e}", style="bold red")
        raise typer.Exit(code=1)


@app.command("offerings")
def publish_offerings(
    data_path: Path | None = typer.Option(
        None,
        "--data-path",
        "-d",
        help="Path to service offering file or directory (default: current directory)",
    ),
):
    """Publish service offering(s) from a file or directory."""
    # Set data path
    if data_path is None:
        data_path = Path.cwd()

    if not data_path.is_absolute():
        data_path = Path.cwd() / data_path

    if not data_path.exists():
        console.print(f"[red]✗[/red] Path not found: {data_path}", style="bold red")
        raise typer.Exit(code=1)

    # Handle single file
    if data_path.is_file():
        console.print(f"[blue]Publishing service offering:[/blue] {data_path}")
        console.print(f"[blue]Backend URL:[/blue] {os.getenv('UNITYSVC_BASE_URL', 'N/A')}\n")
    else:
        console.print(f"[blue]Scanning for service offerings in:[/blue] {data_path}")
        console.print(f"[blue]Backend URL:[/bold blue] {os.getenv('UNITYSVC_BASE_URL', 'N/A')}\n")

    async def _publish_offerings_async():
        async with ServiceDataPublisher() as publisher:
            # Handle single file
            if data_path.is_file():
                return await publisher.post_service_offering_async(data_path), True
            # Handle directory
            else:
                return await publisher.publish_all_offerings(data_path), False

    try:
        result, is_single = asyncio.run(_publish_offerings_async())

        if is_single:
            console.print("[green]✓[/green] Service offering published successfully!")
            console.print(f"[cyan]Response:[/cyan] {json.dumps(result, indent=2)}")
        else:
            console.print("\n[bold]Publishing Summary:[/bold]")
            console.print(f"  Total found: {result['total']}")
            console.print(f"  [green]✓ Success: {result['success']}[/green]")
            console.print(f"  [red]✗ Failed: {result['failed']}[/red]")

            if result["errors"]:
                console.print("\n[bold red]Errors:[/bold red]")
                for error in result["errors"]:
                    console.print(f"  [red]✗[/red] {error['file']}")
                    console.print(f"    {error['error']}")
                raise typer.Exit(code=1)
            else:
                console.print("\n[green]✓[/green] All service offerings published successfully!")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to publish service offerings: {e}", style="bold red")
        raise typer.Exit(code=1)


@app.command("listings")
def publish_listings(
    data_path: Path | None = typer.Option(
        None,
        "--data-path",
        "-d",
        help="Path to service listing file or directory (default: current directory)",
    ),
):
    """Publish service listing(s) from a file or directory."""

    # Set data path
    if data_path is None:
        data_path = Path.cwd()

    if not data_path.is_absolute():
        data_path = Path.cwd() / data_path

    if not data_path.exists():
        console.print(f"[red]✗[/red] Path not found: {data_path}", style="bold red")
        raise typer.Exit(code=1)

    # Handle single file
    if data_path.is_file():
        console.print(f"[blue]Publishing service listing:[/blue] {data_path}")
        console.print(f"[blue]Backend URL:[/blue] {os.getenv('UNITYSVC_BASE_URL', 'N/A')}\n")
    else:
        console.print(f"[blue]Scanning for service listings in:[/blue] {data_path}")
        console.print(f"[blue]Backend URL:[/blue] {os.getenv('UNITYSVC_BASE_URL', 'N/A')}\n")

    async def _publish_listings_async():
        async with ServiceDataPublisher() as publisher:
            # Handle single file
            if data_path.is_file():
                return await publisher.post_service_listing_async(data_path), True
            # Handle directory
            else:
                return await publisher.publish_all_listings(data_path), False

    try:
        result, is_single = asyncio.run(_publish_listings_async())

        if is_single:
            console.print("[green]✓[/green] Service listing published successfully!")
            console.print(f"[cyan]Response:[/cyan] {json.dumps(result, indent=2)}")
        else:
            console.print("\n[bold]Publishing Summary:[/bold]")
            console.print(f"  Total found: {result['total']}")
            console.print(f"  [green]✓ Success: {result['success']}[/green]")
            console.print(f"  [red]✗ Failed: {result['failed']}[/red]")

            if result["errors"]:
                console.print("\n[bold red]Errors:[/bold red]")
                for error in result["errors"]:
                    console.print(f"  [red]✗[/red] {error['file']}")
                    console.print(f"    {error['error']}")
                raise typer.Exit(code=1)
            else:
                console.print("\n[green]✓[/green] All service listings published successfully!")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to publish service listings: {e}", style="bold red")
        raise typer.Exit(code=1)
