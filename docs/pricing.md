# Pricing Specification

This document describes the pricing structure used for `payout_price` (in service files) and `list_price` (in listing files).

## Overview

UnitySVC uses a two-tier pricing model:

- **Seller Price** (`payout_price` in `offering_v1`): The agreed rate between the seller and UnitySVC. This is what the seller charges UnitySVC for each unit of service usage.
- **Customer Price** (`list_price` in `listing_v1`): The price shown to customers on the marketplace. This is what the customer pays for each unit of service usage.

Both use the same `Pricing` structure, which supports multiple pricing types through a discriminated union based on the `type` field.

> **Important: Use String Values for Prices**
>
> All price values (`price`, `input`, `output`) should be specified as **strings** (e.g., `"0.50"`) rather than floating-point numbers. This avoids floating-point precision issues where values like `2.0` might become `1.9999999` when saved and loaded.

## Multi-Currency Support

Currency is specified at the **service/listing level**, not inside the pricing object:

- **Service** (ServiceOffering): Has ONE `payout_price` with ONE currency
- **Listing** (ServiceListing): Has ONE `list_price` with ONE currency
- **Multiple currencies**: Create multiple listings pointing to the same service

```
ServiceOffering (gpt-4-turbo)
├── payout_price (USD)

ServiceListing (gpt-4-turbo-usd)
├── currency: USD
└── list_price

ServiceListing (gpt-4-turbo-eur)
├── currency: EUR
└── list_price
```

### Currency Field Location

| Level           | Field      | Description                                     |
| --------------- | ---------- | ----------------------------------------------- |
| ServiceOffering | `currency` | Currency for payout_price                       |
| ServiceListing  | `currency` | Currency for list_price (indexed for filtering) |

## Pricing Object Structure

Acceptable fields of the Pricing object are based on the `type` field.

```
Pricing
├── type          (required) - Pricing type discriminator
├── description   (optional) - Human-readable pricing description
├── reference     (optional) - URL to upstream pricing page
└── [type-specific fields]
```

### Common Fields

| Field         | Type   | Required | Description                                     |
| ------------- | ------ | -------- | ----------------------------------------------- |
| `type`        | string | **Yes**  | Pricing type (discriminator)                    |
| `description` | string | No       | Human-readable description of the pricing model |
| `reference`   | string | No       | URL to upstream provider's pricing page         |

---

## Per-Request Pricing Types

These pricing types calculate cost based on usage data from a single API request. They are suitable for both `list_price` and `payout_price`.

**Available metrics for per-request pricing:**

| Metric          | Description                   | Source    |
| --------------- | ----------------------------- | --------- |
| `input_tokens`  | Number of input tokens        | UsageData |
| `output_tokens` | Number of output tokens       | UsageData |
| `total_tokens`  | Total tokens (input + output) | UsageData |
| `seconds`       | Duration in seconds           | UsageData |
| `count`         | Count (images, steps, etc.)   | UsageData |

### Token-Based Pricing (`one_million_tokens`)

For LLM and text-based services. Prices are per million tokens.

**Fields:**

| Field    | Type   | Required | Description                      |
| -------- | ------ | -------- | -------------------------------- |
| `type`   | string | **Yes**  | Must be `"one_million_tokens"`   |
| `price`  | string | \*       | Unified price per million tokens |
| `input`  | string | \*       | Price per million input tokens   |
| `output` | string | \*       | Price per million output tokens  |

**Validation Rules:**

- Must specify **either** `price` (unified) **or** both `input` and `output` (separate)
- Cannot specify both `price` and `input`/`output`
- All price values must be >= 0

**Example - Unified Pricing:**

```json
{
    "type": "one_million_tokens",
    "price": "2.50",
    "description": "Per million tokens"
}
```

**Example - Separate Input/Output Pricing:**

```json
{
    "type": "one_million_tokens",
    "input": "0.50",
    "output": "1.50",
    "description": "GPT-4 Turbo pricing"
}
```

**TOML Example:**

