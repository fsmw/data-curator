# Multi-User Workspace Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the monolithic single-user application into a multi-user system where each user has isolated workspaces for datasets, analyses, Copilot sessions, and visualizations.

**Architecture:** Implement user-scoped workspaces using a `UserWorkspace` service that prefixes all data paths with `workspaces/{user_id}/`. Each user gets: isolated directory structure (raw, clean, metadata, graphics), user-specific SQLite database, isolated RAG vector store, and private chat history.

**Tech Stack:** Flask-Login (current user context), SQLAlchemy (User model relations), Pathlib (dynamic path resolution), SQLite (user-scoped DBs), ChromaDB (user-scoped embeddings)

---

## Overview

Current state: Single global workspace at `DATA_ROOT/` with shared directories and single SQLite database.

Target state: Each user has isolated workspace at `DATA_ROOT/workspaces/{user_id}/` with:
- `01_Raw_Data_Bank/` - User's raw downloads
- `02_Datasets_Limpios/` - User's cleaned datasets
- `03_Metadata_y_Notas/` - User's metadata
- `04_Graficos_Asociados/` - User's visualizations
- `datasets_catalog.db` - User's private SQLite database
- `chroma_rag/` - User's private vector store
- `.chat_history/` - User's Copilot sessions

---

## Phase 1: Core Workspace Infrastructure

### Task 1: Create UserWorkspace Service

**Files:**
- Create: `src/workspace.py`

**Step 1: Design the Workspace Service**

```python
"""User-scoped workspace management service."""

from pathlib import Path
from typing import Optional, Dict, Any
from flask_login import current_user


class UserWorkspace:
    """Manages user-scoped workspace directories and resources."""
    
    def __init__(self, user_id: int, base_data_root: Path):
        self.user_id = user_id
        self.base_root = base_data_root
        self.workspace_root = base_data_root / "workspaces" / str(user_id)
        
    @property
    def raw_dir(self) -> Path:
        return self.workspace_root / "01_Raw_Data_Bank"
    
    @property
    def clean_dir(self) -> Path:
        return self.workspace_root / "02_Datasets_Limpios"
    
    @property
    def metadata_dir(self) -> Path:
        return self.workspace_root / "03_Metadata_y_Notas"
    
    @property
    def graphics_dir(self) -> Path:
        return self.workspace_root / "04_Graficos_Asociados"
    
    @property
    def db_path(self) -> Path:
        return self.workspace_root / "datasets_catalog.db"
    
    @property
    def chroma_dir(self) -> Path:
        return self.workspace_root / "chroma_rag"
    
    @property
    def chat_history_dir(self) -> Path:
        return self.workspace_root / ".chat_history"
    
    def ensure_directories(self) -> None:
        """Create all workspace directories if they don't exist."""
        for dir_path in [self.raw_dir, self.clean_dir, self.metadata_dir, 
                        self.graphics_dir, self.chroma_dir, self.chat_history_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def to_config_dict(self) -> Dict[str, Any]:
        """Return workspace paths as config-compatible dict."""
        return {
            'data_root': self.workspace_root,
            'directories': {
                'raw': str(self.raw_dir),
                'clean': str(self.clean_dir),
                'metadata': str(self.metadata_dir),
                'graphics': str(self.graphics_dir),
            },
            'db_path': str(self.db_path),
            'chroma_dir': str(self.chroma_dir),
            'chat_history_dir': str(self.chat_history_dir),
        }


def get_current_user_workspace() -> Optional[UserWorkspace]:
    """Get workspace for current logged-in user."""
    if not current_user or not current_user.is_authenticated:
        return None
    
    from src.config import Config
    config = Config()
    workspace = UserWorkspace(current_user.id, config.data_root)
    workspace.ensure_directories()
    return workspace
```

**Step 2: Verify syntax**

Run: `python -c "from src.workspace import UserWorkspace, get_current_user_workspace; print('OK')"`
Expected: OK

**Step 3: Commit**

```bash
git add src/workspace.py
git commit -m "feat: add UserWorkspace service for multi-user support

- Create UserWorkspace class to manage user-scoped directories
- Properties for raw, clean, metadata, graphics directories
- User-specific database and vector store paths
- Helper function get_current_user_workspace() integrated with Flask-Login"
```

---

### Task 2: Modify Config Class for User Context

**Files:**
- Modify: `src/config.py`

**Step 1: Add User-Aware Configuration**

Add to Config class:

