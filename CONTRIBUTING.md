# Contributing

Contributions are welcome, and they are greatly appreciated! Every little bit helps, and credit will always be given.

## Types of Contributions

### Report Bugs

Report bugs at https://github.com/unitysvc/unitysvc-services/issues.

If you are reporting a bug, please include:

- Your operating system name and version
- Python version
- Any details about your local setup that might be helpful in troubleshooting
- Detailed steps to reproduce the bug

### Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help wanted" is open to whoever wants to implement it.

### Implement Features

Look through the GitHub issues for features. Anything tagged with "enhancement" and "help wanted" is open to whoever wants to implement it.

### Write Documentation

UnitySVC Provider SDK can always use more documentation, whether as part of the official docs, in docstrings, or even on the web in blog posts, articles, and such.

### Submit Feedback

The best way to send feedback is to file an issue at https://github.com/unitysvc/unitysvc-services/issues.

If you are proposing a feature:

- Explain in detail how it would work
- Keep the scope as narrow as possible, to make it easier to implement
- Remember that this is a volunteer-driven project, and that contributions are welcome :)

## Getting Started

Ready to contribute? Here's how to set up `unitysvc-services` for local development.

### 1. Fork and Clone

Fork the repo on GitHub, then clone your fork locally:

```bash
git clone git@github.com:your_username/unitysvc-services.git
cd unitysvc-services
```

### 2. Set Up Development Environment

Using uv (recommended):

```bash
# Install uv
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

### 3. Create a Branch

```bash
git checkout -b feature/my-feature
# or
git checkout -b fix/my-bugfix
```

### 4. Make Your Changes

- Write clear, documented code
- Add tests for new functionality
- Update documentation as needed

### 5. Run Tests and Linting

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=unitysvc_services --cov-report=html

# Lint code
ruff check .
ruff format .

# Type checking
mypy src/
```

### 6. Commit and Push

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
git add .
git commit -m "feat: Add new feature"
# or
git commit -m "fix: Fix bug in validation"
git push origin feature/my-feature
```

Commit types:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Test changes
- `chore:` Maintenance tasks

### 7. Submit a Pull Request

Submit a pull request through GitHub.

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

1. **Tests**: The pull request should include tests for new functionality
2. **Documentation**: Update docs if adding/changing features
3. **Code Quality**: All linting checks must pass
4. **Python Versions**: Code should work with Python 3.11+
5. **Type Hints**: Include type hints for all functions
6. **Docstrings**: Use Google-style docstrings

## Development Guidelines

### Code Style

- Follow PEP 8
- Use type hints
- Write descriptive docstrings
- Keep functions focused and small
- Use meaningful variable names

Example:

```python
from pathlib import Path
from typing import Optional

def find_service(
    name: str,
    data_dir: Path,
    *,
    strict: bool = False
) -> Optional[dict[str, Any]]:
    """
    Find a service by name.

    Args:
        name: Service name to search for
        data_dir: Directory to search in
        strict: Whether to enforce strict matching

    Returns:
        Service data dictionary or None if not found

    Raises:
        ValueError: If name is invalid
    """
    # Implementation
    pass
```

### Testing

- Write unit tests for all new functions
- Use `tmp_path` fixture for file operations
- Test both success and error cases
- Aim for high code coverage

Example:

```python
def test_load_json_file(tmp_path: Path):
    """Test loading JSON file."""
    # Arrange
    test_file = tmp_path / "test.json"
    test_file.write_text('{"schema": "provider_v1"}')

    # Act
    data, fmt = load_data_file(test_file)

    # Assert
    assert fmt == "json"
    assert data["schema"] == "provider_v1"
```

### Documentation

- Update relevant documentation in `docs/`
- Add examples for new features
- Keep README.md up to date
- Use clear, concise language

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_utils.py

# Run specific test
pytest tests/test_utils.py::test_load_json_file

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=unitysvc_services --cov-report=html
open htmlcov/index.html
```

## Building Documentation

```bash
# Install MkDocs
pip install mkdocs mkdocs-material

# Serve locally
mkdocs serve

# Build static site
mkdocs build
```

## Release Process (Maintainers Only)

### 1. Update Version

Update version in `pyproject.toml`:

```toml
[project]
version = "0.2.0"
```

### 2. Update Changelog

Update `CHANGELOG.md` with release notes.

### 3. Create Tag

```bash
git tag -a v0.2.0 -m "Release 0.2.0"
git push origin v0.2.0
```

### 4. Build and Publish

```bash
# Build package
python -m build

# Upload to PyPI
python -m twine upload dist/*
```

### 5. Deploy Documentation

```bash
mkdocs gh-deploy
```

## Code of Conduct

Please note that this project is released with a [Contributor Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.

## Questions?

- Check the [Development Guide](docs/development.md) for detailed information
- Look through existing [issues](https://github.com/unitysvc/unitysvc-services/issues)
- Open a new issue if you need help

Thank you for contributing!
