from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from app.utils.decorators import hr_or_admin_required
from app.models.attendance import Attendance
from app.models.leave import Leave
from app.models.payroll import Payroll
from app.models.user import User
from app.utils.report_generator import generate_payroll_report, generate_attendance_report
from datetime import datetime, timedelta
import os

bp = Blueprint('hr', __name__, url_prefix='/hr')

@bp.route('/dashboard')
@login_required
@hr_or_admin_required
def dashboard():
    """HR dashboard"""
    # Get today's attendance summary
    today = datetime.now().date().isoformat()
    today_attendance = Attendance.get_all(start_date=today, end_date=today)
    
    # Get pending leave requests
    pending_leaves = Leave.get_all(status='pending')
    
    # Get employee count
    employees = User.get_all(role='employee')
    
    # Calculate stats
    total_employees = len(employees)
    present_today = len([a for a in today_attendance if a.get('status') in ['present', 'late']])
    absent_today = total_employees - present_today  # Absent = Total - Present
    pending_leave_count = len(pending_leaves)
    
    return render_template('hr/dashboard.html',
                         total_employees=total_employees,
                         present_today=present_today,
                         absent_today=absent_today,
                         pending_leave_count=pending_leave_count,
                         recent_leaves=pending_leaves[:5])

@bp.route('/employees')
@login_required
@hr_or_admin_required
def employees():
    """View all employees with current status, department, position - with filters"""
    from app.models.database import get_supabase
    
    # Get filter parameters
    search_query = request.args.get('search', '').strip()
    department_filter = request.args.get('department', '')
    position_filter = request.args.get('position', '')
    
    supabase = get_supabase()
    today = datetime.now().date().isoformat()
    
    # Get all employees
    query = supabase.table('users').select('*').eq('role', 'employee')
    employees_response = query.execute()
    employees = employees_response.data
    
    # Get today's attendance for all employees
    attendance_today = Attendance.get_all(start_date=today, end_date=today)
    
    # Create attendance lookup by user_id
    attendance_lookup = {}
    for att in attendance_today:
        user_id = att.get('user_id')
        attendance_lookup[user_id] = {
            'status': att.get('status', 'absent'),
            'time_in': att.get('time_in'),
            'time_out': att.get('time_out')
        }
    
    # First, collect ALL unique departments and positions from ALL employees
    all_departments = set()
    all_positions = set()
    
    for emp in employees:
        emp_dept = emp.get('department', 'N/A')
        emp_position = emp.get('position', 'Employee')
        
        if emp_dept and emp_dept != 'N/A':
            all_departments.add(emp_dept)
        if emp_position and emp_position != 'N/A':
            all_positions.add(emp_position)
    
    # Now combine employee data with attendance status and apply filters
    employee_list = []
    
    for emp in employees:
        emp_id = emp['id']
        emp_name = emp.get('name', 'N/A')
        emp_email = emp.get('email', 'N/A')
        emp_dept = emp.get('department', 'N/A')
        emp_position = emp.get('position', 'Employee')  # Default position
        emp_salary = emp.get('salary', 0)
        
        # Get attendance status
        att_status = attendance_lookup.get(emp_id, {})
        status = att_status.get('status', 'absent')
        time_in = att_status.get('time_in', '-')
        time_out = att_status.get('time_out', '-')
        
        # Apply filters
        if search_query:
            if search_query.lower() not in emp_name.lower() and \
               search_query.lower() not in emp_email.lower():
                continue
        
        if department_filter and emp_dept != department_filter:
            continue
        
        if position_filter and emp_position != position_filter:
            continue
        
        employee_list.append({
            'id': emp_id,
            'name': emp_name,
            'email': emp_email,
            'department': emp_dept,
            'position': emp_position,
            'salary': emp_salary,
            'status_today': status,
            'time_in': time_in,
            'time_out': time_out
        })
    
    # Sort by status (present first) then by name
    status_order = {'present': 0, 'late': 1, 'on_leave': 2, 'absent': 3}
    employee_list.sort(key=lambda x: (status_order.get(x['status_today'], 4), x['name']))
    
    return render_template('hr/employees.html',
                         employees=employee_list,
                         all_departments=sorted(all_departments),
                         all_positions=sorted(all_positions),
                         search_query=search_query,
                         department_filter=department_filter,
                         position_filter=position_filter,
                         today=datetime.now().strftime('%B %d, %Y'))

