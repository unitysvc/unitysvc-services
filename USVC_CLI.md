# USVC CLI Design

## Design Principles

1. **Workflow-aligned**: Commands follow the natural workflow: prepare → test → deploy → maintain
2. **Discoverable**: Related commands grouped under common nouns for easy discovery via `--help`
3. **Concise**: Frequent operations have short paths; less frequent operations can be longer
4. **Consistent**: Similar operations use similar patterns

## Recommended Structure

### Overview

```
usvc
├── data                  # Local data operations (offline, no API key needed)
│   ├── validate          # Validate data files against schemas
│   ├── format            # Format/prettify data files
│   ├── populate          # Generate/populate data files
│   ├── list              # List local data files by type
│   ├── show              # Show contents of a data file
│   ├── list-tests        # List code examples in local data
│   ├── run-tests          # Run code examples locally (upstream credentials)
│   └── show-test         # Show details of a local test
│
└── services              # Remote service operations (requires API key)
    ├── upload            # Upload/sync to backend
    ├── list              # List deployed services
    ├── show              # Show service details
    ├── submit            # Submit for ops review
    ├── deprecate         # Deprecate a service
    ├── delete            # Delete a service
    ├── list-tests        # List tests for deployed services
    ├── show-test         # Show details of a test
    ├── run-tests          # Run tests via gateway (backend execution)
    ├── skip-test         # Mark a test as skipped
    └── unskip-test       # Remove skip status from a test
```

**Key distinction:**
- `usvc data` commands work with **local files** and can be used offline. They test code examples using upstream API credentials from offering files.
- `usvc services` commands interact with the **backend API** and can be run from anywhere with the right API key. They manage deployed services and run tests via the gateway.

### Detailed Command Reference

---

## Local Data Operations (`usvc data`)

Commands for preparing, validating, and testing local data files before upload.

### `usvc data validate`

Validate data files against schemas.

```bash
usvc data validate [DATA_DIR]

Options:
  --schema, -s TEXT    Only validate files matching schema (provider_v1, offering_v1, listing_v1, seller_v1)
  --strict             Fail on warnings
```

Examples:
```bash
usvc data validate                      # Validate all files in current directory
usvc data validate ./data               # Validate specific directory
usvc data validate --schema listing_v1  # Only validate listing files
```

### `usvc data format`

Format data files (JSON, TOML) to match style requirements.

```bash
usvc data format [DATA_DIR]

Options:
  --check              Check formatting without modifying files
  --include TEXT       Only format files matching pattern
```

Examples:
```bash
usvc data format                        # Format all files in current directory
usvc data format --check                # Check without modifying
usvc data format --include "*.json"     # Only JSON files
```

### `usvc data populate`

Generate/populate data files from templates or external sources.

```bash
usvc data populate [DATA_DIR]

Options:
  --provider, -p TEXT  Only populate for specific provider
  --force, -f          Overwrite existing files
```

Examples:
```bash
usvc data populate                      # Populate all providers
usvc data populate --provider fireworks # Specific provider only
```

### `usvc data list`

List local data files by type.

```bash
usvc data list [TYPE] [DATA_DIR]

Arguments:
  TYPE                 File type: providers, offerings, listings, sellers, examples, all (default: all)

Options:
  --format, -f TEXT    Output format: table, json, tsv, csv (default: table)
```

Examples:
```bash
usvc data list                          # List all data files
usvc data list providers                # List only provider files
usvc data list examples                 # List code examples
usvc data list listings ./data          # List listings in specific directory
```

### `usvc data show`

Show contents of a specific data file.

```bash
usvc data show <FILE_PATH>

Options:
  --format, -f TEXT    Output format: json, table, tsv, csv (default: json)
  --resolve            Resolve file references and show expanded content
```

Examples:
```bash
usvc data show ./data/fireworks/provider.json
usvc data show ./listing.json --resolve
```

### `usvc data list-tests`

List code examples in local data files without running them.

```bash
usvc data list-tests [DATA_DIR]

Options:
  --provider, -p TEXT   Filter by provider
  --services, -s TEXT   Filter by service patterns (supports wildcards)
```

Examples:
```bash
usvc data list-tests                          # List all code examples
usvc data list-tests --provider fireworks     # List for specific provider
usvc data list-tests --services "llama*"      # List matching services
```

### `usvc data run-tests`

Run code examples locally using upstream API credentials from offering files.
Validates that the examples themselves work correctly with the upstream provider.

```bash
usvc data run-tests [DATA_DIR]

Options:
  --provider, -p TEXT   Filter by provider
  --services, -s TEXT   Filter by service patterns (supports wildcards)
  --test-file, -t TEXT  Run specific test file only
  --verbose, -v         Show detailed output
  --force, -f           Force rerun (ignore cached results)
  --fail-fast, -x       Stop on first failure
```

