"""SQLAlchemy models for Flask-Admin with Role-Based Access Control."""

from flask_sqlalchemy import SQLAlchemy
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
    """Dataset model mirroring the datasets table."""
    
    __tablename__ = 'datasets'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    file_path = db.Column(db.String(500), unique=True, nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    source = db.Column(db.String(100), nullable=False)
    indicator_id = db.Column(db.String(100))
    indicator_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    topic = db.Column(db.String(100))
    
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
    
    # Relationship
    columns = db.relationship('DatasetColumn', backref='dataset', lazy=True)
    
    def __repr__(self):
        return f'<Dataset {self.indicator_name}>'
    
    def __str__(self):
        return self.indicator_name


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
