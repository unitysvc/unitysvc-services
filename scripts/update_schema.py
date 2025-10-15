#!/usr/bin/env python3
"""Generate JSON schemas from Pydantic models.

This script is used by maintainers after updating Pydantic models.
End users should use the pre-generated schemas included in the package.

Usage:
    python scripts/update_schema.py
"""

import importlib.util
import inspect
import json
import sys
import types
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def load_module_from_file(file_path: Path) -> Any:
    """Load a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {file_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def find_pydantic_models(module: Any) -> dict[str, type[BaseModel]]:
    """Find all Pydantic BaseModel classes in a module."""
    models = {}
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, BaseModel) and obj is not BaseModel and obj.__module__ == module.__name__:
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
    models_dir = project_root / "src" / "unitysvc_services" / "models"
    schema_dir = project_root / "src" / "unitysvc_services" / "schema"

    # Add project root to Python path to enable imports
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Set up module aliasing for scripts.models.base
    # Models import from scripts.models.base which is the pattern used in business-data repos
    # Create fake module hierarchy
    scripts_module = types.ModuleType("scripts")
    scripts_models_module = types.ModuleType("scripts.models")
    sys.modules["scripts"] = scripts_module
    sys.modules["scripts.models"] = scripts_models_module

    # Load base module directly
    base_path = models_dir / "base.py"
    spec = importlib.util.spec_from_file_location("scripts.models.base", base_path)
    if spec and spec.loader:
        base_module = importlib.util.module_from_spec(spec)
        sys.modules["scripts.models.base"] = base_module
        spec.loader.exec_module(base_module)
        scripts_models_module.base = base_module

    # Ensure schema directory exists
    schema_dir.mkdir(exist_ok=True)

    if not models_dir.exists():
        print(f"✗ Models directory not found: {models_dir}")
        sys.exit(1)

    print(f"Processing models from: {models_dir}")
    print(f"Output directory: {schema_dir}\n")

    # Process all Python files in models directory
    total_generated = 0
    for model_file in models_dir.glob("*.py"):
        if model_file.name.startswith("__"):
            continue

        print(f"Processing: {model_file.name}")

        try:
            # Load the module
            module = load_module_from_file(model_file)

            # Find Pydantic models
            models = find_pydantic_models(module)

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
