# Master Test Plan: UnitySVC Admin CLI Tool (usvc_admin)

**Feature:** Administrative CLI tool for managing UnitySVC platform via /admin API endpoints

**Owner:** QA Team
**Status:** Draft
**Created:** 2026-01-21
**Test Data:** `../unitysvc-services-aionlabs` (aionlabs provider with 3 services)
**Repository:** `unitysvc-admin`

---

## Test Execution Mode Legend

| Mode | Description |
|------|-------------|
| :robot: **Automated** | Claude Code executes independently with shell commands |
| :arrows_counterclockwise: **Interactive** | Tester sets up environment/data, Claude executes, tester reviews results |
| :bust_in_silhouette: **Manual** | Human judgment required (UI quality, usability, output readability) |

---

## Prerequisites

- [ ] Python 3.11+ installed
- [ ] unitysvc-admin package installed (`pip install -e ../unitysvc-admin`)
- [ ] Access to UnitySVC staging environment
- [ ] Admin/superuser API key configured
- [ ] Backend running with database access
- [ ] Test data available in staging environment
- [ ] Environment variables configured:
  - `UNITYSVC_API_KEY` - Admin API key from superuser account (required)
  - `UNITYSVC_BASE_URL` - Backend API URL (default: `http://localhost:8000/api/v1`)
  - `GATEWAY_BASE_URL` - Gateway URL (optional)

---

## Phase 1: CLI Setup and Configuration (0.5 day)

### 1.1 Installation and Entry Points

- [ ] :robot: Verify `usvc_admin --help` shows all command groups
- [ ] :robot: Verify `unitysvc_admin --help` (canonical name) works
- [ ] :robot: Verify `usvc_admin --version` displays version
- [ ] :robot: Verify all 18+ command groups listed in help

### 1.2 Environment Variable Handling

- [ ] :robot: Verify error when `UNITYSVC_API_KEY` not set
- [ ] :robot: Verify default `UNITYSVC_BASE_URL` (localhost:8000)
- [ ] :arrows_counterclockwise: Verify custom `UNITYSVC_BASE_URL` used correctly
- [ ] :arrows_counterclockwise: Verify `.env` file loading works
- [ ] :robot: Verify `GATEWAY_BASE_URL` derivation from base URL

### 1.3 Authentication

- [ ] :robot: Verify 401 error with invalid API key
- [ ] :arrows_counterclockwise: Verify valid API key authenticates successfully
- [ ] :robot: Verify non-admin API key gets 403 error

---

## Phase 2: User Management Commands (1 day)

### 2.1 Users List (`usvc_admin users list`)

- [ ] :arrows_counterclockwise: List all users with default pagination
- [ ] :arrows_counterclockwise: Filter by email (partial match)
- [ ] :arrows_counterclockwise: Filter by full_name
- [ ] :arrows_counterclockwise: Filter by customer_id
- [ ] :arrows_counterclockwise: Pagination with `--skip` and `--limit`
- [ ] :robot: Output format `--format table` (default)
- [ ] :robot: Output format `--format json`
- [ ] :robot: Output format `--format tsv`
- [ ] :robot: Output format `--format csv`
- [ ] :arrows_counterclockwise: Custom fields with `--fields`
- [ ] :bust_in_silhouette: Verify table formatting readability

### 2.2 Users Show (`usvc_admin users show`)

- [ ] :arrows_counterclockwise: Show user by UUID
- [ ] :arrows_counterclockwise: Show user by partial UUID (8+ chars)
- [ ] :arrows_counterclockwise: Verify customer associations displayed
- [ ] :arrows_counterclockwise: Verify seller associations displayed
- [ ] :robot: Verify 404 for non-existent user
- [ ] :bust_in_silhouette: Verify detail output formatting

---

## Phase 3: Service Management Commands (1.5 days)

### 3.1 Services List (`usvc_admin services list`)

- [ ] :arrows_counterclockwise: List all services
- [ ] :arrows_counterclockwise: Filter by status (draft, pending, active, etc.)
- [ ] :arrows_counterclockwise: Filter by seller
- [ ] :arrows_counterclockwise: Filter by service_type
- [ ] :arrows_counterclockwise: Pagination with `--skip` and `--limit`
- [ ] :robot: Output format `--format json`
- [ ] :robot: Output format `--format tsv`
- [ ] :robot: Output format `--format csv`
- [ ] :bust_in_silhouette: Verify table formatting