```toml
[list_price]
type = "one_million_tokens"
input = "12.00"
output = "36.00"
description = "Customer token pricing"
```

### Time-Based Pricing (`one_second`)

For audio/video processing, compute time, and other time-based services.

**Fields:**

| Field   | Type   | Required | Description               |
| ------- | ------ | -------- | ------------------------- |
| `type`  | string | **Yes**  | Must be `"one_second"`    |
| `price` | string | **Yes**  | Price per second of usage |

**Example:**

```json
{
    "type": "one_second",
    "price": "0.006",
    "description": "Audio transcription per second"
}
```

### Image Pricing (`image`)

For image generation, processing, and analysis services.

**Fields:**

| Field   | Type   | Required | Description       |
| ------- | ------ | -------- | ----------------- |
| `type`  | string | **Yes**  | Must be `"image"` |
| `price` | string | **Yes**  | Price per image   |

**Example:**

```json
{
    "type": "image",
    "price": "0.04",
    "description": "DALL-E 3 image generation"
}
```

### Step-Based Pricing (`step`)

For diffusion models, iterative processes, and other step-based services.

**Fields:**

| Field   | Type   | Required | Description              |
| ------- | ------ | -------- | ------------------------ |
| `type`  | string | **Yes**  | Must be `"step"`         |
| `price` | string | **Yes**  | Price per step/iteration |

**Example:**

```json
{
    "type": "step",
    "price": "0.001",
    "description": "Diffusion model steps"
}
```

### Constant Pricing (`constant`)

A fixed amount per request that doesn't depend on usage metrics.

> **Note:** When used for `list_price`, this amount is charged **per API request**. For example, `"amount": "0.01"` means the customer pays $0.01 for each request they make.

**Fields:**

| Field    | Type   | Required | Description                                               |
| -------- | ------ | -------- | --------------------------------------------------------- |
| `type`   | string | **Yes**  | Must be `"constant"`                                      |
| `amount` | string | **Yes**  | Fixed amount (positive for charge, negative for discount) |

**Example - Per-Request Fee:**

```json
{
    "type": "constant",
    "amount": "0.01",
    "description": "Per-request fee"
}
```

---

## Volume Pricing Types

These pricing types are designed for `payout_price` to handle volume-based billing over a billing period. They use aggregate metrics like `request_count` (total requests in billing period) or combine multiple pricing components.

> **Note:** While `add` and `multiply` can technically be used for `list_price` when wrapping per-request types, `tiered` and `graduated` with `based_on: "request_count"` are seller-only.

**Additional metrics available for volume pricing:**

| Metric          | Description                              | Availability |
| --------------- | ---------------------------------------- | ------------ |
| `request_count` | Number of API requests in billing period | Seller only  |

### Constant Pricing (`constant`) - Billing Period

When used in volume pricing contexts (e.g., inside `tiered` tiers or combined with `add`), `constant` represents a fixed amount for the billing period rather than per request.

**Example - Flat monthly fee based on tier:**

```json
{
    "type": "tiered",
    "based_on": "request_count",
    "tiers": [
        { "up_to": 1000, "price": { "type": "constant", "amount": "10.00" } },
        { "up_to": 10000, "price": { "type": "constant", "amount": "50.00" } },
        { "up_to": null, "price": { "type": "constant", "amount": "200.00" } }
    ],
    "description": "Flat monthly fee based on request volume"
}
```

### Add Pricing (`add`)

Combines multiple pricing components by summing them together. Useful for base price + fees, or combining different pricing models.

**Fields:**

| Field    | Type   | Required | Description                             |
| -------- | ------ | -------- | --------------------------------------- |
| `type`   | string | **Yes**  | Must be `"add"`                         |
| `prices` | array  | **Yes**  | List of pricing objects to sum together |

**Example - Token pricing with per-request fee:**

```json
{
    "type": "add",
    "prices": [
        { "type": "one_million_tokens", "input": "0.50", "output": "1.50" },
        {
            "type": "constant",
            "amount": "0.001",
            "description": "Per-request fee"
        }
    ]
}
```

