# Workflows

This guide explains the different workflows for managing service data with the UnitySVC Provider SDK.

## Overview

The SDK supports two primary workflows:

1. **Manual Workflow** - For small catalogs or one-time setup
2. **Automated Workflow** - For large or dynamic catalogs

## Manual Workflow

Best for providers with:

-   Small number of services (< 20)
-   Infrequently changing catalogs
-   One-time service setup

### Step-by-Step Process

#### 1. Initialize Data Structure

```bash
# Create provider
unitysvc_services init provider my-provider

# Create seller
unitysvc_services init seller my-marketplace

# Create service offering
unitysvc_services init offering my-service

# Create service listing
unitysvc_services init listing my-listing
```

#### 2. Edit Generated Files

Open files in `./data/` and fill in your service details:

-   Provider information (name, contact, metadata)
-   Seller business information
-   Service offering details (API endpoints, pricing, capabilities)
-   Service listing details (user-facing info, documentation)

#### 3. Validate Data

```bash
unitysvc_services validate
```

Fix any validation errors. Common issues:

-   Directory names not matching field values
-   Missing required fields
-   Invalid file paths

#### 4. Format Files

```bash
unitysvc_services format
```

This ensures:

-   JSON files have 2-space indentation
-   Files end with single newline
-   No trailing whitespace

#### 5. Update Local Files as Needed

```bash
# Update service status
unitysvc_services update offering --name my-service --status ready

# Update multiple fields
unitysvc_services update offering --name my-service \
  --status ready \
  --display-name "My Updated Service" \
  --version "2.0"

# Update listing status
unitysvc_services update listing --service-name my-service --status in_service
```

#### 6. Publish to Platform

```bash
# Set credentials
export UNITYSVC_BASE_URL="https://api.unitysvc.com/api/v1"
export UNITYSVC_API_KEY="your-api-key"

# Publish all (handles order automatically: sellers → providers → offerings → listings)
cd data
unitysvc_services publish

# Or from parent directory
unitysvc_services publish --data-path ./data
```

#### 7. Verify on Platform

```bash
# Query with default fields
unitysvc_services query providers
unitysvc_services query offerings
unitysvc_services query listings

# Or query with custom fields for focused output
unitysvc_services query providers --fields id,name,status
unitysvc_services query listings --fields id,service_name,listing_type,status
```

### Version Control Integration

```bash
# After creating/updating files
git add data/
git commit -m "Add new service: my-service"
git push

# Publish from CI/CD
unitysvc_services validate
unitysvc_services publish --data-path ./data
```

## Automated Workflow

Best for providers with:

-   Large service catalogs (> 20 services)
-   Frequently changing services
-   Dynamic pricing or availability
-   Services added/deprecated automatically

### How It Works

1. Configure a populate script in your provider file
2. Script fetches service data from provider's API
3. Script generates service files automatically
4. Validate, format, and publish as normal

### Step-by-Step Process

#### 1. Initialize Provider with Populate Configuration

```bash
unitysvc_services init provider my-provider
```

#### 2. Configure services_populator

Edit `data/my-provider/provider.toml`:

```toml
name = "my-provider"
display_name = "My Service Provider"

[services_populator]
command = "populate_services.py"

[provider_access_info]
API_KEY = "your-provider-api-key"
API_ENDPOINT = "https://api.provider.com/v1"
REGION = "us-east-1"
```

#### 3. Create Populate Script

Create `data/my-provider/populate_services.py`:

```python
#!/usr/bin/env python3
"""Generate service files from provider API."""

import os
import json
from pathlib import Path
import requests

# Get environment variables from provider_access_info
api_key = os.getenv("API_KEY")
api_endpoint = os.getenv("API_ENDPOINT")
region = os.getenv("REGION")

def fetch_services():
    """Fetch services from provider API."""
    response = requests.get(
        f"{api_endpoint}/services",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"region": region}
    )
    response.raise_for_status()
    return response.json()["services"]

def create_service_files(service_data):
    """Create service.json and listing.json files."""
    service_name = service_data["name"].lower().replace(" ", "-")
    service_dir = Path(f"services/{service_name}")
    service_dir.mkdir(parents=True, exist_ok=True)

    # Create service.json
    service = {
        "schema": "service_v1",
        "name": service_name,
        "display_name": service_data["display_name"],
        "description": service_data["description"],
        "service_type": "llm",
        "upstream_status": "ready",
        # ... map other fields
    }

    with open(service_dir / "service.json", "w") as f:
        json.dump(service, f, indent=2, sort_keys=True)
        f.write("\n")

    # Create listing.json
    listing = {
        "schema": "listing_v1",
        "seller_name": "svcreseller",
        "listing_status": "upstream_ready",
        # ... map other fields
    }

    with open(service_dir / f"listing-svcreseller.json", "w") as f:
        json.dump(listing, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Created service: {service_name}")

if __name__ == "__main__":
    services = fetch_services()
    for service_data in services:
        create_service_files(service_data)
    print(f"Generated {len(services)} services")
```

