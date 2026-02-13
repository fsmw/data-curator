# Design Log 07 — Copilot Chat Model Governance

## Background
The Copilot Chat UI previously showed all models returned by the SDK, which introduced variability and unsupported options.

## Problem
Model availability should be predictable and controlled for UX, cost, and supportability.

## Questions and Answers
- Q: Which models are officially supported in chat UI?
  - A: `gpt-5-mini`, `claude-haiku-4.5`, `gemini-3-flash-preview`, `gpt-4o`, `gpt-4.1`.
- Q: Where is this enforced?
  - A: In the client-side model filtering and selection flow in `src/web/templates/copilot_chat.html`.

## Design
1. Maintain an explicit allowlist in chat UI.
2. Filter API-returned models against that allowlist.
3. Pick default/preferred model from the same ordered allowlist.
4. Reuse filtered list for retry/faster-model fallback logic.

## Implementation Plan
- [x] Add `allowedModelIds` in chat state.
- [x] Add `isAllowedModel()` and `pickPreferredAllowedModel()`.
- [x] Restrict `availableModels` to allowlisted entries.
- [x] Update retry logic to reference `availableModels`.

## Examples
- ✅ Showing only the 5 approved models in selector.
- ❌ Showing all SDK models and allowing unsupported selections.

## Trade-offs
- **Pros:** Stable UX and predictable support envelope.
- **Cons:** New models require intentional updates to allowlist.

