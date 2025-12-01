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

| Command     | Description                                      |
| ----------- | ------------------------------------------------ |
| `init`      | Initialize new data files from schemas           |
| `list`      | List data files in directory                     |
| `query`     | Query backend API for data                       |
| `publish`   | Publish data to backend                          |
| `unpublish` | Unpublish (delete) data from backend             |
| `update`    | Update local data files                          |
| `validate`  | Validate data consistency                        |
| `format`    | Format data files                                |
| `populate`  | Execute provider populate scripts                |
| `test`      | Test code examples with upstream API credentials |

## init - Initialize Data Files

Create new data files through **interactive prompts** or by **copying from existing data**.

All `init` commands support two modes:

1. **Interactive Mode** (default): Prompts you step-by-step for field values with validation and smart defaults
2. **Copy Mode**: Uses `--source` to copy structure from an existing directory

### Key Features

**Interactive Mode Features:**

-   ✅ **Auto-discovery**: Automatically detects seller and service names from existing files
-   ✅ **Validation**: Email format, URI validation, integer checks, and more
-   ✅ **Smart defaults**: Computed defaults based on previous inputs or filesystem discovery
-   ✅ **Skip optional fields**: Press Enter to skip any optional field
-   ✅ **Complex objects**: Add documents and pricing information interactively
-   ✅ **File validation**: Checks document file paths exist before saving
-   ✅ **Cancellation**: Press Ctrl+C to cancel at any time

### init seller

Create a new seller file interactively or copy from existing.

```bash
usvc init seller <name> [OPTIONS]
```

**Arguments:**

-   `<name>` - Seller identifier (URL-friendly name)

**Options:**

-   `--format {json|toml}` - Output format (default: json)
-   `--source PATH` - Copy from existing seller directory (skips interactive prompts)
-   `--output-dir PATH` - Output directory (default: ./data)

**Interactive Mode** prompts for:

-   **Basic Information**: seller type (individual/organization/partnership/corporation), display name, description
-   **Contact Information**: primary email, secondary email, homepage URL
-   **Additional Details**: business registration, tax ID, account manager
-   **Status & Verification**: status (active/pending/disabled), KYC verification

**Examples:**

```bash
# Interactive mode - will prompt for all fields
usvc init seller acme-corp

# Interactive mode with JSON format
usvc init seller acme-corp --format json

# Copy from existing seller
usvc init seller new-seller --source ./data/acme-corp
```

### init provider

Create a new provider file interactively or copy from existing.

```bash
usvc init provider <name> [OPTIONS]
```

**Arguments:**

-   `<name>` - Provider identifier (e.g., 'openai', 'fireworks')

**Options:**

-   `--format {json|toml}` - Output format (default: json)
-   `--source PATH` - Copy from existing provider directory
-   `--output-dir PATH` - Output directory (default: ./data)

**Interactive Mode** prompts for:

-   **Basic Information**: display name, description
-   **Contact & Web**: contact email, secondary email, homepage URL
-   **Provider Access**: API endpoint, API key, access method (http/websocket/grpc)
-   **Status**: provider status
-   **Service Population** (optional): Command to auto-generate service offerings via `usvc populate`

**Examples:**

```bash
# Interactive mode
usvc init provider openai

# Copy mode
usvc init provider new-provider --source ./data/openai
```

**Auto-Population Feature:**

If you enable the services populator, you can create a script that automatically generates service offerings:

```bash
# During init, answer "yes" to "Enable automated service population?"
# Provide command: python scripts/populate_openai.py

# Later, run populate to generate services
usvc populate
```

### init offering

Create a new service offering file interactively or copy from existing.

```bash
usvc init offering <name> [OPTIONS]
```

**Arguments:**

-   `<name>` - Service name (e.g., 'gpt-4', 'llama-3-1-405b')

**Options:**

-   `--format {json|toml}` - Output format (default: json)
-   `--source PATH` - Copy from existing offering directory
-   `--output-dir PATH` - Output directory (default: ./data)

**Interactive Mode** prompts for:

-   **Basic Information**: service name, display name, version, description
-   **Classification**: service type (llm/embedding/vision/audio/image/video), upstream status
-   **Upstream Access Interface**: API endpoint, API key, documents (optional)
-   **Upstream Pricing** (optional): pricing type, currency, price structure
-   **Additional Information**: tagline

**Pricing Types:**

-   `one_million_tokens` - Per million tokens (LLMs)
-   `one_second` - Per second of usage (audio/video)
-   `image` - Per image generated
-   `step` - Per step/iteration
-   `revenue_share` - Percentage of customer charge (seller only)

**Pricing Structures:**

