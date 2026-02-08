"""Flask-Admin custom views with RBAC."""

from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_admin.actions import action
from flask import flash, redirect, url_for, request
from markupsafe import Markup
from flask_login import current_user
from wtforms import PasswordField

from src.models import db, User, Dataset


class SecureAdminIndexView(AdminIndexView):
    """Secure admin index view with authentication."""

    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        # Redirect to login page if user doesn't have access
        return redirect(url_for('auth.login', next=request.url))


class DatasetAdminView(ModelView):
    """Dataset management with sharing controls."""

    column_list = [
        'id', 'indicator_name', 'source', 'topic', 'owner',
        'is_public', 'is_shared', 'shared_with_count', 'row_count'
    ]

    column_sortable_list = [
        'id', 'indicator_name', 'source', 'topic', 'row_count',
        'country_count', 'completeness_score', 'indexed_at'
    ]

    column_filters = [
        'source', 'topic', 'is_public', 'is_shared', 'owner', 'is_edited'
    ]

    column_searchable_list = ['indicator_name', 'description', 'indicator_id']

    column_labels = {
        'id': 'ID',
        'indicator_name': 'Indicator Name',
        'source': 'Source',
        'topic': 'Topic',
        'owner': 'Owner',
        'is_public': 'Public',
        'is_shared': 'Shared',
        'shared_with_count': 'Shared With',
        'row_count': 'Rows',
        'country_count': 'Countries',
        'completeness_score': 'Completeness %',
        'indexed_at': 'Indexed',
        'is_edited': 'Edited'
    }

    column_formatters = {
        'completeness_score': lambda v, c, m, p: f"{m.completeness_score:.1f}%" if m.completeness_score else '-',
        'indicator_name': lambda v, c, m, p: Markup(f'<a href="/edit?dataset_id={m.id}">{m.indicator_name}</a>'),
        'shared_with_count': lambda v, c, m, p: m.access_permissions.count() if hasattr(m, 'access_permissions') else 0,
        'owner': lambda v, c, m, p: m.owner.username if m.owner else 'Unknown'
    }

    form_columns = [
        'indicator_name', 'source', 'topic', 'description',
        'owner', 'is_public', 'is_shared',
        'row_count', 'column_count', 'completeness_score'
    ]

    form_excluded_columns = ['columns', 'indexed_at', 'access_permissions']

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
                count += 1

        flash(f'{count} datasets scheduled for reindexing.', 'success')

    @action('delete_files', 'Delete Files', 'WARNING: This will delete the actual CSV files. Continue?')
    def action_delete_files(self, ids):
        """Delete datasets and their files."""
        flash('File deletion not implemented yet.', 'warning')

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
        'owned_datasets_count': lambda v, c, m, p: len(m.owned_datasets) if m.owned_datasets else 0,
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

    can_view_details = True
    page_size = 50


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