### 3.2 Services Show (`usvc_admin services show`)

- [ ] :arrows_counterclockwise: Show service by UUID
- [ ] :arrows_counterclockwise: Show service by partial UUID
- [ ] :arrows_counterclockwise: Verify provider info included
- [ ] :arrows_counterclockwise: Verify offering info included
- [ ] :arrows_counterclockwise: Verify listing info included
- [ ] :arrows_counterclockwise: Verify seller info included
- [ ] :robot: Verify 404 for non-existent service

### 3.3 Providers List (`usvc_admin providers list`)

- [ ] :arrows_counterclockwise: List all providers
- [ ] :arrows_counterclockwise: Filter by name
- [ ] :arrows_counterclockwise: Pagination support
- [ ] :robot: Output format options
- [ ] :bust_in_silhouette: Verify table formatting

### 3.4 Providers Show (`usvc_admin providers show`)

- [ ] :arrows_counterclockwise: Show provider by UUID
- [ ] :arrows_counterclockwise: Verify usage stats displayed
- [ ] :robot: Verify 404 for non-existent provider

### 3.5 Offerings List (`usvc_admin offerings list`)

- [ ] :arrows_counterclockwise: List all offerings
- [ ] :arrows_counterclockwise: Filter by provider
- [ ] :arrows_counterclockwise: Filter by service_type
- [ ] :arrows_counterclockwise: Pagination support
- [ ] :robot: Output format options

### 3.6 Listings List (`usvc_admin listings list`)

- [ ] :arrows_counterclockwise: List all listings
- [ ] :arrows_counterclockwise: Filter by status
- [ ] :arrows_counterclockwise: Filter by offering
- [ ] :arrows_counterclockwise: Pagination support
- [ ] :robot: Output format options

### 3.7 Listings Show (`usvc_admin listings show`)

- [ ] :arrows_counterclockwise: Show listing by UUID
- [ ] :arrows_counterclockwise: Verify pricing info displayed
- [ ] :arrows_counterclockwise: Verify documents displayed
- [ ] :robot: Verify 404 for non-existent listing

### 3.8 Subscriptions List (`usvc_admin subscriptions list`)

- [ ] :arrows_counterclockwise: List service subscriptions
- [ ] :arrows_counterclockwise: Filter by customer
- [ ] :arrows_counterclockwise: Filter by service
- [ ] :arrows_counterclockwise: Filter by status
- [ ] :arrows_counterclockwise: Pagination support

---

## Phase 4: Seller Management Commands (1 day)

### 4.1 Sellers List (`usvc_admin sellers list`)

- [ ] :arrows_counterclockwise: List all sellers
- [ ] :arrows_counterclockwise: Filter by name
- [ ] :arrows_counterclockwise: Filter by status
- [ ] :arrows_counterclockwise: Pagination with `--skip` and `--limit`
- [ ] :robot: Output format options
- [ ] :bust_in_silhouette: Verify table formatting

### 4.2 Sellers Show (`usvc_admin sellers show`)

- [ ] :arrows_counterclockwise: Show seller by UUID
- [ ] :arrows_counterclockwise: Show seller by partial UUID
- [ ] :arrows_counterclockwise: Verify balance info displayed
- [ ] :arrows_counterclockwise: Verify services count displayed
- [ ] :robot: Verify 404 for non-existent seller

### 4.3 Sellers Ledger (`usvc_admin sellers ledger`)

- [ ] :arrows_counterclockwise: Show seller ledger entries
- [ ] :arrows_counterclockwise: Filter by date range
- [ ] :arrows_counterclockwise: Filter by transaction type
- [ ] :arrows_counterclockwise: Verify payout history displayed
- [ ] :arrows_counterclockwise: Pagination support
- [ ] :bust_in_silhouette: Verify ledger formatting

---

## Phase 5: Billing and Financial Commands (2 days)

### 5.1 Invoices List (`usvc_admin invoices list`)

