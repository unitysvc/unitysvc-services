from datetime import datetime

from pydantic import ConfigDict, Field, HttpUrl, field_validator

from .base import Document, validate_name
from .seller_data import SellerData


class SellerV1(SellerData):
    """
    Seller information for marketplace sellers (seller_v1 schema).

    Extends SellerData with:
    - schema_version: Schema identifier for file validation
    - time_created: Timestamp for file creation
    - logo: Convenience field (converted to documents during import)
    - Typed Document model instead of dict for file validation
    - Field validators for name format

    Each repository can only have one seller.json file at the root of the data directory.
    """

    model_config = ConfigDict(extra="forbid")

    # File-specific fields for validation
    schema_version: str = Field(default="seller_v1", description="Schema identifier", alias="schema")
    time_created: datetime

    # Convenience field for logo (converted to documents during import)
    logo: str | HttpUrl | None = None

    # Override with typed Document model for file validation
    documents: list[Document] | None = Field(  # type: ignore[assignment]
        default=None,
        description="List of documents associated with the seller (e.g. business registration, tax documents)",
    )

    @field_validator("name")
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        """Validate that seller name uses URL-safe identifiers."""
        return validate_name(v, "seller", allow_slash=False)