**Example - Graduated pricing for both input and output tokens:**

```json
{
    "type": "add",
    "prices": [
        {
            "type": "graduated",
            "based_on": "input_tokens",
            "tiers": [
                { "up_to": 1000000, "unit_price": "0.000001" },
                { "up_to": null, "unit_price": "0.0000005" }
            ]
        },
        {
            "type": "graduated",
            "based_on": "output_tokens",
            "tiers": [
                { "up_to": 1000000, "unit_price": "0.000003" },
                { "up_to": null, "unit_price": "0.0000015" }
            ]
        }
    ],
    "description": "Graduated token pricing with separate input/output rates"
}
```

### Multiply Pricing (`multiply`)

Applies a multiplier to a base pricing model. Useful for percentage-based adjustments.

**Fields:**

| Field    | Type   | Required | Description                                  |
| -------- | ------ | -------- | -------------------------------------------- |
| `type`   | string | **Yes**  | Must be `"multiply"`                         |
| `factor` | string | **Yes**  | Multiplication factor (e.g., "0.70" for 70%) |
| `base`   | object | **Yes**  | Base pricing object to multiply              |

**Example - 70% of standard pricing:**

```json
{
    "type": "multiply",
    "factor": "0.70",
    "base": { "type": "one_million_tokens", "input": "1.00", "output": "2.00" },
    "description": "Partner discount (30% off)"
}
```

### Tiered Pricing (`tiered`)

Volume-based pricing where the tier determines the price for ALL usage. Once you cross a threshold, all units are priced at that tier's rate.

**Fields:**

| Field      | Type   | Required | Description                              |
| ---------- | ------ | -------- | ---------------------------------------- |
| `type`     | string | **Yes**  | Must be `"tiered"`                       |
| `based_on` | string | **Yes**  | Metric for tier selection                |
| `tiers`    | array  | **Yes**  | List of tier objects, ordered by `up_to` |

**Tier Object:**

| Field   | Type    | Required | Description                                      |
| ------- | ------- | -------- | ------------------------------------------------ |
| `up_to` | integer | **Yes**  | Upper limit for this tier (`null` for unlimited) |
| `price` | object  | **Yes**  | Pricing object for this tier                     |

**Example - Fixed price tiers based on request volume:**

```json
{
    "type": "tiered",
    "based_on": "request_count",
    "tiers": [
        { "up_to": 1000, "price": { "type": "constant", "amount": "10.00" } },
        { "up_to": 10000, "price": { "type": "constant", "amount": "80.00" } },
        { "up_to": null, "price": { "type": "constant", "amount": "500.00" } }
    ],
    "description": "Volume-based flat pricing"
}
```

**How it works:**

- 500 requests → Tier 1 → $10.00
- 5,000 requests → Tier 2 → $80.00
- 50,000 requests → Tier 3 → $500.00

**Example - Different token rates based on request volume:**

```json
{
    "type": "tiered",
    "based_on": "request_count",
    "tiers": [
        {
            "up_to": 1000,
            "price": {
                "type": "one_million_tokens",
                "input": "3.00",
                "output": "15.00"
            }
        },
        {
            "up_to": null,
            "price": {
                "type": "one_million_tokens",
                "input": "1.50",
                "output": "7.50"
            }
        }
    ],
    "description": "Volume discount on token pricing"
}
```

### Graduated Pricing (`graduated`)

AWS-style pricing where each tier's units are priced at that tier's rate. You always pay the higher rate for the first N units, regardless of total volume.

**Fields:**

| Field      | Type   | Required | Description                              |
| ---------- | ------ | -------- | ---------------------------------------- |
| `type`     | string | **Yes**  | Must be `"graduated"`                    |
| `based_on` | string | **Yes**  | Metric for tier calculation              |
| `tiers`    | array  | **Yes**  | List of tier objects, ordered by `up_to` |

**Graduated Tier Object:**

