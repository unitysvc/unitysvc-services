"""Top-level package for UnitySvc Provider."""

__author__ = """Bo Peng"""
__email__ = "bo.peng@unitysvc.com"

# Export model data utilities for any-llm providers
from .model_data import (
    ModelDataFetcher,
    ModelDataLookup,
)

# Export template-based population utilities
from .template_populate import (
    populate_from_iterator,
)

# Export shared utilities for use by unitysvc backend and SDK consumers
from .utils import (
    compute_file_hash,
    generate_content_based_key,
    get_basename,
    get_file_extension,
    mime_type_to_extension,
)

__all__ = [
    # Model data utilities
    "ModelDataFetcher",
    "ModelDataLookup",
    # Template population
    "populate_from_iterator",
    # File utilities
    "compute_file_hash",
    "generate_content_based_key",
    "get_basename",
    "get_file_extension",
    "mime_type_to_extension",
]
