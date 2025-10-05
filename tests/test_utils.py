"""Tests for utility functions."""

from pathlib import Path

import pytest

from unitysvc_services.utils import resolve_provider_name, resolve_service_name_for_listing


@pytest.fixture
def example_data_dir() -> Path:
    """Return the example data directory."""
    return Path(__file__).parent / "example_data"


def test_resolve_service_name_explicit(example_data_dir: Path) -> None:
    """Test that explicit service_name in listing is used."""
    from unitysvc_services.utils import find_files_by_schema

    # Find a listing with explicit service_name
    listing_files = find_files_by_schema(example_data_dir, "listing_v1")

    # Find the provider2 listing which has explicit service_name
    for file_path, _format, data in listing_files:
        if "provider2" in str(file_path):
            service_name = resolve_service_name_for_listing(file_path, data)
            assert service_name == "example-service-2"
            break
    else:
        pytest.fail("No provider2 listing found")


def test_resolve_service_name_auto(example_data_dir: Path) -> None:
    """Test that service_name is auto-resolved from service offering."""
    from unitysvc_services.utils import find_files_by_schema

    # Find a listing without explicit service_name
    listing_files = find_files_by_schema(example_data_dir, "listing_v1")

    # Find the provider1 listing which should auto-resolve
    for file_path, _format, data in listing_files:
        if "provider1" in str(file_path):
            # Remove service_name if present to test auto-resolution
            data_without_service_name = {k: v for k, v in data.items() if k != "service_name"}
            service_name = resolve_service_name_for_listing(file_path, data_without_service_name)
            assert service_name == "service1"
            break
    else:
        pytest.fail("No provider1 listing found")


def test_resolve_service_name_no_service_offering(tmp_path: Path) -> None:
    """Test that None is returned when no service offering exists."""
    # Create a listing file without a service offering
    listing_file = tmp_path / "listing.json"
    listing_data = {"schema": "listing_v1"}

    service_name = resolve_service_name_for_listing(listing_file, listing_data)
    assert service_name is None


def test_resolve_provider_name_from_service_offering(example_data_dir: Path) -> None:
    """Test that provider name is resolved from service offering file path."""
    from unitysvc_services.utils import find_files_by_schema

    # Find a service offering file
    service_files = find_files_by_schema(example_data_dir, "service_v1")

    # Find the provider1 service file
    for file_path, _format, _data in service_files:
        if "provider1" in str(file_path):
            provider_name = resolve_provider_name(file_path)
            assert provider_name == "provider1"
            break
    else:
        pytest.fail("No provider1 service file found")


def test_resolve_provider_name_from_listing(example_data_dir: Path) -> None:
    """Test that provider name is resolved from listing file path."""
    from unitysvc_services.utils import find_files_by_schema

    # Find a listing file
    listing_files = find_files_by_schema(example_data_dir, "listing_v1")

    # Find the provider2 listing file
    for file_path, _format, _data in listing_files:
        if "provider2" in str(file_path):
            provider_name = resolve_provider_name(file_path)
            assert provider_name == "provider2"
            break
    else:
        pytest.fail("No provider2 listing file found")


def test_resolve_provider_name_invalid_path(tmp_path: Path) -> None:
    """Test that None is returned for invalid path structure."""
    # Create a file not under a "services" directory
    invalid_file = tmp_path / "some_file.json"

    provider_name = resolve_provider_name(invalid_file)
    assert provider_name is None