| Field        | Type    | Required | Description                                      |
| ------------ | ------- | -------- | ------------------------------------------------ |
| `up_to`      | integer | **Yes**  | Upper limit for this tier (`null` for unlimited) |
| `unit_price` | string  | **Yes**  | Price per unit in this tier                      |

**Example - Per-request graduated pricing:**

```json
{
    "type": "graduated",
    "based_on": "request_count",
    "tiers": [
        { "up_to": 1000, "unit_price": "0.01" },
        { "up_to": 10000, "unit_price": "0.008" },
        { "up_to": null, "unit_price": "0.005" }
    ],
    "description": "Graduated per-request pricing"
}
```

**How it works (5,000 requests):**

- First 1,000 × $0.01 = $10.00
- Next 4,000 × $0.008 = $32.00
- **Total = $42.00**

**Example - First 1 million requests free, then pay per request:**

```json
{
    "type": "graduated",
    "based_on": "request_count",
    "tiers": [
        { "up_to": 1000000, "unit_price": "0" },
        { "up_to": null, "unit_price": "0.00001" }
    ],
    "description": "First 1M requests free, then $0.00001 per request"
}
```

### Tiered vs Graduated: Key Difference

| Model         | 5,000 requests                    | Result     |
| ------------- | --------------------------------- | ---------- |
| **Tiered**    | All 5,000 at tier 2 rate ($0.008) | **$40.00** |
| **Graduated** | 1,000 × $0.01 + 4,000 × $0.008    | **$42.00** |

- **Tiered (Volume)**: Rewards high volume - once you reach a tier, ALL units get that rate
- **Graduated**: Each portion pays its tier's rate - first units always cost more

### Expression-Based `based_on`

Both `tiered` and `graduated` pricing support arithmetic expressions in the `based_on` field, enabling complex tier selection logic based on computed values rather than single metrics.

**Supported Operations:**

| Operation      | Example                              | Description                     |
| -------------- | ------------------------------------ | ------------------------------- |
| Addition       | `input_tokens + output_tokens`       | Sum of two metrics              |
| Subtraction    | `total_tokens - input_tokens`        | Difference between metrics      |
| Multiplication | `output_tokens * 4`                  | Metric multiplied by a factor   |
| Division       | `input_tokens / 1000`                | Metric divided by a factor      |
| Parentheses    | `(input_tokens + output_tokens) * 2` | Group operations for precedence |
| Unary minus    | `input_tokens - -100`                | Negation                        |

**Example - Weighted Token Pricing (output tokens cost 4x more):**

```json
{
    "type": "tiered",
    "based_on": "input_tokens + output_tokens * 4",
    "tiers": [
        { "up_to": 10000, "price": { "type": "constant", "amount": "1.00" } },
        { "up_to": null, "price": { "type": "constant", "amount": "10.00" } }
    ],
    "description": "Higher tier when weighted token usage exceeds 10k"
}
```

How it works:

- 5000 input + 1000 output → 5000 + 4000 = 9000 → Tier 1 ($1.00)
- 5000 input + 2000 output → 5000 + 8000 = 13000 → Tier 2 ($10.00)

**Example - Combine Request Count and Token Usage:**

```json
{
    "type": "tiered",
    "based_on": "request_count * 100 + input_tokens",
    "tiers": [
        { "up_to": 10000, "price": { "type": "constant", "amount": "1.00" } },
        { "up_to": null, "price": { "type": "constant", "amount": "5.00" } }
    ],
    "description": "Tier based on weighted combination of requests and tokens"
}
```

**Error Handling:**

Invalid expressions will raise errors at calculation time:

- **Invalid syntax**: `"input_tokens +"` → `Invalid expression syntax`
- **Unknown metric**: `"input_tokens + unknown_field"` → `Unknown metric: unknown_field`
- **Unsupported operator**: `"input_tokens ** 2"` → `Unsupported operator: Pow`

---

## Seller-Only Pricing Types

These pricing types use `customer_charge`, which is only available for `payout_price` calculations. This metric represents what the customer was charged and is used for revenue-sharing arrangements.

