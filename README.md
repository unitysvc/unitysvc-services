# UnitySVC Provider SDK

![PyPI version](https://img.shields.io/pypi/v/unitysvc-services.svg)
[![Documentation Status](https://readthedocs.org/projects/unitysvc-services/badge/?version=latest)](https://unitysvc-services.readthedocs.io/en/latest/?version=latest)

Client library and CLI tools for digital service providers to interact with the UnitySVC platform.

**📚 [Full Documentation](https://unitysvc-services.readthedocs.io)** | **🚀 [Getting Started](https://unitysvc-services.readthedocs.io/en/latest/getting-started/)** | **📖 [CLI Reference](https://unitysvc-services.readthedocs.io/en/latest/cli-reference/)**

## Overview

UnitySVC Provider SDK enables digital service providers to manage their service offerings through a **local-first, version-controlled workflow**:

-   **Define** service data using schema-validated files (JSON/TOML)
-   **Manage** everything locally in git-controlled directories
-   **Validate** data against schemas before publishing
-   **Publish** to UnitySVC platform when ready
-   **Automate** with populate scripts for dynamic catalogs

## Installation

```bash
pip install unitysvc-services
```

Requires Python 3.11+

## Quick Example

```bash
# Initialize provider and service
unitysvc_services init provider my-provider
unitysvc_services init offering my-service
unitysvc_services init seller my-marketplace

# Validate and format
unitysvc_services validate
unitysvc_services format

# Publish to platform (publishes all: sellers, providers, offerings, listings)
export UNITYSVC_BASE_URL="https://api.unitysvc.com/api/v1"
export UNITYSVC_API_KEY="your-api-key"
unitysvc_services publish

# Or publish specific types only
unitysvc_services publish providers

# Verify with default fields
unitysvc_services query offerings

# Query with custom fields
unitysvc_services query providers --fields id,name,contact_email
```

## Key Features

-   📋 **Pydantic Models** - Type-safe data models for all entities
-   ✅ **Data Validation** - Comprehensive schema validation
-   🔄 **Local-First** - Work offline, commit to git, publish when ready
-   🚀 **CLI Tools** - Complete command-line interface
-   🤖 **Automation** - Script-based service generation
-   📝 **Multiple Formats** - Support for JSON and TOML

## Workflows

### Manual Workflow (small catalogs)

```bash
init → edit files → validate → format → publish → verify
```

### Automated Workflow (large/dynamic catalogs)

```bash
init provider → configure populate script → populate → validate → publish
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

| Command    | Description                            |
| ---------- | -------------------------------------- |
| `init`     | Initialize new data files from schemas |
| `list`     | List local data files                  |
| `query`    | Query backend API for published data   |
| `publish`  | Publish data to backend                |
| `update`   | Update local file fields               |
| `validate` | Validate data consistency              |
| `format`   | Format data files                      |
| `populate` | Execute provider populate scripts      |

Run `unitysvc_services --help` or see [CLI Reference](https://unitysvc-services.readthedocs.io/en/latest/cli-reference/) for complete documentation.

## Documentation

-   **[Getting Started](https://unitysvc-services.readthedocs.io/en/latest/getting-started/)** - Installation and first steps
-   **[Data Structure](https://unitysvc-services.readthedocs.io/en/latest/data-structure/)** - File organization rules
-   **[Workflows](https://unitysvc-services.readthedocs.io/en/latest/workflows/)** - Manual and automated patterns
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
