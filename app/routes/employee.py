from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.utils.decorators import role_required
from app.models.attendance import Attendance
from app.models.leave import Leave
from app.models.payroll import Payroll
from app.utils.face_recognition_utils import face_manager
from datetime import datetime, timedelta
import os

bp = Blueprint('employee', __name__, url_prefix='/employee')

@bp.route('/dashboard')
@login_required
@role_required('employee')
def dashboard():
    """Employee dashboard"""
    # Get today's attendance status
    today_status = Attendance.get_today_status(current_user.id)
    
    # Get recent attendance (last 7 days)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)
    recent_attendance = Attendance.get_by_user(
        current_user.id,
        start_date.isoformat(),
        end_date.isoformat()
    )
    
    # Get pending leave requests
    leaves = Leave.get_by_user(current_user.id)
    pending_leaves = [l for l in leaves if l.status == 'pending']
    
    return render_template('employee/dashboard.html',
                         today_status=today_status,
                         recent_attendance=recent_attendance,
                         pending_leaves=pending_leaves,
                         leave_balance=current_user.leave_balance)

@bp.route('/attendance')
@login_required
@role_required('employee')
def attendance():
    """View attendance history"""
    # Get date range from query params
    end_date = request.args.get('end_date', datetime.now().date().isoformat())
    start_date = request.args.get('start_date', 
                                  (datetime.now().date() - timedelta(days=30)).isoformat())
    
    records = Attendance.get_by_user(current_user.id, start_date, end_date)
    
    return render_template('employee/attendance.html',
                         records=records,
                         start_date=start_date,
                         end_date=end_date)

@bp.route('/clock-in', methods=['GET', 'POST'])
@login_required
@role_required('employee')
def clock_in():
    """Clock in with face recognition"""
    if request.method == 'POST':
        image_data = request.json.get('image')
        
        if not image_data:
            return jsonify({'success': False, 'message': 'No image provided'}), 400
        
        # Verify face
        user_id, confidence, error = face_manager.verify_face(image_data)
        
        if error:
            return jsonify({'success': False, 'message': error}), 400
        
        if not user_id or str(user_id) != str(current_user.id):
            return jsonify({'success': False, 'message': 'Face verification failed'}), 401
        
        # Record attendance
        attendance, error = Attendance.clock_in(current_user.id, face_verified=True)
        
        if error:
            return jsonify({'success': False, 'message': error}), 400
        
        return jsonify({
            'success': True,
            'message': f'Clocked in successfully at {attendance.time_in}',
            'confidence': f'{confidence * 100:.1f}%'
        })
    
    # Check if already clocked in
    today_status = Attendance.get_today_status(current_user.id)
    
    return render_template('employee/clock_in.html', today_status=today_status)

@bp.route('/clock-out', methods=['POST'])
@login_required
@role_required('employee')
def clock_out():
    """Clock out with face verification"""
    image_data = request.json.get('image')
    
    if not image_data:
        return jsonify({'success': False, 'message': 'No image provided'}), 400
    
    # Verify face
    user_id, confidence, error = face_manager.verify_face(image_data)
    
    if error:
        return jsonify({'success': False, 'message': error}), 400
    
    if not user_id or str(user_id) != str(current_user.id):
        return jsonify({'success': False, 'message': 'Face verification failed'}), 401
    
    # Clock out
    attendance, error = Attendance.clock_out(current_user.id)
    
    if error:
        return jsonify({'success': False, 'message': error}), 400
    
    return jsonify({
        'success': True,
        'message': f'Clocked out successfully at {attendance.time_out}',
        'confidence': f'{confidence * 100:.1f}%'
    })

@bp.route('/leaves')
@login_required
@role_required('employee')
def leaves():
    """View leave requests"""
    leave_requests = Leave.get_by_user(current_user.id)
    return render_template('employee/leaves.html',
                         leave_requests=leave_requests,
                         leave_balance=current_user.leave_balance)