> **Important:** These pricing types should **only** be used for `payout_price`. Using them for `list_price` will result in errors or undefined behavior.

**Additional metrics available for seller pricing:**

| Metric            | Description                          | Availability |
| ----------------- | ------------------------------------ | ------------ |
| `customer_charge` | Total amount charged to the customer | Seller only  |

### Revenue Share Pricing (`revenue_share`)

For revenue-sharing arrangements where the seller receives a percentage of the customer charge.

**Fields:**

| Field        | Type   | Required | Description                                          |
| ------------ | ------ | -------- | ---------------------------------------------------- |
| `type`       | string | **Yes**  | Must be `"revenue_share"`                            |
| `percentage` | string | **Yes**  | Percentage of customer charge for the seller (0-100) |

**How it works:**

The `percentage` field represents the seller's share of whatever the customer pays. For example:

- If `percentage` is `"70"` and the customer pays $10, the seller receives $7
- If `percentage` is `"85.5"` and the customer pays $100, the seller receives $85.50

**Example:**

```json
{
    "type": "revenue_share",
    "percentage": "70.00",
    "description": "70% revenue share"
}
```

**TOML Example:**

```toml
[payout_price]
type = "revenue_share"
percentage = "70.00"
description = "70% revenue share"
```

**Use Cases:**

- Marketplace arrangements where sellers want a fixed percentage rather than per-unit pricing
- Reseller agreements with variable customer pricing
- Partner programs with revenue-sharing terms

### Expression Pricing (`expr`)

Expression-based pricing that evaluates an arbitrary arithmetic expression using usage metrics. This is useful when the upstream provider's pricing involves complex calculations that can't be expressed with basic pricing types.

**Fields:**

| Field  | Type   | Required | Description                               |
| ------ | ------ | -------- | ----------------------------------------- |
| `type` | string | **Yes**  | Must be `"expr"`                          |
| `expr` | string | **Yes**  | Arithmetic expression using usage metrics |

**Available Metrics:**

- `input_tokens`, `output_tokens`, `total_tokens` - Token counts
- `seconds` - Time-based usage
- `count` - Generic count (images, steps, etc.)
- `request_count` - Number of API requests (seller only)
- `customer_charge` - What the customer paid (seller only)

**Supported Operations:**

- Addition: `+`
- Subtraction: `-`
- Multiplication: `*`
- Division: `/`
- Parentheses: `(` `)`
- Numeric literals: `1000000`, `0.5`, etc.

**Example - Token Pricing with Different Rates:**

```json
{
    "type": "expr",
    "expr": "input_tokens / 1000000 * 0.50 + output_tokens / 1000000 * 1.50",
    "description": "Custom token pricing"
}
```

**Example - Complex Weighted Pricing:**

```json
{
    "type": "expr",
    "expr": "(input_tokens + output_tokens * 4) / 1000000 * 2.00",
    "description": "Output tokens weighted 4x"
}
```

**Example - Revenue Share as Expression:**

```json
{
    "type": "expr",
    "expr": "customer_charge * 0.70",
    "description": "70% revenue share"
}
```

**Example - Per-Request Fee:**

```json
{
    "type": "expr",
    "expr": "request_count * 0.001 + input_tokens / 1000000 * 0.50",
    "description": "Per-request fee plus token cost"
}
```

**TOML Example:**

```toml
[payout_price]
type = "expr"
expr = "input_tokens / 1000000 * 0.50 + output_tokens / 1000000 * 1.50"
description = "Custom token pricing for seller"
```

---

## Nested Composite Pricing

Composite pricing types can be nested for complex scenarios:

**Example - Graduated pricing with minimum fee:**

```json
{
    "type": "add",
    "prices": [
        {
            "type": "graduated",
            "based_on": "request_count",
            "tiers": [
                { "up_to": 1000, "unit_price": "0.01" },
                { "up_to": null, "unit_price": "0.005" }
            ]
        },
        {
            "type": "constant",
            "amount": "5.00",
            "description": "Minimum monthly fee"
        }
    ]
}
```

