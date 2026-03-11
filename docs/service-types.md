# Service Types

This guide explains the different types of services you can define and route through the UnitySVC platform. Each type differs in **who provides the upstream credentials**, **whether customers need to enroll**, and **how the gateway resolves the upstream target**.

## Overview

| Type | Who pays the provider? | Enrollment required? | Customer action |
|------|----------------------|---------------------|-----------------|
| [Regular (managed)](#regular-managed-services) | Seller | No | None — use immediately |
| [Regular with parameters](#regular-services-with-user-parameters) | Seller | Yes | Enroll and configure parameters |
| [BYOK](#byok-services-bring-your-own-key) | Customer | No | Store API key as a secret |
| [BYOE](#byoe-services-bring-your-own-endpoint) | Customer (self-hosted) | Yes | Enroll with endpoint URL + optional secret |
| [Recurrent](#recurrent-services) | Any of the above | Yes | Enroll and configure schedule |

## Regular (Managed) Services

The simplest case: the seller provides static upstream credentials. The platform routes all customer requests to the same upstream endpoint using the seller's API key.

**Characteristics:**

- Seller pays the upstream provider
- All customers share the same upstream credentials
- No enrollment required — customers use the service immediately
- Seller's API key is stored in the seller's secret store

### Offering (upstream)

```toml
schema = "offering_v1"
name = "gpt-4"
display_name = "GPT-4"
service_type = "llm"
status = "ready"

[upstream_access_interfaces."OpenAI API"]
access_method = "http"
base_url = "https://api.openai.com/v1"
api_key = "${ secrets.OPENAI_API_KEY }"
```

The `${ secrets.OPENAI_API_KEY }` reference is resolved from the **seller's** secret store at routing time.

### Listing (customer-facing)

```toml
schema = "listing_v1"
status = "ready"
time_created = "2024-01-25T16:00:00Z"

[user_access_interfaces."OpenAI API Access"]
access_method = "http"
base_url = "${GATEWAY_BASE_URL}/p/openai"

[user_access_interfaces."OpenAI API Access".routing_key]
model = "gpt-4"
```

Note: `user_access_interfaces` has **no** `api_key` field — the customer authenticates with their SVCPASS API key. The gateway injects the seller's upstream credentials when forwarding.

### Request flow

```
Customer → SVCPASS API key → Gateway → seller's upstream credentials → Provider API
```

## Regular Services with User Parameters

Like managed services, but the customer must provide configuration (e.g., model preferences, region) during enrollment. The seller still provides the upstream credentials.

**Characteristics:**

- Seller pays the upstream provider
- Enrollment required because the customer must provide parameters
- Parameters are stored on the enrollment record
- Access interfaces can use Jinja2 templates with enrollment context

### Offering (upstream)

```toml
schema = "offering_v1"
name = "gpt-4-configurable"
display_name = "GPT-4 Configurable"
service_type = "llm"
status = "ready"

[upstream_access_interfaces."OpenAI API"]
access_method = "http"
base_url = "https://api.openai.com/v1"
api_key = "${ secrets.OPENAI_API_KEY }"
```

### Listing (customer-facing)

```toml
schema = "listing_v1"
status = "ready"
time_created = "2024-01-25T16:00:00Z"

[user_access_interfaces."OpenAI API Access"]
access_method = "http"
base_url = "${GATEWAY_BASE_URL}/p/openai"

[user_access_interfaces."OpenAI API Access".routing_key]
model = "gpt-4"
```

```json
{
    "user_parameters_schema": {
        "type": "object",
        "properties": {
            "max_tokens": {
                "type": "integer",
                "title": "Max Tokens",
                "default": 4096,
                "minimum": 1,
                "maximum": 128000
            },
            "temperature": {
                "type": "number",
                "title": "Temperature",
                "default": 0.7,
                "minimum": 0,
                "maximum": 2
            }
        }
    },
    "service_options": {
        "ops_testing_parameters": {
            "max_tokens": 4096,
            "temperature": 0.7
        }
    }
}
```

### Enrollment variables

When you need per-enrollment values in access interface URLs (e.g., unique topic codes), declare them in `enrollment_vars`:

```toml
[service_options.enrollment_vars]
topic = "{{ enrollment_code(6) }}"

[user_access_interfaces.gateway]
access_method = "http"
base_url = "${GATEWAY_BASE_URL}/ntfy/{{ topic }}"
```

The rendering happens in two phases:

1. **Phase 1** (enrollment creation): `enrollment_vars` are rendered — `{{ enrollment_code(6) }}` produces e.g. `VTXBNM`
2. **Phase 2** (access interface rendering): `{{ topic }}` resolves to `VTXBNM`

!!! warning "Enrollment-dependent expressions must go in enrollment_vars"
    Do **not** put `{{ enrollment_code() }}` or `{{ enrollment.id }}` directly in `base_url`. Always declare them in `enrollment_vars` first and reference the variable name in the URL. This makes enrollment dependencies explicit and detectable.

See [User Access Interface Templates](tech-notes/user-access-interface-template.md) for details on template syntax, `enrollment_code()`, and enrollment-scoped access interfaces.

## BYOK Services (Bring Your Own Key)

The customer provides their own API key for a cloud provider (e.g., OpenAI, Groq). The platform routes requests to the provider's API using the customer's key.

**Characteristics:**

- Customer pays the upstream provider directly
- **No enrollment required** — the secret is stored independently in the customer's secret store
- The seller defines the upstream endpoint; the customer supplies the API key
- At routing time, the gateway resolves the customer's secret and injects it into the upstream request

### Offering (upstream)

```toml
schema = "offering_v1"
name = "llama-3.3-70b-versatile"
display_name = "Llama 3.3 70B Versatile (BYOK)"
service_type = "llm"
tags = ["ai", "byok"]
status = "ready"

[upstream_access_interfaces."Groq API"]
access_method = "http"
base_url = "https://api.groq.com/openai/v1"
api_key = "${ customer_secrets.GROQ_API_KEY }"
```

The `${ customer_secrets.GROQ_API_KEY }` reference is resolved from the **customer's** secret store at routing time.

### Listing (customer-facing)

```toml
schema = "listing_v1"
status = "ready"
time_created = "2024-06-01T00:00:00Z"

[user_access_interfaces."Provider API"]
access_method = "http"
base_url = "${GATEWAY_BASE_URL}/p/groq"

[user_access_interfaces."Provider API".routing_key]
model = "llama-3.3-70b-versatile"
```

No `user_parameters_schema`, no `api_key` on `user_access_interfaces`. The listing is minimal.

### Secret ownership convention

The `${ ... }` pattern distinguishes who owns a secret:

| Pattern | Owner | Resolved from |
|---------|-------|---------------|
| `${ secrets.NAME }` | **Seller** | Seller's secret store |
| `${ customer_secrets.NAME }` | **Customer** | Customer's secret store |

Both patterns can appear in `upstream_access_interfaces`, `request_transformer`, and `service_options.ops_testing_parameters`. The `user_access_interfaces` never contains secret references — customers always authenticate to the gateway with their SVCPASS API key.

### Auto-detection

The platform auto-detects required customer secrets by scanning `upstream_access_interfaces` for `${ customer_secrets.XXX }` patterns. No separate declaration is needed. This enables:

- "Bring your own key" badge on the marketplace
- Display of required secrets with links to the customer's secrets UI
- Auto-routing to skip BYOK services where the customer hasn't stored the required secret

### Request flow

```
Customer → SVCPASS API key → Gateway → customer's secret from secret store → Provider API
```

If the customer hasn't stored the required secret, the platform returns a `401` error:
`"Missing required secret: GROQ_API_KEY. Please add it in your secrets settings."`

### Local testing

```bash
# Secret references resolve from environment variables during local tests
export GROQ_API_KEY="gsk_your_actual_key"
usvc data run-tests data/groq/services/llama-3.3-70b-versatile-byok
```

## BYOE Services (Bring Your Own Endpoint)

The customer provides the URL of their own service instance (e.g., self-hosted Ollama, vLLM). The platform routes requests to the customer's endpoint. Optionally, the customer also provides an API key for their endpoint.

**Characteristics:**

- Customer runs their own infrastructure
- **Enrollment required** — the endpoint URL is a real user parameter stored on the enrollment record
- The customer may also provide an API key via the secret store (using a secret-name parameter)
- Two-phase rendering: Jinja templates resolve enrollment parameters, then `${ ... }` patterns resolve secrets

### Offering (upstream)

```toml
schema = "offering_v1"
name = "llama3.3"
display_name = "Llama3.3 (BYOE)"
service_type = "llm"
tags = ["ai", "byoe"]
status = "ready"

[upstream_access_interfaces."Ollama API"]
access_method = "http"
base_url = "{{ base_url }}"
api_key = "${ customer_secrets.{{ api_key_secret }} }"
```

The `base_url` is a Jinja2 template referencing the enrollment parameter `base_url`. The `api_key` uses **double indirection**: the enrollment parameter `api_key_secret` provides the secret *name*, which is then resolved from the customer's secret store.

### Listing (customer-facing)

```toml
schema = "listing_v1"
status = "ready"
time_created = "2024-06-01T00:00:00Z"

[user_access_interfaces."Ollama API"]
access_method = "http"
base_url = "${GATEWAY_BASE_URL}/p/ollama/llama3.3"

[user_access_interfaces."Ollama API".routing_key]
model = "llama3.3"
```

```json
{
    "user_parameters_schema": {
        "type": "object",
        "title": "Ollama Endpoint Configuration",
        "required": ["base_url"],
        "properties": {
            "base_url": {
                "type": "string",
                "title": "Ollama Server URL",
                "default": "http://localhost:11434",
                "description": "Base URL of your Ollama server"
            },
            "api_key_secret": {
                "type": "string",
                "title": "API Key Secret",
                "default": "",
                "description": "Name of your stored secret containing the API key (leave empty if no auth needed)"
            }
        }
    },
    "user_parameters_ui_schema": {
        "base_url": {
            "ui:placeholder": "http://localhost:11434"
        },
        "api_key_secret": {
            "ui:widget": "secret-selector",
            "ui:description": "Select a secret from your secret store, or leave empty if your server requires no authentication"
        }
    },
    "service_options": {
        "ops_testing_parameters": {
            "base_url": "http://test-ollama-server:11434"
        }
    }
}
```

### How the two-phase resolution works

When a customer enrolls with `base_url = "http://my-server:11434"` and `api_key_secret = "MY_OLLAMA_KEY"`:

**Phase 1 — Jinja rendering** (at enrollment creation or routing time):

```
"base_url": "{{ base_url }}"                                → "http://my-server:11434"
"api_key": "${ customer_secrets.{{ api_key_secret }} }"      → "${ customer_secrets.MY_OLLAMA_KEY }"
```

**Phase 2 — Secret resolution** (at routing time):

```
"${ customer_secrets.MY_OLLAMA_KEY }" → actual key value from customer's secret store
```

If the customer left `api_key_secret` empty, the reference resolves to empty/null and no secret lookup occurs.

### Request flow

```
Customer → SVCPASS API key → Gateway
  → find enrollment → resolve {{ base_url }} from parameters
  → resolve ${ customer_secrets.MY_KEY } from secret store
  → forward to customer's endpoint with customer's credentials
```

### Local testing

```bash
# Provide the endpoint URL and optional secret as env vars
export OLLAMA_BASE_URL="http://localhost:11434"
export MY_OLLAMA_KEY="sk-..."
usvc data run-tests data/ollama/services/llama3.3-byoe
```

## Recurrent Services

Recurrent services run automatically on a schedule after a customer enrolls. Instead of manual API requests, the platform triggers requests through the gateway at scheduled intervals. **Recurrence is orthogonal to service type** — any of the above service types (managed, BYOK, BYOE) can be recurrent.

**Examples:**

- Uptime monitoring — check servers every 5 minutes
- Scheduled data sync — daily ETL job
- Periodic report generation — weekly summary

**Characteristics:**

- Enrollment is always required (the platform needs a per-enrollment schedule)
- Customers can still call the service manually at any time — the schedule is an *additional* trigger
- Billing, usage logging, and upstream routing work identically for scheduled and manual requests

### Seller configuration

Enable recurrence via `service_options`:

```toml
[service_options]
recurrence_enabled = true
recurrence_min_interval_seconds = 300    # minimum 5 minutes
recurrence_max_interval_seconds = 86400  # maximum 1 day
recurrence_allow_cron = true             # allow cron expressions
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `recurrence_enabled` | bool | `false` | Master switch for scheduled execution |
| `recurrence_min_interval_seconds` | int | `60` | Floor for customer-chosen interval |
| `recurrence_max_interval_seconds` | int | `604800` | Ceiling for customer-chosen interval (7 days) |
| `recurrence_allow_cron` | bool | `true` | Whether customers can use cron expressions |

### Customer schedule configuration

During enrollment, the customer sees the standard parameter form plus a **platform-level schedule section**:

```
[Service-specific parameters (from user_parameters_schema)]
─────────────────────────────────────────────────────────
[Schedule Configuration]
  ○ Every [___] minutes/hours/days
  ○ Cron: [___________]
  Timezone: [UTC ▾]
```

The schedule supports two modes:

- **Interval**: run every N seconds (must be within seller's min/max bounds)
- **Cron**: standard 5-field cron expression (if allowed by seller)

### Example: Uptime monitoring service (recurrent + managed)

```toml
# offering.toml
schema = "offering_v1"
name = "uptime-monitor"
display_name = "Uptime Monitor"
service_type = "monitoring"
status = "ready"

[upstream_access_interfaces."Monitor API"]
access_method = "http"
base_url = "https://monitor.example.com/api/v1"
api_key = "${ secrets.MONITOR_API_KEY }"
```

```toml
# listing.toml
schema = "listing_v1"
status = "ready"
time_created = "2024-06-01T00:00:00Z"

[user_access_interfaces."Monitor API"]
access_method = "http"
base_url = "${GATEWAY_BASE_URL}/p/monitor"

[service_options]
recurrence_enabled = true
recurrence_min_interval_seconds = 300
recurrence_max_interval_seconds = 86400
```

```json
{
    "user_parameters_schema": {
        "type": "object",
        "required": ["servers"],
        "properties": {
            "servers": {
                "type": "array",
                "title": "Server URLs to Monitor",
                "items": { "type": "string", "format": "uri" }
            },
            "check_type": {
                "type": "string",
                "title": "Check Type",
                "enum": ["http", "ping", "tcp"],
                "default": "http"
            }
        }
    },
    "service_options": {
        "recurrence_enabled": true,
        "recurrence_min_interval_seconds": 300,
        "recurrence_max_interval_seconds": 86400,
        "ops_testing_parameters": {
            "servers": ["https://example.com"],
            "check_type": "http"
        }
    }
}
```

### Combining recurrence with BYOK

A recurrent BYOK service (e.g., scheduled AI summarization using the customer's API key):

```toml
# offering.toml
[upstream_access_interfaces."Provider API"]
access_method = "http"
base_url = "https://api.openai.com/v1"
api_key = "${ customer_secrets.OPENAI_API_KEY }"
```

```toml
# listing.toml
[service_options]
recurrence_enabled = true
recurrence_min_interval_seconds = 3600
```

The customer stores their API key as a secret **and** enrolls to configure the schedule. Recurrence forces enrollment even though a BYOK service alone would not require it.

## Comparison Table

| Aspect | Regular (managed) | Regular + params | BYOK | BYOE | Recurrent |
|--------|-------------------|-----------------|------|------|-----------|
| **Who pays provider?** | Seller | Seller | Customer | Customer (self-hosted) | Depends on base type |
| **upstream api_key** | `${ secrets.X }` | `${ secrets.X }` | `${ customer_secrets.X }` | `${ customer_secrets.{{ param }} }` | Same as base type |
| **upstream base_url** | Static provider URL | Static provider URL | Static provider URL | `{{ base_url }}` (from enrollment) | Same as base type |
| **Enrollment required?** | No | Yes (parameters) | No | Yes (endpoint URL) | Yes (schedule) |
| **Customer provides** | Nothing | Parameters | API key (secret) | Endpoint URL + optional secret | Schedule + base type requirements |
| **user_access_interfaces api_key** | *(none — SVCPASS)* | *(none — SVCPASS)* | *(none — SVCPASS)* | *(none — SVCPASS)* | *(none — SVCPASS)* |

## What Determines Enrollment Requirement?

Enrollment is required when **any** of these conditions are true:

| Condition | Why enrollment is needed |
|-----------|------------------------|
| `user_parameters_schema` is non-empty | Customer must provide configuration stored on enrollment |
| `enrollment_vars` is non-empty | Per-enrollment URL templating (e.g., unique topic codes) |
| `recurrence_enabled` is true | Per-enrollment schedule |

Conditions that do **not** require enrollment:

| Condition | Why enrollment is not needed |
|-----------|----------------------------|
| `${ customer_secrets.X }` only (BYOK) | Stored in customer's secret store, resolved at routing time |
| `${ secrets.X }` (seller secrets) | Seller-level, resolved at routing time |
| Shared access interfaces | Same URL for all customers |
| Price rules | Evaluated from customer context, not enrollment |

## Service Groups

Services can be organized into [service groups](data-structure.md) for unified routing. A customer sends a request to a group path (e.g., `/g/llm/v1/chat/completions`), and the platform auto-routes to the best available service.

Groups can contain a mix of service types:

- **Regular services** — always available
- **BYOK services** — skipped if the customer hasn't stored the required secret
- **BYOE services** — skipped if the customer hasn't enrolled

This enables fallback patterns: route to the customer's own BYOK key first, fall back to a seller-managed service if the key is missing.