- [ ] :arrows_counterclockwise: List all seller invoices
- [ ] :arrows_counterclockwise: Filter by seller
- [ ] :arrows_counterclockwise: Filter by status (draft, sent, paid)
- [ ] :arrows_counterclockwise: Filter by billing period
- [ ] :arrows_counterclockwise: Filter by currency
- [ ] :arrows_counterclockwise: Pagination support
- [ ] :robot: Output format options

### 5.2 Invoices Show (`usvc_admin invoices show`)

- [ ] :arrows_counterclockwise: Show invoice by UUID
- [ ] :arrows_counterclockwise: Verify line items displayed
- [ ] :arrows_counterclockwise: Verify totals displayed
- [ ] :arrows_counterclockwise: Verify seller info displayed
- [ ] :robot: Verify 404 for non-existent invoice

### 5.3 Invoices Generate (`usvc_admin invoices generate`)

- [ ] :arrows_counterclockwise: Generate invoices for billing period
- [ ] :arrows_counterclockwise: Verify async task queued (HTTP 202)
- [ ] :arrows_counterclockwise: Verify task polling works
- [ ] :arrows_counterclockwise: Verify invoices created after completion
- [ ] :robot: Verify error for invalid period format

### 5.4 Statements List (`usvc_admin statements list`)

- [ ] :arrows_counterclockwise: List all customer statements
- [ ] :arrows_counterclockwise: Filter by customer
- [ ] :arrows_counterclockwise: Filter by period
- [ ] :arrows_counterclockwise: Filter by status
- [ ] :arrows_counterclockwise: Pagination support
- [ ] :robot: Output format options

### 5.5 Statements Show (`usvc_admin statements show`)

- [ ] :arrows_counterclockwise: Show statement by UUID
- [ ] :arrows_counterclockwise: Verify line items displayed
- [ ] :arrows_counterclockwise: Verify usage charges displayed
- [ ] :arrows_counterclockwise: Verify adjustments displayed
- [ ] :robot: Verify 404 for non-existent statement

### 5.6 Statements Generate (`usvc_admin statements generate`)

- [ ] :arrows_counterclockwise: Generate statements for billing period
- [ ] :arrows_counterclockwise: Verify async task queued
- [ ] :arrows_counterclockwise: Verify task polling works
- [ ] :arrows_counterclockwise: Verify statements created after completion
- [ ] :robot: Verify error for invalid period format

### 5.7 Plan Subscriptions List (`usvc_admin plansubscriptions list`)

- [ ] :arrows_counterclockwise: List billing subscriptions
- [ ] :arrows_counterclockwise: Filter by customer
- [ ] :arrows_counterclockwise: Filter by plan
- [ ] :arrows_counterclockwise: Filter by status
- [ ] :arrows_counterclockwise: Pagination support

---

## Phase 6: Wallet Management Commands (1 day)

### 6.1 Wallets List (`usvc_admin wallets list`)

- [ ] :arrows_counterclockwise: List all wallets
- [ ] :arrows_counterclockwise: Filter by customer
- [ ] :arrows_counterclockwise: Filter by currency
- [ ] :arrows_counterclockwise: Pagination support
- [ ] :robot: Output format options

### 6.2 Wallets Status (`usvc_admin wallets status`)

- [ ] :arrows_counterclockwise: Show wallet status by UUID
- [ ] :arrows_counterclockwise: Verify balance displayed
- [ ] :arrows_counterclockwise: Verify transaction count displayed
- [ ] :robot: Verify 404 for non-existent wallet

### 6.3 Wallets Reconcile (`usvc_admin wallets reconcile`)

- [ ] :arrows_counterclockwise: Reconcile single wallet by UUID
- [ ] :arrows_counterclockwise: Verify reconciliation result displayed
- [ ] :arrows_counterclockwise: Verify balance adjustment if needed
- [ ] :robot: Verify 404 for non-existent wallet
- [ ] :robot: Verify error handling for reconciliation failures

### 6.4 Wallets Reconcile-All (`usvc_admin wallets reconcile-all`)

- [ ] :arrows_counterclockwise: Reconcile all wallets
- [ ] :arrows_counterclockwise: Verify async task queued
- [ ] :arrows_counterclockwise: Verify task polling works
- [ ] :arrows_counterclockwise: Verify summary displayed after completion

---

## Phase 7: Subscription Plan Commands (1.5 days)

### 7.1 Plans List (`usvc_admin plans list`)

