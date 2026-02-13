import os
import tempfile
import shutil
from pathlib import Path
from src.chat_history import ChatHistory


def test_add_get_list_delete_rename():
    tmpdir = Path(tempfile.mkdtemp())
    try:
        store = ChatHistory(tmpdir)

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]

        eid = store.add_entry(messages=messages, provider="ollama", model="gpt-oss:1b")
        assert isinstance(eid, str) and len(eid) > 0

        entry = store.get(eid)
        assert entry is not None
        assert entry["id"] == eid
        assert entry["provider"] == "ollama"
        assert entry["model"] == "gpt-oss:1b"
        assert isinstance(entry["messages"], list)

        recent = store.list_recent(limit=10)
        assert any(r["id"] == eid for r in recent)

        # Rename
        ok = store.rename_entry(eid, "New Title")
        assert ok
        entry2 = store.get(eid)
        assert entry2["title"] == "New Title"

        # Delete
        ok = store.delete_entry(eid)
        assert ok
        assert store.get(eid) is None

    finally:
        shutil.rmtree(tmpdir)
