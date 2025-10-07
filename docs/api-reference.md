# API Reference

Python API documentation for the UnitySVC Provider SDK.

## Overview

The SDK provides both a CLI and a Python API. While most users will use the CLI, the Python API is available for programmatic access and custom integrations.

## Core Modules

### unitysvc_services.utils

Common utilities for file operations.

#### load_data_file()

Load a data file and return its contents with format information.

```python
from pathlib import Path
from unitysvc_services.utils import load_data_file

data, file_format = load_data_file(Path("data/my-provider/provider.json"))
# data: dict with file contents
# file_format: "json" or "toml"
```

**Parameters:**

-   `file_path` (Path): Path to the data file

**Returns:**

-   `tuple[dict[str, Any], str]`: Data dictionary and format ("json" or "toml")

**Raises:**

-   `ValueError`: If file format is not supported
-   `FileNotFoundError`: If file doesn't exist

#### write_data_file()

Write data to a file in the specified format.

```python
from pathlib import Path
from unitysvc_services.utils import write_data_file

data = {"schema": "provider_v1", "name": "my-provider"}
write_data_file(Path("data/my-provider/provider.json"), data, "json")
```

**Parameters:**

-   `file_path` (Path): Path to write to
-   `data` (dict): Data to write
-   `file_format` (str): Format ("json" or "toml")

**Returns:**

-   `None`

#### find_data_files()

Find all data files (JSON and TOML) in a directory.

```python
from pathlib import Path
from unitysvc_services.utils import find_data_files

files = find_data_files(Path("data"))
# Returns: List[Path] of all .json and .toml files
```

**Parameters:**

-   `data_dir` (Path): Directory to search

**Returns:**

-   `list[Path]`: List of data file paths

#### find_files_by_schema()

Find all files matching a specific schema.

```python
from pathlib import Path
from unitysvc_services.utils import find_files_by_schema

service_files = find_files_by_schema(
    Path("data"),
    schema="service_v1",
    field_filter={"upstream_status": "ready"}
)
# Returns list of (Path, dict) tuples
```

**Parameters:**

-   `data_dir` (Path): Directory to search
-   `schema` (str): Schema to match (e.g., "service_v1")
-   `field_filter` (dict, optional): Additional field filters

**Returns:**

-   `list[tuple[Path, dict]]`: List of (file_path, data) tuples

#### find_file_by_schema_and_name()

Find a single file by schema and name field.

```python
from pathlib import Path
from unitysvc_services.utils import find_file_by_schema_and_name

result = find_file_by_schema_and_name(
    Path("data"),
    schema="service_v1",
    name_field="name",
    name_value="gpt-4"
)

if result:
    file_path, file_format, data = result
    # Process the file
else:
    # File not found
    pass
```

**Parameters:**

-   `data_dir` (Path): Directory to search
-   `schema` (str): Schema to match
-   `name_field` (str): Field name to match (e.g., "name")
-   `name_value` (str): Field value to match

**Returns:**

-   `tuple[Path, str, dict] | None`: (file_path, format, data) or None if not found

### unitysvc_services.cli

Main CLI application built with Typer.

```python
from unitysvc_services.cli import app

# The app is a Typer application with command groups:
# - init: Initialize new files
# - list: List local files
# - query: Query backend
# - publish: Publish to backend
# - update: Update local files
# - validate: Validate data
# - format: Format files
# - populate: Run populate scripts
```

### unitysvc_services.publisher

Backend publishing operations.

#### get_api_client()

Create an authenticated API client.

```python
from unitysvc_services.publisher import get_api_client

client = get_api_client(
    backend_url="https://api.unitysvc.com/api/v1",
    api_key="your-api-key"
)
```

**Parameters:**

-   `backend_url` (str): Backend API URL
-   `api_key` (str): API authentication key

**Returns:**

-   `AuthenticatedClient`: Configured API client

#### publish_provider()

Publish provider data to backend.

```python
from pathlib import Path
from unitysvc_services.publisher import publish_provider

success = publish_provider(
    client=client,
    provider_file=Path("data/my-provider/provider.json")
)
```

**Parameters:**

-   `client` (AuthenticatedClient): API client
-   `provider_file` (Path): Path to provider file

**Returns:**

-   `bool`: True if successful

Similar functions exist for:

-   `publish_seller()`
-   `publish_offering()`
-   `publish_listing()`

### unitysvc_services.validator

Data validation operations.

#### validate_data_directory()

Validate all data in a directory.

```python
from pathlib import Path
from unitysvc_services.validator import validate_data_directory

is_valid, errors = validate_data_directory(Path("data"))

if not is_valid:
    for error in errors:
        print(f"Error: {error}")
```

**Parameters:**

-   `data_dir` (Path): Directory to validate

**Returns:**

-   `tuple[bool, list[str]]`: (is_valid, list of error messages)

**Validation checks:**

-   Schema compliance
-   Required fields present
-   Name uniqueness
-   Directory name matching
-   Valid references
-   File path validity

### unitysvc_services.formatter

File formatting operations.

#### format_data_directory()

Format all data files in a directory.

```python
from pathlib import Path
from unitysvc_services.formatter import format_data_directory

modified_files = format_data_directory(
    Path("data"),
    check_only=False
)

for file_path in modified_files:
    print(f"Formatted: {file_path}")
```

**Parameters:**

-   `data_dir` (Path): Directory to format
-   `check_only` (bool): If True, don't modify files

