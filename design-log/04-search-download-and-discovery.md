# Design Log 04 — Search, Download, and Dataset Discovery

## Background
The platform supports indicator discovery across local definitions and remote sources, then dataset download into local storage/catalog.

## Problem
Search result states (downloaded globally vs in my account), source-specific behavior, and download lifecycle were not formally documented.

## Questions and Answers
- Q: How is search implemented?
  - A: Hybrid local+remote search with normalization and in-memory filtering (`src/web/api/search.py`).
- Q: What does “downloaded” mean?
  - A: Dataset exists in local catalog; separate flag indicates whether it belongs to current user (`in_my_data`).

## Design
1. **Flat/tag-based indicator search**
   - `IndicatorSearcher` searches id/name/description/tags (no rigid hierarchy).
2. **Hybrid API search**
   - Combines local and remote providers; normalizes fields and source labels.
3. **Download states in UI**
   - Tag **My data** when dataset belongs to current user.
   - Tag **Downloaded** when it exists locally but not owned by current user.
4. **Download packaging**
   - Individual ZIP includes CSV + notes + related files.
   - Backup ZIP includes user-scoped folder and display filenames.

## Implementation Plan
- [x] Keep source normalization and dedup in search API.
- [x] Keep `downloaded` + `in_my_data` status split for clear UX.
- [x] Keep owner-safe dataset mutation/download routes.

## Examples
- ✅ `check_indicator_downloaded(...)` returns ownership-aware status (`src/web/api/search.py`).
- ✅ Search table badges show **My data** vs **Downloaded** (`src/web/templates/search.html`).
- ✅ ZIP export uses user-facing CSV names.
- ❌ Treating all local matches as owned by current user.

## Trade-offs
- **Pros:** Better discoverability and reuse awareness across accounts; less accidental duplicate downloads.
- **Cons:** Slightly more API/UI complexity due to dual status model.