**Example - Tiered pricing with partner discount:**

```json
{
    "type": "multiply",
    "factor": "0.80",
    "base": {
        "type": "tiered",
        "based_on": "request_count",
        "tiers": [
            {
                "up_to": 10000,
                "price": {
                    "type": "one_million_tokens",
                    "input": "1.00",
                    "output": "2.00"
                }
            },
            {
                "up_to": null,
                "price": {
                    "type": "one_million_tokens",
                    "input": "0.50",
                    "output": "1.00"
                }
            }
        ]
    },
    "description": "Partner pricing (20% discount on tiered rates)"
}
```

---

## Complete Examples

### Service File with Seller Price (JSON)

```json
{
    "schema": "offering_v1",
    "name": "gpt-4-turbo",
    "display_name": "GPT-4 Turbo",
    "description": "OpenAI's most advanced model",
    "service_type": "llm",
    "currency": "USD",
    "time_created": "2024-01-15T10:00:00Z",
    "details": {
        "context_window": 128000,
        "max_output_tokens": 4096
    },
    "upstream_access_interfaces": {
        "OpenAI Chat API": {
            "access_method": "http",
            "base_url": "https://api.openai.com/v1/chat/completions"
        }
    },
    "payout_price": {
        "type": "one_million_tokens",
        "input": "10.00",
        "output": "30.00",
        "description": "OpenAI GPT-4 Turbo pricing",
        "reference": "https://openai.com/pricing"
    }
}
```

### Service File with Seller Price (TOML)

```toml
schema = "offering_v1"
name = "whisper-large"
display_name = "Whisper Large V3"
description = "Audio transcription model"
service_type = "audio_transcription"
currency = "USD"
time_created = "2024-01-15T10:00:00Z"

[upstream_access_interfaces."OpenAI Audio API"]
access_method = "http"
base_url = "https://api.openai.com/v1/audio/transcriptions"

[payout_price]
type = "one_second"
price = "0.006"
description = "Per second of audio"
reference = "https://openai.com/pricing"
```

### Listing File with Customer Price (TOML)

```toml
schema = "listing_v1"
name = "gpt-4-turbo-premium-usd"
service_name = "gpt-4-turbo"
display_name = "GPT-4 Turbo Premium Access"
status = "ready"
currency = "USD"
time_created = "2024-02-01T12:00:00Z"

[[user_access_interfaces]]
access_method = "http"
base_url = "${GATEWAY_BASE_URL}/v1/chat/completions"
name = "Chat Completions API"

[user_access_interfaces.routing_key]
model = "gpt-4-turbo"

[list_price]
type = "one_million_tokens"
input = "12.00"
output = "36.00"
description = "Premium access with priority support"
```

### Image Generation Service (JSON)

```json
{
    "schema": "offering_v1",
    "name": "flux-pro",
    "display_name": "FLUX Pro",
    "description": "High-quality image generation",
    "service_type": "image_generation",
    "currency": "USD",
    "time_created": "2024-03-15T10:30:00Z",
    "details": {
        "max_resolution": "2048x2048",
        "supported_formats": ["PNG", "JPEG", "WEBP"]
    },
    "upstream_access_interfaces": {
        "Image Generation API": {
            "access_method": "http",
            "base_url": "https://api.provider.com/v1/images/generate"
        }
    },
    "payout_price": {
        "type": "image",
        "price": "0.04",
        "description": "Per image pricing"
    }
}
```

---

## Pricing Type Selection Guide

### Per-Request Pricing Types (for `list_price` and `payout_price`)

| Service Type                | Recommended Pricing Type | Example Use Cases              |
| --------------------------- | ------------------------ | ------------------------------ |
| LLM, Chat, Completion       | `one_million_tokens`     | GPT-4, Claude, Llama           |
| Embedding                   | `one_million_tokens`     | text-embedding-ada-002         |
| Audio Transcription         | `one_second`             | Whisper, Deepgram              |
| Text-to-Speech              | `one_second`             | ElevenLabs, Azure TTS          |
| Video Processing            | `one_second`             | Video transcription, analysis  |
| Image Generation            | `image`                  | DALL-E, Stable Diffusion, FLUX |
| Image Analysis              | `image`                  | GPT-4 Vision (per image)       |
| Diffusion with Step Control | `step`                   | Custom diffusion pipelines     |
| Per-request fees/discounts  | `constant`               | Fixed fee per API request      |

