from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.functional_validators import BeforeValidator


def _validate_price_string(v: Any) -> str:
    """Validate that price values are strings representing valid non-negative decimal numbers.

    This prevents floating-point precision issues where values like 2.0
    might become 1.9999999 when saved/loaded. Prices are stored as strings
    and converted to Decimal only when calculations are needed.
    """
    if isinstance(v, float):
        raise ValueError(
            f"Price value must be a string (e.g., '0.50'), not a float ({v}). Floats can cause precision issues."
        )

    # Convert int to string first
    if isinstance(v, int):
        v = str(v)

    if not isinstance(v, str):
        raise ValueError(f"Price value must be a string, got {type(v).__name__}")

    # Validate it's a valid decimal number and non-negative
    try:
        decimal_val = Decimal(v)
    except InvalidOperation:
        raise ValueError(f"Price value '{v}' is not a valid decimal number")

    if decimal_val < 0:
        raise ValueError(f"Price value must be non-negative, got '{v}'")

    return v


# Price string type that only accepts strings/ints, not floats
PriceStr = Annotated[str, BeforeValidator(_validate_price_string)]


# ============================================================================
# Usage Data for cost calculation
# ============================================================================


class UsageData(BaseModel):
    """
    Usage data for cost calculation.

    Different pricing types require different usage fields:
    - one_million_tokens: input_tokens, output_tokens (or total_tokens)
    - one_second: seconds
    - image: count
    - step: count

    Extra fields are ignored, so you can pass **usage_info directly.
    """

    model_config = ConfigDict(extra="ignore")

    # Token-based usage (for LLMs)
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None  # Alternative to input/output for unified pricing

    # Time-based usage
    seconds: float | None = None

    # Count-based usage (images, steps, requests)
    count: int | None = None


class AccessMethodEnum(StrEnum):
    http = "http"
    websocket = "websocket"
    grpc = "grpc"


class CurrencyEnum(StrEnum):
    """Supported currency codes for pricing."""

    # Traditional currencies
    USD = "USD"  # US Dollar
    EUR = "EUR"  # Euro
    GBP = "GBP"  # British Pound
    JPY = "JPY"  # Japanese Yen
    CNY = "CNY"  # Chinese Yuan
    CAD = "CAD"  # Canadian Dollar
    AUD = "AUD"  # Australian Dollar
    CHF = "CHF"  # Swiss Franc
    INR = "INR"  # Indian Rupee
    KRW = "KRW"  # Korean Won

    # Cryptocurrencies
    BTC = "BTC"  # Bitcoin
    ETH = "ETH"  # Ethereum
    USDT = "USDT"  # Tether
    USDC = "USDC"  # USD Coin
    TAO = "TAO"  # Bittensor TAO

    # Credits/Points (for platforms that use credits)
    CREDITS = "CREDITS"  # Generic credits system


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
    # Backend-specific contexts
    seller = "seller"  # Documents belong to Seller
    provider = "provider"  # Documents belong to Provider


class DocumentCategoryEnum(StrEnum):
    getting_started = "getting_started"
    api_reference = "api_reference"
    tutorial = "tutorial"
    code_example = "code_example"
    code_example_output = "code_example_output"
    use_case = "use_case"
    troubleshooting = "troubleshooting"
    changelog = "changelog"
    best_practice = "best_practice"
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
    service_subscription = "service_subscription"  # User's subscription to a service


class SellerTypeEnum(StrEnum):
    individual = "individual"
    organization = "organization"
    partnership = "partnership"
    corporation = "corporation"


class ListingStatusEnum(StrEnum):
    """
    Listing status values that sellers can set locally.

    Seller-accessible statuses:
    - draft: Listing is being worked on, skipped during publish (won't be sent to backend)
    - ready: Listing is complete and ready for admin review/testing
    - deprecated: Seller marks service as retired/replaced

    Note: Admin-managed workflow statuses (upstream_ready, downstream_ready, in_service)
    are set by the backend admin after testing and validation. These are not included in this
    enum since sellers cannot set them through the CLI tool.
    """

    # Still being worked on - skip during publish
    draft = "draft"
    # Ready for admin review and testing
    ready = "ready"
    # No longer offered
    deprecated = "deprecated"


class OveragePolicyEnum(StrEnum):
    block = "block"  # Block requests when quota exceeded
    throttle = "throttle"  # Reduce rate when quota exceeded
    charge = "charge"  # Allow with additional charges
    queue = "queue"  # Queue requests until quota resets


class PricingTypeEnum(StrEnum):
    """
    Pricing type determines how price_data is structured and calculated.
    The type is stored inside price_data as the 'type' field.
    """

    one_million_tokens = "one_million_tokens"
    one_second = "one_second"
    image = "image"
    step = "step"
    # Seller-only: seller receives a percentage of what customer pays
    revenue_share = "revenue_share"


