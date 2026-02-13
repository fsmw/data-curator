# Design Log 05 — UI, I18N, and UX Conventions

## Background
The web UI uses Jinja templates + Alpine.js with bilingual support and a lightweight design system.

## Problem
UX conventions (status tags, destructive actions, button style decisions, localization workflow) were spread across templates and translation files.

## Questions and Answers
- Q: Is UI English-first?
  - A: Yes; English strings are primary and localized via gettext catalogs.
- Q: How are destructive actions handled?
  - A: Confirmed through modal dialogs for irreversible actions.

## Design
1. **Template-driven interactive UI**
   - Jinja-rendered templates with Alpine state/actions.
2. **Localization**
   - `gettext`/`_()` strings with `translations/es_CL/LC_MESSAGES/messages.po|mo`.
3. **Status tags and visual semantics**
   - Soft badges for readability; explicit status tags for ownership/download state.
4. **Action ergonomics**
   - Browse Local action row prioritizes refresh/download/delete and consistent icon spacing.
5. **Destructive safety**
   - “Clean My Data” action requires explicit modal confirmation.

## Implementation Plan
- [x] Keep UI copy in English-first source strings.
- [x] Keep translation update flow (`.po` edit + compile `.mo`).
- [x] Keep modal confirmation for irreversible operations.

## Examples
- ✅ `browse_local.html` uses modal-confirmed `cleanMyData()` flow.
- ✅ `search.html` displays localized tags and action labels.
- ✅ Spanish catalog compiled via pybabel to `.mo`.
- ❌ Direct irreversible deletion without confirmation UI.

## Trade-offs
- **Pros:** Safer operations, clearer states, multilingual usability.
- **Cons:** More translation maintenance as features grow.

