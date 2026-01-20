"""Data publisher module for posting service data to UnitySVC backend."""

import asyncio
import base64
import json
import os
from pathlib import Path
from typing import Any

import httpx
import typer
from rich.console import Console
from rich.table import Table

import unitysvc_services

from .api import UnitySvcAPI
from .markdown import Attachment, process_markdown_content, upload_attachments
from .models.base import ListingStatusEnum, OfferingStatusEnum, ProviderStatusEnum
from .utils import (
    convert_convenience_fields_to_documents,
    find_files_by_schema,
    load_data_file,
    render_template_file,
    write_override_file,
)
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
        self,
        data: dict[str, Any],
        base_path: Path,
        listing: dict[str, Any] | None = None,
        offering: dict[str, Any] | None = None,
        provider: dict[str, Any] | None = None,
        seller: dict[str, Any] | None = None,
        listing_filename: str | None = None,
        interface: dict[str, Any] | None = None,
        collected_attachments: list[Attachment] | None = None,
    ) -> dict[str, Any]:
        """Recursively resolve file references and include content in data.

        For Jinja2 template files (.j2), renders the template with provided context
        and strips the .j2 extension from file_path.

        For markdown files, processes attachments (images, linked files) by:
        1. Computing content-based object keys locally (no network calls)
        2. Replacing local paths with $UNITYSVC_S3_BASE_URL/{object_key}
        3. Collecting attachments for later batch upload

        Args:
            data: Data dictionary potentially containing file_path references
            base_path: Base path for resolving relative file paths
            listing: Listing data for template rendering (optional)
            offering: Offering data for template rendering (optional)
            provider: Provider data for template rendering (optional)
            seller: Seller data for template rendering (optional)
            listing_filename: Listing filename for constructing output filenames (optional)
            interface: AccessInterface data for template rendering (optional, for interface documents)
            collected_attachments: List to collect attachments for later upload (optional)

        Returns:
            Data with file references resolved and content loaded
        """
        result: dict[str, Any] = {}

        # Check if this dict looks like an AccessInterface (has base_url or interface_type)
        # If so, use it as the interface context for nested documents
        current_interface = interface
        if "base_url" in data or "interface_type" in data:
            current_interface = data

        for key, value in data.items():
            if isinstance(value, dict):
                # Recursively process nested dictionaries
                result[key] = self.resolve_file_references(
                    value,
                    base_path,
                    listing=listing,
                    offering=offering,
                    provider=provider,
                    seller=seller,
                    listing_filename=listing_filename,
                    interface=current_interface,
                    collected_attachments=collected_attachments,
                )
            elif isinstance(value, list):
                # Process lists
                processed_items = []
                for item in value:
                    if isinstance(item, dict):
                        processed_items.append(
                            self.resolve_file_references(
                                item,
                                base_path,
                                listing=listing,
                                offering=offering,
                                provider=provider,
                                seller=seller,
                                listing_filename=listing_filename,
                                interface=current_interface,
                                collected_attachments=collected_attachments,
                            )
                        )
                    else:
                        processed_items.append(item)
                result[key] = processed_items
            elif key == "file_path" and isinstance(value, str):
                # This is a file reference - load the content and render if template
                full_path = base_path / value if not Path(value).is_absolute() else Path(value)

                if not full_path.exists():
                    raise FileNotFoundError(f"File not found: {full_path}")

                # Render template if applicable
                try:
                    content, actual_filename = render_template_file(
                        full_path,
                        listing=listing,
                        offering=offering,
                        provider=provider,
                        seller=seller,
                        interface=current_interface,
                    )

                    # Check if this is a markdown file - process attachments
                    is_markdown = actual_filename.endswith(".md") or data.get("mime_type") == "markdown"
                    if is_markdown:
                        # Process markdown to compute object keys and revise paths (no network calls)
                        md_result = process_markdown_content(
                            content,
                            full_path.parent,  # Base path for resolving relative paths in markdown
                            is_public=data.get("is_public", True),
                        )
                        content = md_result.content
                        # Collect attachments for later upload
                        if collected_attachments is not None:
                            collected_attachments.extend(md_result.attachments)

                    result["file_content"] = content

                    # Update file_path to remove .j2 extension if it was a template
                    if full_path.name.endswith(".j2"):
                        # Strip .j2 from the path
                        new_path = str(value)[:-3]  # Remove last 3 characters (.j2)
                        result[key] = new_path
                    else:
                        result[key] = value

                except Exception as e:
                    raise ValueError(f"Failed to load/render file content from '{value}': {e}")
            else:
                result[key] = value

        # After processing all fields, check if this is a code_examples document
        # If so, try to load corresponding .out file and add to meta.output
        if result.get("category") == "code_examples" and result.get("file_content") and listing_filename:
            # Get the actual filename (after .j2 stripping if applicable)
            # If file_path was updated (e.g., from "test.py.j2" to "test.py"), use that
            # Otherwise, extract basename from original file_path
            output_base_filename: str | None = None

            # Check if file_path was modified (original might have had .j2)
            file_path_value = result.get("file_path", "")
            if file_path_value:
                output_base_filename = Path(file_path_value).name

            if output_base_filename:
                # Construct output filename: {listing_stem}_{output_base_filename}.out
                # e.g., "svclisting_test.py.out" for svclisting.json and test.py
                listing_stem = Path(listing_filename).stem
                output_filename = f"{listing_stem}_{output_base_filename}.out"

                # Try to find the .out file in base_path (listing directory)
                output_path = base_path / output_filename

                if output_path.exists():
                    try:
                        with open(output_path, encoding="utf-8") as f:
                            output_content = f.read()

                        # Add output to meta field
                        if "meta" not in result or result["meta"] is None:
                            result["meta"] = {}
                        result["meta"]["output"] = output_content
                    except Exception:
                        # Don't fail if output file can't be read, just skip it
                        pass

        return result

    async def post(  # type: ignore[override]
        self, endpoint: str, data: dict[str, Any], check_status: bool = True, dryrun: bool = False
    ) -> tuple[dict[str, Any], int]:
        """Make a POST request to the backend API with automatic curl fallback.

        Override of base class post() that returns both JSON and status code.
        Uses base class client with automatic curl fallback.

        Args:
            endpoint: API endpoint path (e.g., "/publish/seller")
            data: JSON data to post
            check_status: Whether to raise on non-2xx status codes (default: True)
            dryrun: If True, adds dryrun=true as query parameter

        Returns:
            Tuple of (JSON response, HTTP status code)

        Raises:
            RuntimeError: If both httpx and curl fail
        """
        # Build query parameters
        params = {"dryrun": "true"} if dryrun else None

        # Use base class client (self.client from UnitySvcQuery) with automatic curl fallback
        # If we already know curl is needed, use it directly
        if self.use_curl_fallback:
            # Use base class curl fallback method
            response_json = await super().post(endpoint, json_data=data, params=params)
            # Curl POST doesn't return status code separately, assume 2xx if no exception
            status_code = 200
        else:
            try:
                response = await self.client.post(f"{self.base_url}{endpoint}", json=data, params=params)
                status_code = response.status_code

                if check_status:
                    response.raise_for_status()

                response_json = response.json()
            except (httpx.ConnectError, OSError):
                # Connection failed - switch to curl fallback and retry
                self.use_curl_fallback = True
                response_json = await super().post(endpoint, json_data=data, params=params)
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
        dryrun: bool = False,
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
            dryrun: If True, runs in dry run mode (no actual changes)

        Returns:
            Response JSON from successful API call

        Raises:
            ValueError: On client errors (4xx) or after exhausting retries
        """
        last_exception = None
        for attempt in range(max_retries):
            try:
                # Use the public post() method with automatic curl fallback
                response_json, status_code = await self.post(endpoint, data, check_status=False, dryrun=dryrun)

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

    async def post_service_async(
        self,
        listing_file: Path,
        max_retries: int = 3,
        dryrun: bool = False,
    ) -> dict[str, Any]:
        """
        Publish a complete service (provider, offering, and listing) together.

        This method takes a listing file and automatically finds the associated
        offering (same directory) and provider (parent directory) files, loads them,
        resolves file references, and posts to the unified /seller/services endpoint.

        Args:
            listing_file: Path to listing data file (listing_v1 schema)
            max_retries: Maximum number of retry attempts
            dryrun: If True, runs in dry run mode (no actual changes)

        Returns:
            Response JSON from successful API call containing results for all three entities
        """
        # Load the listing data file
        listing_data, _ = load_data_file(listing_file)

        # Extract provider directory from path structure
        # Expected: .../provider_name/services/service_name/listing.json
        parts = listing_file.parts
        try:
            services_idx = parts.index("services")
            # Find provider directory to load provider data
            provider_dir = Path(*parts[:services_idx])
        except (ValueError, IndexError):
            raise ValueError(
                f"Cannot extract provider directory from path: {listing_file}. "
                f"Expected path to contain .../provider_name/services/..."
            )

        # Find offering file in the same directory as the listing
        # Each service directory must have exactly one offering file
        offering_files = find_files_by_schema(listing_file.parent, "offering_v1")
        if len(offering_files) == 0:
            raise ValueError(
                f"Cannot find any offering_v1 files in {listing_file.parent}. "
                f"Listing files must be in the same directory as an offering definition."
            )
        elif len(offering_files) > 1:
            offering_names = [off_data.get("name", "unknown") for _, _, off_data in offering_files]
            raise ValueError(
                f"Multiple offerings found in {listing_file.parent}: {', '.join(offering_names)}. "
                f"Each service directory must have exactly one offering file."
            )

        offering_file, _format, offering_data = offering_files[0]

        # Derive offering name from directory structure if not specified
        # e.g., data/fireworks/services/qwen3-vl-235b-a22b-instruct/ -> qwen3-vl-235b-a22b-instruct
        if "name" not in offering_data or not offering_data.get("name"):
            offering_data["name"] = parts[services_idx + 1]

        # If listing name is not provided, use offering name
        # Service name = listing name or offering name
        if "name" not in listing_data or not listing_data.get("name"):
            listing_data["name"] = offering_data.get("name")

        # Find provider file in the parent directory
        provider_files = find_files_by_schema(provider_dir, "provider_v1")
        if not provider_files:
            raise ValueError(
                f"Cannot find any provider_v1 files in {provider_dir}. "
                f"Provider file must exist in the parent directory of services."
            )
        provider_file, _format, provider_data = provider_files[0]

        # Check provider status - skip if draft
        provider_status = provider_data.get("status", ProviderStatusEnum.draft)
        if provider_status == ProviderStatusEnum.draft:
            return {
                "skipped": True,
                "reason": f"Provider status is '{provider_status}' - not publishing to backend (still in draft)",
                "service_name": offering_data.get("name", "unknown"),
            }

        # Check offering status - skip if draft
        offering_status = offering_data.get("status", OfferingStatusEnum.draft)
        if offering_status == OfferingStatusEnum.draft:
            return {
                "skipped": True,
                "reason": f"Offering status is '{offering_status}' - not publishing to backend (still in draft)",
                "service_name": offering_data.get("name", "unknown"),
            }

        # Check listing status - skip if draft
        listing_status = listing_data.get("status", ListingStatusEnum.draft)
        if listing_status == ListingStatusEnum.draft:
            return {
                "skipped": True,
                "reason": f"Listing status is '{listing_status}' - not publishing to backend (still in draft)",
                "service_name": offering_data.get("name", "unknown"),
            }

        collected_attachments: list[Attachment] = []

        # Process provider data
        provider_base_path = provider_file.parent
        provider_data = convert_convenience_fields_to_documents(
            provider_data, provider_base_path, logo_field="logo", terms_field="terms_of_service"
        )
        provider_data_resolved = self.resolve_file_references(
            provider_data,
            provider_base_path,
            provider=provider_data,
            collected_attachments=collected_attachments,
        )

        # Process offering data
        offering_base_path = offering_file.parent
        offering_data = convert_convenience_fields_to_documents(
            offering_data, offering_base_path, logo_field="logo", terms_field="terms_of_service"
        )
        offering_data_resolved = self.resolve_file_references(
            offering_data,
            offering_base_path,
            offering=offering_data,
            provider=provider_data,
            collected_attachments=collected_attachments,
        )

        # Process listing data
        listing_base_path = listing_file.parent
        listing_data = convert_convenience_fields_to_documents(
            listing_data, listing_base_path, logo_field="logo", terms_field="terms_of_service"
        )
        # Note: interface is intentionally NOT passed here - code examples should be
        # interface-independent and use offering.details for service-specific values
        listing_data_resolved = self.resolve_file_references(
            listing_data,
            listing_base_path,
            listing=listing_data,
            offering=offering_data,
            provider=provider_data,
            listing_filename=listing_file.name,
            collected_attachments=collected_attachments,
        )

        # Upload collected attachments before publishing
        if collected_attachments:
            await upload_attachments(self, collected_attachments)

        # Combine all data into ServiceData format
        service_data = {
            "provider_data": provider_data_resolved,
            "offering_data": offering_data_resolved,
            "listing_data": listing_data_resolved,
        }

        # Get entity names for error messages
        provider_name_str = provider_data.get("name", "unknown")
        listing_name = listing_data.get("name", "unknown")

        # Post to the unified service endpoint
        result = await self._post_with_retry(
            endpoint="/seller/services",
            data=service_data,
            entity_type="service",
            entity_name=f"{provider_name_str}/{listing_name}",
            max_retries=max_retries,
            dryrun=dryrun,
        )

        # Add local metadata to result for display purposes
        result["listing_name"] = listing_name
        result["service_name"] = offering_data_resolved.get("name")
        result["provider_name"] = provider_name_str

        # Save service_id to override file for future updates (not in dryrun mode)
        if not dryrun:
            service_result = result.get("service", {})
            service_id = service_result.get("id")
            if service_id:
                override_data: dict[str, Any] = {"service_id": service_id}
                override_path = write_override_file(listing_file, override_data)
                result["override_file"] = str(override_path)

        return result

    def find_listing_files(self, data_dir: Path) -> list[Path]:
        """Find all service listing files in a directory tree."""
        files = find_files_by_schema(data_dir, "listing_v1")
        return sorted([f[0] for f in files])

    @staticmethod
    def _get_status_display(status: str) -> tuple[str, str]:
        """Get color and symbol for status display."""
        status_map = {
            "created": ("[green]+[/green]", "green"),
            "updated": ("[blue]~[/blue]", "blue"),
            "unchanged": ("[dim]=[/dim]", "dim"),
            "create": ("[yellow]?[/yellow]", "yellow"),  # Dryrun: would be created
            "update": ("[cyan]?[/cyan]", "cyan"),  # Dryrun: would be updated
        }
        return status_map.get(status, ("[green]✓[/green]", "green"))

    @staticmethod
    def _derive_effective_status(result: dict[str, Any]) -> str:
        """
        Derive effective status from nested provider/offering/listing/service results.

        The backend returns individual statuses for each entity. This method
        combines them into a single effective status:
        - If any entity was created (including Service record) -> "created"
        - If any entity was updated (none created) -> "updated"
        - If all entities are unchanged -> "unchanged"
        """
        statuses = []
        for key in ["provider", "offering", "listing", "service"]:
            nested = result.get(key, {})
            if isinstance(nested, dict):
                status = nested.get("status", "")
                # Map service-specific statuses to generic ones
                if status == "revision_created":
                    status = "created"
                statuses.append(status)

        # Dryrun statuses
        if "create" in statuses:
            return "create"
        if "update" in statuses:
            return "update"

        # Normal statuses
        if "created" in statuses:
            return "created"
        if "updated" in statuses:
            return "updated"
        if all(s == "unchanged" for s in statuses if s):
            return "unchanged"

        # Fallback
        return "created"

    async def _upload_service_task(
        self, listing_file: Path, console: Console, semaphore: asyncio.Semaphore, dryrun: bool = False
    ) -> tuple[Path, dict[str, Any] | Exception]:
        """
        Async task to upload a single service (provider + offering + listing) with concurrency control.

        Returns tuple of (listing_file, result_or_exception).
        """
        async with semaphore:  # Limit concurrent requests
            try:
                # Load listing data to get the name
                data, _ = load_data_file(listing_file)
                listing_name = data.get("name", listing_file.stem)

                # Upload the service (provider + offering + listing together)
                result = await self.post_service_async(listing_file, dryrun=dryrun)

                # Print complete statement after upload
                if result.get("skipped"):
                    reason = result.get("reason", "unknown")
                    # Use service_name (offering name) as primary identifier
                    skip_name = result.get("service_name") or listing_name
                    console.print(f"  [yellow]⊘[/yellow] Skipped service: [cyan]{skip_name}[/cyan] - {reason}")
                else:
                    service_name = result.get("service_name")
                    provider_name = result.get("provider_name")
                    # Derive effective status from nested results
                    # Backend returns provider/offering/listing each with their own status
                    status = self._derive_effective_status(result)
                    symbol, color = self._get_status_display(status)

                    # Get listing status and ops_status from the listing result
                    listing_result = result.get("listing", {})
                    listing_status = listing_result.get("listing_status", "unknown")
                    ops_status = listing_result.get("ops_status", "unknown")

                    console.print(
                        f"  {symbol} [{color}]{status.capitalize()}[/{color}] service: [cyan]{service_name}[/cyan] "
                        f"(provider: {provider_name}) "
                        f"[dim]status={listing_status}, ops_status={ops_status}[/dim]"
                    )
                    # Update result with derived status for summary tracking
                    result["status"] = status

                return (listing_file, result)
            except Exception as e:
                try:
                    data, _ = load_data_file(listing_file)
                    listing_name = data.get("name", listing_file.stem)
                except Exception:
                    listing_name = listing_file.stem
                console.print(f"  [red]✗[/red] Failed to upload service: [cyan]{listing_name}[/cyan] - {str(e)}")
                return (listing_file, e)

    async def upload_all_services(self, data_dir: Path, dryrun: bool = False) -> dict[str, Any]:
        """
        Upload all services found in a directory tree concurrently.

        Each listing file triggers a unified upload of provider + offering + listing
        to the /seller/services endpoint.

        Validates data consistency before uploading.
        Returns a summary of successes and failures.

        Args:
            data_dir: Directory to search for listing files
            dryrun: If True, runs in dry run mode (no actual changes)
        """
        # Validate all service directories first
        schema_dir = Path(unitysvc_services.__file__).parent / "schema"
        validator = DataValidator(data_dir, schema_dir)
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
            "skipped": 0,
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "errors": [],
        }

        if not listing_files:
            return results

        console = Console()

        # Run all service uploads concurrently with rate limiting
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        tasks = [
            self._upload_service_task(listing_file, console, semaphore, dryrun=dryrun)
            for listing_file in listing_files
        ]
        task_results = await asyncio.gather(*tasks)

        # Process results
        for listing_file, result in task_results:
            if isinstance(result, Exception):
                results["failed"] += 1
                results["errors"].append({"file": str(listing_file), "error": str(result)})
            elif result.get("skipped"):
                results["skipped"] += 1
                results["success"] += 1  # Skipped is still a success (intentional skip)
            else:
                results["success"] += 1
                # Track status counts (handle both normal and dryrun statuses)
                status = result.get("status", "created")
                if status in ("created", "create"):  # "create" is dryrun mode
                    results["created"] += 1
                elif status in ("updated", "update"):  # "update" is dryrun mode
                    results["updated"] += 1
                elif status == "unchanged":
                    results["unchanged"] += 1

        return results


# CLI commands for uploading
app = typer.Typer(help="Upload service data to backend")
console = Console()


@app.callback(invoke_without_command=True)
def upload_callback(
    data_path: Path | None = typer.Option(
        None,
        "--data-path",
        "-d",
        help="Path to data directory or listing file (default: current directory)",
    ),
    dryrun: bool = typer.Option(
        False,
        "--dryrun",
        help="Run in dry run mode (no actual changes)",
    ),
):
    """
    Upload service data to backend.

    Finds all listing files (listing_v1 schema) in the directory tree, then for each
    listing automatically discovers the associated offering (same directory) and
    provider (parent directory), and uploads all three together to /seller/services.

    When given a single listing file, uploads only that service.

    Services are uploaded in 'draft' status. Use 'usvc test' to run gateway tests,
    then 'usvc submit' to submit for admin review.

    If service_id already exists (from a previous upload), this updates the existing
    service rather than creating a new one.

    Required environment variables:
    - UNITYSVC_BASE_URL: Backend API URL
    - UNITYSVC_API_KEY: API key for authentication (seller API key)
    """
    # Set data path
    if data_path is None:
        data_path = Path.cwd()

    if not data_path.is_absolute():
        data_path = Path.cwd() / data_path

    if not data_path.exists():
        console.print(f"[red]✗[/red] Path not found: {data_path}", style="bold red")
        raise typer.Exit(code=1)

    # Handle single file vs directory
    is_single_file = data_path.is_file()

    if is_single_file:
        console.print(f"[bold blue]Uploading service from:[/bold blue] {data_path}")
    else:
        console.print(f"[bold blue]Uploading services from:[/bold blue] {data_path}")
    console.print(f"[bold blue]Backend URL:[/bold blue] {os.getenv('UNITYSVC_BASE_URL', 'N/A')}\n")

    async def _upload_async():
        async with ServiceDataPublisher() as uploader:
            if is_single_file:
                # Upload single service from listing file
                result = await uploader.post_service_async(data_path, dryrun=dryrun)
                return result, True
            else:
                # Upload all services from directory
                results = await uploader.upload_all_services(data_path, dryrun=dryrun)
                return results, False

    try:
        result, is_single = asyncio.run(_upload_async())

        if is_single:
            # Single file result
            if result.get("skipped"):
                console.print(f"[yellow]⊘[/yellow] Skipped: {result.get('reason', 'unknown')}")
            else:
                console.print("[green]✓[/green] Service uploaded successfully!")
                console.print(f"[cyan]Response:[/cyan] {json.dumps(result, indent=2)}")
        else:
            # Directory results - create summary table
            console.print("\n[bold cyan]Upload Summary[/bold cyan]")

            table = Table(show_header=True, header_style="bold cyan", border_style="cyan")
            table.add_column("Type", style="cyan", no_wrap=True)
            table.add_column("Found", justify="right")
            table.add_column("Success", justify="right", style="green")
            table.add_column("Skipped", justify="right", style="yellow")
            table.add_column("Failed", justify="right", style="red")
            table.add_column("Created", justify="right", style="green")
            table.add_column("Updated", justify="right", style="blue")
            table.add_column("Unchanged", justify="right", style="dim")

            table.add_row(
                "Services",
                str(result["total"]),
                str(result["success"]),
                str(result.get("skipped", 0)) if result.get("skipped", 0) > 0 else "",
                str(result["failed"]) if result["failed"] > 0 else "",
                str(result.get("created", 0)) if result.get("created", 0) > 0 else "",
                str(result.get("updated", 0)) if result.get("updated", 0) > 0 else "",
                str(result.get("unchanged", 0)) if result.get("unchanged", 0) > 0 else "",
            )

            console.print(table)

            # Display errors if any
            if result.get("errors"):
                console.print("\n[bold red]Errors:[/bold red]")
                for error in result["errors"]:
                    console.print(f"  [red]✗[/red] {error.get('file', 'unknown')}")
                    console.print(f"    {error.get('error', 'unknown error')}")

            if result["failed"] > 0:
                console.print(
                    f"\n[yellow]⚠[/yellow]  Completed with {result['failed']} failure(s)",
                    style="bold yellow",
                )
                raise typer.Exit(code=1)
            else:
                if dryrun:
                    console.print(
                        "\n[green]✓[/green] Dry run completed successfully - no changes made!",
                        style="bold green",
                    )
                else:
                    console.print(
                        "\n[green]✓[/green] All services uploaded successfully!",
                        style="bold green",
                    )
                    console.print(
                        "\n[dim]Next steps: Run 'usvc test' to validate, then 'usvc submit' to submit for review.[/dim]"
                    )

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to upload services: {e}", style="bold red")
        raise typer.Exit(code=1)
