from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from datetime import datetime

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

@bp.route('/setup-admin', methods=['GET', 'POST'])
def setup_admin():
    """One-time setup endpoint to create admin account"""
    if request.method == 'GET':
        # Check if admin already exists
        admin = User.get_by_email('admin@workvault.com')
        if admin:
            return jsonify({
                'success': True,
                'message': 'Admin account already exists!',
                'email': 'admin@workvault.com',
                'note': 'You can now login at /auth/login'
            })
        
        return jsonify({
            'success': False,
            'message': 'Admin account does not exist',
            'action': 'Send POST request to this endpoint to create admin account'
        })
    
    # POST request - create admin
    try:
        # Check if admin already exists
        existing_admin = User.get_by_email('admin@workvault.com')
        if existing_admin:
            return jsonify({
                'success': False,
                'message': 'Admin account already exists',
                'email': 'admin@workvault.com'
            }), 400
        
        # Create admin user
        admin = User.create(
            email='admin@workvault.com',
            password='admin123',
            name='System Administrator',
            role='admin',
            department='Administration',
            salary=0,
            leave_balance=15
        )
        
        if admin:
            return jsonify({
                'success': True,
                'message': 'Admin account created successfully!',
                'email': 'admin@workvault.com',
                'password': 'admin123',
                'note': 'Please login and change your password immediately',
                'login_url': '/auth/login'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to create admin account'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error creating admin: {str(e)}'
        }), 500
