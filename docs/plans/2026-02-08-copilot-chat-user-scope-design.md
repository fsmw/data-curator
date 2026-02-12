# Copilot Chat User-Scoped Threads Design

## Summary
Implement server-side, user-scoped Copilot chat threads. Each chat thread and prompt belongs to a user and is only visible to that user. Add endpoints to create, list, update, and delete threads. Remove legacy localStorage persistence and clear existing shared conversations.

## Goals
- Store Copilot chat threads and messages per user.
- Ensure users can only access their own threads.
- Allow users to delete individual threads or clear all threads.
- Remove legacy localStorage history and start with a clean slate.

## Non-Goals
- Redesign Copilot UI or chat features.
- Add analytics or cross-user reporting.
- Change the Copilot SDK integration or streaming protocol.

## Data Model
Add a new SQLAlchemy model:

`CopilotThread`
- `id` (int, PK)
- `user_id` (FK users.id, indexed)
- `title` (string)
- `session_id` (string, nullable)
- `messages_json` (text/json string)
- `charts_json` (text/json string)
- `last_message` (string)
- `created_at` (datetime)
- `updated_at` (datetime)

Indexes: `user_id`, `updated_at`.

## API Endpoints
All endpoints are `@login_required` and enforce `thread.user_id == current_user.id`.

- `GET /api/copilot/threads`
  - Returns the current user threads, ordered by `updated_at` desc.

- `POST /api/copilot/threads`
  - Creates a new empty thread for the current user.
  - Returns thread metadata.

- `PUT /api/copilot/threads/<id>`
  - Updates title, messages_json, charts_json, session_id, last_message.
  - Rejects updates for threads not owned by the user.

- `DELETE /api/copilot/threads/<id>`
  - Deletes one thread owned by the user.

- `POST /api/copilot/threads/clear`
  - Deletes all threads for the current user.

## UI Changes
- Replace localStorage-based persistence with API calls.
- On load, fetch `/api/copilot/threads` and populate `threads`, `messages`, `activeThreadId`.
- On new thread, `POST /api/copilot/threads` and switch to returned id.
- On send/stream completion, `PUT /api/copilot/threads/<id>` to persist messages and session_id.
- On delete thread, call `DELETE /api/copilot/threads/<id>`.
- On clear chat, call `POST /api/copilot/threads/clear`.

## Legacy History Deletion
- Remove existing shared localStorage key `copilot_threads` once per browser load.
- New server table starts empty; no legacy history is migrated.

## Security & Authorization
- All thread access is scoped to `current_user.id`.
- Return 404 for threads not owned by the user.
- No cross-user data is returned in list or detail endpoints.

## Error Handling
- Missing or invalid payloads return 400 with a clear message.
- Unauthorized access returns 404 (avoid leaking existence).
- Server errors return 500 with log details.

## Testing
- Unit tests for thread CRUD: create, list, update, delete, clear.
- Authorization tests: user cannot access another user thread.
- UI sanity check: create thread, send message, reload page, verify persistence.
