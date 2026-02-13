"""Authentication blueprint for login/logout."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from src.models import User, db
from flask_babel import gettext as _

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        return redirect(url_for('ui.status'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been disabled.', 'error')
                return render_template('auth/login.html')

            login_user(user, remember=remember)
            session.permanent = remember
            user.last_login = db.func.now()
            db.session.commit()

            # Redirect to requested page or admin
            next_page = request.args.get('next')
            if next_page:
                # Si next_page comienza con el prefijo, redirigir directamente
                # Si no, usar url_for para asegurar que la URL sea correcta
                if next_page.startswith('/'):
                    return redirect(next_page)
                else:
                    return redirect(url_for('ui.status'))
            return redirect(url_for('admin.index'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/set-language', methods=['POST'])
@login_required
def set_language():
    """Set user language preference."""
    from flask import jsonify
    data = request.get_json()
    language = data.get('language') if data else None
    
    if language not in ['en_US', 'es_CL']:
        return jsonify({'success': False, 'error': 'Invalid language'}), 400
    
    ws = current_user.workspace
    if ws:
        try:
            ws.language = language
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return jsonify({'success': False, 'error': 'Workspace not found'}), 404


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Show and edit user profile."""
    if request.method == 'POST':
        email = request.form.get('email')
        language = request.form.get('language')

        if not email:
            flash(_('Email is required.'), 'error')
            return render_template('auth/profile.html', user=current_user, workspace=current_user.workspace)

        current_user.email = email

        ws = current_user.workspace
        if ws and language:
            ws.language = language

        try:
            db.session.commit()
            flash(_('Profile updated successfully.'), 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            db.session.rollback()
            flash(_('Error updating profile. Please try again.'), 'error')
            print(f"Profile update error: {e}")

    return render_template('auth/profile.html', user=current_user, workspace=getattr(current_user, 'workspace', None))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password."""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate current password
        if not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'error')
            return render_template('auth/change_password.html')

        # Validate new password
        if not new_password or len(new_password) < 6:
            flash('New password must be at least 6 characters long.', 'error')
            return render_template('auth/change_password.html')

        # Validate confirmation
        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return render_template('auth/change_password.html')
        
        # Update password
        current_user.set_password(new_password)
        db.session.commit()
        flash('Password changed successfully.', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/change_password.html')
