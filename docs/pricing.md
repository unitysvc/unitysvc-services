# Pricing Specification

This document describes the pricing structure used for `seller_price` (in service files) and `customer_price` (in listing files).

## Overview

UnitySVC uses a two-tier pricing model:

- **Seller Price** (`seller_price` in `service_v1`): The agreed rate between the seller and UnitySVC. This is what the seller charges UnitySVC for each unit of service usage.
- **Customer Price** (`customer_price` in `listing_v1`): The price shown to customers on the marketplace. This is what the customer pays for each unit of service usage.

Both use the same `Pricing` structure, which supports multiple pricing types through a discriminated union in the `price_data` field.

> **Important: Use String Values for Prices**
>
> All price values (`price`, `input`, `output`) should be specified as **strings** (e.g., `"0.50"`) rather than floating-point numbers. This avoids floating-point precision issues where values like `2.0` might become `1.9999999` when saved and loaded.

## Pricing Object Structure

```
Pricing
├── description   (optional) - Human-readable pricing description
├── currency      (optional) - ISO currency code (e.g., "USD", "EUR")
├── price_data    (required) - Type-specific pricing data (see below)
└── reference     (optional) - URL to upstream pricing page
```

### Fields

| Field         | Type   | Required | Description                                         |
| ------------- | ------ | -------- | --------------------------------------------------- |
| `description` | string | No       | Human-readable description of the pricing model     |
| `currency`    | string | No       | ISO 4217 currency code (e.g., "USD", "EUR", "GBP")  |
| `price_data`  | object | **Yes**  | Type-specific pricing structure (see below)         |
| `reference`   | string | No       | URL to upstream provider's pricing page             |

## Price Data Types

The `price_data` field uses a **discriminated union** based on the `type` field. Each pricing type has specific fields and validation rules.

### Token-Based Pricing (`one_million_tokens`)

For LLM and text-based services. Prices are per million tokens.

**Fields:**

| Field    | Type   | Required | Description                           |
| -------- | ------ | -------- | ------------------------------------- |
| `type`   | string | **Yes**  | Must be `"one_million_tokens"`        |
| `price`  | string | *        | Unified price per million tokens      |
| `input`  | string | *        | Price per million input tokens        |
| `output` | string | *        | Price per million output tokens       |

**Validation Rules:**

- Must specify **either** `price` (unified) **or** both `input` and `output` (separate)
- Cannot specify both `price` and `input`/`output`
- All price values must be >= 0

**Example - Unified Pricing:**

```json
{
  "price_data": {
    "type": "one_million_tokens",
    "price": "2.50"
  }
}
```

**Example - Separate Input/Output Pricing:**

```json
{
  "price_data": {
    "type": "one_million_tokens",
    "input": "0.50",
    "output": "1.50"
  }
}
```

**TOML Example - Separate Pricing:**

```toml
[seller_price]
currency = "USD"
description = "GPT-4 Turbo pricing"

[seller_price.price_data]
type = "one_million_tokens"
input = "10.00"
output = "30.00"
```

### Time-Based Pricing (`one_second`)

For audio/video processing, compute time, and other time-based services.

**Fields:**

| Field   | Type   | Required | Description                    |
| ------- | ------ | -------- | ------------------------------ |
| `type`  | string | **Yes**  | Must be `"one_second"`         |
| `price` | string | **Yes**  | Price per second of usage      |

**Example:**

```json
{
  "price_data": {
    "type": "one_second",
    "price": "0.006"
  }
}
```

**TOML Example:**

```toml
[seller_price]
currency = "USD"
description = "Audio transcription pricing"

[seller_price.price_data]
type = "one_second"
price = "0.006"
```

### Image Pricing (`image`)

For image generation, processing, and analysis services.

**Fields:**

| Field   | Type   | Required | Description              |
| ------- | ------ | -------- | ------------------------ |
| `type`  | string | **Yes**  | Must be `"image"`        |
| `price` | string | **Yes**  | Price per image          |

**Example:**

```json
{
  "price_data": {
    "type": "image",
    "price": "0.04"
  }
}
```

**TOML Example:**

```toml
[seller_price]
currency = "USD"
description = "DALL-E 3 image generation"

[seller_price.price_data]
type = "image"
price = "0.04"
```

### Step-Based Pricing (`step`)

For diffusion models, iterative processes, and other step-based services.

**Fields:**

| Field   | Type   | Required | Description                    |
| ------- | ------ | -------- | ------------------------------ |
| `type`  | string | **Yes**  | Must be `"step"`               |
| `price` | string | **Yes**  | Price per step/iteration       |

**Example:**

```json
{
  "price_data": {
    "type": "step",
    "price": "0.001"
  }
}
```

**TOML Example:**

```toml
[seller_price]
currency = "USD"
description = "Diffusion model steps"

[seller_price.price_data]
type = "step"
price = "0.001"
```

### Revenue Share Pricing (`revenue_share`) - Seller Only

For revenue-sharing arrangements where the seller receives a percentage of the customer charge.

> **Important:** This pricing type can **only** be used for `seller_price`. It cannot be used for `customer_price` since customer pricing must specify a concrete amount.

**Fields:**

| Field        | Type   | Required | Description                                           |
| ------------ | ------ | -------- | ----------------------------------------------------- |
| `type`       | string | **Yes**  | Must be `"revenue_share"`                             |
| `percentage` | string | **Yes**  | Percentage of customer charge for the seller (0-100)  |

**How it works:**

