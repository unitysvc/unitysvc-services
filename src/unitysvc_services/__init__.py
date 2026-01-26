"""Top-level package for UnitySvc Provider."""

__author__ = """Bo Peng"""
__email__ = "bo.peng@unitysvc.com"

# Export data builder classes for creating service data files
from .data_builder import (
    ListingDataBuilder,
    OfferingDataBuilder,
    ProviderDataBuilder,
)

# Export model data utilities for any-llm providers
from .model_data import (
    ModelDataFetcher,
    ModelDataLookup,
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
    # Data builders
    "ListingDataBuilder",
    "OfferingDataBuilder",
    "ProviderDataBuilder",
    # Model data utilities
    "ModelDataFetcher",
    "ModelDataLookup",
    # File utilities
    "compute_file_hash",
    "generate_content_based_key",
    "get_basename",
    "get_file_extension",
    "mime_type_to_extension",
]
