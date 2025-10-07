from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from unitysvc_services.models.base import (
    AccessInterface,
    Document,
    ListingStatusEnum,
    Pricing,
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

    seller_name: str = Field(description="Name of the seller offering this service listing")

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
