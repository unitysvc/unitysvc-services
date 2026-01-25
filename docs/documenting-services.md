# Documenting Service Listings

This guide explains how to add documentation and files to your service listings in UnitySVC.

## Overview

Documents in UnitySVC can be in any format (`.md`, `.py`, `.js`, `.sh`, etc.) and are referenced in listing files. Files with an additional `.j2` extension are treated as **Jinja2 templates** and expanded dynamically before use.

## Document Types

### Standard Documents

Regular files are used as-is without any processing:

```
docs/
├── description.md          # Markdown documentation
├── getting-started.md      # Tutorial
├── api-reference.md        # API documentation
├── faq.md                  # Frequently asked questions
```

**Characteristics:**

-   Used exactly as stored
-   No variable substitution
-   No template processing
-   Validated only for file existence

**Example use cases:**

-   Static documentation that doesn't change per service
-   General guides and tutorials
-   Privacy policies and terms of service
-   FAQ documents

### Jinja2 Template Documents

Files ending with `.j2` are processed as Jinja2 templates:

```
docs/
├── description.md.j2       # Service-specific description template
├── quickstart.md.j2        # Quickstart guide with dynamic content
├── example.py.j2           # Python code example template
├── example.js.j2           # JavaScript code example template
└── test.sh.j2              # Shell script template
```

**Characteristics:**

-   Rendered before use with actual data
-   Support variable substitution
-   Access to listing, offering, provider, and seller data
-   Validated for Jinja2 syntax errors
-   `.j2` extension is stripped after rendering

**Example use cases:**

-   Service-specific descriptions that include model names
-   Code examples that reference specific endpoints
-   Documentation that varies by provider or seller
-   Dynamic content based on listing data

## File Naming Convention

The file extension determines how the document is processed:

| Filename            | Type                | Rendered As | Processing          |
| ------------------- | ------------------- | ----------- | ------------------- |
| `description.md`    | Markdown            | `.md`       | Used as-is          |
| `description.md.j2` | Markdown template   | `.md`       | Jinja2 → Markdown   |
| `example.py`        | Python script       | `.py`       | Used as-is          |
| `example.py.j2`     | Python template     | `.py`       | Jinja2 → Python     |
| `example.js`        | JavaScript          | `.js`       | Used as-is          |
| `example.js.j2`     | JavaScript template | `.js`       | Jinja2 → JavaScript |
| `example.sh`        | Shell script        | `.sh`       | Used as-is          |
| `example.sh.j2`     | Shell template      | `.sh`       | Jinja2 → Shell      |
| `api-guide.md`      | Markdown            | `.md`       | Used as-is          |
| `api-guide.md.j2`   | Markdown template   | `.md`       | Jinja2 → Markdown   |

## Adding Documents to Listings

Documents are added to listings through the `documents` field at the listing level.

### Basic Document Structure

Documents are defined in your listing files at the top level. The listing automatically belongs to the offering in the same directory.

**Example: `listing.json`**

```json
{
    "schema": "listing_v1",
    "name": "listing-default",
    "user_access_interfaces": {
        "API Interface": {
            "access_method": "http",
            "base_url": "https://api.example.com/v1"
        }
    },
    "documents": {
        "GPT-4 Overview": {
            "category": "getting_started",
            "file_path": "../../docs/gpt4-description.md.j2",
            "mime_type": "markdown",
            "is_public": true
        },
        "Quick Start Guide": {
            "category": "getting_started",
            "file_path": "../../docs/quickstart.md",
            "mime_type": "markdown",
            "is_public": true
        }
    }
}
```

**Note:** Both `documents` and `user_access_interfaces` use dict format where the key becomes the title/name. This enables easy merging via override files.

### Document Fields

-   **`category`** (required): Document category type

    -   `description` - Service descriptions
    -   `getting_started` - Quickstart guides
    -   `api_reference` - API documentation
    -   `code_examples` - Executable code examples (see [Creating Code Examples](code-examples.md))
    -   `faq` - Frequently asked questions
    -   `pricing` - Pricing information
    -   `terms_of_service` - Terms of service
    -   `privacy_policy` - Privacy policy
    -   `logo` - Company/service logos

