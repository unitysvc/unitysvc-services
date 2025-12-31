"""Markdown processing utilities for document publishing.

This module provides utilities for:
- Parsing markdown to identify local file attachments (images, links)
- Computing content-based object keys locally (no network calls)
- Revising markdown content to use $UNITYSVC_S3_BASE_URL placeholder
- Batch uploading attachments when ready to publish

The $UNITYSVC_S3_BASE_URL placeholder is replaced at retrieval time with the
actual S3 base URL, making content environment-agnostic.
"""

import mimetypes
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import mistune
from mistune.renderers.markdown import MarkdownRenderer

from .utils import generate_content_based_key, get_file_extension

if TYPE_CHECKING:
    from .publisher import ServiceDataPublisher


@dataclass
class Attachment:
    """Represents a local file attachment found in markdown content."""

    original_path: str  # The path as written in markdown (e.g., "./images/diagram.png")
    absolute_path: Path  # Resolved absolute path to the file
    object_key: str  # Computed content-based key (hash.extension)
    is_public: bool = True  # Whether the attachment should be publicly accessible

    def __hash__(self) -> int:
        return hash(self.absolute_path)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Attachment):
            return False
        return self.absolute_path == other.absolute_path


@dataclass
class MarkdownProcessingResult:
    """Result of processing markdown content."""

    content: str  # Revised markdown content with $UNITYSVC_S3_BASE_URL placeholders
    attachments: list[Attachment] = field(default_factory=list)  # Attachments to upload


class AttachmentExtractor(MarkdownRenderer):
    """Custom mistune renderer that extracts local file references."""

    def __init__(self) -> None:
        super().__init__()
        self.attachments: list[dict[str, str | bool]] = []

    def image(self, token: dict[str, Any], state: Any) -> str:
        """Extract image references."""
        src = token.get("src", "")
        if src and not src.startswith(("http://", "https://", "$UNITYSVC_S3_BASE_URL")):
            self.attachments.append(
                {
                    "path": src,
                    "is_image": True,
                }
            )
        return super().image(token, state)

    def link(self, token: dict[str, Any], state: Any) -> str:
        """Extract link references to local files."""
        href = token.get("link", "")
        if href and not href.startswith(("http://", "https://", "#", "mailto:", "$UNITYSVC_S3_BASE_URL")):
            # Check if it looks like a file reference (has extension or is a path)
            if "." in Path(href).name or "/" in href:
                self.attachments.append(
                    {
                        "path": href,
                        "is_image": False,
                    }
                )
        return super().link(token, state)


def get_mime_type_from_path(file_path: Path) -> str:
    """Determine MIME type from file path.

    Args:
        file_path: Path to the file

    Returns:
        MIME type string (e.g., "image/png", "application/pdf")
    """
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type or "application/octet-stream"


