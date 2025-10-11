# File Schemas

Complete reference for all data file schemas used in the UnitySVC Provider SDK.

## Overview

All data files must include a `schema` field identifying their type and version. The SDK currently supports these schemas:

- `provider_v1` - Provider metadata
- `seller_v1` - Seller/marketplace information
- `service_v1` - Service offering details
- `listing_v1` - Service listing (user-facing information)

## Schema: provider_v1

Provider files define the service provider's metadata and configuration.

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `schema` | string | Must be `"provider_v1"` |
| `name` | string | Provider identifier (normalized to lowercase-with-hyphens) |
| `display_name` | string | Human-readable provider name |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `description` | string | Provider description |
| `contact_email` | string | Contact email address |
| `website` | string | Provider website URL |
| `logo_url` | string | URL to provider logo |
| `services_populator` | object | Automated service generation configuration |
| `provider_access_info` | object | Environment variables for populate scripts |

### services_populator Object

| Field | Type | Description |
|-------|------|-------------|
| `command` | string | Script filename to execute (relative to provider directory) |

### provider_access_info Object

Key-value pairs that become environment variables when running the populate script.

### Example (TOML)

```toml
schema = "provider_v1"
name = "openai"
display_name = "OpenAI"
description = "Leading AI research laboratory"
contact_email = "support@openai.com"
website = "https://openai.com"

[services_populator]
command = "populate_services.py"

[provider_access_info]
API_KEY = "your-api-key"
API_ENDPOINT = "https://api.openai.com/v1"
```

### Example (JSON)

```json
{
  "schema": "provider_v1",
  "name": "openai",
  "display_name": "OpenAI",
  "description": "Leading AI research laboratory",
  "contact_email": "support@openai.com",
  "website": "https://openai.com",
  "services_populator": {
    "command": "populate_services.py"
  },
  "provider_access_info": {
    "API_KEY": "your-api-key",
    "API_ENDPOINT": "https://api.openai.com/v1"
  }
}
```

## Schema: seller_v1

Seller files define the marketplace or reseller information. **Only one seller file per repository.**

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `schema` | string | Must be `"seller_v1"` |
| `name` | string | Seller identifier (normalized to lowercase-with-hyphens) |
| `display_name` | string | Human-readable seller name |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `description` | string | Seller description |
| `business_name` | string | Legal business name |
| `contact_email` | string | Business contact email |
| `website` | string | Seller website URL |
| `logo_url` | string | URL to seller logo |
| `address` | object | Business address |
| `tax_id` | string | Tax identification number |

### Example (TOML)

```toml
schema = "seller_v1"
name = "svcreseller"
display_name = "SvcReseller"
description = "Premium AI services marketplace"
business_name = "SvcReseller Inc."
contact_email = "business@svcreseller.com"
website = "https://svcreseller.com"

[address]
street = "123 Market St"
city = "San Francisco"
state = "CA"
postal_code = "94105"
country = "USA"
```

## Schema: service_v1

Service files define the service offering (upstream/provider perspective).

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `schema` | string | Must be `"service_v1"` |
| `name` | string | Service identifier (must match directory name) |
| `display_name` | string | Human-readable service name |
| `description` | string | Service description |
| `service_type` | string | Service category (e.g., "llm", "api", "compute") |
| `upstream_status` | string | Service status (see Status Values) |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Service version |
| `pricing` | object | Pricing information |
| `access_interfaces` | array | API/access endpoints |
| `capabilities` | object | Service capabilities and limits |
| `metadata` | object | Additional metadata |

### upstream_status Values

- `uploading` - Service data being uploaded
- `ready` - Service is operational
- `deprecated` - Service being phased out

### Example (TOML)

```toml
schema = "service_v1"
name = "gpt-4"
display_name = "GPT-4"
description = "Most capable GPT-4 model"
service_type = "llm"
upstream_status = "ready"
version = "2024-01"

[pricing]
model = "pay-per-token"
input_price_per_1m = 30.00
output_price_per_1m = 60.00
currency = "USD"

[[access_interfaces]]
type = "openai-compatible"
endpoint = "https://api.openai.com/v1"
authentication = "bearer-token"

[capabilities]
context_window = 128000
max_output_tokens = 4096
supports_function_calling = true
supports_vision = true
```

## Schema: listing_v1