```python
    def get_user_config(self, user_id: int = None) -> 'UserConfig':
        """Get user-scoped configuration.
        
        If user_id is None and user is logged in, uses current user.
        """
        if user_id is None:
            from flask_login import current_user
            if current_user and current_user.is_authenticated:
                user_id = current_user.id
            else:
                raise ValueError("No user_id provided and no user logged in")
        
        from src.workspace import UserWorkspace
        workspace = UserWorkspace(user_id, self.data_root)
        workspace.ensure_directories()
        
        return UserConfig(self, workspace)


class UserConfig:
    """User-scoped configuration wrapper."""
    
    def __init__(self, base_config: Config, workspace: 'UserWorkspace'):
        self._base = base_config
        self.workspace = workspace
        
    @property
    def data_root(self) -> Path:
        return self.workspace.workspace_root
        
    def get_directory(self, dir_type: str) -> Path:
        """Get user-scoped directory."""
        dir_map = {
            'raw': self.workspace.raw_dir,
            'clean': self.workspace.clean_dir,
            'metadata': self.workspace.metadata_dir,
            'graphics': self.workspace.graphics_dir,
        }
        if dir_type in dir_map:
            return dir_map[dir_type]
        # Fallback to base config
        return self._base.get_directory(dir_type)
    
    def get_rag_config(self) -> Dict[str, Any]:
        """Get user-scoped RAG configuration."""
        base_rag = self._base.get_rag_config()
        base_rag['chroma_persist_dir'] = self.workspace.chroma_dir
        return base_rag
    
    def get_llm_config(self) -> Dict[str, Any]:
        """LLM config is shared across users."""
        return self._base.get_llm_config()
    
    def get_indicators(self) -> List[Dict[str, Any]]:
        """Indicators are shared across users."""
        return self._base.get_indicators()
    
    def get_regions(self) -> Dict[str, List[str]]:
        """Regions are shared across users."""
        return self._base.get_regions()
```

**Step 2: Update imports**

Add to config.py imports:
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.workspace import UserWorkspace
```

**Step 3: Test**

Run: `python -c "from src.config import Config; c = Config(); print('Config OK')"`
Expected: Config OK

**Step 4: Commit**

```bash
git add src/config.py
git commit -m "feat: add UserConfig for user-scoped configuration

- Add get_user_config() method to Config class
- Create UserConfig wrapper class
- UserConfig provides user-scoped directories and RAG config
- Shared resources (indicators, LLM) fall back to base config"
```

---

### Task 3: Update DatasetCatalog for User Scope

**Files:**
- Modify: `src/dataset_catalog.py`

**Step 1: Add User ID Support**

Modify DatasetCatalog.__init__:

```python
    def __init__(self, config: Config, user_id: int = None):
        """Initialize catalog for specific user or global.
        
        Args:
            config: Config or UserConfig instance
            user_id: Optional user ID (uses current user if None)
        """
        self.config = config
        
        # Determine database path based on user
        if user_id is None and hasattr(config, 'workspace'):
            # Using UserConfig - get path from workspace
            self.db_path = config.workspace.db_path
            self.datasets_dir = config.get_directory('clean')
        else:
            # Legacy global mode
            self.db_path = config.data_root / "datasets_catalog.db"
            self.datasets_dir = config.get_directory('clean')
        
        # Initialize database
        self._init_database()
```

**Step 2: Add user_id column to schema**

Update _init_database to include user_id:

```python
        # Check if user_id column exists
        try:
            cursor.execute("SELECT user_id FROM datasets LIMIT 1")
        except sqlite3.OperationalError:
            # Add user_id column for migration
            try:
                cursor.execute("ALTER TABLE datasets ADD COLUMN user_id INTEGER DEFAULT NULL")
            except sqlite3.OperationalError:
                pass
```

**Step 3: Update methods to filter by user**

Modify query methods to accept user_id parameter:

```python
    def get_datasets(self, user_id: int = None, **filters) -> List[Dict[str, Any]]:
        """Get datasets filtered by user and other criteria."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        query = "SELECT * FROM datasets WHERE 1=1"
        params = []
        
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)
        
        # Apply other filters...
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
```

**Step 4: Commit**

```bash
git add src/dataset_catalog.py
git commit -m "feat: add user_id support to DatasetCatalog

- Modify __init__ to accept user_id parameter
- Support both UserConfig and legacy Config modes
- Add user_id column to schema
- Filter queries by user_id"
```

---

## Phase 2: Update Web Layer

### Task 4: Create Workspace-Aware Decorator

**Files:**
- Create: `src/web/decorators.py`

**Step 1: Create Decorator**

```python
"""Custom decorators for workspace management."""

from functools import wraps
from flask import g, redirect, url_for, flash
from flask_login import current_user


def with_user_workspace(f):
    """Decorator that injects user workspace into request context."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        # Initialize workspace for current user
        from src.config import Config
        from src.workspace import UserWorkspace
        
        config = Config()
        g.user_workspace = UserWorkspace(current_user.id, config.data_root)
        g.user_workspace.ensure_directories()
        
        # Create user config and attach to g
        g.user_config = config.get_user_config(current_user.id)
        
        return f(*args, **kwargs)
    return decorated_function
