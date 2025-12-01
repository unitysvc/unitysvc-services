from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field, HttpUrl, field_validator

from .base import AccessInterface, Document, validate_name
from .provider_data import ProviderData


class ProviderV1(ProviderData):
    """
    Provider information for service providers (provider_v1 schema).

    Extends ProviderData with:
    - schema_version: Schema identifier for file validation
    - time_created: Timestamp for file creation
    - services_populator: How to automatically populate service data
    - provider_access_info: Parameters for accessing service provider
    - logo, terms_of_service: Convenience fields (converted to documents during import)
    - Typed Document model instead of dict for file validation
    - Field validators for name format
    """

    model_config = ConfigDict(extra="forbid")

    # File-specific fields for validation
    schema_version: str = Field(default="provider_v1", description="Schema identifier", alias="schema")
    time_created: datetime

    # How to automatically populate service data, if available
    services_populator: dict[str, Any] | None = None

    # Parameters for accessing service provider (base_url, api_key)
    provider_access_info: AccessInterface = Field(description="Dictionary of upstream access interface")

    # Convenience fields for logo and terms of service (converted to documents during import)
    logo: str | HttpUrl | None = None

    terms_of_service: None | str | HttpUrl = Field(
        default=None,
        description="Either a path to a .md file or a URL to terms of service",
    )

    # Override with typed Document model for file validation
    documents: list[Document] | None = Field(  # type: ignore[assignment]
        default=None,
        description="List of documents associated with the provider (e.g. logo)",
    )

    @field_validator("name")
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        """Validate that provider name uses URL-safe identifiers."""
        return validate_name(v, "provider", allow_slash=False)
