# Creating and Testing Code Examples

This guide explains how to create, test, and publish code examples for your services on the UnitySVC platform.

## Overview

Code examples help users understand how to interact with your services. The UnitySVC Services SDK provides a complete workflow for:

-   Creating executable code examples in multiple languages (Python, JavaScript, Shell)
-   Using Jinja2 templates for dynamic content
-   Testing examples against upstream APIs
-   Validating output automatically
-   Publishing examples with your service listings

## Basic Concepts

Before diving into creating code examples, understand these fundamental principles:

### 1. Code Examples Should Be Complete

Code examples must be **fully executable** and **self-contained**. Users should be able to run them directly without modifications:

```python
# ✓ GOOD: Complete, runnable example
#!/usr/bin/env python3
import httpx
import os

response = httpx.post(
    f"{os.environ['BASE_URL']}/chat/completions",
    headers={"Authorization": f"Bearer {os.environ['API_KEY']}"},
    json={"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]}
)
print(response.json())

# ✗ BAD: Incomplete snippet
response = api.chat(...)  # What is 'api'? How to initialize it?
```

### 2. Never Include Sensitive Information

**IMPORTANT:** Code examples are public. Never hardcode sensitive information:

```python
# ✗ BAD: Hardcoded credentials
API_KEY = "sk-abc123xyz789"  # NEVER DO THIS!

# ✓ GOOD: Use environment variables
API_KEY = os.environ.get("API_KEY")
BASE_URL = os.environ.get("BASE_URL")
```

**Standard Environment Variables:**

The test framework automatically sets these environment variables when running code examples:

-   `API_KEY` - Provider API key from `provider.provider_access_info.api_key`
-   `BASE_URL` - Provider API endpoint from `provider.provider_access_info.base_url`

Your code examples should **always** read credentials from these environment variables.

### 3. Add to Service Listing Documents

Code examples are referenced in your `listing.json` or `listing.toml` file under the `documents` array:

```json
{
    "schema": "listing_v1",
    "service_name": "gpt-4",
    "user_access_interfaces": [
        {
            "interface_type": "openai_chat_completions",
            "documents": [
                {
                    "category": "code_examples",
                    "title": "Python Example",
                    "file_path": "../../docs/example.py.j2",
                    "mime_type": "python",
                    "is_public": true,
                    "meta": {
                        "requirements": ["httpx"],
                        "expect": "✓ Test passed"
                    }
                }
            ]
        }
    ]
}
```

**Required Fields:**

-   **`category`**: Must be `"code_examples"` for test framework to discover it
-   **`title`**: Descriptive name (e.g., "Python Example", "cURL Example")
-   **`file_path`**: Path to the code file (relative to the listing file)
-   **`mime_type`**: File type (`python`, `javascript`, `shell`, etc.)
-   **`is_public`**: Should be `true` for code examples

**Optional but Recommended Fields (in `meta` object):**

-   **`meta.requirements`**: _(User-maintained)_ Package dependencies needed to run the code example
    -   For Python: PyPI packages (e.g., `["httpx", "openai"]`)
    -   For JavaScript: npm packages (e.g., `["node-fetch"]`)
    -   For Shell scripts: commands (e.g., `["curl"]`)
    -   Helps users understand what to install before running the example
-   **`meta.expect`**: _(User-maintained)_ Expected substring in stdout for validation
    -   Examples: `"✓ Test passed"`, `"\"choices\""`, `"Status: 200"`
    -   If specified, test passes only if stdout contains this string
    -   Without this field, tests only check exit code (0 = pass, non-zero = fail)

**System-Maintained Fields (in `meta` object):**

-   **`meta.output`**: _(System-maintained)_ Actual output from successful test execution
    -   Automatically populated by `usvc test run` when a test passes
    -   Contains the stdout from the last successful test run
    -   Included in your service listing during `usvc publish`
    -   Displayed alongside code examples for documentation

### 4. Use Relative Paths

The `file_path` must be **relative to the listing file**, not absolute:

```
data/
└── fireworks/
    ├── docs/
    │   └── example.py.j2          # Shared code example
    └── services/
        └── llama-3-1-405b/
            └── listing.json        # References: ../../docs/example.py.j2
```

```json
{
    "file_path": "../../docs/example.py.j2" // ✓ GOOD: Relative path
}
```

```json
{
    "file_path": "/data/fireworks/docs/example.py.j2" // ✗ BAD: Absolute path
}
```

### 5. Templates Work Across Multiple Services

Code examples ending with `.j2` are **Jinja2 templates** that can be reused across multiple service listings:

**Template File: `docs/example.py.j2`**

