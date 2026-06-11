from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.utils.decorators import admin_required
from app.models.user import User
from app.models.attendance import Attendance
from app.models.leave import Leave
from app.models.payroll import Payroll
from app.utils.face_recognition_utils import face_manager
from datetime import datetime, timedelta

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard"""
    # Get statistics
    all_users = User.get_all()
    employees = [u for u in all_users if u.role == 'employee']
    hr_users = [u for u in all_users if u.role == 'hr']
    
    today = datetime.now().date().isoformat()
    today_attendance = Attendance.get_all(start_date=today, end_date=today)
    
    pending_leaves = Leave.get_all(status='pending')
    
    stats = {
        'total_employees': len(employees),
        'total_hr': len(hr_users),
        'present_today': len([a for a in today_attendance if a.get('status') in ['present', 'late']]),
        'pending_leaves': len(pending_leaves)
    }
    
    return render_template('admin/dashboard.html', stats=stats)

@bp.route('/employees')
@login_required
@admin_required
def employees():
    """Manage employees"""
    employees = User.get_all(role='employee')
    
    # Check face enrollment status for each employee
    for employee in employees:
        employee.has_face = face_manager.has_enrollment(employee.id)
    
    return render_template('admin/employees.html', employees=employees)

@bp.route('/employees/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_employee():
    """Add new employee"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        department = request.form.get('department')
        salary = request.form.get('salary')
        
        print(f"[ADD EMPLOYEE] Received data: email={email}, name={name}, dept={department}, salary={salary}")
        
        # Validate
        if not all([email, password, name, department, salary]):
            flash('All fields are required', 'danger')
            return redirect(url_for('admin.add_employee'))
        
        # Check if email exists
        existing = User.get_by_email(email)
        if existing:
            flash('Email already exists', 'danger')
            return redirect(url_for('admin.add_employee'))
        
        # Create user
        try:
            user = User.create(
                email=email,
                password=password,
                name=name,
                role='employee',
                department=department,
                salary=float(salary)
            )
            
            if user:
                flash(f'Employee {name} added successfully', 'success')
                return redirect(url_for('admin.employees'))
            else:
                flash('Failed to create employee - User.create returned None', 'danger')
        except Exception as e:
            print(f"[ADD EMPLOYEE ERROR] {e}")
            import traceback
            traceback.print_exc()
            flash(f'Error creating employee: {str(e)}', 'danger')
    
    return render_template('admin/add_employee.html')

@bp.route('/employees/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_employee(user_id):
    """Edit employee details"""
    user = User.get_by_id(user_id)
    
    if not user or user.role != 'employee':
        flash('Employee not found', 'danger')
        return redirect(url_for('admin.employees'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        department = request.form.get('department')
        salary = request.form.get('salary')
        leave_balance = request.form.get('leave_balance')
        is_active = request.form.get('is_active') == 'on'
        
        updates = {
            'name': name,
            'department': department,
            'salary': float(salary),
            'leave_balance': int(leave_balance),
            'is_active': is_active
        }
        
        if user.update(**updates):
            flash(f'Employee {name} updated successfully', 'success')
            return redirect(url_for('admin.employees'))
        else:
            flash('Failed to update employee', 'danger')
    
    return render_template('admin/edit_employee.html', user=user)

@bp.route('/employees/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_employee(user_id):
    """Deactivate employee"""
    user = User.get_by_id(user_id)
    
    if not user:
        return jsonify({'success': False, 'message': 'Employee not found'}), 404
    
    if user.update(is_active=False):
        # Also delete face encoding
        face_manager.delete_face(user_id)
        return jsonify({'success': True, 'message': 'Employee deactivated'})
    else:
        return jsonify({'success': False, 'message': 'Failed to deactivate employee'}), 400

@bp.route('/employees/<int:user_id>/enroll-face', methods=['GET', 'POST'])
@login_required
@admin_required
def enroll_employee_face(user_id):
    """Enroll employee face (admin enrolls for employee)"""
    user = User.get_by_id(user_id)
    
    if not user or user.role != 'employee':
        flash('Employee not found', 'danger')
        return redirect(url_for('admin.employees'))
    
    if request.method == 'POST':
        image_data = request.json.get('image')
        
        if not image_data:
            return jsonify({'success': False, 'message': 'No image provided'}), 400
        
        success, message = face_manager.enroll_face(user_id, image_data)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
    
    # GET request - show enrollment page
    has_face = face_manager.has_enrollment(user_id)
    return render_template('admin/enroll_face.html', employee=user, has_face=has_face)

@bp.route('/hr-users')
@login_required
@admin_required
def hr_users():
    """Manage HR users"""
    hr_users = User.get_all(role='hr')
    return render_template('admin/hr_users.html', hr_users=hr_users)

@bp.route('/hr-users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_hr_user():
    """Add new HR user"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        department = request.form.get('department')
        
        print(f"[ADD HR USER] Received data: email={email}, name={name}, dept={department}")
        
        if not all([email, password, name]):
            flash('Email, password, and name are required', 'danger')
            return redirect(url_for('admin.add_hr_user'))
        
        existing = User.get_by_email(email)
        if existing:
            flash('Email already exists', 'danger')
            return redirect(url_for('admin.add_hr_user'))
        
        try:
            user = User.create(
                email=email,
                password=password,
                name=name,
                role='hr',
                department=department
            )
            
            if user:
                flash(f'HR user {name} added successfully', 'success')
                return redirect(url_for('admin.hr_users'))
            else:
                flash('Failed to create HR user - User.create returned None', 'danger')
        except Exception as e:
            print(f"[ADD HR USER ERROR] {e}")
            import traceback
            traceback.print_exc()
            flash(f'Error creating HR user: {str(e)}', 'danger')
    
    return render_template('admin/add_hr_user.html')

@bp.route('/settings')
@login_required
@admin_required
def settings():
    """System settings"""
    return render_template('admin/settings.html')

@bp.route('/attendance')
@login_required
@admin_required
def attendance():
    """View all attendance (admin view)"""
    end_date = request.args.get('end_date', datetime.now().date().isoformat())
    start_date = request.args.get('start_date',
                                  (datetime.now().date() - timedelta(days=7)).isoformat())
    
    records = Attendance.get_all(start_date=start_date, end_date=end_date)
    
    return render_template('admin/attendance.html',
                         records=records,
                         start_date=start_date,
                         end_date=end_date)

@bp.route('/leaves')
@login_required
@admin_required
def leaves():
    """View all leaves (admin view)"""
    status_filter = request.args.get('status', 'all')
    
    if status_filter == 'all':
        leave_requests = Leave.get_all()
    else:
        leave_requests = Leave.get_all(status=status_filter)
    
    return render_template('admin/leaves.html',
                         leave_requests=leave_requests,
                         status_filter=status_filter)

@bp.route('/payroll')
@login_required
@admin_required
def payroll():
    """View all payroll (admin view)"""
    period_start = request.args.get('period_start')
    period_end = request.args.get('period_end')
    
    records = Payroll.get_all(period_start=period_start, period_end=period_end)
    
    return render_template('admin/payroll.html',
                         records=records,
                         period_start=period_start,
                         period_end=period_end)