@bp.route('/leaves/request', methods=['GET', 'POST'])
@login_required
@role_required('employee')
def request_leave():
    """Request new leave"""
    if request.method == 'POST':
        leave_type = request.form.get('leave_type')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        reason = request.form.get('reason')
        
        # Calculate days
        from datetime import datetime
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        days_count = (end - start).days + 1
        
        # Check leave balance
        if days_count > current_user.leave_balance:
            flash(f'Insufficient leave balance. You have {current_user.leave_balance} days available.', 'danger')
            return redirect(url_for('employee.request_leave'))
        
        # Create leave request
        leave, error = Leave.create(
            user_id=current_user.id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            days_count=days_count,
            reason=reason
        )
        
        if leave:
            flash('Leave request submitted successfully', 'success')
            return redirect(url_for('employee.leaves'))
        else:
            flash(f'Failed to submit leave request: {error}', 'danger')
    
    return render_template('employee/request_leave.html')

@bp.route('/payroll')
@login_required
@role_required('employee')
def payroll():
    """View payroll history (only paid/released payroll)"""
    all_payroll = Payroll.get_by_user(current_user.id)
    # Filter to only show paid payroll (status = 'paid')
    payroll_records = [p for p in all_payroll if p.status == 'paid']
    return render_template('employee/payroll.html', payroll_records=payroll_records)

@bp.route('/payroll/preview')
@login_required
@role_required('employee')
def payroll_preview():
    """Preview estimated paycheck for current period based on attendance so far"""
    return _preview_payroll_period('current')

@bp.route('/payroll/preview/last')
@login_required
@role_required('employee')
def payroll_preview_last():
    """Preview last paycheck - shows draft payroll if exists, otherwise calculates last completed period"""
    return _preview_payroll_period('last')

