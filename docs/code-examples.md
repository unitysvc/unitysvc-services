# Creating and Testing Code Examples

This guide explains how to create, test, and publish code examples for your services on the UnitySVC platform.

## Overview

Code examples help users understand how to interact with your services. The UnitySVC Services SDK provides a complete workflow for:

- Creating executable code examples in multiple languages (Python, JavaScript, Shell)
- Using Jinja2 templates for dynamic content
- Testing examples against upstream APIs
- Validating output automatically
- Publishing examples with your service listings

## Test Command

The `test` command helps validate code examples against upstream APIs before publishing.

### Listing Code Examples

```bash
# List all available code examples
usvc test list

# List examples for a specific provider
usvc test list --provider fireworks

# List examples for specific services (supports wildcards)
usvc test list --services "llama*,gpt-4*"
```

The output shows:
- Service name
- Provider name
- Example title
- File type (.py, .js, .sh, etc.)
- Relative file path from data directory

### Running Tests

```bash
# Run all code examples
usvc test run

# Run tests for a specific provider
usvc test run --provider fireworks

# Run tests for specific services (supports wildcards)
usvc test run --services "code-llama-*"

# Show verbose output including stdout/stderr
usvc test run --verbose
```

**How tests work:**

1. Test framework discovers code examples from listing files (category = `code_examples`)
2. Renders Jinja2 templates with listing, offering, provider, and seller data
3. Sets environment variables (API_KEY, API_ENDPOINT) from provider credentials
4. Executes the code example using appropriate interpreter (python3, node, bash)
5. Validates results:
   - Test passes if exit code is 0 AND (no `expect` field OR expected string found in stdout)
   - Test fails if exit code is non-zero OR expected string not found

**Failed test debugging:**

When a test fails, the rendered content is automatically saved to the current directory:

```bash
# Example output:
Testing: llama-3-1-405b - Python code example
  ✗ Failed - Output validation failed: expected substring '✓ Test passed' not found
  → Test content saved to: failed_llama-3-1-405b_Python_code_example.py

# The saved file includes:
# - Environment variables used (API_KEY, API_ENDPOINT)
# - Full rendered template content
# - You can run it directly to reproduce the issue
```

## Developing Code Examples

This section provides a step-by-step guide for creating and testing code examples for your services.

### Step 1: Develop and Test the Script Locally

Start by writing a working script using actual values. This allows you to verify the API works correctly before templating.

**Example: `test.py` (initial version)**

```python
#!/usr/bin/env python3
"""Test script for llama-3-1-405b"""
import httpx
import os

# Hardcoded values for initial testing
response = httpx.post(
    "https://api.fireworks.ai/inference/v1/chat/completions",
    headers={"Authorization": "Bearer fw_abc123xyz789"},
    json={
        "model": "accounts/fireworks/models/llama-v3p1-405b-instruct",
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_tokens": 50
    }
)

print(response.json())
if response.status_code == 200 and "choices" in response.json():
    print("✓ Test passed")
```

**Test it:**

```bash
python3 test.py
# Verify it works and outputs "✓ Test passed"
```

### Step 2: Use Environment Variables

Replace hardcoded credentials with environment variables to avoid exposing sensitive data.

**Example: `test.py` (with environment variables)**

```python
#!/usr/bin/env python3
"""Test script for llama-3-1-405b"""
import httpx
import os

# Use environment variables
API_KEY = os.environ.get("API_KEY")
API_ENDPOINT = os.environ.get("API_ENDPOINT")

response = httpx.post(
    f"{API_ENDPOINT}/chat/completions",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "model": "accounts/fireworks/models/llama-v3p1-405b-instruct",
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_tokens": 50
    }
)

print(response.json())
if response.status_code == 200 and "choices" in response.json():
    print("✓ Test passed")
```

**Test with environment variables:**

```bash
export API_KEY="fw_abc123xyz789"
export API_ENDPOINT="https://api.fireworks.ai/inference/v1"
python3 test.py
```

### Step 3: Replace Static Values with Template Variables

Convert hardcoded service-specific values to Jinja2 template variables and rename the file to `.j2`.

**Example: `test.py.j2` (templated version)**

```python
#!/usr/bin/env python3
"""Test script for {{ offering.name }}"""
import httpx
import os

# Use environment variables (set by test framework)
API_KEY = os.environ.get("API_KEY")
API_ENDPOINT = os.environ.get("API_ENDPOINT")

response = httpx.post(
    f"{API_ENDPOINT}/chat/completions",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "model": "{{ offering.name }}",  # Template variable
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_tokens": 50
    }
)

print(response.json())
if response.status_code == 200 and "choices" in response.json():
    print("✓ Test passed")
```

**Common template variables:**

