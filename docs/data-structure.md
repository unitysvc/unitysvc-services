# Data Directory Structure

## Overview

The UnitySVC services data management follows a **local-first, version-controlled workflow**. All service data is created and maintained in a local directory (typically called `data/`) that is version-controlled with git.

## Terminology

In this SDK:

-   **"Services" or "Offerings"** refer to service offering files (schema `service_v1`) that define what providers offer
-   **"Listings"** refer to service listing files (schema `listing_v1`) that define how sellers present/sell those services
-   Both offerings and listings are organized under each provider's `services/` directory

## Required File Structure

The data directory must follow a specific structure with naming conventions and file placement rules:

```
data/
├── seller.json                          # Required: ONE seller file for entire repo
├── ${provider_name}/                    # Provider directory (matches provider name)
│   ├── provider.json or provider.toml   # Required: Provider metadata
│   ├── README.md                        # Optional: Provider documentation
│   ├── terms-of-service.md             # Optional: Provider ToS
│   ├── docs/                            # Optional: Shared documentation folder
│   │   ├── code-example.py             # Can be referenced by multiple services
│   │   └── api-guide.md                # Shared across services
│   └── services/                        # Required: Services directory
│       ├── ${service_name}/             # Service directory (matches service name)
│       │   ├── service.json or service.toml      # Required: Service offering
│       │   ├── listing-${seller}.json or .toml   # Required: Service listing(s)
│       │   └── specific-example.md      # Optional: Service-specific docs
│       └── ${another_service}/
│           ├── service.json
│           └── listing-svcreseller.json  # Can reference ../../docs/code-example.py
└── ${another_provider}/
    ├── provider.toml
    └── services/
        └── ...
```

## Naming Rules and Restrictions

### 1. Provider Directory (`${provider_name}/`)

-   **Must match** the `name` field in `provider.json`/`provider.toml`
-   Name is normalized: lowercase with hyphens replacing spaces/underscores
-   Example: Provider name `"My Provider"` → directory `my-provider/`

### 2. Seller File (`seller.json` or `seller.toml`)

-   **Exactly ONE** seller file per repository (at root of `data/`)
-   Defines the seller for all services in this data repository
-   Can be JSON or TOML format
-   Contains seller business information, contact details, and branding

### 3. Services Directory

-   **Must be** named `services/` under each provider directory
-   Path: `${provider_name}/services/`
-   This is where all service offerings and listings are defined

### 4. Service Directory (`${service_name}/`)

-   **Must match** the `name` field in `service.json`/`service.toml`
-   Name is normalized: lowercase with hyphens
-   Example: Service name `"GPT-4"` → directory `gpt-4/`
-   Located under: `${provider_name}/services/${service_name}/`

### 5. Service Offering Files (referred to as "services" in the SDK)

-   **service.json** or **service.toml**: Service offering metadata (required)
-   Schema must be `"service_v1"`
-   Contains upstream service details, pricing, access interfaces
-   Defines what the provider offers
-   Location: `${provider_name}/services/${service_name}/service.json`

### 6. Service Listing Files

-   **listing-${seller}.json** or **listing-${seller}.toml**: Service listing (required)
-   File name pattern: `listing-*.json` or `listing-*.toml`
-   Commonly named: `listing-svcreseller.json`, `listing-marketplace.json`
-   Schema must be `"listing_v1"`
-   Contains user-facing information, downstream pricing, documentation
-   Defines how the seller presents/sells the service
-   Location: `${provider_name}/services/${service_name}/listing-*.json`
-   Both offerings and listings are defined in the same service directory under the provider

#### Multiple Listings Per Service

When a single service offering has multiple listings (e.g., different pricing tiers, different marketplaces), the filename becomes significant:

-   **Filename as identifier**: If the `name` field is not provided in the listing file, the filename (without extension) is automatically used as the listing name
-   **Example**: `listing-premium.json`, `listing-basic.json`, `listing-enterprise.json` for different tiers
-   **Best practice**: Use descriptive filenames that indicate the listing variant, or explicitly set the `name` field in each file

### 7. External Files (Documentation, Code Examples, etc.)

-   External files like code examples, documentation, images can be placed anywhere in the directory structure
-   They are referenced by **relative paths** from the referencing file
-   This allows sharing files across multiple services

## File Formats

Both JSON and TOML formats are supported for all data files:

### JSON Format

```json
{
    "schema": "service_v1",
    "name": "my-service",
    "display_name": "My Service",
    "description": "A high-performance digital service"
}
```

### TOML Format

```toml
schema = "service_v1"
name = "my-service"
display_name = "My Service"
description = "A high-performance digital service"
```

## Override Files

Override files provide a way to complement and customize data files without modifying the base files. This is particularly useful when base files are auto-generated by scripts, and you need to manually curate specific values like status, logo URLs, or other metadata.

### Naming Pattern

Override files follow the pattern: `<base_name>.override.<extension>`

Examples:

-   `service.json` → `service.override.json`
-   `provider.toml` → `provider.override.toml`
-   `listing-premium.json` → `listing-premium.override.json`

### How Override Files Work

When any data file is loaded by the SDK:

1. The base file is loaded first
2. The system checks for a corresponding `.override.*` file
3. If found, the override file is loaded and **deep-merged** into the base data
4. Override values take precedence over base values

This merge happens automatically and transparently - you don't need to do anything special.

### Merge Behavior

**Nested Dictionaries**: Recursively merged - override values complement and replace base values

**Example**:

