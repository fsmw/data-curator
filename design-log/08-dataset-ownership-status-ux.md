# Design Log 08 — Dataset Ownership Status UX

## Background
Search results can include datasets that already exist locally but may belong to another user account.

## Problem
Users need to distinguish “exists in server storage” from “already in my account” to avoid confusion.

## Questions and Answers
- Q: What status tags are required?
  - A: `Downloaded` (exists locally but not in my account) and `My data` (already in my account).
- Q: Where is ownership determined?
  - A: In `src/web/api/search.py`, using catalog matches plus `owner_username` comparison.

## Design
1. Return two flags from search status resolution:
   - `downloaded`
   - `in_my_data`
2. Render tags in search UI:
   - `My data` when `in_my_data=true`
   - `Downloaded` when `downloaded=true` and `in_my_data=false`
3. Drive action button semantics from `in_my_data` (update vs download).

## Implementation Plan
- [x] Extend status computation in search API.
- [x] Bind new flags in `search.html`.
- [x] Add localization key for `My data`.

## Examples
- ✅ Dataset from another user appears as `Downloaded`.
- ✅ Dataset from current user appears as `My data`.
- ❌ Treating both states as identical.

## Trade-offs
- **Pros:** Clear ownership semantics and better decision support in search.
- **Cons:** Slight increase in API/UI state complexity.