The `percentage` field represents the seller's share of whatever the customer pays. For example:
- If `percentage` is `"70"` and the customer pays $10, the seller receives $7
- If `percentage` is `"85.5"` and the customer pays $100, the seller receives $85.50

**Example:**

```json
{
  "price_data": {
    "type": "revenue_share",
    "percentage": "70.00"
  }
}
```

**TOML Example:**

```toml
[seller_price]
currency = "USD"
description = "70% revenue share"

[seller_price.price_data]
type = "revenue_share"
percentage = "70.00"
```

**Use Cases:**

- Marketplace arrangements where sellers want a fixed percentage rather than per-unit pricing
- Reseller agreements with variable customer pricing
- Partner programs with revenue-sharing terms

## Complete Examples

### Service File with Seller Price (JSON)

```json
{
  "schema": "service_v1",
  "name": "gpt-4-turbo",
  "display_name": "GPT-4 Turbo",
  "description": "OpenAI's most advanced model",
  "service_type": "llm",
  "time_created": "2024-01-15T10:00:00Z",
  "details": {
    "context_window": 128000,
    "max_output_tokens": 4096
  },
  "upstream_access_interface": {
    "access_method": "http",
    "base_url": "https://api.openai.com/v1/chat/completions"
  },
  "seller_price": {
    "currency": "USD",
    "description": "OpenAI GPT-4 Turbo pricing",
    "price_data": {
      "type": "one_million_tokens",
      "input": "10.00",
      "output": "30.00"
    },
    "reference": "https://openai.com/pricing"
  }
}
```

### Listing File with Customer Price (TOML)

```toml
schema = "listing_v1"
name = "gpt-4-turbo-premium"
service_name = "gpt-4-turbo"
display_name = "GPT-4 Turbo Premium Access"
listing_status = "ready"
time_created = "2024-02-01T12:00:00Z"

[[user_access_interfaces]]
access_method = "http"
base_url = "${GATEWAY_BASE_URL}/v1/chat/completions"
name = "Chat Completions API"

[user_access_interfaces.routing_key]
model = "gpt-4-turbo"

[customer_price]
currency = "USD"
description = "Premium access with priority support"

[customer_price.price_data]
type = "one_million_tokens"
input = "12.00"
output = "36.00"
```

### Image Generation Service (JSON)

```json
{
  "schema": "service_v1",
  "name": "flux-pro",
  "display_name": "FLUX Pro",
  "description": "High-quality image generation",
  "service_type": "image_generation",
  "time_created": "2024-03-15T10:30:00Z",
  "details": {
    "max_resolution": "2048x2048",
    "supported_formats": ["PNG", "JPEG", "WEBP"]
  },
  "upstream_access_interface": {
    "access_method": "http",
    "base_url": "https://api.provider.com/v1/images/generate"
  },
  "seller_price": {
    "currency": "USD",
    "description": "Per image pricing",
    "price_data": {
      "type": "image",
      "price": "0.04"
    }
  }
}
```

## Pricing Type Selection Guide

| Service Type                | Recommended Pricing Type | Example Use Cases                    |
| --------------------------- | ------------------------ | ------------------------------------ |
| LLM, Chat, Completion       | `one_million_tokens`     | GPT-4, Claude, Llama                 |
| Embedding                   | `one_million_tokens`     | text-embedding-ada-002               |
| Audio Transcription         | `one_second`             | Whisper, Deepgram                    |
| Text-to-Speech              | `one_second`             | ElevenLabs, Azure TTS                |
| Video Processing            | `one_second`             | Video transcription, analysis        |
| Image Generation            | `image`                  | DALL-E, Stable Diffusion, FLUX       |
| Image Analysis              | `image`                  | GPT-4 Vision (per image analyzed)    |
| Diffusion with Step Control | `step`                   | Custom diffusion pipelines           |
| Revenue Share (seller only) | `revenue_share`          | Marketplace partnerships, resellers  |

## Validation

When you run `usvc validate`, the pricing structure is validated:

1. **JSON Schema Validation**: Ensures the structure matches the expected format
2. **Pydantic Model Validation**: Enforces business rules:
   - `price_data.type` must be a valid pricing type
   - Token pricing requires either `price` OR both `input`/`output`
   - All price values must be non-negative (>= 0)
   - Extra fields in `price_data` are rejected

### Common Validation Errors

**Invalid: Both unified and separate pricing**
```json
{
  "price_data": {
    "type": "one_million_tokens",
    "price": 2.50,
    "input": 0.50,
    "output": 1.50
  }
}
```
Error: "Cannot specify both 'price' and 'input'/'output'"

**Invalid: Missing output price**
```json
{
  "price_data": {
    "type": "one_million_tokens",
    "input": 0.50
  }
}
```
Error: "Both 'input' and 'output' must be specified for separate pricing"

**Invalid: Unknown pricing type**
```json
{
  "price_data": {
    "type": "per_request",
    "price": 0.001
  }
}
```
Error: "Input should be 'one_million_tokens', 'one_second', 'image' or 'step'"

## Cost Calculation

The backend calculates costs using this formula:

| Pricing Type          | Cost Formula                                          |
| --------------------- | ----------------------------------------------------- |
| `one_million_tokens`  | (input_tokens × input_price + output_tokens × output_price) / 1,000,000 |
| `one_million_tokens` (unified) | total_tokens × price / 1,000,000             |
| `one_second`          | seconds × price                                       |
| `image`               | count × price                                         |
| `step`                | count × price                                         |

## See Also

- [File Schemas](file-schemas.md) - Complete schema reference
- [Data Structure](data-structure.md) - File organization
- [CLI Reference](cli-reference.md#validate) - Validation command