# ============================================================================
# Price Data Models - Discriminated Union for type-safe price_data validation
# ============================================================================


class BasePriceData(BaseModel):
    """Base class for all price data types."""

    model_config = ConfigDict(extra="forbid")


class TokenPriceData(BasePriceData):
    """
    Price data for token-based pricing (LLMs).
    Supports either unified pricing or separate input/output pricing.

    Price values use Decimal for precision. In JSON/TOML, specify as strings
    (e.g., "0.50") to avoid floating-point precision issues.
    """

    type: Literal["one_million_tokens"] = "one_million_tokens"

    # Option 1: Unified price for all tokens
    price: PriceStr | None = Field(
        default=None,
        description="Unified price per million tokens (used when input/output are the same)",
    )

    # Option 2: Separate input/output pricing
    input: PriceStr | None = Field(
        default=None,
        description="Price per million input tokens",
    )
    output: PriceStr | None = Field(
        default=None,
        description="Price per million output tokens",
    )

    @model_validator(mode="after")
    def validate_price_fields(self) -> TokenPriceData:
        """Ensure either unified price or input/output pair is provided."""
        has_unified = self.price is not None
        has_input_output = self.input is not None or self.output is not None

        if has_unified and has_input_output:
            raise ValueError(
                "Cannot specify both 'price' and 'input'/'output'. "
                "Use 'price' for unified pricing or 'input'/'output' for separate pricing."
            )

        if not has_unified and not has_input_output:
            raise ValueError("Must specify either 'price' (unified) or 'input'/'output' (separate pricing).")

        if has_input_output and (self.input is None or self.output is None):
            raise ValueError("Both 'input' and 'output' must be specified for separate pricing.")

        return self

    def calculate_cost(self, usage: UsageData) -> Decimal:
        """Calculate cost for token-based pricing."""
        input_tokens = usage.input_tokens or 0
        output_tokens = usage.output_tokens or 0

        if usage.total_tokens is not None and usage.input_tokens is None:
            input_tokens = usage.total_tokens
            output_tokens = 0

        if self.input is not None and self.output is not None:
            input_cost = Decimal(self.input) * input_tokens / 1_000_000
            output_cost = Decimal(self.output) * output_tokens / 1_000_000
        else:
            price = Decimal(self.price)  # type: ignore[arg-type]
            input_cost = price * input_tokens / 1_000_000
            output_cost = price * output_tokens / 1_000_000

        return input_cost + output_cost


class TimePriceData(BasePriceData):
    """
    Price data for time-based pricing (audio/video processing, compute time).

    Price values use Decimal for precision. In JSON/TOML, specify as strings
    (e.g., "0.006") to avoid floating-point precision issues.
    """

    type: Literal["one_second"] = "one_second"

    price: PriceStr = Field(
        description="Price per second of usage",
    )

    def calculate_cost(self, usage: UsageData) -> Decimal:
        """Calculate cost for time-based pricing."""
        if usage.seconds is None:
            raise ValueError("Time-based pricing requires 'seconds' in usage data")

        return Decimal(self.price) * Decimal(str(usage.seconds))


class ImagePriceData(BasePriceData):
    """
    Price data for per-image pricing (image generation, processing).

    Price values use Decimal for precision. In JSON/TOML, specify as strings
    (e.g., "0.04") to avoid floating-point precision issues.
    """

    type: Literal["image"] = "image"

    price: PriceStr = Field(
        description="Price per image",
    )

    def calculate_cost(self, usage: UsageData) -> Decimal:
        """Calculate cost for image-based pricing."""
        if usage.count is None:
            raise ValueError("Image pricing requires 'count' in usage data")

        return Decimal(self.price) * usage.count


class StepPriceData(BasePriceData):
    """
    Price data for per-step pricing (diffusion steps, iterations).

    Price values use Decimal for precision. In JSON/TOML, specify as strings
    (e.g., "0.001") to avoid floating-point precision issues.
    """

    type: Literal["step"] = "step"

    price: PriceStr = Field(
        description="Price per step/iteration",
    )

    def calculate_cost(self, usage: UsageData) -> Decimal:
        """Calculate cost for step-based pricing."""
        if usage.count is None:
            raise ValueError("Step pricing requires 'count' in usage data")

        return Decimal(self.price) * usage.count


def _validate_percentage_string(v: Any) -> str:
    """Validate that percentage values are strings representing valid decimals in range 0-100."""
    # First use the standard price validation
    v = _validate_price_string(v)

    # Then check the 0-100 range
    decimal_val = Decimal(v)
    if decimal_val > 100:
        raise ValueError(f"Percentage must be between 0 and 100, got '{v}'")

    return v


