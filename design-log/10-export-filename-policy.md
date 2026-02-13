# Design Log 10 — Export Filename Policy (UUID vs Display Name)

## Background
Physical storage may use UUID filenames, but exported ZIP contents must be user-friendly.

## Problem
Users were receiving UUID CSV names inside ZIPs, conflicting with expected real/friendly names.

## Questions and Answers
- Q: Which name should appear in exports?
  - A: `display_file_name` (fallback `file_name`) for CSV entries in ZIP downloads.
- Q: Where does this apply?
  - A: Individual dataset ZIP and “download all” backup ZIP.

## Design
1. Keep physical filename decoupled from user-facing export name.
2. Resolve archive CSV name from metadata (`display_file_name` → `file_name`).
3. In backup ZIP, handle filename collisions deterministically with suffixes.

## Implementation Plan
- [x] Update individual ZIP packaging logic.
- [x] Update backup ZIP directory-add helper with display-name mapping.
- [x] Add anti-collision suffixing for duplicate archive names.

## Examples
- ✅ ZIP contains `real_dataset_name.csv`.
- ✅ Duplicate names become `name.csv`, `name_2.csv`, etc.
- ❌ ZIP exposes raw UUID physical filename.

## Trade-offs
- **Pros:** Better UX and traceability for downloaded artifacts.
- **Cons:** Requires metadata lookup during backup packaging.