- `{{ offering.name }}` - Service/model name
- `{{ provider.provider_name }}` - Provider name
- `{{ listing.service_name }}` - Service name from listing
- `{{ provider.provider_access_info.api_endpoint }}` - Provider API endpoint
- `{{ listing.field_name }}` - Any field from the listing
- `{{ seller.seller_name }}` - Seller name

**File renamed:** `test.py` → `test.py.j2`

### Step 4: Add to Listing Documentation

Reference the code example in your `listing.json` file.

**Example: `listing.json`**

```json
{
    "schema": "listing_v1",
    "service_name": "llama-3-1-405b-instruct",
    "listing_type": "svcreseller",
    "user_access_interfaces": [
        {
            "interface_type": "openai_chat_completions",
            "documents": [
                {
                    "category": "code_examples",
                    "title": "Python code example",
                    "file_path": "../../docs/test.py.j2",
                    "mime_type": "python",
                    "is_public": true,
                    "requirements": ["httpx"],
                    "expect": "✓ Test passed"
                }
            ]
        }
    ]
}
```

**Important fields:**

- `category`: Must be `"code_examples"` for test framework to find it
- `title`: Descriptive name for the example
- `file_path`: Relative path from listing file to your `.j2` template
- `mime_type`: File type (`python`, `javascript`, `shell`, etc.)
- `is_public`: Should be `true` for code examples
- `requirements`: **[Optional]** List of package dependencies needed to run the code example
  - For Python: PyPI packages (e.g., `["httpx", "openai"]`)
  - For JavaScript: npm packages (e.g., `["node-fetch"]`)
  - Helps users understand what to install before running the example
- `expect`: **[Optional but strongly recommended]** Expected substring that should appear in stdout when the test passes
  - Examples:
    - `"✓ Test passed"` - Explicit success message
    - `"\"choices\""` - Check for JSON field in API response
    - `"Status: 200"` - Check for HTTP status
  - Without this field, tests only check exit code (0 = pass, non-zero = fail)

### Step 5: Validate and Test Before Publishing

Run the validation and testing commands to ensure everything works correctly.

**Step 5.1: Validate schema and templates**

```bash
# Validate all files including Jinja2 syntax
usvc validate

# Expected output:
# ✓ All files validated successfully
```

**Step 5.2: List code examples**

```bash
# Verify your code example is detected
usvc test list

# Should show:
# Service: llama-3-1-405b-instruct
# Provider: fireworks
# Title: Python code example
# Type: .py
# File Path: fireworks/docs/test.py.j2
```

**Step 5.3: Run tests**

```bash
# Test your specific provider
usvc test run --provider fireworks

# Or test specific services
usvc test run --services "llama*"

# Expected output:
# Testing: llama-3-1-405b-instruct - Python code example
#   ✓ Success (exit code: 0)
```

**Step 5.4: Fix any failures**

If tests fail, the rendered content is saved to the current directory for debugging:

```bash
# If test fails, you'll see:
#   ✗ Failed - Output validation failed: expected substring '✓ Test passed' not found
#   → Test content saved to: failed_llama-3-1-405b_Python_code_example.py
#   (includes environment variables for reproduction)

# Debug the saved file:
cat failed_llama-3-1-405b_Python_code_example.py

# The file will contain:
# - Environment variables used (API_KEY, API_ENDPOINT)
# - Full rendered template content
# - You can run it directly to reproduce the issue
```

**Step 5.5: Publish when ready**

```bash
# Only publish after all tests pass
usvc publish
```

## Common Patterns

### Pattern 1: Simple shell script with expect

**File: `test.sh.j2`**

```bash
#!/bin/bash
# Simple test that outputs JSON response

curl ${API_ENDPOINT}/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -d '{"model": "{{ offering.name }}", "messages": [{"role": "user", "content": "test"}]}'
```

**In `listing.json`:**

```json
{
    "file_path": "test.sh.j2",
    "expect": "\"choices\""
}
```

### Pattern 2: Python with validation

**File: `test.py.j2`**

```python
#!/usr/bin/env python3
import httpx
import os

response = httpx.post(
    f"{os.environ['API_ENDPOINT']}/chat/completions",
    headers={"Authorization": f"Bearer {os.environ['API_KEY']}"},
    json={"model": "{{ offering.name }}", "messages": [{"role": "user", "content": "test"}]}
)

data = response.json()

# Print response and validation message
print(data)
if "choices" in data:
    print("✓ Validation passed")  # Will be checked by expect
```

**In `listing.json`:**

```json
{
    "file_path": "test.py.j2",
    "expect": "✓ Validation passed",
    "requirements": ["httpx"]
}
```

### Pattern 3: JavaScript/Node.js

**File: `test.js.j2`**

