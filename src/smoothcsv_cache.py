"""Shared helpers for sampled SmoothCSV SQLite cache tables."""

import os
import re
import sqlite3
from pathlib import Path

import pandas as pd

SQL_SAMPLE_LIMIT = int(os.getenv("SMOOTHCSV_SQL_SAMPLE_LIMIT", "5000"))
SQL_PREVIEW_LIMIT = int(os.getenv("SMOOTHCSV_SQL_PREVIEW_LIMIT", "200"))


def get_smoothcsv_db_path(data_root: Path) -> Path:
    return data_root / "smoothcsv_cache.db"


def _init_smoothcsv_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dataset_mapping (
            dataset_id INTEGER PRIMARY KEY,
            table_name TEXT NOT NULL,
            file_hash TEXT,
            sample_limit INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def _smoothcsv_table_name(dataset_id: int) -> str:
    return f"table{dataset_id:06d}"


def ensure_smoothcsv_table(
    conn: sqlite3.Connection,
    dataset: dict,
    sample_limit: int,
) -> str:
    _init_smoothcsv_db(conn)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT table_name, file_hash, sample_limit FROM dataset_mapping WHERE dataset_id = ?",
        (dataset["id"],),
    )
    row = cursor.fetchone()
    table_name = row["table_name"] if row else _smoothcsv_table_name(dataset["id"])
    current_hash = dataset.get("file_hash")
    needs_reload = (
        row is None
        or row["file_hash"] != current_hash
        or row["sample_limit"] != sample_limit
    )

    if needs_reload:
        file_path = Path(dataset["file_path"])
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")
        df = pd.read_csv(file_path, nrows=sample_limit)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        cursor.execute(
            """
            INSERT INTO dataset_mapping (dataset_id, table_name, file_hash, sample_limit)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(dataset_id) DO UPDATE SET
                table_name = excluded.table_name,
                file_hash = excluded.file_hash,
                sample_limit = excluded.sample_limit,
                updated_at = CURRENT_TIMESTAMP
            """,
            (dataset["id"], table_name, current_hash, sample_limit),
        )
        conn.commit()

    return table_name


def prepare_smoothcsv_sql(sql: str, limit: int) -> str:
    sql = sql.strip().rstrip(";")
    if not sql:
        raise ValueError("Missing SQL query.")
    if not sql.lower().startswith("select"):
        raise ValueError("Only SELECT queries are supported.")
    if not re.search(r"\blimit\b", sql, flags=re.IGNORECASE):
        sql = f"{sql} LIMIT {limit}"
    return sql
