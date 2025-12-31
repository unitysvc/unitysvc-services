"""Top-level package for UnitySvc Provider."""

__author__ = """Bo Peng"""
__email__ = "bo.peng@unitysvc.com"

# Export shared utilities for use by unitysvc backend and SDK consumers
from .utils import (
    compute_file_hash,
    generate_content_based_key,
    get_basename,
    get_file_extension,
    mime_type_to_extension,
)

__all__ = [
    "compute_file_hash",
    "generate_content_based_key",
    "get_basename",
    "get_file_extension",
    "mime_type_to_extension",
]
