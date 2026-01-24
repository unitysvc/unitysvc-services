# Development Scripts

This directory contains development and maintenance scripts for the UnitySVC Seller SDK.

## update_schema.py

Generates JSON schemas from Pydantic models.

**When to use:**

- After modifying any Pydantic model in `src/unitysvc_services/models/`
- Before committing model changes

**Usage:**

```bash
python scripts/update_schema.py
```

**What it does:**

1. Scans all Python files in `src/unitysvc_services/models/`
2. Extracts Pydantic BaseModel classes
3. Generates JSON schemas for each model
4. Writes schemas to `src/unitysvc_services/schema/`
5. Formats output to match pre-commit requirements (2-space indent, sorted keys)

**Output:**

```
src/unitysvc_services/schema/
├── base.json           # Base models and enums
├── provider_v1.json    # Provider schema
├── seller_v1.json      # Seller schema
├── offering_v1.json     # Service offering schema
└── listing_v1.json     # Service listing schema
```

The generated schemas are:

- Used for data validation in CLI commands
- Included in the package distribution
- Referenced in documentation
