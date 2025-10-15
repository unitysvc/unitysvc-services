import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AccessMethodEnum(StrEnum):
    http = "http"
    websocket = "websocket"
    grpc = "grpc"


class AuthMethodEnum(StrEnum):
    api_key = "api_key"
    oauth = "oauth"
    jwt = "jwt"
    bearer_token = "bearer_token"
    basic_auth = "basic_auth"


class ContentFilterEnum(StrEnum):
    adult = "adult"
    violence = "violence"
    hate_speech = "hate_speech"
    profanity = "profanity"
    pii = "pii"  # Personally Identifiable Information


class DocumentContextEnum(StrEnum):
    access_interface = "access_interface"  # Documents belong to AccessInterface
    service_definition = "service_definition"  # Documents belong to ServiceDefinition
    service_offering = "service_offering"  # Documents belong to ServiceOffering
    service_listing = "service_listing"  # Documents belong to ServiceListing
    user = "user"  # can be for seller, subscriber, consumer


class DocumentCategoryEnum(StrEnum):
    getting_started = "getting_started"
    api_reference = "api_reference"
    tutorials = "tutorials"
    code_examples = "code_examples"
    use_cases = "use_cases"
    troubleshooting = "troubleshooting"
    changelog = "changelog"
    best_practices = "best_practices"
    specification = "specification"
    service_level_agreement = "service_level_agreement"
    terms_of_service = "terms_of_service"
    invoice = "invoice"
    logo = "logo"
    avatar = "avatar"
    other = "other"


class MimeTypeEnum(StrEnum):
    markdown = "markdown"
    python = "python"
    javascript = "javascript"
    bash = "bash"
    html = "html"
    text = "text"
    pdf = "pdf"
    jpeg = "jpeg"
    png = "png"
    svg = "svg"
    url = "url"


class InterfaceContextTypeEnum(StrEnum):
    service_offering = "service_offering"  # Pricing from upstream provider
    service_listing = "service_listing"  # Pricing shown to end users


class SellerTypeEnum(StrEnum):
    individual = "individual"
    organization = "organization"
    partnership = "partnership"
    corporation = "corporation"


class ListingStatusEnum(StrEnum):
    # Not yet determined
    unknown = "unknown"
    # step 1: upstream is ready to be used
    upstream_ready = "upstream_ready"
    # step 2: downstream is ready, with proper routing, logging, and billing
    downstream_ready = "downstream_ready"
    # step 3: service is operationally ready (with proper documentation and initial
    # performance metrics, and pricing strategy)
    ready = "ready"
    # step 4: service is in service
    in_service = "in_service"
    # step 5.1: service is deprecated from upstream
    upstream_deprecated = "upstream_deprecated"
    # step 5.2: service is no longer offered to users (due to business reasons)
    deprecated = "deprecated"


class OveragePolicyEnum(StrEnum):
    block = "block"  # Block requests when quota exceeded
    throttle = "throttle"  # Reduce rate when quota exceeded
    charge = "charge"  # Allow with additional charges
    queue = "queue"  # Queue requests until quota resets


class PricingTypeEnum(StrEnum):
    upstream = "upstream"  # Pricing from upstream provider
    user_facing = "user_facing"  # Pricing shown to end users


class PricingUnitEnum(StrEnum):
    one_million_tokens = "one_million_tokens"
    one_second = "one_second"
    image = "image"
    step = "step"


