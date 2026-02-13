# User Access Interface Templates

> **Issue**: [unitysvc-bridge-ntfy#1 — Restrict users to enrollment-specific topics](https://github.com/unitysvc/unitysvc-bridge-ntfy/issues/1)
> **Related PR**: [unitysvc#437 — ntfy service integration](https://github.com/unitysvc/unitysvc/pull/437)
> **Date**: 2026-02-10
> **Status**: Implemented

## Overview

String values in `user_access_interfaces` (and `upstream_access_interfaces`) support **Jinja2 template syntax** for dynamic rendering at enrollment time. This enables per-enrollment access interfaces — for example, generating unique endpoint URLs or routing keys for each subscriber.

Interfaces containing template syntax (`{{` or `{%`) are rendered per-enrollment and create enrollment-scoped `AccessInterface` records. Static interfaces (no template syntax) are shared across all enrollments at the listing level.

## Template Context

Templates are rendered with these variables:

| Variable                     | Type   | Description                     |
| ---------------------------- | ------ | ------------------------------- |
| `enrollment.id`              | string | Enrollment UUID                 |
| `enrollment.customer_id`     | string | Customer UUID                   |
| `enrollment.parameters`      | dict   | All enrollment parameters       |

## Template Functions

### `enrollment_code(length=6)`

Creates or retrieves a random code tied to a specific enrollment. The function is **idempotent** — repeated calls for the same enrollment return the same code (looked up by `entity_id` and `code_type=enrollment` in the `action_code` table). This allows both `user_access_interfaces` and `upstream_access_interfaces` to reference the same enrollment-specific code.

```jinja2
{{ enrollment_code() }}      {# 6-character uppercase token, e.g. VTXBNM #}
{{ enrollment_code(8) }}     {# 8-character token #}
```

## Example: ntfy Service

The ntfy service exposes a notification gateway where each enrollment gets a unique topic code.

### Configuration

```toml
# listing.toml — user-facing endpoint with per-enrollment topic
[user_access_interfaces.ntfy-gateway]
access_method = "http"
base_url = "${GATEWAY_BASE_URL}/ntfy/{{ enrollment_code(6) }}"
description = "Your ntfy notification endpoint"
```

```toml
# offering.toml — upstream endpoint with same enrollment code
[upstream_access_interfaces.ntfy-upstream]
access_method = "http"
base_url = "https://ntfy.svcpass.com/{{ enrollment_code(6) }}"
description = "Private ntfy instance"
```

Both templates call `enrollment_code(6)` and resolve to the same code (e.g. `VTXBNM`) for a given enrollment.

### After Enrollment

- Topic code `VTXBNM` is generated and persisted in the `action_code` table
- An enrollment-scoped `AccessInterface` is created with `base_url = "${GATEWAY_BASE_URL}/ntfy/VTXBNM"`
- The user sees their complete, personalized endpoint
- At gateway routing time, the upstream template resolves to `https://ntfy.svcpass.com/VTXBNM`
- Gateway forwards the request to the correct upstream topic

### Access Control

Enrollment-scoped `AccessInterface` records are only visible to the enrollment that generated them:

| `AccessInterface` scope | Who can access | Linked via |
|-------------------------|----------------|------------|
| Listing-level (no template) | All enrolled customers | ServiceEnrollment |
| Group-scoped (`group_id` set) | Customers with GroupEnrollment | GroupEnrollment |
| Enrollment-scoped (from template) | Only that specific enrollment | enrollment_id match |

## How It Works

### User access interfaces (enrollment time)

1. During enrollment creation or activation, the backend checks `listing.user_access_interfaces`
2. Each interface is classified:
   - **Template** (contains `{{` or `{%`): rendered per-enrollment, creates enrollment-scoped `AccessInterface`
   - **Static** (no template syntax): shared listing-scoped `AccessInterface` (idempotent)
3. Template rendering uses `jinja2.Environment(enable_async=True)` with `render_async()`, which auto-awaits async functions like `enrollment_code()`
4. Rendered values are validated as `AccessInterfaceData` and persisted via upsert

### Upstream access interfaces (gateway routing time)

1. When a request arrives, the gateway identifies the enrollment from the user access interface match
2. If the offering's `upstream_access_interfaces` contain template syntax, they are rendered using the enrollment context
3. `enrollment_code()` resolves to the same code that was created at enrollment time (idempotent lookup)
4. The resolved upstream URL is used to forward the request — no upstream `AccessInterface` records are created per enrollment

## Consistency with Service Groups

This mechanism mirrors the existing service group template pattern:

| Aspect | Service Groups | Enrollment Templates |
|--------|---------------|---------------------|
| Template language | Jinja2 | Jinja2 |
| Trigger | Service joins group | User enrolls in service |
| Context | Service metadata | Enrollment + parameters |
| Output | `AccessInterfaceData` | `AccessInterfaceData` |
| Scope link | `AccessInterface.group_id` | `AccessInterface.entity_id` (enrollment) |