def _preview_payroll_period(period_type='current'):
    """
    Preview payroll for a specific period
    
    Args:
        period_type: 'current' for current period, 'last' for last completed period
    """
    from app.utils.ph_payroll_calculator import PHPayrollCalculator, calculate_late_minutes
    from app.models.database import get_supabase
    from dateutil import parser
    from datetime import time as dt_time
    
    supabase = get_supabase()
    
    # Get current date
    today = datetime.now().date()
    
    if period_type == 'last':
        # Check if there's a draft payroll for employee
        draft_payroll_response = supabase.table('payroll').select('*')\
            .eq('user_id', current_user.id)\
            .eq('status', 'draft')\
            .order('period_end', desc=True)\
            .limit(1)\
            .execute()
        
        if draft_payroll_response.data and len(draft_payroll_response.data) > 0:
            # Show the draft payroll that HR generated but hasn't finalized yet
            draft = draft_payroll_response.data[0]
            
            preview_data = {
                'period_start': parser.parse(draft['period_start']).date(),
                'period_end': parser.parse(draft['period_end']).date(),
                'period_name': 'Draft Payroll (Under HR Review)',
                'monthly_salary': draft['base_salary'],
                'days_present': draft['days_present'],
                'days_absent': draft['days_absent'],
                'days_on_leave': draft['days_on_leave'],
                'working_days': draft['days_present'] + draft['days_absent'] + draft['days_on_leave'],
                'basic_pay': draft['base_salary'] / 2,
                'overtime_pay': draft.get('overtime_pay', 0),
                'gross_earnings': draft.get('gross_earnings', draft['base_salary'] / 2),
                'tardiness_deduction': draft.get('tardiness_deduction', 0),
                'undertime_deduction': draft.get('undertime_deduction', 0),
                'absent_deduction': draft.get('absent_deduction', 0),
                'sss_contribution': draft.get('sss_contribution', 0),
                'philhealth_contribution': draft.get('philhealth_contribution', 0),
                'pagibig_contribution': draft.get('pagibig_contribution', 0),
                'withholding_tax': draft.get('withholding_tax', 0),
                'other_deductions': draft.get('other_deductions', 0),
                'total_deductions': draft['deductions'],
                'net_pay': draft.get('net_pay', draft.get('net_salary', 0)),
                'daily_rate': draft.get('daily_rate', 0),
                'hourly_rate': draft.get('hourly_rate', 0),
                'is_draft': True,  # Flag to show different messaging
                'draft_message': 'This is the draft payroll HR generated. Review it and request attendance corrections if needed BEFORE HR finalizes it.'
            }
            
            return render_template('employee/payroll_preview.html', preview=preview_data)
        
        # No draft payroll, calculate for last completed period
        if today.day <= 15:
            # Currently in 1st half, show 2nd half of last month
            if today.month == 1:
                last_month = today.replace(year=today.year - 1, month=12, day=16)
            else:
                last_month = today.replace(month=today.month - 1, day=16)
            
            period_start = last_month
            # Get last day of that month
            if last_month.month == 12:
                next_month = last_month.replace(year=last_month.year + 1, month=1, day=1)
            else:
                next_month = last_month.replace(month=last_month.month + 1, day=1)
            period_end = (next_month - timedelta(days=1))
            period_name = "Last Period (2nd Half)"
        else:
            # Currently in 2nd half, show 1st half of this month
            period_start = today.replace(day=1)
            period_end = today.replace(day=15)
            period_name = "Last Period (1st Half)"
    else:
        # Current period
        if today.day <= 15:
            period_start = today.replace(day=1)
            period_end = today.replace(day=15)
            period_name = "1st Half"
        else:
            period_start = today.replace(day=16)
            # Get last day of month
            if today.month == 12:
                next_month = today.replace(year=today.year + 1, month=1, day=1)
            else:
                next_month = today.replace(month=today.month + 1, day=1)
            period_end = (next_month - timedelta(days=1))
            period_name = "2nd Half"
    
    # Get user salary
    user_response = supabase.table('users').select('*').eq('id', current_user.id).execute()
    if not user_response.data:
        flash('User not found', 'danger')
        return redirect(url_for('employee.dashboard'))
    
    user = user_response.data[0]
    monthly_salary = user.get('salary', 0)
    
    if not monthly_salary:
        flash('Salary not configured. Please contact HR.', 'warning')
        return redirect(url_for('employee.payroll'))
    
    # Initialize Philippine payroll calculator
    calculator = PHPayrollCalculator(monthly_salary)
    
    # Get attendance records for current period
    attendance_response = supabase.table('attendance').select('*')\
        .eq('user_id', current_user.id)\
        .gte('date', period_start.isoformat())\
        .lte('date', period_end.isoformat())\
        .execute()
    
    attendance_records = attendance_response.data
    
    # Calculate attendance metrics (same logic as payroll calculation)
    days_present = 0
    days_on_leave = 0
    total_late_minutes = 0
    total_undertime_hours = 0
    total_overtime_hours = 0
    
    standard_time_in = dt_time(8, 0)  # 8:00 AM
    standard_time_out = dt_time(17, 0)  # 5:00 PM
    
    for record in attendance_records:
        status = record.get('status', '')
        
        # Only count completed days (has clock_out)
        if status in ['present', 'late'] and record.get('clock_out'):
            days_present += 1
            
            # Calculate tardiness
            if record.get('clock_in'):
                try:
                    clock_in_time = parser.parse(record['clock_in']).time()
                    late_minutes = calculate_late_minutes(standard_time_in, clock_in_time)
                    total_late_minutes += late_minutes
                except:
                    pass
            
            # Calculate overtime
            try:
                clock_out_time = parser.parse(record['clock_out']).time()
                if clock_out_time > standard_time_out:
                    # Use a fixed date for time comparison
                    comparison_date = datetime.now().date()
                    standard_dt = datetime.combine(comparison_date, standard_time_out)
                    actual_dt = datetime.combine(comparison_date, clock_out_time)
                    ot_hours = (actual_dt - standard_dt).total_seconds() / 3600
                    total_overtime_hours += ot_hours
            except:
                pass
        
        elif status == 'on_leave':
            days_on_leave += 1
    
    # Calculate working days in period up to today
    days_in_period = min((today - period_start).days + 1, (period_end - period_start).days + 1)
    working_days = sum(1 for i in range(days_in_period) 
                      if (period_start + timedelta(days=i)).weekday() < 5)  # Mon-Fri
    
    days_absent = working_days - days_present - days_on_leave
    
    # Calculate estimated payroll
    payroll_result = calculator.calculate_semi_monthly_payroll(
        worked_days=days_present + days_on_leave,
        late_minutes=total_late_minutes,
        undertime_hours=total_undertime_hours,
        absent_days=days_absent,
        ot_hours=total_overtime_hours,
        ot_type='regular',
        other_deductions=0
    )
    
    # Prepare preview data
    preview_data = {
        'period_start': period_start,
        'period_end': period_end,
        'period_name': period_name,
        'monthly_salary': monthly_salary,
        'days_present': days_present,
        'days_absent': days_absent,
        'days_on_leave': days_on_leave,
        'working_days': working_days,
        'basic_pay': payroll_result['basic_pay'],
        'overtime_pay': payroll_result['overtime_pay'],
        'gross_earnings': payroll_result['gross_earnings'],
        'tardiness_deduction': payroll_result['tardiness_deduction'],
        'undertime_deduction': payroll_result['undertime_deduction'],
        'absent_deduction': payroll_result['absent_deduction'],
        'sss_contribution': payroll_result['sss_contribution'],
        'philhealth_contribution': payroll_result['philhealth_contribution'],
        'pagibig_contribution': payroll_result['pagibig_contribution'],
        'withholding_tax': payroll_result['withholding_tax'],
        'other_deductions': payroll_result['other_deductions'],
        'total_deductions': payroll_result['total_deductions'],
        'net_pay': payroll_result['net_pay'],
        'daily_rate': payroll_result['daily_rate'],
        'hourly_rate': payroll_result['hourly_rate']
    }
    
    return render_template('employee/payroll_preview.html', preview=preview_data)

