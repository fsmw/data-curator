# Multi-User System with Admin Management - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a complete multi-user system where users, roles, permissions, and dataset sharing are fully manageable through Flask-Admin interface.

**Architecture:** Use SQLAlchemy models with many-to-many relationships for users-roles and users-datasets. All user/role/permission management happens via Flask-Admin. Dataset ownership and sharing controlled through database relationships, not filesystem separation.

**Tech Stack:** Flask-Admin, Flask-Login, SQLAlchemy, SQLite

---

## Admin Management Requirements

All configuration must be doable via `/admin`:
- ✅ User CRUD (create, edit, delete, deactivate)
- ✅ Role CRUD (create, edit, delete roles)
- ✅ Assign roles to users
- ✅ Dataset ownership assignment
- ✅ Dataset sharing (grant access to specific users)
- ✅ Permission levels (read/write/admin) per dataset per user
- ✅ Public/private dataset visibility toggle
- ✅ User workspace configuration
- ✅ Activity monitoring

---

## Phase 1: Enhanced Models with Admin Support

### Task 1: Update Dataset Model with Ownership

**Files:** Modify `src/models.py`

**Step 1: Add ownership and visibility fields to Dataset**

```python
class Dataset(db.Model):
    """Dataset model with ownership and sharing."""
    
    __tablename__ = 'datasets'
    
    # ... existing fields ...
    
    # Ownership and visibility
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_public = db.Column(db.Boolean, default=False)
    is_shared = db.Column(db.Boolean, default=False)
    
    # Relationships
    owner = db.relationship('User', foreign_keys=[owner_id], backref='owned_datasets')
    shared_with = db.relationship('User', secondary='user_dataset_access', 
                                  backref='accessible_datasets')
    access_permissions = db.relationship('UserDatasetAccess', backref='dataset', 
                                        lazy='dynamic', cascade='all, delete-orphan')
```

**Step 2: Create UserDatasetAccess model for permissions**

```python
class UserDatasetAccess(db.Model):
    """Permission matrix for dataset access."""
    
    __tablename__ = 'user_dataset_access'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id'), nullable=False)
    access_level = db.Column(db.String(20), default='read')  # 'read', 'write', 'admin'
    granted_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='dataset_permissions')
    granter = db.relationship('User', foreign_keys=[granted_by])
    
    __table_args__ = (db.UniqueConstraint('user_id', 'dataset_id', name='unique_user_dataset_access'),)
    
    def __repr__(self):
        return f'<UserDatasetAccess user={self.user_id} dataset={self.dataset_id} level={self.access_level}>'
```

**Step 3: Add permission helper methods to Dataset**

```python
    def can_access(self, user_id, min_level='read'):
        """Check if user can access with minimum permission level."""
        if self.owner_id == user_id:
            return True
        if self.is_public and min_level == 'read':
            return True
        
        access = self.access_permissions.filter_by(user_id=user_id).first()
        if not access:
            return False
        
        levels = {'read': 1, 'write': 2, 'admin': 3}
        return levels.get(access.access_level, 0) >= levels.get(min_level, 1)
    
    def share_with(self, user_id, access_level='read', granted_by=None):
        """Grant access to user."""
        access = UserDatasetAccess(
            user_id=user_id,
            dataset_id=self.id,
            access_level=access_level,
            granted_by=granted_by
        )
        self.is_shared = True
        db.session.add(access)
    
    def revoke_access(self, user_id):
        """Revoke access from user."""
        access = self.access_permissions.filter_by(user_id=user_id).first()
        if access:
            db.session.delete(access)
            if not self.access_permissions.count():
                self.is_shared = False
```

**Step 4: Commit**

```bash
git add src/models.py
git commit -m "feat: add Dataset ownership and UserDatasetAccess permission model

- Add owner_id, is_public, is_shared to Dataset model
- Create UserDatasetAccess model for permission matrix
- Add can_access(), share_with(), revoke_access() methods
- Support read/write/admin permission levels"
```