```python
#!/usr/bin/env python3
"""Example for {{ offering.name }} from {{ provider.name }}"""
import httpx
import os

response = httpx.post(
    f"{os.environ['BASE_URL']}/chat/completions",
    headers={"Authorization": f"Bearer {os.environ['API_KEY']}"},
    json={
        "model": "{{ offering.name }}",  # Dynamic: changes per service
        "messages": [{"role": "user", "content": "Hello"}]
    }
)
print(response.json())
```

**Multiple Listings Reference the Same Template:**

```
data/fireworks/
├── docs/
│   └── example.py.j2              # One template
└── services/
    ├── llama-3-1-405b/
    │   └── listing.json            # References: ../../docs/example.py.j2
    ├── llama-3-1-70b/
    │   └── listing.json            # References: ../../docs/example.py.j2
    └── mixtral-8x7b/
        └── listing.json            # References: ../../docs/example.py.j2
```

**Benefits of Templates:**

-   **Write once, use many times** - One template serves all services
-   **Automatic updates** - Fix the template once, all services benefit
-   **Dynamic content** - Service-specific values inserted automatically
-   **Type safety** - Variables validated during testing

See [Template Variables Reference](#template-variables-reference) for complete list.

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

-   Service name
-   Provider name
-   Example title
-   File type (.py, .js, .sh, etc.)
-   Relative file path from data directory

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

# Force rerun all tests (ignore cached results)
usvc test run --force

# Stop on first failure (useful for quick feedback during development)
usvc test run --fail-fast

# Combine options
usvc test run --force --fail-fast --verbose
```

**How tests work:**

1. Test framework discovers code examples from listing files (category = `code_examples`)
2. **Checks for cached results**: If both `.out` and `.err` files exist in the listing directory, skips the test (unless `--force` is used)
3. Renders Jinja2 templates with `listing`, `offering`, `provider`, and `seller` data
4. Sets environment variables (`API_KEY`, `BASE_URL`) from provider credentials
5. Executes the code example using appropriate interpreter (python3, node, bash)
6. Validates results:
    - Test passes if exit code is 0 AND (no `meta.expect` field OR expected string found in stdout)
    - Test fails if exit code is non-zero OR expected string not found
7. **Saves output**: When a test passes, stdout and stderr are saved to listing directory as `{service}_{listing}_{filename}.{out|err}`
    - Example: For `listing.json` in `llama-3-1-405b` with code file `test.py`, output is saved as `llama-3-1-405b_listing_test.py.out` and `llama-3-1-405b_listing_test.py.err`
    - Saved in the same directory as the listing file for easy version control
    - Used to skip re-running tests on subsequent runs (unless `--force` is specified)
8. **Fail-fast mode**: If `--fail-fast` is enabled, testing stops immediately after the first failure

**Failed test debugging:**

When a test fails, the rendered content is automatically saved to the current directory:

```bash
# Example output:
Testing: llama-3-1-405b - Python code example
  ✗ Failed - Output validation failed: expected substring '✓ Test passed' not found
  → Test content saved to: failed_llama-3-1-405b_Python_code_example.py

# The saved file includes:
# - Environment variables used (API_KEY, BASE_URL)
# - Full rendered template content
# - You can run it directly to reproduce the issue
```

## Developing Code Examples

This section provides a step-by-step guide for creating and testing code examples for your services.

### Step 1: Develop and Test the Script Locally

Start by writing a working script using actual values. This allows you to verify the API works correctly before templating.

Note the expected output and find a suitable `expect` word.

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
BASE_URL = os.environ.get("BASE_URL")

response = httpx.post(
    f"{BASE_URL}/chat/completions",
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
export BASE_URL="https://api.fireworks.ai/inference/v1"
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
BASE_URL = os.environ.get("BASE_URL")

response = httpx.post(
    f"{BASE_URL}/chat/completions",
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

-   `{{ listing.name }}` - Service listing name
-   `{{ offering.name }}` - Model/service name
-   `{{ provider.name }}` - Provider name
-   `{{ provider.display_name }}` - Provider name
-   `{{ seller.name }}` - Seller name
-   `{{ seller.display_name }}` - Seller name

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
                    "meta": {
                        "requirements": ["httpx"],
                        "expect": "✓ Test passed"
                    }
                }
            ]
        }
    ]
}
```

**Important fields:**

-   `category`: Must be `"code_examples"` for test framework to find it
-   `title`: Descriptive name for the example
-   `file_path`: Relative path from listing file to your `.j2` template
-   `mime_type`: File type (`python`, `javascript`, `shell`, etc.)
-   `is_public`: Should be `true` for code examples
-   `meta`: **[Optional]** Metadata object containing:
    -   `requirements`: _(User-maintained)_ List of package dependencies needed to run the code example
        -   For Python: PyPI packages (e.g., `["httpx", "openai"]`)
        -   For JavaScript: npm packages (e.g., `["node-fetch"]`)
        -   For Shell scripts: commands (e.g., `["curl"]`)
        -   Helps users understand what to install before running the example
    -   `expect`: _(User-maintained, strongly recommended)_ Expected substring that should appear in stdout when the test passes
        -   Examples:
            -   `"✓ Test passed"` - Explicit success message
            -   `"\"choices\""` - Check for JSON field in API response
            -   `"Status: 200"` - Check for HTTP status
        -   Without this field, tests only check exit code (0 = pass, non-zero = fail), which is unreliable
    -   `output`: _(System-maintained)_ Automatically populated by `usvc test run`
        -   Contains stdout from the last successful test execution
        -   Saved to `{listing_stem}_{code_filename}.out` file during test run
        -   Embedded into `meta.output` during `usvc publish`
        -   Displayed alongside code examples in your service listing

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

pass option `--services` to limit to particular services.

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
# - Environment variables used (API_KEY, BASE_URL)
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

curl ${BASE_URL}/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -d '{"model": "{{ offering.name }}", "messages": [{"role": "user", "content": "test"}]}'
```

**In `listing.json`:**

```json
{
    "category": "code_examples",
    "title": "Shell Example",
    "file_path": "test.sh.j2",
    "mime_type": "bash",
    "is_public": true,
    "meta": {
        "expect": "\"choices\""
    }
}
```

### Pattern 2: Python with validation

**File: `test.py.j2`**

```python
#!/usr/bin/env python3
import httpx
import os

response = httpx.post(
    f"{os.environ['BASE_URL']}/chat/completions",
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
    "category": "code_examples",
    "title": "Python Example",
    "file_path": "test.py.j2",
    "mime_type": "python",
    "is_public": true,
    "meta": {
        "requirements": ["httpx"],
        "expect": "✓ Validation passed"
    }
}
```

### Pattern 3: JavaScript/Node.js

**File: `test.js.j2`**

```javascript
#!/usr/bin/env node
const response = await fetch(`${process.env.BASE_URL}/chat/completions`, {
    method: "POST",
    headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${process.env.API_KEY}`,
    },
    body: JSON.stringify({
        model: "{{ offering.name }}",
        messages: [{ role: "user", content: "test" }],
    }),
});

const data = await response.json();

console.log(data);
if (data.choices) {
    console.log("✓ Success"); // Will be checked by expect
}
```

**In `listing.json`:**

```json
{
    "category": "code_examples",
    "title": "JavaScript Example",
    "file_path": "test.js.j2",
    "mime_type": "javascript",
    "is_public": true,
    "meta": {
        "expect": "✓ Success"
    }
}
```

## Template Variables Reference

Templates have access to four data structures:

### listing

The listing data structure (Listing_v1 schema)

-   `listing.service_name` - Service name
-   `listing.listing_type` - Listing type (svcreseller, byop, etc.)
-   `listing.status` - Listing status
-   All other fields from the listing schema

### offering

Service offering data (Offering_v1 schema)

-   `offering.name` - Service/model name
-   `offering.offering_id` - Unique offering ID
-   `offering.service_type` - Service type (llm, embedding, etc.)
-   All other fields from the offering schema

### provider

Provider metadata (Provider_v1 schema)

-   `provider.provider_name` - Provider name
-   `provider.provider_access_info` - Access credentials and endpoints
    -   `provider.provider_access_info.base_url` - API endpoint URL
    -   `provider.provider_access_info.api_key` - API key
-   All other fields from the provider schema

### seller

Seller metadata (Seller_v1 schema)

-   `seller.seller_name` - Seller name
-   `seller.contact_email` - Contact email
-   All other fields from the seller schema

**Using defaults:**

If a field might not exist, use Jinja2 defaults:

```jinja2
{{ listing.optional_field | default('N/A') }}
{{ offering.description | default('No description available') }}
```

## Tips for Effective Code Examples

1. **Keep examples short and focused** - Test one thing at a time
2. **Use `meta.expect` field** - Makes validation automatic and reliable
3. **Print clear success messages** - Makes debugging easier
4. **Handle errors gracefully** - Exit with non-zero code on failure
5. **Test locally first** - Always verify with hardcoded values before templating
6. **Use meaningful output** - Print enough info to understand what happened
7. **Add requirements** - List all dependencies in `meta.requirements` field

## Workflow Summary

```bash
# 1. Develop script with hardcoded values
vim test.py
python3 test.py

# 2. Use environment variables
export API_KEY="..."
export BASE_URL="..."
python3 test.py

# 3. Convert to template
mv test.py test.py.j2
vim test.py.j2  # Replace with {{ offering.name }}, etc.

# 4. Add to listing.json with meta fields
vim listing.json  # Add document entry with meta.requirements and meta.expect

# 5. Validate and test
usvc validate
usvc test list
usvc test run --provider your-provider
# ✓ Successful tests create .out and .err files (e.g., servicename_listing_test.py.out)
# ✓ Subsequent runs skip tests with existing results (use --force to rerun)
# ✓ Use --fail-fast to stop on first failure for quick feedback

# 6. Debug if needed
cat failed_*  # Check saved test files (in current directory)
cat services/*/listing_*.out  # Review successful test outputs (in listing directories)

# 7. Publish - embeds .out files into meta.output
usvc publish
# ✓ Reads .out files from listing directories and adds content to meta.output
# ✓ Output will appear alongside code examples in your service listing
```

## Understanding meta.output Workflow

The `meta.output` field follows an automated workflow from test execution to publication:

### 1. Testing Phase: `usvc test run`

When you run tests, successful executions generate `.out` files:

```bash
$ usvc test run --provider fireworks

Testing: llama-3-1-405b - Python code example
  ✓ Success (exit code: 0)
  → Output saved to: /path/to/fireworks/services/llama-3-1-405b/listing_test.py.out
```

**Output file naming:** `{listing_stem}_{code_filename}.out`

-   `listing_stem`: The listing filename without extension (e.g., "listing" from "listing.json")
-   `code_filename`: The code filename after template expansion (e.g., "test.py" from "test.py.j2")
-   Example: `listing_test.py.out`, `svclisting_example.sh.out`

**File location:** Same directory as the listing file that references the code example

### 2. Publishing Phase: `usvc publish`

During publish, the SDK automatically:

1. Expands `.j2` templates for each model if a template is used
2. Looks for matching `.out` files in the listing's base directory
3. Reads the output content and embeds it into `meta.output`

**Example published document:**

```json
{
    "category": "code_examples",
    "title": "Python code example",
    "file_path": "chat-completion.py",
    "file_content": "#!/usr/bin/env python3\nimport httpx...",
    "mime_type": "python",
    "meta": {
        "requirements": ["httpx"],
        "expect": "✓ Test passed",
        "output": "{'id': 'chatcmpl-...', 'choices': [{'message': {'content': 'Hello!'}}]}\n✓ Test passed"
    }
}
```

### 3. Display in Service Listing

After publishing, the output will automatically appear alongside the code example in your service listing documentation, allowing users to see both the code and its expected output together.

### 4. Key Points

-   **`.out` files are model-specific**: Since templates expand per model, each model gets its own output file
-   **`.out` files location**: Saved in the **same directory as the listing file**, making them easy to find and version control
-   **`.out` file naming**: Format is `{listing_stem}_{code_filename}.out` to clearly associate output with both listing and code
-   **Version control**: You **can** commit `.out` files to version control since they're co-located with listings
-   **Publishing is flexible**: `usvc publish` works even if `.out` files are missing (gracefully skips)
-   **User vs System fields**:
    -   `meta.requirements` and `meta.expect` are **user-maintained** (you write these)
    -   `meta.output` is **system-maintained** (auto-generated by `usvc test run` and `usvc publish`)

## Interpreter Detection

The test framework automatically detects the appropriate interpreter based on file extension:

-   **`.py` files**: Uses `python3` (falls back to `python` if python3 not available)
-   **`.js` files**: Uses `node` (Node.js required)
-   **`.sh` files**: Uses `bash`
-   **Other files**: Checks shebang line (e.g., `#!/usr/bin/env python3`)

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

-   Python: `brew install python3` or `apt-get install python3`
-   Node.js: `brew install node` or download from nodejs.org
-   Bash: Usually pre-installed on Unix systems

**Problem:** Test passes locally but fails in test framework

**Solution:**

-   Check that you're using environment variables (API_KEY, BASE_URL)
-   Verify template variables are correct
-   Run `usvc test run --verbose` to see full output

**Problem:** Exit code is 0 but test still fails

**Solution:** Check the `meta.expect` field - test requires the expected string to appear in stdout

### Validation Errors

**Problem:** `usvc validate` reports Jinja2 syntax errors

**Solution:**

-   Validate template syntax in isolation
-   Common issues: missing `}`, incorrect variable names
-   Use a Jinja2 linter or IDE plugin

**Problem:** Code example not found by `usvc test list`

**Solution:**

-   Verify `category` is set to `"code_examples"` in document object
-   Check that `file_path` is correct relative to listing file
-   Run `usvc validate` to check for schema errors
