# File Schemas

Complete reference for all data file schemas used in the UnitySVC Services SDK.

## Overview

All data files must include a `schema` field identifying their type and version. The SDK currently supports these schemas:

-   `provider_v1` - Provider metadata and upstream access configuration
-   `seller_v1` - Seller/marketplace information
-   `service_v1` - Service offering details (upstream provider perspective)
-   `listing_v1` - Service listing (user-facing marketplace perspective)

## Schema: provider_v1

Provider files define the service provider's metadata and access configuration for automated service population.

### Required Fields

| Field                  | Type                | Description                                                               |
| ---------------------- | ------------------- | ------------------------------------------------------------------------- |
| `schema`               | string              | Must be `"provider_v1"`                                                   |
| `name`                 | string              | Provider identifier (URL-friendly: lowercase, hyphens, underscores, dots) |
| `homepage`             | string (URL)        | Provider website URL                                                      |
| `contact_email`        | string (email)      | Contact email address                                                     |
| `provider_access_info` | AccessInterface     | Upstream access interface configuration                                   |
| `time_created`         | datetime (ISO 8601) | Timestamp when the provider was created                                   |

### Optional Fields

| Field                     | Type              | Description                                                            |
| ------------------------- | ----------------- | ---------------------------------------------------------------------- |
| `display_name`            | string            | Human-readable provider name (max 200 chars)                           |
| `description`             | string            | Provider description                                                   |
| `secondary_contact_email` | string (email)    | Secondary contact email                                                |
| `logo`                    | string/URL        | Path to logo file or URL (converted to document during import)         |
| `terms_of_service`        | string/URL        | Path to terms file or URL (converted to document during import)        |
| `documents`               | array of Document | Associated documents                                                   |
| `services_populator`      | object            | Automated service generation configuration                             |
| `status`                  | enum              | Provider status: `active` (default), `pending`, `disabled`, or `draft` |

### services_populator Object

| Field     | Type   | Description                                                 |
| --------- | ------ | ----------------------------------------------------------- |
| `command` | string | Script filename to execute (relative to provider directory) |

### provider_access_info (AccessInterface)