-   **Document key** (required): The dict key serves as the document title (5-255 chars)

-   **`file_path`** (required): Relative path from listing file to the document

    -   Path resolution is relative to the listing file location
    -   Example: `../../docs/description.md.j2` points to provider-level docs
    -   Example: `quickstart.md` points to service-level doc in same directory

-   **`mime_type`** (required): Document content type

    -   `markdown` - Markdown documents
    -   `python` - Python scripts
    -   `javascript` - JavaScript files
    -   `shell` - Shell scripts
    -   `json` - JSON documents
    -   `pdf` - PDF files
    -   `png`, `jpeg`, `svg` - Image files

-   **`is_public`** (required): Whether document is publicly accessible

    -   `true` - Available to all users
    -   `false` - Restricted access

-   **`requirements`** (optional): Package dependencies for code examples

    -   For Python: `["httpx", "openai"]`
    -   For JavaScript: `["node-fetch", "openai"]`

-   **`expect`** (optional): Expected output for code example validation
    -   Used by test framework (see [Creating Code Examples](code-examples.md))
    -   Example: `"✓ Test passed"`

## Template Variables

Templates have access to four main data structures:

### 1. `listing` - Listing Data (Listing_v1)

Full access to the listing data structure:

```jinja2
{{ listing.name }}                      # Listing identifier
{{ listing.display_name }}              # Customer-facing name
{{ listing.status }}                    # Listing status (draft, ready, deprecated)
{{ listing.user_access_interfaces }}    # Array of interfaces
{{ listing.list_price }}                # Customer-facing pricing
```

### 2. `offering` - Service Offering Data (Offering_v1)

Service offering metadata from `offering.json`:

```jinja2
{{ offering.name }}                     # Service/offering name (use this for service name)
{{ offering.display_name }}             # Human-readable service name
{{ offering.service_type }}             # e.g., "llm", "embedding"
{{ offering.description }}              # Service description
{{ offering.details }}                  # Technical details
{{ interface.signature.model }}         # model of a LLM request
```

### 3. `provider` - Provider Data (Provider_v1)

Provider metadata from `provider.toml` or `provider.json`:

```jinja2
{{ provider.name }}                     # Provider name (use this for provider name)
{{ provider.display_name }}             # Human-readable provider name
{{ provider.contact_email }}            # Contact email
```

Note: For API credentials, use environment variables (`API_KEY`, `BASE_URL`) instead of template variables.

### 4. `seller` - Seller Data (Seller_v1)

Seller metadata from `seller.json` (seller is derived from API key during publishing):

```jinja2
{{ seller.name }}                       # Seller name
{{ seller.display_name }}               # Human-readable seller name
{{ seller.contact_email }}              # Contact email
```

### Using Defaults

If a field might not exist, use Jinja2 defaults to prevent errors:

```jinja2
{{ listing.optional_field | default('N/A') }}
{{ offering.description | default('No description available') }}
{{ provider.support_url | default('https://example.com/support') }}
```

## Document Examples

### Static Markdown Document

**File: `description.md`**

```markdown
# GPT-4 Overview

GPT-4 is a large multimodal model that can solve complex problems with greater accuracy.

## Features

-   Advanced reasoning capabilities
-   Multimodal input support
-   Improved factual accuracy
-   Better instruction following

## Use Cases

-   Content generation
-   Code assistance
-   Data analysis
-   Question answering
```

**In `listing.json` documents:**

```json
"Service Overview": {
    "category": "getting_started",
    "file_path": "description.md",
    "mime_type": "markdown",
    "is_public": true
}
```

### Template Markdown Document

**File: `description.md.j2`**