@bp.route('/attendance')
@login_required
@hr_or_admin_required
def attendance():
    """View all attendance records"""
    end_date = request.args.get('end_date', datetime.now().date().isoformat())
    start_date = request.args.get('start_date',
                                  (datetime.now().date() - timedelta(days=7)).isoformat())
    
    records = Attendance.get_all(start_date=start_date, end_date=end_date)
    
    return render_template('hr/attendance.html',
                         records=records,
                         start_date=start_date,
                         end_date=end_date)

@bp.route('/leaves')
@login_required
@hr_or_admin_required
def leaves():
    """View all leave requests"""
    status_filter = request.args.get('status', 'all')
    
    if status_filter == 'all':
        leave_requests = Leave.get_all()
    else:
        leave_requests = Leave.get_all(status=status_filter)
    
    return render_template('hr/leaves.html',
                         leave_requests=leave_requests,
                         status_filter=status_filter)

@bp.route('/leaves/<int:leave_id>/approve', methods=['POST'])
@login_required
@hr_or_admin_required
def approve_leave(leave_id):
    """Approve a leave request"""
    from app.models.notification import Notification
    
    leave = Leave.get_by_id(leave_id)
    
    if not leave:
        return jsonify({'success': False, 'message': 'Leave request not found'}), 404
    
    success, message = leave.approve(current_user.id)
    
    if success:
        # Send notification to employee
        Notification.notify_leave_approved(
            leave.user_id,
            leave.leave_type,
            leave.start_date,
            leave.end_date
        )
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': message}), 400

@bp.route('/leaves/<int:leave_id>/reject', methods=['POST'])
@login_required
@hr_or_admin_required
def reject_leave(leave_id):
    """Reject a leave request"""
    from app.models.notification import Notification
    
    leave = Leave.get_by_id(leave_id)
    
    if not leave:
        return jsonify({'success': False, 'message': 'Leave request not found'}), 404
    
    success, message = leave.reject(current_user.id)
    
    if success:
        # Send notification to employee
        Notification.notify_leave_rejected(
            leave.user_id,
            leave.leave_type,
            leave.start_date,
            leave.end_date
        )
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': message}), 400

@bp.route('/payroll')
@login_required
@hr_or_admin_required
def payroll():
    """View payroll records"""
    period_start = request.args.get('period_start')
    period_end = request.args.get('period_end')
    
    records = Payroll.get_all(period_start=period_start, period_end=period_end)
    
    return render_template('hr/payroll.html',
                         records=records,
                         period_start=period_start,
                         period_end=period_end)

@bp.route('/payroll/export')
@login_required
@hr_or_admin_required
def export_payroll():
    """Export payroll summary as Excel"""
    from app.utils.payroll_export import export_payroll_summary
    from flask import send_file
    
    period_start = request.args.get('period_start')
    period_end = request.args.get('period_end')
    
    records = Payroll.get_all(period_start=period_start, period_end=period_end)
    
    if not records:
        flash('No payroll records found for the selected period', 'warning')
        return redirect(url_for('hr.payroll'))
    
    try:
        filepath = export_payroll_summary(records)
        return send_file(filepath, as_attachment=True, download_name=os.path.basename(filepath))
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'danger')
        return redirect(url_for('hr.payroll'))

@bp.route('/payroll/generate', methods=['GET', 'POST'])
@login_required
@hr_or_admin_required
def generate_payroll():
    """Generate payroll for a period"""
    if request.method == 'POST':
        period_start = request.form.get('period_start')
        period_end = request.form.get('period_end')
        employee_ids = request.form.getlist('employee_ids')
        
        if not period_start or not period_end:
            flash('Please provide both start and end dates', 'danger')
            return redirect(url_for('hr.generate_payroll'))
        
        results = []
        errors = []
        
        for emp_id in employee_ids:
            payroll, error = Payroll.calculate_for_user(
                emp_id, period_start, period_end, current_user.id
            )
            
            if payroll:
                results.append(payroll)
            else:
                errors.append(f"Employee {emp_id}: {error}")
        
        if results:
            flash(f'Generated payroll for {len(results)} employees', 'success')
        
        if errors:
            for error in errors:
                flash(error, 'warning')
        
        return redirect(url_for('hr.payroll'))
    
    # GET request - show form
    employees = User.get_all(role='employee')
    return render_template('hr/generate_payroll.html', employees=employees)

