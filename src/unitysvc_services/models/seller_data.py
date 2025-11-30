"""Base data model for sellers.

This module defines `SellerData`, a base model containing the core fields
for seller data that is shared between:
- unitysvc-services (CLI): Used for file-based seller definitions
- unitysvc (backend): Used for API payloads and database operations

The `SellerV1` model extends this with file-specific fields like `schema_version`
and `time_created` for data file validation.
"""

from typing import Any

from pydantic import BaseModel, EmailStr, Field, HttpUrl

from .base import SellerStatusEnum, SellerTypeEnum


class SellerData(BaseModel):
    """
    Base data structure for seller information.

    This model contains the core fields needed to describe a seller,
    without file-specific validation fields. It serves as:

    1. The base class for `SellerV1` in unitysvc-services (with additional
       schema_version and time_created fields for file validation)

    2. The data structure imported by unitysvc backend for:
       - API payload validation
       - Database comparison logic in find_and_compare_seller()
       - Publish operations from CLI

    Key characteristics:
    - Uses string identifiers that match database requirements
    - account_manager is a string (username/email) that gets resolved to account_manager_id
    - Contains all user-provided data without system-generated IDs
    - Does not include permission/audit fields (handled by backend CRUD layer)
    """

    # Seller identification
    name: str = Field(
        description="Unique seller identifier (URL-friendly, e.g., 'acme-corp', 'john-doe')",
        min_length=2,
        max_length=100,
    )

    display_name: str | None = Field(
        default=None,
        max_length=200,
        description="Human-readable seller name (e.g., 'ACME Corporation', 'John Doe')",
    )

    # Seller type
    seller_type: SellerTypeEnum = Field(
        default=SellerTypeEnum.individual,
        description="Type of seller entity",
    )

    # Contact information
    contact_email: EmailStr = Field(description="Primary contact email for the seller")

    secondary_contact_email: EmailStr | None = Field(
        default=None,
        description="Secondary contact email",
    )

    account_manager: str | None = Field(
        default=None,
        max_length=100,
        description="Email or username of the user managing this seller account",
    )

    homepage: HttpUrl | None = Field(
        default=None,
        description="Seller's homepage URL",
    )

    # Business information
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Brief description of the seller",
    )

    business_registration: str | None = Field(
        default=None,
        max_length=100,
        description="Business registration number (if organization)",
    )

    tax_id: str | None = Field(
        default=None,
        max_length=100,
        description="Tax identification number (EIN, VAT, etc.)",
    )

    # Stripe Connect integration
    stripe_connect_id: str | None = Field(
        default=None,
        max_length=255,
        description="Stripe Connect account ID for payment processing",
    )

    # Status
    status: SellerStatusEnum = Field(
        default=SellerStatusEnum.active,
        description="Seller status: active, disabled, or draft (skip publish)",
    )

    is_verified: bool = Field(
        default=False,
        description="Whether the seller has been verified (KYC/business verification)",
    )

    # Documents (as dicts for flexibility)
    documents: list[dict[str, Any]] | None = Field(
        default=None,
        description="List of documents associated with the seller",
    )
