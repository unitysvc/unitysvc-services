# File Schemas

Complete reference for all data file schemas used in the UnitySVC Services SDK.

## Overview

All data files must include a `schema` field identifying their type and version. The SDK currently supports these schemas:

- `provider_v1` - Provider metadata and upstream access configuration
- `seller_v1` - Seller/marketplace information
- `offering_v1` - Service offering details (upstream provider perspective)
- `listing_v1` - Service listing (user-facing marketplace perspective)

## Schema: provider_v1

Provider files define the service provider's metadata and access configuration for automated service population.

### Required Fields

| Field           | Type                | Description                                                               |
| --------------- | ------------------- | ------------------------------------------------------------------------- |
| `schema`        | string              | Must be `"provider_v1"`                                                   |
| `name`          | string              | Provider identifier (URL-friendly: lowercase, hyphens, underscores, dots) |
| `homepage`      | string (URL)        | Provider website URL                                                      |
| `contact_email` | string (email)      | Contact email address                                                     |
| `time_created`  | datetime (ISO 8601) | Timestamp when the provider was created                                   |

### Optional Fields

| Field                     | Type                 | Description                                                     |
| ------------------------- | -------------------- | --------------------------------------------------------------- |
| `display_name`            | string               | Human-readable provider name (max 200 chars)                    |
| `description`             | string               | Provider description                                            |
| `secondary_contact_email` | string (email)       | Secondary contact email                                         |
| `logo`                    | string/URL           | Path to logo file or URL (converted to document during import)  |
| `terms_of_service`        | string/URL           | Path to terms file or URL (converted to document during import) |
| `documents`               | dict of DocumentData | Documents keyed by title                                        |
| `services_populator`      | object               | Automated service generation configuration                      |
| `status`                  | enum                 | Provider status: `draft` (default), `ready`, or `deprecated`    |

### services_populator Object

Configuration for automatically populating service data using `usvc data populate`.

| Field          | Type                   | Description                                                                               |
| -------------- | ---------------------- | ----------------------------------------------------------------------------------------- |
| `command`      | string or list[string] | Command to execute (string or list of arguments). Relative to provider directory.         |
| `requirements` | array of strings       | Python packages to install before executing (e.g., `["httpx", "any-llm-sdk[anthropic]"]`) |
| `envs`         | object                 | Environment variables to set when executing the command (values converted to strings)     |

**Notes:**

- Comment out or omit `command` to disable population for a provider
- `requirements` packages are installed via pip before running the command
- `envs` values are converted to strings and set as environment variables

### Example (TOML)

```toml
schema = "provider_v1"
name = "openai"
display_name = "OpenAI"
description = "Leading AI research laboratory"
contact_email = "support@openai.com"
homepage = "https://openai.com"
time_created = "2024-01-15T10:00:00Z"
status = "ready"

[services_populator]
command = "populate_services.py"
requirements = ["httpx", "openai"]

[services_populator.envs]
API_KEY = "sk-YOUR-API-KEY"
BASE_URL = "https://api.openai.com/v1"
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
    "status": "ready",
    "services_populator": {
        "command": "populate_services.py",
        "requirements": ["httpx", "openai"],
        "envs": {
            "API_KEY": "sk-YOUR-API-KEY",
            "BASE_URL": "https://api.openai.com/v1"
        }
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

| Field                     | Type                 | Description                                                                       |
| ------------------------- | -------------------- | --------------------------------------------------------------------------------- |
| `display_name`            | string               | Human-readable seller name (max 200 chars)                                        |
| `seller_type`             | enum                 | Seller type: `individual` (default), `organization`, `partnership`, `corporation` |
| `description`             | string               | Seller description (max 1000 chars)                                               |
| `homepage`                | string (URL)         | Seller website URL                                                                |
| `secondary_contact_email` | string (email)       | Secondary contact email                                                           |
| `account_manager`         | string               | Email/username of account manager (max 100 chars)                                 |
| `business_registration`   | string               | Business registration number (max 100 chars)                                      |
| `tax_id`                  | string               | Tax ID (EIN, VAT, etc., max 100 chars)                                            |
| `stripe_connect_id`       | string               | Stripe Connect account ID (max 255 chars)                                         |
| `logo`                    | string/URL           | Path to logo file or URL (converted to document)                                  |
| `documents`               | dict of DocumentData | Documents keyed by title (business registration, tax docs, etc.)                  |
| `status`                  | enum                 | Seller status: `draft` (default), `ready`, or `deprecated`                        |
| `is_verified`             | boolean              | KYC/business verification status (default: false)                                 |

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
status = "ready"
is_verified = true
```