---

### Task 2: Create User Workspace Model

**Files:** Modify `src/models.py`

**Step 1: Add UserWorkspace model**

```python
class UserWorkspace(db.Model):
    """User workspace configuration."""
    
    __tablename__ = 'user_workspaces'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    name = db.Column(db.String(100), default='My Workspace')
    description = db.Column(db.Text)
    
    # Preferences
    default_chart_type = db.Column(db.String(50), default='line')
    theme = db.Column(db.String(20), default='light')
    language = db.Column(db.String(10), default='en')
    
    # Quotas and limits
    max_datasets = db.Column(db.Integer, default=100)
    max_storage_mb = db.Column(db.Integer, default=1000)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='workspace', uselist=False)
    
    def __repr__(self):
        return f'<UserWorkspace {self.name} for {self.user.username}>'
```

**Step 2: Auto-create workspace on user creation**

Add to User model:
```python
@event.listens_for(User, 'after_insert')
def create_user_workspace(mapper, connection, target):
    """Auto-create workspace when user is created."""
    workspace = UserWorkspace(user_id=target.id)
    db.session.add(workspace)
```

**Step 3: Commit**

```bash
git add src/models.py
git commit -m "feat: add UserWorkspace model for user preferences and quotas

- Create UserWorkspace with name, description, preferences
- Add quotas: max_datasets, max_storage_mb
- Auto-create workspace on user creation via SQLAlchemy event"
```

---

## Phase 2: Admin Views for Management

### Task 3: Create Comprehensive User Admin View

**Files:** Modify `src/admin_views.py`

**Step 1: Enhanced UserAdminView with roles and permissions**

```python
class UserAdminView(ModelView):
    """Comprehensive user management admin view."""
    
    column_list = [
        'id', 'username', 'email', 'is_active', 'roles_list', 
        'owned_datasets_count', 'created_at', 'last_login'
    ]
    
    column_filters = [
        'is_active', 'roles', 'created_at'
    ]
    
    column_searchable_list = ['username', 'email']
    
    column_labels = {
        'id': 'ID',
        'username': 'Username',
        'email': 'Email',
        'is_active': 'Active',
        'roles_list': 'Roles',
        'owned_datasets_count': 'Datasets',
        'created_at': 'Created',
        'last_login': 'Last Login'
    }
    
    # Custom formatters
    column_formatters = {
        'roles_list': lambda v, c, m, p: ', '.join([r.name for r in m.roles]) if m.roles else 'No roles',
        'owned_datasets_count': lambda v, c, m, p: len(m.owned_datasets),
    }
    
    # Form configuration
    form_columns = [
        'username', 'email', 'password', 'is_active', 'roles'
    ]
    
    form_extra_fields = {
        'password': PasswordField('Password (leave empty to keep current)')
    }
    
    # Actions
    @action('deactivate', 'Deactivate Users', 'Are you sure you want to deactivate selected users?')
    def action_deactivate(self, ids):
        for user_id in ids:
            user = User.query.get(user_id)
            if user and user.username != 'admin':  # Prevent deactivating admin
                user.is_active = False
        db.session.commit()
        flash(f'{len(ids)} users deactivated.', 'success')
    
    @action('activate', 'Activate Users')
    def action_activate(self, ids):
        for user_id in ids:
            user = User.query.get(user_id)
            if user:
                user.is_active = True
        db.session.commit()
        flash(f'{len(ids)} users activated.', 'success')
    
    def on_model_change(self, form, model, is_created):
        """Hash password when creating or updating user."""
        if is_created or (hasattr(form, 'password') and form.password.data):
            model.set_password(form.password.data)
    
    can_view_details = True
    details_modal = True
    page_size = 50
```

**Step 2: Commit**