```json
// Base: service.json
{
  "name": "my-service",
  "config": {
    "host": "localhost",
    "port": 8080,
    "timeout": 30
  }
}

// Override: service.override.json
{
  "config": {
    "port": 9000,
    "ssl": true
  },
  "status": "active"
}

// Merged Result
{
  "name": "my-service",
  "config": {
    "host": "localhost",    // preserved from base
    "port": 9000,           // overridden
    "timeout": 30,          // preserved from base
    "ssl": true             // added from override
  },
  "status": "active"        // added from override
}
```

**Lists and Primitives**: Completely replaced (not merged)

```json
// Base: service.json
{
  "tags": ["python", "web", "api"],
  "version": 1
}

// Override: service.override.json
{
  "tags": ["backend", "production"]
}

// Merged Result
{
  "tags": ["backend", "production"],  // completely replaced
  "version": 1
}
```

This replacement behavior for lists is intentional and predictable - if you want to change a list, simply specify the complete desired list in the override file.

### Common Use Cases

**1. Manual curation of auto-generated data**

```json
// service.json (auto-generated by script)
{
  "schema": "service_v1",
  "name": "gpt-4",
  "description": "Auto-generated description",
  "status": "draft"
}

// service.override.json (manually maintained)
{
  "status": "active",
  "logo_url": "https://example.com/custom-logo.png",
  "featured": true
}
```

**2. Environment-specific configuration**

```toml
# provider.toml (base configuration)
schema = "provider_v1"
name = "my-provider"
base_url = "https://api.example.com"

# provider.override.toml (local testing overrides)
base_url = "http://localhost:8000"
debug_mode = true
```

**3. Maintaining custom metadata**

```json
// listing-premium.json (generated from template)
{
  "schema": "listing_v1",
  "name": "premium-tier",
  "pricing": { /* auto-generated */ }
}

// listing-premium.override.json (manual customization)
{
  "featured": true,
  "promotional_badge": "Best Value",
  "custom_cta": "Try Premium Now!"
}
```

### Version Control

Override files should be committed to version control alongside base files. They are part of your data and represent intentional manual customizations that should be preserved and tracked.

### File Location

Override files must be in the same directory as their corresponding base files, following the directory structure rules described above.

## Schema Requirements

Each file must include a `schema` field identifying its type:

-   **provider.json/toml**: `schema = "provider_v1"`
-   **seller.json/toml**: `schema = "seller_v1"`
-   **service.json/toml**: `schema = "service_v1"`
-   **listing-\*.json/toml**: `schema = "listing_v1"`

## Validation Rules

The validator enforces these structure rules:

1. **Service name uniqueness**: Service names must be unique within each provider's `services/` directory
2. **Listing references**: Each listing file must reference a valid service in the same directory
3. **Single service convenience**: If a service directory contains only one service file, listing files can omit the `service_name` field (it will be inferred)
4. **Multiple services requirement**: If a service directory contains multiple services, listing files **must** explicitly specify `service_name`
5. **Seller uniqueness**: Only one seller file is allowed per repository
6. **Provider name matching**: Provider directory name must match the normalized `name` field in provider file
7. **Service name matching**: Service directory name must match the normalized `name` field in service file

## Shared Documentation Pattern

External files can be shared across multiple services using relative paths:

### Example Structure

```
data/
├── openai/
│   ├── provider.toml
│   ├── docs/
│   │   ├── code-example.py        # Shared by multiple services
│   │   └── api-guide.md
│   └── services/
│       ├── gpt-4/
│       │   ├── service.json
│       │   └── listing.json       # References: ../../docs/code-example.py
│       └── gpt-3.5-turbo/
│           ├── service.json
│           └── listing.json       # References: ../../docs/code-example.py (same file!)
```

### In Listing Files

```json
{
    "schema": "listing_v1",
    "user_access_interfaces": [
        {
            "documents": [
                {
                    "title": "Python Code Example",
                    "file_path": "../../docs/code-example.py",
                    "category": "code_examples"
                }
            ]
        }
    ]
}
```

### Benefits

-   **Reusability**: One code example can be shared by multiple services
-   **Maintainability**: Update one file, all services reflect the change
-   **Organization**: Group related documentation at provider level
-   **Flexibility**: Place files wherever makes sense for your structure

## Complete Example

```
data/
├── seller.json                          # Seller: "My Marketplace"
├── openai/                              # Provider: "openai"
│   ├── provider.toml                    # name = "openai"
│   └── services/
│       ├── gpt-4/                       # Service: "gpt-4"
│       │   ├── service.json             # name = "gpt-4"
│       │   ├── listing-premium.json     # name = "listing-premium" (or defaults to filename)
│       │   └── listing-basic.json       # name = "listing-basic" (multiple listings for one service)
│       └── gpt-3.5-turbo/              # Service: "gpt-3.5-turbo"
│           ├── service.json             # name = "gpt-3.5-turbo"
│           └── listing-svcreseller.json # Single listing
└── anthropic/                           # Provider: "anthropic"
    ├── provider.json                    # name = "anthropic"
    └── services/
        └── claude-3-opus/               # Service: "claude-3-opus"
            ├── service.toml             # name = "claude-3-opus"
            ├── listing-svcreseller.toml # seller_name = "svcreseller"
            └── docs/
                └── usage-guide.md
```

## Next Steps

-   [File Schemas](file-schemas.md) - Detailed schema specifications
-   [CLI Reference](cli-reference.md#validate) - Validation command details
-   [Workflows](workflows.md) - Learn about manual and automated workflows