```javascript
#!/usr/bin/env node
const response = await fetch(
    `${process.env.API_ENDPOINT}/chat/completions`,
    {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${process.env.API_KEY}`
        },
        body: JSON.stringify({
            model: "{{ offering.name }}",
            messages: [{role: "user", content: "test"}]
        })
    }
);

const data = await response.json();

console.log(data);
if (data.choices) {
    console.log("✓ Success");  // Will be checked by expect
}
```

**In `listing.json`:**

```json
{
    "file_path": "test.js.j2",
    "expect": "✓ Success"
}
```

## Template Variables Reference

Templates have access to four data structures:

### listing
The listing data structure (Listing_v1 schema)
- `listing.service_name` - Service name
- `listing.listing_type` - Listing type (svcreseller, byop, etc.)
- `listing.status` - Listing status
- All other fields from the listing schema

### offering
Service offering data (Offering_v1 schema)
- `offering.name` - Service/model name
- `offering.offering_id` - Unique offering ID
- `offering.service_type` - Service type (llm, embedding, etc.)
- All other fields from the offering schema

### provider
Provider metadata (Provider_v1 schema)
- `provider.provider_name` - Provider name
- `provider.provider_access_info` - Access credentials and endpoints
  - `provider.provider_access_info.api_endpoint` - API endpoint URL
  - `provider.provider_access_info.api_key` - API key
- All other fields from the provider schema

### seller
Seller metadata (Seller_v1 schema)
- `seller.seller_name` - Seller name
- `seller.contact_email` - Contact email
- All other fields from the seller schema

**Using defaults:**

If a field might not exist, use Jinja2 defaults:

```jinja2
{{ listing.optional_field | default('N/A') }}
{{ offering.description | default('No description available') }}
```

## Tips for Effective Code Examples

1. **Keep examples short and focused** - Test one thing at a time
2. **Use `expect` field** - Makes validation automatic and reliable
3. **Print clear success messages** - Makes debugging easier
4. **Handle errors gracefully** - Exit with non-zero code on failure
5. **Test locally first** - Always verify with hardcoded values before templating
6. **Use meaningful output** - Print enough info to understand what happened
7. **Add requirements** - List all dependencies in the `requirements` field

## Workflow Summary

```bash
# 1. Develop script with hardcoded values
vim test.py
python3 test.py

# 2. Use environment variables
export API_KEY="..."
export API_ENDPOINT="..."
python3 test.py

# 3. Convert to template
mv test.py test.py.j2
vim test.py.j2  # Replace with {{ offering.name }}, etc.

# 4. Add to listing.json
vim listing.json  # Add document entry

# 5. Validate and test
usvc validate
usvc test list
usvc test run --provider your-provider

# 6. Debug if needed
cat failed_*  # Check saved test files

# 7. Publish when tests pass
usvc publish
```

## Interpreter Detection

The test framework automatically detects the appropriate interpreter based on file extension:

- **`.py` files**: Uses `python3` (falls back to `python` if python3 not available)
- **`.js` files**: Uses `node` (Node.js required)
- **`.sh` files**: Uses `bash`
- **Other files**: Checks shebang line (e.g., `#!/usr/bin/env python3`)

If the required interpreter is not found, the test will fail with a clear error message.

## Troubleshooting

### Template Rendering Errors

**Problem:** `Jinja2 syntax error: unexpected 'end of template'`

**Solution:** Check for unclosed tags (`{{`, `{%`, `{#`)

**Problem:** `undefined variable: listing.field_name`

**Solution:** Verify field exists in Listing_v1 schema or use default filter:
```jinja2
{{ listing.field_name | default('fallback') }}
```

### Test Execution Errors

**Problem:** Test fails with "interpreter not found"

**Solution:** Install the required interpreter:
- Python: `brew install python3` or `apt-get install python3`
- Node.js: `brew install node` or download from nodejs.org
- Bash: Usually pre-installed on Unix systems

**Problem:** Test passes locally but fails in test framework

**Solution:**
- Check that you're using environment variables (API_KEY, API_ENDPOINT)
- Verify template variables are correct
- Run `usvc test run --verbose` to see full output

**Problem:** Exit code is 0 but test still fails

**Solution:** Check the `expect` field - test requires the expected string to appear in stdout

### Validation Errors

**Problem:** `usvc validate` reports Jinja2 syntax errors

**Solution:**
- Validate template syntax in isolation
- Common issues: missing `}`, incorrect variable names
- Use a Jinja2 linter or IDE plugin

**Problem:** Code example not found by `usvc test list`

**Solution:**
- Verify `category` is set to `"code_examples"` in document object
- Check that `file_path` is correct relative to listing file
- Run `usvc validate` to check for schema errors
