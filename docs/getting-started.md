# Getting Started

This guide will help you get started with the UnitySVC Provider SDK.

## Installation

### Requirements

-   Python 3.11 or later
-   pip or uv package manager

### Install from PyPI

```bash
pip install unitysvc-services
```

### Verify Installation

```bash
unitysvc_services --help
```

You should see the command-line interface help output.

## Quick Start: Create Your First Service

### Step 1: Initialize Your Data Directory

Create a new provider:

```bash
unitysvc_services init provider my-provider
```

This creates:

```
data/
└── my-provider/
    ├── provider.toml
    └── services/
```

### Step 2: Create a Service Offering

```bash
unitysvc_services init offering my-first-service
```

This creates:

```
data/
└── my-provider/
    └── services/
        └── my-first-service/
            └── service.toml
```

### Step 3: Create a Service Listing

```bash
unitysvc_services init listing my-first-listing
```

This creates:

```
data/
└── my-provider/
    └── services/
        └── my-first-service/
            ├── service.toml
            └── listing-svcreseller.toml
```

### Step 4: Create a Seller

Create a seller file at the root of your data directory:

```bash
unitysvc_services init seller my-marketplace
```

This creates:

```
data/
├── seller.toml
└── my-provider/
    └── services/
        └── my-first-service/
            ├── service.toml
            └── listing-svcreseller.toml
```

### Step 5: Edit Your Files

Open the generated files and fill in your service details:

-   **provider.toml** - Provider information (name, display name, contact)
-   **seller.toml** - Seller business information
-   **service.toml** - Service offering details (pricing, API endpoints)
-   **listing-svcreseller.toml** - User-facing service information

### Step 6: Validate Your Data

```bash
unitysvc_services validate
```

Fix any validation errors reported.

### Step 7: Format Your Files

```bash
unitysvc_services format
```

This ensures consistent formatting (2-space JSON indentation, proper line endings, etc.).

### Step 8: Publish to UnitySVC Platform

Set your credentials:

```bash
export UNITYSVC_BASE_URL="https://api.unitysvc.com/api/v1"
export UNITYSVC_API_KEY="your-api-key"
```

Publish your data (publishes all types in correct order: sellers → providers → offerings → listings):

```bash
# From data directory
cd data
unitysvc_services publish

# Or specify path
unitysvc_services publish --data-path ./data

# Or publish specific types
unitysvc_services publish providers
unitysvc_services publish sellers
```

### Step 9: Verify Your Published Data

```bash
# Query with default fields
unitysvc_services query providers
unitysvc_services query offerings
unitysvc_services query listings

# Query with custom fields - show only specific columns
unitysvc_services query providers --fields id,name,contact_email
unitysvc_services query listings --fields id,service_name,listing_type,status

# Query as JSON for programmatic use
unitysvc_services query offerings --format json
```

## Next Steps

-   **[Data Structure](data-structure.md)** - Learn about file organization and naming rules
-   **[Workflows](workflows.md)** - Explore manual and automated workflows
-   **[CLI Reference](cli-reference.md)** - Browse all available commands

## Common Operations

### List Local Files

```bash
unitysvc_services list providers
unitysvc_services list offerings
unitysvc_services list listings
```

### Update Local Files

```bash
# Update service status
unitysvc_services update offering --name my-service --status ready

# Update listing status
unitysvc_services update listing --service-name my-service --status in_service
```

### Automated Service Generation

For providers with large catalogs, set up automated generation:

1. Add `services_populator` configuration to `provider.toml`
2. Create a script to fetch and generate service files
3. Run: `unitysvc_services populate`

See [Workflows](workflows.md#automated-workflow) for details.

## Troubleshooting

### Validation Errors

-   Check that directory names match normalized field values
-   Ensure all required fields are present
-   Verify file paths are correct (relative paths)

### Publishing Errors

-   Verify API credentials are set correctly
-   Use `unitysvc_services publish` (without subcommand) to publish all types in the correct order automatically
-   Ensure backend URL is accessible
-   Check that you're running from the correct directory or using `--data-path`

### Format Issues

-   Run `unitysvc_services format --check` to see what would change
-   Use `unitysvc_services format` to auto-fix formatting

## Getting Help

-   Check the [CLI Reference](cli-reference.md) for command details
-   Review [Data Structure](data-structure.md) for file organization rules
-   Open an issue on [GitHub](https://github.com/unitysvc/unitysvc-services/issues)
