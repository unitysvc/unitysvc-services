"""Tests for the data validator."""

from pathlib import Path

import pytest

from unitysvc_services.validator import DataValidator


@pytest.fixture
def schema_dir():
    """Get the schema directory path."""
    pkg_path = Path(__file__).parent.parent / "src" / "unitysvc_services"
    return pkg_path / "schema"


@pytest.fixture
def example_data_dir():
    """Get the example data directory path."""
    return Path(__file__).parent / "example_data"


def test_validator_loads_schemas(schema_dir, example_data_dir):
    """Test that the validator can load all schemas."""
    validator = DataValidator(example_data_dir, schema_dir)

    # Check that schemas were loaded
    assert len(validator.schemas) > 0
    assert "base" in validator.schemas
    assert "provider_v1" in validator.schemas
    assert "service_v1" in validator.schemas
    assert "listing_v1" in validator.schemas


def test_validate_provider_toml(schema_dir, example_data_dir):
    """Test validation of provider TOML file."""
    validator = DataValidator(example_data_dir, schema_dir)

    provider_file = example_data_dir / "provider1" / "provider.toml"
    is_valid, errors = validator.validate_data_file(provider_file)

    if not is_valid:
        print(f"Validation errors for {provider_file}:")
        for error in errors:
            print(f"  - {error}")

    assert is_valid, f"Provider TOML validation failed: {errors}"


def test_validate_provider_json(schema_dir, example_data_dir):
    """Test validation of provider JSON file."""
    validator = DataValidator(example_data_dir, schema_dir)

    provider_file = example_data_dir / "provider2" / "provider.json"
    is_valid, errors = validator.validate_data_file(provider_file)

    if not is_valid:
        print(f"Validation errors for {provider_file}:")
        for error in errors:
            print(f"  - {error}")

    assert is_valid, f"Provider JSON validation failed: {errors}"


def test_validate_service_toml(schema_dir, example_data_dir):
    """Test validation of service TOML file."""
    validator = DataValidator(example_data_dir, schema_dir)

    service_file = example_data_dir / "provider1" / "services" / "service1" / "service.toml"
    is_valid, errors = validator.validate_data_file(service_file)

    if not is_valid:
        print(f"Validation errors for {service_file}:")
        for error in errors:
            print(f"  - {error}")

    assert is_valid, f"Service TOML validation failed: {errors}"


def test_validate_service_json(schema_dir, example_data_dir):
    """Test validation of service JSON file."""
    validator = DataValidator(example_data_dir, schema_dir)

    service_file = example_data_dir / "provider2" / "services" / "service2" / "service.json"
    is_valid, errors = validator.validate_data_file(service_file)

    if not is_valid:
        print(f"Validation errors for {service_file}:")
        for error in errors:
            print(f"  - {error}")

    assert is_valid, f"Service JSON validation failed: {errors}"


def test_validate_listing_toml(schema_dir, example_data_dir):
    """Test validation of listing TOML file."""
    validator = DataValidator(example_data_dir, schema_dir)

    listing_file = example_data_dir / "provider1" / "services" / "service1" / "svcreseller.toml"
    is_valid, errors = validator.validate_data_file(listing_file)

    if not is_valid:
        print(f"Validation errors for {listing_file}:")
        for error in errors:
            print(f"  - {error}")

    assert is_valid, f"Listing TOML validation failed: {errors}"


def test_validate_listing_json(schema_dir, example_data_dir):
    """Test validation of listing JSON file."""
    validator = DataValidator(example_data_dir, schema_dir)

    listing_file = example_data_dir / "provider2" / "services" / "service2" / "svcreseller.json"
    is_valid, errors = validator.validate_data_file(listing_file)

    if not is_valid:
        print(f"Validation errors for {listing_file}:")
        for error in errors:
            print(f"  - {error}")

    assert is_valid, f"Listing JSON validation failed: {errors}"


def test_validate_markdown_files(schema_dir, example_data_dir):
    """Test validation of markdown files."""
    validator = DataValidator(example_data_dir, schema_dir)

    md_files = [
        example_data_dir / "provider1" / "README.md",
        example_data_dir / "provider1" / "terms-of-service.md",
        example_data_dir / "provider1" / "services" / "service1" / "code-example.md",
    ]

    for md_file in md_files:
        is_valid, errors = validator.validate_md_file(md_file)

        if not is_valid:
            print(f"Validation errors for {md_file}:")
            for error in errors:
                print(f"  - {error}")

        assert is_valid, f"Markdown validation failed for {md_file}: {errors}"


def test_validate_all_files(schema_dir, example_data_dir):
    """Test validation of all files in example_data."""
    validator = DataValidator(example_data_dir, schema_dir)

    results = validator.validate_all()

    # Should have found multiple files
    assert len(results) > 0

    # Count valid vs invalid
    valid_count = sum(1 for is_valid, _ in results.values() if is_valid)
    invalid_count = len(results) - valid_count

    # Print summary
    print("\nValidation Summary:")
    print(f"  Total files: {len(results)}")
    print(f"  Valid: {valid_count}")
    print(f"  Invalid: {invalid_count}")

    if invalid_count > 0:
        print("\nInvalid files:")
        for file_path, (is_valid, errors) in results.items():
            if not is_valid:
                print(f"\n  {file_path}:")
                for error in errors:
                    print(f"    - {error}")

    # All files should be valid
    assert invalid_count == 0, f"{invalid_count} files failed validation"


def test_file_reference_validation(schema_dir, example_data_dir):
    """Test that file references are properly validated."""
    validator = DataValidator(example_data_dir, schema_dir)

    # This should validate that referenced files (like logo, documents) exist
    results = validator.validate_all()

    # Check for file reference errors
    file_ref_errors = []
    for file_path, (_is_valid, errors) in results.items():
        for error in errors:
            if "does not exist" in error or "file reference" in error.lower():
                file_ref_errors.append((file_path, error))

    if file_ref_errors:
        print("\nFile reference errors found:")
        for file_path, error in file_ref_errors:
            print(f"  {file_path}: {error}")

    # Should have no file reference errors in example data
    assert len(file_ref_errors) == 0, "File reference validation failed"
