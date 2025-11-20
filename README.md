# UnitySVC Services SDK

![PyPI version](https://img.shields.io/pypi/v/unitysvc-services.svg)
[![Documentation Status](https://readthedocs.org/projects/unitysvc-services/badge/?version=latest)](https://unitysvc-services.readthedocs.io/en/latest/?version=latest)

Client library and CLI tools for sellers and providers of digital service to interact with the UnitySVC platform.

**📚 [Full Documentation](https://unitysvc-services.readthedocs.io)** | **🚀 [Getting Started](https://unitysvc-services.readthedocs.io/en/latest/getting-started/)** | **📖 [CLI Reference](https://unitysvc-services.readthedocs.io/en/latest/cli-reference/)**

## Overview

UnitySVC Services SDK enables digital service sellers and providers to manage their service offerings through a **local-first, version-controlled workflow**:

-   **Define** service data using schema-validated files (JSON/TOML)
-   **Manage** everything locally in git-controlled directories
-   **Validate** data against schemas
-   **Test** code examples using provider credentials
-   **Publish** to UnitySVC platform when ready
-   **Automate** with populate scripts for dynamic catalogs

## Installation

```bash
pip install unitysvc-services
```

Requires Python 3.11+

**CLI Alias:** The command `unitysvc_services` can also be invoked using the shorter alias `usvc`.

## Quick Example

```bash
# Initialize provider and service (using short alias 'usvc')
usvc init provider my-provider
usvc init offering my-service
usvc init seller my-marketplace

# Validate and format
usvc validate
usvc format

# Test code examples with upstream credentials
usvc test list --provider fireworks
usvc test run --provider fireworks --services "llama*"

# if you write a script to manage services
usvc populate

# Publish to platform (publishes all: sellers, providers, offerings, listings)
export UNITYSVC_BASE_URL="https://api.unitysvc.com/api/v1"
export UNITYSVC_API_KEY="your-api-key"
usvc publish

# Query unitysvc backend to verify data
usvc query providers --fields id,name,contact_email
```

## Key Features

-   📋 **Pydantic Models** - Type-safe data models for all entities
-   ✅ **Data Validation** - Comprehensive schema validation
-   🔄 **Local-First** - Work offline, commit to git, publish when ready
-   🚀 **CLI Tools** - Complete command-line interface
-   🤖 **Automation** - Script-based service generation
-   📝 **Multiple Formats** - Support for JSON and TOML
-   🎯 **Smart Routing** - Request routing based on routing keys (e.g., model-specific endpoints)

## Workflows

### Manual Workflow (small catalogs)

```bash
init → edit files → validate → test → format → publish → verify
```

### Automated Workflow (large/dynamic catalogs)

```bash
init → configure populate script → populate → validate → publish
```

See [Workflows Documentation](https://unitysvc-services.readthedocs.io/en/latest/workflows/) for details.

## Data Structure

```
data/
├── seller.json                    # One seller per repo
├── ${provider_name}/
│   ├── provider.json              # Provider metadata
│   ├── docs/                      # Shared documentation
│   └── services/
│       └── ${service_name}/
│           ├── service.json       # Service offering
│           └── listing-*.json     # Service listing(s)
```

See [Data Structure Documentation](https://unitysvc-services.readthedocs.io/en/latest/data-structure/) for complete details.

## CLI Commands

| Command     | Description                                      |
| ----------- | ------------------------------------------------ |
| `init`      | Initialize new data files from schemas           |
| `list`      | List local data files                            |
| `query`     | Query backend API for published data             |
| `publish`   | Publish data to backend                          |
| `unpublish` | Unpublish (delete) data from backend             |
| `update`    | Update local file fields                         |
| `validate`  | Validate data consistency                        |
| `format`    | Format data files                                |
| `populate`  | Execute provider populate scripts                |
| `test`      | Test code examples with upstream API credentials |

Run `usvc --help` or see [CLI Reference](https://unitysvc-services.readthedocs.io/en/latest/cli-reference/) for complete documentation.

## Documentation

-   **[Getting Started](https://unitysvc-services.readthedocs.io/en/latest/getting-started/)** - Installation and first steps
-   **[Data Structure](https://unitysvc-services.readthedocs.io/en/latest/data-structure/)** - File organization rules
-   **[Workflows](https://unitysvc-services.readthedocs.io/en/latest/workflows/)** - Manual and automated patterns
-   **[Documenting Service Listings](https://unitysvc-services.readthedocs.io/en/latest/documenting-services/)** - Add documentation to services
-   **[Creating Code Examples](https://unitysvc-services.readthedocs.io/en/latest/code-examples/)** - Develop and test code examples
-   **[CLI Reference](https://unitysvc-services.readthedocs.io/en/latest/cli-reference/)** - All commands and options
-   **[File Schemas](https://unitysvc-services.readthedocs.io/en/latest/file-schemas/)** - Schema specifications
-   **[Python API](https://unitysvc-services.readthedocs.io/en/latest/api-reference/)** - Programmatic usage

## Links

-   **PyPI**: https://pypi.org/project/unitysvc-services/
-   **Documentation**: https://unitysvc-services.readthedocs.io
-   **Source Code**: https://github.com/unitysvc/unitysvc-services
-   **Issue Tracker**: https://github.com/unitysvc/unitysvc-services/issues

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions welcome! See [Contributing Guide](https://unitysvc-services.readthedocs.io/en/latest/contributing/) for details.
