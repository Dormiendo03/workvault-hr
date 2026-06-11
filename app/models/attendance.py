from app.models.database import get_supabase
from datetime import datetime, date

class Attendance:
    """Attendance model for tracking employee clock in/out"""
    
    def __init__(self, id, user_id, date, time_in, time_out=None, 
                 status='present', created_at=None):
        self.id = id
        self.user_id = user_id
        self.date = date
        self.time_in = time_in
        self.time_out = time_out
        self.status = status  # 'present', 'late', 'absent', 'on_leave'
        self.created_at = created_at
    
    @staticmethod
    def clock_in(user_id, face_verified=True):
        """Record clock in for employee"""
        try:
            supabase = get_supabase()
            today = date.today().isoformat()
            now = datetime.now()
            now_time = now.time().isoformat()
            
            # Check if already clocked in today (after 6:00 AM)
            # Clock in resets at 6:00 AM every day
            # This allows employees to clock in fresh each day after 6 AM
            existing = supabase.table('attendance').select('*')\
                .eq('user_id', user_id)\
                .eq('date', today)\
                .execute()
            
            if existing.data and len(existing.data) > 0:
                # Check if the existing clock in is from today AFTER 6 AM
                existing_record = existing.data[0]
                if existing_record.get('clock_in'):
                    from dateutil import parser
                    clock_in_dt = parser.parse(existing_record['clock_in'])
                    
                    # Define 6 AM cutoff for today
                    from datetime import time as time_class
                    cutoff_time = datetime.combine(now.date(), time_class(6, 0, 0))
                    
                    # Only prevent clock in if the existing clock in is AFTER 6 AM today
                    # This allows fresh clock in after 6 AM even if there was a late checkout from previous day
                    if clock_in_dt >= cutoff_time:
                        return None, "Already clocked in today. You clocked in at {}.".format(
                            clock_in_dt.strftime('%I:%M %p')
                        )
            
            # Determine status (late if after 8:10 AM - 10 min grace period)
            status = 'late' if now.hour > 8 or (now.hour == 8 and now.minute > 10) else 'present'
            
            data = {
                'user_id': user_id,
                'date': today,
                'clock_in': now.isoformat(),
                'time_in': now_time,
                'status': status,
                'face_verified': face_verified,
                'created_at': datetime.utcnow().isoformat()
            }
            
            response = supabase.table('attendance').insert(data).execute()
            
            if response.data and len(response.data) > 0:
                att_data = response.data[0]
                return Attendance(
                    id=att_data['id'],
                    user_id=att_data['user_id'],
                    date=att_data['date'],
                    time_in=att_data['time_in'],
                    time_out=att_data.get('time_out'),
                    status=att_data['status'],
                    created_at=att_data.get('created_at')
                ), None
            
            return None, "Failed to record attendance"
        except Exception as e:
            print(f"Error clocking in: {e}")
            return None, str(e)
    
    @staticmethod
    def clock_out(user_id):
        """Record clock out for employee"""
        try:
            supabase = get_supabase()
            today = date.today().isoformat()
            now = datetime.now()
            now_time = now.time().isoformat()
            
            # Find today's attendance record
            response = supabase.table('attendance').select('*')\
                .eq('user_id', user_id)\
                .eq('date', today)\
                .execute()
            
            if not response.data or len(response.data) == 0:
                return None, "No clock-in record found for today"
            
            record = response.data[0]
            
            # Check both time_out and clock_out for backward compatibility
            if record.get('time_out') or record.get('clock_out'):
                return None, "Already clocked out today"
            
            # Update with both clock_out (timestamp) and time_out (time only) for compatibility
            update_response = supabase.table('attendance')\
                .update({
                    'clock_out': now.isoformat(),
                    'time_out': now_time
                })\
                .eq('id', record['id'])\
                .execute()
            
            if update_response.data and len(update_response.data) > 0:
                att_data = update_response.data[0]
                return Attendance(
                    id=att_data['id'],
                    user_id=att_data['user_id'],
                    date=att_data['date'],
                    time_in=att_data['time_in'],
                    time_out=att_data.get('time_out'),
                    status=att_data['status'],
                    created_at=att_data.get('created_at')
                ), None
            
            return None, "Failed to record clock out"
        except Exception as e:
            print(f"Error clocking out: {e}")
            return None, str(e)
    
    @staticmethod
    def get_by_user(user_id, start_date=None, end_date=None):
        """Get attendance records for a user"""
        try:
            supabase = get_supabase()
            query = supabase.table('attendance').select('*').eq('user_id', user_id)
            
            if start_date:
                query = query.gte('date', start_date)
            if end_date:
                query = query.lte('date', end_date)
            
            response = query.order('date', desc=True).execute()
            
            records = []
            for att_data in response.data:
                records.append(Attendance(
                    id=att_data['id'],
                    user_id=att_data['user_id'],
                    date=att_data['date'],
                    time_in=att_data['time_in'],
                    time_out=att_data.get('time_out'),
                    status=att_data['status'],
                    created_at=att_data.get('created_at')
                ))
            
            return records
        except Exception as e:
            print(f"Error getting attendance: {e}")
            return []
    
    @staticmethod
    def get_all(start_date=None, end_date=None):
        """Get all attendance records"""
        try:
            supabase = get_supabase()
            query = supabase.table('attendance').select('*, users!attendance_user_id_fkey(name, email, department)')
            
            if start_date:
                query = query.gte('date', start_date)
            if end_date:
                query = query.lte('date', end_date)
            
            response = query.order('date', desc=True).execute()
            return response.data
        except Exception as e:
            print(f"Error getting all attendance: {e}")
            return []
    
    @staticmethod
    def get_today_status(user_id):
        """Check if user has clocked in/out today"""
        try:
            supabase = get_supabase()
            today = date.today().isoformat()
            
            response = supabase.table('attendance').select('*')\
                .eq('user_id', user_id)\
                .eq('date', today)\
                .execute()
            
            if response.data and len(response.data) > 0:
                record = response.data[0]
                return {
                    'clocked_in': True,
                    'clocked_out': record.get('time_out') is not None,
                    'time_in': record.get('time_in'),
                    'time_out': record.get('time_out'),
                    'status': record.get('status')
                }
            
            return {
                'clocked_in': False,
                'clocked_out': False,
                'time_in': None,
                'time_out': None,
                'status': None
            }
        except Exception as e:
            print(f"Error getting today's status: {e}")
            return None
