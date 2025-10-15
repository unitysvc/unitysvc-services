"""Tests for utility functions."""

from pathlib import Path

import pytest

from unitysvc_services.utils import (
    convert_convenience_fields_to_documents,
    resolve_provider_name,
    resolve_service_name_for_listing,
)


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


def test_convert_logo_file_path_to_document(tmp_path: Path) -> None:
    """Test converting logo file path to Document."""
    data = {"name": "test-provider", "logo": "assets/logo.png", "documents": []}

    result = convert_convenience_fields_to_documents(data, tmp_path)

    # Logo field should be removed
    assert "logo" not in result

    # Document should be added
    assert len(result["documents"]) == 1
    doc = result["documents"][0]
    assert doc["title"] == "Company Logo"
    assert doc["category"] == "logo"
    assert doc["mime_type"] == "png"
    assert doc["file_path"] == "assets/logo.png"
    assert "external_url" not in doc
    assert doc["is_public"] is True


def test_convert_logo_url_to_document(tmp_path: Path) -> None:
    """Test converting logo URL to Document."""
    data = {"name": "test-provider", "logo": "https://example.com/logo.svg", "documents": None}

    result = convert_convenience_fields_to_documents(data, tmp_path)

    # Logo field should be removed
    assert "logo" not in result

    # Document should be added
    assert len(result["documents"]) == 1
    doc = result["documents"][0]
    assert doc["title"] == "Company Logo"
    assert doc["category"] == "logo"
    assert doc["mime_type"] == "svg"
    assert doc["external_url"] == "https://example.com/logo.svg"
    assert "file_path" not in doc
    assert doc["is_public"] is True


def test_convert_terms_of_service_to_document(tmp_path: Path) -> None:
    """Test converting terms_of_service to Document."""
    data = {
        "name": "test-provider",
        "logo": "logo.png",
        "terms_of_service": "docs/terms.md",
        "documents": [],
    }

    result = convert_convenience_fields_to_documents(data, tmp_path)

    # Both convenience fields should be removed
    assert "logo" not in result
    assert "terms_of_service" not in result

    # Two documents should be added
    assert len(result["documents"]) == 2

    # Check logo document
    logo_doc = result["documents"][0]
    assert logo_doc["title"] == "Company Logo"
    assert logo_doc["category"] == "logo"

    # Check terms document
    terms_doc = result["documents"][1]
    assert terms_doc["title"] == "Terms of Service"
    assert terms_doc["category"] == "terms_of_service"
    assert terms_doc["mime_type"] == "markdown"
    assert terms_doc["file_path"] == "docs/terms.md"
    assert terms_doc["is_public"] is True


def test_convert_seller_logo_only(tmp_path: Path) -> None:
    """Test converting seller logo (no terms_of_service)."""
    data = {"name": "test-seller", "logo": "logo.jpeg"}

    # Sellers don't have terms_of_service, so we pass None
    result = convert_convenience_fields_to_documents(data, tmp_path, terms_field=None)

    # Logo field should be removed
    assert "logo" not in result

    # Only one document should be added
    assert len(result["documents"]) == 1
    doc = result["documents"][0]
    assert doc["title"] == "Company Logo"
    assert doc["mime_type"] == "jpeg"


def test_convert_no_convenience_fields(tmp_path: Path) -> None:
    """Test when no convenience fields are present."""
    data = {"name": "test-provider", "documents": [{"title": "Existing Doc"}]}

    result = convert_convenience_fields_to_documents(data, tmp_path)

    # Original document should still be there
    assert len(result["documents"]) == 1
    assert result["documents"][0]["title"] == "Existing Doc"


def test_convert_mime_type_detection(tmp_path: Path) -> None:
    """Test MIME type detection for various file types."""
    test_cases = [
        ("logo.png", "png"),
        ("logo.jpg", "jpeg"),
        ("logo.svg", "svg"),
        ("terms.pdf", "pdf"),
        ("terms.md", "markdown"),
        ("https://example.com/doc", "url"),
    ]

    for file_path, expected_mime in test_cases:
        data = {"logo": file_path}
        result = convert_convenience_fields_to_documents(data, tmp_path, terms_field=None)
        assert result["documents"][0]["mime_type"] == expected_mime
