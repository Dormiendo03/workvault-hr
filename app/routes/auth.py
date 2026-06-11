from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for(f'{current_user.role}.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        try:
            user = User.authenticate(email, password)
            
            if user and user.is_active:
                login_user(user, remember=remember)
                flash(f'Welcome back, {user.name}!', 'success')
                
                # Redirect based on role
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                
                return redirect(url_for(f'{user.role}.dashboard'))
            else:
                flash('Invalid email or password', 'danger')
        except Exception as e:
            print(f"Login error: {e}")
            flash(f'Login error: {str(e)}', 'danger')
    
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('auth.login'))