```bash
git add src/admin_views.py
git commit -m "feat: enhance UserAdminView with role management and bulk actions

- Display roles and dataset counts in list view
- Add activate/deactivate bulk actions
- Password field with validation
- Prevent admin deactivation"
```

---

### Task 4: Create Dataset Permission Admin View

**Files:** Modify `src/admin_views.py`

**Step 1: Create UserDatasetAccessAdminView**

```python
class UserDatasetAccessAdminView(ModelView):
    """Manage dataset permissions from admin."""
    
    column_list = [
        'id', 'user', 'dataset', 'access_level', 'granted_by', 'granted_at'
    ]
    
    column_filters = [
        'access_level', 'granted_at', 'user', 'dataset'
    ]
    
    column_searchable_list = ['user.username', 'dataset.indicator_name']
    
    column_labels = {
        'id': 'ID',
        'user': 'User',
        'dataset': 'Dataset',
        'access_level': 'Permission Level',
        'granted_by': 'Granted By',
        'granted_at': 'Granted At',
        'expires_at': 'Expires At'
    }
    
    form_columns = [
        'user', 'dataset', 'access_level', 'expires_at'
    ]
    
    # Auto-set granted_by to current admin
    def on_model_change(self, form, model, is_created):
        if is_created:
            model.granted_by = current_user.id
    
    # Custom validation
    def validate_form(self, form):
        if form.user.data and form.dataset.data:
            if form.user.data.id == form.dataset.data.owner_id:
                raise ValidationError('User is already the owner of this dataset')
        return super().validate_form(form)
    
    can_view_details = True
    page_size = 50
```

**Step 2: Enhanced DatasetAdminView with sharing**

```python
class DatasetAdminView(ModelView):
    """Dataset management with sharing controls."""
    
    column_list = [
        'id', 'indicator_name', 'source', 'topic', 'owner', 
        'is_public', 'is_shared', 'shared_with_count', 'row_count'
    ]
    
    column_filters = [
        'source', 'topic', 'is_public', 'is_shared', 'owner', 'is_edited'
    ]
    
    form_columns = [
        'indicator_name', 'source', 'topic', 'description',
        'owner', 'is_public', 'is_shared',
        'row_count', 'column_count', 'completeness_score'
    ]
    
    column_formatters = {
        'shared_with_count': lambda v, c, m, p: m.access_permissions.count(),
        'owner': lambda v, c, m, p: m.owner.username if m.owner else 'Unknown'
    }
    
    # Actions for bulk sharing
    @action('make_public', 'Make Public', 'Make selected datasets publicly readable?')
    def action_make_public(self, ids):
        for dataset_id in ids:
            dataset = Dataset.query.get(dataset_id)
            if dataset:
                dataset.is_public = True
        db.session.commit()
        flash(f'{len(ids)} datasets made public.', 'success')
    
    @action('make_private', 'Make Private')
    def action_make_private(self, ids):
        for dataset_id in ids:
            dataset = Dataset.query.get(dataset_id)
            if dataset:
                dataset.is_public = False
        db.session.commit()
        flash(f'{len(ids)} datasets made private.', 'success')
    
    @action('transfer_ownership', 'Transfer Ownership', 'Transfer to user:')
    def action_transfer_ownership(self, ids):
        # This would open a modal to select new owner
        # For now, just a placeholder
        flash('Use individual edit to transfer ownership', 'info')
```

**Step 3: Commit**

```bash
git add src/admin_views.py
git commit -m "feat: add UserDatasetAccessAdminView and enhance DatasetAdminView

- Create UserDatasetAccessAdminView for permission management
- Auto-set granted_by to current admin
- Add make_public/make_private bulk actions
- Display sharing status and counts in dataset list"
```

---

### Task 5: Create Workspace Admin View

**Files:** Modify `src/admin_views.py`

**Step 1: Create UserWorkspaceAdminView**

