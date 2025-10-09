# CLI Reference

Complete command-line interface reference for `unitysvc_services`.

## Global Options

```bash
unitysvc_services [OPTIONS] COMMAND [ARGS]...
```

### Options

-   `--install-completion` - Install shell completion
-   `--show-completion` - Show completion script
-   `--help` - Show help message

## Commands Overview

| Command    | Description                            |
| ---------- | -------------------------------------- |
| `init`     | Initialize new data files from schemas |
| `list`     | List data files in directory           |
| `query`    | Query backend API for data             |
| `publish`  | Publish data to backend                |
| `update`   | Update local data files                |
| `validate` | Validate data consistency              |
| `format`   | Format data files                      |
| `populate` | Execute provider populate scripts      |

## init - Initialize Data Files

Create new data file skeletons from schemas.

### init offering

Create a new service offering skeleton.

```bash
unitysvc_services init offering <name> [OPTIONS]
```

**Arguments:**

-   `<name>` - Name of the service offering (required)

**Options:**

-   `--format {json|toml}` - Output format (default: toml)
-   `--source PATH` - Source directory to copy from
-   `--output PATH` - Output directory (default: ./data)

**Examples:**

```bash
# Create TOML offering
unitysvc_services init offering my-service

# Create JSON offering
unitysvc_services init offering my-service --format json

# Copy from existing
unitysvc_services init offering new-service --source ./data/old-service
```

### init listing

Create a new service listing skeleton.

```bash
unitysvc_services init listing <name> [OPTIONS]
```

**Arguments:**

-   `<name>` - Name of the service listing (required)

**Options:**

-   `--format {json|toml}` - Output format (default: toml)
-   `--source PATH` - Source directory to copy from
-   `--output PATH` - Output directory (default: ./data)

### init provider

Create a new provider skeleton.

```bash
unitysvc_services init provider <name> [OPTIONS]
```

**Arguments:**

-   `<name>` - Provider name (required)

**Options:**

-   `--format {json|toml}` - Output format (default: toml)
-   `--source PATH` - Source directory to copy from
-   `--output PATH` - Output directory (default: ./data)

### init seller

Create a new seller skeleton.

```bash
unitysvc_services init seller <name> [OPTIONS]
```

**Arguments:**

-   `<name>` - Seller name (required)

**Options:**

-   `--format {json|toml}` - Output format (default: toml)
-   `--source PATH` - Source directory to copy from
-   `--output PATH` - Output directory (default: ./data)

## list - List Local Files

List data files in local directory.

### list providers

```bash
unitysvc_services list providers [DATA_DIR]
```

**Arguments:**

-   `[DATA_DIR]` - Data directory (default: current directory)

### list sellers

```bash
unitysvc_services list sellers [DATA_DIR]
```

### list offerings

```bash
unitysvc_services list offerings [DATA_DIR]
```

### list listings

```bash
unitysvc_services list listings [DATA_DIR]
```

**Output:**

-   Table format with file paths and key fields
-   Color-coded status indicators

## query - Query Backend

Query data from UnitySVC backend API.

All query commands support field selection to customize output columns and pagination options.

### query providers

```bash
unitysvc_services query providers [OPTIONS]
```

**Options:**

-   `--format, -f {table|json}` - Output format (default: table)
-   `--fields FIELDS` - Comma-separated list of fields to display (default: id,name,display_name,status)
-   `--skip SKIP` - Number of records to skip for pagination (default: 0)
-   `--limit LIMIT` - Maximum number of records to return (default: 100)

**Available Fields:**

id, name, display_name, contact_email, secondary_contact_email, homepage, description, status, created_at, updated_at

### query sellers

```bash
unitysvc_services query sellers [OPTIONS]
```

**Options:**

-   `--format, -f {table|json}` - Output format (default: table)
-   `--fields FIELDS` - Comma-separated list of fields to display (default: id,name,display_name,seller_type)
-   `--skip SKIP` - Number of records to skip for pagination (default: 0)
-   `--limit LIMIT` - Maximum number of records to return (default: 100)

**Available Fields:**

id, name, display_name, seller_type, contact_email, secondary_contact_email, homepage, description, business_registration, tax_id, account_manager_id, created_at, updated_at, status

### query offerings

```bash
unitysvc_services query offerings [OPTIONS]
```

**Options:**

-   `--format, -f {table|json}` - Output format (default: table)
-   `--fields FIELDS` - Comma-separated list of fields to display (default: id,service_name,service_type,provider_name,status)
-   `--skip SKIP` - Number of records to skip for pagination (default: 0)
-   `--limit LIMIT` - Maximum number of records to return (default: 100)

**Available Fields:**

id, definition_id, provider_id, status, price, service_name, service_type, provider_name