Examples:
```bash
usvc data run-tests                          # Test all examples
usvc data run-tests --services "llama*"      # Test matching services
usvc data run-tests --force                  # Rerun all (ignore cache)
usvc data run-tests --fail-fast              # Stop on first failure
```

### `usvc data show-test`

Show details of a local code example test, including rendered content and results.

```bash
usvc data show-test [DATA_DIR]

Options:
  --provider, -p TEXT   Filter by provider
  --services, -s TEXT   Filter by service name
  --test-file, -t TEXT  Show specific test file
```

Examples:
```bash
usvc data show-test --services "my-service" --test-file "example.py.j2"
```

---

## Service Management (`usvc services`)

Commands for managing services on the backend (remote operations).

### `usvc services upload`

Upload services to backend. Creates or updates services based on local data files.

```bash
usvc services upload [DATA_DIR]

Options:
  --provider, -p TEXT   Only upload specific provider
  --services, -s TEXT   Only upload matching services
  --dryrun              Show what would be uploaded without making changes
  --force, -f           Force upload even if unchanged
```

Examples:
```bash
usvc services upload                            # Upload all services
usvc services upload --dryrun                   # Preview changes
usvc services upload --provider fireworks       # Upload specific provider
usvc services upload --services "llama*"        # Upload matching services
```

### `usvc services list`

List services deployed on the backend.

```bash
usvc services list

Options:
  --format, -f TEXT     Output format: table, json, tsv, csv (default: table)
  --status TEXT         Filter by status: draft, pending, testing, active, rejected, suspended
  --provider TEXT       Filter by provider name
  --limit INT           Maximum records to return (default: 100)
  --skip INT            Records to skip for pagination (default: 0)
  --fields TEXT         Comma-separated fields to display
```

Examples:
```bash
usvc services list                              # List all services
usvc services list --status active              # List active services
usvc services list --format json                # JSON output
usvc services list --provider fireworks         # Filter by provider
```

### `usvc services show`

Show detailed information about a specific service.

```bash
usvc services show <SERVICE_ID_OR_NAME>

Options:
  --format, -f TEXT     Output format: json, table, tsv, csv (default: json)
  --include-documents   Include document details
```

Examples:
```bash
usvc services show llama-3-1-405b-instruct
usvc services show abc123-uuid --format json
```

### `usvc services list-tests`

List tests for deployed services. If no service ID is specified, lists tests for all services.

```bash
usvc services list-tests [SERVICE_ID]

Options:
  --format, -f TEXT     Output format: table, json, tsv, csv (default: table)
```

Examples:
```bash
usvc services list-tests                        # List tests for all services
usvc services list-tests abc123                 # List tests for specific service
usvc services list-tests --format json          # JSON output
```

### `usvc services show-test`

Show details of a test for a deployed service.

```bash
usvc services show-test <SERVICE_ID> -t <TEST_TITLE>

Options:
  --test-title, -t TEXT   Test title (required)
  --format, -f TEXT       Output format: json, table, tsv, csv (default: json)
```

Examples:
```bash
usvc services show-test abc123 -t "Python Example"
```

### `usvc services run-tests`

Run tests via gateway using the backend's execution environment.
Queues a Celery task to execute the test script with gateway credentials.

```bash
usvc services run-tests <SERVICE_ID>

Options:
  --test-title, -t TEXT   Run specific test by title (runs all if not specified)
  --verbose, -v           Show detailed output
  --force, -f             Force rerun (ignore skip status)
  --fail-fast, -x         Stop on first failure
```

Examples:
```bash
usvc services run-tests abc123                   # Run all tests for service
usvc services run-tests abc123 -t "Demo"         # Run specific test
usvc services run-tests abc123 --force           # Rerun even if skipped
usvc services run-tests abc123 -v                # Verbose output
```

### `usvc services skip-test`

Mark a code example test as skipped. Skipped tests are excluded from test runs.
Note: Connectivity tests cannot be skipped.

```bash
usvc services skip-test <SERVICE_ID> -t <TEST_TITLE>

Options:
  --test-title, -t TEXT   Test title (required)
```

Examples:
```bash
usvc services skip-test abc123 -t "Demo"
```

### `usvc services unskip-test`

Remove skip status from a test, making it eligible for execution again.

```bash
usvc services unskip-test <SERVICE_ID> -t <TEST_TITLE>

Options:
  --test-title, -t TEXT   Test title (required)
```

