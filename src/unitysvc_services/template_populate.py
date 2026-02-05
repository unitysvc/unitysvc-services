"""
Template-based service population utilities.

This module provides utilities for populating services using Jinja2 templates
instead of the DataBuilder APIs. This approach separates data from structure.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterator

from jinja2 import Environment, FileSystemLoader

if TYPE_CHECKING:
    pass


def populate_from_iterator(
    iterator: Iterator[dict],
    templates_dir: str | Path,
    output_dir: str | Path,
    offering_template: str = "offering.json.j2",
    listing_template: str = "listing.json.j2",
    name_field: str = "name",
    filter_func: Callable[[dict], bool] | None = None,
    dry_run: bool = False,
    deprecate_missing: bool = True,
) -> dict:
    """
    Populate services from an iterator of model dictionaries.

    This function renders Jinja2 templates with each dictionary from the iterator
    and writes the resulting offering.json and listing.json files.

    Args:
        iterator: Yields dicts with template variables. Must include `name_field`.
        templates_dir: Directory containing .j2 templates.
        output_dir: Directory to write services (creates {name}/ subdirs).
        offering_template: Filename of offering template (default: offering.json.j2).
        listing_template: Filename of listing template (default: listing.json.j2).
        name_field: Dict key to use for directory name (default: "name").
        filter_func: Optional function that takes a model dict and returns True to
            include it, False to skip. Useful for filtering without modifying iterator.
        dry_run: If True, don't write files, just report what would happen.
        deprecate_missing: If True (default), mark services that exist locally but
            are no longer in the iterator as deprecated (sets status="deprecated").

    Returns:
        Stats dict: {"total": N, "written": N, "skipped": N, "filtered": N, "errors": N, "deprecated": N}

    Example:
        >>> def iter_models():
        ...     yield {"name": "model-1", "service_type": "llm", ...}
        ...     yield {"name": "model-2", "service_type": "llm", ...}
        >>> populate_from_iterator(iter_models(), "templates", "services")

        # With filter - only include LLM models
        >>> populate_from_iterator(
        ...     iter_models(),
        ...     "templates",
        ...     "services",
        ...     filter_func=lambda m: m.get("service_type") == "llm"
        ... )
    """
    templates_dir = Path(templates_dir)
    output_dir = Path(output_dir)

    # Track existing services before iteration (for deprecation)
    existing_services: set[str] = set()
    if deprecate_missing and output_dir.exists():
        existing_services = {
            d.name for d in output_dir.iterdir()
            if d.is_dir() and (d / "offering.json").exists()
        }

    updated_services: set[str] = set()

    # Set up Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )

    # Load templates
    offering_tpl = env.get_template(offering_template)
    listing_tpl = env.get_template(listing_template)

    stats = {"total": 0, "written": 0, "skipped": 0, "filtered": 0, "errors": 0, "deprecated": 0}

    for model_data in iterator:
        stats["total"] += 1

        # Get service name for directory
        service_name = model_data.get(name_field)
        if not service_name:
            print(f"  Warning: Missing '{name_field}' field, skipping")
            stats["errors"] += 1
            continue

        # Apply filter if provided
        if filter_func is not None and not filter_func(model_data):
            stats["filtered"] += 1
            continue

        # Sanitize directory name
        dir_name = _sanitize_dirname(service_name)
        service_dir = output_dir / dir_name

        # Track this service as updated (for deprecation logic)
        updated_services.add(dir_name)

        try:
            # Render templates
            offering_json = offering_tpl.render(**model_data)
            listing_json = listing_tpl.render(**model_data)

            # Parse to validate JSON and normalize formatting
            offering_data = json.loads(offering_json)
            listing_data = json.loads(listing_json)

            if dry_run:
                print(f"  Would write: {dir_name}/")
                stats["written"] += 1
                continue

            # Create directory
            service_dir.mkdir(parents=True, exist_ok=True)

            # Smart write (skip if unchanged, preserve time_created)
            offering_written = _smart_write_json(
                service_dir / "offering.json",
                offering_data,
            )
            listing_written = _smart_write_json(
                service_dir / "listing.json",
                listing_data,
            )

            if offering_written or listing_written:
                stats["written"] += 1
            else:
                stats["skipped"] += 1

        except json.JSONDecodeError as e:
            print(f"  Error: Invalid JSON for {service_name}: {e}")
            stats["errors"] += 1
        except Exception as e:
            print(f"  Error processing {service_name}: {e}")
            stats["errors"] += 1

    # Deprecate services no longer in upstream
    if deprecate_missing and not dry_run:
        missing_services = existing_services - updated_services
        for service_name in sorted(missing_services):
            service_dir = output_dir / service_name
            if _deprecate_service(service_dir):
                stats["deprecated"] += 1
                print(f"  Deprecated: {service_name}")

    print(f"\nDone! Total: {stats['total']}, Written: {stats['written']}, "
          f"Skipped: {stats['skipped']}, Filtered: {stats['filtered']}, "
          f"Errors: {stats['errors']}, Deprecated: {stats['deprecated']}")

    return stats


def _sanitize_dirname(name: str) -> str:
    """Convert model name to valid directory name."""
    return name.replace(":", "_").replace("/", "_")


def _smart_write_json(path: Path, data: dict) -> bool:
    """
    Write JSON file only if content changed (ignoring time_created).

    Preserves original time_created if file exists and content is different.
    Adds time_created if not present.

    Returns:
        True if file was written, False if skipped (unchanged).
    """
    path = Path(path)

    # Check existing file
    if path.exists():
        try:
            existing = json.loads(path.read_text())

            # Compare without time_created
            existing_cmp = {k: v for k, v in existing.items() if k != "time_created"}
            new_cmp = {k: v for k, v in data.items() if k != "time_created"}

            if existing_cmp == new_cmp:
                return False  # No changes

            # Preserve original time_created
            if "time_created" in existing:
                data["time_created"] = existing["time_created"]

        except (json.JSONDecodeError, IOError):
            pass

    # Add time_created if not present
    if "time_created" not in data:
        data["time_created"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Write file with consistent formatting (sorted keys for deterministic output)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return True


def _deprecate_service(service_dir: Path) -> bool:
    """
    Mark a service as deprecated by updating its offering.json.

    Sets status="deprecated" if not already deprecated.

    Args:
        service_dir: Path to the service directory.

    Returns:
        True if the service was newly deprecated, False if already deprecated or error.
    """
    offering_path = service_dir / "offering.json"
    if not offering_path.exists():
        return False

    try:
        data = json.loads(offering_path.read_text())

        # Skip if already deprecated
        if data.get("status") == "deprecated":
            return False

        # Mark as deprecated
        data["status"] = "deprecated"

        offering_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        return True

    except (json.JSONDecodeError, IOError):
        return False
