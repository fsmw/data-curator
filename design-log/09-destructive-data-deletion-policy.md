# Design Log 09 — Destructive Data Deletion Policy

## Background
Users requested an account-scoped “delete all my data” operation from Browse Local.

## Problem
Bulk deletion is irreversible and needs explicit safety and ownership boundaries.

## Questions and Answers
- Q: What is the action contract?
  - A: Delete all datasets/files for current user profile only.
- Q: How is confirmation enforced?
  - A: Mandatory modal confirmation (Yes/No) before API call.

## Design
1. Add `Clean My Data` action in Browse Local.
2. Require confirmation modal with irreversible-action warning.
3. Implement backend endpoint `POST /api/datasets/clear-my-data`.
4. Scope deletion by `owner_username` and user directory.

## Implementation Plan
- [x] UI modal + action button in `browse_local.html`.
- [x] Endpoint implementation in `src/web/api/datasets.py`.
- [x] Delete user-owned files and catalog rows.
- [x] Keep success/error feedback in UI alerts.

## Examples
- ✅ User confirms modal and only own data is removed.
- ❌ Deleting data without confirmation prompt.
- ❌ Deleting data belonging to other users.

## Trade-offs
- **Pros:** Powerful self-service cleanup with explicit safety gate.
- **Cons:** Irreversible action requires clear communication and careful logging.

