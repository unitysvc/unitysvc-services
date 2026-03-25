# Service Types

UnitySVC is a multi-protocol service marketplace. Sellers list services, and the platform handles discovery, authentication, routing, metering, and billing. This guide covers what types of services the platform supports and how they are delivered.

## Service Categories

The platform supports services across multiple protocols and use cases:

| Category | Protocol | Gateway | Examples |
|----------|----------|---------|----------|
| **AI / ML** | HTTP | API Gateway | Chat APIs, embeddings, image generation, transcription, translation |
| **Email delivery** | SMTP | SMTP Gateway | Transactional email, bulk email, email verification |
| **Content / media** | HTTP or S3 | API Gateway or S3 Gateway | Stock media, datasets, video courses, software distribution |
| **Compute environments** | SSH / WireGuard | SSH Gateway | GPU instances, licensed software, dev environments |
| **Database access** | SSH tunnel | SSH Gateway | Managed Postgres, Redis, Elasticsearch |
| **Monitoring** | HTTP (platform-triggered) | API Gateway | Uptime checks, SSL monitoring, DNS monitoring |
| **Scheduled tasks** | HTTP (platform-triggered) | API Gateway | Cron-as-a-service, data collection, report generation |
| **Webhook relay** | HTTP | API Gateway | Webhook buffering, retry, fan-out, transformation |
| **Notifications** | HTTP | API Gateway | Push notifications, alerting |

### AI and machine learning

Language models, embeddings, image generators, speech-to-text, and more. Customers access them through a unified HTTP API with the same API key. The platform supports intelligent routing across providers and automatic failover.

**Service types**: `llm`, `embedding`, `rerank`, `image_generation`, `speech_to_text`, `text_to_speech`, `video_generation`, `text_to_image`, `vision_language_model`, `streaming_transcription`, `prerecorded_transcription`, `prerecorded_translation`, `text_to_3d`

### Email delivery

Sellers wrap SMTP providers (SendGrid, Mailgun, SES) as marketplace services. Customers point their app's SMTP settings at `smtp.unitysvc.com` and send. The seller's SMTP credentials are hidden — customers authenticate with their UnitySVC API key.

**Service types**: `smtp_relay`

### Content and media

Sellers host files on S3, GCS, R2, or other storage. Customers browse and download through the S3 gateway (`s3.unitysvc.com`) using standard S3 tools (boto3, aws-cli, rclone). The platform meters downloads and hides the seller's storage credentials.

For video/audio streaming (HLS, DASH), the HTTP API gateway serves manifest files and media segments — standard HTTP, no special infrastructure needed.

**Service types**: `content_delivery`, `video_streaming`, `audio_streaming`, `data_feed`

### Compute environments

Sellers offer on-demand computing environments (GPU instances, licensed software, analysis tools). Customers enroll, connect via SSH tunnel or WireGuard VPN, use the environment, and disconnect. Time-based billing charges only for active usage.

**Service types**: `compute`

### Monitoring and scheduled tasks

The platform triggers actions on a schedule on behalf of customers. Sellers provide the checking/action logic; the platform handles scheduling, alerting, and billing. Uses the existing RecurrentRequest infrastructure.

**Service types**: `uptime_monitoring`, `ssl_monitoring`, `dns_monitoring`, `cron`, `webhook_relay`

## Service Delivery Patterns

Orthogonal to the service category, each service uses one of these delivery patterns. The pattern determines **who provides upstream credentials** and **whether enrollment is required**.

| Pattern | Who pays provider? | Enrollment? | Customer action |
|---------|-------------------|-------------|-----------------|
| **Managed** | Seller | No | None — use immediately |
| **Managed + parameters** | Seller | Yes | Enroll and configure |
| **BYOK** | Customer | No | Store API key as a secret |
| **BYOE** | Customer (self-hosted) | Yes | Enroll with endpoint URL |
| **Recurrent** | Any of the above | Yes | Enroll and configure schedule |
| **Subscription** | Seller | Yes | Enroll; platform charges daily/hourly via heartbeat |

### Managed services

The seller provides upstream credentials. All customers share the same upstream endpoint. No enrollment required.

```toml
# Offering — seller's upstream credentials
[upstream_access_config."OpenAI API"]
base_url = "https://api.openai.com/v1"
api_key = "${ secrets.OPENAI_API_KEY }"

# Listing — customer-facing gateway path
[user_access_interfaces."OpenAI API Access"]
access_method = "http"
base_url = "${API_GATEWAY_BASE_URL}/p/openai"

[user_access_interfaces."OpenAI API Access".routing_key]
model = "gpt-4"
```

Request flow: `Customer → API key → Gateway → seller's upstream creds → Provider`

### BYOK (Bring Your Own Key)