- [ ] :arrows_counterclockwise: List all subscription plans
- [ ] :arrows_counterclockwise: Filter by tier (free, pro, team)
- [ ] :arrows_counterclockwise: Filter by status
- [ ] :arrows_counterclockwise: Pagination support
- [ ] :robot: Output format options
- [ ] :bust_in_silhouette: Verify table formatting

### 7.2 Plans Init (`usvc_admin plans init`)

- [ ] :arrows_counterclockwise: Initialize plan data from file
- [ ] :robot: Verify error for missing file
- [ ] :robot: Verify error for invalid file format
- [ ] :arrows_counterclockwise: Verify plan data loaded correctly

### 7.3 Plans Validate (`usvc_admin plans validate`)

- [ ] :arrows_counterclockwise: Validate plan data against schema
- [ ] :robot: Verify error for invalid schema
- [ ] :arrows_counterclockwise: Verify success message for valid data
- [ ] :robot: Verify detailed error messages for validation failures

### 7.4 Plans Upload (`usvc_admin plans upload`)

- [ ] :arrows_counterclockwise: Upload plan to backend
- [ ] :arrows_counterclockwise: Verify plan created/updated successfully
- [ ] :arrows_counterclockwise: Verify dry-run mode (`--dryrun`)
- [ ] :robot: Verify error for invalid plan data
- [ ] :robot: Verify error for authentication failure

---

## Phase 8: Content Management Commands (1 day)

### 8.1 Blogs List (`usvc_admin blogs list`)

- [ ] :arrows_counterclockwise: List all blog posts
- [ ] :arrows_counterclockwise: Filter by status (draft, published)
- [ ] :arrows_counterclockwise: Filter by author
- [ ] :arrows_counterclockwise: Pagination support
- [ ] :robot: Output format options

### 8.2 Blogs Show (`usvc_admin blogs show`)

- [ ] :arrows_counterclockwise: Show blog post by UUID
- [ ] :arrows_counterclockwise: Verify content displayed
- [ ] :arrows_counterclockwise: Verify metadata displayed
- [ ] :robot: Verify 404 for non-existent post

### 8.3 Blogs Publish (`usvc_admin blogs publish`)

- [ ] :arrows_counterclockwise: Publish draft blog post
- [ ] :arrows_counterclockwise: Verify status changed to published
- [ ] :robot: Verify error for already published post
- [ ] :robot: Verify error for non-existent post

### 8.4 Blogs Update (`usvc_admin blogs update`)

- [ ] :arrows_counterclockwise: Update blog post content
- [ ] :arrows_counterclockwise: Update blog post metadata
- [ ] :robot: Verify error for non-existent post

### 8.5 Documents List (`usvc_admin documents list`)

- [ ] :arrows_counterclockwise: List all documents
- [ ] :arrows_counterclockwise: Filter by entity type
- [ ] :arrows_counterclockwise: Filter by category
- [ ] :arrows_counterclockwise: Pagination support
- [ ] :robot: Output format options

### 8.6 Interfaces List (`usvc_admin interfaces list`)

- [ ] :arrows_counterclockwise: List access interfaces
- [ ] :arrows_counterclockwise: Filter by service
- [ ] :arrows_counterclockwise: Pagination support
- [ ] :robot: Output format options

---

## Phase 9: Audit and Logging Commands (0.5 day)

### 9.1 Logs List (`usvc_admin logs list`)

- [ ] :arrows_counterclockwise: List audit log entries
- [ ] :arrows_counterclockwise: Filter by user
- [ ] :arrows_counterclockwise: Filter by action
- [ ] :arrows_counterclockwise: Filter by resource type
- [ ] :arrows_counterclockwise: Filter by date range
- [ ] :arrows_counterclockwise: Pagination support
- [ ] :robot: Output format options
- [ ] :bust_in_silhouette: Verify log entry formatting

---

## Phase 10: Task Management Commands (0.5 day)

### 10.1 Tasks List (`usvc_admin tasks list`)

- [ ] :arrows_counterclockwise: List available Celery tasks
- [ ] :arrows_counterclockwise: Verify whitelisted tasks shown
- [ ] :robot: Output format options

### 10.2 Tasks Run (`usvc_admin tasks run`)

