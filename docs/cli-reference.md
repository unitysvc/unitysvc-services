# CLI Reference

Complete command-line interface reference for `unitysvc_services` (alias: `usvc`).

## Global Options

```bash
unitysvc_services [OPTIONS] COMMAND [ARGS]...
# Or using the shorter alias:
usvc [OPTIONS] COMMAND [ARGS]...
```

### Options

-   `--install-completion` - Install shell completion
-   `--show-completion` - Show completion script
-   `--help` - Show help message

**Note:** All examples below use the shorter `usvc` alias. You can always replace `usvc` with `unitysvc_services` if preferred.

## Commands Overview

| Command    | Description                                      |
| ---------- | ------------------------------------------------ |
| `init`     | Initialize new data files from schemas           |
| `list`     | List data files in directory                     |
| `query`    | Query backend API for data                       |
| `publish`  | Publish data to backend                          |
| `update`   | Update local data files                          |
| `validate` | Validate data consistency                        |
| `format`   | Format data files                                |
| `populate` | Execute provider populate scripts                |
| `test`     | Test code examples with upstream API credentials |

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
usvc init offering my-service

# Create JSON offering
usvc init offering my-service --format json

# Copy from existing
usvc init offering new-service --source ./data/old-service
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

**Examples:**

```bash
# List providers in current directory
usvc list providers

# List providers in specific directory
usvc list providers ./data
```

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

id, provider_id, status, price, service_name, service_type, provider_name

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
usvc query providers

# JSON output
usvc query offerings --format json

# Custom fields - show only specific columns
usvc query providers --fields id,name,contact_email

# Show all available fields for sellers
usvc query sellers --fields id,name,display_name,seller_type,contact_email,homepage,created_at,updated_at

# Custom fields for listings
usvc query listings --fields id,service_name,listing_type,status

# Retrieve more than 100 records
usvc query providers --limit 500

# Pagination: get second page of 100 records
usvc query offerings --skip 100 --limit 100

# Large dataset retrieval
usvc query listings --limit 1000

# Combine pagination with custom fields
usvc query sellers --skip 50 --limit 50 --fields id,name,contact_email
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
-   `--dryrun` - Preview what would be created/updated without making actual changes

**Required Environment Variables:**

-   `UNITYSVC_BASE_URL` - Backend API URL
-   `UNITYSVC_API_KEY` - API key for authentication

**Examples:**

```bash
# Publish all data from current directory
usvc publish

# Publish all data from custom directory
usvc publish --data-path ./data

# Publish only providers
usvc publish providers

# Preview changes before publishing (dryrun mode)
usvc publish --dryrun

# Preview specific type
usvc publish providers --dryrun
```

**Dryrun Mode:**

The `--dryrun` option allows you to preview what would happen during publish without making actual changes to the backend. This is useful for:

- Verifying which entities would be created vs updated
- Checking that all dependencies exist before publishing
- Confirming changes before committing them

In dryrun mode:
- No actual data is sent to the backend
- Backend returns what action would be taken (create/update)
- Missing dependencies are reported but don't cause errors
- Summary shows what would happen if published

**Dryrun Output Format:**

Dryrun mode displays a summary table showing what actions would be taken:

```bash
$ usvc publish --dryrun

Publishing Sellers...
╭──────────┬─────────┬─────────┬────────╮
│ Type     │ Created │ Updated │ Failed │
├──────────┼─────────┼─────────┼────────┤
│ Sellers  │ 1       │ 0       │        │
╰──────────┴─────────┴─────────┴────────╯

Publishing Providers...
╭───────────┬─────────┬─────────┬────────╮
│ Type      │ Created │ Updated │ Failed │
├───────────┼─────────┼─────────┼────────┤
│ Providers │ 2       │ 0       │        │
╰───────────┴─────────┴─────────┴────────╯

Publishing Offerings...
╭───────────┬─────────┬─────────┬────────╮
│ Type      │ Created │ Updated │ Failed │
├───────────┼─────────┼─────────┼────────┤
│ Offerings │ 5       │ 3       │        │
╰───────────┴─────────┴─────────┴────────╯

Publishing Listings...
╭──────────┬─────────┬─────────┬────────╮
│ Type     │ Created │ Updated │ Failed │
├──────────┼─────────┼─────────┼────────┤
│ Listings │ 8       │ 0       │        │
╰──────────┴─────────┴─────────┴────────╯

Summary
╭───────────┬─────────┬─────────┬────────╮
│ Type      │ Created │ Updated │ Failed │
├───────────┼─────────┼─────────┼────────┤
│ Sellers   │ 1       │ 0       │        │
│ Providers │ 2       │ 0       │        │
│ Offerings │ 5       │ 3       │        │
│ Listings  │ 8       │ 0       │        │
╰───────────┴─────────┴─────────┴────────╯
```