Listing files define how a seller presents/sells a service (downstream/marketplace perspective).

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `schema` | string | Must be `"listing_v1"` |
| `name` | string | Listing identifier (defaults to filename without extension if not provided) |
| `seller_name` | string | Seller identifier (references seller file) |
| `listing_status` | string | Listing status (see Status Values) |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `service_name` | string | Service identifier (required if multiple services in directory) |
| `user_facing_name` | string | Name shown to customers |
| `user_facing_description` | string | Description for customers |
| `pricing` | object | Downstream pricing |
| `user_access_interfaces` | array | User-facing access details |
| `documents` | array | Documentation files |
| `tags` | array | Search/filter tags |

### Listing Name Field

The `name` field identifies the listing and is especially important when multiple listings exist for a single service offering:

- **Automatic naming**: If the `name` field is not provided, the SDK automatically uses the filename (without extension) as the listing name
- **Multiple listings**: When you have multiple listings for one service (e.g., different tiers or marketplaces), use descriptive filenames
- **Example**: A file named `listing-premium.json` will automatically get `name = "listing-premium"` if the field is omitted
- **Best practice**: Use explicit `name` fields for clarity, or use descriptive filenames that will serve as meaningful listing identifiers

### listing_status Values

- `unknown` - Status not yet determined
- `upstream_ready` - Upstream service is ready
- `downstream_ready` - Downstream integration ready
- `ready` - Operationally ready for customers
- `in_service` - Currently serving customers
- `upstream_deprecated` - Upstream service deprecated
- `deprecated` - No longer offered to new customers

### Example (TOML)

```toml
schema = "listing_v1"
name = "listing-premium"
seller_name = "svcreseller"
service_name = "gpt-4"
listing_status = "in_service"
user_facing_name = "GPT-4 Advanced"
user_facing_description = "Most powerful AI model for complex tasks"

[pricing]
model = "pay-per-token"
input_price_per_1m = 35.00
output_price_per_1m = 70.00
currency = "USD"
markup_percentage = 16.67

[[user_access_interfaces]]
type = "api"
endpoint = "https://api.svcreseller.com/v1/gpt4"
documentation_url = "https://docs.svcreseller.com/gpt4"

[[documents]]
title = "Quick Start Guide"
file_path = "../../docs/quick-start.md"
category = "guides"

[[documents]]
title = "Python Code Examples"
file_path = "../../docs/code-example.py"
category = "code_examples"

[tags]
categories = ["ai", "language-model", "gpt"]
use_cases = ["chat", "completion", "analysis"]
```

## Data Types

### Pricing Object

Used in both service and listing schemas.

| Field | Type | Description |
|-------|------|-------------|
| `model` | string | Pricing model (e.g., "pay-per-token", "subscription", "pay-per-request") |
| `currency` | string | ISO currency code (e.g., "USD", "EUR") |
| `input_price_per_1m` | number | Input cost per 1M tokens/units |
| `output_price_per_1m` | number | Output cost per 1M tokens/units |
| `base_price` | number | Base/minimum price |
| `markup_percentage` | number | Markup percentage (listing only) |

### Access Interface Object

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Interface type (e.g., "openai-compatible", "rest-api", "grpc") |
| `endpoint` | string | API endpoint URL |
| `authentication` | string | Auth method (e.g., "bearer-token", "api-key", "oauth2") |
| `documentation_url` | string | API documentation URL |

### Document Object

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Document title |
| `file_path` | string | Relative path to file |
| `category` | string | Document category (e.g., "guides", "code_examples", "api_docs") |
| `format` | string | File format (e.g., "markdown", "pdf", "python") |

## Validation Rules

The SDK enforces these validation rules:

1. **Schema field required**: All files must have a `schema` field
2. **Schema version**: Only supported schema versions are allowed
3. **Required fields**: All required fields for the schema must be present
4. **Name normalization**: Directory names must match normalized field values
5. **Unique names**: Service names must be unique within provider
6. **Valid references**: Listing `seller_name` must reference existing seller
7. **File paths**: Document file paths must be relative and point to existing files
8. **Enum values**: Status fields must use valid enum values

## Format Support

Both JSON and TOML formats are supported for all schemas:

### JSON
- Uses 2-space indentation
- Keys are sorted alphabetically
- Files end with single newline

### TOML
- Uses standard TOML syntax
- Sections use `[header]` notation
- Arrays use `[[header]]` notation for array of tables

The SDK preserves the original format when updating files.

## See Also

- [Data Structure](data-structure.md) - File organization rules
- [CLI Reference](cli-reference.md#validate) - Validation command
- [Getting Started](getting-started.md) - Create your first files