- [ ] :arrows_counterclockwise: Run `reconcile_wallet` task
- [ ] :arrows_counterclockwise: Run `reconcile_all_wallets` task
- [ ] :arrows_counterclockwise: Verify task queued successfully
- [ ] :arrows_counterclockwise: Verify task polling works
- [ ] :robot: Verify error for non-whitelisted task
- [ ] :robot: Verify error for invalid task name

### 10.3 Tasks Status (`usvc_admin tasks status`)

- [ ] :arrows_counterclockwise: Check status of running task
- [ ] :arrows_counterclockwise: Check status of completed task
- [ ] :robot: Verify error for non-existent task

---

## Phase 11: Database Commands (0.5 day)

### 11.1 DB Status (`usvc_admin db status`)

- [ ] :arrows_counterclockwise: Display PostgreSQL connection status
- [ ] :arrows_counterclockwise: Verify connection info displayed
- [ ] :bust_in_silhouette: Verify output formatting

### 11.2 DB Reset (`usvc_admin db reset`)

- [ ] :arrows_counterclockwise: Reset database (non-production only)
- [ ] :robot: Verify error in production environment
- [ ] :arrows_counterclockwise: Verify confirmation prompt
- [ ] :arrows_counterclockwise: Verify database reset successfully

---

## Phase 12: Gateway Commands (1.5 days)

### 12.1 Gateway Status (`usvc_admin gateway status`)

- [ ] :arrows_counterclockwise: Check gateway health
- [ ] :arrows_counterclockwise: Verify status response displayed
- [ ] :bust_in_silhouette: Verify output formatting

### 12.2 Gateway Test-Route (`usvc_admin gateway test-route`)

- [ ] :arrows_counterclockwise: Query routing info for path
- [ ] :arrows_counterclockwise: Verify route mapping displayed
- [ ] :arrows_counterclockwise: Verify upstream info displayed
- [ ] :robot: Verify error for invalid path

### 12.3 Gateway Sync-Tests (`usvc_admin gateway sync-tests`)

- [ ] :arrows_counterclockwise: Sync service listings to test database
- [ ] :arrows_counterclockwise: Verify sync completion message
- [ ] :arrows_counterclockwise: Verify listings count displayed

### 12.4 Gateway Test-Examples (`usvc_admin gateway test-examples`)

- [ ] :arrows_counterclockwise: Run code examples for a service
- [ ] :arrows_counterclockwise: Verify test results displayed
- [ ] :arrows_counterclockwise: Verify pass/fail status for each example
- [ ] :robot: Verify error for non-existent service

### 12.5 Gateway List-Examples (`usvc_admin gateway list-examples`)

- [ ] :arrows_counterclockwise: List available code examples
- [ ] :arrows_counterclockwise: Filter by service
- [ ] :arrows_counterclockwise: Pagination support
- [ ] :robot: Output format options

### 12.6 Gateway Export-Results (`usvc_admin gateway export-results`)

- [ ] :arrows_counterclockwise: Export test results to CSV
- [ ] :arrows_counterclockwise: Export test results to JSON
- [ ] :arrows_counterclockwise: Export test results to HTML
- [ ] :robot: Verify file created successfully

### 12.7 Gateway Clean (`usvc_admin gateway clean`)

- [ ] :arrows_counterclockwise: Clean old test results
- [ ] :arrows_counterclockwise: Verify cleanup message displayed
- [ ] :arrows_counterclockwise: Specify retention period

---

## Phase 13: End-to-End Workflows (1.5 days)

### 13.1 User Lookup Workflow

- [ ] :arrows_counterclockwise: List users → Find user by email → Show user details
- [ ] :arrows_counterclockwise: Verify customer/seller associations

### 13.2 Service Investigation Workflow

- [ ] :arrows_counterclockwise: List services → Show service → View provider → View offering → View listing
- [ ] :arrows_counterclockwise: Verify all related entities accessible

### 13.3 Seller Financial Workflow

- [ ] :arrows_counterclockwise: Show seller → View ledger → List invoices → Show invoice
- [ ] :arrows_counterclockwise: Verify financial data consistency

### 13.4 Billing Period Workflow

- [ ] :arrows_counterclockwise: Generate statements → List statements → Show statement
- [ ] :arrows_counterclockwise: Generate invoices → List invoices → Show invoice
- [ ] :arrows_counterclockwise: Verify billing data complete

