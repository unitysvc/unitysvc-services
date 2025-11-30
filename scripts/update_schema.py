#!/usr/bin/env python3
"""Generate JSON schemas from Pydantic models.

This script is used by maintainers after updating Pydantic models.
End users should use the pre-generated schemas included in the package.

Usage:
    python scripts/update_schema.py
"""

import importlib
import inspect
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def find_pydantic_models(module: Any, module_name: str) -> dict[str, type[BaseModel]]:
    """Find all Pydantic BaseModel classes defined in a module that have schema_version field.

    Only models with schema_version are file validation schemas (V1 models).
    Data classes used for API don't have schema_version and are skipped.
    """
    models = {}
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if (
            issubclass(obj, BaseModel)
            and obj is not BaseModel
            and obj.__module__ == module_name
            and "schema_version" in obj.model_fields  # Only V1 models with schema_version
        ):
            models[name] = obj
    return models


def generate_schema_file(model_class: type[BaseModel], output_path: Path) -> None:
    """Generate a JSON schema file for a Pydantic model."""
    schema = model_class.model_json_schema()

    # Format JSON exactly as pretty-format-json expects
    with open(output_path, "w", encoding="utf-8") as f:
        # Match pretty-format-json: 2-space indent, sorted keys, trailing newline
        json_str = json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True)
        f.write(json_str)
        f.write("\n")

    print(f"✓ Generated schema: {output_path}")


def main():
    """Generate JSON schemas from Pydantic models."""
    # Determine paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    src_dir = project_root / "src"
    models_dir = project_root / "src" / "unitysvc_services" / "models"
    schema_dir = project_root / "src" / "unitysvc_services" / "schema"

    # Add src directory to Python path to enable package imports
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    # Ensure schema directory exists
    schema_dir.mkdir(exist_ok=True)

    if not models_dir.exists():
        print(f"✗ Models directory not found: {models_dir}")
        sys.exit(1)

    print(f"Processing models from: {models_dir}")
    print(f"Output directory: {schema_dir}\n")

    # Process all Python files in models directory
    # Only models with schema_version field will generate schemas
    total_generated = 0
    for model_file in models_dir.glob("*.py"):
        if model_file.name.startswith("__"):
            continue

        print(f"Processing: {model_file.name}")

        try:
            # Import the module properly using the package structure
            module_name = f"unitysvc_services.models.{model_file.stem}"
            module = importlib.import_module(module_name)

            # Find Pydantic models defined in this module
            models = find_pydantic_models(module, module_name)

            if not models:
                print("  No Pydantic models found")
                continue

            # Generate schema for each model (one file per model)
            if model_file.stem == "base":
                # For base.py, generate a single schema with all models as definitions
                schema_filename = f"{model_file.stem}.json"
                schema_path = schema_dir / schema_filename
                first_model = next(iter(models.values()))
                generate_schema_file(first_model, schema_path)
                total_generated += 1
            else:
                # For other files, assume one main model per file
                for model_class in models.values():
                    schema_filename = f"{model_file.stem}.json"
                    schema_path = schema_dir / schema_filename
                    generate_schema_file(model_class, schema_path)
                    total_generated += 1
                    break  # Only generate once per file

        except Exception as e:
            print(f"  ✗ Error: {e}")

    print(f"\n✓ Generated {total_generated} schema(s)")


if __name__ == "__main__":
    main()
