"""Download coordinator for orchestrating data downloads."""

from typing import Callable, Dict, Optional, List
from pathlib import Path
import sys
import os
import json
import asyncio
import threading
from datetime import datetime

# Add parent directory to path to import existing modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.config import Config
from src.ingestion import DataIngestionManager
from src.cleaning import DataCleaner
from src.metadata import MetadataGenerator


class DownloadCoordinator:
    """Orchestrate downloads by coordinating with existing managers."""

    def __init__(self, progress_callback: Optional[Callable] = None):
        """
        Initialize coordinator.
        
        Args:
            progress_callback: Function to call with (step, percent) updates
        """
        self.progress_callback = progress_callback
        self.is_cancelled = False
        
        # Queue management
        self.queue = []
        self.current_download = None
        self.is_downloading = False
        self.download_history = []
        
        # Queue persistence path
        self.queue_file = Path.home() / ".mises_data_curator" / "queue.json"
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize with project config
        try:
            config = Config()
        except Exception:
            # Fallback if config loading fails
            config = None
        
        try:
            self.ingestion_manager = DataIngestionManager(config=config) if config else None
        except Exception:
            self.ingestion_manager = None
        
        try:
            self.cleaner = DataCleaner(config=config) if config else None
        except Exception:
            self.cleaner = None
        
        try:
            self.metadata_gen = MetadataGenerator(config=config) if config else None
        except Exception:
            self.metadata_gen = None
        
        # Load queue from persistent storage
        self._load_queue()

    def download_indicator(
        self,
        source: str,
        indicator_id: str,
        topic: str,
        coverage: str,
        countries: Optional[List[str]] = None,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> Dict:
        """
        Download and process an indicator through the full pipeline.
        
        Args:
            source: Data source (oecd, ilostat, imf, etc.)
            indicator_id: Indicator code/ID
            topic: Topic name (salarios_reales, etc.)
            coverage: Geographic coverage (latam, global, etc.)
            countries: List of country codes to filter
            start_year: Start year for data
            end_year: End year for data
            
        Returns:
            Dict with status and output file path
        """
        try:
            # Step 1: Ingest (Download)
            self._update_progress("ingest", 0)
            raw_data = self.ingestion_manager.ingest(
                source=source,
                indicator=indicator_id,
                countries=countries,
                start_year=start_year,
                end_year=end_year,
            )
            self._update_progress("ingest", 100)

            if self.is_cancelled:
                return {"success": False, "error": "Download cancelled by user"}

            # Step 2: Clean (Transform)
            self._update_progress("clean", 0)
            cleaned_data = self.cleaner.clean(
                data=raw_data,
                topic=topic,
                source=source,
                coverage=coverage,
            )
            self._update_progress("clean", 100)

            if self.is_cancelled:
                return {"success": False, "error": "Cleaning cancelled by user"}

            # Step 3: Document (Metadata)
            self._update_progress("document", 0)
            metadata = self.metadata_gen.generate(
                data=cleaned_data,
                topic=topic,
                source=source,
                coverage=coverage,
            )
            self._update_progress("document", 100)

            return {
                "success": True,
                "topic": topic,
                "source": source,
                "coverage": coverage,
                "rows": len(cleaned_data),
                "metadata_file": metadata.get("file"),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    # Queue Management Methods
    def add_to_queue(self, download_spec: Dict) -> bool:
        """
        Add a download to the queue.
        
        Args:
            download_spec: Dict with source, indicator, topic, coverage, etc.
            
        Returns:
            True if added successfully
        """
        try:
            item = {
                "id": len(self.queue) + len(self.download_history),
                "timestamp": datetime.now().isoformat(),
                "status": "queued",
                **download_spec,
            }
            self.queue.append(item)
            self._save_queue()
            return True
        except Exception as e:
            print(f"Error adding to queue: {e}")
            return False

    def remove_from_queue(self, index: int) -> bool:
        """Remove an item from the queue."""
        try:
            if 0 <= index < len(self.queue):
                self.queue.pop(index)
                self._save_queue()
                return True
            return False
        except Exception as e:
            print(f"Error removing from queue: {e}")
            return False

    def clear_queue(self) -> None:
        """Clear all items from the queue."""
        self.queue.clear()
        self._save_queue()

    def get_queue(self) -> List[Dict]:
        """Get current queue."""
        return self.queue.copy()

    def get_queue_size(self) -> int:
        """Get number of items in queue."""
        return len(self.queue)

    def start_queue(self, on_complete: Optional[Callable] = None) -> None:
        """
        Start processing the download queue.
        
        Args:
            on_complete: Callback when entire queue is done
        """
        if self.is_downloading or not self.queue:
            return
        
        # Run in a separate thread to avoid blocking UI
        thread = threading.Thread(
            target=self._process_queue,
            args=(on_complete,),
            daemon=True,
        )
        thread.start()

    def _process_queue(self, on_complete: Optional[Callable] = None) -> None:
        """Process all items in the queue."""
        self.is_downloading = True
        
        while self.queue and not self.is_cancelled:
            # Get next item
            item = self.queue[0]
            self.current_download = item
            
            # Download
            result = self.download_indicator(
                source=item["source"],
                indicator_id=item["indicator"],
                topic=item["topic"],
                coverage=item["coverage"],
                countries=item.get("countries"),
                start_year=item.get("start_year"),
                end_year=item.get("end_year"),
            )
            
            # Record result
            item["status"] = "success" if result["success"] else "failed"
            item["result"] = result
            item["completed_at"] = datetime.now().isoformat()
            
            # Move to history
            self.download_history.append(item)
            self.queue.pop(0)
            self._save_queue()
        
        self.is_downloading = False
        self.current_download = None
        
        if on_complete:
            on_complete()

    def _load_queue(self) -> None:
        """Load queue from persistent storage."""
        try:
            if self.queue_file.exists():
                with open(self.queue_file, "r") as f:
                    data = json.load(f)
                    self.queue = data.get("queue", [])
                    self.download_history = data.get("history", [])
        except Exception as e:
            print(f"Error loading queue: {e}")

    def _save_queue(self) -> None:
        """Save queue to persistent storage."""
        try:
            data = {
                "queue": self.queue,
                "history": self.download_history[-100:],  # Keep last 100
            }
            with open(self.queue_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving queue: {e}")

    def get_history(self, limit: int = 20) -> List[Dict]:
        """Get recent download history."""
        return self.download_history[-limit:]

    def _update_progress(self, step: str, percent: int) -> None:
        """Call progress callback if registered."""
        if self.progress_callback:
            self.progress_callback(step=step, percent=percent)

    def cancel(self) -> None:
        """Cancel ongoing download."""
        self.is_cancelled = True
