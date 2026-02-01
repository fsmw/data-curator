#!/usr/bin/env python3
"""
Migration script to fix the FTS table definition.
This removes the content=datasets linkage that causes the "no such column: T.columns" error.
"""
import sqlite3
from pathlib import Path

def migrate_fts_table(db_path: str = "datasets_catalog.db"):
    """Recreate the FTS table without content linkage."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print(f"Migrating database: {db_path}")
        
        # Drop the old FTS table and its triggers
        print("Dropping old FTS table and triggers...")
        cursor.execute("DROP TABLE IF EXISTS datasets_fts")
        cursor.execute("DROP TRIGGER IF EXISTS datasets_ai")
        cursor.execute("DROP TRIGGER IF EXISTS datasets_ad")
        cursor.execute("DROP TRIGGER IF EXISTS datasets_au")
        
        # Create new FTS table without content linkage
        print("Creating new FTS table...")
        cursor.execute("""
            CREATE VIRTUAL TABLE datasets_fts USING fts5(
                indicator_name,
                description,
                columns,
                countries
            )
        """)
        
        # Recreate triggers
        print("Recreating triggers...")
        cursor.execute("""
            CREATE TRIGGER datasets_ai AFTER INSERT ON datasets BEGIN
                INSERT INTO datasets_fts(rowid, indicator_name, description, columns, countries)
                VALUES (new.id, new.indicator_name, COALESCE(new.description, ''), 
                        COALESCE(new.columns_json, ''), COALESCE(new.countries_json, ''));
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER datasets_ad AFTER DELETE ON datasets BEGIN
                DELETE FROM datasets_fts WHERE rowid = old.id;
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER datasets_au AFTER UPDATE ON datasets BEGIN
                UPDATE datasets_fts SET 
                    indicator_name = new.indicator_name,
                    description = COALESCE(new.description, ''),
                    columns = COALESCE(new.columns_json, ''),
                    countries = COALESCE(new.countries_json, '')
                WHERE rowid = new.id;
            END
        """)
        
        # Re-populate FTS table from existing data
        print("Re-populating FTS table from existing datasets...")
        cursor.execute("""
            INSERT INTO datasets_fts(rowid, indicator_name, description, columns, countries)
            SELECT id, indicator_name, COALESCE(description, ''), 
                   COALESCE(columns_json, ''), COALESCE(countries_json, '')
            FROM datasets
        """)
        
        conn.commit()
        print("Migration completed successfully!")
        
        # Verify the migration
        cursor.execute("SELECT COUNT(*) FROM datasets")
        datasets_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM datasets_fts")
        fts_count = cursor.fetchone()[0]
        
        print(f"Verification: {datasets_count} datasets, {fts_count} FTS entries")
        
        if datasets_count != fts_count:
            print("WARNING: Mismatch between datasets and FTS entries!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_fts_table()