```

**Step 2: Commit**

```bash
git add src/web/decorators.py
git commit -m "feat: add with_user_workspace decorator

- Inject user workspace into Flask g context
- Ensure directories exist on each request
- Attach user_config to g for easy access"
```

---

### Task 5: Update All Routes to Use User Workspace

**Files:**
- Modify: `src/web/routes.py`

**Step 1: Apply Decorator to Routes**

Add import:
```python
from src.web.decorators import with_user_workspace
```

Apply to status route as example:

```python
@ui_bp.route("/")
@ui_bp.route("/status")
@login_required
@with_user_workspace
def status() -> str:
    """Render the status/home page with user workspace."""
    from flask import g
    
    # Use user config instead of global config
    user_config = g.user_config
    catalog = DatasetCatalog(user_config)
    
    # Rest of function uses catalog...
```

**Step 2: Update All Route Handlers**

Repeat for all routes:
- Add `@with_user_workspace` decorator after `@login_required`
- Replace `Config()` with `g.user_config`
- Replace `DatasetCatalog(config)` with `DatasetCatalog(g.user_config)`

**Step 3: Commit**

```bash
git add src/web/routes.py
git commit -m "feat: update all routes to use user workspaces

- Add with_user_workspace decorator to all routes
- Replace global Config with g.user_config
- Update DatasetCatalog initialization"
```

---

## Phase 3: Database Schema Migration

### Task 6: Create Migration Script

**Files:**
- Create: `scripts/migrate_to_multiuser.py`

**Step 1: Design Migration**

```python
#!/usr/bin/env python3
"""Migrate from single-user to multi-user workspace structure."""

import sys
from pathlib import Path
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.workspace import UserWorkspace
from src.models import db, User, Role


def migrate_to_multiuser():
    """Migrate existing data to multi-user workspace structure."""
    print("Starting migration to multi-user workspaces...")
    
    config = Config()
    
    # Get or create default admin user
    from src.web import create_app
    app = create_app()
    
    with app.app_context():
        # Ensure tables exist
        db.create_all()
        
        # Check for existing users
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            print("Creating default admin user...")
            admin_role = Role.query.filter_by(name='admin').first()
            if not admin_role:
                admin_role = Role(name='admin', description='Administrator')
                db.session.add(admin_role)
            
            admin_user = User(username='admin', email='admin@example.com')
            admin_user.set_password('admin123')
            admin_user.roles.append(admin_role)
            db.session.add(admin_user)
            db.session.commit()
            print("✓ Created admin user")
        
        # Migrate existing data to admin's workspace
        print(f"\nMigrating data to user {admin_user.id} workspace...")
        
        workspace = UserWorkspace(admin_user.id, config.data_root)
        workspace.ensure_directories()
        
        # Copy existing directories
        dirs_to_migrate = ['01_Raw_Data_Bank', '02_Datasets_Limpios', 
                          '03_Metadata_y_Notas', '04_Graficos_Asociados']
        
        for dir_name in dirs_to_migrate:
            src = config.data_root / dir_name
            if src.exists():
                dst = workspace.workspace_root / dir_name
                if not dst.exists():
                    print(f"  Copying {dir_name}...")
                    shutil.copytree(src, dst)
                    print(f"  ✓ Migrated {dir_name}")
        
        # Migrate database
        old_db = config.data_root / "datasets_catalog.db"
        if old_db.exists():
            print("\n  Migrating database...")
            import sqlite3
            
            # Copy and update database
            new_db = workspace.db_path
            shutil.copy2(old_db, new_db)
            
            # Add user_id column and set all to admin
            conn = sqlite3.connect(new_db)
            cursor = conn.cursor()
            
            try:
                cursor.execute("ALTER TABLE datasets ADD COLUMN user_id INTEGER DEFAULT ?", 
                             (admin_user.id,))
            except sqlite3.OperationalError:
                # Column might already exist
                cursor.execute("UPDATE datasets SET user_id = ? WHERE user_id IS NULL",
                             (admin_user.id,))
            
            conn.commit()
            conn.close()
            print(f"  ✓ Migrated database")
        
        print("\n✓ Migration complete!")
        print(f"\nAdmin user: admin / admin123")
        print(f"Workspace: {workspace.workspace_root}")


if __name__ == '__main__':
    migrate_to_multiuser()
