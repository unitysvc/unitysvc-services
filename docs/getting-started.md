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
usvc --help
# Or using the full command name:
unitysvc_services --help
```

You should see the command-line interface help output.

**Note:** The command `unitysvc_services` can be invoked using the shorter alias `usvc`. All examples below use the shorter `usvc` alias.

## Quick Start: Create Your First Service

### Step 1: Initialize Your Data Directory

Create a new provider:

```bash
usvc init provider my-provider
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
usvc init offering my-first-service
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
usvc init listing my-first-listing
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
usvc init seller my-marketplace
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
usvc validate
```

Fix any validation errors reported.

### Step 7: Format Your Files

```bash
usvc format
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
usvc publish

# Or specify path
usvc publish --data-path ./data

# Or publish specific types
usvc publish providers
usvc publish sellers
```

### Step 9: Verify Your Published Data

```bash
# Query with default fields
usvc query providers
usvc query offerings
usvc query listings

# Query with custom fields - show only specific columns
usvc query providers --fields id,name,contact_email
usvc query listings --fields id,service_name,listing_type,status

# Query as JSON for programmatic use
usvc query offerings --format json
```

## Next Steps

-   **[Data Structure](data-structure.md)** - Learn about file organization and naming rules
-   **[Workflows](workflows.md)** - Explore manual and automated workflows
-   **[CLI Reference](cli-reference.md)** - Browse all available commands

## Common Operations

### List Local Files

```bash
usvc list providers
usvc list offerings
usvc list listings
```

### Update Local Files

```bash
# Update service status
usvc update offering --name my-service --status ready

# Update listing status
usvc update listing --services my-service --status in_service
```

### Automated Service Generation

For providers with large catalogs, set up automated generation:

1. Add `services_populator` configuration to `provider.toml`
2. Create a script to fetch and generate service files
3. Run: `usvc populate`

See [Workflows](workflows.md#automated-workflow) for details.

## Troubleshooting

### Validation Errors

-   Check that directory names match normalized field values
-   Ensure all required fields are present
-   Verify file paths are correct (relative paths)

### Publishing Errors

-   Verify API credentials are set correctly
-   Use `usvc publish` (without subcommand) to publish all types in the correct order automatically
-   Ensure backend URL is accessible
-   Check that you're running from the correct directory or using `--data-path`

### Format Issues

-   Run `usvc format --check` to see what would change
-   Use `usvc format` to auto-fix formatting

## Getting Help

-   Check the [CLI Reference](cli-reference.md) for command details
-   Review [Data Structure](data-structure.md) for file organization rules
-   Open an issue on [GitHub](https://github.com/unitysvc/unitysvc-services/issues)