### Volume Pricing Types (for `payout_price` - uses `request_count`)

| Use Case                | Recommended Type | Description                          |
| ----------------------- | ---------------- | ------------------------------------ |
| Flat billing period fee | `constant`       | Fixed amount per billing period      |
| Combined pricing        | `add`            | Sum of multiple pricing components   |
| Percentage adjustments  | `multiply`       | Apply discount/markup factor         |
| Request-based tiers     | `tiered`         | Tiers based on `request_count`       |
| Request-based graduated | `graduated`      | Graduated pricing by `request_count` |

### Seller-Only Pricing Types (for `payout_price` - uses `customer_charge`)

| Use Case            | Recommended Type | Description                      |
| ------------------- | ---------------- | -------------------------------- |
| Revenue sharing     | `revenue_share`  | Percentage of customer charge    |
| Complex expressions | `expr`           | Arbitrary arithmetic expressions |

---

## Validation

When you run `usvc data validate`, the pricing structure is validated:

1. **JSON Schema Validation**: Ensures the structure matches the expected format
2. **Pydantic Model Validation**: Enforces business rules:
    - `type` must be a valid pricing type
    - Token pricing requires either `price` OR both `input`/`output`
    - All price values must be non-negative (>= 0)
    - Extra fields are rejected

### Common Validation Errors

**Invalid: Both unified and separate pricing**

```json
{
    "type": "one_million_tokens",
    "price": "2.50",
    "input": "0.50",
    "output": "1.50"
}
```

Error: "Cannot specify both 'price' and 'input'/'output'"

**Invalid: Missing output price**

```json
{
    "type": "one_million_tokens",
    "input": "0.50"
}
```

Error: "Both 'input' and 'output' must be specified for separate pricing"

**Invalid: Unknown pricing type**

```json
{
    "type": "per_request",
    "price": "0.001"
}
```

Error: "Invalid pricing type. Valid types: 'one_million_tokens', 'one_second', 'image', 'step', 'revenue_share', 'constant', 'add', 'multiply', 'tiered', 'graduated', 'expr'"

---

## Cost Calculation

The backend calculates costs using these formulas:

### Per-Request Pricing Types

| Pricing Type                   | Cost Formula                                                            |
| ------------------------------ | ----------------------------------------------------------------------- |
| `one_million_tokens`           | (input_tokens × input_price + output_tokens × output_price) / 1,000,000 |
| `one_million_tokens` (unified) | total_tokens × price / 1,000,000                                        |
| `one_second`                   | seconds × price                                                         |
| `image`                        | count × price                                                           |
| `step`                         | count × price                                                           |
| `constant`                     | amount (fixed value per request)                                        |

### Volume Pricing Types

| Pricing Type | Cost Formula                                                       |
| ------------ | ------------------------------------------------------------------ |
| `constant`   | amount (fixed value per billing period)                            |
| `add`        | sum(price.calculate_cost() for each price in prices)               |
| `multiply`   | base.calculate_cost() × factor                                     |
| `tiered`     | Find tier where metric ≤ up_to, return tier.price.calculate_cost() |
| `graduated`  | Sum of (units_in_tier × unit_price) for each tier                  |

### Seller-Only Pricing Types

| Pricing Type    | Cost Formula                           |
| --------------- | -------------------------------------- |
| `revenue_share` | customer_charge × percentage / 100     |
| `expr`          | Evaluate expression with usage metrics |

---

## See Also

- [File Schemas](file-schemas.md) - Complete schema reference
- [Data Structure](data-structure.md) - File organization
- [CLI Reference](cli-reference.md#validate) - Validation command
