"""
Dataset Catalog - SQLite3-based metadata index for local CSV datasets.

This module provides a fast, searchable catalog of all downloaded datasets
with metadata extraction, statistics, and full-text search capabilities.
"""

import sqlite3
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import pandas as pd

from src.config import Config


class DatasetCatalog:
    """Manages a SQLite3 catalog of downloaded datasets with metadata."""
    
    def __init__(self, config: Config):
        self.config = config
        self.db_path = config.data_root / "datasets_catalog.db"
        self.datasets_dir = config.get_directory('clean')
        
        # Initialize database
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize SQLite3 database with schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main datasets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_name TEXT NOT NULL,
                source TEXT NOT NULL,
                indicator_id TEXT,
                indicator_name TEXT NOT NULL,
                description TEXT,
                topic TEXT,
                
                file_size_bytes INTEGER,
                file_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modified_at TIMESTAMP,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                row_count INTEGER,
                column_count INTEGER,
                columns_json TEXT,
                
                min_year INTEGER,
                max_year INTEGER,
                
                countries_json TEXT,
                country_count INTEGER,
                regions_json TEXT,
                
                null_percentage REAL,
                completeness_score REAL,
                is_edited INTEGER DEFAULT 0
            )
        """)
        
        try:
            cursor.execute("ALTER TABLE datasets ADD COLUMN is_edited INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        # Full-text search index
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS datasets_fts USING fts5(
                indicator_name,
                description,
                columns,
                countries
            )
        """)
        
        # Dataset columns detail table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dataset_columns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL,
                column_name TEXT NOT NULL,
                column_type TEXT,
                sample_values_json TEXT,
                unique_count INTEGER,
                null_count INTEGER,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
            )
        """)
        
        # Triggers for FTS sync
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS datasets_ai AFTER INSERT ON datasets BEGIN
                INSERT INTO datasets_fts(rowid, indicator_name, description, columns, countries)
                VALUES (new.id, new.indicator_name, COALESCE(new.description, ''), 
                        COALESCE(new.columns_json, ''), COALESCE(new.countries_json, ''));
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS datasets_ad AFTER DELETE ON datasets BEGIN
                DELETE FROM datasets_fts WHERE rowid = old.id;
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS datasets_au AFTER UPDATE ON datasets BEGIN
                UPDATE datasets_fts SET 
                    indicator_name = new.indicator_name,
                    description = COALESCE(new.description, ''),
                    columns = COALESCE(new.columns_json, ''),
                    countries = COALESCE(new.countries_json, '')
                WHERE rowid = new.id;
            END
        """)
        
        # Indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_datasets_source ON datasets(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_datasets_topic ON datasets(topic)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_datasets_modified ON datasets(modified_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_datasets_indicator ON datasets(indicator_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_columns_dataset ON dataset_columns(dataset_id)")
        
        conn.commit()
        conn.close()
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file for change detection."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from CSV file."""
        try:
            # Read CSV (sample first to avoid loading huge files)
            df = pd.read_csv(file_path, nrows=10000)
            
            metadata = {
                'row_count': len(df),
                'column_count': len(df.columns),
                'columns': df.columns.tolist(),
            }
            
            # Detect year column and extract temporal range
            year_col = None
            for col in ['year', 'Year', 'YEAR', 'año', 'time']:
                if col in df.columns:
                    year_col = col
                    break
            
            if year_col and df[year_col].notna().any():
                metadata['min_year'] = int(df[year_col].min())
                metadata['max_year'] = int(df[year_col].max())
            
            # Detect country column and extract countries
            country_col = None
            for col in ['country', 'Country', 'COUNTRY', 'country_code', 'iso3', 'ISO3']:
                if col in df.columns:
                    country_col = col
                    break
            
            if country_col:
                countries = df[country_col].dropna().unique().tolist()
                metadata['countries'] = [str(c) for c in countries[:200]]  # Limit to 200
                metadata['country_count'] = len(countries)
            
            # Calculate data quality metrics
            total_cells = df.shape[0] * df.shape[1]
            null_cells = df.isna().sum().sum()
            metadata['null_percentage'] = (null_cells / total_cells * 100) if total_cells > 0 else 0
            metadata['completeness_score'] = max(0, 100 - metadata['null_percentage'])
            
            # Extract column details
            columns_detail = []
            for col in df.columns:
                col_info = {
                    'name': col,
                    'type': str(df[col].dtype),
                    'unique_count': df[col].nunique(),
                    'null_count': int(df[col].isna().sum()),
                    'sample_values': df[col].dropna().head(5).tolist()
                }
                columns_detail.append(col_info)
            
            metadata['columns_detail'] = columns_detail
            
            return metadata
            
        except Exception as e:
            print(f"Error extracting metadata from {file_path}: {e}")
            return {
                'row_count': 0,
                'column_count': 0,
                'columns': [],
                'null_percentage': 0,
                'completeness_score': 0,
                'columns_detail': []
            }
    
    def _parse_filename(self, file_path: Path) -> Dict[str, str]:
        """Parse filename to extract indicator info.
        
        Handles filenames produced by the cleaner which include an optional identifier
        and a timestamp, e.g.:
            topic_source_identifier_coverage_start_end_YYYYMMDDHHMMSS.csv
        or
            topic_source_coverage_start_end_YYYYMMDDHHMMSS.csv

        Returns a dict with keys: topic, source, indicator_name, indicator_id (optional)
        """
        parts = file_path.stem.split('_')

        # Detect and strip trailing timestamp (YYYYMMDDHHMMSS)
        id_part = None
        timestamp = None
        if parts and len(parts[-1]) == 14 and parts[-1].isdigit():
            timestamp = parts.pop()

        # Detect and strip year range if present (last two parts are 4-digit years)
        start_year = None
        end_year = None
        if len(parts) >= 2 and parts[-1].isdigit() and len(parts[-1]) == 4 and parts[-2].isdigit() and len(parts[-2]) == 4:
            end_year = parts.pop()
            start_year = parts.pop()

        # Basic defaults
        topic = parts[0] if parts else 'general'
        source = 'unknown'
        indicator_name = file_path.stem.replace('_', ' ').title()

        # Known sources
        sources = ['owid', 'oecd', 'ilostat', 'imf', 'worldbank', 'eclac', 'sample']

        # Find source and possible identifier
        for idx, part in enumerate(parts):
            pl = part.lower()
            if pl in sources:
                source = pl
                # If there is an extra part after source and before coverage, treat it as identifier
                # Expected layout now: topic, source, identifier?, coverage, ...
                if idx + 1 < len(parts):
                    # candidate for identifier is the next part if it's not a known coverage or year
                    candidate = parts[idx + 1]
                    # if candidate is not a known source and not numeric, accept as identifier
                    if candidate.lower() not in sources and not (candidate.isdigit() and len(candidate) == 4):
                        id_part = candidate
                break

        # Build a human-friendly indicator_name
        if id_part:
            # IMPROVEMENT: Combine topic and identifier for better context if id_part is generic keywords like "latam"
            if str(id_part).lower() in ['latam', 'global', 'world', 'total']:
                indicator_name = f"{topic.replace('_', ' ').title()} - {str(id_part).title()}"
            else:
                # Use identifier (slug-like) as primary label
                indicator_name = str(id_part).replace('-', ' ').replace('_', ' ').title()
                
            # Add source if ambiguous? changing logic to be strictly Topic - ID seems better for browsing
            # If indicator name is too short, prepend topic
            if len(indicator_name) < 5 and topic:
                 indicator_name = f"{topic.replace('_', ' ').title()} - {indicator_name}"

        else:
            # Fall back to combining topic and source for a readable name
            indicator_name = f"{topic.replace('_', ' ').title()} ({source.upper()})" if source != 'unknown' else topic.replace('_', ' ').title()

        return {
            'topic': topic,
            'source': source,
            'indicator_name': indicator_name,
            'indicator_id': id_part
        }
    
    def index_dataset(self, file_path: Path, force: bool = False) -> Optional[int]:
        """Index a single dataset into the catalog.
        
        Args:
            file_path: Path to CSV file
            force: If True, re-index even if file hasn't changed
            
        Returns:
            Dataset ID if indexed successfully, None otherwise
        """
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return None

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Check if file already indexed
            file_hash = self._compute_file_hash(file_path)
            cursor.execute("SELECT id, file_hash FROM datasets WHERE file_path = ?", (str(file_path),))
            existing = cursor.fetchone()

            if existing and not force:
                existing_id, existing_hash = existing
                if existing_hash == file_hash:
                    # File hasn't changed, skip
                    return existing_id

            # Extract metadata
            metadata = self._extract_metadata(file_path)
            filename_info = self._parse_filename(file_path)

            # Get file stats
            stat = file_path.stat()
            modified_at = datetime.fromtimestamp(stat.st_mtime).isoformat()

            # Generate description
            description = (
                f"{filename_info['indicator_name']} dataset from {filename_info['source'].upper()}. "
                f"Contains {metadata.get('row_count', 0):,} rows and {metadata.get('column_count', 0)} columns"
            )
            if metadata.get('min_year') and metadata.get('max_year'):
                description += f" covering available years {metadata['min_year']} to {metadata['max_year']}."
            else:
                description += "."

            # Prepare data
            dataset_data = {
                'file_path': str(file_path),
                'file_name': file_path.name,
                'source': filename_info['source'],
                'indicator_name': filename_info['indicator_name'],
                'topic': filename_info['topic'],
                'description': description, # Computed field
                'file_size_bytes': stat.st_size,
                'file_hash': file_hash,
                'modified_at': modified_at,
                'indexed_at': datetime.now().isoformat(),
                'row_count': metadata.get('row_count', 0),
                'column_count': metadata.get('column_count', 0),
                'columns_json': json.dumps(metadata.get('columns', [])),
                'indicator_id': filename_info.get('indicator_id'),
                'min_year': metadata.get('min_year'),
                'max_year': metadata.get('max_year'),
                'countries_json': json.dumps(metadata.get('countries', [])),
                'country_count': metadata.get('country_count', 0),
                'null_percentage': metadata.get('null_percentage', 0),
                'completeness_score': metadata.get('completeness_score', 0),
            }

            # Upsert record
            if existing:
                dataset_id = existing[0]
                update_sql = """
                    UPDATE datasets SET 
                        file_name = ?, source = ?, indicator_id = ?, indicator_name = ?, topic = ?, description = ?,
                        file_size_bytes = ?, file_hash = ?, modified_at = ?, indexed_at = ?,
                        row_count = ?, column_count = ?, columns_json = ?,
                        min_year = ?, max_year = ?,
                        countries_json = ?, country_count = ?,
                        null_percentage = ?, completeness_score = ?
                    WHERE id = ?
                """
                cursor.execute(update_sql, (
                    dataset_data['file_name'], dataset_data['source'], dataset_data['indicator_id'],
                    dataset_data['indicator_name'], dataset_data['topic'], dataset_data['description'],
                    dataset_data['file_size_bytes'], dataset_data['file_hash'],
                    dataset_data['modified_at'], dataset_data['indexed_at'],
                    dataset_data['row_count'], dataset_data['column_count'],
                    dataset_data['columns_json'],
                    dataset_data['min_year'], dataset_data['max_year'],
                    dataset_data['countries_json'], dataset_data['country_count'],
                    dataset_data['null_percentage'], dataset_data['completeness_score'],
                    dataset_id
                ))

                # Delete old column details
                cursor.execute("DELETE FROM dataset_columns WHERE dataset_id = ?", (dataset_id,))
            else:
                insert_sql = """
                    INSERT INTO datasets (
                        file_path, file_name, source, indicator_id, indicator_name, topic, description,
                        file_size_bytes, file_hash, modified_at, indexed_at,
                        row_count, column_count, columns_json,
                        min_year, max_year,
                        countries_json, country_count,
                        null_percentage, completeness_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(insert_sql, (
                    dataset_data['file_path'], dataset_data['file_name'],
                    dataset_data['source'], dataset_data['indicator_id'], dataset_data['indicator_name'], 
                    dataset_data['topic'], dataset_data['description'],
                    dataset_data['file_size_bytes'], dataset_data['file_hash'],
                    dataset_data['modified_at'], dataset_data['indexed_at'],
                    dataset_data['row_count'], dataset_data['column_count'],
                    dataset_data['columns_json'],
                    dataset_data['min_year'], dataset_data['max_year'],
                    dataset_data['countries_json'], dataset_data['country_count'],
                    dataset_data['null_percentage'], dataset_data['completeness_score'],
                ))
                dataset_id = cursor.lastrowid

            # Insert column details
            for col_info in metadata.get('columns_detail', []):
                cursor.execute("""
                    INSERT INTO dataset_columns (
                        dataset_id, column_name, column_type,
                        sample_values_json, unique_count, null_count
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    dataset_id, col_info['name'], col_info['type'],
                    json.dumps(col_info.get('sample_values', [])),
                    col_info.get('unique_count', 0), col_info.get('null_count', 0)
                ))

            conn.commit()
            print(f"✓ Indexed: {file_path.name}")
            return dataset_id

        except Exception as e:
            conn.rollback()
            print(f"Error indexing {file_path}: {e}")
            return None

        finally:
            conn.close()

    
    def index_all(self, force: bool = False) -> Dict[str, int]:
        """Index all CSV files in the datasets directory.
        
        Returns:
            Dictionary with statistics: indexed, skipped, errors
        """
        stats = {'indexed': 0, 'skipped': 0, 'errors': 0}
        
        print(f"Scanning {self.datasets_dir} for CSV files...")
        csv_files = list(self.datasets_dir.rglob("*.csv"))
        print(f"Found {len(csv_files)} CSV files")
        
        for csv_file in csv_files:
            result = self.index_dataset(csv_file, force=force)
            if result:
                stats['indexed'] += 1
            elif result is None:
                stats['errors'] += 1
            else:
                stats['skipped'] += 1
        
        return stats

    def list_datasets(self, limit: int = 5000) -> List[Dict]:
        """List all datasets in the catalog (for recommender and listing)."""
        return self.search(query="", filters=None, limit=limit)

    def search(self, query: str = "", filters: Optional[Dict] = None, 
               limit: int = 100) -> List[Dict]:
        """Search datasets with full-text search and filters.
        
        Args:
            query: Search query (searches name, description, columns, countries)
            filters: Optional filters (source, topic, min_year, max_year)
            limit: Maximum number of results
            
        Returns:
            List of dataset records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Build query
            if query:
                # Full-text search
                sql = """
                    SELECT d.* FROM datasets d
                    JOIN datasets_fts fts ON d.id = fts.rowid
                    WHERE datasets_fts MATCH ?
                """
                params = [query]
            else:
                sql = "SELECT * FROM datasets WHERE 1=1"
                params = []
            
            # Apply filters
            if filters:
                if 'source' in filters and filters['source']:
                    sql += " AND source = ?"
                    params.append(filters['source'])
                
                if 'topic' in filters and filters['topic']:
                    sql += " AND topic = ?"
                    params.append(filters['topic'])
                
                if 'min_year' in filters and filters['min_year']:
                    sql += " AND max_year >= ?"
                    params.append(filters['min_year'])
                
                if 'max_year' in filters and filters['max_year']:
                    sql += " AND min_year <= ?"
                    params.append(filters['max_year'])
            
            sql += " ORDER BY indexed_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # Convert to dicts and parse JSON fields
            results = []
            for row in rows:
                record = dict(row)
                record['columns'] = json.loads(record['columns_json']) if record['columns_json'] else []
                record['countries'] = json.loads(record['countries_json']) if record['countries_json'] else []
                results.append(record)
            
            return results
            
        finally:
            conn.close()
    
    def get_dataset(self, dataset_id: int) -> Optional[Dict]:
        """Get a single dataset by ID with full details."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            dataset = dict(row)
            dataset['columns'] = json.loads(dataset['columns_json']) if dataset['columns_json'] else []
            dataset['countries'] = json.loads(dataset['countries_json']) if dataset['countries_json'] else []
            
            # Get column details
            cursor.execute("SELECT * FROM dataset_columns WHERE dataset_id = ?", (dataset_id,))
            column_rows = cursor.fetchall()
            dataset['columns_detail'] = [dict(r) for r in column_rows]
            
            return dataset
            
        finally:
            conn.close()

    def get_dataset_by_file_name(self, file_name: str) -> Optional[Dict]:
        """Get a single dataset by exact file name."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM datasets WHERE file_name = ?", (file_name,))
            row = cursor.fetchone()

            if not row:
                return None

            dataset = dict(row)
            dataset['columns'] = json.loads(dataset['columns_json']) if dataset['columns_json'] else []
            dataset['countries'] = json.loads(dataset['countries_json']) if dataset['countries_json'] else []

            # Get column details
            cursor.execute("SELECT * FROM dataset_columns WHERE dataset_id = ?", (dataset['id'],))
            column_rows = cursor.fetchall()
            dataset['columns_detail'] = [dict(r) for r in column_rows]

            return dataset

        finally:
            conn.close()
    
    def get_preview_data(self, dataset_id: int, limit: int = 100) -> Optional[pd.DataFrame]:
        """Load preview of dataset (first N rows)."""
        dataset = self.get_dataset(dataset_id)
        if not dataset:
            return None
        
        try:
            file_path = Path(dataset['file_path'])
            if not file_path.exists():
                return None
            
            df = pd.read_csv(file_path, nrows=limit)
            return df
        except Exception as e:
            print(f"Error loading preview: {e}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get catalog statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # Total datasets
            cursor.execute("SELECT COUNT(*) FROM datasets")
            stats['total_datasets'] = cursor.fetchone()[0]
            
            # By source
            cursor.execute("SELECT source, COUNT(*) FROM datasets GROUP BY source")
            stats['by_source'] = dict(cursor.fetchall())
            
            # By topic
            cursor.execute("SELECT topic, COUNT(*) FROM datasets GROUP BY topic")
            stats['by_topic'] = dict(cursor.fetchall())
            
            # Total size
            cursor.execute("SELECT SUM(file_size_bytes) FROM datasets")
            stats['total_size_mb'] = (cursor.fetchone()[0] or 0) / (1024 * 1024)
            
            # Average completeness
            cursor.execute("SELECT AVG(completeness_score) FROM datasets")
            stats['avg_completeness'] = cursor.fetchone()[0] or 0
            
            return stats
            
        finally:
            conn.close()
    
    def delete_dataset(self, dataset_id: int) -> bool:
        """Delete a dataset from the catalog (and optionally the file)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def refresh(self) -> Dict[str, int]:
        """Re-index all datasets (check for changes)."""
        return self.index_all(force=False)

    def latest_per_identifier(self) -> List[Dict[str, Any]]:
        """Return one latest dataset record per indicator identifier.

        If `indicator_id` is present, group by it; otherwise group by `indicator_name`.
        Returns a list of dataset dicts ordered by indexed_at DESC.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Prefer grouping by indicator_id when available
            sql = """
                SELECT d.* FROM datasets d
                INNER JOIN (
                    SELECT
                        COALESCE(NULLIF(indicator_id, ''), indicator_name) AS gid,
                        MAX(indexed_at) AS max_indexed
                    FROM datasets
                    GROUP BY gid
                ) sub ON (COALESCE(NULLIF(d.indicator_id, ''), d.indicator_name) = sub.gid AND d.indexed_at = sub.max_indexed)
                ORDER BY d.indexed_at DESC
            """
            cursor.execute(sql)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                record = dict(row)
                record['columns'] = json.loads(record['columns_json']) if record.get('columns_json') else []
                record['countries'] = json.loads(record['countries_json']) if record.get('countries_json') else []
                results.append(record)

            return results
        finally:
            conn.close()

    def get_versions_for_identifier(self, identifier: str, source: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return all dataset versions for a given identifier (indicator_id or indicator_name).

        If `source` is provided, filter by source as well.
        Results ordered by `indexed_at` DESC (newest first).
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Match by exact indicator_id or case-insensitive indicator_name
            sql = "SELECT * FROM datasets WHERE (indicator_id = ? OR lower(indicator_name) = ?)"
            params = [identifier, identifier.lower()]
            if source:
                sql += " AND source = ?"
                params.append(source)
            sql += " ORDER BY indexed_at DESC"

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                record = dict(row)
                record['columns'] = json.loads(record['columns_json']) if record.get('columns_json') else []
                record['countries'] = json.loads(record['countries_json']) if record.get('countries_json') else []
                results.append(record)

            return results
        finally:
            conn.close()