# Percentage string type for revenue share (0-100 range)
PercentageStr = Annotated[str, BeforeValidator(_validate_percentage_string)]


class RevenueSharePriceData(BasePriceData):
    """
    Price data for revenue share pricing (seller_price only).

    This pricing type is used exclusively for seller_price when the seller
    receives a percentage of what the customer pays. It cannot be used for
    customer_price since the customer price must be a concrete amount.

    The percentage represents the seller's share of the customer charge.
    For example, if percentage is "70" and the customer pays $10, the seller
    receives $7.

    Percentage values must be strings (e.g., "70.00") to avoid floating-point
    precision issues.
    """

    type: Literal["revenue_share"] = "revenue_share"

    percentage: PercentageStr = Field(
        description="Percentage of customer charge that goes to the seller (0-100)",
    )


# Discriminated union of all price data types
PriceData = Annotated[
    TokenPriceData | TimePriceData | ImagePriceData | StepPriceData | RevenueSharePriceData,
    Field(discriminator="type"),
]


def validate_price_data(
    data: dict[str, Any],
) -> TokenPriceData | TimePriceData | ImagePriceData | StepPriceData | RevenueSharePriceData:
    """
    Validate price_data dict and return the appropriate typed model.

    Args:
        data: Dictionary containing price data with 'type' field

    Returns:
        Validated PriceData model instance

    Raises:
        ValueError: If validation fails

    Example:
        >>> data = {"type": "one_million_tokens", "input": 0.5, "output": 1.5}
        >>> validated = validate_price_data(data)
        >>> print(validated.input)  # 0.5
    """
    from pydantic import TypeAdapter

    adapter: TypeAdapter[TokenPriceData | TimePriceData | ImagePriceData | StepPriceData | RevenueSharePriceData] = (
        TypeAdapter(PriceData)
    )
    return adapter.validate_python(data)


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
    draft = "draft"  # Provider information is incomplete, skip during publish


class SellerStatusEnum(StrEnum):
    """Seller status enum."""

    active = "active"
    pending = "pending"
    disabled = "disabled"
    draft = "draft"  # Seller information is incomplete, skip during publish


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

    base_url: str = Field(max_length=500, description="Base URL for api access")

    api_key: str | None = Field(default=None, max_length=2000, description="API key if required")

    name: str | None = Field(default=None, max_length=100, description="Interface name")

    description: str | None = Field(default=None, max_length=500, description="Interface description")

    request_transformer: dict[RequestTransformEnum, dict[str, Any]] | None = Field(
        default=None, description="Request transformation configuration"
    )

    routing_key: dict[str, Any] | None = Field(
        default=None,
        description="Request routing key for matching (e.g., {'model': 'gpt-4'})",
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
    """
    Universal pricing model for services.

    The price_data field uses a discriminated union based on the 'type' field:
    - "one_million_tokens": TokenPriceData (for LLMs, supports unified or input/output pricing)
    - "one_second": TimePriceData (for audio/video, compute time)
    - "image": ImagePriceData (for image generation)
    - "step": StepPriceData (for diffusion steps, iterations)

    Example usage:
        # Token pricing with separate input/output
        Pricing(
            currency=CurrencyEnum.USD,
            price_data={"type": "one_million_tokens", "input": 0.5, "output": 1.5}
        )

        # Image pricing
        Pricing(
            currency=CurrencyEnum.USD,
            price_data={"type": "image", "price": 0.04}
        )
    """

    model_config = ConfigDict(extra="forbid")

    description: str | None = Field(default=None, description="Pricing model description")

    currency: CurrencyEnum | None = Field(default=None, description="Currency code (e.g., USD)")

    # Price data with type-based validation
    # Use get_validated_price_data() to get the typed model
    price_data: PriceData = Field(
        description="Price data with 'type' field determining structure. "
        "See TokenPriceData, TimePriceData, ImagePriceData, StepPriceData for valid structures.",
    )

    # Optional reference to upstream pricing
    reference: str | None = Field(default=None, description="Reference URL to upstream pricing")

    def get_price_type(self) -> str:
        """Get the pricing type from price_data."""
        return self.price_data.type

    def get_unified_price(self) -> str | None:
        """
        Get unified price if available.
        Returns the 'price' field for all types, or None for input/output token pricing.
        """
        if hasattr(self.price_data, "price"):
            return self.price_data.price  # type: ignore[return-value]
        return None

    def get_input_output_prices(self) -> tuple[str, str] | None:
        """
        Get input/output prices for token-based pricing.
        Returns (input_price, output_price) tuple or None if not applicable.
        """
        if isinstance(self.price_data, TokenPriceData):
            if self.price_data.input is not None and self.price_data.output is not None:
                return (self.price_data.input, self.price_data.output)
        return None


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
