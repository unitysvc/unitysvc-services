"""Base data models for service listings.

This module defines `ServiceListingData`, a base model containing the core fields
for service listing data that is shared between:
- unitysvc-services (CLI): Used for file-based listing definitions
- unitysvc (backend): Used for API payloads and database operations

The `ListingV1` model extends this with file-specific fields like `schema_version`
and `time_created` for data file validation.
"""

from typing import Any

from pydantic import BaseModel, Field

from .base import ListingStatusEnum


class ServiceListingData(BaseModel):
    """
    Base data structure for service listing information.

    This model contains the core fields needed to describe a service listing,
    without file-specific validation fields. It serves as:

    1. The base class for `ListingV1` in unitysvc-services (with additional
       schema_version and time_created fields for file validation)

    2. The data structure imported by unitysvc backend for:
       - API payload validation
       - Database comparison logic in find_and_compare_service_listing()
       - Publish operations from CLI

    Key characteristics:
    - Uses string identifiers (service_name, provider_name, seller_name)
      that get resolved to database IDs by the backend
    - Contains all user-provided data without system-generated IDs
    - Does not include permission/audit fields (handled by backend CRUD layer)
    - Uses dict types for nested structures to maintain flexibility between
      file definitions and database operations
    """

    # Reference to service offering - required for backend resolution
    service_name: str | None = Field(
        default=None,
        description=(
            "Name of the service (ServiceV1.name), optional if only one service is defined under the same directory."
        ),
    )
    service_version: str | None = Field(
        default=None,
        description="Version of the service offering",
    )
    provider_name: str | None = Field(
        default=None,
        description="Provider name (resolved from directory structure if not specified)",
    )

    # Seller info
    seller_name: str | None = Field(
        default=None,
        description="Name of the seller offering this service listing",
    )

    # Listing identification
    name: str | None = Field(
        default=None,
        max_length=255,
        description="Name identifier for the service listing (defaults to 'default' if not provided)",
    )

    # Display name for UI
    display_name: str | None = Field(
        default=None,
        max_length=200,
        description="Human-readable listing name (e.g., 'Premium GPT-4 Access', 'Enterprise AI Services')",
    )

    # Status - seller-accessible statuses
    listing_status: ListingStatusEnum = Field(
        default=ListingStatusEnum.draft,
        description="Listing status: draft (skip publish), ready (ready for admin review), or deprecated (retired)",
    )

    # Customer pricing
    customer_price: dict[str, Any] | None = Field(
        default=None,
        description="Customer pricing: What the customer pays for each unit of service usage",
    )

    # Access interfaces
    user_access_interfaces: list[dict[str, Any]] | None = Field(
        default=None,
        description="List of user access interfaces for the listing",
    )

    # Documents
    documents: list[dict[str, Any]] | None = Field(
        default=None,
        description="List of documents associated with the listing (e.g., service level agreements)",
    )

    # User parameters
    user_parameters_schema: dict[str, Any] | None = Field(
        default=None,
        description="JSON Schema for user parameters",
    )

    user_parameters_ui_schema: dict[str, Any] | None = Field(
        default=None,
        description="UI schema for user parameters form rendering",
    )
