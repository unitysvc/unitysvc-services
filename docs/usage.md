# Usage

This guide covers common usage patterns for the UnitySVC Services SDK.

## Python API Usage

```python
import unitysvc_services
from unitysvc_services.publisher import ServiceDataPublisher
```

### Publishing Services Programmatically

```python
import asyncio
from pathlib import Path
from unitysvc_services.publisher import ServiceDataPublisher

async def publish_services():
    async with ServiceDataPublisher() as publisher:
        # Publish all services from a directory
        results = await publisher.publish_all_services(Path("./data"))

        print(f"Published {results['success']} services")
        print(f"Created: {results['created']}")
        print(f"Updated: {results['updated']}")
        print(f"Unchanged: {results['unchanged']}")

        if results['errors']:
            for error in results['errors']:
                print(f"Error: {error}")

asyncio.run(publish_services())
```

### Publishing a Single Service

```python
import asyncio
from pathlib import Path
from unitysvc_services.publisher import ServiceDataPublisher

async def publish_single_service():
    async with ServiceDataPublisher() as publisher:
        # Publish a single service from a listing file
        # The publisher automatically finds the offering and provider files
        listing_file = Path("./data/my-provider/services/my-service/listing.json")
        result = await publisher.post_service_async(listing_file)

        if result.get("skipped"):
            print(f"Skipped: {result['reason']}")
        else:
            print(f"Published: {result}")

asyncio.run(publish_single_service())
```

## CLI Usage

### Basic Workflow

```bash
# 1. Create data via web interface at unitysvc.com, then export
#    Or create files manually following the file schemas

# 2. Place files in the expected structure:
#    data/my-provider/provider.toml
#    data/my-provider/services/my-service/offering.toml
#    data/my-provider/services/my-service/listing.toml

# 3. Validate your data
usvc data validate

# 4. Format files for consistency (optional)
usvc data format

# 5. Set environment variables
export UNITYSVC_BASE_URL="https://api.unitysvc.com/v1"
export UNITYSVC_API_KEY="your-seller-api-key"

# 6. Preview what would be uploaded
usvc services upload --dryrun

# 7. Upload to the platform
usvc services upload

# 8. Verify uploaded data
usvc services list
```

### Understanding the Service Data Model

Services in UnitySVC consist of three data components:

| Component         | Schema        | Purpose                    |
| ----------------- | ------------- | -------------------------- |
| **Provider Data** | `provider_v1` | WHO provides the service   |
| **Offering Data** | `offering_v1` | WHAT is being provided     |
| **Listing Data**  | `listing_v1`  | HOW it's sold to customers |

These are organized separately but uploaded together:

```
data/
└── my-provider/
    ├── provider.toml          # Provider Data
    └── services/
        └── my-service/
            ├── offering.toml  # Offering Data
            └── listing.toml   # Listing Data ← upload entry point
```

### Upload Behavior

When you run `usvc services upload`:

1. Finds all listing files in the directory
2. For each listing, locates the offering in the same directory
3. Locates the provider in the parent directory
4. Uploads all three together atomically

### Multiple Listings

One offering can have multiple listings (e.g., different pricing tiers):

```
data/
└── my-provider/
    └── services/
        └── my-service/
            ├── offering.toml          # One offering
            ├── listing-basic.toml     # Basic tier listing
            ├── listing-premium.toml   # Premium tier listing
            └── listing-enterprise.toml # Enterprise tier listing
```

Each listing is uploaded as a separate service, but they all share the same provider and offering data.

### Dry Run Mode

Always preview changes before uploading:

```bash
usvc services upload --dryrun
```

This shows:

- Which services would be created (new)
- Which services would be updated (changed)
- Which services are unchanged
- Any errors or missing files

### Listing Uploaded Services

```bash
# List your services
usvc services list

# List services with specific fields
usvc services list --fields id,name,status

# Filter by status
usvc services list --status active

# Output as JSON
usvc services list --format json
```

## Environment Variables

| Variable            | Description                                           |
| ------------------- | ----------------------------------------------------- |
| `UNITYSVC_BASE_URL` | Backend API URL (e.g., `https://api.unitysvc.com/v1`) |
| `UNITYSVC_API_KEY`  | Your seller API key for authentication                |

## Next Steps

- [Data Structure](data-structure.md) - Learn about file organization
- [CLI Reference](cli-reference.md) - Complete command documentation
- [Workflows](workflows.md) - Manual and automated workflows
- [API Reference](api-reference.md) - Python API documentation