```markdown
# {{ offering.name }} Overview

{{ offering.name }} is available through {{ provider.name }} on the {{ seller.name }} platform.

## Service Details

-   **Service Name**: {{ offering.name }}
-   **Provider**: {{ provider.name }}
-   **Type**: {{ offering.service_type }}
-   **Listing Type**: {{ listing.listing_type }}

## Getting Started

To use this service, connect to the API endpoint at:
`{{ interface.base_url }}`

{% if offering.service_info.description %}
{{ offering.service_info.description }}
{% endif %}

## Support

For support inquiries, contact {{ seller.contact_email }}.
```

**In `listing.json` documents:**

```json
"Service Overview": {
    "category": "getting_started",
    "file_path": "description.md.j2",
    "mime_type": "markdown",
    "is_public": true
}
```

### Quickstart Guide Template

**File: `quickstart.md.j2`**

````markdown
# Quick Start: {{ offering.name }}

This guide helps you get started with {{ offering.name }} from {{ provider.name }}.

## Prerequisites

-   API key from {{ provider.name }}
-   HTTP client library (curl, httpx, etc.)

## Basic Usage

### Using curl

\```bash
curl {{ interface.base_url }}/chat/completions \
 -H "Content-Type: application/json" \
 -H "Authorization: Bearer YOUR_API_KEY" \
 -d '{
"model": "{{ offering.name }}",
"messages": [{"role": "user", "content": "Hello!"}]
}'
\```

### Using Python

\```python
import httpx

response = httpx.post(
"{{ interface.base_url }}/chat/completions",
headers={"Authorization": "Bearer YOUR_API_KEY"},
json={
"model": "{{ offering.name }}",
"messages": [{"role": "user", "content": "Hello!"}]
}
)

print(response.json())
\```

## Next Steps

-   Check the [API Reference](#) for detailed documentation
-   Try the [code examples](#) for your preferred language
-   Review [best practices](#) for production use
````

**In `listing.json` documents:**

```json
"Quick Start Guide": {
    "category": "getting_started",
    "file_path": "quickstart.md.j2",
    "mime_type": "markdown",
    "is_public": true
}
```

## Directory Organization

### Provider-Level Documents (Shared)

Documents shared across all services from a provider:

```
data/
└── fireworks/
    ├── provider.toml
    ├── docs/                       # Shared documents
    │   ├── auth-guide.md          # Static auth guide
    │   ├── base-example.py.j2     # Shared template
    │   └── quickstart.md.j2       # Shared quickstart
    └── services/
        ├── llama-3-1-405b/
        │   ├── offering.json
        │   └── listing.json       # References ../docs/
        └── llama-3-1-70b/
            ├── offering.json
            └── listing.json       # References ../docs/
```

**Benefit:** Update one shared document and all services inherit the change.

### Service-Level Documents (Specific)

Documents unique to a specific service:

```
data/
└── fireworks/
    └── services/
        └── llama-3-1-405b/
            ├── offering.json
            ├── listing.json
            ├── description.md.j2      # Service-specific description
            └── examples/
                ├── basic.py.j2
                └── advanced.py.j2
```

**Benefit:** Customize documentation per service when needed.

### Mixed Approach (Recommended)

Combine shared and specific documents:

```
data/
└── fireworks/
    ├── provider.toml
    ├── docs/                          # Shared templates
    │   ├── auth-guide.md
    │   ├── base-example.py.j2
    │   └── quickstart.md.j2
    └── services/
        └── llama-3-1-405b/
            ├── offering.json
            ├── listing.json           # References both
            ├── model-specific.md      # Service-specific doc
            └── examples/
                └── use-case.py.j2
