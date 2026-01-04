# Data Directory Structure

## Overview

UnitySVC provides two ways to manage service data:

1. **Web Interface** ([unitysvc.com](https://unitysvc.com)) - Create and edit data visually, then export for SDK use
2. **SDK** (this tool) - Manage data locally with version control, automation, and CI/CD integration

The SDK follows a **local-first, version-controlled workflow**. All service data is maintained in a local directory (typically called `data/`) that is version-controlled with git. Data can be created via the web interface and exported, or created manually following the schemas.

## The Service Data Model

A **Service** in UnitySVC consists of three complementary data components. These are organized separately in the filesystem for reusability, but are **published together** as a unified service:

```mermaid
flowchart TB
    subgraph Service["Published Together"]
        P["<b>Provider Data</b><br/>WHO provides<br/><i>provider_v1</i>"]
        O["<b>Offering Data</b><br/>WHAT is provided<br/><i>offering_v1</i>"]
        L["<b>Listing Data</b><br/>HOW it's sold<br/><i>listing_v1</i>"]
    end

    P --> O --> L

    style P fill:#e3f2fd
    style O fill:#fff3e0
    style L fill:#e8f5e9
```

### Component Details

| Component | Schema | Location | Purpose |
|-----------|--------|----------|---------|
| **Provider Data** | `provider_v1` | `{provider}/provider.json` | Identity of the service provider |
| **Offering Data** | `offering_v1` | `{provider}/services/{service}/service.json` | Technical service definition |
| **Listing Data** | `listing_v1` | `{provider}/services/{service}/listing-*.json` | Customer-facing presentation |

### Why Three Parts?

1. **Provider Data** - Defined once per provider, automatically shared across all their offerings
2. **Offering Data** - Defined once per service, can have multiple listings (pricing tiers, marketplaces)
3. **Listing Data** - Defines how each service variant is presented and priced for customers

This separation enables:
- **Reusability**: Update provider info once, affects all services
- **Flexibility**: One offering can have basic/premium/enterprise listings
- **Maintainability**: Clear separation of concerns

### Publishing Model

When you run `usvc publish`, the SDK uses a **listing-centric** approach:

1. Finds all listing files (`listing_v1` schema) in the directory tree
2. For each listing, locates the **single** offering file (`offering_v1`) in the same directory
3. Locates the provider file (`provider_v1`) in the parent directory
4. Publishes all three together as a unified service to `/seller/services`

**Relationship by Location**: The relationship between providers, offerings, and listings is determined entirely by file location:
- A listing belongs to the offering in the same directory
- An offering belongs to the provider in the parent directory
- No explicit linking fields (like `service_name` or `provider_name`) are needed in the data files

```mermaid
graph TD
    A[Listing File] -->|same directory| B[Offering File]
    A -->|parent directory| C[Provider File]
    A & B & C -->|published together| D[/seller/services API]
```

## Required File Structure

The data directory must follow a specific structure with naming conventions and file placement rules:

```
data/
├── ${provider_name}/                    # Provider directory (matches provider name)
│   ├── provider.json or provider.toml   # Required: Provider Data
│   ├── README.md                        # Optional: Provider documentation
│   ├── terms-of-service.md             # Optional: Provider ToS
│   ├── docs/                            # Optional: Shared documentation folder
│   │   ├── code-example.py             # Can be referenced by multiple services
│   │   └── api-guide.md                # Shared across services
│   └── services/                        # Required: Services directory
│       ├── ${service_name}/             # Service directory (matches service name)
│       │   ├── service.json or service.toml      # Required: Offering Data
│       │   ├── listing-${variant}.json or .toml  # Required: Listing Data
│       │   └── specific-example.md      # Optional: Service-specific docs
│       └── ${another_service}/
│           ├── service.json
│           └── listing-premium.json     # Can reference ../../docs/code-example.py
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

### 2. Services Directory

-   **Must be** named `services/` under each provider directory
-   Path: `${provider_name}/services/`
-   This is where all service offerings and listings are defined

### 3. Service Directory (`${service_name}/`)

-   **Must match** the `name` field in `service.json`/`service.toml`
-   Name is normalized: lowercase with hyphens
-   Example: Service name `"GPT-4"` → directory `gpt-4/`
-   Located under: `${provider_name}/services/${service_name}/`

### 4. Offering Files (Offering Data)

-   **service.json** or **service.toml**: Service offering metadata (required)
-   Schema must be `"offering_v1"`
-   **Exactly one** offering file per service directory
-   Contains upstream service details, pricing, access interfaces
-   Defines what the provider offers
-   Location: `${provider_name}/services/${service_name}/service.json`
-   The offering automatically belongs to the provider in the parent directory

### 5. Listing Files (Listing Data)

-   **listing-${variant}.json** or **listing-${variant}.toml**: Service listing (required)
-   File name pattern: `listing-*.json` or `listing-*.toml`
-   Commonly named: `listing-default.json`, `listing-premium.json`, `listing-basic.json`
-   Schema must be `"listing_v1"`
-   Contains user-facing information, downstream pricing, documentation
-   Defines how the seller presents/sells the service
-   Location: `${provider_name}/services/${service_name}/listing-*.json`
-   Automatically belongs to the single offering in the same directory

#### Multiple Listings Per Service

When a single service offering has multiple listings (e.g., different pricing tiers, different marketplaces), the filename becomes significant:

-   **Filename as identifier**: If the `name` field is not provided in the listing file, the filename (without extension) is automatically used as the listing name
-   **Example**: `listing-premium.json`, `listing-basic.json`, `listing-enterprise.json` for different tiers
-   **Best practice**: Use descriptive filenames that indicate the listing variant, or explicitly set the `name` field in each file

### 6. External Files (Documentation, Code Examples, etc.)

-   External files like code examples, documentation, images can be placed anywhere in the directory structure
-   They are referenced by **relative paths** from the referencing file
-   This allows sharing files across multiple services

## File Formats

Both JSON and TOML formats are supported for all data files:

### JSON Format

```json
{
    "schema": "offering_v1",
    "name": "my-service",
    "display_name": "My Service",
    "description": "A high-performance digital service"
}
```

### TOML Format

```toml
schema = "offering_v1"
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
  "schema": "offering_v1",
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
-   **service.json/toml**: `schema = "offering_v1"`
-   **listing-\*.json/toml**: `schema = "listing_v1"`

## Validation Rules

The validator enforces these structure rules:

1. **Single offering per directory**: Each service directory must have exactly **one** offering file (`offering_v1` schema)
2. **Listing location**: Each listing file must be in the same directory as a valid offering file
3. **Provider name matching**: Provider directory name must match the normalized `name` field in provider file
4. **Service name matching**: Service directory name must match the normalized `name` field in offering file
5. **Relationship by location**: Listings automatically belong to the offering in their directory—no explicit `service_name` or `provider_name` fields needed

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
├── openai/                              # Provider: "openai"
│   ├── provider.toml                    # Provider Data: name = "openai"
│   └── services/
│       ├── gpt-4/                       # Service: "gpt-4"
│       │   ├── service.json             # Offering Data: name = "gpt-4"
│       │   ├── listing-premium.json     # Listing Data (premium tier)
│       │   └── listing-basic.json       # Listing Data (basic tier)
│       └── gpt-3.5-turbo/              # Service: "gpt-3.5-turbo"
│           ├── service.json             # Offering Data
│           └── listing-default.json     # Listing Data
└── anthropic/                           # Provider: "anthropic"
    ├── provider.json                    # Provider Data: name = "anthropic"
    └── services/
        └── claude-3-opus/               # Service: "claude-3-opus"
            ├── service.toml             # Offering Data
            ├── listing-standard.toml    # Listing Data (standard tier)
            └── docs/
                └── usage-guide.md
```

When publishing, each listing triggers a unified publish:
- `listing-premium.json` → publishes openai provider + gpt-4 offering + premium listing
- `listing-basic.json` → publishes openai provider + gpt-4 offering + basic listing
- etc.

The provider and offering data are sent with each publish but are deduplicated on the backend (unchanged data returns "unchanged" status).

## Next Steps

-   [File Schemas](file-schemas.md) - Detailed schema specifications
-   [CLI Reference](cli-reference.md#publish) - Publishing command details
-   [Workflows](workflows.md) - Learn about manual and automated workflows
