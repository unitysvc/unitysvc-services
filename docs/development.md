# Development Guide

Guide for setting up a development environment and contributing to the UnitySVC Provider SDK.

## Development Setup

### Prerequisites

- Python 3.11 or later
- Git
- uv (recommended) or pip
- Code editor (VS Code, PyCharm, etc.)

### Clone Repository

```bash
git clone https://github.com/unitysvc/unitysvc-services.git
cd unitysvc-services
```

### Install Development Dependencies

Using uv (recommended):

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

Using pip:

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Verify Installation

```bash
# Run CLI
unitysvc_services --help

# Run tests
pytest

# Run linting
ruff check .
mypy src/
```

## Project Structure

```
unitysvc-services/
├── src/
│   └── unitysvc_services/
│       ├── __init__.py
│       ├── cli.py              # Main CLI application
│       ├── init.py             # Init commands
│       ├── list.py             # List commands
│       ├── query.py            # Query commands
│       ├── publish.py          # Publish commands
│       ├── update.py           # Update commands
│       ├── standalone.py       # Format/validate/populate
│       ├── utils.py            # Common utilities
│       ├── publisher.py        # Backend publishing logic
│       ├── validator.py        # Validation logic
│       ├── formatter.py        # Formatting logic
│       └── populator.py        # Population logic
├── tests/
│   ├── test_cli.py
│   ├── test_utils.py
│   └── fixtures/               # Test data
├── docs/                        # Documentation
├── pyproject.toml              # Project configuration
├── mkdocs.yml                  # MkDocs configuration
└── README.md
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/my-feature
```

### 2. Make Changes

Edit code in `src/unitysvc_services/`.

### 3. Run Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_utils.py

# Run with coverage
pytest --cov=unitysvc_services --cov-report=html

# View coverage report
open htmlcov/index.html
```

### 4. Lint Code

```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .

# Type checking
mypy src/
```

### 5. Test CLI Locally

```bash
# Install in editable mode
pip install -e .

# Run CLI
unitysvc_services --help

# Test specific command
unitysvc_services init provider test-provider
```

### 6. Update Documentation

If you added/changed features:

```bash
# Edit relevant docs
vim docs/cli-reference.md

# Preview documentation locally
mkdocs serve

# View at http://localhost:8000
```

### 7. Commit Changes

```bash
git add .
git commit -m "feat: Add new feature"
```

Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Test changes
- `chore:` Maintenance tasks

### 8. Push and Create PR

```bash
git push origin feature/my-feature
```

Create a pull request on GitHub.

## Testing

### Test Structure

```python
# tests/test_utils.py
import pytest
from pathlib import Path
from unitysvc_services.utils import load_data_file

def test_load_json_file(tmp_path: Path):
    """Test loading JSON file."""
    # Create test file
    test_file = tmp_path / "test.json"
    test_file.write_text('{"schema": "provider_v1", "name": "test"}')

    # Load file
    data, fmt = load_data_file(test_file)

    # Assert
    assert fmt == "json"
    assert data["schema"] == "provider_v1"
    assert data["name"] == "test"
