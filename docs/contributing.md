# Contributing

For the complete contributing guide, see [CONTRIBUTING.md](https://github.com/unitysvc/unitysvc-services/blob/main/CONTRIBUTING.md) in the repository root.

## Quick Links

- [Report Bugs](https://github.com/unitysvc/unitysvc-services/issues)
- [Request Features](https://github.com/unitysvc/unitysvc-services/issues)
- [Development Guide](development.md)

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up development environment (see [Development Guide](development.md))
4. Create a feature branch
5. Make your changes
6. Run tests and linting
7. Commit and push
8. Submit a pull request

## Development Setup

```bash
# Clone your fork
git clone git@github.com:your_username/unitysvc-services.git
cd unitysvc-services

# Install with dev dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Create a branch
git checkout -b feature/my-feature
```

## Testing and Linting

```bash
# Run tests
pytest

# Run linting
ruff check .
ruff format .

# Type checking
mypy src/
```

## Commit Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Test changes
- `chore:` Maintenance tasks

## Code of Conduct

Please note that this project is released with a Contributor Code of Conduct. By participating in this project you agree to abide by its terms.

For full details, see the [complete contributing guide](https://github.com/unitysvc/unitysvc-services/blob/main/CONTRIBUTING.md).