#### 4. Run Populate Command

```bash
# Generate all services
unitysvc_services populate

# Generate for specific provider only
unitysvc_services populate --provider my-provider

# Dry run to see what would execute
unitysvc_services populate --dry-run
```

#### 5. Validate and Format

```bash
unitysvc_services validate
unitysvc_services format
```

#### 6. Review Changes

```bash
git diff
git add data/
git commit -m "Update service catalog from API"
```

#### 7. Publish

```bash
cd data
unitysvc_services publish
```

#### 8. Verify

```bash
# Query with default fields
unitysvc_services query offerings

# Or query with custom fields
unitysvc_services query offerings --fields id,service_name,status
```

### Automation with CI/CD

Create `.github/workflows/update-services.yml`:

```yaml
name: Update Services

on:
    schedule:
        - cron: "0 0 * * *" # Daily at midnight
    workflow_dispatch:

jobs:
    update:
        runs-on: ubuntu-latest
        steps:
            - uses: actions/checkout@v3

            - name: Set up Python
              uses: actions/setup-python@v4
              with:
                  python-version: "3.11"

            - name: Install dependencies
              run: pip install unitysvc-services requests

            - name: Generate services
              run: unitysvc_services populate

            - name: Validate
              run: unitysvc_services validate

            - name: Format
              run: unitysvc_services format

            - name: Commit changes
              run: |
                  git config user.name "GitHub Actions"
                  git config user.email "actions@github.com"
                  git add data/
                  git diff --staged --quiet || git commit -m "Update services from API"
                  git push

            - name: Publish to UnitySVC
              env:
                  UNITYSVC_BASE_URL: ${{ secrets.UNITYSVC_BASE_URL }}
                  UNITYSVC_API_KEY: ${{ secrets.UNITYSVC_API_KEY }}
              run: |
                  unitysvc_services publish --data-path ./data
```

## Hybrid Workflow

Combine manual and automated approaches:

1. Use automated populate for most services
2. Manually create special/custom services
3. Use update commands to adjust individual services

```bash
# Generate bulk of services
unitysvc_services populate

# Manually create premium service
unitysvc_services init offering premium-service

# Update specific service
unitysvc_services update offering --name premium-service --status ready
```

## Publishing Order

**Recommended:** Use `unitysvc_services publish` without subcommands to publish all types automatically in the correct order:

1. **Sellers** - Must exist before listings
2. **Providers** - Must exist before offerings
3. **Service Offerings** - Links providers to services
4. **Service Listings** - Links sellers to offerings

The CLI handles this order automatically when you use `publish` without a subcommand. You can also publish specific types individually if needed (e.g., `unitysvc_services publish providers`).

Incorrect order will result in foreign key errors.

## Best Practices

### Version Control

-   Commit generated files to git
-   Review changes before publishing
-   Use meaningful commit messages
-   Tag releases

### Validation

-   Always run `validate` before `publish`
-   Fix all validation errors
-   Use `format --check` in CI to enforce formatting

### Environment Management

-   Use different API keys for dev/staging/prod
-   Store secrets in environment variables, not files

### Error Handling

-   Check exit codes in scripts
-   Log populate script output
-   Retry failed publishes with exponential backoff

### Documentation

-   Document custom populate scripts
-   Keep README.md updated with service catalog
-   Explain any special services or pricing

## Troubleshooting

### Populate Script Fails

-   Check API credentials in `provider_access_info`
-   Verify script has execute permissions
-   Test script manually: `python3 populate_services.py`

### Validation Errors After Populate

-   Check generated file formats
-   Verify all required fields are populated
-   Ensure file paths are relative

### Publishing Failures

-   Verify credentials are set
-   Check network connectivity
-   Use `unitysvc_services publish` to handle publishing order automatically
-   Look for foreign key constraint errors
-   Verify you're in the correct directory or using `--data-path`

## Next Steps

-   [CLI Reference](cli-reference.md) - Detailed command documentation
-   [Data Structure](data-structure.md) - File organization rules
-   [File Schemas](file-schemas.md) - Schema specifications
