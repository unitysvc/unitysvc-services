from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field, HttpUrl, field_validator

from .base import (
    AccessInterface,
    Document,
    Pricing,
    TagEnum,
    validate_name,
)
from .service_data import ServiceOfferingData


class ServiceV1(ServiceOfferingData):
    """
    Service offering model for file-based definitions (service_v1 schema).

    Extends ServiceOfferingData with:
    - schema_version: Schema identifier for file validation
    - time_created: Timestamp for file creation
    - logo: Convenience field (converted to documents during import)
    - tags: Tags for the service (e.g., bring your own API key)
    - Typed models (AccessInterface, Document, Pricing) instead of dicts
    - Field validators for name format

    This model is used for validating service.json/service.toml files
    created by the CLI tool.
    """

    model_config = ConfigDict(extra="forbid")

    # File-specific fields for validation
    schema_version: str = Field(default="service_v1", description="Schema identifier", alias="schema")
    time_created: datetime

    # Override to make required in file validation (base has Optional for API flexibility)
    display_name: str = Field(  # type: ignore[assignment]
        max_length=150,
        description="Human-friendly common name (e.g., 'GPT-4 Turbo')",
    )

    description: str = Field(  # type: ignore[assignment]
        description="Service description",
    )

    # Required in file for static information
    details: dict[str, Any] = Field(  # type: ignore[assignment]
        description="Dictionary of static features and information",
    )

    # Convenience field for logo (converted to documents during import)
    logo: str | HttpUrl | None = None

    # Tags for the service
    tags: list[TagEnum] | None = Field(
        default=None,
        description="List of tags for the service, e.g., bring your own API key",
    )

    # Override with typed models for file validation
    upstream_access_interface: AccessInterface = Field(  # type: ignore[assignment]
        description="Dictionary of upstream access interface",
    )

    documents: list[Document] | None = Field(  # type: ignore[assignment]
        default=None,
        description="List of documents associated with the service (e.g. tech spec.)",
    )

    seller_price: Pricing | None = Field(  # type: ignore[assignment]
        default=None,
        description="Seller pricing information",
    )

    @field_validator("name")
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        """Validate that service name uses valid identifiers (allows slashes for hierarchical names)."""
        return validate_name(v, "service", allow_slash=True)
