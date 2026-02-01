import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime


class ChatHistory:
    """SQLite-backed chat history store.

    Stores recent chat sessions in an SQLite database file under a directory.
    """

    def __init__(self, storage_dir: Path, max_items: int = 50):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.storage_dir / "history.db"
        self.max_items = int(max_items)
        self._ensure_db()

    def _get_conn(self):
        # Open a new connection per operation to avoid cross-thread issues.
        return sqlite3.connect(str(self.db_path))

    def _ensure_db(self):
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS history (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    provider TEXT,
                    model TEXT,
                    created_at TEXT,
                    messages_json TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def add_entry(
        self,
        messages: List[Dict[str, str]],
        provider: str,
        model: Optional[str] = None,
        title: Optional[str] = None,
    ) -> str:
        """Add a new chat session. Returns the generated id."""
        entry_id = str(uuid4())
        created_at = datetime.utcnow().isoformat() + "Z"

        # Determine a title if not provided (use first user message snippet)
        if not title:
            title = ""
            for m in messages:
                if m.get("role") == "user" and m.get("content"):
                    title = m.get("content")[:80]
                    break
            if not title:
                title = f"Chat {created_at}"

        messages_json = json.dumps(messages, ensure_ascii=False)

        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO history (id, title, provider, model, created_at, messages_json) VALUES (?, ?, ?, ?, ?, ?)",
                (entry_id, title, provider, model, created_at, messages_json),
            )
            conn.commit()

            # Trim to most recent max_items
            cur.execute("SELECT COUNT(1) FROM history")
            count = cur.fetchone()[0]
            if count > self.max_items:
                to_remove = count - self.max_items
                # delete oldest rows
                cur.execute(
                    "DELETE FROM history WHERE id IN (SELECT id FROM history ORDER BY created_at ASC LIMIT ?)",
                    (to_remove,),
                )
                conn.commit()
        finally:
            conn.close()

        return entry_id

    def list_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, title, provider, model, created_at FROM history ORDER BY created_at DESC LIMIT ?",
                (int(limit),),
            )
            rows = cur.fetchall()
            results = []
            for r in rows:
                results.append(
                    {
                        "id": r[0],
                        "title": r[1],
                        "provider": r[2],
                        "model": r[3],
                        "created_at": r[4],
                    }
                )
            return results
        finally:
            conn.close()

    def get(self, entry_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, title, provider, model, created_at, messages_json FROM history WHERE id = ?",
                (entry_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            try:
                messages = json.loads(row[5])
            except Exception:
                messages = []
            return {
                "id": row[0],
                "title": row[1],
                "provider": row[2],
                "model": row[3],
                "created_at": row[4],
                "messages": messages,
            }
        finally:
            conn.close()

    def delete_entry(self, entry_id: str) -> bool:
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM history WHERE id = ?", (entry_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def rename_entry(self, entry_id: str, new_title: str) -> bool:
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE history SET title = ? WHERE id = ?", (new_title, entry_id))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
