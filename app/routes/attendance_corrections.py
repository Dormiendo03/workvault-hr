from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.utils.decorators import role_required, hr_or_admin_required
from app.models.attendance_correction import AttendanceCorrection
from app.models.attendance import Attendance
from app.models.notification import Notification
from app.models.user import User
from datetime import datetime

bp = Blueprint('attendance_corrections', __name__, url_prefix='/attendance-corrections')

@bp.route('/request', methods=['GET', 'POST'])
@login_required
@role_required('employee')
def request_correction():
    """Request attendance correction"""
    if request.method == 'POST':
        attendance_date = request.form.get('attendance_date')
        correction_type = request.form.get('correction_type')
        reason = request.form.get('reason')
        requested_clock_in = request.form.get('requested_clock_in')
        requested_clock_out = request.form.get('requested_clock_out')
        
        # Get current attendance data if exists
        from app.models.database import get_supabase
        supabase = get_supabase()
        existing = supabase.table('attendance').select('*')\
            .eq('user_id', current_user.id)\
            .eq('date', attendance_date)\
            .execute()
        
        current_clock_in = None
        current_clock_out = None
        
        if existing.data and len(existing.data) > 0:
            record = existing.data[0]
            current_clock_in = record.get('clock_in')
            current_clock_out = record.get('clock_out')
        
        # Format datetime strings
        if requested_clock_in:
            requested_clock_in = f"{attendance_date}T{requested_clock_in}:00"
        if requested_clock_out:
            requested_clock_out = f"{attendance_date}T{requested_clock_out}:00"
        
        success, message = AttendanceCorrection.create(
            user_id=current_user.id,
            attendance_date=attendance_date,
            correction_type=correction_type,
            reason=reason,
            current_clock_in=current_clock_in,
            current_clock_out=current_clock_out,
            requested_clock_in=requested_clock_in,
            requested_clock_out=requested_clock_out
        )
        
        if success:
            # Send notification to HR users only (not admin)
            from app.models.database import get_supabase
            supabase = get_supabase()
            hr_users = supabase.table('users').select('id')\
                .eq('role', 'hr')\
                .execute()
            
            correction_type_display = {
                'missing_clock_out': 'Missing Clock Out',
                'missing_day': 'Missing Day',
                'wrong_time': 'Wrong Time'
            }.get(correction_type, correction_type)
            
            for hr_user in hr_users.data:
                Notification.create(
                    user_id=hr_user['id'],
                    title='New Attendance Correction Request',
                    message=f'{current_user.name} requested a correction for {correction_type_display} on {attendance_date}',
                    type='info',
                    link='/attendance-corrections/manage'
                )
            
            flash(message, 'success')
            return redirect(url_for('attendance_corrections.my_requests'))
        else:
            flash(f'Error: {message}', 'danger')
    
    return render_template('attendance_corrections/request.html')

@bp.route('/my-requests')
@login_required
@role_required('employee')
def my_requests():
    """View my correction requests"""
    corrections = AttendanceCorrection.get_by_user(current_user.id)
    return render_template('attendance_corrections/my_requests.html', corrections=corrections)

@bp.route('/manage')
@login_required
@hr_or_admin_required
def manage():
    """Manage all correction requests (HR/Admin)"""
    status_filter = request.args.get('status', 'pending')
    corrections = AttendanceCorrection.get_all(status=status_filter if status_filter != 'all' else None)
    return render_template('attendance_corrections/manage.html', 
                         corrections=corrections,
                         status_filter=status_filter)

@bp.route('/<int:correction_id>/approve', methods=['POST'])
@login_required
@hr_or_admin_required
def approve(correction_id):
    """Approve a correction request"""
    review_notes = request.form.get('review_notes', '')
    
    # Get correction details before approving
    from app.models.database import get_supabase
    supabase = get_supabase()
    correction_response = supabase.table('attendance_corrections')\
        .select('*, users!attendance_corrections_user_id_fkey(name)')\
        .eq('id', correction_id)\
        .execute()
    
    if not correction_response.data:
        return jsonify({'success': False, 'message': 'Correction not found'}), 404
    
    correction = correction_response.data[0]
    employee_id = correction['user_id']
    employee_name = correction['users']['name']
    
    success, message = AttendanceCorrection.approve(correction_id, current_user.id, review_notes)
    
    if success:
        # Send notification to employee
        Notification.create(
            user_id=employee_id,
            title='Attendance Correction Approved',
            message=f'Your attendance correction request for {correction["attendance_date"]} has been approved by {current_user.name}',
            type='success',
            link='/attendance-corrections/my-requests'
        )
        
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': message}), 400

@bp.route('/<int:correction_id>/reject', methods=['POST'])
@login_required
@hr_or_admin_required
def reject(correction_id):
    """Reject a correction request"""
    review_notes = request.form.get('review_notes', '')
    
    if not review_notes:
        return jsonify({'success': False, 'message': 'Please provide a reason for rejection'}), 400
    
    # Get correction details before rejecting
    from app.models.database import get_supabase
    supabase = get_supabase()
    correction_response = supabase.table('attendance_corrections')\
        .select('*, users!attendance_corrections_user_id_fkey(name)')\
        .eq('id', correction_id)\
        .execute()
    
    if not correction_response.data:
        return jsonify({'success': False, 'message': 'Correction not found'}), 404
    
    correction = correction_response.data[0]
    employee_id = correction['user_id']
    employee_name = correction['users']['name']
    
    success, message = AttendanceCorrection.reject(correction_id, current_user.id, review_notes)
    
    if success:
        # Send notification to employee
        Notification.create(
            user_id=employee_id,
            title='Attendance Correction Rejected',
            message=f'Your attendance correction request for {correction["attendance_date"]} has been rejected by {current_user.name}. Reason: {review_notes}',
            type='error',
            link='/attendance-corrections/my-requests'
        )
        
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': message}), 400
