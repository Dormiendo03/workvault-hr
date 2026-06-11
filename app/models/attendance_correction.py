from app.models.database import get_supabase
from datetime import datetime
from dateutil import parser

class AttendanceCorrection:
    """Attendance correction request model"""
    
    def __init__(self, id, user_id, attendance_date, correction_type,
                 current_clock_in=None, current_clock_out=None,
                 requested_clock_in=None, requested_clock_out=None,
                 reason=None, status='pending', reviewed_by=None,
                 reviewed_at=None, review_notes=None, created_at=None):
        self.id = id
        self.user_id = user_id
        self.attendance_date = attendance_date
        self.correction_type = correction_type
        self.current_clock_in = current_clock_in
        self.current_clock_out = current_clock_out
        self.requested_clock_in = requested_clock_in
        self.requested_clock_out = requested_clock_out
        self.reason = reason
        self.status = status
        self.reviewed_by = reviewed_by
        self.reviewed_at = reviewed_at
        self.review_notes = review_notes
        self.created_at = created_at
    
    @staticmethod
    def create(user_id, attendance_date, correction_type, reason,
               current_clock_in=None, current_clock_out=None,
               requested_clock_in=None, requested_clock_out=None):
        """Create a new attendance correction request"""
        try:
            supabase = get_supabase()
            
            data = {
                'user_id': user_id,
                'attendance_date': attendance_date,
                'correction_type': correction_type,
                'current_clock_in': current_clock_in,
                'current_clock_out': current_clock_out,
                'requested_clock_in': requested_clock_in,
                'requested_clock_out': requested_clock_out,
                'reason': reason,
                'status': 'pending',
                'created_at': datetime.utcnow().isoformat()
            }
            
            response = supabase.table('attendance_corrections').insert(data).execute()
            
            if response.data and len(response.data) > 0:
                return True, "Correction request submitted successfully"
            
            return False, "Failed to submit correction request"
        except Exception as e:
            print(f"Error creating attendance correction: {e}")
            return False, str(e)
    
    @staticmethod
    def get_by_user(user_id):
        """Get all correction requests for a user"""
        try:
            supabase = get_supabase()
            response = supabase.table('attendance_corrections').select('*')\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)\
                .execute()
            
            corrections = []
            for data in response.data:
                corrections.append(AttendanceCorrection(
                    id=data['id'],
                    user_id=data['user_id'],
                    attendance_date=data['attendance_date'],
                    correction_type=data['correction_type'],
                    current_clock_in=data.get('current_clock_in'),
                    current_clock_out=data.get('current_clock_out'),
                    requested_clock_in=data.get('requested_clock_in'),
                    requested_clock_out=data.get('requested_clock_out'),
                    reason=data.get('reason'),
                    status=data['status'],
                    reviewed_by=data.get('reviewed_by'),
                    reviewed_at=data.get('reviewed_at'),
                    review_notes=data.get('review_notes'),
                    created_at=data.get('created_at')
                ))
            
            return corrections
        except Exception as e:
            print(f"Error getting user corrections: {e}")
            return []
    
    @staticmethod
    def get_all(status=None):
        """Get all correction requests (for HR/Admin)"""
        try:
            supabase = get_supabase()
            query = supabase.table('attendance_corrections')\
                .select('*, users!attendance_corrections_user_id_fkey(name, email, department)')
            
            if status:
                query = query.eq('status', status)
            
            response = query.order('created_at', desc=True).execute()
            return response.data
        except Exception as e:
            print(f"Error getting all corrections: {e}")
            return []
    
    @staticmethod
    def approve(correction_id, reviewed_by_id, review_notes=None):
        """Approve a correction request and update attendance"""
        try:
            supabase = get_supabase()
            
            # Get the correction request
            correction_response = supabase.table('attendance_corrections')\
                .select('*').eq('id', correction_id).execute()
            
            if not correction_response.data:
                return False, "Correction request not found"
            
            correction = correction_response.data[0]
            
            print(f"Processing correction: {correction}")
            
            # Update or create attendance record
            from app.models.attendance import Attendance
            
            if correction['correction_type'] == 'missing_clock_out':
                # Update existing attendance with clock out time
                # Extract time from timestamp for time_out column
                requested_clock_out_dt = parser.parse(correction['requested_clock_out'])
                time_out_only = requested_clock_out_dt.time().isoformat()
                
                # Check if attendance record exists
                existing_attendance = supabase.table('attendance')\
                    .select('*')\
                    .eq('user_id', correction['user_id'])\
                    .eq('date', correction['attendance_date'])\
                    .execute()
                
                if existing_attendance.data and len(existing_attendance.data) > 0:
                    # Update existing record
                    attendance_response = supabase.table('attendance')\
                        .update({
                            'clock_out': correction['requested_clock_out'],
                            'time_out': time_out_only
                        })\
                        .eq('user_id', correction['user_id'])\
                        .eq('date', correction['attendance_date'])\
                        .execute()
                else:
                    # If no record exists, we can't add just clock out
                    return False, "No attendance record found for this date. Cannot add clock out without clock in."
            
            elif correction['correction_type'] == 'missing_day':
                # Create new attendance record
                # Extract time from timestamps for time_in and time_out columns
                requested_clock_in_dt = parser.parse(correction['requested_clock_in'])
                requested_clock_out_dt = parser.parse(correction['requested_clock_out'])
                time_in_only = requested_clock_in_dt.time().isoformat()
                time_out_only = requested_clock_out_dt.time().isoformat()
                
                # Check if record already exists (avoid duplicates)
                existing_attendance = supabase.table('attendance')\
                    .select('*')\
                    .eq('user_id', correction['user_id'])\
                    .eq('date', correction['attendance_date'])\
                    .execute()
                
                if existing_attendance.data and len(existing_attendance.data) > 0:
                    # Update existing record instead of creating duplicate
                    print(f"Attendance record already exists for {correction['attendance_date']}, updating instead")
                    attendance_response = supabase.table('attendance')\
                        .update({
                            'clock_in': correction['requested_clock_in'],
                            'clock_out': correction['requested_clock_out'],
                            'time_in': time_in_only,
                            'time_out': time_out_only,
                            'status': 'present'
                        })\
                        .eq('user_id', correction['user_id'])\
                        .eq('date', correction['attendance_date'])\
                        .execute()
                    print(f"Update response: {attendance_response.data}")
                else:
                    # Create new record
                    attendance_data = {
                        'user_id': correction['user_id'],
                        'date': correction['attendance_date'],
                        'clock_in': correction['requested_clock_in'],
                        'clock_out': correction['requested_clock_out'],
                        'time_in': time_in_only,
                        'time_out': time_out_only,
                        'status': 'present',
                        'created_at': datetime.utcnow().isoformat()
                    }
                    print(f"Creating new attendance record: {attendance_data}")
                    insert_response = supabase.table('attendance').insert(attendance_data).execute()
                    print(f"Insert response: {insert_response.data}")
            
            elif correction['correction_type'] == 'wrong_time':
                # Update existing attendance with corrected times
                # Extract time from timestamps for time_in and time_out columns
                requested_clock_in_dt = parser.parse(correction['requested_clock_in'])
                time_in_only = requested_clock_in_dt.time().isoformat()
                
                # Check if requested_clock_out exists
                time_out_only = None
                if correction['requested_clock_out']:
                    requested_clock_out_dt = parser.parse(correction['requested_clock_out'])
                    time_out_only = requested_clock_out_dt.time().isoformat()
                
                # Check if attendance record exists
                existing_attendance = supabase.table('attendance')\
                    .select('*')\
                    .eq('user_id', correction['user_id'])\
                    .eq('date', correction['attendance_date'])\
                    .execute()
                
                if existing_attendance.data and len(existing_attendance.data) > 0:
                    # Update existing record
                    update_data = {
                        'clock_in': correction['requested_clock_in'],
                        'time_in': time_in_only
                    }
                    
                    if correction['requested_clock_out']:
                        update_data['clock_out'] = correction['requested_clock_out']
                        update_data['time_out'] = time_out_only
                    
                    attendance_response = supabase.table('attendance')\
                        .update(update_data)\
                        .eq('user_id', correction['user_id'])\
                        .eq('date', correction['attendance_date'])\
                        .execute()
                else:
                    # Create new record if it doesn't exist
                    attendance_data = {
                        'user_id': correction['user_id'],
                        'date': correction['attendance_date'],
                        'clock_in': correction['requested_clock_in'],
                        'time_in': time_in_only,
                        'status': 'present',
                        'created_at': datetime.utcnow().isoformat()
                    }
                    
                    if correction['requested_clock_out']:
                        attendance_data['clock_out'] = correction['requested_clock_out']
                        attendance_data['time_out'] = time_out_only
                    
                    supabase.table('attendance').insert(attendance_data).execute()
            
            # Update correction request status
            update_response = supabase.table('attendance_corrections').update({
                'status': 'approved',
                'reviewed_by': reviewed_by_id,
                'reviewed_at': datetime.utcnow().isoformat(),
                'review_notes': review_notes
            }).eq('id', correction_id).execute()
            
            print(f"Correction status updated: {update_response.data}")
            
            # Create SEPARATE payroll record for the corrected day only
            # This keeps the original payroll record untouched (already paid)
            # and creates a new supplemental payroll for the correction
            should_create_payroll = False
            
            if correction['correction_type'] == 'missing_day':
                # Missing day adds a completed day (both clock in and clock out)
                should_create_payroll = True
            elif correction['correction_type'] == 'missing_clock_out':
                # Adding clock out completes an incomplete day
                should_create_payroll = True
            elif correction['correction_type'] == 'wrong_time':
                # If correction includes clock out, the day is completed
                if correction.get('requested_clock_out'):
                    should_create_payroll = True
            
            if should_create_payroll:
                try:
                    attendance_date = correction['attendance_date']
                    user_id = correction['user_id']
                    
                    print(f"Creating SEPARATE payroll record for corrected date: {attendance_date}")
                    
                    # Import here to avoid circular import
                    from app.utils.ph_payroll_calculator import PHPayrollCalculator
                    from app.models.user import User
                    
                    # Get user salary
                    user_data = supabase.table('users').select('salary, name').eq('id', user_id).execute()
                    if not user_data.data:
                        print("User not found, skipping payroll creation")
                    else:
                        monthly_salary = user_data.data[0].get('salary', 0)
                        user_name = user_data.data[0].get('name', 'Unknown')
                        calculator = PHPayrollCalculator(monthly_salary)
                        
                        # Get the corrected attendance record to calculate tardiness/OT
                        corrected_attendance = supabase.table('attendance')\
                            .select('*')\
                            .eq('user_id', user_id)\
                            .eq('date', attendance_date)\
                            .execute()
                        
                        if not corrected_attendance.data:
                            print(f"Warning: No attendance record found for corrected date {attendance_date}")
                        else:
                            att_record = corrected_attendance.data[0]
                            
                            # Calculate tardiness for this day
                            from app.utils.ph_payroll_calculator import calculate_late_minutes
                            from datetime import time
                            
                            late_minutes = 0
                            ot_hours = 0
                            standard_time_in = time(8, 0)
                            standard_time_out = time(17, 0)
                            
                            try:
                                if att_record.get('clock_in'):
                                    clock_in_time = parser.parse(att_record['clock_in']).time()
                                    late_minutes = calculate_late_minutes(standard_time_in, clock_in_time)
                                
                                if att_record.get('clock_out'):
                                    clock_out_time = parser.parse(att_record['clock_out']).time()
                                    if clock_out_time > standard_time_out:
                                        from datetime import datetime as dt
                                        today = dt.today().date()
                                        standard_dt = dt.combine(today, standard_time_out)
                                        actual_dt = dt.combine(today, clock_out_time)
                                        ot_hours = (actual_dt - standard_dt).total_seconds() / 3600
                            except:
                                pass
                            
                            # Calculate payroll for this single day
                            day_payroll = calculator.calculate_semi_monthly_payroll(
                                worked_days=1,  # Just this one corrected day
                                late_minutes=late_minutes,
                                undertime_hours=0,
                                absent_days=0,
                                ot_hours=ot_hours,
                                ot_type='regular',
                                other_deductions=0
                            )
                            
                            # Create a NEW separate payroll record for just this day
                            # This is a supplemental/adjustment payroll
                            # IMPORTANT: Match the exact schema from database_schema.sql
                            payroll_data = {
                                'user_id': user_id,
                                'period_start': attendance_date,  # Same date (1-day period)
                                'period_end': attendance_date,    # Same date (1-day period)
                                'base_salary': float(calculator.monthly_salary / 2),  # Semi-monthly salary
                                'days_present': 1,  # Just this one day
                                'days_absent': 0,
                                'days_on_leave': 0,  # Required field
                                'deductions': round(day_payroll['total_deductions'], 2),
                                'net_salary': round(day_payroll['net_pay'], 2),  # Base table uses net_salary, not net_pay
                                'status': 'draft',  # HR needs to finalize/release this
                                'created_at': datetime.utcnow().isoformat()
                            }
                            
                            # Add Philippine payroll fields if they exist in the table (from update_payroll_schema.sql)
                            try:
                                payroll_data.update({
                                    'overtime_pay': round(day_payroll.get('overtime_pay', 0), 2),
                                    'tardiness_deduction': round(day_payroll.get('tardiness_deduction', 0), 2),
                                    'undertime_deduction': round(day_payroll.get('undertime_deduction', 0), 2),
                                    'absent_deduction': round(day_payroll.get('absent_deduction', 0), 2),
                                    'sss_contribution': round(day_payroll.get('sss_contribution', 0), 2),
                                    'philhealth_contribution': round(day_payroll.get('philhealth_contribution', 0), 2),
                                    'pagibig_contribution': round(day_payroll.get('pagibig_contribution', 0), 2),
                                    'withholding_tax': round(day_payroll.get('withholding_tax', 0), 2),
                                    'other_deductions': round(day_payroll.get('other_deductions', 0), 2),
                                    'gross_earnings': round(day_payroll['gross_earnings'], 2),
                                    'total_deductions': round(day_payroll['total_deductions'], 2),
                                    'daily_rate': round(float(calculator.daily_rate), 2),
                                    'hourly_rate': round(float(calculator.hourly_rate), 2),
                                    'net_pay': round(day_payroll['net_pay'], 2)  # Include both net_salary and net_pay
                                })
                            except:
                                # If Philippine payroll fields don't exist, that's fine - use base schema only
                                pass
                            
                            # Insert the new payroll record
                            payroll_response = supabase.table('payroll').insert(payroll_data).execute()
                            
                            if payroll_response.data:
                                print(f"✅ SEPARATE payroll record created successfully!")
                                print(f"   Employee: {user_name}")
                                print(f"   Date: {attendance_date} (1 day only)")
                                print(f"   Days present: 1")
                                print(f"   Tardiness deduction: ₱{day_payroll.get('tardiness_deduction', 0):.2f}")
                                print(f"   Overtime pay: ₱{day_payroll.get('overtime_pay', 0):.2f}")
                                print(f"   Net pay: ₱{day_payroll['net_pay']:.2f}")
                                print(f"   Status: DRAFT (HR must finalize/release)")
                                print(f"   📝 This is a SEPARATE record, original payroll is UNCHANGED")
                            else:
                                print("Failed to create payroll record")
                        
                except Exception as payroll_error:
                    print(f"Error creating payroll: {payroll_error}")
                    import traceback
                    traceback.print_exc()
                    # Don't fail the approval if payroll creation fails
                    # The correction is still approved, payroll can be created manually
            
            return True, "Correction approved and attendance updated"
        except Exception as e:
            print(f"Error approving correction: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)
    
    @staticmethod
    def reject(correction_id, reviewed_by_id, review_notes):
        """Reject a correction request"""
        try:
            supabase = get_supabase()
            
            response = supabase.table('attendance_corrections').update({
                'status': 'rejected',
                'reviewed_by': reviewed_by_id,
                'reviewed_at': datetime.utcnow().isoformat(),
                'review_notes': review_notes
            }).eq('id', correction_id).execute()
            
            if response.data:
                return True, "Correction request rejected"
            
            return False, "Failed to reject correction request"
        except Exception as e:
            print(f"Error rejecting correction: {e}")
            return False, str(e)
