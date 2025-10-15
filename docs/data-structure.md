# Data Directory Structure

## Overview

The UnitySVC services data management follows a **local-first, version-controlled workflow**. All service data is created and maintained in a local directory (typically called `data/`) that is version-controlled with git.

## Terminology

In this SDK:
- **"Services" or "Offerings"** refer to service offering files (schema `service_v1`) that define what providers offer
- **"Listings"** refer to service listing files (schema `listing_v1`) that define how sellers present/sell those services
- Both offerings and listings are organized under each provider's `services/` directory

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
- **Must match** the `name` field in `provider.json`/`provider.toml`
- Name is normalized: lowercase with hyphens replacing spaces/underscores
- Example: Provider name `"My Provider"` → directory `my-provider/`

### 2. Seller File (`seller.json` or `seller.toml`)
- **Exactly ONE** seller file per repository (at root of `data/`)
- Defines the seller for all services in this data repository
- Can be JSON or TOML format
- Contains seller business information, contact details, and branding

### 3. Services Directory
- **Must be** named `services/` under each provider directory
- Path: `${provider_name}/services/`
- This is where all service offerings and listings are defined

### 4. Service Directory (`${service_name}/`)
- **Must match** the `name` field in `service.json`/`service.toml`
- Name is normalized: lowercase with hyphens
- Example: Service name `"GPT-4"` → directory `gpt-4/`
- Located under: `${provider_name}/services/${service_name}/`

### 5. Service Offering Files (referred to as "services" in the SDK)
- **service.json** or **service.toml**: Service offering metadata (required)
- Schema must be `"service_v1"`
- Contains upstream service details, pricing, access interfaces
- Defines what the provider offers
- Location: `${provider_name}/services/${service_name}/service.json`

### 6. Service Listing Files
- **listing-${seller}.json** or **listing-${seller}.toml**: Service listing (required)
- File name pattern: `listing-*.json` or `listing-*.toml`
- Commonly named: `listing-svcreseller.json`, `listing-marketplace.json`
- Schema must be `"listing_v1"`
- Contains user-facing information, downstream pricing, documentation
- Defines how the seller presents/sells the service
- Location: `${provider_name}/services/${service_name}/listing-*.json`
- Both offerings and listings are defined in the same service directory under the provider

#### Multiple Listings Per Service
When a single service offering has multiple listings (e.g., different pricing tiers, different marketplaces), the filename becomes significant:

- **Filename as identifier**: If the `name` field is not provided in the listing file, the filename (without extension) is automatically used as the listing name
- **Example**: `listing-premium.json`, `listing-basic.json`, `listing-enterprise.json` for different tiers
- **Best practice**: Use descriptive filenames that indicate the listing variant, or explicitly set the `name` field in each file

### 7. External Files (Documentation, Code Examples, etc.)
- External files like code examples, documentation, images can be placed anywhere in the directory structure
- They are referenced by **relative paths** from the referencing file
- This allows sharing files across multiple services

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

## Schema Requirements

Each file must include a `schema` field identifying its type:

- **provider.json/toml**: `schema = "provider_v1"`
- **seller.json/toml**: `schema = "seller_v1"`
- **service.json/toml**: `schema = "service_v1"`
- **listing-*.json/toml**: `schema = "listing_v1"`

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
  "user_access_interfaces": [{
    "documents": [
      {
        "title": "Python Code Example",
        "file_path": "../../docs/code-example.py",
        "category": "code_examples"
      }
    ]
  }]
}
```

### Benefits
- **Reusability**: One code example can be shared by multiple services
- **Maintainability**: Update one file, all services reflect the change
- **Organization**: Group related documentation at provider level
- **Flexibility**: Place files wherever makes sense for your structure

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

- [File Schemas](file-schemas.md) - Detailed schema specifications
- [CLI Reference](cli-reference.md#validate) - Validation command details
- [Workflows](workflows.md) - Learn about manual and automated workflows