### query listings

```bash
unitysvc_services query listings [OPTIONS]
```

**Options:**

-   `--format, -f {table|json}` - Output format (default: table)
-   `--fields FIELDS` - Comma-separated list of fields to display (default: id,service_name,service_type,seller_name,listing_type,status)
-   `--skip SKIP` - Number of records to skip for pagination (default: 0)
-   `--limit LIMIT` - Maximum number of records to return (default: 100)

**Available Fields:**

id, offering_id, seller_id, status, created_at, updated_at, parameters_schema, parameters_ui_schema, tags, service_name, service_type, provider_name, seller_name, listing_type

**Required Environment Variables:**

-   `UNITYSVC_BASE_URL` - Backend API URL
-   `UNITYSVC_API_KEY` - API key for authentication

**Examples:**

```bash
# Table output with default fields
unitysvc_services query providers

# JSON output
unitysvc_services query offerings --format json

# Custom fields - show only specific columns
unitysvc_services query providers --fields id,name,contact_email

# Show all available fields for sellers
unitysvc_services query sellers --fields id,name,display_name,seller_type,contact_email,homepage,created_at,updated_at

# Custom fields for listings
unitysvc_services query listings --fields id,service_name,listing_type,status

# Retrieve more than 100 records
unitysvc_services query providers --limit 500

# Pagination: get second page of 100 records
unitysvc_services query offerings --skip 100 --limit 100

# Large dataset retrieval
unitysvc_services query listings --limit 1000

# Combine pagination with custom fields
unitysvc_services query sellers --skip 50 --limit 50 --fields id,name,contact_email
```

## publish - Publish to Backend

Publish local data files to UnitySVC backend.

**Default Behavior:** When called without a subcommand, publishes all data types in the correct order: sellers → providers → offerings → listings.

**Usage:**

```bash
# Publish all data types (default)
unitysvc_services publish [OPTIONS]

# Or publish specific data types
unitysvc_services publish COMMAND [OPTIONS]
```

**Common Options:**

-   `--data-path, -d PATH` - Data directory path (default: current directory)

**Required Environment Variables:**

-   `UNITYSVC_BASE_URL` - Backend API URL
-   `UNITYSVC_API_KEY` - API key for authentication

**Examples:**

```bash
# Publish all data from current directory
unitysvc_services publish

# Publish all data from custom directory
unitysvc_services publish --data-path ./data

# Publish only providers
unitysvc_services publish providers
```

**Publishing Order (when publishing all):**

1. Sellers - Must exist before listings
2. Providers - Must exist before offerings
3. Service Offerings - Must exist before listings
4. Service Listings - Depends on sellers, providers, and offerings

### publish providers

Publish only providers (ignoring other types).

```bash
unitysvc_services publish providers [OPTIONS]
```

**Options:**

-   `--data-path, -d PATH` - File or directory path (default: current directory)

**Examples:**

```bash
# Publish all providers in current directory
unitysvc_services publish providers

# Publish specific file
unitysvc_services publish providers --data-path ./data/my-provider/provider.json

# Publish from custom directory
unitysvc_services publish providers --data-path ./custom-data
```

### publish sellers

Publish only sellers (ignoring other types).

```bash
unitysvc_services publish sellers [OPTIONS]
```

**Options:**

-   `--data-path, -d PATH` - File or directory path (default: current directory)

### publish offerings

Publish only service offerings (ignoring other types).

```bash
unitysvc_services publish offerings [OPTIONS]
```

**Options:**

-   `--data-path, -d PATH` - File or directory path (default: current directory)

### publish listings

Publish only service listings (ignoring other types).

```bash
unitysvc_services publish listings [OPTIONS]
```

**Options:**

-   `--data-path, -d PATH` - File or directory path (default: current directory)

**Publishing Order:**

1. Providers (required first)
2. Sellers (required before listings)
3. Offerings (required before listings)
4. Listings (last)

## update - Update Local Files

Update fields in local data files.

### update offering

```bash
unitysvc_services update offering --name <name> [OPTIONS]
```

**Options:**

-   `--name, -n NAME` - Service offering name (required)
-   `--status, -s STATUS` - New upstream_status (uploading|ready|deprecated)
-   `--display-name NAME` - New display name
-   `--description TEXT` - New description
-   `--version VERSION` - New version
-   `--data-dir, -d PATH` - Data directory (default: current directory)

**Examples:**

```bash
# Update status
unitysvc_services update offering --name my-service --status ready

# Update multiple fields
unitysvc_services update offering --name my-service \
  --status ready \
  --display-name "My Updated Service" \
  --version "2.0"
```

### update listing

```bash
unitysvc_services update listing --service-name <name> [OPTIONS]
```

**Options:**