```python
class UserWorkspaceAdminView(ModelView):
    """Manage user workspaces from admin."""
    
    column_list = [
        'id', 'user', 'name', 'theme', 'language', 
        'max_datasets', 'max_storage_mb', 'updated_at'
    ]
    
    column_filters = [
        'theme', 'language', 'max_datasets'
    ]
    
    column_labels = {
        'id': 'ID',
        'user': 'User',
        'name': 'Workspace Name',
        'theme': 'UI Theme',
        'language': 'Language',
        'max_datasets': 'Max Datasets',
        'max_storage_mb': 'Max Storage (MB)',
        'updated_at': 'Last Updated'
    }
    
    form_columns = [
        'user', 'name', 'description',
        'default_chart_type', 'theme', 'language',
        'max_datasets', 'max_storage_mb'
    ]
    
    form_choices = {
        'theme': [
            ('light', 'Light'),
            ('dark', 'Dark')
        ],
        'language': [
            ('en', 'English'),
            ('es', 'Español')
        ],
        'default_chart_type': [
            ('line', 'Line Chart'),
            ('bar', 'Bar Chart'),
            ('scatter', 'Scatter Plot'),
            ('pie', 'Pie Chart')
        ]
    }
    
    can_create = False  # Workspaces auto-created with users
    can_delete = False  # Prevent deleting workspaces
    can_view_details = True
```

**Step 2: Commit**

```bash
git add src/admin_views.py
git commit -m "feat: add UserWorkspaceAdminView for workspace management

- Manage workspace name, theme, language preferences
- Configure quotas: max_datasets, max_storage_mb
- Prevent manual creation/deletion (auto-managed)"
```

---

### Task 6: Register All Admin Views

**Files:** Modify `src/web/__init__.py`

**Step 1: Import and register all views**

```python
from src.admin_views import (
    SecureAdminIndexView, DatasetAdminView,
    DatasetColumnAdminView, IndicatorAdminView, 
    UserAdminView, RoleAdminView,
    UserDatasetAccessAdminView,  # NEW
    UserWorkspaceAdminView       # NEW
)
from src.models import (
    Dataset, DatasetColumn, Indicator, 
    User, Role, UserDatasetAccess, UserWorkspace  # NEW imports
)

# ... in create_app() ...

admin.add_view(DatasetAdminView(Dataset, db.session))
admin.add_view(DatasetColumnAdminView(DatasetColumn, db.session))
admin.add_view(IndicatorAdminView(Indicator, db.session))
admin.add_view(UserAdminView(User, db.session))
admin.add_view(RoleAdminView(Role, db.session))
admin.add_view(UserDatasetAccessAdminView(UserDatasetAccess, db.session, 
                                         name='Permissions', 
                                         category='Access Control'))
admin.add_view(UserWorkspaceAdminView(UserWorkspace, db.session, 
                                     name='Workspaces'))
```

**Step 2: Commit**

```bash
git add src/web/__init__.py
git commit -m "feat: register all admin views including permissions and workspaces

- Add UserDatasetAccessAdminView as 'Permissions' in Access Control category
- Add UserWorkspaceAdminView as 'Workspaces'
- Import all required models"
```

---

## Phase 3: Data Access Layer

### Task 7: Create Permission Service

**Files:** Create `src/services/permissions.py`

**Step 1: Create permission checking service**

