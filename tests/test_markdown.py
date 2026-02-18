"""Tests for markdown processing utilities."""

from pathlib import Path

import pytest

from unitysvc_services.markdown import process_markdown_content


@pytest.fixture
def tmp_images(tmp_path: Path) -> Path:
    """Create temporary image files for testing."""
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    (images_dir / "test.png").write_bytes(b"fake png content")
    (images_dir / "test.jpg").write_bytes(b"fake jpg content")
    (images_dir / "screenshot.png").write_bytes(b"fake screenshot content")
    return tmp_path


def test_markdown_image_extraction(tmp_images: Path) -> None:
    """Standard markdown image syntax is detected and rewritten."""
    md = "![alt text](images/test.png)"
    result = process_markdown_content(md, tmp_images)

    assert len(result.attachments) == 1
    assert result.attachments[0].original_path == "images/test.png"
    assert "$UNITYSVC_S3_BASE_URL/" in result.content
    assert "images/test.png" not in result.content


def test_html_img_tag_extraction(tmp_images: Path) -> None:
    """HTML <img src="..."> tags are detected and rewritten."""
    md = '<img src="images/test.jpg" width="400">'
    result = process_markdown_content(md, tmp_images)

    assert len(result.attachments) == 1
    assert result.attachments[0].original_path == "images/test.jpg"
    assert "$UNITYSVC_S3_BASE_URL/" in result.content
    assert 'src="images/test.jpg"' not in result.content


def test_html_img_in_table(tmp_images: Path) -> None:
    """HTML img tags inside table cells are handled."""
    md = '<td><img src="images/test.jpg" width="300"></td>'
    result = process_markdown_content(md, tmp_images)

    assert len(result.attachments) == 1
    assert "$UNITYSVC_S3_BASE_URL/" in result.content
    assert 'src="images/test.jpg"' not in result.content


def test_mixed_markdown_and_html_images(tmp_images: Path) -> None:
    """Both markdown and HTML images in the same document are extracted."""
    md = '![alt](images/test.png)\n\n<img src="images/test.jpg" width="400">'
    result = process_markdown_content(md, tmp_images)

    assert len(result.attachments) == 2
    paths = {a.original_path for a in result.attachments}
    assert paths == {"images/test.png", "images/test.jpg"}
    assert "images/test.png" not in result.content
    assert 'src="images/test.jpg"' not in result.content


def test_external_urls_ignored(tmp_images: Path) -> None:
    """HTTP/HTTPS URLs are not extracted as attachments."""
    md = '![logo](https://example.com/logo.png)\n\n<img src="https://cdn.example.com/img.jpg">'
    result = process_markdown_content(md, tmp_images)

    assert len(result.attachments) == 0
    assert result.content == md


def test_already_processed_urls_ignored(tmp_images: Path) -> None:
    """$UNITYSVC_S3_BASE_URL paths are not re-extracted."""
    md = "![logo]($UNITYSVC_S3_BASE_URL/abc123.png)"
    result = process_markdown_content(md, tmp_images)

    assert len(result.attachments) == 0
    assert result.content == md


def test_nonexistent_files_skipped(tmp_images: Path) -> None:
    """References to missing files don't produce attachments or errors."""
    md = "![missing](images/does_not_exist.png)"
    result = process_markdown_content(md, tmp_images)

    assert len(result.attachments) == 0


def test_deduplication(tmp_images: Path) -> None:
    """Same image referenced twice produces one attachment."""
    md = "![first](images/test.png)\n\n![second](images/test.png)"
    result = process_markdown_content(md, tmp_images)

    assert len(result.attachments) == 1
    # Both references should be rewritten
    assert "images/test.png" not in result.content
    assert result.content.count("$UNITYSVC_S3_BASE_URL/") == 2


def test_html_img_single_quotes(tmp_images: Path) -> None:
    """HTML img tags with single-quoted src are handled."""
    md = "<img src='images/test.png' width='300'>"
    result = process_markdown_content(md, tmp_images)

    assert len(result.attachments) == 1
    assert "$UNITYSVC_S3_BASE_URL/" in result.content