-   `--service-name, -n NAME` - Service name (required)
-   `--status, -s STATUS` - New listing_status
-   `--seller SELLER` - Filter by seller name
-   `--data-dir, -d PATH` - Data directory (default: current directory)

**Listing Status Values:**

-   `unknown` - Not yet determined
-   `upstream_ready` - Upstream ready
-   `downstream_ready` - Downstream ready
-   `ready` - Operationally ready
-   `in_service` - Currently in service
-   `upstream_deprecated` - Deprecated upstream
-   `deprecated` - No longer offered

**Examples:**

```bash
# Update listing status
unitysvc_services update listing --service-name my-service --status ready

# Update for specific seller
unitysvc_services update listing \
  --service-name my-service \
  --status in_service \
  --seller svcreseller
```

## validate - Validate Data

Validate data consistency and schema compliance.

```bash
unitysvc_services validate [DATA_DIR]
```

**Arguments:**

-   `[DATA_DIR]` - Data directory (default: current directory)

**Checks:**

-   Schema compliance
-   Service name uniqueness
-   Listing references
-   Provider/service name matching
-   File path validity
-   Seller uniqueness

**Examples:**

```bash
# Validate current directory
unitysvc_services validate

# Validate specific directory
unitysvc_services validate ./data
```

**Exit Codes:**

-   `0` - All validations passed
-   `1` - Validation errors found

## format - Format Files

Format data files to match pre-commit requirements.

```bash
unitysvc_services format [DATA_DIR] [OPTIONS]
```

**Arguments:**

-   `[DATA_DIR]` - Data directory (default: current directory)

**Options:**

-   `--check` - Check formatting without modifying files

**Actions:**

-   Format JSON with 2-space indentation
-   Remove trailing whitespace
-   Ensure single newline at end of file
-   Sort JSON keys

**Examples:**

```bash
# Format all files in current directory
unitysvc_services format

# Check formatting without changes
unitysvc_services format --check

# Format specific directory
unitysvc_services format ./data
```

**Exit Codes:**

-   `0` - All files formatted or already formatted
-   `1` - Formatting errors or files need formatting (with --check)

## populate - Generate Services

Execute provider populate scripts to auto-generate service data.

```bash
unitysvc_services populate [DATA_DIR] [OPTIONS]
```

**Arguments:**

-   `[DATA_DIR]` - Data directory (default: current directory)

**Options:**

-   `--provider, -p NAME` - Only populate specific provider
-   `--dry-run` - Show what would execute without running

**Requirements:**

-   Provider file must have `services_populator` configuration
-   Script specified in `services_populator.command`
-   Environment variables from `provider_access_info`

**Examples:**

```bash
# Run all populate scripts
unitysvc_services populate

# Run for specific provider
unitysvc_services populate --provider openai

# Dry run
unitysvc_services populate --dry-run
```

## Environment Variables

| Variable            | Description            | Used By        |
| ------------------- | ---------------------- | -------------- |
| `UNITYSVC_BASE_URL` | Backend API URL        | query, publish |
| `UNITYSVC_API_KEY`  | API authentication key | query, publish |

**Example:**

```bash
export UNITYSVC_BASE_URL=https://api.unitysvc.com/api/v1
export UNITYSVC_API_KEY=your-api-key

unitysvc_services validate
unitysvc_services publish providers
```

## Exit Codes

| Code | Meaning                           |
| ---- | --------------------------------- |
| 0    | Success                           |
| 1    | Error (validation, publish, etc.) |

## Shell Completion

### Install Completion

```bash
# Bash
unitysvc_services --install-completion bash

# Zsh
unitysvc_services --install-completion zsh

# Fish
unitysvc_services --install-completion fish
```

### Show Completion Script

```bash
unitysvc_services --show-completion
```

## Common Workflows

### Full Publish Flow

```bash
# Set environment
export UNITYSVC_BASE_URL=https://api.unitysvc.com/api/v1
export UNITYSVC_API_KEY=your-key

# Validate and format
unitysvc_services validate
unitysvc_services format

# Publish all (handles order automatically)
cd data
unitysvc_services publish

# Verify
unitysvc_services query offerings
```

### Update and Republish

```bash
# Update local file
unitysvc_services update offering --name my-service --status ready

# Validate
unitysvc_services validate

# Publish changes
unitysvc_services publish offerings
```

### Automated Generation

```bash
# Generate services
unitysvc_services populate

# Validate and format
unitysvc_services validate
unitysvc_services format

# Publish all
cd data
unitysvc_services publish
```

## See Also

-   [Getting Started](getting-started.md) - First steps tutorial
-   [Workflows](workflows.md) - Common usage patterns
-   [Data Structure](data-structure.md) - File organization rules
