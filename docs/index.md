# UnitySVC Seller SDK Documentation

Welcome to the UnitySVC Seller SDK documentation. This package enables digital service providers to manage their service offerings through a local-first, version-controlled workflow.

## Quick Links

-   **[Getting Started](getting-started.md)** - Installation and first steps
-   **[Data Structure](data-structure.md)** - Understanding the Service Data model
-   **[CLI Reference](cli-reference.md)** - Complete command-line interface guide
-   **[Workflows](workflows.md)** - Common usage patterns and best practices
-   **[API Reference](api-reference.md)** - Python API documentation

## What is UnitySVC Seller SDK?

The UnitySVC Seller SDK is a Python package that enables digital service providers to:

-   **Define** service offerings and listings using schema-validated files
-   **Manage** service data locally in version-controlled repositories
-   **Validate** data against JSON schemas before uploading
-   **Upload** services to the UnitySVC platform
-   **Manage Lifecycle** - Submit services for review, deprecate, or withdraw services
-   **Query** and verify uploaded data

## The Service Data Model

A **Service** in UnitySVC consists of three complementary data components that work together:

| Component | Schema | Purpose | Reusability |
|-----------|--------|---------|-------------|
| **Provider Data** | `provider_v1` | WHO provides the service | One per provider, shared by all offerings |
| **Offering Data** | `offering_v1` | WHAT is being provided | One per service, can have multiple listings |
| **Listing Data** | `listing_v1` | HOW it's sold to customers | One per pricing tier/marketplace |

These three parts are **organized separately** in the file system for reusability, but are **uploaded together** as a unified service to the UnitySVC platform.

### Why This Structure?

-   **Provider Data** contains identity, contact info, and terms of service - defined once and reused
-   **Offering Data** defines the service itself, API endpoints, and upstream pricing
-   **Listing Data** defines customer-facing presentation, documentation, and pricing

This enables scenarios like:
- One provider with multiple service offerings
- One offering with multiple listings (e.g., basic/premium tiers)
- Shared documentation across services

## Key Features

-   **Unified Upload** - Provider, offering, and listing uploaded together atomically
-   **Service Lifecycle** - Submit for review, deprecate, or withdraw services
-   **Pydantic Models** - Type-safe data models for all entities
-   **Data Validation** - Comprehensive schema validation
-   **Local-First** - Work offline, commit to git, upload when ready
-   **CLI Tools** - Complete command-line interface
-   **Automation** - Script-based service generation
-   **Multiple Formats** - Support for JSON and TOML
-   **Smart Routing** - Request routing based on routing keys (e.g., model-specific endpoints)

## Documentation Overview

### For New Users

1. [**Getting Started**](getting-started.md) - Install the SDK and create your first service
2. [**Data Structure**](data-structure.md) - Learn about the Service Data model and file organization
3. [**Workflows**](workflows.md) - Understand manual and automated workflows

### For Reference

-   [**CLI Reference**](cli-reference.md) - All available commands and options
-   [**File Schemas**](file-schemas.md) - Detailed schema specifications
-   [**API Reference**](api-reference.md) - Python API documentation

### For Contributors

-   [**Development Guide**](development.md) - Set up development environment
-   [**Contributing**](contributing.md) - How to contribute to the project

## Community & Support

-   **GitHub**: [unitysvc/unitysvc-services](https://github.com/unitysvc/unitysvc-services)
-   **Issues**: [Report bugs or request features](https://github.com/unitysvc/unitysvc-services/issues)
-   **PyPI**: [unitysvc-services](https://pypi.org/project/unitysvc-services/)

## License

This project is licensed under the MIT License.
