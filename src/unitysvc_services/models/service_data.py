"""Base data model for service offerings.

This module defines `ServiceOfferingData`, a base model containing the core fields
for service offering data that is shared between:
- unitysvc-services (CLI): Used for file-based service definitions
- unitysvc (backend): Used for API payloads and database operations

The `ServiceV1` model extends this with file-specific fields like `schema_version`
and `time_created` for data file validation.
"""

from typing import Any

from pydantic import BaseModel, Field

from .base import ServiceTypeEnum, UpstreamStatusEnum


class ServiceOfferingData(BaseModel):
    """
    Base data structure for service offering information.

    This model contains the core fields needed to describe a service offering,
    without file-specific validation fields. It serves as:

    1. The base class for `ServiceV1` in unitysvc-services (with additional
       schema_version and time_created fields for file validation)

    2. The data structure imported by unitysvc backend for:
       - API payload validation
       - Database comparison logic in find_and_compare_service_offering()
       - Publish operations from CLI

    Key characteristics:
    - Uses string identifiers (provider_name) that get resolved to database IDs
    - upstream_status maps to database 'status' field
    - Contains all user-provided data without system-generated IDs
    - Does not include permission/audit fields (handled by backend CRUD layer)
    """

    # Service identification
    name: str = Field(
        description="Technical service name (e.g., 'gpt-4')",
        max_length=100,
    )

    display_name: str | None = Field(
        default=None,
        max_length=150,
        description="Human-friendly common name (e.g., 'GPT-4 Turbo')",
    )

    version: str | None = Field(
        default=None,
        max_length=50,
        description="Service version if applicable",
    )

    service_type: ServiceTypeEnum = Field(
        default=ServiceTypeEnum.llm,
        description="Category for grouping/comparison",
    )

    description: str | None = Field(
        default=None,
        description="Service description",
    )

    tagline: str | None = Field(
        default=None,
        description="Short elevator pitch or description for the service",
    )

    # Provider info (resolved by publish layer)
    provider_name: str | None = Field(
        default=None,
        description="Provider name (resolved from directory structure if not specified)",
    )

    # Status
    upstream_status: UpstreamStatusEnum = Field(
        default=UpstreamStatusEnum.ready,
        description="Status of the service from upstream service provider",
    )

    # Technical details
    details: dict[str, Any] | None = Field(
        default=None,
        description="Static technical specifications and features",
    )

    # Pricing
    seller_price: dict[str, Any] | None = Field(
        default=None,
        description="Seller pricing: The agreed rate between seller and UnitySVC",
    )

    # Access interface
    upstream_access_interface: dict[str, Any] | None = Field(
        default=None,
        description="How to access the service from upstream",
    )

    # Documents
    documents: list[dict[str, Any]] | None = Field(
        default=None,
        description="List of documents associated with the service",
    )
