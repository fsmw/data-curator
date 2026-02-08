"""SQLAlchemy models for Flask-Admin with Role-Based Access Control."""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from datetime import datetime
from typing import List

db = SQLAlchemy()

# Association table for many-to-many relationship between User and Role
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)


class Role(db.Model):
    """Role model for RBAC."""
    
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    
    def __repr__(self):
        return f'<Role {self.name}>'
    
    def __str__(self):
        return self.name


class Dataset(db.Model):
    """Dataset model with ownership and sharing."""

    __tablename__ = 'datasets'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    file_path = db.Column(db.String(500), unique=True, nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    source = db.Column(db.String(100), nullable=False)
    indicator_id = db.Column(db.String(100))
    indicator_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    topic = db.Column(db.String(100))

    # Ownership and visibility
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_public = db.Column(db.Boolean, default=False)
    is_shared = db.Column(db.Boolean, default=False)

    file_size_bytes = db.Column(db.Integer)
    file_hash = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime)
    indexed_at = db.Column(db.DateTime, default=datetime.utcnow)

    row_count = db.Column(db.Integer)
    column_count = db.Column(db.Integer)
    columns_json = db.Column(db.Text)

    min_year = db.Column(db.Integer)
    max_year = db.Column(db.Integer)

    countries_json = db.Column(db.Text)
    country_count = db.Column(db.Integer)
    regions_json = db.Column(db.Text)

    null_percentage = db.Column(db.Float)
    completeness_score = db.Column(db.Float)
    is_edited = db.Column(db.Integer, default=0)

    # Relationships
    owner = db.relationship('User', foreign_keys=[owner_id], backref='owned_datasets')
    columns = db.relationship('DatasetColumn', backref='dataset', lazy=True)
    access_permissions = db.relationship('UserDatasetAccess', backref='dataset',
                                        lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Dataset {self.indicator_name}>'

    def __str__(self):
        return self.indicator_name

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


class DatasetColumn(db.Model):
    """Dataset column metadata."""

    __tablename__ = 'dataset_columns'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id'), nullable=False)
    column_name = db.Column(db.String(255), nullable=False)
    column_type = db.Column(db.String(50))
    sample_values_json = db.Column(db.Text)
    unique_count = db.Column(db.Integer)
    null_count = db.Column(db.Integer)

    def __repr__(self):
        return f'<DatasetColumn {self.column_name}>'


class Indicator(db.Model):
    """Indicator configuration model."""

    __tablename__ = 'indicators_config'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    indicator_id = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    source = db.Column(db.String(50), nullable=False)
    topic = db.Column(db.String(100))
    tags = db.Column(db.Text)  # JSON array
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Indicator {self.name}>'


class User(db.Model):
    """User model for authentication with roles."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    roles = db.relationship('Role', secondary=user_roles, lazy='dynamic',
                           backref=db.backref('users', lazy=True))

    def __repr__(self):
        return f'<User {self.username}>'

    def __str__(self):
        return self.username

    def set_password(self, password):
        """Hash and set user password."""
        from flask_bcrypt import generate_password_hash
        self.password_hash = generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Check if password matches."""
        from flask_bcrypt import check_password_hash
        return check_password_hash(self.password_hash, password)

    def has_role(self, role_name):
        """Check if user has a specific role."""
        return any(role.name == role_name for role in self.roles)
    
    @property
    def is_admin(self):
        """Check if user is admin."""
        return self.has_role('admin')

    # Flask-Login required methods
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active_user(self):
        return self.is_active

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


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
        return f'<UserWorkspace {self.name} for user {self.user_id}>'


class CopilotThread(db.Model):
    __tablename__ = "copilot_threads"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(255), default="New Analysis")
    session_id = db.Column(db.String(128))
    messages_json = db.Column(db.Text)
    charts_json = db.Column(db.Text)
    last_message = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref="copilot_threads")


# Auto-create workspace when user is created
@event.listens_for(User, 'after_insert')
def create_user_workspace(mapper, connection, target):
    """Auto-create workspace when user is created."""
    workspace = UserWorkspace(user_id=target.id)
    # Use the connection directly to avoid session issues
    from sqlalchemy import insert
    from sqlalchemy.orm import Session
    session = Session(bind=connection)
    session.add(workspace)
    session.commit()