```

### Fixtures

Use `tmp_path` fixture for temporary files:

```python
def test_with_temp_dir(tmp_path: Path):
    """Test with temporary directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create test files
    provider_dir = data_dir / "test-provider"
    provider_dir.mkdir()

    provider_file = provider_dir / "provider.json"
    provider_file.write_text('{"schema": "provider_v1", "name": "test-provider"}')

    # Test your code
    # ...
```

### Running Specific Tests

```bash
# Run by name
pytest -k test_load_json_file

# Run by marker
pytest -m slow

# Run with verbose output
pytest -v

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf
```

### Updating Schemas

When you modify Pydantic models, regenerate JSON schemas:

```bash
python scripts/update_schema.py
```

This script:
- Scans all models in `src/unitysvc_services/models/`
- Generates JSON schemas for each model
- Outputs to `src/unitysvc_services/schema/`
- Formats schemas to match pre-commit requirements

The generated schemas are used for:
- Data validation in the CLI
- Documentation generation
- IDE autocomplete support

## Code Style

### Python Style

Follow PEP 8 and project conventions:

```python
from pathlib import Path
from typing import Any, Optional

def my_function(
    data_dir: Path,
    schema: str,
    name_field: str = "name",
    *,
    strict: bool = False
) -> Optional[dict[str, Any]]:
    """
    Short description.

    Longer description if needed.

    Args:
        data_dir: Directory to search
        schema: Schema type to match
        name_field: Field name to match against
        strict: Whether to enforce strict matching

    Returns:
        Dictionary with data or None if not found

    Raises:
        ValueError: If schema is invalid
    """
    # Implementation
    pass
```

### Type Hints

Always use type hints:

```python
# Good
def find_files(data_dir: Path) -> list[Path]:
    return list(data_dir.glob("*.json"))

# Bad
def find_files(data_dir):
    return list(data_dir.glob("*.json"))
```

### Docstrings

Use Google-style docstrings:

```python
def process_data(data: dict[str, Any], *, validate: bool = True) -> dict[str, Any]:
    """
    Process and transform data.

    This function takes raw data and applies various transformations
    including validation, normalization, and enrichment.

    Args:
        data: Raw data dictionary
        validate: Whether to validate before processing

    Returns:
        Processed data dictionary

    Raises:
        ValueError: If data is invalid and validate=True

    Examples:
        >>> process_data({"name": "test"})
        {"name": "test", "processed": True}
    """
    pass
```

## CLI Development

### Adding New Commands

```python
# src/unitysvc_services/mycommand.py
import typer
from pathlib import Path
from typing import Optional

app = typer.Typer()

@app.command("subcommand")
def my_subcommand(
    name: str = typer.Argument(..., help="Name of the resource"),
    data_dir: Optional[Path] = typer.Option(None, "--data-dir", "-d"),
):
    """
    Command description here.
    """
    typer.echo(f"Processing: {name}")
    # Implementation
```

Register in `cli.py`:

```python
from unitysvc_services import mycommand

app.add_typer(mycommand.app, name="mycommand", help="My command group")
```

### Rich Output

Use `rich` for better CLI output:

```python
from rich.console import Console
from rich.table import Table

console = Console()

def display_results(items: list[dict]):
    """Display results in a table."""
    table = Table(title="Results")

    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")

    for item in items:
        table.add_row(item["name"], item["status"])

    console.print(table)
```

## Documentation

### Building Docs Locally

```bash
# Install MkDocs
pip install mkdocs mkdocs-material

# Serve locally
mkdocs serve

# Build static site
mkdocs build

# Deploy to GitHub Pages (maintainers only)
mkdocs gh-deploy
```

### Documentation Style

- Use clear, concise language
- Include code examples
- Link to related pages
- Use admonitions for important notes

```markdown
!!! note
    Important information here

!!! warning
    Warning message here

!!! tip
    Helpful tip here
```

## Debugging

### Debug CLI Commands

```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use ipdb for better experience
import ipdb; ipdb.set_trace()
```

### Enable Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.error("Error message")
```

### VS Code Launch Configuration

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal"
    },
    {
      "name": "CLI: validate",
      "type": "python",
      "request": "launch",
      "module": "unitysvc_services.cli",
      "args": ["validate", "data"],
      "console": "integratedTerminal"
    }
  ]
}
```

## Release Process

### Version Bump

Update version in `pyproject.toml`:

```toml
[project]
version = "0.2.0"
```

### Create Release

```bash
# Tag release
git tag -a v0.2.0 -m "Release 0.2.0"
git push origin v0.2.0

# Build package
python -m build

# Upload to PyPI (maintainers only)
python -m twine upload dist/*
```

### Changelog

Update `CHANGELOG.md`:

```markdown
## [0.2.0] - 2024-01-15

### Added
- New feature X
- New command Y

### Fixed
- Bug in Z

### Changed
- Improved performance of W
```

## Common Tasks

### Add New Schema Field

1. Update Pydantic model in `src/unitysvc_services/models/`
2. Regenerate JSON schemas: `python scripts/update_schema.py`
3. Update schema validation if needed
4. Update documentation
5. Add tests
6. Update examples

### Add New CLI Command

1. Create command module
2. Register in `cli.py`
3. Add tests
4. Update CLI reference docs
5. Add examples to workflows

### Fix a Bug

1. Write failing test
2. Fix the code
3. Verify test passes
4. Update docs if needed
5. Create PR with fix

## Getting Help

- Check existing [issues](https://github.com/unitysvc/unitysvc-services/issues)
- Join discussions on GitHub
- Read the [contributing guide](contributing.md)
- Ask questions in issues

## See Also

- [Contributing Guide](contributing.md) - Contribution guidelines
- [CLI Reference](cli-reference.md) - Command reference
- [API Reference](api-reference.md) - Python API