```

## Document Categories Reference

### description

Service overview and feature descriptions. Typically shown first to users.

**Example (in documents dict):**

```json
"Service Overview": {
    "category": "getting_started",
    "file_path": "description.md.j2",
    "mime_type": "markdown",
    "is_public": true
}
```

### getting_started

Quickstart guides and initial setup instructions.

**Example:**

```json
"Quick Start Guide": {
    "category": "getting_started",
    "file_path": "quickstart.md",
    "mime_type": "markdown",
    "is_public": true
}
```

### api_reference

Detailed API documentation, endpoint references, and parameter descriptions.

**Example:**

```json
"API Reference": {
    "category": "api_reference",
    "file_path": "api-docs.md",
    "mime_type": "markdown",
    "is_public": true
}
```

### code_example

Executable code examples in various languages. See [Creating Code Examples](code-examples.md) for detailed guide.

**Example:**

```json
"Python Example": {
    "category": "code_example",
    "file_path": "example.py.j2",
    "mime_type": "python",
    "is_public": true,
    "meta": {
        "requirements": ["httpx"],
        "expect": "✓ Test passed"
    }
}
```

### troubleshooting

Frequently asked questions and troubleshooting guides.

**Example:**

```json
"Frequently Asked Questions": {
    "category": "troubleshooting",
    "file_path": "faq.md",
    "mime_type": "markdown",
    "is_public": true
}
```

### specification

Pricing information, specifications, and technical details.

**Example:**

```json
"Pricing Details": {
    "category": "specification",
    "file_path": "pricing.md.j2",
    "mime_type": "markdown",
    "is_public": true
}
```

### terms_of_service

Terms of service for using the service.

**Example:**

```json
"Terms of Service": {
    "category": "terms_of_service",
    "file_path": "terms.md",
    "mime_type": "markdown",
    "is_public": true
}
```

### logo

Company or service logo images.

**Example:**

```json
"Company Logo": {
    "category": "logo",
    "file_path": "logo.png",
    "mime_type": "png",
    "is_public": true
}
```

## Validation

### Validating Documents

Use the validate command to check document references and template syntax:

```bash
# Validate all files including documents
usvc data validate

# Expected output:
# ✓ All files validated successfully
```

**What is validated:**

-   Data files (`.json`, `.toml`) are validated against schemas
-   Template files (`.j2`) are validated for Jinja2 syntax errors
-   File references are checked for existence
-   Document categories are validated against allowed values
-   Regular documents are checked for file existence only

### Common Validation Errors

**Problem:** `File not found: docs/example.md`

**Solution:** Check that the file_path is correct relative to the listing file.

**Problem:** `Jinja2 syntax error: unexpected 'end of template'`

**Solution:** Check for unclosed tags in your `.j2` template files (`{{`, `{%`, `{#`).

**Problem:** `Invalid category: 'custom_category'`

**Solution:** Use one of the standard categories (description, getting_started, api_reference, code_examples, etc.).

## Best Practices

### 1. Use Templates for Dynamic Content

Use `.j2` templates when content varies by service, provider, or listing:

```jinja2
# Good: Uses template for dynamic content
Service {{ offering.name }} from {{ provider.name }}

# Bad: Static content that requires manual updates per service
Service gpt-4 from OpenAI
```

### 2. Share Common Documents

Place shared documents at provider level to reduce duplication:

```
# Good: Shared authentication guide
fireworks/docs/auth-guide.md

# Bad: Duplicated in every service
fireworks/services/llama-3-1-405b/auth-guide.md
fireworks/services/llama-3-1-70b/auth-guide.md (duplicate)
```

### 3. Organize by Category

Use clear document categories to help users find information:

```json
"documents": {
    "Overview": {"category": "getting_started", ...},
    "Quick Start": {"category": "getting_started", ...},
    "API Docs": {"category": "api_reference", ...},
    "Python Example": {"category": "code_example", ...}
}
```

### 4. Make Documents Public

Set `is_public: true` for user-facing documentation:

```json
{
    "is_public": true // Users can access this
}
```

### 5. Validate Before Uploading

Always validate documents before uploading:

```bash
usvc data validate
usvc services upload
```

## Next Steps

-   Learn about [Creating Code Examples](code-examples.md) for testing executable examples
-   Review [File Schemas](https://unitysvc-services.readthedocs.io/en/latest/file-schemas/) for complete field reference
-   Check [Workflows](https://unitysvc-services.readthedocs.io/en/latest/workflows/) for best practices