When adding pricing, you can choose from three structures:

1. **Simple**: `{"type": "one_million_tokens", "price": "10.00"}`
2. **Input/Output** (for LLMs): `{"type": "one_million_tokens", "input": "5.00", "output": "15.00"}`
3. **Custom JSON**: any structure with required "type" field

**Examples:**

```bash
# Interactive mode - will create data/gpt-4/service.json
usvc init offering gpt-4

# Interactive with TOML format
usvc init offering gpt-4 --format toml

# Copy from existing offering
usvc init offering gpt-4-turbo --source ./data/gpt-4
```

### init listing

Create a new service listing file interactively or copy from existing.

```bash
usvc init listing <name> [OPTIONS]
```

**Arguments:**

-   `<name>` - Listing identifier

**Options:**

-   `--format {json|toml}` - Output format (default: json)
-   `--source PATH` - Copy from existing listing directory
-   `--output-dir PATH` - Output directory (default: ./data)

**Interactive Mode** prompts for:

-   **Basic Information**: service name (auto-detected), listing name, display name
-   **Seller Information**: seller name (auto-detected from seller.json)
-   **Status**: listing status (draft/ready/deprecated)
-   **Documents** (optional): Add multiple documents interactively

**Auto-Discovery:**

The listing workflow automatically discovers:

-   **seller_name**: Searches ./data, ./, ../data, ../ for seller.json/seller.toml
-   **service_name**: Searches ./, ../ for service.json/service.toml

This means you don't need to manually type names - they're auto-filled!

**Document Support:**

When adding documents, you can specify:

-   **Required**: title, MIME type, category
-   **Optional**: description, file path (relative to listing dir), external URL, public flag
-   **Validation**: File existence checks, at least one of file_path or external_URL required

**Examples:**

```bash
# Interactive mode from project root
usvc init listing premium-gpt4
# Auto-detects seller from ./data/seller.json

# From inside service directory
cd data/my-provider/gpt-4
usvc init listing standard
# Auto-detects service from ./service.json and seller from ../../data/seller.json

# Copy mode
usvc init listing new-listing --source ./data/old-listing
```

### Important Notes

**The `init` command provides a starting point but does not handle all fields and validate all input values.**

The interactive mode and copy mode are designed to:

-   Generate basic file structure according to the schema
-   Populate fields with reasonable default values
-   Validate common field formats (emails, URLs, etc.)
-   Ensure required fields are populated

However, **users are expected to manually review and modify the generated spec files** to ensure:

-   Business logic correctness (pricing, terms, policies)
-   Accurate service descriptions and metadata
-   Proper document references and paths
-   Compliance with organizational standards
-   Semantic correctness beyond schema validation

Always run `usvc validate` after manual modifications and before publishing to production.

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

-   Verifying which entities would be created vs updated
-   Checking that all dependencies exist before publishing
-   Confirming changes before committing them

In dryrun mode:

-   No actual data is sent to the backend
-   Backend returns what action would be taken (create/update)
-   Missing dependencies are reported but don't cause errors
-   Summary shows what would happen if published

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