The customer provides their own API key. No enrollment required — the key is stored in the customer's secret store.

```toml
# Offering — references customer's secret
[upstream_access_config."Groq API"]
base_url = "https://api.groq.com/openai/v1"
api_key = "${ customer_secrets.GROQ_API_KEY }"
```

The `${ ... }` pattern distinguishes secret ownership:

| Pattern | Owner | Resolved from |
|---------|-------|---------------|
| `${ secrets.NAME }` | Seller | Seller's secret store |
| `${ customer_secrets.NAME }` | Customer | Customer's secret store |

Customer secrets are auto-detected by scanning `upstream_access_config` for `${ customer_secrets.XXX }` patterns. No separate declaration needed.

### BYOE (Bring Your Own Endpoint)

The customer provides the URL of their own service instance (e.g., self-hosted Ollama). Enrollment required.

```toml
# Offering — templates resolve from enrollment parameters
[upstream_access_config."Ollama API"]
base_url = "{{ base_url }}"
api_key = "${ customer_secrets.{{ api_key_secret }} }"
```

Two-phase resolution:
1. **Jinja rendering**: `{{ base_url }}` → `http://my-server:11434`
2. **Secret resolution**: `${ customer_secrets.MY_KEY }` → actual key value

### Recurrent services

The platform triggers requests on a schedule. Recurrence is orthogonal to delivery pattern — any service type can be recurrent.

```toml
[service_options]
prompt_recurrence = true
recurrence_min_interval_seconds = 300    # minimum 5 minutes
recurrence_max_interval_seconds = 86400  # maximum 1 day
recurrence_allow_cron = true
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `prompt_recurrence` | bool | `false` | Prompt for recurrence parameters during enrollment |
| `recurrence_min_interval_seconds` | int | `60` | Minimum interval |
| `recurrence_max_interval_seconds` | int | `604800` | Maximum interval (7 days) |
| `recurrence_allow_cron` | bool | `true` | Allow cron expressions |

### Subscription (time-based billing)

For services where customers pay for duration (compute, content libraries), the platform creates a daily/hourly heartbeat request via RecurrentRequest. Charges accrue while enrolled; cancellation stops charges. No new billing model — uses existing `constant` pricing + scheduled requests.

### Enrollment variables

When per-enrollment values are needed in URLs (e.g., unique topic codes):

```toml
[service_options.enrollment_vars]
topic = "{{ enrollment_code(6) }}"

[user_access_interfaces.gateway]
access_method = "http"
base_url = "${API_GATEWAY_BASE_URL}/ntfy/{{ topic }}"
```

Rendering happens in two phases:
1. `enrollment_vars` rendered first — `{{ enrollment_code(6) }}` → `VTXBNM`
2. Access interface URL rendered — `{{ topic }}` → `VTXBNM`

See [User Access Interface Templates](tech-notes/user-access-interface-template.md) for details.

## Comparison Table

| Aspect | Managed | BYOK | BYOE | Recurrent | Subscription |
|--------|---------|------|------|-----------|-------------|
| **upstream api_key** | `${ secrets.X }` | `${ customer_secrets.X }` | `${ customer_secrets.{{ param }} }` | Same as base | Same as base |
| **upstream base_url** | Static URL | Static URL | `{{ base_url }}` | Same as base | Same as base |
| **Enrollment?** | No | No | Yes | Yes | Yes |
| **Customer provides** | Nothing | API key | Endpoint URL | Schedule | Nothing |
| **Pricing** | Per-request/token | Per-request/token | Per-request/token | Per-request/token | Time-based (daily/hourly) |

## What Requires Enrollment?

| Condition | Why |
|-----------|-----|
| `user_parameters_schema` is non-empty | Customer must provide configuration |
| `enrollment_vars` is non-empty | Per-enrollment URL templating |
| `prompt_recurrence` is true | Per-enrollment schedule |
| Subscription pricing | Heartbeat linked to enrollment lifecycle |

Conditions that do **not** require enrollment:

| Condition | Why |
|-----------|-----|
| BYOK (`${ customer_secrets.X }`) | Resolved from secret store at routing time |
| Seller secrets (`${ secrets.X }`) | Seller-level, resolved at routing time |
| Shared access interfaces | Same URL for all customers |

## Service Groups

Services can be organized into [service groups](data-structure.md) for unified routing. A customer sends a request to a group path (e.g., `/g/llm/v1/chat/completions`), and the platform routes to the best available service using weighted selection.

Groups can contain a mix of delivery patterns:

- **Managed services** — always available
- **BYOK services** — skipped if the customer hasn't stored the required secret
- **BYOE services** — skipped if the customer hasn't enrolled

This enables fallback patterns: route to the customer's BYOK key first, fall back to a seller-managed service if the key is missing.
