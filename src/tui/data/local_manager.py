"""Local filesystem data manager for the TUI."""

from pathlib import Path
from typing import Dict, List, Optional
import os
from ..config import DATA_DIR, METADATA_DIR


class LocalDataManager:
    """Manage reading local dataset and metadata files."""

    def __init__(self):
        self.data_dir = DATA_DIR
        self.metadata_dir = METADATA_DIR
        self._topics_cache: Optional[Dict] = None

    def get_topics(self) -> List[str]:
        """Get list of topics from 02_Datasets_Limpios/."""
        if not self.data_dir.exists():
            return []

        topics = []
        for item in self.data_dir.iterdir():
            if item.is_dir():
                topics.append(item.name)
        return sorted(topics)

    def get_datasets_by_topic(self, topic: str) -> List[Dict]:
        """Get all datasets for a specific topic."""
        topic_dir = self.data_dir / topic
        if not topic_dir.exists():
            return []

        datasets = []
        for file in topic_dir.glob("*.csv"):
            datasets.append(self._parse_dataset_info(file))
        return sorted(datasets, key=lambda x: x["name"])

    def _parse_dataset_info(self, file_path: Path) -> Dict:
        """Parse dataset information from filename and file stats."""
        stat = file_path.stat()
        
        # Parse filename: {topic}_{source}_{coverage}_{start}_{end}.csv
        name = file_path.stem
        parts = name.split("_")
        
        return {
            "name": file_path.name,
            "path": str(file_path),
            "size": stat.st_size,
            "size_readable": self._format_size(stat.st_size),
            "rows": self._count_csv_rows(file_path),
            "modified": stat.st_mtime,
            "modified_readable": self._format_timestamp(stat.st_mtime),
            "metadata": self.get_metadata_for_dataset(name),
        }

    def get_all_datasets(self) -> List[Dict]:
        """Get all datasets across all topics."""
        all_datasets = []
        for topic in self.get_topics():
            all_datasets.extend(self.get_datasets_by_topic(topic))
        return all_datasets

    def get_metadata_for_dataset(self, dataset_name: str) -> Optional[str]:
        """Get metadata file content for a dataset."""
        # Extract topic from dataset name
        parts = dataset_name.split("_")
        if not parts:
            return None

        topic = parts[0]
        metadata_file = self.metadata_dir / f"{topic}.md"

        if metadata_file.exists():
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                return None
        return None

    def get_metadata_content(self, topic: str) -> Optional[str]:
        """Get metadata file content for a topic."""
        metadata_file = self.metadata_dir / f"{topic}.md"

        if metadata_file.exists():
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                return None
        return None

    def _count_csv_rows(self, file_path: Path) -> int:
        """Count rows in a CSV file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return sum(1 for _ in f) - 1  # Subtract header
        except Exception:
            return 0

    @staticmethod
    def _format_size(bytes_size: int) -> str:
        """Format bytes to human readable size."""
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_size < 1024:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.1f} TB"

    @staticmethod
    def _format_timestamp(timestamp: float) -> str:
        """Format timestamp to readable date."""
        from datetime import datetime

        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
