"""SQLAlchemy models for Flask-Admin."""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


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
