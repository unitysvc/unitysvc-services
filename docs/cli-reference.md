# CLI Reference

Complete command-line interface reference for `unitysvc_services`.

## Global Options

```bash
unitysvc_services [OPTIONS] COMMAND [ARGS]...
```

### Options
- `--install-completion` - Install shell completion
- `--show-completion` - Show completion script
- `--help` - Show help message

## Commands Overview

| Command | Description |
|---------|-------------|
| `init` | Initialize new data files from schemas |
| `list` | List data files in directory |
| `query` | Query backend API for data |
| `publish` | Publish data to backend |
| `update` | Update local data files |
| `validate` | Validate data consistency |
| `format` | Format data files |
| `populate` | Execute provider populate scripts |

## init - Initialize Data Files

Create new data file skeletons from schemas.

### init offering

Create a new service offering skeleton.

```bash
unitysvc_services init offering <name> [OPTIONS]
```

**Arguments:**
- `<name>` - Name of the service offering (required)

**Options:**
- `--format {json|toml}` - Output format (default: toml)
- `--source PATH` - Source directory to copy from
- `--output PATH` - Output directory (default: ./data)

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
- `<name>` - Name of the service listing (required)

**Options:**
- `--format {json|toml}` - Output format (default: toml)
- `--source PATH` - Source directory to copy from
- `--output PATH` - Output directory (default: ./data)

### init provider

Create a new provider skeleton.

```bash
unitysvc_services init provider <name> [OPTIONS]
```

**Arguments:**
- `<name>` - Provider name (required)

**Options:**
- `--format {json|toml}` - Output format (default: toml)
- `--source PATH` - Source directory to copy from
- `--output PATH` - Output directory (default: ./data)

### init seller

Create a new seller skeleton.

```bash
unitysvc_services init seller <name> [OPTIONS]
```

**Arguments:**
- `<name>` - Seller name (required)

**Options:**
- `--format {json|toml}` - Output format (default: toml)
- `--source PATH` - Source directory to copy from
- `--output PATH` - Output directory (default: ./data)

## list - List Local Files

List data files in local directory.

### list providers

```bash
unitysvc_services list providers [DATA_DIR]
```

**Arguments:**
- `[DATA_DIR]` - Data directory (default: ./data or $UNITYSVC_DATA_DIR)

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
- Table format with file paths and key fields
- Color-coded status indicators

## query - Query Backend

Query data from UnitySVC backend API.

### query providers

```bash
unitysvc_services query providers [OPTIONS]
```

**Options:**
- `--backend-url, -u URL` - Backend URL (or $UNITYSVC_BACKEND_URL)
- `--api-key, -k KEY` - API key (or $UNITYSVC_API_KEY)
- `--format, -f {table|json}` - Output format (default: table)

### query sellers

```bash
unitysvc_services query sellers [OPTIONS]
```

### query offerings

```bash
unitysvc_services query offerings [OPTIONS]
```

### query listings

```bash
unitysvc_services query listings [OPTIONS]
```

### query interfaces

```bash
unitysvc_services query interfaces [OPTIONS]
```

Query access interfaces (private endpoint).

### query documents

```bash
unitysvc_services query documents [OPTIONS]
```

Query documents (private endpoint).

**Examples:**
```bash
# Table output
unitysvc_services query providers

# JSON output
unitysvc_services query offerings --format json

# With explicit credentials
unitysvc_services query listings \
  --backend-url https://api.unitysvc.com/api/v1 \
  --api-key your-key
```

## publish - Publish to Backend

Publish local data files to UnitySVC backend.

### publish providers

```bash
unitysvc_services publish providers [DATA_PATH] [OPTIONS]
```

**Arguments:**
- `[DATA_PATH]` - File or directory path (default: ./data or $UNITYSVC_DATA_DIR)

**Options:**
- `--backend-url, -u URL` - Backend URL (or $UNITYSVC_BACKEND_URL)
- `--api-key, -k KEY` - API key (or $UNITYSVC_API_KEY)

**Examples:**
```bash
# Publish all providers in ./data
unitysvc_services publish providers

# Publish specific file
unitysvc_services publish providers ./data/my-provider/provider.json

# Publish from custom directory
unitysvc_services publish providers ./custom-data
```

### publish sellers

