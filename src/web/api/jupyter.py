"""Jupyter integration API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import shutil
from pathlib import Path

from flask import jsonify, request, current_app
from flask_login import login_required

from . import api_bp


def _manager():
    return current_app.extensions.get("jupyter_manager")


def _notebook_root() -> Path:
    manager = _manager()
    if manager and getattr(manager, "notebook_dir", None):
        return Path(manager.notebook_dir)
    return Path(current_app.root_path).parent.parent / "notebooks"


@api_bp.route("/jupyter/health", methods=["GET"])
@login_required
def jupyter_health():
    manager = _manager()
    if not manager:
        return jsonify({"status": "disabled", "enabled": False, "message": "Jupyter manager not configured"})
    return jsonify(manager.health_check())


@api_bp.route("/notebooks", methods=["GET"])
@login_required
def list_notebooks():
    root = _notebook_root()
    root.mkdir(parents=True, exist_ok=True)
    notebooks = []
    for nb in sorted(root.rglob("*.ipynb")):
        if ".ipynb_checkpoints" in str(nb):
            continue
        rel = nb.relative_to(root)
        stat = nb.stat()
        notebooks.append(
            {
                "name": nb.stem,
                "path": str(rel),
                "directory": str(rel.parent),
                "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "size_kb": round(stat.st_size / 1024, 2),
            }
        )
    return jsonify({"status": "success", "notebooks": notebooks})


@api_bp.route("/notebooks/create", methods=["POST"])
@login_required
def create_notebook():
    payload = request.get_json(silent=True) or {}
    template_name = str(payload.get("template") or "").strip()
    custom_name = str(payload.get("name") or "").strip()

    root = _notebook_root()
    user_dir = root / "user"
    templates_dir = root / "templates"
    user_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    if template_name:
        src = templates_dir / template_name
        if not src.exists():
            return jsonify({"status": "error", "message": "Template not found"}), 404
        dest_name = custom_name or f"{src.stem}_{timestamp}.ipynb"
        dest = user_dir / dest_name
        shutil.copy2(src, dest)
    else:
        dest_name = custom_name or f"notebook_{timestamp}.ipynb"
        if not dest_name.endswith(".ipynb"):
            dest_name = f"{dest_name}.ipynb"
        dest = user_dir / dest_name
        empty_notebook = {
            "cells": [],
            "metadata": {
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {"name": "python"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        }
        with dest.open("w", encoding="utf-8") as fh:
            json.dump(empty_notebook, fh, indent=2)

    return jsonify({"status": "success", "path": f"user/{dest_name}", "name": dest_name, "created": True})


@api_bp.route("/notebooks/provision", methods=["POST"])
@login_required
def provision_notebooks():
    manager = _manager()
    if manager:
        copied = manager.provision_templates()
        templates_dir = Path(manager.notebook_dir) / "templates"
        user_dir = Path(manager.notebook_dir) / "user"
    else:
        root = _notebook_root()
        templates_dir = root / "templates"
        user_dir = root / "user"
        templates_dir.mkdir(parents=True, exist_ok=True)
        user_dir.mkdir(parents=True, exist_ok=True)
        copied = 0
    return jsonify(
        {
            "status": "success",
            "templates_dir": str(templates_dir),
            "user_dir": str(user_dir),
            "copied_templates": copied,
        }
    )


@api_bp.route("/notebooks/data-path", methods=["GET"])
@login_required
def notebooks_data_path():
    manager = _manager()
    db_path = getattr(manager, "db_path", None)
    csv_dir = None
    if db_path:
        csv_dir = str((Path(db_path).parent / "csv").absolute())
    return jsonify({"status": "success", "db_path": db_path, "csv_dir": csv_dir})