class QuotaResetCycleEnum(StrEnum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"


class RateLimitUnitEnum(StrEnum):
    requests = "requests"
    tokens = "tokens"
    input_tokens = "input_tokens"
    output_tokens = "output_tokens"
    bytes = "bytes"
    concurrent = "concurrent"


class RequestTransformEnum(StrEnum):
    # https://docs.api7.ai/hub/proxy-rewrite
    proxy_rewrite = "proxy_rewrite"
    # https://docs.api7.ai/hub/body-transformer
    body_transformer = "body_transformer"


class ServiceTypeEnum(StrEnum):
    llm = "llm"
    # generate embedding from texts
    embedding = "embedding"
    # generation of images from prompts
    image_generation = "image_generation"
    # streaming trancription needs websocket connection forwarding, and cannot
    # be provided for now.
    streaming_transcription = "streaming_transcription"
    # prerecorded transcription
    prerecorded_transcription = "prerecorded_transcription"
    # prerecorded translation
    prerecorded_translation = "prerecorded_translation"
    # describe images
    vision_language_model = "vision_language_model"
    #
    speech_to_text = "speech_to_text"
    #
    text_to_speech = "text_to_speech"
    #
    video_generation = "video_generation"
    #
    text_to_image = "text_to_image"
    #
    undetermined = "undetermined"
    #
    text_to_3d = "text_to_3d"


class SubscriptionStatusEnum(StrEnum):
    active = "active"
    cancelled = "cancelled"
    expired = "expired"
    pending = "pending"
    trialing = "trialing"
    failed = "failed"
    paused = "paused"
    incomplete = "incomplete"
    incomplete_expired = "incomplete_expired"
    unpaid = "unpaid"


class TagEnum(StrEnum):
    """
    Allowed enums, currently not enforced.
    """

    # Service requires users to provide their own API key for access.
    byop = "byop"


class TimeWindowEnum(StrEnum):
    second = "second"
    minute = "minute"
    hour = "hour"
    day = "day"
    month = "month"


class UpstreamStatusEnum(StrEnum):
    # uploading (not ready)
    uploading = "uploading"
    # upstream is ready to be used
    ready = "ready"
    # service is deprecated from upstream
    deprecated = "deprecated"


class ProviderStatusEnum(StrEnum):
    """Provider status enum."""

    active = "active"
    pending = "pending"
    disabled = "disabled"
    incomplete = "incomplete"  # Provider information is incomplete


class SellerStatusEnum(StrEnum):
    """Seller status enum."""

    active = "active"
    pending = "pending"
    disabled = "disabled"
    incomplete = "incomplete"  # Seller information is incomplete


class Document(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # fields that will be stored in backend database
    #
    title: str = Field(min_length=5, max_length=255, description="Document title")
    description: str | None = Field(default=None, max_length=500, description="Document description")
    mime_type: MimeTypeEnum = Field(description="Document MIME type")
    version: str | None = Field(default=None, max_length=50, description="Document version")
    category: DocumentCategoryEnum = Field(description="Document category for organization and filtering")
    meta: dict[str, Any] | None = Field(
        default=None,
        description="JSON containing operation stats",
    )
    file_path: str | None = Field(
        default=None,
        max_length=1000,
        description="Path to file to upload (mutually exclusive with external_url)",
    )
    external_url: str | None = Field(
        default=None,
        max_length=1000,
        description="External URL for the document (mutually exclusive with object_key)",
    )
    sort_order: int = Field(default=0, description="Sort order within category")
    is_active: bool = Field(default=True, description="Whether document is active")
    is_public: bool = Field(
        default=False,
        description="Whether document is publicly accessible without authentication",
    )


class RateLimit(BaseModel):
    """Store rate limiting rules for services."""

    model_config = ConfigDict(extra="forbid")

    # Core rate limit definition
    limit: int = Field(description="Maximum allowed in the time window")
    unit: RateLimitUnitEnum = Field(description="What is being limited")
    window: TimeWindowEnum = Field(description="Time window for the limit")

    # Optional additional info
    description: str | None = Field(default=None, max_length=255, description="Human-readable description")
    burst_limit: int | None = Field(default=None, description="Short-term burst allowance")

    # Status
    is_active: bool = Field(default=True, description="Whether rate limit is active")


class ServiceConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Usage Quotas & Billing
    monthly_quota: int | None = Field(default=None, description="Monthly usage quota (requests, tokens, etc.)")
    daily_quota: int | None = Field(default=None, description="Daily usage quota (requests, tokens, etc.)")
    quota_unit: RateLimitUnitEnum | None = Field(default=None, description="Unit for quota limits")
    quota_reset_cycle: QuotaResetCycleEnum | None = Field(default=None, description="How often quotas reset")
    overage_policy: OveragePolicyEnum | None = Field(default=None, description="What happens when quota is exceeded")

    # Authentication & Security
    auth_methods: list[AuthMethodEnum] | None = Field(default=None, description="Supported authentication methods")
    ip_whitelist_required: bool | None = Field(default=None, description="Whether IP whitelisting is required")
    tls_version_min: str | None = Field(default=None, description="Minimum TLS version required")

    # Request/Response Constraints
    max_request_size_bytes: int | None = Field(default=None, description="Maximum request payload size in bytes")
    max_response_size_bytes: int | None = Field(default=None, description="Maximum response payload size in bytes")
    timeout_seconds: int | None = Field(default=None, description="Request timeout in seconds")
    max_batch_size: int | None = Field(default=None, description="Maximum number of items in batch requests")

    # Content & Model Restrictions
    content_filters: list[ContentFilterEnum] | None = Field(
        default=None, description="Active content filtering policies"
    )
    input_languages: list[str] | None = Field(default=None, description="Supported input languages (ISO 639-1 codes)")
    output_languages: list[str] | None = Field(default=None, description="Supported output languages (ISO 639-1 codes)")
    max_context_length: int | None = Field(default=None, description="Maximum context length in tokens")
    region_restrictions: list[str] | None = Field(
        default=None, description="Geographic restrictions (ISO country codes)"
    )

    # Availability & SLA
    uptime_sla_percent: float | None = Field(default=None, description="Uptime SLA percentage (e.g., 99.9)")
    response_time_sla_ms: int | None = Field(default=None, description="Response time SLA in milliseconds")
    maintenance_windows: list[str] | None = Field(default=None, description="Scheduled maintenance windows")

    # Concurrency & Connection Limits
    max_concurrent_requests: int | None = Field(default=None, description="Maximum concurrent requests allowed")
    connection_timeout_seconds: int | None = Field(default=None, description="Connection timeout in seconds")
    max_connections_per_ip: int | None = Field(default=None, description="Maximum connections per IP address")


class AccessInterface(BaseModel):
    model_config = ConfigDict(extra="allow")

    access_method: AccessMethodEnum = Field(default=AccessMethodEnum.http, description="Type of access method")

    api_endpoint: str = Field(max_length=500, description="API endpoint URL")

    api_key: str | None = Field(default=None, max_length=2000, description="API key if required")

    name: str | None = Field(default=None, max_length=100, description="Interface name")

    description: str | None = Field(default=None, max_length=500, description="Interface description")

    request_transformer: dict[RequestTransformEnum, dict[str, Any]] | None = Field(
        default=None, description="Request transformation configuration"
    )

    documents: list[Document] | None = Field(
        default=None, description="List of documents associated with the interface"
    )

    rate_limits: list[RateLimit] | None = Field(
        default=None,
        description="Rate limit",
    )
    constraint: ServiceConstraints | None = Field(default=None, description="Service constraints and conditions")
    is_active: bool = Field(default=True, description="Whether interface is active")
    is_primary: bool = Field(default=False, description="Whether this is the primary interface")
    sort_order: int = Field(default=0, description="Display order")


class Pricing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Pricing tier name (Basic, Pro, Enterprise, etc.)
    name: str | None = Field(default=None, description="Pricing tier name (e.g., Basic, Pro, Enterprise)")

    description: str | None = Field(default=None, description="Pricing model description")

    # Currency and description
    currency: str | None = Field(default=None, description="Currency code (e.g., USD)")

    unit: PricingUnitEnum = Field(description="Unit of pricing")

    # Store price as JSON - flexible structure for different pricing models
    price_data: dict[str, Any] = Field(
        description="JSON containing price data (single price, tiered, usage-based, etc.)",
    )

    # Optional reference to upstream pricing
    reference: str | None = Field(default=None, description="Reference URL to upstream pricing")


def validate_name(name: str, entity_type: str, display_name: str | None = None, *, allow_slash: bool = False) -> str:
    """
    Validate that a name field uses valid identifiers.

    Name format rules:
    - Only letters (upper/lowercase), numbers, dots, dashes, and underscores allowed
    - If allow_slash=True, slashes are also allowed for hierarchical names
    - Must start and end with alphanumeric characters (not special characters)
    - Cannot have consecutive slashes (when allow_slash=True)
    - Cannot be empty

    Args:
        name: The name value to validate
        entity_type: Type of entity (provider, seller, service, listing) for error messages
        display_name: Optional display name to suggest a valid name from
        allow_slash: Whether to allow slashes for hierarchical names (default: False)

    Returns:
        The validated name (unchanged if valid)

    Raises:
        ValueError: If the name doesn't match the required pattern

    Examples:
        Without slashes (providers, sellers):
            - name='amazon-bedrock' or name='Amazon-Bedrock'
            - name='fireworks.ai' or name='Fireworks.ai'
            - name='llama-3.1' or name='Llama-3.1'

        With slashes (services, listings):
            - name='gpt-4' or name='GPT-4'
            - name='models/gpt-4' or name='models/GPT-4'
            - name='black-forest-labs/FLUX.1-dev'
            - name='api/v1/completion'
    """
    # Build pattern based on allow_slash parameter
    if allow_slash:
        # Pattern: starts with alphanumeric, can contain alphanumeric/dot/dash/underscore/slash, ends with alphanumeric
        name_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9._/-]*[a-zA-Z0-9])?$"
        allowed_chars = "letters, numbers, dots, dashes, underscores, and slashes"
    else:
        # Pattern: starts with alphanumeric, can contain alphanumeric/dot/dash/underscore, ends with alphanumeric
        name_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$"
        allowed_chars = "letters, numbers, dots, dashes, and underscores"

    # Check for consecutive slashes if slashes are allowed
    if allow_slash and "//" in name:
        raise ValueError(f"Invalid {entity_type} name '{name}'. Name cannot contain consecutive slashes.")

    if not re.match(name_pattern, name):
        # Build helpful error message
        error_msg = (
            f"Invalid {entity_type} name '{name}'. "
            f"Name must contain only {allowed_chars}. "
            f"It must start and end with an alphanumeric character.\n"
        )

        # Suggest a valid name based on display_name if available
        if display_name:
            suggested_name = suggest_valid_name(display_name, allow_slash=allow_slash)
            if suggested_name and suggested_name != name:
                error_msg += f"  Suggestion: Set name='{suggested_name}' and display_name='{display_name}'\n"

        # Add appropriate examples based on allow_slash
        if allow_slash:
            error_msg += (
                "  Examples:\n"
                "    - name='gpt-4' or name='GPT-4'\n"
                "    - name='models/gpt-4' or name='models/GPT-4'\n"
                "    - name='black-forest-labs/FLUX.1-dev'\n"
                "    - name='api/v1/completion'"
            )
        else:
            error_msg += (
                "  Note: Use 'display_name' field for brand names with spaces and special characters.\n"
                "  Examples:\n"
                "    - name='amazon-bedrock' or name='Amazon-Bedrock'\n"
                "    - name='fireworks.ai' or name='Fireworks.ai'\n"
                "    - name='llama-3.1' or name='Llama-3.1'"
            )

        raise ValueError(error_msg)

    return name


def suggest_valid_name(display_name: str, *, allow_slash: bool = False) -> str:
    """
    Suggest a valid name based on a display name.

    Replaces invalid characters with hyphens and ensures it follows the naming rules.
    Preserves the original case.

    Args:
        display_name: The display name to convert
        allow_slash: Whether to allow slashes for hierarchical names (default: False)

    Returns:
        A suggested valid name
    """
    if allow_slash:
        # Replace characters that aren't alphanumeric, dot, dash, underscore, or slash with hyphens
        suggested = re.sub(r"[^a-zA-Z0-9._/-]+", "-", display_name)
        # Remove leading/trailing special characters
        suggested = suggested.strip("._/-")
        # Collapse multiple consecutive dashes
        suggested = re.sub(r"-+", "-", suggested)
        # Remove consecutive slashes
        suggested = re.sub(r"/+", "/", suggested)
    else:
        # Replace characters that aren't alphanumeric, dot, dash, or underscore with hyphens
        suggested = re.sub(r"[^a-zA-Z0-9._-]+", "-", display_name)
        # Remove leading/trailing dots, dashes, or underscores
        suggested = suggested.strip("._-")
        # Collapse multiple consecutive dashes
        suggested = re.sub(r"-+", "-", suggested)

    return suggested
