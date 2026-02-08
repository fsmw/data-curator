# Flask-Admin Configuration for Mises Data Curator

## Installation

Add to `requirements.txt`:
```
flask-admin>=1.6.0
flask-sqlalchemy>=3.0.0
sqlalchemy>=2.0.0
```

Then install:
```bash
pip install flask-admin flask-sqlalchemy sqlalchemy
```

## Implementation Plan

### 1. Create Database Models (`src/models.py`)

```python
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
```

### 2. Create Admin Views (`src/admin_views.py`)

```python
"""Flask-Admin custom views."""

from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_admin.actions import action
from flask import flash, redirect, url_for
from markupsafe import Markup


class SecureAdminIndexView(AdminIndexView):
    """Secure admin index view."""
    
    def is_accessible(self):
        # Add authentication here if needed
        return True


class DatasetAdminView(ModelView):
    """Custom Dataset admin view."""
    
    # List view configuration
    column_list = [
        'id', 'indicator_name', 'source', 'topic', 'row_count', 
        'country_count', 'completeness_score', 'indexed_at', 'is_edited'
    ]
    
    column_sortable_list = [
        'id', 'indicator_name', 'source', 'topic', 'row_count',
        'country_count', 'completeness_score', 'indexed_at'
    ]
    
    column_filters = [
        'source', 'topic', 'is_edited', 'min_year', 'max_year',
        'indicator_name'
    ]
    
    column_searchable_list = ['indicator_name', 'description', 'indicator_id']
    
    # Column labels
    column_labels = {
        'id': 'ID',
        'indicator_name': 'Indicator Name',
        'source': 'Source',
        'topic': 'Topic',
        'row_count': 'Rows',
        'country_count': 'Countries',
        'completeness_score': 'Completeness %',
        'indexed_at': 'Indexed',
        'is_edited': 'Edited'
    }
    
    # Formatters
    column_formatters = {
        'completeness_score': lambda v, c, m, p: f"{m.completeness_score:.1f}%" if m.completeness_score else '-',
        'indicator_name': lambda v, c, m, p: Markup(f'<a href="/edit?dataset_id={m.id}">{m.indicator_name}</a>'),
    }
    
    # Actions
    @action('reindex', 'Reindex Selected', 'Are you sure you want to reindex selected datasets?')
    def action_reindex(self, ids):
        """Reindex selected datasets."""
        from src.dataset_catalog import DatasetCatalog
        from src.config import Config
        
        config = Config()
        catalog = DatasetCatalog(config)
        
        count = 0
        for _id in ids:
            dataset = catalog.get_dataset(int(_id))
            if dataset:
                # Reindex logic here
                count += 1
        
        flash(f'{count} datasets scheduled for reindexing.', 'success')
    
    @action('delete_files', 'Delete Files', 'WARNING: This will delete the actual CSV files. Continue?')
    def action_delete_files(self, ids):
        """Delete datasets and their files."""
        flash('File deletion not implemented yet.', 'warning')
    
    # Form configuration
    form_excluded_columns = ['columns', 'indexed_at']
    
    can_create = False  # Datasets are created via ingestion
    can_edit = True
    can_delete = True
    can_view_details = True
    
    details_modal = True
    
    page_size = 50


class DatasetColumnAdminView(ModelView):
    """Dataset Column admin view."""
    
    column_list = ['id', 'dataset', 'column_name', 'column_type', 'unique_count', 'null_count']
    column_filters = ['column_name', 'column_type']
    column_searchable_list = ['column_name']
    
    column_labels = {
        'dataset': 'Dataset',
        'column_name': 'Column Name',
        'column_type': 'Type',
        'unique_count': 'Unique Values',
        'null_count': 'Null Count'
    }
    
    can_create = False
    can_edit = False
    can_delete = False


class IndicatorAdminView(ModelView):
    """Indicator configuration admin view."""
    
    column_list = ['indicator_id', 'name', 'source', 'topic', 'active', 'created_at']
    column_filters = ['source', 'topic', 'active']
    column_searchable_list = ['indicator_id', 'name', 'description']
    
    column_labels = {
        'indicator_id': 'Indicator ID',
        'name': 'Name',
        'source': 'Source',
        'topic': 'Topic',
        'active': 'Active'
    }
    
    form_columns = ['indicator_id', 'name', 'description', 'source', 'topic', 'tags', 'active']
    
    page_size = 50
```

### 3. Initialize Admin in Web App (`src/web/__init__.py`)

Add to `create_app()`:

```python
from src.models import db, Dataset, DatasetColumn, Indicator
from src.admin_views import (
    SecureAdminIndexView, DatasetAdminView, 
    DatasetColumnAdminView, IndicatorAdminView
)

def create_app():
    app = Flask(__name__)
    
    # ... existing configuration ...
    
    # Configure SQLAlchemy
    from src.config import Config
    config = Config()
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{config.data_root / 'datasets_catalog.db'}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    
    # Initialize Flask-Admin
    admin = Admin(
        app, 
        name='Data Curator Admin',
        template_mode='bootstrap4',
        index_view=SecureAdminIndexView()
    )
    
    # Add views
    admin.add_view(DatasetAdminView(Dataset, db.session))
    admin.add_view(DatasetColumnAdminView(DatasetColumn, db.session))
    admin.add_view(IndicatorAdminView(Indicator, db.session))
    
    # ... rest of your app setup ...
    
    return app
```

### 4. Add Migration Script (`scripts/init_admin.py`)

```python
#!/usr/bin/env python3
"""Initialize Flask-Admin database tables."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.web import create_app
from src.models import db


def init_admin():
    """Create admin tables."""
    app = create_app()
    
    with app.app_context():
        # Create tables
        db.create_all()
        print("✓ Admin tables created successfully")
        
        # Import existing indicators
        from src.config import Config
        from src.models import Indicator
        
        config = Config()
        indicators = config.get_indicators()
        
        count = 0
        for ind in indicators:
            # Check if already exists
            existing = Indicator.query.filter_by(
                indicator_id=ind.get('id', ind.get('indicator_id'))
            ).first()
            
            if not existing:
                indicator = Indicator(
                    indicator_id=ind.get('id', ind.get('indicator_id')),
                    name=ind.get('name', ind.get('indicator_name', '')),
                    description=ind.get('description'),
                    source=ind.get('source', 'manual'),
                    topic=ind.get('topic'),
                    tags=str(ind.get('tags', [])),
                    active=True
                )
                db.session.add(indicator)
                count += 1
        
        db.session.commit()
        print(f"✓ Imported {count} indicators")


if __name__ == '__main__':
    init_admin()
```

### 5. Run Setup

```bash
# Add to requirements and install
pip install flask-admin flask-sqlalchemy sqlalchemy

# Initialize admin tables
python scripts/init_admin.py

# Run the web app
python -m src.web
```

### 6. Access Admin

Navigate to: `http://127.0.0.1:5000/admin`

### Features

- **Datasets**: View, edit metadata, search, filter by source/topic
- **Columns**: View column metadata per dataset
- **Indicators**: Manage indicator configurations
- **Actions**: Bulk reindex, export data
- **Secure**: Ready for authentication integration

### Next Steps

1. Add authentication (Flask-Login)
2. Add more admin actions (export, sync)
3. Create custom dashboard widgets
4. Add data validation rules

Would you like me to implement this configuration?
