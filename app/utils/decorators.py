from functools import wraps
from flask import redirect, url_for, flash, abort
from flask_login import current_user

def role_required(*roles):
    """Decorator to restrict access to specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            
            if not current_user.has_role(*roles):
                flash('You do not have permission to access this page.', 'danger')
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator to restrict access to admin only"""
    return role_required('admin')(f)

def hr_or_admin_required(f):
    """Decorator to restrict access to HR or admin"""
    return role_required('admin', 'hr')(f)
