# Implementation Plan: Mises Agentic Architecture
**Based on "Data Formulator" & "Data Anvil" Research**

## 1. Vision & Objectives
Elevate Mises Copilot from a simple chat bot to an **Agentic Data Workbench**. By adopting the "Concept Binding" and "Data Threads" patterns from Microsoft Research, we will allow users to:
1.  **Iterate on Data**: Not just ask questions, but branches of analysis (Data Threads).
2.  **Visual Transformation**: Use natural language to transform data for specific visualizations (e.g., "Aggregate by Region then Pivot by Year").
3.  **Proactive Assistance**: Receive intelligent suggestions for next steps.

## 2. Architecture Overview

### New Module: `src/agents/`
We have introduced a specialized multi-agent system:

| Agent | Purpose | System Prompt Strategy |
|-------|---------|------------------------|
| **DataTransformAgent** | Generates Python (Pandas) code to mutate dataframes. | "Refine Goal" -> "Generate Code" (JSON) |
| **ExplorationAgent** | Suggests follow-up questions. | "Zoom In/Out" taxonomy (JSON) |
| **ExplorationFlow** | Orchestrator. Manages state and routes requests. | Code execution & State management |

### New API Endpoints (`/api/agent/`)
*   `POST /transform`: Accepts Query + Data Summary -> Returns Code & Plan.
*   `POST /suggest`: Accepts Context + History -> Returns Question Suggestions.

## 3. Implementation Phases

### Phase 1: Backend Foundation (COMPLETED)
- [x] Create `src/agents/` structure.
- [x] Implement `DataTransformAgent` with JSON logic.
- [x] Implement `ExplorationAgent` with suggestion logic.
- [x] Implement `ExplorationFlow` orchestrator.
- [x] Enable Streaming in `MisesCopilotAgent`.
- [x] Expose V2 API endpoints.

### Phase 2: Frontend "Data Threads" (NEXT)
- [ ] **State Management**: Update Frontend Store (Alpine/Vue/React) to track "Analysis Steps" (Thread Nodes).
- [ ] **Thread UI**: Create a sidebar or timeline view showing history of transformations.
- [ ] **Suggestion Chips**: Display `ExplorationAgent` output as clickable chips in Chat.

### Phase 3: "Concept Binding" UI
- [ ] **Drag & Drop**: Allow dragging column names into Chat or specific "Channels" (X-Axis, Y-Axis).
- [ ] **Visual Feedback**: Real-time chart updates based on Transformation Agent output.
- [ ] **Auto-Repair**: Frontend auto-submits error logs back to Agent if visualization fails.

## 4. Risks & Mitigations
*   **LLM Latency**: Agents require complex reasoning. **Mitigation**: Use Streaming for all user-facing feedback.
*   **Code Safety**: `DataTransformAgent` generates code. **Mitigation**: (Future) Run code in sandboxed Docker container, not host. Currently running in process (risk accepted for internal tool).
