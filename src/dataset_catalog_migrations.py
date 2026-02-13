"""Formal schema migrations for DatasetCatalog."""

from pathlib import Path
import sqlite3


MIGRATIONS: list[tuple[int, str, str]] = [
    (1, "add is_edited", "ALTER TABLE datasets ADD COLUMN is_edited INTEGER DEFAULT 0"),
    (2, "add owner_id", "ALTER TABLE datasets ADD COLUMN owner_id INTEGER"),
    (3, "add owner_username", "ALTER TABLE datasets ADD COLUMN owner_username TEXT"),
    (4, "add display_file_name", "ALTER TABLE datasets ADD COLUMN display_file_name TEXT"),
    (5, "add is_public", "ALTER TABLE datasets ADD COLUMN is_public INTEGER DEFAULT 0"),
    (6, "add is_shared", "ALTER TABLE datasets ADD COLUMN is_shared INTEGER DEFAULT 0"),
]


def migrate_dataset_catalog(db_path: Path) -> dict[str, int]:
    """Run ordered schema migrations for datasets_catalog.db."""
    conn = sqlite3.connect(db_path)
    applied = 0
    skipped = 0
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute("SELECT version FROM schema_migrations")
        applied_versions = {row[0] for row in cursor.fetchall()}

        for version, name, sql in MIGRATIONS:
            if version in applied_versions:
                skipped += 1
                continue
            try:
                cursor.execute(sql)
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
            cursor.execute(
                "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
                (version, name),
            )
            applied += 1

        conn.commit()
        return {"applied": applied, "skipped": skipped}
    finally:
        conn.close()
