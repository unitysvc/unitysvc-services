# Schema Directory

This directory contains **JSON schemas** automatically generated from Pydantic models for validating business data. These schemas ensure data consistency and integrity across the repository.

## 📋 Schema Files

### Core Schemas

- **`base.json`** - Base types and enums used across all schemas
  - Common enums (ServiceTypeEnum, SellerTypeEnum, etc.)
  - Shared data structures (Document, UpstreamInterface, etc.)
  - Reusable field definitions

### Business Entity Schemas

- **`provider_v1.json`** - Validates provider business data
  - Company information (name, homepage, contact emails)
  - Terms of service references (file paths or URLs)
  - Business relationship metadata
  - Provider access information and service population configuration

- **`seller_v1.json`** - Validates seller business data
  - Seller identification (name, display name, type)
  - Contact information (primary and secondary emails)
  - Account management (account_manager field)
  - Business registration and tax information
  - Stripe Connect integration
  - Status flags (is_active, is_verified)
  - Logo and document references

### Service Schemas

- **`offering_v1.json`** - Validates service offering technical data
  - Service specifications (name, category, description)
  - Technical details (context length, API methods)
  - Business information (pricing, providers, SLA)
  - Integration details (documentation, code examples)
  - Upstream interfaces and pricing

- **`listing_v1.json`** - Validates service listing marketplace data
  - Service reference (service_name, service_version)
  - Provider and seller information
  - User-facing pricing and access interfaces
  - Listing status and metadata

## 🔧 Schema Generation

Schemas are automatically generated from Pydantic models using the dev CLI:

```bash
# Generate all schemas
python -m unitysvc_services.dev_cli
```

This generates 5 schema files:
- `base.json` - Base types and enums
- `provider_v1.json` - Provider schema
- `seller_v1.json` - Seller schema
- `offering_v1.json` - Service offering schema
- `listing_v1.json` - Service listing schema

### Source Models

All models are located in `src/unitysvc_services/models/`:
- **Base Model**: `base.py` - Common types and enums
- **Provider Model**: `provider_v1.py`
- **Seller Model**: `seller_v1.py`
- **Service Model**: `offering_v1.py`
- **Listing Model**: `listing_v1.py`

## ✅ Validation Features

### JSON Schema Compliance

- **Type validation** for all fields
- **Required field enforcement**
- **Format validation** (emails, URLs)
- **Enum value constraints**
- **Pattern matching** for identifiers

### Union Field Validation

For `Union[str, HttpUrl]` fields:
- ✓ **URL validation** - Proper URL format checking
- ✓ **File reference validation** - Ensures referenced files exist
- ✓ **Path resolution** - Relative paths resolved to same directory

### Repository-Level Validation

- **Seller uniqueness** - Each repository must have exactly one seller.json file
- **File consistency** - All referenced files must exist
- **Schema matching** - Data files matched to correct schema version

### Examples of Validated Fields

```json
{
  "schema": "seller_v1",
  "name": "acme-corp",
  "display_name": "ACME Corporation",
  "seller_type": "organization",
  "contact_email": "contact@acme.com",
  "account_manager": "admin",
  "terms_of_service": "terms.md",           // File must exist
  "documentation": "https://api.acme.com",  // Valid URL
  "is_active": true,
  "is_verified": false
}
```

## 🔍 Usage in Validation

Schemas are used by the unitysvc_services CLI:

```bash
# Validate all data files in a directory
unitysvc_services validate-data [data_dir]

# Validate specific repository
unitysvc_services validate-data /path/to/repo/data
```

### Validation Process

1. **Schema Loading** - All JSON schemas loaded from this directory
2. **Data Matching** - Data files matched to schemas via `schema` field
3. **Validation** - Data validated against corresponding schema
4. **File Checking** - Referenced files validated for existence
5. **Uniqueness Checks** - Repository-level constraints verified (e.g., single seller)

### Validation Results

```
Validation Results: 564/564 files valid
==================================================
✓ VALID: provider.toml
✓ VALID: seller.json
✓ VALID: services/llama-3.1-8b/offering.json
✓ VALID: services/llama-3.1-8b/listing-svcreseller.json
...
✓ All files valid!
```

## 📦 Publishing Workflow

After validation, data can be published to the backend:

```bash
# Publish providers
unitysvc_services publish-providers [data_dir]

# Publish sellers
unitysvc_services publish-sellers [data_dir]

# Publish service offerings
unitysvc_services publish-offerings [data_dir]

# Publish service listings
unitysvc_services publish-listings [data_dir]
```

### Publishing Order

The correct order for publishing is:
1. **Providers** - Must exist before offerings
2. **Sellers** - Must exist before listings
3. **Service Offerings** - Links providers to services
4. **Service Listings** - Links sellers to offerings

## 📌 Schema Versioning

### Naming Convention

- Format: `{schema_name}.json`
- Examples: `provider_v1.json`, `seller_v1.json`, `offering_v1.json`

### Version Management

- **Model Updates** - Modify source Pydantic models in `models/`
- **Schema Regeneration** - Run `python -m unitysvc_services.dev_cli`
- **Data Migration** - Update existing data files to match new schema
- **Backward Compatibility** - Consider migration path for breaking changes

## ⚠️ Important Notes

- **Auto-Generated**: Do not manually edit schema files
- **Source of Truth**: Pydantic models in `src/unitysvc_services/models/` are authoritative
- **Consistency**: Schemas must be regenerated after any model changes
- **Breaking Changes**: Model updates may require data migration in repositories

## 🔗 Related Files

- **Source Models**: [`src/unitysvc_services/models/`](../models/)
- **Generation Script**: [`src/unitysvc_services/dev_cli.py`](../dev_cli.py)
- **Validation Module**: [`src/unitysvc_services/validator.py`](../validator.py)
- **CLI Tool**: [`src/unitysvc_services/cli.py`](../cli.py)
- **Publisher Module**: [`src/unitysvc_services/publisher.py`](../publisher.py)

## 📚 Additional Resources

- **Main README**: [`../../README.md`](../../README.md)
- **Example Data**: Test data available in `tests/example_data/`
- **Backend API**: Publishing endpoints in `unitysvc/backend/app/api/routes/publish.py`
