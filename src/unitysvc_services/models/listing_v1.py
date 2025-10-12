from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from unitysvc_services.models.base import (
    AccessInterface,
    Document,
    ListingStatusEnum,
    Pricing,
    validate_name,
)


class ListingV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    #
    # fields for business data collection and maintenance
    #
    schema_version: str = Field(default="listing_v1", description="Schema identifier", alias="schema")
    time_created: datetime

    #
    # fields that will be stored in backend database
    #
    service_name: str | None = Field(
        default=None,
        description=(
            "Name of the service (ServiceV1.name), optional if only one service is defined under the same directory."
        ),
    )

    seller_name: str | None = Field(default=None, description="Name of the seller offering this service listing")

    name: str | None = Field(
        default=None,
        max_length=255,
        description="Name identifier for the service listing, default to filename",
    )

    # Display name for UI (human-readable listing name)
    display_name: str | None = Field(
        default=None,
        max_length=200,
        description="Human-readable listing name (e.g., 'Premium GPT-4 Access', 'Enterprise AI Services')",
    )

    # unique name for each provider, usually following upstream naming convention
    # status of the service, public, deprecated etc
    listing_status: ListingStatusEnum = Field(
        default=ListingStatusEnum.unknown,
        description="Operation status of the service",
    )

    #
    # how to users access the service from upstream, which can include
    #  - endpoint
    #  - access_method
    #  - code_examples
    # multiple access interfaces can be provided, for example, if the service
    # is available through multiple interfaces or service groups
    user_access_interfaces: list[AccessInterface] = Field(description="Dictionary of user access interfaces")

    #
    # how upstream charges for their services, which can include
    # a list of pricing models
    #
    user_price: Pricing | None = Field(description="Dictionary of pricing information")

    documents: list[Document] | None = Field(
        default=None,
        description="List of documents associated with the listing (e.g. service level agreements)",
    )
    #
    # schema for accepting user parameters for the service
    #
    user_parameters_schema: dict[str, Any] | None = Field(
        default=None, description="Dictionary of user parameters schema"
    )

    user_parameters_ui_schema: dict[str, Any] | None = Field(
        default=None, description="Dictionary of user parameters UI schema"
    )

    @field_validator("name")
    @classmethod
    def validate_name_format(cls, v: str | None) -> str | None:
        """Validate that listing name uses valid identifiers (allows slashes for hierarchical names)."""
        if v is None:
            return v
        return validate_name(v, "listing", allow_slash=True)