**Returns:**

-   `list[Path]`: List of modified (or would-be modified) files

**Formatting rules:**

-   JSON: 2-space indentation, sorted keys
-   TOML: Standard formatting
-   Remove trailing whitespace
-   Single newline at end of file

### unitysvc_services.populator

Service population operations.

#### run_populate_scripts()

Execute populate scripts for providers.

```python
from pathlib import Path
from unitysvc_services.populator import run_populate_scripts

results = run_populate_scripts(
    Path("data"),
    provider_filter="openai",
    dry_run=False
)

for provider, success, output in results:
    print(f"{provider}: {'✓' if success else '✗'}")
    print(output)
```

**Parameters:**

-   `data_dir` (Path): Data directory
-   `provider_filter` (str, optional): Run for specific provider only
-   `dry_run` (bool): If True, don't actually execute

**Returns:**

-   `list[tuple[str, bool, str]]`: List of (provider_name, success, output)

## Pydantic Models

### Provider

```python
from unitysvc_services.models import Provider

provider = Provider(
    schema="provider_v1",
    name="my-provider",
    display_name="My Provider",
    description="A digital service provider"
)
```

### Seller

```python
from unitysvc_services.models import Seller

seller = Seller(
    schema="seller_v1",
    name="my-marketplace",
    display_name="My Marketplace",
    business_name="Marketplace Inc."
)
```

### ServiceOffering

```python
from unitysvc_services.models import ServiceOffering

service = ServiceOffering(
    schema="service_v1",
    name="my-service",
    display_name="My Service",
    description="A high-performance service",
    service_type="api",
    upstream_status="ready"
)
```

### ServiceListing

```python
from unitysvc_services.models import ServiceListing

listing = ServiceListing(
    schema="listing_v1",
    seller_name="my-marketplace",
    service_name="my-service",
    listing_status="in_service"
)
```

## Environment Variables

The SDK respects these environment variables:

```python
import os

# Backend connection
backend_url = os.getenv("UNITYSVC_BASE_URL", "https://api.unitysvc.com/api/v1")
api_key = os.getenv("UNITYSVC_API_KEY")
```

## Custom Scripts

### Example: Bulk Status Update

```python
from pathlib import Path
from unitysvc_services.utils import find_files_by_schema, write_data_file

data_dir = Path("data")

# Find all ready services
services = find_files_by_schema(
    data_dir,
    schema="service_v1",
    field_filter={"upstream_status": "ready"}
)

# Update to deprecated
for file_path, data in services:
    data["upstream_status"] = "deprecated"
    # Preserve original format
    file_format = "json" if file_path.suffix == ".json" else "toml"
    write_data_file(file_path, data, file_format)
    print(f"Updated: {file_path}")
```

### Example: Custom Validator

```python
from pathlib import Path
from unitysvc_services.utils import find_files_by_schema

def validate_pricing(data_dir: Path) -> list[str]:
    """Validate all services have pricing information."""
    errors = []

    services = find_files_by_schema(data_dir, schema="service_v1")

    for file_path, data in services:
        if "pricing" not in data:
            errors.append(f"{file_path}: Missing pricing information")
        elif "currency" not in data["pricing"]:
            errors.append(f"{file_path}: Missing currency in pricing")

    return errors

# Run validation
errors = validate_pricing(Path("data"))
if errors:
    for error in errors:
        print(f"Error: {error}")
```

### Example: Report Generation

```python
from pathlib import Path
from unitysvc_services.utils import find_files_by_schema
import json

def generate_service_report(data_dir: Path) -> dict:
    """Generate summary report of all services."""
    services = find_files_by_schema(data_dir, schema="service_v1")

    report = {
        "total_services": len(services),
        "by_type": {},
        "by_status": {},
        "by_provider": {}
    }

    for file_path, data in services:
        # By type
        svc_type = data.get("service_type", "unknown")
        report["by_type"][svc_type] = report["by_type"].get(svc_type, 0) + 1

        # By status
        status = data.get("upstream_status", "unknown")
        report["by_status"][status] = report["by_status"].get(status, 0) + 1

        # By provider (from file path)
        provider = file_path.parts[-4]  # data/provider/services/service/
        report["by_provider"][provider] = report["by_provider"].get(provider, 0) + 1

    return report

# Generate and print report
report = generate_service_report(Path("data"))
print(json.dumps(report, indent=2))
```

## Exception Handling

The SDK raises standard Python exceptions:

```python
from pathlib import Path
from unitysvc_services.utils import load_data_file

try:
    data, fmt = load_data_file(Path("data/provider.json"))
except FileNotFoundError:
    print("File not found")
except ValueError as e:
    print(f"Invalid file format: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Type Hints

The SDK provides full type hints for IDE support:

```python
from pathlib import Path
from typing import Any
from unitysvc_services.utils import find_file_by_schema_and_name

def get_service(name: str, data_dir: Path = Path("data")) -> dict[str, Any] | None:
    """Get service data by name."""
    result = find_file_by_schema_and_name(
        data_dir,
        schema="service_v1",
        name_field="name",
        name_value=name
    )

    if result:
        _, _, data = result
        return data

    return None
```

## See Also

-   [CLI Reference](cli-reference.md) - Command-line interface
-   [File Schemas](file-schemas.md) - Data schema specifications
-   [Workflows](workflows.md) - Usage patterns and examples