### 13.5 Wallet Reconciliation Workflow

- [ ] :arrows_counterclockwise: List wallets → Check status → Reconcile → Verify balance
- [ ] :arrows_counterclockwise: Reconcile all wallets → Verify completion

### 13.6 Plan Management Workflow

- [ ] :arrows_counterclockwise: Init plan data → Validate → Upload → List plans → Verify
- [ ] :arrows_counterclockwise: Verify plan active and usable

### 13.7 Gateway Testing Workflow

- [ ] :arrows_counterclockwise: Sync tests → List examples → Test examples → Export results
- [ ] :arrows_counterclockwise: Verify test pipeline complete

---

## Phase 14: Edge Cases and Error Handling (1 day)

### 14.1 Invalid Input Handling

- [ ] :robot: Invalid UUID format
- [ ] :robot: Non-existent UUID
- [ ] :robot: Empty required fields
- [ ] :robot: Invalid date format
- [ ] :robot: Invalid enum values
- [ ] :robot: Negative pagination values

### 14.2 Network and API Errors

- [ ] :arrows_counterclockwise: Handle connection timeout
- [ ] :arrows_counterclockwise: Handle server 500 error
- [ ] :robot: Handle 401 unauthorized
- [ ] :robot: Handle 403 forbidden
- [ ] :robot: Handle 404 not found
- [ ] :arrows_counterclockwise: Verify curl fallback on macOS network issues

### 14.3 Async Task Errors

- [ ] :arrows_counterclockwise: Handle task timeout
- [ ] :arrows_counterclockwise: Handle task failure
- [ ] :arrows_counterclockwise: Verify error message displayed

### 14.4 Output Handling

- [ ] :robot: Handle empty result set
- [ ] :robot: Handle large result set (pagination)
- [ ] :arrows_counterclockwise: Handle special characters in data
- [ ] :arrows_counterclockwise: Handle unicode in output

---

## Phase 15: Documentation Quality (0.5 day)

### 15.1 README Documentation

- [ ] :bust_in_silhouette: Verify README.md exists and is complete
- [ ] :bust_in_silhouette: Verify installation instructions
- [ ] :bust_in_silhouette: Verify quick start guide
- [ ] :bust_in_silhouette: Verify environment variable documentation

### 15.2 Command Documentation

- [ ] :robot: Verify `--help` for all command groups
- [ ] :robot: Verify `--help` for all subcommands
- [ ] :bust_in_silhouette: Verify docs/ contains documentation for each command group
- [ ] :bust_in_silhouette: Verify command examples in documentation

### 15.3 Documentation Accuracy

- [ ] :bust_in_silhouette: Verify documented options match implementation
- [ ] :bust_in_silhouette: Verify documented output matches actual output
- [ ] :bust_in_silhouette: Verify error message documentation

---

## Claude Code Commands Reference

### Installation and Setup

```bash
# Install unitysvc-admin package
pip install -e ../unitysvc-admin

# Verify installation
usvc_admin --help

# Set up environment
export UNITYSVC_API_KEY="your-admin-api-key"
export UNITYSVC_BASE_URL="http://localhost:8000/api/v1"
```

### Running Tests by Command Group

```bash
# Test user commands
usvc_admin users list --limit 5
usvc_admin users show <user-id>

# Test service commands
usvc_admin services list --format json --limit 10
usvc_admin services show <service-id>

# Test seller commands
usvc_admin sellers list
usvc_admin sellers show <seller-id>
usvc_admin sellers ledger <seller-id>

# Test billing commands
usvc_admin invoices list --status draft
usvc_admin statements generate --period 2026-01

# Test wallet commands
usvc_admin wallets list
usvc_admin wallets reconcile <wallet-id>

# Test gateway commands
usvc_admin gateway status
usvc_admin gateway test-examples --service <service-id>
```

### Running pytest Tests

```bash
# Run all tests
cd ../unitysvc-admin && pytest tests/ -v

# Run with coverage
pytest tests/ --cov=unitysvc_admin --cov-report=html

# Run specific test file
pytest tests/test_users.py -v
```

---

## Post-Testing: Converting to Unit Tests