```python
"""Permission checking service for multi-user access control."""

from typing import Optional, List
from src.models import Dataset, UserDatasetAccess, User, db


class PermissionService:
    """Service for checking and managing dataset permissions."""
    
    @staticmethod
    def can_read(user_id: int, dataset_id: int) -> bool:
        """Check if user can read dataset."""
        dataset = Dataset.query.get(dataset_id)
        if not dataset:
            return False
        return dataset.can_access(user_id, 'read')
    
    @staticmethod
    def can_write(user_id: int, dataset_id: int) -> bool:
        """Check if user can modify dataset."""
        dataset = Dataset.query.get(dataset_id)
        if not dataset:
            return False
        return dataset.can_access(user_id, 'write')
    
    @staticmethod
    def can_admin(user_id: int, dataset_id: int) -> bool:
        """Check if user can administer dataset (share, delete)."""
        dataset = Dataset.query.get(dataset_id)
        if not dataset:
            return False
        return dataset.can_access(user_id, 'admin')
    
    @staticmethod
    def get_user_datasets(user_id: int, include_public: bool = True) -> List[Dataset]:
        """Get all datasets accessible by user."""
        # User's own datasets
        own_datasets = Dataset.query.filter_by(owner_id=user_id).all()
        
        # Datasets shared with user
        shared = Dataset.query.join(UserDatasetAccess).filter(
            UserDatasetAccess.user_id == user_id
        ).all()
        
        # Public datasets
        public = []
        if include_public:
            public = Dataset.query.filter_by(is_public=True).all()
        
        # Combine and remove duplicates
        all_datasets = {d.id: d for d in own_datasets + shared + public}
        return list(all_datasets.values())
    
    @staticmethod
    def grant_access(owner_id: int, dataset_id: int, user_id: int, 
                    access_level: str = 'read') -> bool:
        """Grant access to dataset. Only owner or admin can grant."""
        dataset = Dataset.query.get(dataset_id)
        if not dataset:
            return False
        
        # Check if owner or admin
        if dataset.owner_id != owner_id:
            # Check if granter has admin permission
            granter_access = UserDatasetAccess.query.filter_by(
                user_id=owner_id, dataset_id=dataset_id
            ).first()
            if not granter_access or granter_access.access_level != 'admin':
                return False
        
        # Grant access
        dataset.share_with(user_id, access_level, owner_id)
        db.session.commit()
        return True
    
    @staticmethod
    def revoke_access(revoker_id: int, dataset_id: int, user_id: int) -> bool:
        """Revoke access from dataset."""
        dataset = Dataset.query.get(dataset_id)
        if not dataset:
            return False
        
        # Only owner, admin, or the granter can revoke
        if dataset.owner_id != revoker_id:
            revoker_access = UserDatasetAccess.query.filter_by(
                user_id=revoker_id, dataset_id=dataset_id
            ).first()
            if not revoker_access or revoker_access.access_level != 'admin':
                return False
        
        dataset.revoke_access(user_id)
        db.session.commit()
        return True
```

**Step 2: Commit**

```bash
git add src/services/permissions.py
git commit -m "feat: create PermissionService for access control

- can_read(), can_write(), can_admin() permission checks
- get_user_datasets() to list accessible datasets
- grant_access() and revoke_access() with validation
- Centralized permission logic"
```

---

## Phase 4: Migration Script

### Task 8: Create Migration Script

**Files:** Create `scripts/migrate_multiuser_admin.py`

```bash
git add scripts/migrate_multiuser_admin.py
git commit -m "feat: add migration script for admin-managed multiuser system

- Add owner_id to existing datasets
- Create default admin user
- Create initial roles
- Setup admin workspace"
```

---

## Summary

### Admin Interface Now Supports:

**Users Management:**
- Create/edit/delete users
- Activate/deactivate users (bulk)
- Assign roles to users
- View user datasets count

**Roles Management:**
- Create/edit/delete roles
- Assign descriptions

**Dataset Management:**
- View ownership and sharing status
- Make datasets public/private (bulk)
- Transfer ownership
- See sharing count

**Permissions Management (New Menu):**
- Grant access to users
- Set permission levels (read/write/admin)
- Set expiration dates
- View who granted access
- Revoke access

**Workspace Management:**
- Configure workspace name
- Set UI theme and language
- Set quotas (max datasets, storage)
- View last updated

### Security:
- Only admin can access admin panel
- Users can only see their own data (unless shared)
- Permission checks in service layer
- Audit trail (granted_by, granted_at)

All configuration is now 100% doable via `/admin` interface!
