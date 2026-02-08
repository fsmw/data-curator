# Multi-User Data Model Design

## Overview

Instead of physical workspace directories, we'll use a relational database model where:
- **Datasets are shared** but have ownership and permissions
- **Users have logical workspaces** through relationships
- **Sessions, analyses, and visualizations** are user-scoped in the database
- **Filesystem remains simple** - all data in shared directories with user_id metadata

## Database Schema

### Core Tables

```sql
-- Users (existing)
users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120),
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

-- Roles (existing)
roles (
    id INTEGER PRIMARY KEY,
    name VARCHAR(80) UNIQUE NOT NULL,
    description VARCHAR(255)
)

-- User-Roles association (existing)
user_roles (
    user_id INTEGER REFERENCES users(id),
    role_id INTEGER REFERENCES roles(id),
    PRIMARY KEY (user_id, role_id)
)

-- Datasets (enhanced)
datasets (
    id INTEGER PRIMARY KEY,
    file_path VARCHAR(500) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    source VARCHAR(100) NOT NULL,
    indicator_id VARCHAR(100),
    indicator_name VARCHAR(255) NOT NULL,
    description TEXT,
    topic VARCHAR(100),
    
    -- Owner of the dataset
    owner_id INTEGER REFERENCES users(id),
    
    -- Sharing settings
    is_public BOOLEAN DEFAULT FALSE,
    is_shared BOOLEAN DEFAULT FALSE,
    
    file_size_bytes INTEGER,
    file_hash VARCHAR(64),
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
    is_edited INTEGER DEFAULT 0,
    
    UNIQUE(file_path)
)

-- User-Dataset Access (many-to-many with permissions)
user_dataset_access (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    dataset_id INTEGER REFERENCES datasets(id) NOT NULL,
    access_level VARCHAR(20) DEFAULT 'read', -- 'read', 'write', 'admin'
    granted_by INTEGER REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    UNIQUE(user_id, dataset_id)
)

-- Dataset Columns (existing, add dataset_id FK)
dataset_columns (
    id INTEGER PRIMARY KEY,
    dataset_id INTEGER REFERENCES datasets(id) ON DELETE CASCADE,
    column_name VARCHAR(255) NOT NULL,
    column_type VARCHAR(50),
    sample_values_json TEXT,
    unique_count INTEGER,
    null_count INTEGER
)

-- User Workspaces (logical workspace configuration)
user_workspaces (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) UNIQUE NOT NULL,
    name VARCHAR(100) DEFAULT 'My Workspace',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

-- Copilot Chat Sessions (user-scoped)
chat_sessions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    session_name VARCHAR(255),
    dataset_id INTEGER REFERENCES datasets(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
)

-- Chat Messages (user-scoped)
chat_messages (
    id INTEGER PRIMARY KEY,
    session_id INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    role VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    metadata_json TEXT, -- For charts, code, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

-- Saved Analyses (user-scoped)
saved_analyses (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    dataset_id INTEGER REFERENCES datasets(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    analysis_type VARCHAR(50), -- 'correlation', 'regression', 'summary', etc.
    parameters_json TEXT, -- Stored analysis parameters
    results_json TEXT, -- Cached results
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

-- Saved Visualizations (user-scoped)
saved_visualizations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    dataset_id INTEGER REFERENCES datasets(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    vega_spec_json TEXT, -- Vega-Lite specification
    chart_config_json TEXT, -- UI configuration
    is_shared BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

-- User Activity Log
user_activity_log (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    activity_type VARCHAR(50) NOT NULL, -- 'login', 'download', 'analysis', etc.
    dataset_id INTEGER REFERENCES datasets(id),
    details_json TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

-- Indicators (existing, shared)
indicators_config (
    id INTEGER PRIMARY KEY,
    indicator_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    source VARCHAR(50) NOT NULL,
    topic VARCHAR(100),
    tags TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## Key Relationships

```
User 1---* UserWorkspace (1 workspace per user)
User 1---* Dataset (owned datasets)
User *---* Dataset (accessible via UserDatasetAccess)
User 1---* ChatSession
User 1---* SavedAnalysis
User 1---* SavedVisualization
Dataset 1---* DatasetColumn
Dataset 1---* ChatSession
Dataset 1---* SavedAnalysis
Dataset 1---* SavedVisualization
```

## Permission Model

### Access Levels:
1. **Owner** (owner_id): Full control, can delete, share, modify
2. **Admin** (access_level='admin'): Can modify, share with others
3. **Write** (access_level='write'): Can modify data
4. **Read** (access_level='read'): View only

### Visibility:
- **Private** (is_public=FALSE, is_shared=FALSE): Only owner can access
- **Shared** (is_shared=TRUE): Specific users have access via user_dataset_access
- **Public** (is_public=TRUE): All users can read

## Implementation Strategy

### Phase 1: Enhance Dataset Model
1. Add owner_id, is_public, is_shared to Dataset model
2. Create UserDatasetAccess model for m2m relationship
3. Update DatasetCatalog to filter by user permissions

### Phase 2: User-Scoped Features
1. Create ChatSession and ChatMessage models
2. Create SavedAnalysis model
3. Create SavedVisualization model
4. Create UserWorkspace model (logical, not physical)

### Phase 3: Permission System
1. Add permission checks to all data access
2. Implement sharing mechanism
3. Add public dataset support

### Phase 4: Migration
1. Migrate existing datasets to have owner (admin)
2. Set up default user workspaces
3. Migrate existing chat history to new structure

## Code Example

```python
# Get datasets visible to user
def get_user_datasets(user_id: int, include_public: bool = True):
    """Get all datasets accessible by user."""
    query = Dataset.query.filter(
        or_(
            Dataset.owner_id == user_id,  # User owns it
            Dataset.is_public == True,      # It's public
            Dataset.id.in_(
                select(UserDatasetAccess.dataset_id)
                .where(UserDatasetAccess.user_id == user_id)
            )  # User has explicit access
        )
    )
    return query.all()

