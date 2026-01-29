from __future__ import annotations

import ast
import operator
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


def _validate_amount_string(v: Any) -> str:
    """Validate that amount values are strings representing valid decimal numbers.

    Similar to _validate_price_string but allows negative values for
    discounts, fees, and adjustments.
    """
    if isinstance(v, float):
        raise ValueError(
            f"Amount value must be a string (e.g., '-5.00'), not a float ({v}). Floats can cause precision issues."
        )

    # Convert int to string first
    if isinstance(v, int):
        v = str(v)

    if not isinstance(v, str):
        raise ValueError(f"Amount value must be a string, got {type(v).__name__}")

    # Validate it's a valid decimal number (can be negative)
    try:
        Decimal(v)
    except InvalidOperation:
        raise ValueError(f"Amount value '{v}' is not a valid decimal number")

    return v


# Amount string type that allows negative values (for fees, discounts)
AmountStr = Annotated[str, BeforeValidator(_validate_amount_string)]


# ============================================================================
# Usage Data for cost calculation
# ============================================================================


class UsageData(BaseModel):
    """
    Usage data for cost calculation.

    Different pricing types require different usage fields:
    - one_million_tokens: input_tokens, output_tokens, cached_input_tokens (or total_tokens)
    - one_second: seconds
    - image: count
    - step: count

    Extra fields are ignored, so you can pass **usage_info directly.
    """

    model_config = ConfigDict(extra="ignore")

    # Token-based usage (for LLMs)
    input_tokens: int | None = None
    cached_input_tokens: int | None = None  # For providers with discounted cached token rates
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
    service_definition = "service_definition"  # Documents belong to ServiceDefinition
    service_offering = "service_offering"  # Documents belong to ServiceOffering
    service_listing = "service_listing"  # Documents belong to ServiceListing
    user = "user"  # can be for seller, subscriber, consumer
    # Backend-specific contexts
    seller = "seller"  # Documents belong to Seller
    provider = "provider"  # Documents belong to Provider
    blog_post = "blog_post"  # Documents belong to BlogPost
    #
    customer_statement = "customer_statement"
    seller_invoice = "seller_invoice"


class DocumentCategoryEnum(StrEnum):
    getting_started = "getting_started"
    api_reference = "api_reference"
    tutorial = "tutorial"
    code_example = "code_example"
    code_example_output = "code_example_output"
    connectivity_test = "connectivity_test"  # Test connectivity & performance (not visible to users)
    use_case = "use_case"
    troubleshooting = "troubleshooting"
    changelog = "changelog"
    best_practice = "best_practice"
    specification = "specification"
    service_level_agreement = "service_level_agreement"
    terms_of_service = "terms_of_service"
    statement = "statement"
    invoice = "invoice"
    logo = "logo"
    avatar = "avatar"
    blog_content = "blog_content"  # Main content for blog posts
    blog_banner = "blog_banner"  # Banner/cover image for blog posts
    attachment = "attachment"  # Attachments for markdown documents
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
    service_subscription = "service_enrollment"  # User's subscription to a service


class SellerTypeEnum(StrEnum):
    individual = "individual"
    organization = "organization"
    partnership = "partnership"
    corporation = "corporation"


class ListingStatusEnum(StrEnum):
    """
    Status values that sellers can set for listings.

    Seller-accessible statuses:
    - draft: Work in progress, skipped during publish (won't be sent to backend)
    - ready: Complete and ready for admin review/testing
    - deprecated: Retired/end of life, no longer offered

    Note: Admin-managed workflow statuses (upstream_ready, downstream_ready, in_service)
    are set by the backend admin after testing and validation. These are not included in this
    enum since sellers cannot set them through the CLI tool.
    """

    draft = "draft"
    ready = "ready"
    deprecated = "deprecated"


class OveragePolicyEnum(StrEnum):
    block = "block"  # Block requests when quota exceeded
    throttle = "throttle"  # Reduce rate when quota exceeded
    charge = "charge"  # Allow with additional charges
    queue = "queue"  # Queue requests until quota resets