Notes:
- Created: Entities that would be created (don't exist on backend)
- Updated: Entities that would be updated (exist but have changes)
- Failed: Entities that encountered errors (shown in red if > 0, blank if 0)
- Blank cells indicate zero count for easier reading

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
-   `--dryrun` - Preview what would be created/updated without making actual changes

**Examples:**

```bash
# Publish all providers in current directory
usvc publish providers

# Publish specific file
usvc publish providers --data-path ./data/my-provider/provider.json

# Publish from custom directory
usvc publish providers --data-path ./custom-data

# Preview provider changes
usvc publish providers --dryrun
```

### publish sellers

Publish only sellers (ignoring other types).

```bash
unitysvc_services publish sellers [OPTIONS]
```

**Options:**

-   `--data-path, -d PATH` - File or directory path (default: current directory)
-   `--dryrun` - Preview what would be created/updated without making actual changes

### publish offerings

Publish only service offerings (ignoring other types).

```bash
unitysvc_services publish offerings [OPTIONS]
```

**Options:**

-   `--data-path, -d PATH` - File or directory path (default: current directory)
-   `--dryrun` - Preview what would be created/updated without making actual changes

### publish listings

Publish only service listings (ignoring other types).

```bash
unitysvc_services publish listings [OPTIONS]
```

**Options:**

-   `--data-path, -d PATH` - File or directory path (default: current directory)
-   `--dryrun` - Preview what would be created/updated without making actual changes

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
usvc update offering --name my-service --status ready

# Update multiple fields
usvc update offering --name my-service \
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
usvc update listing --service-name my-service --status ready

# Update for specific seller
usvc update listing \
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
usvc validate

# Validate specific directory
usvc validate ./data
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
usvc format

# Check formatting without changes
usvc format --check

# Format specific directory
usvc format ./data
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
usvc populate

# Run for specific provider
usvc populate --provider openai

# Dry run
usvc populate --dry-run
```

## test - Test Code Examples

Test code examples with upstream API credentials. This command discovers code examples from listing files and executes them with provider credentials.

**How it works:**

1. Scans for all listing files (schema: listing_v1)
2. Extracts code example documents (category = `code_examples`)
3. Loads provider credentials from provider files
4. Renders Jinja2 templates with listing, offering, provider, and seller data
5. Sets environment variables (API_KEY, API_ENDPOINT) from provider credentials
6. Executes code examples using appropriate interpreter (python3, node, bash)
7. Validates results based on exit code and optional `expect` field

### test list

List available code examples without running them.

```bash
unitysvc_services test list [DATA_DIR] [OPTIONS]
```

**Arguments:**

-   `[DATA_DIR]` - Data directory (default: current directory)

**Options:**

-   `--provider, -p NAME` - Only list code examples for a specific provider
-   `--services, -s PATTERNS` - Comma-separated list of service patterns (supports wildcards)

**Output:**

-   Table showing: Service name, Provider, Title, File type, Relative file path

**Examples:**

```bash
# List all code examples
usvc test list

# List for specific provider
usvc test list --provider fireworks

# List for specific services (with wildcards)
usvc test list --services "llama*,gpt-4*"

# List from custom directory
usvc test list ./data
```

### test run

Execute code examples and report results.

```bash
unitysvc_services test run [DATA_DIR] [OPTIONS]
```

**Arguments:**

-   `[DATA_DIR]` - Data directory (default: current directory)

**Options:**

-   `--provider, -p NAME` - Only test code examples for a specific provider
-   `--services, -s PATTERNS` - Comma-separated list of service patterns (supports wildcards)
-   `--verbose, -v` - Show detailed output including stdout/stderr from scripts

**Test Pass Criteria:**

-   Exit code is 0 AND
-   If `expect` field is defined in document: expected string found in stdout
-   If `expect` field is NOT defined: only exit code matters

**Failed Test Output:**

When a test fails, the rendered content is saved to the current directory:

-   Filename format: `failed_{service}_{title}{extension}`
-   Contains environment variables used (API_KEY, API_ENDPOINT)
-   Full rendered template content
-   Can be run directly to reproduce the issue

**Examples:**

```bash
# Test all code examples
usvc test run

# Test specific provider
usvc test run --provider fireworks

# Test specific services (with wildcards)
usvc test run --services "llama*,gpt-4*"

# Test single service
usvc test run --services "llama-3-1-405b-instruct"

# Combine filters
usvc test run --provider fireworks --services "llama*"

# Show detailed output
usvc test run --verbose
```

**Interpreter Detection:**

-   `.py` files: Uses `python3` (falls back to `python`)
-   `.js` files: Uses `node` (Node.js required)
-   `.sh` files: Uses `bash`
-   Other files: Checks shebang line for interpreter

**Exit Codes:**

-   `0` - All tests passed
-   `1` - One or more tests failed

See [Creating Code Examples](https://unitysvc-services.readthedocs.io/en/latest/code-examples/) for detailed guide on creating and debugging code examples.

## Environment Variables

| Variable            | Description            | Used By        |
| ------------------- | ---------------------- | -------------- |
| `UNITYSVC_BASE_URL` | Backend API URL        | query, publish |
| `UNITYSVC_API_KEY`  | API authentication key | query, publish |

**Example:**

```bash
export UNITYSVC_BASE_URL=https://api.unitysvc.com/api/v1
export UNITYSVC_API_KEY=your-api-key

usvc validate
usvc publish providers
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
usvc --install-completion bash

# Zsh
usvc --install-completion zsh

# Fish
usvc --install-completion fish
```

### Show Completion Script

```bash
usvc --show-completion
```

## Common Workflows

### Full Publish Flow

```bash
# Set environment
export UNITYSVC_BASE_URL=https://api.unitysvc.com/api/v1
export UNITYSVC_API_KEY=your-key

# Validate and format
usvc validate
usvc format

# Preview changes before publishing (recommended)
cd data
usvc publish --dryrun

# If preview looks good, publish all (handles order automatically)
usvc publish

# Verify
usvc query offerings
```

### Update and Republish

```bash
# Update local file
usvc update offering --name my-service --status ready

# Validate
usvc validate

# Preview changes
usvc publish offerings --dryrun

# Publish changes
usvc publish offerings
```

### Automated Generation

```bash
# Generate services
usvc populate

# Validate and format
usvc validate
usvc format

# Preview generated data
cd data
usvc publish --dryrun

# Publish all
usvc publish
```

## See Also

-   [Getting Started](getting-started.md) - First steps tutorial
-   [Workflows](workflows.md) - Common usage patterns
-   [Data Structure](data-structure.md) - File organization rules
-   [Documenting Service Listings](documenting-services.md) - Add documentation to services
-   [Creating Code Examples](code-examples.md) - Develop and test code examples
-   [API Reference](api-reference.md) - Python API documentation