See [AccessInterface Object](#access-interface-object) below for complete field reference.

### Example (TOML)

```toml
schema = "provider_v1"
name = "openai"
display_name = "OpenAI"
description = "Leading AI research laboratory"
contact_email = "support@openai.com"
homepage = "https://openai.com"
time_created = "2024-01-15T10:00:00Z"
status = "active"

[services_populator]
command = "populate_services.py"

[provider_access_info]
access_method = "http"
base_url = "https://api.openai.com/v1"
api_key = "sk-YOUR-API-KEY"
```

### Example (JSON)

```json
{
    "schema": "provider_v1",
    "name": "openai",
    "display_name": "OpenAI",
    "description": "Leading AI research laboratory",
    "contact_email": "support@openai.com",
    "homepage": "https://openai.com",
    "time_created": "2024-01-15T10:00:00Z",
    "status": "active",
    "services_populator": {
        "command": "populate_services.py"
    },
    "provider_access_info": {
        "access_method": "http",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-YOUR-API-KEY"
    }
}
```

## Schema: seller_v1

Seller files define the marketplace or reseller information. **Only one seller file per repository.**

### Required Fields

| Field           | Type                | Description                                   |
| --------------- | ------------------- | --------------------------------------------- |
| `schema`        | string              | Must be `"seller_v1"`                         |
| `name`          | string              | Seller identifier (URL-friendly, 2-100 chars) |
| `contact_email` | string (email)      | Primary contact email                         |
| `time_created`  | datetime (ISO 8601) | Timestamp when seller was created             |

### Optional Fields

| Field                     | Type              | Description                                                                       |
| ------------------------- | ----------------- | --------------------------------------------------------------------------------- |
| `display_name`            | string            | Human-readable seller name (max 200 chars)                                        |
| `seller_type`             | enum              | Seller type: `individual` (default), `organization`, `partnership`, `corporation` |
| `description`             | string            | Seller description (max 1000 chars)                                               |
| `homepage`                | string (URL)      | Seller website URL                                                                |
| `secondary_contact_email` | string (email)    | Secondary contact email                                                           |
| `account_manager`         | string            | Email/username of account manager (max 100 chars)                                 |
| `business_registration`   | string            | Business registration number (max 100 chars)                                      |
| `tax_id`                  | string            | Tax ID (EIN, VAT, etc., max 100 chars)                                            |
| `stripe_connect_id`       | string            | Stripe Connect account ID (max 255 chars)                                         |
| `logo`                    | string/URL        | Path to logo file or URL (converted to document)                                  |
| `documents`               | array of Document | Associated documents (business registration, tax docs, etc.)                      |
| `status`                  | enum              | Seller status: `active` (default), `pending`, `disabled`, or `draft`              |
| `is_verified`             | boolean           | KYC/business verification status (default: false)                                 |

### Example (TOML)

```toml
schema = "seller_v1"
name = "acme-corp"
display_name = "ACME Corporation"
seller_type = "corporation"
description = "Premium AI services marketplace"
contact_email = "business@acme.com"
homepage = "https://acme.com"
time_created = "2024-01-10T12:00:00Z"
status = "active"
is_verified = true
```

## Schema: service_v1

Service files define the service offering from the upstream provider's perspective.

### Required Fields

| Field                       | Type                | Description                                                                  |
| --------------------------- | ------------------- | ---------------------------------------------------------------------------- |
| `schema`                    | string              | Must be `"service_v1"`                                                       |
| `name`                      | string              | Service identifier (must match directory name, allows slashes for hierarchy) |
| `display_name`              | string              | Human-readable service name                                                  |
| `description`               | string              | Service description                                                          |
| `service_type`              | enum                | Service category (see [ServiceTypeEnum values](#servicetype-enum-values))    |
| `details`                   | object              | Service-specific features and information                                    |
| `upstream_access_interface` | AccessInterface     | How to access the upstream service                                           |
| `time_created`              | datetime (ISO 8601) | Timestamp when service was created                                           |

### Optional Fields

| Field             | Type              | Description                                                     |
| ----------------- | ----------------- | --------------------------------------------------------------- |
| `version`         | string            | Service version                                                 |
| `logo`            | string/URL        | Path to logo or URL (converted to document)                     |
| `tagline`         | string            | Short elevator pitch                                            |
| `tags`            | array of enum     | Service tags (e.g., `["byop"]` for bring-your-own-provider)     |
| `upstream_status` | enum              | Service status: `uploading`, `ready` (default), or `deprecated` |
| `seller_price`    | [Pricing](pricing.md) | Seller pricing information (what seller charges UnitySVC)       |
| `documents`       | array of Document | Technical specs, documentation                                  |

### ServiceType Enum Values

-   `llm` - Large Language Model
-   `embedding` - Text embedding generation
-   `image_generation` - Image generation from prompts
-   `text_to_image` - Text to image conversion
-   `vision_language_model` - Image description/analysis
-   `speech_to_text` - Audio transcription
-   `text_to_speech` - Voice synthesis
-   `video_generation` - Video generation
-   `text_to_3d` - 3D model generation
-   `streaming_transcription` - Real-time audio transcription
-   `prerecorded_transcription` - Batch audio transcription
-   `prerecorded_translation` - Batch audio translation
-   `undetermined` - Type not yet determined

### Example (TOML)

```toml
schema = "service_v1"
name = "gpt-4"
display_name = "GPT-4"
description = "Most capable GPT-4 model for complex reasoning tasks"
service_type = "llm"
upstream_status = "ready"
version = "2024-01"
time_created = "2024-01-20T14:00:00Z"

[details]
context_window = 128000
max_output_tokens = 4096
supports_function_calling = true
supports_vision = true

[upstream_access_interface]
access_method = "http"
base_url = "https://api.openai.com/v1"

[seller_price]
currency = "USD"

[seller_price.price_data]
type = "one_million_tokens"
input = "30.00"
output = "60.00"
```

## Schema: listing_v1

Listing files define how a seller presents/sells a service to end users.

### Required Fields

| Field                    | Type                     | Description                        |
| ------------------------ | ------------------------ | ---------------------------------- |
| `schema`                 | string                   | Must be `"listing_v1"`             |
| `user_access_interfaces` | array of AccessInterface | How users access the service       |
| `time_created`           | datetime (ISO 8601)      | Timestamp when listing was created |

### Optional Fields

| Field                       | Type              | Description                                                                |
| --------------------------- | ----------------- | -------------------------------------------------------------------------- |
| `name`                      | string            | Listing identifier (defaults to filename without extension, max 255 chars) |
| `service_name`              | string            | Service identifier (required if multiple services in directory)            |
| `seller_name`               | string            | Seller identifier (references seller file)                                 |
| `display_name`              | string            | Customer-facing name (max 200 chars)                                       |
| `listing_status`            | enum              | Status: `draft` (skip publish), `ready` (ready for review), `deprecated`   |
| `customer_price`            | [Pricing](pricing.md) | Customer-facing pricing (what customer pays)                               |
| `documents`                 | array of Document | SLAs, documentation, guides                                                |
| `user_parameters_schema`    | object            | JSON schema for user configuration                                         |
| `user_parameters_ui_schema` | object            | UI schema for user configuration                                           |

### Listing Name Field

-   **Automatic naming**: If `name` is omitted, uses filename (without extension)
-   **Multiple listings**: Use descriptive filenames for different tiers/marketplaces
-   **Example**: `listing-premium.json` → `name = "listing-premium"`

### listing_status Values

-   `draft` - Work in progress, skipped during publish (default)
-   `ready` - Ready for admin review and testing
-   `deprecated` - No longer offered to new customers

### Example (TOML)

```toml
schema = "listing_v1"
name = "listing-premium"
seller_name = "acme-corp"
service_name = "gpt-4"
display_name = "GPT-4 Premium Access"
listing_status = "ready"
time_created = "2024-01-25T16:00:00Z"

[[user_access_interfaces]]
access_method = "http"
base_url = "${GATEWAY_BASE_URL}/p/openai"
name = "OpenAI API Access"

[user_access_interfaces.routing_key]
model = "gpt-4"

[customer_price]
currency = "USD"

[customer_price.price_data]
type = "one_million_tokens"
input = "35.00"
output = "70.00"

[[documents]]
title = "Quick Start Guide"
file_path = "../../docs/quick-start.md"
category = "getting_started"
mime_type = "markdown"
```

## Data Types

### Access Interface Object

The `AccessInterface` object defines how to access a service (used in providers, services, and listings).

| Field                 | Type               | Description                                                               |
| --------------------- | ------------------ | ------------------------------------------------------------------------- |
| `access_method`       | enum               | Access method: `http` (default), `websocket`, `grpc`                      |
| `base_url`            | string             | API endpoint URL (max 500 chars)                                          |
| `api_key`             | string             | API key if required (max 2000 chars)                                      |
| `name`                | string             | Interface name (max 100 chars)                                            |
| `description`         | string             | Interface description (max 500 chars)                                     |
| `request_transformer` | object             | Request transformation config (keys: `proxy_rewrite`, `body_transformer`) |
| `routing_key`         | object             | Optional routing key for request matching                                 |
| `rate_limits`         | array of RateLimit | Rate limiting rules                                                       |
| `constraint`          | ServiceConstraints | Service constraints                                                       |
| `documents`           | array of Document  | Interface documentation                                                   |
| `is_active`           | boolean            | Whether interface is active (default: true)                               |
| `is_primary`          | boolean            | Whether this is primary interface (default: false)                        |
| `sort_order`          | integer            | Display order (default: 0)                                                |

#### Routing Key

The `routing_key` field enables fine-grained request routing when multiple service listings share the same endpoint. The gateway extracts routing information from incoming requests and uses exact matching to find the correct service listing.

**How it works:**

-   Gateway extracts routing key from request body (currently the `model` field: `{"model": "value"}`)
-   Performs exact JSON equality match against `routing_key` in access interfaces
-   Only interfaces with matching `routing_key` handle the request
-   If `routing_key` is `null`, matches requests without a routing key

**Example use case:** Multiple GPT models on same endpoint:

```json
{
    "user_access_interfaces": [
        {
            "base_url": "${GATEWAY_BASE_URL}/p/openai",
            "routing_key": { "model": "gpt-4" }
        }
    ]
}
```

When a request arrives at `/p/openai` with `{"model": "gpt-4", "messages": [...]}`, the gateway extracts `{"model": "gpt-4"}` and routes to the matching listing.

### Pricing Object

Flexible pricing structure for both upstream (`seller_price`) and user-facing (`customer_price`) prices.

> **Full documentation:** See [Pricing Specification](pricing.md) for complete details on pricing types, validation rules, and examples.

| Field         | Type         | Description                                                               |
| ------------- | ------------ | ------------------------------------------------------------------------- |
| `currency`    | string       | ISO currency code (e.g., "USD", "EUR")                                    |
| `price_data`  | object       | Type-specific price structure (see [Pricing Types](pricing.md#price-data-types)) |
| `description` | string       | Pricing model description                                                 |
| `reference`   | string (URL) | Reference URL to upstream pricing page                                    |

**price_data types:**

| Type                  | Description                              | Example Fields                    |
| --------------------- | ---------------------------------------- | --------------------------------- |
| `one_million_tokens`  | Per million tokens (for LLMs)            | `price` or `input`/`output`       |
| `one_second`          | Per second of usage                      | `price`                           |
| `image`               | Per image generated                      | `price`                           |
| `step`                | Per step/iteration                       | `price`                           |
| `revenue_share`       | Percentage of customer charge (seller_price only) | `percentage`             |

**Quick examples:**

```json
// Unified token pricing
{"price_data": {"type": "one_million_tokens", "price": "2.50"}}

// Separate input/output pricing (LLM)
{"price_data": {"type": "one_million_tokens", "input": "10.00", "output": "30.00"}}

// Image generation pricing
{"price_data": {"type": "image", "price": "0.04"}}
```

> **Note:** Use string values for prices (e.g., `"2.50"`) to avoid floating-point precision issues.

See [Pricing Specification](pricing.md) for TOML examples, validation rules, and cost calculation details.

### Document Object

Documents associated with entities (providers, services, listings, access interfaces).

| Field          | Type    | Description                                                                                               |
| -------------- | ------- | --------------------------------------------------------------------------------------------------------- |
| `title`        | string  | Document title (5-255 chars)                                                                              |
| `mime_type`    | enum    | MIME type: `markdown`, `python`, `javascript`, `bash`, `html`, `text`, `pdf`, `jpeg`, `png`, `svg`, `url` |
| `category`     | enum    | Document category (see [DocumentCategory values](#documentcategory-enum-values))                          |
| `description`  | string  | Document description (max 500 chars)                                                                      |
| `version`      | string  | Document version (max 50 chars)                                                                           |
| `file_path`    | string  | Relative path to file (max 1000 chars, mutually exclusive with external_url)                              |
| `external_url` | string  | External URL (max 1000 chars, mutually exclusive with file_path)                                          |
| `meta`         | object  | Additional metadata                                                                                       |
| `sort_order`   | integer | Sort order within category (default: 0)                                                                   |
| `is_active`    | boolean | Whether document is active (default: true)                                                                |
| `is_public`    | boolean | Publicly accessible without auth (default: false)                                                         |

### DocumentCategory Enum Values

-   `getting_started` - Getting started guides
-   `api_reference` - API reference documentation
-   `tutorial` - Step-by-step tutorials
-   `code_example` - Code examples
-   `code_example_output` - Expected output from code examples
-   `use_case` - Use case descriptions
-   `troubleshooting` - Troubleshooting guides
-   `changelog` - Version changelogs
-   `best_practice` - Best practices
-   `specification` - Technical specifications
-   `service_level_agreement` - SLAs
-   `terms_of_service` - Terms of service
-   `invoice` - Invoices/receipts
-   `logo` - Logo images
-   `avatar` - Avatar images
-   `other` - Other documents

### RateLimit Object

Rate limiting rules for services.

| Field         | Type    | Description                                                                                   |
| ------------- | ------- | --------------------------------------------------------------------------------------------- |
| `limit`       | integer | Maximum allowed in time window                                                                |
| `unit`        | enum    | What is limited: `requests`, `tokens`, `input_tokens`, `output_tokens`, `bytes`, `concurrent` |
| `window`      | enum    | Time window: `second`, `minute`, `hour`, `day`, `month`                                       |
| `description` | string  | Human-readable description (max 255 chars)                                                    |
| `burst_limit` | integer | Short-term burst allowance                                                                    |
| `is_active`   | boolean | Whether limit is active (default: true)                                                       |

**Example:**

```json
{
    "limit": 10000,
    "unit": "requests",
    "window": "hour",
    "description": "10K requests per hour limit",
    "burst_limit": 1000
}
```

### ServiceConstraints Object

Comprehensive service constraints and policies. All fields are optional.

**Usage Quotas:**

-   `monthly_quota`, `daily_quota` - Usage quotas
-   `quota_unit` - Unit for quotas (RateLimitUnitEnum)
-   `quota_reset_cycle` - Reset cycle: `daily`, `weekly`, `monthly`, `yearly`
-   `overage_policy` - Policy when exceeded: `block`, `throttle`, `charge`, `queue`

**Authentication:**

-   `auth_methods` - Supported auth methods (array of AuthMethodEnum)
-   `ip_whitelist_required` - IP whitelisting required (boolean)
-   `tls_version_min` - Minimum TLS version (string)

**Request/Response:**

-   `max_request_size_bytes`, `max_response_size_bytes` - Size limits
-   `timeout_seconds` - Request timeout
-   `max_batch_size` - Max batch items

**Content:**

-   `content_filters` - Content filtering: `adult`, `violence`, `hate_speech`, `profanity`, `pii`
-   `input_languages`, `output_languages` - Supported languages (ISO 639-1)
-   `max_context_length` - Max context tokens
-   `region_restrictions` - Geographic restrictions (ISO country codes)

**Availability:**

-   `uptime_sla_percent` - Uptime SLA (e.g., 99.9)
-   `response_time_sla_ms` - Response time SLA
-   `maintenance_windows` - Scheduled maintenance

**Concurrency:**

-   `max_concurrent_requests` - Max concurrent requests
-   `connection_timeout_seconds` - Connection timeout
-   `max_connections_per_ip` - Max connections per IP

## Validation Rules

The SDK enforces these validation rules:

1. **Schema field required**: All files must have `schema` field
2. **Schema version**: Only supported schema versions allowed
3. **Required fields**: All required fields must be present
4. **Name format**: Names must be URL-friendly (lowercase, hyphens, underscores, dots)
    - Provider/Seller: No slashes allowed
    - Service/Listing: Slashes allowed for hierarchical names
5. **Time created**: Must be valid ISO 8601 datetime
6. **Email validation**: Email fields must be valid email addresses
7. **URL validation**: URL fields must be valid URLs
8. **File paths**: Document paths must be relative and exist
9. **Enum values**: Must use valid enum values
10. **Mutual exclusivity**: Some fields are mutually exclusive (e.g., `file_path` and `external_url` in documents)

## Format Support

Both JSON and TOML formats are supported for all schemas:

### JSON

-   Uses 2-space indentation
-   Keys sorted alphabetically
-   Files end with single newline

### TOML

-   Standard TOML syntax
-   Sections use `[header]` notation
-   Arrays of objects use `[[header]]` notation

The SDK preserves the original format when updating files.

## See Also

-   [Pricing Specification](pricing.md) - Complete pricing documentation
-   [Data Structure](data-structure.md) - File organization rules
-   [CLI Reference](cli-reference.md#validate) - Validation command
-   [Getting Started](getting-started.md) - Create your first files