class PricingTypeEnum(StrEnum):
    """
    Pricing type determines the structure and calculation method.
    The type is stored as the 'type' field in the pricing object.
    """

    # Basic pricing types
    one_million_tokens = "one_million_tokens"
    one_second = "one_second"
    image = "image"
    step = "step"
    # Seller-only: seller receives a percentage of what customer pays
    revenue_share = "revenue_share"
    # Composite pricing types
    constant = "constant"  # Fixed amount (fee or discount)
    add = "add"  # Sum of multiple prices
    multiply = "multiply"  # Base price multiplied by factor
    # Tiered pricing types
    tiered = "tiered"  # Volume-based tiers (all units at one tier's price)
    graduated = "graduated"  # Graduated tiers (each tier's units at that rate)
    # Expression-based pricing (payout_price only)
    expr = "expr"  # Arbitrary expression using usage metrics


# ============================================================================
# Pricing Models - Discriminated Union for type-safe pricing validation
# ============================================================================


class BasePriceData(BaseModel):
    """Base class for all price data types.

    All pricing types include:
    - type: Discriminator field for the pricing type
    - description: Optional human-readable description
    - reference: Optional URL to upstream pricing page
    """

    model_config = ConfigDict(extra="forbid")

    description: str | None = Field(
        default=None,
        description="Human-readable description of the pricing model",
    )

    reference: str | None = Field(
        default=None,
        description="URL to upstream provider's pricing page",
    )