@bp.route('/payroll/<int:payroll_id>/finalize', methods=['POST'])
@login_required
@hr_or_admin_required
def finalize_payroll(payroll_id):
    """Finalize a payroll record (HR review complete)"""
    # Get payroll record
    records = Payroll.get_all()
    payroll = next((p for p in records if p.get('id') == payroll_id), None)
    
    if not payroll:
        return jsonify({'success': False, 'message': 'Payroll record not found'}), 404
    
    # Create Payroll object and finalize
    payroll_obj = Payroll(
        id=payroll['id'],
        user_id=payroll['user_id'],
        period_start=payroll['period_start'],
        period_end=payroll['period_end'],
        base_salary=payroll['base_salary'],
        days_present=payroll['days_present'],
        days_absent=payroll['days_absent'],
        days_on_leave=payroll['days_on_leave'],
        deductions=payroll['deductions'],
        net_pay=payroll.get('net_pay', payroll.get('net_salary', 0)),
        status=payroll['status'],
        generated_by=payroll.get('generated_by'),
        created_at=payroll.get('created_at')
    )
    
    if payroll_obj.finalize():
        return jsonify({'success': True, 'message': 'Payroll finalized successfully. Ready to release to employees.'})
    else:
        return jsonify({'success': False, 'message': 'Failed to finalize payroll'}), 400

@bp.route('/payroll/<int:payroll_id>/release', methods=['POST'])
@login_required
@hr_or_admin_required
def release_payroll(payroll_id):
    """Release/pay payroll (employees can now see it)"""
    # Get payroll record
    records = Payroll.get_all()
    payroll = next((p for p in records if p.get('id') == payroll_id), None)
    
    if not payroll:
        return jsonify({'success': False, 'message': 'Payroll record not found'}), 404
    
    # Check if already finalized
    if payroll['status'] != 'finalized':
        return jsonify({'success': False, 'message': 'Payroll must be finalized before releasing'}), 400
    
    # Create Payroll object and release
    payroll_obj = Payroll(
        id=payroll['id'],
        user_id=payroll['user_id'],
        period_start=payroll['period_start'],
        period_end=payroll['period_end'],
        base_salary=payroll['base_salary'],
        days_present=payroll['days_present'],
        days_absent=payroll['days_absent'],
        days_on_leave=payroll['days_on_leave'],
        deductions=payroll['deductions'],
        net_pay=payroll.get('net_pay', payroll.get('net_salary', 0)),
        status=payroll['status'],
        generated_by=payroll.get('generated_by'),
        created_at=payroll.get('created_at')
    )
    
    if payroll_obj.release():
        # Send notification to employee
        from app.models.notification import Notification
        employee_name = payroll.get('users', {}).get('name', 'Employee')
        period = f"{payroll['period_start']} to {payroll['period_end']}"
        Notification.create(
            user_id=payroll['user_id'],
            title='Payroll Released',
            message=f'Your payroll for {period} is now available. Net Pay: ₱{payroll.get("net_pay", 0):,.2f}',
            type='success',
            link='/employee/payroll'
        )
        return jsonify({'success': True, 'message': f'Payroll released to {employee_name}. Employee has been notified.'})
    else:
        return jsonify({'success': False, 'message': 'Failed to release payroll'}), 400

@bp.route('/payroll/<int:payroll_id>/delete', methods=['POST'])
@login_required
@hr_or_admin_required
def delete_payroll(payroll_id):
    """Delete a payroll record"""
    success, message = Payroll.delete(payroll_id)
    
    if success:
        flash(message, 'success')
        return jsonify({'success': True, 'message': message})
    else:
        flash(message, 'danger')
        return jsonify({'success': False, 'message': message}), 400

@bp.route('/reports/payroll')
@login_required
@hr_or_admin_required
def download_payroll_report():
    """Download payroll report"""
    period_start = request.args.get('period_start')
    period_end = request.args.get('period_end')
    format_type = request.args.get('format', 'excel')  # 'excel' or 'pdf'
    
    records = Payroll.get_all(period_start=period_start, period_end=period_end)
    
    if not records:
        flash('No payroll records found for the selected period', 'warning')
        return redirect(url_for('hr.payroll'))
    
    file_path = generate_payroll_report(records, format_type, period_start, period_end)
    
    return send_file(file_path, as_attachment=True)

@bp.route('/reports/attendance')
@login_required
@hr_or_admin_required
def download_attendance_report():
    """Download attendance report"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    format_type = request.args.get('format', 'excel')
    
    records = Attendance.get_all(start_date=start_date, end_date=end_date)
    
    if not records:
        flash('No attendance records found for the selected period', 'warning')
        return redirect(url_for('hr.attendance'))
    
    file_path = generate_attendance_report(records, format_type, start_date, end_date)
    
    return send_file(file_path, as_attachment=True)
