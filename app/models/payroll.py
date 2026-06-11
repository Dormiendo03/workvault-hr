from app.models.database import get_supabase
from datetime import datetime, timedelta, time
from dateutil import parser
from app.utils.ph_payroll_calculator import PHPayrollCalculator, calculate_late_minutes

class Payroll:
    """Payroll computation model"""
    
    def __init__(self, id, user_id, period_start, period_end, base_salary,
                 days_present, days_absent, days_on_leave, deductions,
                 net_pay, status='draft', generated_by=None, created_at=None,
                 overtime_pay=0, tardiness_deduction=0, undertime_deduction=0,
                 absent_deduction=0, sss_contribution=0, philhealth_contribution=0,
                 pagibig_contribution=0, withholding_tax=0, other_deductions=0,
                 gross_earnings=0, total_deductions=0, daily_rate=0, hourly_rate=0):
        self.id = id
        self.user_id = user_id
        self.period_start = period_start
        self.period_end = period_end
        self.base_salary = base_salary
        self.days_present = days_present
        self.days_absent = days_absent
        self.days_on_leave = days_on_leave
        self.deductions = deductions
        self.net_pay = net_pay
        self.status = status  # 'draft', 'finalized', 'paid'
        self.generated_by = generated_by
        self.created_at = created_at
        # Philippine payroll fields
        self.overtime_pay = overtime_pay
        self.tardiness_deduction = tardiness_deduction
        self.undertime_deduction = undertime_deduction
        self.absent_deduction = absent_deduction
        self.sss_contribution = sss_contribution
        self.philhealth_contribution = philhealth_contribution
        self.pagibig_contribution = pagibig_contribution
        self.withholding_tax = withholding_tax
        self.other_deductions = other_deductions
        self.gross_earnings = gross_earnings
        self.total_deductions = total_deductions
        self.daily_rate = daily_rate
        self.hourly_rate = hourly_rate
    
    @staticmethod
    def calculate_for_user(user_id, period_start, period_end, generated_by):
        """Calculate payroll for a user for a given period using Philippine payroll standards"""
        try:
            supabase = get_supabase()
            
            # Check if payroll already exists for this user and period
            existing_payroll = supabase.table('payroll').select('id')\
                .eq('user_id', user_id)\
                .eq('period_start', period_start)\
                .eq('period_end', period_end)\
                .execute()
            
            if existing_payroll.data and len(existing_payroll.data) > 0:
                return None, f"Payroll already exists for this period. Delete existing record first or choose a different period."
            
            # Get user details
            user_response = supabase.table('users').select('*').eq('id', user_id).execute()
            if not user_response.data or len(user_response.data) == 0:
                return None, "User not found"
            
            user = user_response.data[0]
            monthly_salary = user.get('salary', 0)
            
            if not monthly_salary:
                return None, "User salary not configured"
            
            # Initialize Philippine payroll calculator
            calculator = PHPayrollCalculator(monthly_salary)
            
            # Get attendance records for the period
            attendance_response = supabase.table('attendance').select('*')\
                .eq('user_id', user_id)\
                .gte('date', period_start)\
                .lte('date', period_end)\
                .execute()
            
            attendance_records = attendance_response.data
            
            # Calculate attendance metrics
            # IMPORTANT: Only count completed days (where employee has clocked out)
            # Days where employee is still clocked in are not counted until they clock out
            days_present = 0
            days_on_leave = 0
            total_late_minutes = 0
            total_undertime_hours = 0
            total_overtime_hours = 0
            
            standard_time_in = time(8, 0)  # 8:00 AM
            standard_time_out = time(17, 0)  # 5:00 PM
            
            for record in attendance_records:
                status = record.get('status', '')
                
                # Only count days where employee has clocked out (completed the day)
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
                    
                    # Calculate overtime (if clocked out after 5 PM)
                    try:
                        clock_out_time = parser.parse(record['clock_out']).time()
                        if clock_out_time > standard_time_out:
                            # Calculate overtime hours
                            today = datetime.today().date()
                            standard_dt = datetime.combine(today, standard_time_out)
                            actual_dt = datetime.combine(today, clock_out_time)
                            ot_hours = (actual_dt - standard_dt).total_seconds() / 3600
                            total_overtime_hours += ot_hours
                    except:
                        pass
                
                elif status == 'on_leave':
                    days_on_leave += 1
            
            # Calculate working days in period
            start = parser.parse(period_start).date()
            end = parser.parse(period_end).date()
            total_days = (end - start).days + 1
            working_days = sum(1 for i in range(total_days) 
                             if (start + timedelta(days=i)).weekday() < 5)  # Mon-Fri
            
            days_absent = working_days - days_present - days_on_leave
            
            # Calculate payroll using Philippine calculator
            payroll_result = calculator.calculate_semi_monthly_payroll(
                worked_days=days_present + days_on_leave,  # Leave days are paid
                late_minutes=total_late_minutes,
                undertime_hours=total_undertime_hours,
                absent_days=days_absent,
                ot_hours=total_overtime_hours,
                ot_type='regular',
                other_deductions=0
            )
            
            # Create payroll record with all Philippine payroll fields
            data = {
                'user_id': user_id,
                'period_start': period_start,
                'period_end': period_end,
                'base_salary': monthly_salary,
                'days_present': days_present,
                'days_absent': days_absent,
                'days_on_leave': days_on_leave,
                'deductions': round(payroll_result['total_deductions'], 2),
                'net_pay': round(payroll_result['net_pay'], 2),
                'status': 'draft',
                'generated_by': generated_by,
                'created_at': datetime.utcnow().isoformat(),
                # Philippine payroll fields
                'overtime_pay': round(payroll_result['overtime_pay'], 2),
                'tardiness_deduction': round(payroll_result['tardiness_deduction'], 2),
                'undertime_deduction': round(payroll_result['undertime_deduction'], 2),
                'absent_deduction': round(payroll_result['absent_deduction'], 2),
                'sss_contribution': round(payroll_result['sss_contribution'], 2),
                'philhealth_contribution': round(payroll_result['philhealth_contribution'], 2),
                'pagibig_contribution': round(payroll_result['pagibig_contribution'], 2),
                'withholding_tax': round(payroll_result['withholding_tax'], 2),
                'other_deductions': round(payroll_result['other_deductions'], 2),
                'gross_earnings': round(payroll_result['gross_earnings'], 2),
                'total_deductions': round(payroll_result['total_deductions'], 2),
                'daily_rate': round(payroll_result['daily_rate'], 2),
                'hourly_rate': round(payroll_result['hourly_rate'], 2)
            }
            
            response = supabase.table('payroll').insert(data).execute()
            
            if response.data and len(response.data) > 0:
                payroll_data = response.data[0]
                return Payroll(
                    id=payroll_data['id'],
                    user_id=payroll_data['user_id'],
                    period_start=payroll_data['period_start'],
                    period_end=payroll_data['period_end'],
                    base_salary=payroll_data['base_salary'],
                    days_present=payroll_data['days_present'],
                    days_absent=payroll_data['days_absent'],
                    days_on_leave=payroll_data['days_on_leave'],
                    deductions=payroll_data['deductions'],
                    net_pay=payroll_data.get('net_pay', payroll_data.get('net_salary', 0)),
                    status=payroll_data['status'],
                    generated_by=payroll_data.get('generated_by'),
                    created_at=payroll_data.get('created_at'),
                    overtime_pay=payroll_data.get('overtime_pay', 0),
                    tardiness_deduction=payroll_data.get('tardiness_deduction', 0),
                    undertime_deduction=payroll_data.get('undertime_deduction', 0),
                    absent_deduction=payroll_data.get('absent_deduction', 0),
                    sss_contribution=payroll_data.get('sss_contribution', 0),
                    philhealth_contribution=payroll_data.get('philhealth_contribution', 0),
                    pagibig_contribution=payroll_data.get('pagibig_contribution', 0),
                    withholding_tax=payroll_data.get('withholding_tax', 0),
                    other_deductions=payroll_data.get('other_deductions', 0),
                    gross_earnings=payroll_data.get('gross_earnings', 0),
                    total_deductions=payroll_data.get('total_deductions', 0),
                    daily_rate=payroll_data.get('daily_rate', 0),
                    hourly_rate=payroll_data.get('hourly_rate', 0)
                ), None
            
            return None, "Failed to create payroll record"
        except Exception as e:
            print(f"Error calculating payroll: {e}")
            import traceback
            traceback.print_exc()
            return None, str(e)
    
    @staticmethod
    def get_by_user(user_id):
        """Get all payroll records for a user"""
        try:
            supabase = get_supabase()
            response = supabase.table('payroll').select('*')\
                .eq('user_id', user_id)\
                .order('period_end', desc=True)\
                .execute()
            
            records = []
            for payroll_data in response.data:
                records.append(Payroll(
                    id=payroll_data['id'],
                    user_id=payroll_data['user_id'],
                    period_start=payroll_data['period_start'],
                    period_end=payroll_data['period_end'],
                    base_salary=payroll_data['base_salary'],
                    days_present=payroll_data['days_present'],
                    days_absent=payroll_data['days_absent'],
                    days_on_leave=payroll_data['days_on_leave'],
                    deductions=payroll_data['deductions'],
                    net_pay=payroll_data.get('net_pay', payroll_data.get('net_salary', 0)),
                    status=payroll_data['status'],
                    generated_by=payroll_data.get('generated_by'),
                    created_at=payroll_data.get('created_at'),
                    overtime_pay=payroll_data.get('overtime_pay', 0),
                    tardiness_deduction=payroll_data.get('tardiness_deduction', 0),
                    undertime_deduction=payroll_data.get('undertime_deduction', 0),
                    absent_deduction=payroll_data.get('absent_deduction', 0),
                    sss_contribution=payroll_data.get('sss_contribution', 0),
                    philhealth_contribution=payroll_data.get('philhealth_contribution', 0),
                    pagibig_contribution=payroll_data.get('pagibig_contribution', 0),
                    withholding_tax=payroll_data.get('withholding_tax', 0),
                    other_deductions=payroll_data.get('other_deductions', 0),
                    gross_earnings=payroll_data.get('gross_earnings', 0),
                    total_deductions=payroll_data.get('total_deductions', 0),
                    daily_rate=payroll_data.get('daily_rate', 0),
                    hourly_rate=payroll_data.get('hourly_rate', 0)
                ))
            
            return records
        except Exception as e:
            print(f"Error getting user payroll: {e}")
            return []
    
    @staticmethod
    def get_all(period_start=None, period_end=None):
        """Get all payroll records"""
        try:
            supabase = get_supabase()
            query = supabase.table('payroll').select('*, users!payroll_user_id_fkey(name, email, department)')
            
            if period_start:
                query = query.gte('period_start', period_start)
            if period_end:
                query = query.lte('period_end', period_end)
            
            response = query.order('period_end', desc=True).execute()
            return response.data
        except Exception as e:
            print(f"Error getting all payroll: {e}")
            return []
    
    def finalize(self):
        """Finalize payroll record (HR review complete, not yet released to employees)"""
        try:
            supabase = get_supabase()
            response = supabase.table('payroll').update({
                'status': 'finalized'
            }).eq('id', self.id).execute()
            
            if response.data and len(response.data) > 0:
                self.status = 'finalized'
                return True
            return False
        except Exception as e:
            print(f"Error finalizing payroll: {e}")
            return False
    
    def release(self):
        """Release/pay payroll (employees can now see and download it)"""
        try:
            supabase = get_supabase()
            response = supabase.table('payroll').update({
                'status': 'paid'
            }).eq('id', self.id).execute()
            
            if response.data and len(response.data) > 0:
                self.status = 'paid'
                return True
            return False
        except Exception as e:
            print(f"Error releasing payroll: {e}")
            return False
    
    @staticmethod
    def delete(payroll_id):
        """Delete a payroll record"""
        try:
            supabase = get_supabase()
            response = supabase.table('payroll').delete().eq('id', payroll_id).execute()
            return True, "Payroll record deleted successfully"
        except Exception as e:
            print(f"Error deleting payroll: {e}")
            return False, str(e)