class TokenPriceData(BasePriceData):
    """
    Price data for token-based pricing (LLMs).
    Supports either unified pricing or separate input/output pricing.
    Optionally supports cached_input pricing for providers that offer discounted rates
    for cached/repeated input tokens.

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
    cached_input: PriceStr | None = Field(
        default=None,
        description="Price per million cached input tokens (optional, for discounted cached rates)",
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

    def calculate_cost(
        self,
        usage: UsageData,
        customer_charge: Decimal | None = None,
        request_count: int | None = None,
    ) -> Decimal:
        """Calculate cost for token-based pricing.

        Args:
            usage: Usage data with token counts (input_tokens, cached_input_tokens, output_tokens)
            customer_charge: Not used for token pricing (ignored)
            request_count: Number of requests (ignored for token pricing)

        Returns:
            Calculated cost based on token usage
        """
        input_tokens = usage.input_tokens or 0
        cached_input_tokens = usage.cached_input_tokens or 0
        output_tokens = usage.output_tokens or 0

        if usage.total_tokens is not None and usage.input_tokens is None:
            input_tokens = usage.total_tokens
            output_tokens = 0

        if self.input is not None and self.output is not None:
            input_cost = Decimal(self.input) * input_tokens / 1_000_000
            # Use cached_input price if available, otherwise fall back to input price
            cached_price = Decimal(self.cached_input) if self.cached_input else Decimal(self.input)
            cached_input_cost = cached_price * cached_input_tokens / 1_000_000
            output_cost = Decimal(self.output) * output_tokens / 1_000_000
        else:
            price = Decimal(self.price)  # type: ignore[arg-type]
            input_cost = price * input_tokens / 1_000_000
            cached_input_cost = price * cached_input_tokens / 1_000_000
            output_cost = price * output_tokens / 1_000_000

        return input_cost + cached_input_cost + output_cost


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

    def calculate_cost(
        self,
        usage: UsageData,
        customer_charge: Decimal | None = None,
        request_count: int | None = None,
    ) -> Decimal:
        """Calculate cost for time-based pricing.

        Args:
            usage: Usage data with seconds
            customer_charge: Not used for time pricing (ignored)
            request_count: Number of requests (ignored for time pricing)

        Returns:
            Calculated cost based on time usage
        """
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

    def calculate_cost(
        self,
        usage: UsageData,
        customer_charge: Decimal | None = None,
        request_count: int | None = None,
    ) -> Decimal:
        """Calculate cost for image-based pricing.

        Args:
            usage: Usage data with count
            customer_charge: Not used for image pricing (ignored)
            request_count: Number of requests (ignored for image pricing)

        Returns:
            Calculated cost based on image count
        """
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

    def calculate_cost(
        self,
        usage: UsageData,
        customer_charge: Decimal | None = None,
        request_count: int | None = None,
    ) -> Decimal:
        """Calculate cost for step-based pricing.

        Args:
            usage: Usage data with count
            customer_charge: Not used for step pricing (ignored)
            request_count: Number of requests (ignored for step pricing)

        Returns:
            Calculated cost based on step count
        """
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
    Price data for revenue share pricing (payout_price only).

    This pricing type is used exclusively for payout_price when the seller
    receives a percentage of what the customer pays. It cannot be used for
    list_price since the list price must be a concrete amount.

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

    def calculate_cost(
        self,
        usage: UsageData,
        customer_charge: Decimal | None = None,
        request_count: int | None = None,
    ) -> Decimal:
        """Calculate cost for revenue share pricing.

        Args:
            usage: Usage data (not used for revenue share, but kept for consistent API)
            customer_charge: Total amount charged to customer (required)
            request_count: Number of requests (ignored for revenue share)

        Returns:
            Seller's share of the customer charge

        Raises:
            ValueError: If customer_charge is not provided
        """
        if customer_charge is None:
            raise ValueError("Revenue share pricing requires 'customer_charge'")

        return customer_charge * Decimal(self.percentage) / Decimal("100")


class ConstantPriceData(BasePriceData):
    """
    Price data for a constant/fixed amount.

    Used for fixed fees, discounts, or adjustments that don't depend on usage.
    Amount can be positive (charge) or negative (discount/credit).
    """

    type: Literal["constant"] = "constant"

    amount: AmountStr = Field(
        description="Fixed amount (positive for charge, negative for discount)",
    )

    def calculate_cost(
        self,
        usage: UsageData,
        customer_charge: Decimal | None = None,
        request_count: int | None = None,
    ) -> Decimal:
        """Return the constant amount regardless of usage.

        Args:
            usage: Usage data (ignored for constant pricing)
            customer_charge: Customer charge (ignored for constant pricing)
            request_count: Number of requests (ignored for constant pricing)

        Returns:
            The fixed amount
        """
        return Decimal(self.amount)


# Forward reference for nested pricing - will be resolved after Pricing is defined
class AddPriceData(BasePriceData):
    """
    Composite pricing that sums multiple price components.

    Allows combining different pricing types, e.g., base token cost + fixed fee.

    Example:
        {
            "type": "add",
            "prices": [
                {"type": "one_million_tokens", "input": "0.50", "output": "1.50"},
                {"type": "constant", "amount": "-5.00", "description": "Platform fee"}
            ]
        }
    """

    type: Literal["add"] = "add"

    prices: list[dict[str, Any]] = Field(
        description="List of pricing components to sum together",
        min_length=1,
    )

    def calculate_cost(
        self,
        usage: UsageData,
        customer_charge: Decimal | None = None,
        request_count: int | None = None,
    ) -> Decimal:
        """Calculate total cost by summing all price components.

        Args:
            usage: Usage data passed to each component
            customer_charge: Customer charge passed to each component
            request_count: Number of requests passed to each component

        Returns:
            Sum of all component costs
        """
        total = Decimal("0")
        for price_data in self.prices:
            component = validate_pricing(price_data)
            total += component.calculate_cost(usage, customer_charge, request_count)
        return total


class MultiplyPriceData(BasePriceData):
    """
    Composite pricing that multiplies a base price by a factor.

    Useful for applying percentage-based adjustments to a base price.

    Example:
        {
            "type": "multiply",
            "factor": "0.70",
            "base": {"type": "one_million_tokens", "input": "0.50", "output": "1.50"}
        }
    """

    type: Literal["multiply"] = "multiply"

    factor: PriceStr = Field(
        description="Multiplication factor (e.g., '0.70' for 70%)",
    )

    base: dict[str, Any] = Field(
        description="Base pricing to multiply",
    )

    def calculate_cost(
        self,
        usage: UsageData,
        customer_charge: Decimal | None = None,
        request_count: int | None = None,
    ) -> Decimal:
        """Calculate cost by multiplying base price by factor.

        Args:
            usage: Usage data passed to base component
            customer_charge: Customer charge passed to base component
            request_count: Number of requests passed to base component

        Returns:
            Base cost multiplied by factor
        """
        base_pricing = validate_pricing(self.base)
        base_cost = base_pricing.calculate_cost(usage, customer_charge, request_count)
        return base_cost * Decimal(self.factor)


def _get_metric_value(
    based_on: str,
    usage: UsageData,
    customer_charge: Decimal | None,
    request_count: int | None,
) -> Decimal:
    """Get the value of a metric by name.

    Args:
        based_on: Name of the metric (e.g., 'request_count', 'customer_charge', or any UsageData field)
        usage: Usage data object
        customer_charge: Customer charge value
        request_count: Request count value

    Returns:
        The metric value as Decimal
    """
    # Check special parameters first
    if based_on == "request_count":
        return Decimal(request_count or 0)
    elif based_on == "customer_charge":
        return customer_charge or Decimal("0")

    # Try to get from UsageData fields
    if hasattr(usage, based_on):
        value = getattr(usage, based_on)
        if value is not None:
            return Decimal(str(value))

    # Build context with all available metrics
    context: dict[str, Decimal] = {
        "request_count": Decimal(request_count or 0),
        "customer_charge": customer_charge or Decimal("0"),
    }

    # Add all UsageData fields
    for field_name in UsageData.model_fields:
        value = getattr(usage, field_name)
        context[field_name] = Decimal(str(value)) if value is not None else Decimal("0")

    try:
        tree = ast.parse(based_on, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Invalid expression syntax: {based_on}") from e

    binary_ops: dict[type[ast.operator], Any] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }
    unary_ops: dict[type[ast.unaryop], Any] = {
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def safe_eval(node: ast.expr) -> Decimal:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, int | float):
                return Decimal(str(node.value))
            raise ValueError(f"Unsupported constant type: {type(node.value)}")
        elif isinstance(node, ast.Name):
            if node.id not in context:
                raise ValueError(f"Unknown metric: {node.id}")
            return context[node.id]
        elif isinstance(node, ast.BinOp):
            bin_op_type = type(node.op)
            if bin_op_type not in binary_ops:
                raise ValueError(f"Unsupported operator: {bin_op_type.__name__}")
            return binary_ops[bin_op_type](safe_eval(node.left), safe_eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            unary_op_type = type(node.op)
            if unary_op_type not in unary_ops:
                raise ValueError(f"Unsupported unary operator: {unary_op_type.__name__}")
            return unary_ops[unary_op_type](safe_eval(node.operand))
        else:
            raise ValueError(f"Unsupported expression type: {type(node).__name__}")

    return safe_eval(tree.body)


class ExprPriceData(BasePriceData):
    """
    Expression-based pricing that evaluates an arithmetic expression using usage metrics.

    **IMPORTANT: This pricing type should only be used for `payout_price`.**
    It is NOT suitable for `list_price` because:
    1. List pricing should be predictable and transparent
    2. Expression-based pricing can lead to confusing or unexpected charges
    3. Customers should be able to easily calculate their costs before using a service

    For payout pricing, expressions are useful when the cost from an upstream provider
    involves complex calculations that can't be expressed with basic pricing types.

    The expression can use any available metrics and arithmetic operators (+, -, *, /).

    Available metrics:
    - input_tokens, output_tokens, total_tokens (token counts)
    - seconds (time-based usage)
    - count (images, steps, etc.)
    - request_count (number of API requests)
    - customer_charge (what the customer paid, for revenue share calculations)

    Example:
        {
            "type": "expr",
            "expr": "input_tokens / 1000000 * 0.50 + output_tokens / 1000000 * 1.50"
        }
    """

    type: Literal["expr"] = "expr"

    expr: str = Field(
        description="Arithmetic expression using usage metrics (e.g., 'input_tokens / 1000000 * 2.5')",
    )

    def calculate_cost(
        self,
        usage: UsageData,
        customer_charge: Decimal | None = None,
        request_count: int | None = None,
    ) -> Decimal:
        """Calculate cost by evaluating the expression with usage data.

        Args:
            usage: Usage data providing metric values
            customer_charge: Customer charge value (available as 'customer_charge' in expression)
            request_count: Number of requests (available as 'request_count' in expression)

        Returns:
            The result of evaluating the expression
        """
        return _get_metric_value(self.expr, usage, customer_charge, request_count)


class PriceTier(BaseModel):
    """A single tier in tiered pricing."""

    model_config = ConfigDict(extra="forbid")

    up_to: int | None = Field(
        description="Upper limit for this tier (None for unlimited)",
    )
    price: dict[str, Any] = Field(
        description="Price configuration for this tier",
    )


class TieredPriceData(BasePriceData):
    """
    Volume-based tiered pricing where the tier determines price for ALL units.

    The tier is determined by the `based_on` metric, and ALL units are priced
    at that tier's rate. `based_on` can be 'request_count', 'customer_charge',
    or any field from UsageData (e.g., 'input_tokens', 'seconds', 'count').

    Example (volume pricing - all units at same rate):
        {
            "type": "tiered",
            "based_on": "request_count",
            "tiers": [
                {"up_to": 1000, "price": {"type": "constant", "amount": "10.00"}},
                {"up_to": 10000, "price": {"type": "constant", "amount": "80.00"}},
                {"up_to": null, "price": {"type": "constant", "amount": "500.00"}}
            ]
        }
    If request_count is 5000, the price is $80.00 (falls in 1001-10000 tier).
    """

    type: Literal["tiered"] = "tiered"

    based_on: str = Field(
        description="Metric for tier selection: 'request_count', 'customer_charge', or UsageData field",
    )

    tiers: list[PriceTier] = Field(
        description="List of tiers, ordered by up_to (ascending). Last tier should have up_to=null.",
        min_length=1,
    )

    def calculate_cost(
        self,
        usage: UsageData,
        customer_charge: Decimal | None = None,
        request_count: int | None = None,
    ) -> Decimal:
        """Calculate cost based on which tier the usage falls into.

        Args:
            usage: Usage data
            customer_charge: Customer charge (used if based_on="customer_charge")
            request_count: Number of requests (used if based_on="request_count")

        Returns:
            Cost from the matching tier's price
        """
        metric_value = _get_metric_value(self.based_on, usage, customer_charge, request_count)

        # Find the matching tier
        for tier in self.tiers:
            if tier.up_to is None or metric_value <= tier.up_to:
                tier_pricing = validate_pricing(tier.price)
                return tier_pricing.calculate_cost(usage, customer_charge, request_count)

        # Should not reach here if tiers are properly configured
        raise ValueError("No matching tier found")


class GraduatedTier(BaseModel):
    """A single tier in graduated pricing with per-unit price."""

    model_config = ConfigDict(extra="forbid")

    up_to: int | None = Field(
        description="Upper limit for this tier (None for unlimited)",
    )
    unit_price: PriceStr = Field(
        description="Price per unit in this tier",
    )


class GraduatedPriceData(BasePriceData):
    """
    Graduated tiered pricing where each tier's units are priced at that tier's rate.

    Like AWS pricing - first N units at price A, next M units at price B, etc.
    `based_on` can be 'request_count', 'customer_charge', or any UsageData field.

    Example (graduated pricing - different rates per tier):
        {
            "type": "graduated",
            "based_on": "request_count",
            "tiers": [
                {"up_to": 1000, "unit_price": "0.01"},
                {"up_to": 10000, "unit_price": "0.008"},
                {"up_to": null, "unit_price": "0.005"}
            ]
        }
    If request_count is 5000:
        - First 1000 at $0.01 = $10.00
        - Next 4000 at $0.008 = $32.00
        - Total = $42.00
    """

    type: Literal["graduated"] = "graduated"

    based_on: str = Field(
        description="Metric for graduated calc: 'request_count', 'customer_charge', or UsageData field",
    )

    tiers: list[GraduatedTier] = Field(
        description="List of tiers, ordered by up_to (ascending). Last tier should have up_to=null.",
        min_length=1,
    )

    def calculate_cost(
        self,
        usage: UsageData,
        customer_charge: Decimal | None = None,
        request_count: int | None = None,
    ) -> Decimal:
        """Calculate cost with graduated pricing across tiers.

        Args:
            usage: Usage data
            customer_charge: Customer charge (used if based_on="customer_charge")
            request_count: Number of requests (used if based_on="request_count")

        Returns:
            Total cost summed across all applicable tiers
        """
        metric_value = _get_metric_value(self.based_on, usage, customer_charge, request_count)
        total_cost = Decimal("0")
        remaining = metric_value
        previous_limit = Decimal("0")

        for tier in self.tiers:
            if remaining <= 0:
                break

            # Calculate units in this tier
            if tier.up_to is None:
                units_in_tier = remaining
            else:
                tier_size = Decimal(tier.up_to) - previous_limit
                units_in_tier = min(remaining, tier_size)

            # Add cost for this tier
            total_cost += units_in_tier * Decimal(tier.unit_price)
            remaining -= units_in_tier
            previous_limit = Decimal(tier.up_to) if tier.up_to else previous_limit

        return total_cost


# Discriminated union of all pricing types
# This is the type used for payout_price and list_price fields
# Note: ExprPriceData should only be used for payout_price
Pricing = Annotated[
    TokenPriceData
    | TimePriceData
    | ImagePriceData
    | StepPriceData
    | RevenueSharePriceData
    | ConstantPriceData
    | AddPriceData
    | MultiplyPriceData
    | TieredPriceData
    | GraduatedPriceData
    | ExprPriceData,
    Field(discriminator="type"),
]


def validate_pricing(
    data: dict[str, Any],
) -> (
    TokenPriceData
    | TimePriceData
    | ImagePriceData
    | StepPriceData
    | RevenueSharePriceData
    | ConstantPriceData
    | AddPriceData
    | MultiplyPriceData
    | TieredPriceData
    | GraduatedPriceData
    | ExprPriceData
):
    """
    Validate pricing dict and return the appropriate typed model.

    Args:
        data: Dictionary containing pricing data with 'type' field

    Returns:
        Validated Pricing model instance

    Raises:
        ValueError: If validation fails

    Example:
        >>> data = {"type": "one_million_tokens", "input": "0.5", "output": "1.5"}
        >>> validated = validate_pricing(data)
        >>> print(validated.input)  # "0.5"
    """
    from pydantic import TypeAdapter

    adapter: TypeAdapter[TokenPriceData | TimePriceData | ImagePriceData | StepPriceData | RevenueSharePriceData] = (
        TypeAdapter(Pricing)
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
    # rerank documents by relevance
    rerank = "rerank"
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


class OfferingStatusEnum(StrEnum):
    """
    Status values that sellers can set for service offerings.

    Seller-accessible statuses:
    - draft: Work in progress, skipped during publish
    - ready: Complete and ready for admin review
    - deprecated: Service is retired/end of life
    """

    draft = "draft"
    ready = "ready"
    deprecated = "deprecated"


# Backwards compatibility alias
UpstreamStatusEnum = OfferingStatusEnum


class ProviderStatusEnum(StrEnum):
    """
    Status values that sellers can set for providers.

    Seller-accessible statuses:
    - draft: Work in progress, skipped during publish
    - ready: Complete and ready for admin review
    - deprecated: Provider is retired/end of life
    """

    draft = "draft"
    ready = "ready"
    deprecated = "deprecated"


class DocumentData(BaseModel):
    """Document data for SDK/API payloads.

    Note: The document title is NOT stored here - it's the key in the documents dict.
    When stored in the database, the backend extracts the key as the title field.
    """

    model_config = ConfigDict(extra="forbid")

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


class AccessInterfaceData(BaseModel):
    """Access interface data for SDK/API payloads.

    Note: The interface name is NOT stored here - it's the key in the interfaces dict.
    When stored in the database, the backend extracts the key as the name field.
    """

    model_config = ConfigDict(extra="forbid")

    access_method: AccessMethodEnum = Field(default=AccessMethodEnum.http, description="Type of access method")

    base_url: str = Field(max_length=500, description="Base URL for api access")

    api_key: str | None = Field(default=None, max_length=2000, description="API key if required")

    description: str | None = Field(default=None, max_length=500, description="Interface description")

    request_transformer: dict[RequestTransformEnum, dict[str, Any]] | None = Field(
        default=None, description="Request transformation configuration"
    )

    routing_key: dict[str, Any] | None = Field(
        default=None,
        description="Request routing key for matching (e.g., {'model': 'gpt-4'})",
    )

    rate_limits: list[RateLimit] | None = Field(
        default=None,
        description="Rate limit",
    )
    constraints: ServiceConstraints | None = Field(default=None, description="Service constraints and conditions")
    is_active: bool = Field(default=True, description="Whether interface is active")
    is_primary: bool = Field(default=False, description="Whether this is the primary interface")
    sort_order: int = Field(default=0, description="Display order")


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