@bp.route('/payroll/<int:payroll_id>/export')
@login_required
@role_required('employee')
def export_payslip(payroll_id):
    """Export individual payslip as Excel (only if paid)"""
    from app.utils.payroll_export import export_employee_payslip
    from flask import send_file
    
    # Get payroll record
    payroll_records = Payroll.get_by_user(current_user.id)
    payroll = next((p for p in payroll_records if p.id == payroll_id), None)
    
    if not payroll:
        flash('Payroll record not found', 'danger')
        return redirect(url_for('employee.payroll'))
    
    # Check if payroll is released/paid
    if payroll.status != 'paid':
        flash('This payroll has not been released yet', 'warning')
        return redirect(url_for('employee.payroll'))
    
    # Prepare employee data
    employee_data = {
        'id': current_user.id,
        'name': current_user.name,
        'department': current_user.department,
        'position': 'Employee'
    }
    
    # Prepare payroll data
    payroll_data = {
        'period_start': payroll.period_start,
        'period_end': payroll.period_end,
        'basic_pay': payroll.base_salary / 2,  # Semi-monthly
        'overtime_pay': getattr(payroll, 'overtime_pay', 0),
        'gross_earnings': getattr(payroll, 'gross_earnings', payroll.base_salary / 2),
        'tardiness_deduction': getattr(payroll, 'tardiness_deduction', 0),
        'undertime_deduction': getattr(payroll, 'undertime_deduction', 0),
        'absent_deduction': getattr(payroll, 'absent_deduction', 0),
        'sss_contribution': getattr(payroll, 'sss_contribution', 0),
        'philhealth_contribution': getattr(payroll, 'philhealth_contribution', 0),
        'pagibig_contribution': getattr(payroll, 'pagibig_contribution', 0),
        'withholding_tax': getattr(payroll, 'withholding_tax', 0),
        'other_deductions': getattr(payroll, 'other_deductions', 0),
        'total_deductions': payroll.deductions,
        'net_pay': getattr(payroll, 'net_pay', getattr(payroll, 'net_salary', 0)),
        'daily_rate': getattr(payroll, 'daily_rate', 0),
        'hourly_rate': getattr(payroll, 'hourly_rate', 0),
        'per_minute_rate': 0
    }
    
    # Generate Excel file
    try:
        filepath = export_employee_payslip(employee_data, payroll_data)
        return send_file(filepath, as_attachment=True, download_name=os.path.basename(filepath))
    except Exception as e:
        flash(f'Error generating payslip: {str(e)}', 'danger')
        return redirect(url_for('employee.payroll'))