After manual testing, use these prompt templates to have Claude Code write unit tests:

### CLI Command Tests

```
Write pytest unit tests for the usvc_admin users commands:
1. Test `users list` with various filters (email, full_name)
2. Test `users show` with valid and invalid UUIDs
3. Test output formatting (table vs json)
4. Mock the AdminQuery API calls

Use typer.testing.CliRunner and unittest.mock.
Reference: unitysvc-admin/src/unitysvc_admin/users.py
```

### API Client Tests

```
Write pytest unit tests for the AdminQuery class:
1. Test authentication header construction
2. Test GET request handling
3. Test POST with status code return
4. Test async task polling (HTTP 202)
5. Test curl fallback mechanism

Reference: unitysvc-admin/src/unitysvc_admin/query.py
```

### Error Handling Tests

```
Write pytest tests for CLI error handling:
1. Test missing UNITYSVC_API_KEY error
2. Test 401/403/404 error responses
3. Test connection timeout handling
4. Test invalid input validation

Reference: unitysvc-admin/src/unitysvc_admin/utils.py
```

### Billing Command Tests

```
Write pytest tests for billing commands:
1. Test invoices list/show/generate
2. Test statements list/show/generate
3. Test async task completion polling
4. Test error handling for failed generation

Reference: unitysvc-admin/src/unitysvc_admin/invoices.py
Reference: unitysvc-admin/src/unitysvc_admin/statements.py
```

---

## Bug Tracking Table

| Bug ID | Test ID | Mode | Description | Severity | Status |
|--------|---------|------|-------------|----------|--------|
| | | | | | |

**Severity Levels:**
- **Critical**: CLI crashes, data corruption, authentication bypass
- **High**: Command fails completely, no workaround
- **Medium**: Command partially works, workaround exists
- **Low**: Minor output formatting, cosmetic issues

---

## Test Metrics

### Functional Test Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Total Functional Test Cases | 168 | - |
| :robot: Automated Tests Passed | 100% | - |
| :arrows_counterclockwise: Interactive Tests Passed | 95%+ | - |
| Tests Failed | <5% | - |
| Bugs Found - Critical | 0 | - |
| Bugs Found - High | <3 | - |
| Bugs Found - Medium | <10 | - |
| Bugs Found - Low | <20 | - |

### Documentation Test Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Total Documentation Checks | 14 | - |
| :robot: Automated Checks Passed | 100% | - |
| Help Text Coverage | 100% | - |
| Docs Files Exist | 100% | - |
| :bust_in_silhouette: Clarity Average Rating | 4.0+ | - |

### Execution Efficiency

| Metric | Target | Actual |
|--------|--------|--------|
| :robot: Automated test coverage | 30% | - |
| :arrows_counterclockwise: Interactive test coverage | 60% | - |
| :bust_in_silhouette: Manual test coverage | 10% | - |
| Time saved by automation | 40%+ | - |

---

## Execution Mode Summary

| Phase | :robot: Auto | :arrows_counterclockwise: Interactive | :bust_in_silhouette: Manual | Total |
|-------|-------------|---------------------|-------------|-------|
| 1. CLI Setup | 6 | 2 | 0 | 8 |
| 2. User Management | 4 | 7 | 2 | 13 |
| 3. Service Management | 6 | 19 | 2 | 27 |
| 4. Seller Management | 1 | 9 | 2 | 12 |
| 5. Billing & Financial | 4 | 19 | 0 | 23 |
| 6. Wallet Management | 3 | 9 | 0 | 12 |
| 7. Subscription Plans | 4 | 8 | 1 | 13 |
| 8. Content Management | 4 | 12 | 0 | 16 |
| 9. Audit & Logging | 1 | 6 | 1 | 8 |
| 10. Task Management | 3 | 6 | 0 | 9 |
| 11. Database | 1 | 4 | 1 | 6 |
| 12. Gateway | 3 | 12 | 1 | 16 |
| 13. E2E Workflows | 0 | 14 | 0 | 14 |
| 14. Edge Cases | 10 | 7 | 0 | 17 |
| 15. Documentation | 2 | 0 | 12 | 14 |
| **Total** | **52** | **134** | **22** | **208** |

---

## Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| QA Lead | | | |
| Dev Lead | | | |
| Product Owner | | | |
