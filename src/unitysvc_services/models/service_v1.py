from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from unitysvc_services.models.base import (
    AccessInterface,
    Document,
    Pricing,
    ServiceTypeEnum,
    TagEnum,
    UpstreamStatusEnum,
    validate_name,
)


class ServiceV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    #
    # fields for business data collection and maintenance
    #
    schema_version: str = Field(default="service_v1", description="Schema identifier", alias="schema")
    time_created: datetime

    #
    # fields that will be stored in backend database
    #
    # unique name for each provider, usually following upstream naming convention
    name: str
    # type of service to group services
    service_type: ServiceTypeEnum
    # common display name for the service, allowing across provider linking
    display_name: str
    # version of the service, this, combined with display_name, allowing across provider linking
    # of specific services, despite of provider internal naming conventions. Note that
    # same display_name and version does not guarantee the same service (e.g. context window
    # can be different)
    version: str | None

    # description of service, mandatory
    description: str

    # this field is added for convenience. It will be converted to
    # documents during importing.
    logo: str | HttpUrl | None = None

    # Short elevator pitch or description for the service
    tagline: str | None = None

    # Tags for the service, e.g., bring your own API key
    tags: list[TagEnum] | None = Field(
        default=None,
        description="List of tags for the service, e.g., bring your own API key",
    )

    # status of the service, public, deprecated etc
    upstream_status: UpstreamStatusEnum = Field(
        default=UpstreamStatusEnum.ready,
        description="Status of the service from upstream service provider",
    )

    # static information from upstream, each service_type will have a
    # set of mandatory fields
    details: dict[str, Any] = Field(description="Dictionary of static features and information")

    documents: list[Document] | None = Field(
        default=None,
        description="List of documents associated with the service (e.g. tech spec.)",
    )
    #
    # how to access the service from upstream, which can include
    #  - endpoint
    #  - apikey
    #  - access_method
    upstream_access_interface: AccessInterface = Field(description="Dictionary of upstream access interface")
    #
    # how upstream charges for their services, which can include
    # a list of pricing models
    #
    upstream_price: Pricing | None = Field(description="List of pricing information")

    @field_validator("name")
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        """Validate that service name uses valid identifiers (allows slashes for hierarchical names)."""
        return validate_name(v, "service", allow_slash=True)
