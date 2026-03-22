# PR Summary: Seller Dashboard Improvements & Dedup Command

## Overview

This PR introduces several improvements to the seller and admin dashboards, fixes bugs related to service management, and adds a new `usvc services dedup` command for removing duplicate draft services.

## Changes

### Seller Dashboard (`frontend/app/(seller)/seller/listings/page.tsx`)

- **Added "deprecated" status** to the status filter dropdown to match backend `OpsStatusEnum`
- **Improved Actions dropdown UX**: Now shows all possible actions with enabled/disabled states based on selected services, instead of only showing applicable actions
- **Expanded deletable statuses**: Services with status `draft`, `pending`, `testing`, `rejected`, `suspended`, or `deprecated` can now be deleted (backend determines final deletability)
- **Fixed stats counters**: Separated "Draft" and "Pending" counters that were previously combined
- **Added auto-scroll**: When a row is selected, the details panel automatically scrolls into view
- **Removed pagination**: All services are now displayed in a scrollable container (sellers typically don't have huge numbers of services)
- **Fixed dedup API call**: Changed from raw `fetch()` to use generated client `SellerServicesService.sellerDedupDraftServices()`

### Admin Dashboard (`frontend/app/(admin)/admin/services/page.tsx`)

- **Added auto-scroll**: Same improvement as seller dashboard - details panel scrolls into view on row selection

### Backend (`backend/app/api/routes/seller/services.py`)

- **Fixed FK constraint error**: Added `await session.flush()` after deleting enrollments before deleting the service to prevent foreign key violations
- **Added dedup endpoint** (`POST /v1/seller/services/dedup`): Removes duplicate draft services that have identical `provider_id`, `offering_id`, and `listing_id`

### Dead Code Removal (`frontend/app/(seller)/seller/drafts/[id]/page.tsx`, `frontend/components/DraftEditor/DraftTreeEditor.tsx`)

- Removed `ProviderSharingInfo` and `OfferingSharingInfo` interfaces
- Removed `useQuery` calls to non-existent `/api/v1/seller/services/sharing-info/*` endpoints
- Removed all `sharingInfo` props and related UI code from panels

### Documentation (`unitysvc-services` repo)

- **README.md**: Added `dedup` command to the Remote Service Operations table
- **docs/cli-reference.md**: Added comprehensive documentation for `usvc services dedup` command including:
  - Command syntax and options
  - How duplicate detection works
  - Why the command is needed (cloning, repeated uploads, submit failures)
  - Example usage and output
  - Important notes and limitations

## Dedup Command Details

### Purpose

Remove duplicate draft services that were created by:
- Cloning a service and uploading without changes
- Repeatedly uploading the same data
- Preventing "A service with identical content already exists" errors when submitting for review

### How It Works

1. Finds all draft services for the current seller
2. Processes in creation order (oldest first)
3. Keeps the first draft with unique content (same `provider_id` + `offering_id` + `listing_id`)
4. Removes subsequent drafts with identical content
5. Also removes drafts that duplicate non-draft services (pending, active, etc.)

### Usage

```bash
# Interactive (with confirmation)
usvc services dedup

# Non-interactive
usvc services dedup -y
```

## Test Plan

- [ ] Verify status filter dropdown includes "deprecated" option
- [ ] Verify Actions dropdown shows all actions with correct enabled/disabled states
- [ ] Verify deleting services works without FK constraint errors
- [ ] Verify stats counters update correctly after status changes
- [ ] Verify auto-scroll works when selecting a row in the table
- [ ] Verify all services display without pagination
- [ ] Verify `usvc services dedup` removes duplicate drafts correctly
- [ ] Verify dedup button in frontend calls the correct API endpoint

---

🤖 Generated with [Claude Code](https://claude.ai/code)
