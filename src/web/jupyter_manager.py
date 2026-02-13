"""Lifecycle manager for embedded Jupyter Server."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import shutil

from src.logger import get_logger

logger = get_logger(__name__)


class JupyterManager:
    """Manage Jupyter Server process lifecycle for Flask embedding."""

    def __init__(
        self,
        port: int = 8888,
        notebook_dir: str = "./notebooks",
        config_dir: str = "./jupyter_config",
        template_seed_dir: Optional[str] = None,
        db_path: str = "./datasets_catalog.db",
        flask_port: int = 5000,
        enabled: bool = False,
        app_prefix: str = "",
    ) -> None:
        self.port = int(port)
        self.notebook_dir = str(Path(notebook_dir).absolute())
        self.config_dir = str(Path(config_dir).absolute())
        self.template_seed_dir = (
            str(Path(template_seed_dir).absolute()) if template_seed_dir else str((Path(self.config_dir) / "notebook_templates").absolute())
        )
        self.db_path = str(Path(db_path).absolute())
        self.flask_port = int(flask_port)
        self.enabled = bool(enabled)
        # app_prefix is the Flask app's SCRIPT_NAME (e.g., "/misesdata")
        # Jupyter's base_url must include this prefix so generated URLs work behind nginx
        self.app_prefix = app_prefix.rstrip("/") if app_prefix else ""
        self.process: Optional[subprocess.Popen[str]] = None
        self._started_at: Optional[datetime] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._should_run = False
        self._lock = threading.Lock()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def jupyter_base_path(self) -> str:
        """Return Jupyter's base_url path including app prefix (e.g., '/misesdata/jupyter/')."""
        return f"{self.app_prefix}/jupyter/" if self.app_prefix else "/jupyter/"

    @property
    def jupyter_internal_path(self) -> str:
        """Return Jupyter's internal base_url path without app prefix (always '/jupyter/')."""
        return "/jupyter/"

    def _wait_for_ready(self, timeout: int = 30) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            if self.process and self.process.poll() is not None:
                return False
            try:
                with urllib.request.urlopen(f"{self.base_url}{self.jupyter_base_path}api", timeout=2) as response:
                    if response.status == 200:
                        return True
            except (urllib.error.URLError, TimeoutError, OSError, ValueError):
                time.sleep(0.5)
        return False

    def ensure_notebook_dirs(self) -> None:
        """Ensure notebook and config directories exist."""
        Path(self.notebook_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)
        if self.template_seed_dir:
            Path(self.template_seed_dir).mkdir(parents=True, exist_ok=True)

    def _build_command(self) -> list[str]:
        """Build the Jupyter Server command with proper base_url."""
        return [
            sys.executable,
            "-m",
            "jupyter_server",
            f"--ServerApp.port={self.port}",
            f"--ServerApp.base_url={self.jupyter_base_path}",
            f"--ServerApp.root_dir={self.notebook_dir}",
            "--ServerApp.token=",
            "--ServerApp.password=",
            "--ServerApp.open_browser=False",
            "--ServerApp.allow_origin=*",
            "--ServerApp.disable_check_xsrf=True",
        ]

    def _build_env(self) -> dict[str, str]:
        """Build environment variables for Jupyter process."""
        env = os.environ.copy()
        env["JUPYTER_CONFIG_DIR"] = self.config_dir
        if self.template_seed_dir:
            env["JUPYTER_TEMPLATE_SEED_DIR"] = self.template_seed_dir
        if self.db_path:
            env["DATASETS_CATALOG_DB"] = self.db_path
        return env

    def _launch_process(self) -> None:
        self.ensure_notebook_dirs()
        command = self._build_command()
        self.process = subprocess.Popen(
            command,
            env=self._build_env(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        self._started_at = datetime.now(timezone.utc)

    def _monitor_loop(self) -> None:
        while self._should_run:
            if self.process and self.process.poll() is not None and self.enabled:
                logger.warning("Jupyter process exited unexpectedly; attempting restart")
                try:
                    self._launch_process()
                    self._wait_for_ready()
                except (OSError, ValueError, RuntimeError) as exc:
                    logger.error("Jupyter restart failed: %s", exc)
            time.sleep(5)

    def start(self) -> bool:
        if not self.enabled:
            return False
        with self._lock:
            if self.is_alive():
                return True
            self._should_run = True
            try:
                self._launch_process()
                ready = self._wait_for_ready()
                if ready and (not self._monitor_thread or not self._monitor_thread.is_alive()):
                    self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
                    self._monitor_thread.start()
                return ready
            except (OSError, ValueError, RuntimeError) as exc:
                logger.error("Error starting Jupyter: %s", exc)
                return False

    def stop(self) -> None:
        with self._lock:
            self._should_run = False
            if not self.process:
                return
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            self.process = None

    def restart(self) -> bool:
        self.stop()
        return self.start()

    def is_alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def health_check(self) -> Dict[str, Any]:
        if not self.enabled:
            return {"status": "disabled", "enabled": False, "port": self.port}
        if not self.is_alive():
            return {"status": "down", "enabled": True, "port": self.port}
        try:
            with urllib.request.urlopen(f"{self.base_url}{self.jupyter_base_path}api", timeout=3) as response:
                if response.status == 200:
                    uptime = None
                    if self._started_at:
                        uptime = max(0, int((datetime.now(timezone.utc) - self._started_at).total_seconds()))
                    return {
                        "status": "ok",
                        "enabled": True,
                        "port": self.port,
                        "pid": self.process.pid if self.process else None,
                        "uptime_seconds": uptime,
                    }
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            return {
                "status": "down",
                "enabled": True,
                "port": self.port,
                "pid": self.process.pid if self.process else None,
                "error": str(exc),
            }
        return {"status": "down", "enabled": True, "port": self.port}

    def provision_templates(self) -> int:
        """Copy template notebooks to user directory. Returns count of files copied."""
        if not self.notebook_dir:
            return 0
        templates_dir = Path(self.notebook_dir) / "templates"
        user_dir = Path(self.notebook_dir) / "user"

        templates_dir.mkdir(parents=True, exist_ok=True)
        user_dir.mkdir(parents=True, exist_ok=True)

        copied = 0
        for template in templates_dir.glob("*.ipynb"):
            dest = user_dir / template.name
            if not dest.exists():
                shutil.copy2(template, dest)
                copied += 1
        return copied