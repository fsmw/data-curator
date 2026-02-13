# Design Log 06 — AI Agents, RAG, and Fallback Strategy

## Background
The project includes AI-assisted analysis, metadata generation, and retrieval workflows, but it must still function when AI dependencies fail.

## Problem
AI-related design decisions (provider abstraction, fallback modes, compatibility workarounds) were implemented but not explicitly logged.

## Questions and Answers
- Q: Is AI provider hardcoded?
  - A: No, LLM and embedding providers are abstracted and configurable.
- Q: What happens when AI infra fails?
  - A: System falls back to deterministic/template behavior.

## Design
0. **Copilot-first AI stack**
   - Primary LLM runtime is GitHub Copilot SDK.
   - Other provider adapters are legacy compatibility paths, not the default architecture.
1. **Agent orchestration layer**
   - `AgentOrchestrator` composes specialized agents (clean/transform/explore/report).
2. **Unified LLM client abstraction**
   - `MisesLLMClient` defaults to `copilot_sdk`; legacy LiteLLM providers remain optional.
3. **Metadata generation fallback**
   - LLM-first generation with template fallback path in `MetadataGenerator`.
4. **RAG vector backend fallback**
   - Prefer Chroma; fallback to `SimpleVectorStore` (JSON + numpy) for compatibility/runtime resilience.
5. **Embedding provider abstraction**
   - OpenAI-compatible and local sentence-transformer options.

## Implementation Plan
- [x] Keep provider-agnostic AI interfaces.
- [x] Keep graceful fallback behavior for metadata and vector storage.
- [x] Keep orchestration boundaries between agent roles.

## Examples
- ✅ `metadata.py` degrades to template generation when Copilot/LLM init fails.
- ✅ `vector_store.py` supports Chroma and a simple file-based backend.
- ✅ `embeddings.py` factory selects openai/local provider by config.
- ❌ Hard-fail entire pipeline when optional AI features are unavailable.

## Trade-offs
- **Pros:** Higher reliability and operability across environments.
- **Cons:** More code paths to test and maintain for parity.