## Schema: offering_v1

Service files define the service offering from the upstream provider's perspective.

### Required Fields

| Field                        | Type                        | Description                                                                  |
| ---------------------------- | --------------------------- | ---------------------------------------------------------------------------- |
| `schema`                     | string                      | Must be `"offering_v1"`                                                      |
| `name`                       | string                      | Service identifier (must match directory name, allows slashes for hierarchy) |
| `service_type`               | enum                        | Service category (see [ServiceTypeEnum values](#servicetype-enum-values))    |
| `upstream_access_interfaces` | dict of AccessInterfaceData | How to access upstream services, keyed by interface name                     |
| `time_created`               | datetime (ISO 8601)         | Timestamp when offering was created                                          |

### Optional Fields

| Field          | Type                  | Description                                                   |
| -------------- | --------------------- | ------------------------------------------------------------- |
| `display_name` | string                | Human-readable service name for display (e.g., 'GPT-4 Turbo') |
| `description`  | string                | Service description                                           |
| `logo`         | string/URL            | Path to logo or URL (converted to document)                   |
| `tagline`      | string                | Short elevator pitch                                          |
| `tags`         | array of enum         | Service tags (e.g., `["byop"]` for bring-your-own-provider)   |
| `status`       | enum                  | Offering status: `draft` (default), `ready`, or `deprecated`  |
| `details`      | object                | Service-specific features and information                     |
| `payout_price` | [Pricing](pricing.md) | Seller pricing information (what seller charges UnitySVC)     |
| `documents`    | dict of DocumentData  | Technical specs, documentation, keyed by title                |

### ServiceType Enum Values

- `llm` - Large Language Model
- `embedding` - Text embedding generation
- `image_generation` - Image generation from prompts
- `text_to_image` - Text to image conversion
- `vision_language_model` - Image description/analysis
- `speech_to_text` - Audio transcription
- `text_to_speech` - Voice synthesis
- `video_generation` - Video generation
- `text_to_3d` - 3D model generation
- `streaming_transcription` - Real-time audio transcription
- `prerecorded_transcription` - Batch audio transcription
- `prerecorded_translation` - Batch audio translation
- `undetermined` - Type not yet determined

### Example (TOML)

```toml
schema = "offering_v1"
name = "gpt-4"
display_name = "GPT-4"
description = "Most capable GPT-4 model for complex reasoning tasks"
service_type = "llm"
status = "ready"
time_created = "2024-01-20T14:00:00Z"

[details]
context_window = 128000
max_output_tokens = 4096
supports_function_calling = true
supports_vision = true

[upstream_access_interfaces."OpenAI API"]
access_method = "http"
base_url = "https://api.openai.com/v1"

[payout_price]
currency = "USD"

[payout_price.price_data]
type = "one_million_tokens"
input = "30.00"
output = "60.00"
```

## Schema: listing_v1

Listing files define how a seller presents/sells a service to end users.

**Relationship by Location**: Listings automatically belong to the single offering in the same directory. The provider is determined by the parent directory structure. No explicit linking fields are needed.

### Required Fields

| Field                    | Type                        | Description                                 |
| ------------------------ | --------------------------- | ------------------------------------------- |
| `schema`                 | string                      | Must be `"listing_v1"`                      |
| `user_access_interfaces` | dict of AccessInterfaceData | How users access the service, keyed by name |
| `time_created`           | datetime (ISO 8601)         | Timestamp when listing was created          |

### Optional Fields

| Field                       | Type                  | Description                                                                                           |
| --------------------------- | --------------------- | ----------------------------------------------------------------------------------------------------- |
| `name`                      | string                | Listing identifier (defaults to filename without extension, max 255 chars)                            |
| `display_name`              | string                | Customer-facing name (max 200 chars)                                                                  |
| `status`                    | enum                  | Status: `draft` (skip upload), `ready` (ready for review), `deprecated`                               |
| `list_price`                | [Pricing](pricing.md) | Customer-facing pricing (what customer pays)                                                          |
| `documents`                 | dict of DocumentData  | SLAs, documentation, guides, keyed by title                                                           |
| `user_parameters_schema`    | object                | JSON schema defining user parameters for subscriptions (see [User Parameters](#user-parameters))      |
| `user_parameters_ui_schema` | object                | UI schema for user parameter form rendering (see [User Parameters](#user-parameters))     |
| `service_options`           | object                | Service-specific options (see [Service Options](#service-options))                       |

### Service Options

The `service_options` field configures backend behavior for service listings. All fields are optional.

| Field                            | Type    | Description                                                                                                    |
| -------------------------------- | ------- | -------------------------------------------------------------------------------------------------------------- |
| `ops_testing_parameters`         | object  | Default parameter values for testing (see [User Parameters](#user-parameters))                                 |
| `subscription_limit`             | integer | Maximum total active subscriptions allowed for this service (global limit)                                     |
| `subscription_limit_per_customer` | integer | Maximum active subscriptions per customer for this service                                                     |
| `subscription_limit_per_user`    | integer | Maximum active subscriptions per user (creator) for this service                                               |
| `subscription_code_name`         | string  | Parameter name for auto-generated subscription codes. If set, backend generates unique tokens for subscriptions |

**Subscription Limits:**

- Limits apply only to **active** subscriptions (cancelled/inactive subscriptions don't count)
- Invalid values (non-integers, zero, negative, or boolean) are treated as "no limit"
- Limits are checked when creating **new** subscriptions (not when updating existing ones)
- Checks are performed in order: per-customer → per-user → global

**Subscription Codes:**

When `subscription_code_name` is set (e.g., `"subscription_code"`), the backend automatically:
1. Generates a unique action code token for each new subscription
2. Adds the token to subscription parameters: `{subscription_code_name: "generated_token"}`
3. Skips this field when comparing parameters to determine if a subscription is an update

**Example (JSON):**

```json
{
  "service_options": {
    "ops_testing_parameters": {
      "api_key": "${ secrets.SERVICE_API_KEY }",
      "region": "us-east-1"
    },
    "subscription_limit": 100,
    "subscription_limit_per_customer": 5,
    "subscription_limit_per_user": 2,
    "subscription_code_name": "subscription_code"
  }
}
```

**Example (TOML):**

```toml
[service_options]
subscription_limit = 100
subscription_limit_per_customer = 5
subscription_limit_per_user = 2
subscription_code_name = "subscription_code"

[service_options.ops_testing_parameters]
api_key = "${ secrets.SERVICE_API_KEY }"
region = "us-east-1"
```

### Listing Name Field

- **Automatic naming**: If `name` is omitted, uses filename (without extension)
- **Multiple listings**: Use descriptive filenames for different tiers/marketplaces
- **Example**: `listing-premium.json` → `name = "listing-premium"`

### status Values (Listing)

- `draft` - Work in progress, skipped during upload (default)
- `ready` - Ready for admin review and testing
- `deprecated` - No longer offered to new customers

### Example (TOML)

```toml
# File: data/openai/services/gpt-4/listing-premium.toml
# This listing automatically belongs to the gpt-4 offering in the same directory
# and the openai provider in the parent directory.

schema = "listing_v1"
name = "listing-premium"
display_name = "GPT-4 Premium Access"
status = "ready"
time_created = "2024-01-25T16:00:00Z"

[user_access_interfaces."OpenAI API Access"]
access_method = "http"
base_url = "${GATEWAY_BASE_URL}/p/openai"

[user_access_interfaces."OpenAI API Access".routing_key]
model = "gpt-4"

[list_price]
currency = "USD"

[list_price.price_data]
type = "one_million_tokens"
input = "35.00"
output = "70.00"

[documents."Quick Start Guide"]
file_path = "../../docs/quick-start.md"
category = "getting_started"
mime_type = "markdown"
```

## User Parameters

User parameters allow services to collect configuration values from subscribers when they create subscriptions. These parameters are defined using JSON Schema and rendered as interactive forms using the react-jsonschema-form library.

### Overview

User parameters enable dynamic service configuration through:

1. **`user_parameters_schema`** - JSON Schema defining parameters, validation rules, and UI components
2. **`user_parameters_ui_schema`** - UI customization for form rendering
3. **`service_options.ops_testing_parameters`** - Default values for testing services before deployment (see [Service Options](#service-options))

### user_parameters_schema

Defines the parameters users must provide when subscribing to a service. Uses [JSON Schema](https://json-schema.org/) format with extensions from [react-jsonschema-form](https://rjsf-team.github.io/react-jsonschema-form/).

**Common properties:**

- `type` - Data type: `"string"`, `"number"`, `"boolean"`, `"object"`, `"array"`
- `title` - Human-readable field label
- `description` - Help text shown to users
- `default` - Default value for the field
- `enum` - List of allowed values (creates dropdown)
- `required` - Array of required field names

**Example:**

```json
{
    "type": "object",
    "title": "Service Configuration",
    "properties": {
        "api_key": {
            "type": "string",
            "title": "API Key",
            "description": "Your API key for authentication"
        },
        "model": {
            "type": "string",
            "title": "Model",
            "description": "Model to use",
            "enum": ["gpt-4", "gpt-3.5-turbo"],
            "default": "gpt-4"
        },
        "temperature": {
            "type": "number",
            "title": "Temperature",
            "description": "Sampling temperature (0-2)",
            "default": 0.7,
            "minimum": 0,
            "maximum": 2
        }
    },
    "required": ["api_key", "model"]
}
```

### user_parameters_ui_schema

Customizes how the form is rendered. Controls field order, visibility, widgets, and presentation.

**Common UI options:**

- `ui:widget` - Widget type: `"textarea"`, `"password"`, `"select"`, `"radio"`, `"checkbox"`
- `ui:placeholder` - Placeholder text
- `ui:help` - Additional help text
- `ui:disabled` - Disable field (e.g., for secrets managed separately)
- `ui:order` - Field display order

**Example:**

```json
{
    "api_key": {
        "ui:widget": "password",
        "ui:placeholder": "sk-...",
        "ui:disabled": true,
        "ui:help": "API key is managed through secrets. Add via the 'Add Secret' button."
    },
    "model": {
        "ui:widget": "select"
    },
    "temperature": {
        "ui:widget": "range"
    },
    "ui:order": ["model", "temperature", "api_key"]
}
```

### Handling Secrets

Sensitive values like API keys should be handled through the secrets management system, not collected directly through forms.

**Best practices for secrets:**

1. **Define in schema** - Include secret fields in `user_parameters_schema` for documentation
2. **Disable in UI** - Set `"ui:disabled": true` in `user_parameters_ui_schema`
3. **Add help text** - Guide users to add secrets separately
4. **Use secret references** - In `ops_testing_parameters`, reference secrets using `${ secrets.SECRET_NAME }`

**Example with API key secret:**

```json
// user_parameters_schema
{
  "type": "object",
  "properties": {
    "api_key": {
      "type": "string",
      "title": "API Key",
      "description": "Your service API key"
    }
  },
  "required": ["api_key"]
}

// user_parameters_ui_schema
{
  "api_key": {
    "ui:widget": "password",
    "ui:disabled": true,
    "ui:help": "Managed via secrets. Click 'Add Secret' to provide your API key."
  }
}
```

### service_options.ops_testing_parameters

Provides default parameter values for testing services before deployment. This is **required** when `user_parameters_schema` defines required parameters that don't have default values in the schema itself.

**Key requirements:**

1. **All required parameters must have defaults** - Each parameter listed in `user_parameters_schema.required` must have either a `default` value in the schema OR a value in `ops_testing_parameters`
2. **Secrets use special syntax** - Reference seller secrets using `${ secrets.SECRET_NAME }`
3. **Must be testable** - Values must allow the service to be tested successfully

**Example:**

```json
{
    "service_options": {
        "ops_testing_parameters": {
            "api_key": "${ secrets.OPENAI_API_KEY }",
            "model": "gpt-4",
            "temperature": 0.7
        }
    }
}
```

### Complete Example (JSON)

```json
{
    "schema": "listing_v1",
    "display_name": "Custom AI Service",
    "status": "ready",
    "time_created": "2024-01-25T16:00:00Z",
    "user_parameters_schema": {
        "type": "object",
        "title": "Service Configuration",
        "description": "Configure your AI service subscription",
        "properties": {
            "api_key": {
                "type": "string",
                "title": "API Key",
                "description": "Your service API key for authentication"
            },
            "model": {
                "type": "string",
                "title": "Model",
                "description": "AI model to use",
                "enum": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
                "default": "gpt-4"
            },
            "max_tokens": {
                "type": "integer",
                "title": "Max Tokens",
                "description": "Maximum tokens per request",
                "default": 1000,
                "minimum": 1,
                "maximum": 4096
            },
            "enable_streaming": {
                "type": "boolean",
                "title": "Enable Streaming",
                "description": "Enable streaming responses",
                "default": false
            }
        },
        "required": ["api_key", "model"]
    },
    "user_parameters_ui_schema": {
        "api_key": {
            "ui:widget": "password",
            "ui:disabled": true,
            "ui:help": "API key is managed through secrets. Use 'Add Secret' to provide your key."
        },
        "model": {
            "ui:widget": "select"
        },
        "max_tokens": {
            "ui:widget": "range",
            "ui:help": "Higher values allow longer responses but cost more"
        },
        "enable_streaming": {
            "ui:widget": "checkbox"
        },
        "ui:order": ["model", "max_tokens", "enable_streaming", "api_key"]
    },
    "service_options": {
        "ops_testing_parameters": {
            "api_key": "${ secrets.SERVICE_API_KEY }",
            "model": "gpt-4",
            "max_tokens": 1000,
            "enable_streaming": false
        }
    },
    "user_access_interfaces": {
        "API Access": {
            "access_method": "http",
            "base_url": "${GATEWAY_BASE_URL}/p/my-service"
        }
    }
}
```

### Complete Example (TOML)

```toml
schema = "listing_v1"
display_name = "Custom AI Service"
status = "ready"
time_created = "2024-01-25T16:00:00Z"

[user_parameters_schema]
type = "object"
title = "Service Configuration"
description = "Configure your AI service subscription"
required = ["api_key", "model"]

[user_parameters_schema.properties.api_key]
type = "string"
title = "API Key"
description = "Your service API key for authentication"

[user_parameters_schema.properties.model]
type = "string"
title = "Model"
description = "AI model to use"
default = "gpt-4"
enum = ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]

[user_parameters_schema.properties.max_tokens]
type = "integer"
title = "Max Tokens"
description = "Maximum tokens per request"
default = 1000
minimum = 1
maximum = 4096

[user_parameters_schema.properties.enable_streaming]
type = "boolean"
title = "Enable Streaming"
description = "Enable streaming responses"
default = false

[user_parameters_ui_schema.api_key]
"ui:widget" = "password"
"ui:disabled" = true
"ui:help" = "API key is managed through secrets. Use 'Add Secret' to provide your key."

[user_parameters_ui_schema.model]
"ui:widget" = "select"

[user_parameters_ui_schema.max_tokens]
"ui:widget" = "range"
"ui:help" = "Higher values allow longer responses but cost more"

[user_parameters_ui_schema.enable_streaming]
"ui:widget" = "checkbox"

[user_parameters_ui_schema]
"ui:order" = ["model", "max_tokens", "enable_streaming", "api_key"]

[service_options.ops_testing_parameters]
api_key = "${ secrets.SERVICE_API_KEY }"
model = "gpt-4"
max_tokens = 1000
enable_streaming = false

[user_access_interfaces."API Access"]
access_method = "http"
base_url = "${GATEWAY_BASE_URL}/p/my-service"
```

### Validation Rules

The SDK validates user parameters during the `usvc data validate` command:

1. **Required parameter defaults** - All parameters in `user_parameters_schema.required` must have either:
    - A `default` value in the parameter's schema definition, OR
    - A corresponding value in `service_options.ops_testing_parameters`
2. **Service options required** - If required parameters exist without defaults in the schema, `service_options` with `ops_testing_parameters` must be defined
3. **Complete coverage** - Every required parameter must have a testable default value from one of the two sources

**Valid scenarios:**

```json
// Scenario 1: All required params have defaults in schema (ops_testing_parameters not needed)
{
  "user_parameters_schema": {
    "properties": {
      "model": {"type": "string", "default": "gpt-4"}
    },
    "required": ["model"]
  }
}

// Scenario 2: Required params without defaults need ops_testing_parameters
{
  "user_parameters_schema": {
    "properties": {
      "api_key": {"type": "string"}
    },
    "required": ["api_key"]
  },
  "service_options": {
    "ops_testing_parameters": {
      "api_key": "${ secrets.API_KEY }"
    }
  }
}
```

**Validation errors:**

```
✗ Required parameters missing default values in service_options.ops_testing_parameters: ['api_key', 'model']
```

### Workflow

1. **Define schema** - Create `user_parameters_schema` with required and optional parameters
2. **Customize UI** - Create `user_parameters_ui_schema` for form customization
3. **Disable secrets** - Set `"ui:disabled": true` for sensitive fields
4. **Add testing defaults** - Create `service_options.ops_testing_parameters` with all required values
5. **Reference secrets** - Use `${ secrets.SECRET_NAME }` format for API keys
6. **Validate** - Run `usvc data validate` to check all required parameters have defaults
7. **Test** - Services are tested using the values in `ops_testing_parameters` before deployment

### Resources

- [react-jsonschema-form Documentation](https://rjsf-team.github.io/react-jsonschema-form/)
- [JSON Schema Specification](https://json-schema.org/)
- [JSON Schema Validation](https://json-schema.org/draft/2020-12/json-schema-validation.html)

## Data Types

### AccessInterfaceData Object

The `AccessInterfaceData` object defines how to access a service (used in offerings and listings). The interface name is the dict key, not a field in the object.

| Field                 | Type               | Description                                                               |
| --------------------- | ------------------ | ------------------------------------------------------------------------- |
| `access_method`       | enum               | Access method: `http` (default), `websocket`, `grpc`                      |
| `base_url`            | string             | API endpoint URL (max 500 chars)                                          |
| `api_key`             | string             | API key using secrets format: `${ secrets.VAR_NAME }` (see [Secrets](#secrets-for-sensitive-information)) |
| `description`         | string             | Interface description (max 500 chars)                                     |
| `request_transformer` | object             | Request transformation config (keys: `proxy_rewrite`, `body_transformer`) |
| `routing_key`         | object             | Optional routing key for request matching                                 |
| `rate_limits`         | array of RateLimit | Rate limiting rules                                                       |
| `constraints`         | ServiceConstraints | Service constraints                                                       |
| `is_active`           | boolean            | Whether interface is active (default: true)                               |
| `is_primary`          | boolean            | Whether this is primary interface (default: false)                        |
| `sort_order`          | integer            | Display order (default: 0)                                                |

**Note:** The interface name is specified as the dict key, not as a field within the object.

#### Routing Key

The `routing_key` field enables fine-grained request routing when multiple service listings share the same endpoint. The gateway extracts routing information from incoming requests and uses exact matching to find the correct service listing.

**How it works:**

- Gateway extracts routing key from request body (currently the `model` field: `{"model": "value"}`)
- Performs exact JSON equality match against `routing_key` in access interfaces
- Only interfaces with matching `routing_key` handle the request
- If `routing_key` is `null`, matches requests without a routing key

**Example use case:** Multiple GPT models on same endpoint:

```json
{
    "user_access_interfaces": {
        "GPT-4 API": {
            "base_url": "${GATEWAY_BASE_URL}/p/openai",
            "routing_key": { "model": "gpt-4" }
        }
    }
}
```

When a request arrives at `/p/openai` with `{"model": "gpt-4", "messages": [...]}`, the gateway extracts `{"model": "gpt-4"}` and routes to the matching listing.

### Pricing Object

Flexible pricing structure for both upstream (`payout_price`) and user-facing (`list_price`) prices.

> **Full documentation:** See [Pricing Specification](pricing.md) for complete details on pricing types, validation rules, and examples.

| Field         | Type         | Description                                                                      |
| ------------- | ------------ | -------------------------------------------------------------------------------- |
| `currency`    | string       | ISO currency code (e.g., "USD", "EUR")                                           |
| `price_data`  | object       | Type-specific price structure (see [Pricing Types](pricing.md#price-data-types)) |
| `description` | string       | Pricing model description                                                        |
| `reference`   | string (URL) | Reference URL to upstream pricing page                                           |

**price_data types:**

| Type                 | Description                                       | Example Fields              |
| -------------------- | ------------------------------------------------- | --------------------------- |
| `one_million_tokens` | Per million tokens (for LLMs)                     | `price` or `input`/`output` |
| `one_second`         | Per second of usage                               | `price`                     |
| `image`              | Per image generated                               | `price`                     |
| `step`               | Per step/iteration                                | `price`                     |
| `revenue_share`      | Percentage of customer charge (payout_price only) | `percentage`                |

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

### DocumentData Object

Documents associated with entities (providers, offerings, listings). The document title is the dict key, not a field in the object.

| Field          | Type    | Description                                                                                               |
| -------------- | ------- | --------------------------------------------------------------------------------------------------------- |
| `mime_type`    | enum    | MIME type: `markdown`, `python`, `javascript`, `bash`, `html`, `text`, `pdf`, `jpeg`, `png`, `svg`, `url` |
| `category`     | enum    | Document category (see [DocumentCategory values](#documentcategory-enum-values))                          |
| `description`  | string  | Document description (max 500 chars)                                                                      |
| `version`      | string  | Document version (max 50 chars)                                                                           |
| `file_path`    | string  | Relative path to file (max 1000 chars, mutually exclusive with external_url)                              |
| `external_url` | string  | External URL (max 1000 chars, mutually exclusive with file_path)                                          |
| `meta`         | object  | Additional metadata (e.g., test results, requirements)                                                    |
| `sort_order`   | integer | Sort order within category (default: 0)                                                                   |
| `is_active`    | boolean | Whether document is active (default: true)                                                                |
| `is_public`    | boolean | Publicly accessible without auth (default: false)                                                         |

**Note:** The document title is specified as the dict key (5-255 chars), not as a field within the object.

### DocumentCategory Enum Values

- `getting_started` - Getting started guides
- `api_reference` - API reference documentation
- `tutorial` - Step-by-step tutorials
- `code_example` - Code examples (visible to users)
- `code_example_output` - Expected output from code examples
- `connectivity_test` - Connectivity and performance tests (not visible to users, `is_public: false`)
- `use_case` - Use case descriptions
- `troubleshooting` - Troubleshooting guides
- `changelog` - Version changelogs
- `best_practice` - Best practices
- `specification` - Technical specifications
- `service_level_agreement` - SLAs
- `terms_of_service` - Terms of service
- `invoice` - Invoices/receipts
- `logo` - Logo images
- `avatar` - Avatar images
- `other` - Other documents

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

- `monthly_quota`, `daily_quota` - Usage quotas
- `quota_unit` - Unit for quotas (RateLimitUnitEnum)
- `quota_reset_cycle` - Reset cycle: `daily`, `weekly`, `monthly`, `yearly`
- `overage_policy` - Policy when exceeded: `block`, `throttle`, `charge`, `queue`

**Authentication:**

- `auth_methods` - Supported auth methods (array of AuthMethodEnum)
- `ip_whitelist_required` - IP whitelisting required (boolean)
- `tls_version_min` - Minimum TLS version (string)

**Request/Response:**

- `max_request_size_bytes`, `max_response_size_bytes` - Size limits
- `timeout_seconds` - Request timeout
- `max_batch_size` - Max batch items

**Content:**

- `content_filters` - Content filtering: `adult`, `violence`, `hate_speech`, `profanity`, `pii`
- `input_languages`, `output_languages` - Supported languages (ISO 639-1)
- `max_context_length` - Max context tokens
- `region_restrictions` - Geographic restrictions (ISO country codes)

**Availability:**

- `uptime_sla_percent` - Uptime SLA (e.g., 99.9)
- `response_time_sla_ms` - Response time SLA
- `maintenance_windows` - Scheduled maintenance

**Concurrency:**

- `max_concurrent_requests` - Max concurrent requests
- `connection_timeout_seconds` - Connection timeout
- `max_connections_per_ip` - Max connections per IP

## Secrets for Sensitive Information

API keys and other sensitive credentials must **never** be stored as plain text in data files. Instead, use the secrets reference format to specify credentials that will be securely retrieved at runtime.

### Creating Secrets

Before referencing secrets in your data files, you must create them in the UnitySVC platform:

1. Log in to the UnitySVC website
2. Navigate to **Seller Dashboard** → **Secrets**
3. Click **Create Secret**
4. Enter a name (e.g., `OPENAI_API_KEY`) and the secret value
5. Save the secret

Secret names must:
- Start with a letter or underscore
- Contain only letters, numbers, and underscores
- Be unique within your seller account

### Referencing Secrets in Data Files

Use the `${ secrets.VAR_NAME }` format to reference secrets. Spaces around the variable name are optional.

**Valid formats:**
```
${ secrets.OPENAI_API_KEY }
${secrets.OPENAI_API_KEY}
${ secrets.MY_PROVIDER_KEY }
```

### API Key Fields

The following fields require secrets references (plain text API keys are not allowed):

- `upstream_access_interfaces.<name>.api_key` - API keys for upstream provider access
- `user_access_interfaces.<name>.api_key` - API keys for user-facing interfaces
- `service_options.ops_testing_parameters.api_key` - Ops testing API key parameters

### Example Usage

**TOML:**
```toml
[upstream_access_interfaces."OpenAI API"]
access_method = "http"
base_url = "https://api.openai.com/v1"
api_key = "${ secrets.OPENAI_API_KEY }"
```

**JSON:**
```json
{
    "upstream_access_interfaces": {
        "OpenAI API": {
            "access_method": "http",
            "base_url": "https://api.openai.com/v1",
            "api_key": "${ secrets.OPENAI_API_KEY }"
        }
    }
}
```

### How Secrets Work

1. **Upload**: When you upload data files, the `${ secrets.VAR_NAME }` references are validated for correct format and the secret's existence is verified by the backend
2. **Storage**: The reference string is stored as-is in the database (secrets are NOT expanded during upload)
3. **Runtime**: When the API key is actually needed, the platform retrieves the decrypted value from the secure secrets storage

This approach ensures that:
- Sensitive credentials are never exposed in version-controlled files
- Secrets can be rotated without re-uploading data files
- Access to secrets is controlled through the seller dashboard

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

- Uses 2-space indentation
- Keys sorted alphabetically
- Files end with single newline

### TOML

- Standard TOML syntax
- Sections use `[header]` notation
- Arrays of objects use `[[header]]` notation

The SDK preserves the original format when updating files.

## See Also

- [Service Options](#service-options) - Configure subscription limits and backend behavior
- [User Parameters](#user-parameters) - Define and collect subscription configuration
- [Pricing Specification](pricing.md) - Complete pricing documentation
- [Data Structure](data-structure.md) - File organization rules
- [CLI Reference](cli-reference.md#validate) - Validation command
- [Getting Started](getting-started.md) - Create your first files