-   Created: Entities that would be created (don't exist on backend)
-   Updated: Entities that would be updated (exist but have changes)
-   Failed: Entities that encountered errors (shown in red if > 0, blank if 0)
-   Blank cells indicate zero count for easier reading

**Publishing Order (when publishing all):**

1. Sellers - Must exist before listings
2. Providers - Must exist before offerings
3. Service Offerings - Must exist before listings
4. Service Listings - Depends on sellers, providers, and offerings

## unpublish - Unpublish from Backend

Unpublish (delete) data from UnitySVC backend. This command provides granular control over removing offerings, listings, providers, and sellers.

**⚠️ IMPORTANT CASCADE BEHAVIOR:**

-   **Deleting a seller** will automatically delete ALL associated listings from that seller (across all providers and offerings)
-   **Deleting a provider** will automatically delete ALL associated offerings AND listings from that provider
-   **Deleting an offering** will automatically delete ALL associated listings for that offering
-   **Deleting a listing** only removes that specific listing

By default, deletion is blocked if there are active subscriptions. Use `--force` to override this protection.

**Common Options:**

-   `--dryrun` - Preview what would be deleted without actually deleting
-   `--force` - Force deletion even with active subscriptions
-   `--yes, -y` - Skip confirmation prompt

**Required Environment Variables:**

-   `UNITYSVC_BASE_URL` - Backend API URL
-   `UNITYSVC_API_KEY` - API key for authentication

### unpublish offerings

Unpublish (delete) service offerings from backend.

**⚠️ CASCADE WARNING:** Deleting an offering will also delete ALL associated listings and subscriptions.

```bash
unitysvc_services unpublish offerings [DATA_DIR] [OPTIONS]
```

**Arguments:**

-   `[DATA_DIR]` - Directory containing offering files (default: current directory)

**Options:**

-   `--services, -s NAMES` - Comma-separated list of service names to unpublish
-   `--provider, -p NAME` - Unpublish offerings from specific provider
-   `--dryrun` - Show what would be deleted without actually deleting
-   `--force` - Force deletion even with active subscriptions
-   `--yes, -y` - Skip confirmation prompt

**Examples:**

```bash
# Dry-run to see what would be deleted
usvc unpublish offerings --services "gpt-4" --dryrun

# Delete specific offering
usvc unpublish offerings --services "gpt-4"

# Delete multiple offerings
usvc unpublish offerings --services "gpt-4,gpt-3.5-turbo"

# Delete all offerings from a provider
usvc unpublish offerings --provider openai

# Force delete (ignore active subscriptions)
usvc unpublish offerings --services "gpt-4" --force --yes
```

**Output:**

Shows a table of offerings to be deleted, including service name, provider, and offering ID. After deletion, displays cascade information (how many listings and subscriptions were also deleted).

### unpublish listings

Unpublish (delete) a specific service listing from backend.

```bash
unitysvc_services unpublish listings <listing-id> [OPTIONS]
```

**Arguments:**

-   `<listing-id>` - UUID of the listing to unpublish (required)

**Options:**

-   `--dryrun` - Show what would be deleted without actually deleting
-   `--force` - Force deletion even with active subscriptions
-   `--yes, -y` - Skip confirmation prompt

**Examples:**

```bash
# Dry-run
usvc unpublish listings abc-123-def-456 --dryrun

# Delete listing
usvc unpublish listings abc-123-def-456

# Force delete without confirmation
usvc unpublish listings abc-123-def-456 --force --yes
```

**Output:**

Shows deletion confirmation and number of subscriptions deleted (if any).

### unpublish providers

Unpublish (delete) a provider from backend.

**⚠️ CASCADE WARNING:** Deleting a provider will delete the provider AND ALL associated offerings, listings, and subscriptions.

```bash
unitysvc_services unpublish providers <provider-name> [OPTIONS]
```

**Arguments:**

-   `<provider-name>` - Name of the provider to unpublish (required)

**Options:**

-   `--dryrun` - Show what would be deleted without actually deleting
-   `--force` - Force deletion even with active subscriptions
-   `--yes, -y` - Skip confirmation prompt

**Examples:**

```bash
# Dry-run to see impact
usvc unpublish providers openai --dryrun

# Delete provider and all its offerings/listings
usvc unpublish providers openai

# Force delete without confirmation
usvc unpublish providers openai --force --yes
```

**Output:**

Shows deletion summary including counts of:

-   Offerings deleted
-   Listings deleted
-   Subscriptions deleted

### unpublish sellers

Unpublish (delete) a seller from backend.

**⚠️ CASCADE WARNING:** Deleting a seller will delete the seller AND ALL associated listings and subscriptions. Note that this does NOT delete providers or offerings (which can be resold by other sellers), only the listings tied to this specific seller.

```bash
unitysvc_services unpublish sellers <seller-name> [OPTIONS]
```

**Arguments:**

-   `<seller-name>` - Name of the seller to unpublish (required)

**Options:**

-   `--dryrun` - Show what would be deleted without actually deleting
-   `--force` - Force deletion even with active subscriptions
-   `--yes, -y` - Skip confirmation prompt

**Examples:**

```bash
# Dry-run to see impact
usvc unpublish sellers my-company --dryrun

# Delete seller and all its listings
usvc unpublish sellers my-company

# Force delete without confirmation
usvc unpublish sellers my-company --force --yes
```

**Output:**

Shows deletion summary including counts of:

-   Providers deleted (if seller owns providers)
-   Offerings deleted (if seller owns providers with offerings)
-   Listings deleted
-   Subscriptions deleted

**Important Notes:**

-   Always use `--dryrun` first to preview the impact before actual deletion
-   Cascade deletions are permanent and cannot be undone
-   Active subscriptions will block deletion unless `--force` is used
-   Use `--yes` flag in automated scripts to skip interactive confirmation

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
unitysvc_services update listing --services <name> [OPTIONS]
```

**Options:**

-   `--services, -n NAME` - Service name (required)
-   `--status, -s STATUS` - New listing_status
-   `--seller SELLER` - Filter by seller name
-   `--data-dir, -d PATH` - Data directory (default: current directory)

**Listing Status Values:**

Seller-accessible statuses (can be set via CLI):

-   `draft` - Listing is being worked on, skipped during publish (won't be sent to backend)
-   `ready` - Listing is complete and ready for admin review/testing
-   `deprecated` - Seller marks service as retired/replaced

Note: Admin-managed workflow statuses (upstream_ready, downstream_ready, in_service) are set by the backend admin after testing and validation, not through the CLI tool.

**Examples:**

```bash
# Update listing status
usvc update listing --services my-service --status ready

# Update for specific seller
usvc update listing \
  --services my-service \
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
5. Sets environment variables (API_KEY, BASE_URL) from provider credentials
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
-   `--test-file, -t FILENAME` - Only run a specific test file by filename (e.g., 'code-example.py.j2')
-   `--verbose, -v` - Show detailed output including stdout/stderr from scripts
-   `--force, -f` - Force rerun all tests, ignoring existing .out and .err files
-   `--fail-fast, -x` - Stop testing on first failure

\*\*Test Pass Criteria:

-   Exit code is 0 AND
-   If `expect` field is defined in document: expected string found in stdout
-   If `expect` field is NOT defined: only exit code matters

**Test Result Caching:**

By default, successful test results are cached to avoid re-running tests unnecessarily:

-   When a test passes, `.out` and `.err` files are saved in the same directory as the listing file
-   On subsequent runs, tests with existing result files are skipped
-   Use `--force` to ignore cached results and re-run all tests
-   Failed tests are always re-run (their output goes to current directory with `failed_` prefix)

**Failed Test Output:**

When a test fails, the rendered content is saved to the current directory:

-   Filename format: `failed_{service}_{listing}_{filename}.{out|err|extension}`
-   `.out` file: stdout from the test
-   `.err` file: stderr from the test
-   Script file: Full rendered template content with environment variables
-   Can be run directly to reproduce the issue

**Successful Test Output:**

When a test passes, output files are saved in the listing directory:

-   Filename format: `{service}_{listing}_{filename}.{out|err}`
-   Saved alongside the listing definition file
-   Used to skip re-running tests unless `--force` is specified

\*\*Examples:

```bash
# Test all code examples
usvc test run

# Test specific provider
usvc test run --provider fireworks

# Test specific services (with wildcards)
usvc test run --services "llama*,gpt-4*"

# Test single service
usvc test run --services "llama-3-1-405b-instruct"

# Test specific file
usvc test run --test-file "code-example.py.j2"

# Combine filters
usvc test run --provider fireworks --services "llama*"

# Show detailed output
usvc test run --verbose

# Force rerun all tests (ignore cached results)
usvc test run --force

# Stop on first failure (useful for quick feedback)
usvc test run --fail-fast

# Combine options
usvc test run --force --fail-fast --verbose
usvc test run -f -x -v  # Short form
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

### Creating Data from Scratch (Interactive)

Create a complete data structure interactively:

```bash
# 1. Create seller (will prompt for contact info, etc.)
usvc init seller acme-corp
# Follow prompts: enter email, homepage, etc.

# 2. Create provider (will prompt for API endpoint, etc.)
cd data/acme-corp
usvc init provider openai
# Follow prompts: API endpoint, contact, optional services_populator

# 3. Create service offering (will prompt for service details)
cd openai
usvc init offering gpt-4
# Follow prompts: description, upstream API, optional pricing

# 4. Create listing (auto-detects seller and service!)
cd gpt-4
usvc init listing standard
# Auto-fills seller from data/seller.json and service from service.json
# Add optional documents

# 5. Validate everything
cd ../../../..  # Back to project root
usvc validate

# 6. Format files
usvc format

# 7. Preview before publishing
cd data
usvc publish --dryrun

# 8. Publish if everything looks good
usvc publish
```

**Note**: The interactive prompts include:

-   ✅ Auto-discovery of seller/service names
-   ✅ Validation of emails, URLs, and required fields
-   ✅ Smart defaults (e.g., display name from ID)
-   ✅ Optional document and pricing support

### Copying from Existing Data

Quickly create new data by copying from existing structures:

```bash
# Copy an existing service offering to create a similar one
usvc init offering gpt-4-turbo --source ./data/acme-corp/openai/gpt-4

# Copy a listing
usvc init listing premium --source ./data/acme-corp/openai/gpt-4/standard

# Copy a provider
usvc init provider anthropic --source ./data/acme-corp/openai

# Copy a seller
usvc init seller new-seller --source ./data/acme-corp
```

**Benefits of copy mode:**

-   🚀 Skip interactive prompts for similar services
-   📋 Preserves structure and documents
-   ⚡ Faster than manual entry for bulk creation
-   🔄 Updates names and IDs automatically

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
