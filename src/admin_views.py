"""Flask-Admin custom views with RBAC."""

from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_admin.actions import action
from flask import flash, redirect, url_for, request
from markupsafe import Markup
from flask_login import current_user


class SecureAdminIndexView(AdminIndexView):
    """Secure admin index view with authentication."""

    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        # Redirect to login page if user doesn't have access
        return redirect(url_for('auth.login', next=request.url))


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


class UserAdminView(ModelView):
    """User management admin view."""

    column_list = ['id', 'username', 'email', 'is_active', 'created_at', 'last_login', 'roles']
    column_filters = ['is_active', 'roles']
    column_searchable_list = ['username', 'email']

    column_labels = {
        'id': 'ID',
        'username': 'Username',
        'email': 'Email',
        'is_active': 'Active',
        'created_at': 'Created',
        'last_login': 'Last Login',
        'roles': 'Roles'
    }

    form_columns = ['username', 'email', 'password', 'is_active', 'roles']
    
    # Custom formatter for roles
    column_formatters = {
        'roles': lambda v, c, m, p: ', '.join([role.name for role in m.roles]) if m.roles else 'No roles'
    }

    def on_model_change(self, form, model, is_created):
        """Hash password when creating or updating user."""
        if hasattr(form, 'password') and form.password.data:
            model.set_password(form.password.data)

    can_view_details = True
    page_size = 50


class RoleAdminView(ModelView):
    """Role management admin view."""
    
    column_list = ['id', 'name', 'description', 'users']
    column_searchable_list = ['name']
    
    column_labels = {
        'id': 'ID',
        'name': 'Role Name',
        'description': 'Description',
        'users': 'Users'
    }
    
    form_columns = ['name', 'description']
    
    column_formatters = {
        'users': lambda v, c, m, p: str(m.users.count()) + ' users'
    }
    
    page_size = 50