```

**Step 2: Commit**

```bash
git add scripts/migrate_to_multiuser.py
chmod +x scripts/migrate_to_multiuser.py
git add scripts/migrate_to_multiuser.py
git commit -m "feat: add migration script for multi-user workspaces

- Migrate existing single-user data to admin workspace
- Copy all directories (raw, clean, metadata, graphics)
- Migrate database with user_id column
- Create default admin user if doesn't exist"
```

---

## Phase 4: API Layer Updates

### Task 6: Update API Blueprints

**Files:**
- Modify: `src/web/api/*.py` files

**Step 1: Update API Routes**

For each API file, update to use user workspace:

```python
# In each API endpoint
from flask import g
from flask_login import login_required, current_user
from src.web.decorators import with_user_workspace

@api_bp.route('/datasets')
@login_required
@with_user_workspace
def get_datasets():
    """Get datasets for current user."""
    user_config = g.user_config
    catalog = DatasetCatalog(user_config)
    
    datasets = catalog.get_datasets(user_id=current_user.id)
    return jsonify(datasets)
```

**Step 2: Commit**

```bash
git add src/web/api/
git commit -m "feat: update API layer for user-scoped access

- Add with_user_workspace decorator to API routes
- Filter datasets by current_user.id
- Use g.user_config for workspace isolation"
```

---

## Phase 5: Testing & Validation

### Task 7: Create Test Suite

**Files:**
- Create: `tests/test_multiuser.py`

**Step 1: Write Tests**

```python
"""Tests for multi-user workspace functionality."""

import pytest
from pathlib import Path
from src.workspace import UserWorkspace
from src.config import Config, UserConfig


def test_user_workspace_creation(tmp_path):
    """Test workspace directory creation."""
    workspace = UserWorkspace(1, tmp_path)
    workspace.ensure_directories()
    
    assert workspace.raw_dir.exists()
    assert workspace.clean_dir.exists()
    assert workspace.metadata_dir.exists()
    assert workspace.graphics_dir.exists()
    assert workspace.chroma_dir.exists()


def test_user_config_directories(app, tmp_path):
    """Test UserConfig returns correct directories."""
    with app.app_context():
        # Create test user
        from src.models import User, db
        user = User(username='testuser', email='test@test.com')
        user.set_password('test123')
        db.session.add(user)
        db.session.commit()
        
        config = Config()
        user_config = config.get_user_config(user.id)
        
        # Check directories are user-scoped
        assert str(user_id) in str(user_config.get_directory('clean'))
        assert str(user_id) in str(user_config.get_directory('raw'))


def test_dataset_isolation(app, tmp_path):
    """Test datasets are isolated per user."""
    with app.app_context():
        from src.models import User, db
        from src.dataset_catalog import DatasetCatalog
        
        # Create two users
        user1 = User(username='user1', email='u1@test.com')
        user1.set_password('test')
        user2 = User(username='user2', email='u2@test.com')
        user2.set_password('test')
        db.session.add_all([user1, user2])
        db.session.commit()
        
        # Add dataset for user1
        config = Config()
        catalog1 = DatasetCatalog(config.get_user_config(user1.id))
        # ... add test dataset
        
        # Verify user2 can't see user1's dataset
        catalog2 = DatasetCatalog(config.get_user_config(user2.id))
        datasets = catalog2.get_datasets(user_id=user2.id)
        assert len(datasets) == 0
```

**Step 2: Commit**

```bash
git add tests/test_multiuser.py
git commit -m "test: add multi-user workspace tests

- Test workspace directory creation
- Test UserConfig directory isolation
- Test dataset isolation between users"
```

---

## Summary

### Changes Made:

**Core Infrastructure:**
1. `src/workspace.py` - UserWorkspace service
2. `src/config.py` - UserConfig with user-scoped paths
3. `src/dataset_catalog.py` - User ID filtering
4. `src/web/decorators.py` - with_user_workspace decorator

**Web Layer:**
5. `src/web/routes.py` - All routes use user workspace
6. `src/web/api/*.py` - API routes filter by user

**Migration:**
7. `scripts/migrate_to_multiuser.py` - Data migration script

**Testing:**
8. `tests/test_multiuser.py` - Test suite

### Usage:

```bash
# Fresh install
python scripts/init_admin.py
python scripts/create_admin_user.py
python -m src.web

# Migrate existing data
python scripts/migrate_to_multiuser.py
python -m src.web
```

### Each User Gets:
- Isolated directory: `workspaces/{user_id}/`
- Private database: `workspaces/{user_id}/datasets_catalog.db`
- Private RAG: `workspaces/{user_id}/chroma_rag/`
- Private chat history
- Private datasets, visualizations, metadata

**Architecture:** Clean separation via UserWorkspace service with Flask g context injection.