Examples:
```bash
usvc services unskip-test abc123 -t "Demo"
```

### `usvc services submit`

Submit a draft service for ops review.

```bash
usvc services submit <SERVICE_ID_OR_NAME>

Options:
  --message, -m TEXT    Submission message/notes for reviewer
```

Examples:
```bash
usvc services submit llama-3-1-405b-instruct
usvc services submit abc123-uuid --message "Ready for production"
```

### `usvc services deprecate`

Deprecate or delete a service from the backend.

```bash
usvc services deprecate <SERVICE_ID_OR_NAME>

Options:
  --force, -f           Skip confirmation prompt
  --hard-delete         Permanently delete instead of deprecate
```

Examples:
```bash
usvc services deprecate old-service-name
usvc services deprecate abc123-uuid --force
```

---

## Migration from Current Commands

| Current Command | New Command | Notes |
|----------------|-------------|-------|
| `usvc validate` | `usvc data validate` | Moved under `data` |
| `usvc format` | `usvc data format` | Moved under `data` |
| `usvc populate` | `usvc data populate` | Moved under `data` |
| `usvc list providers` | `usvc data list providers` | Consolidated under `data` |
| `usvc list offerings` | `usvc data list offerings` | Consolidated under `data` |
| `usvc list listings` | `usvc data list listings` | Consolidated under `data` |
| `usvc list sellers` | `usvc data list sellers` | Consolidated under `data` |
| `usvc examples list` | `usvc data list-tests` | Renamed to hyphenated form |
| `usvc examples run-local` | `usvc data run-tests` | Renamed to hyphenated form |
| `usvc upload` | `usvc services upload` | Moved under `services` |
| `usvc query` | `usvc services list` | Renamed for clarity |
| `usvc unpublish` | `usvc services deprecate` | Renamed for clarity |
| (new) | `usvc data show` | Show local file contents |
| (new) | `usvc data show-test` | Show local test details |
| (new) | `usvc services show` | Show deployed service details |
| (new) | `usvc services list-tests` | List tests for deployed services |
| (new) | `usvc services show-test` | Show test details |
| (new) | `usvc services run-tests` | Run tests via gateway |
| (new) | `usvc services skip-test` | Skip a test |
| (new) | `usvc services unskip-test` | Unskip a test |
| (new) | `usvc services submit` | Submit for review |
| (new) | `usvc services delete` | Delete a service |

---

## Workflow Examples

### New Service Development

```bash
# 1. Create data files
mkdir -p data/myprovider/services/myservice

# 2. Validate and format (local operations)
usvc data validate data/myprovider
usvc data format data/myprovider

# 3. List and run code examples locally (using upstream credentials)
usvc data list-tests --provider myprovider
usvc data run-tests --provider myprovider

# 4. Upload to backend (draft status)
usvc services upload --provider myprovider --dryrun   # Preview
usvc services upload --provider myprovider            # Upload

# 5. Run tests via gateway (backend execution)
usvc services list-tests                              # List all tests
usvc services run-tests <service-id>                   # Run tests for service

# 6. Submit for review
usvc services submit <service-id>
```

### Updating Existing Services

```bash
# 1. Make changes to local files

# 2. Validate changes (local)
usvc data validate

# 3. Test locally (using upstream credentials)
usvc data run-tests --force

# 4. Upload changes
usvc services upload --dryrun    # Preview
usvc services upload             # Apply

# 5. Verify via gateway (backend execution)
usvc services run-tests <service-id> --force
```

### Querying Deployed Services

```bash
# List all active services
usvc services list --status active

# Get details of specific service
usvc services show <service-id>

# List tests for all services
usvc services list-tests

# List tests for specific service
usvc services list-tests <service-id>

# Export as JSON for scripting
usvc services list --format json > services.json
```

### Managing Test Status

```bash
# Skip a code example test (e.g., test requires manual setup)
usvc services skip-test <service-id> -t "Demo that requires GPU"

# Re-enable a skipped test
usvc services unskip-test <service-id> -t "Demo that requires GPU"

# View test details
usvc services show-test <service-id> -t "Python Example"
```

---

## Environment Configuration

The CLI reads configuration from environment variables and config files:

```bash
# Required for remote operations
export USVC_API_URL="https://api.example.com"
export USVC_API_KEY="your-api-key"

# Optional
export USVC_GATEWAY_URL="https://gateway.example.com"
export USVC_DEFAULT_DATA_DIR="./data"
```

Or via config file `~/.usvc/config.toml`:

```toml
[api]
url = "https://api.example.com"
key = "your-api-key"

[gateway]
url = "https://gateway.example.com"

[defaults]
data_dir = "./data"
format = "table"
```