def process_markdown_content(
    markdown_content: str,
    base_path: Path,
    is_public: bool = True,
) -> MarkdownProcessingResult:
    """Process markdown content to identify attachments and revise paths.

    This function:
    1. Parses markdown to find local file attachments
    2. Computes content-based object_key for each attachment (no network calls)
    3. Replaces local paths with $UNITYSVC_S3_BASE_URL/{object_key}
    4. Returns the revised content and list of attachments for later upload

    The $UNITYSVC_S3_BASE_URL placeholder is replaced at retrieval time with
    the actual S3 base URL, making the content environment-agnostic.

    Args:
        markdown_content: The markdown content to process
        base_path: Base directory for resolving relative paths
        is_public: Whether attachments should be publicly accessible

    Returns:
        MarkdownProcessingResult with revised content and attachments list

    Example:
        Input:  "![Logo](./images/logo.png)"
        Output: MarkdownProcessingResult(
            content="![Logo]($UNITYSVC_S3_BASE_URL/abc123def.png)",
            attachments=[Attachment(...)]
        )
    """
    # Use mistune to parse markdown and extract attachments
    extractor = AttachmentExtractor()
    md = mistune.create_markdown(renderer=extractor)
    md(markdown_content)

    if not extractor.attachments:
        return MarkdownProcessingResult(content=markdown_content, attachments=[])

    # Build mapping from original path to object_key
    path_to_attachment: dict[str, Attachment] = {}
    unique_attachments: list[Attachment] = []

    for item in extractor.attachments:
        original_path = str(item["path"])

        # Skip if already processed
        if original_path in path_to_attachment:
            continue

        # Resolve the path relative to base_path
        if Path(original_path).is_absolute():
            absolute_path = Path(original_path)
        else:
            absolute_path = (base_path / original_path).resolve()

        # Skip if file doesn't exist
        if not absolute_path.exists():
            continue

        # Read file and compute object_key
        with open(absolute_path, "rb") as f:
            content = f.read()

        extension = get_file_extension(absolute_path.name)
        object_key = generate_content_based_key(content, extension)

        attachment = Attachment(
            original_path=original_path,
            absolute_path=absolute_path,
            object_key=object_key,
            is_public=is_public,
        )
        path_to_attachment[original_path] = attachment
        unique_attachments.append(attachment)

    # Replace paths in markdown
    # Pattern for images: ![...](path) or links: [...](path)
    result = markdown_content
    for original_path, attachment in path_to_attachment.items():
        escaped_path = re.escape(original_path)
        pattern = rf"(!?\[[^\]]*\]\()({escaped_path})(\))"
        new_url = f"$UNITYSVC_S3_BASE_URL/{attachment.object_key}"
        result = re.sub(pattern, rf"\g<1>{new_url}\g<3>", result)

    return MarkdownProcessingResult(content=result, attachments=unique_attachments)


async def upload_attachments(
    publisher: "ServiceDataPublisher",
    attachments: list[Attachment],
) -> dict[str, bool]:
    """Upload attachments to the backend.

    Checks if each object already exists before uploading to save bandwidth.
    Only uploads files that don't already exist in storage.

    Args:
        publisher: ServiceDataPublisher instance for making API calls
        attachments: List of attachments to upload

    Returns:
        Dict mapping object_key to upload status (True=uploaded, False=already existed)

    Raises:
        ValueError: If upload fails for any attachment
    """
    import httpx

    results: dict[str, bool] = {}

    for attachment in attachments:
        # First check if the object already exists (saves bandwidth)
        try:
            check_response = await publisher.client.get(
                f"{publisher.base_url}/documents/{attachment.object_key}/exists",
            )
            if check_response.status_code == 200:
                check_data = check_response.json()
                if check_data.get("exists", False):
                    # Object already exists, skip upload
                    results[attachment.object_key] = False
                    continue
        except httpx.ConnectError:
            raise ValueError(f"Failed to connect to backend for checking '{attachment.absolute_path.name}'")

        # Object doesn't exist, proceed with upload
        with open(attachment.absolute_path, "rb") as f:
            file_content = f.read()

        mime_type = get_mime_type_from_path(attachment.absolute_path)

        # Prepare multipart form data
        files = {
            "file": (attachment.absolute_path.name, file_content, mime_type),
        }
        data = {
            "is_public": str(attachment.is_public).lower(),
        }

        # Upload via backend API using multipart/form-data
        try:
            response = await publisher.client.post(
                f"{publisher.base_url}/documents/attachments",
                files=files,
                data=data,
            )
            status_code = response.status_code
            response_json = response.json()
        except httpx.ConnectError:
            raise ValueError(f"Failed to connect to backend for uploading '{attachment.absolute_path.name}'")

        if status_code >= 400:
            error_detail = response_json.get("detail", str(response_json))
            raise ValueError(f"Failed to upload attachment '{attachment.absolute_path.name}': {error_detail}")

        # Track whether it was newly uploaded or already existed
        results[attachment.object_key] = response_json.get("uploaded", True)

    return results