```bash
unitysvc_services publish sellers [DATA_PATH] [OPTIONS]
```

### publish offerings

```bash
unitysvc_services publish offerings [DATA_PATH] [OPTIONS]
```

### publish listings

```bash
unitysvc_services publish listings [DATA_PATH] [OPTIONS]
```

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
- `--name, -n NAME` - Service offering name (required)
- `--status, -s STATUS` - New upstream_status (uploading|ready|deprecated)
- `--display-name NAME` - New display name
- `--description TEXT` - New description
- `--version VERSION` - New version
- `--data-dir, -d PATH` - Data directory (default: ./data)

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
- `--service-name, -n NAME` - Service name (required)
- `--status, -s STATUS` - New listing_status
- `--seller SELLER` - Filter by seller name
- `--data-dir, -d PATH` - Data directory (default: ./data)

**Listing Status Values:**
- `unknown` - Not yet determined
- `upstream_ready` - Upstream ready
- `downstream_ready` - Downstream ready
- `ready` - Operationally ready
- `in_service` - Currently in service
- `upstream_deprecated` - Deprecated upstream
- `deprecated` - No longer offered

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
- `[DATA_DIR]` - Data directory (default: ./data or $UNITYSVC_DATA_DIR)

**Checks:**
- Schema compliance
- Service name uniqueness
- Listing references
- Provider/service name matching
- File path validity
- Seller uniqueness

**Examples:**
```bash
# Validate ./data
unitysvc_services validate

# Validate specific directory
unitysvc_services validate ./my-data

# Using environment variable
export UNITYSVC_DATA_DIR=/path/to/data
unitysvc_services validate
```

**Exit Codes:**
- `0` - All validations passed
- `1` - Validation errors found

## format - Format Files

Format data files to match pre-commit requirements.

```bash
unitysvc_services format [DATA_DIR] [OPTIONS]
```

**Arguments:**
- `[DATA_DIR]` - Data directory (default: ./data or $UNITYSVC_DATA_DIR)

**Options:**
- `--check` - Check formatting without modifying files

**Actions:**
- Format JSON with 2-space indentation
- Remove trailing whitespace
- Ensure single newline at end of file
- Sort JSON keys

**Examples:**
```bash
# Format all files
unitysvc_services format

# Check formatting without changes
unitysvc_services format --check

# Format specific directory
unitysvc_services format ./my-data
```

**Exit Codes:**
- `0` - All files formatted or already formatted
- `1` - Formatting errors or files need formatting (with --check)

## populate - Generate Services

Execute provider populate scripts to auto-generate service data.

```bash
unitysvc_services populate [DATA_DIR] [OPTIONS]
```

**Arguments:**
- `[DATA_DIR]` - Data directory (default: ./data or $UNITYSVC_DATA_DIR)

**Options:**
- `--provider, -p NAME` - Only populate specific provider
- `--dry-run` - Show what would execute without running

**Requirements:**
- Provider file must have `services_populator` configuration
- Script specified in `services_populator.command`
- Environment variables from `provider_access_info`

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

| Variable | Description | Used By |
|----------|-------------|---------|
| `UNITYSVC_DATA_DIR` | Default data directory | All file commands |
| `UNITYSVC_BACKEND_URL` | Backend API URL | query, publish |
| `UNITYSVC_API_KEY` | API authentication key | query, publish |

**Example:**
```bash
export UNITYSVC_DATA_DIR=/path/to/data
export UNITYSVC_BACKEND_URL=https://api.unitysvc.com/api/v1
export UNITYSVC_API_KEY=your-api-key

unitysvc_services validate
unitysvc_services publish providers
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (validation, publish, etc.) |

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
export UNITYSVC_BACKEND_URL=https://api.unitysvc.com/api/v1
export UNITYSVC_API_KEY=your-key

# Validate and format
unitysvc_services validate
unitysvc_services format

# Publish in order
unitysvc_services publish providers
unitysvc_services publish sellers
unitysvc_services publish offerings
unitysvc_services publish listings

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

# Publish
unitysvc_services publish offerings
unitysvc_services publish listings
```

## See Also

- [Getting Started](getting-started.md) - First steps tutorial
- [Workflows](workflows.md) - Common usage patterns
- [Data Structure](data-structure.md) - File organization rules
