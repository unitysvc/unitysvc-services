from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator

from unitysvc_services.models.base import Document, SellerStatusEnum, SellerTypeEnum, validate_name


class SellerV1(BaseModel):
    """
    Seller information for marketplace sellers.

    Each repository can only have one seller.json file at the root of the data directory.
    """

    model_config = ConfigDict(extra="forbid")

    #
    # fields for business data collection and maintenance
    #
    schema_version: str = Field(default="seller_v1", description="Schema identifier", alias="schema")
    time_created: datetime

    #
    # fields that will be stored in backend database
    #

    # Seller name must be unique and URL-friendly (lowercase, hyphens)
    name: str = Field(
        description="Unique seller identifier (URL-friendly, e.g., 'acme-corp', 'john-doe')",
        min_length=2,
        max_length=100,
    )

    # Display name for UI
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

    secondary_contact_email: EmailStr | None = Field(default=None, description="Secondary contact email")

    # Account manager
    account_manager: str | None = Field(
        default=None,
        max_length=100,
        description="Email or username of the user managing this seller account",
    )

    homepage: HttpUrl | None = Field(default=None, description="Seller's homepage URL")

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

    # Documents (logo, business docs, etc.)
    # This field is added for convenience. It will be converted to
    # documents during importing.
    logo: str | HttpUrl | None = None

    documents: list[Document] | None = Field(
        default=None,
        description="List of documents associated with the seller (e.g. business registration, tax documents)",
    )

    #
    # fields for business operation purposes
    #

    # Status field to track seller state
    status: SellerStatusEnum = Field(
        default=SellerStatusEnum.active,
        description="Seller status: active, disabled, or incomplete",
    )

    is_verified: bool = Field(
        default=False,
        description="Whether the seller has been verified (KYC/business verification)",
    )

    @field_validator("name")
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        """Validate that seller name uses URL-safe identifiers."""
        return validate_name(v, "seller", allow_slash=False)