# Share dataset
def share_dataset(owner_id: int, dataset_id: int, user_id: int, access_level: str = 'read'):
    """Share dataset with another user."""
    dataset = Dataset.query.get(dataset_id)
    if dataset.owner_id != owner_id:
        raise PermissionError("Only owner can share")
    
    access = UserDatasetAccess(
        user_id=user_id,
        dataset_id=dataset_id,
        access_level=access_level,
        granted_by=owner_id
    )
    dataset.is_shared = True
    db.session.add(access)
    db.session.commit()

# Check permission
def can_access_dataset(user_id: int, dataset_id: int, min_access: str = 'read') -> bool:
    """Check if user can access dataset."""
    dataset = Dataset.query.get(dataset_id)
    if not dataset:
        return False
    
    # Owner has full access
    if dataset.owner_id == user_id:
        return True
    
    # Check if public
    if dataset.is_public and min_access == 'read':
        return True
    
    # Check explicit access
    access = UserDatasetAccess.query.filter_by(
        user_id=user_id, 
        dataset_id=dataset_id
    ).first()
    
    if not access:
        return False
    
    # Check access level hierarchy
    levels = {'read': 1, 'write': 2, 'admin': 3}
    return levels.get(access.access_level, 0) >= levels.get(min_access, 1)
```

## Advantages Over Physical Workspaces

1. **Data Sharing**: Easy to share datasets between users
2. **Storage Efficiency**: No duplication of shared datasets
3. **Permissions**: Fine-grained access control
4. **Backup**: Single database backup covers everything
5. **Search**: Full-text search across all accessible data
6. **Audit**: Complete activity logging
7. **Collaboration**: Multiple users can work on same dataset
8. **Simpler Filesystem**: All files in one place, metadata in DB

## Migration from Current System

1. Keep existing file structure (01_Raw_Data_Bank, etc.)
2. Add owner_id to existing datasets (set to admin user)
3. Create user workspaces for existing users
4. Migrate chat history to new schema with session concept

This approach maintains simplicity while adding powerful multi-user capabilities.
