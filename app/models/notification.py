from app.models.database import get_supabase
from datetime import datetime

class Notification:
    """Notification model for user notifications"""
    
    def __init__(self, id, user_id, title, message, type='info', 
                 is_read=False, link=None, created_at=None, read_at=None):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.message = message
        self.type = type  # 'info', 'success', 'warning', 'error'
        self.is_read = is_read
        self.link = link
        self.created_at = created_at
        self.read_at = read_at
    
    @staticmethod
    def create(user_id, title, message, type='info', link=None):
        """Create a new notification"""
        try:
            supabase = get_supabase()
            
            data = {
                'user_id': user_id,
                'title': title,
                'message': message,
                'type': type,
                'is_read': False,
                'link': link,
                'created_at': datetime.utcnow().isoformat()
            }
            
            response = supabase.table('notifications').insert(data).execute()
            
            if response.data and len(response.data) > 0:
                notif_data = response.data[0]
                return Notification(
                    id=notif_data['id'],
                    user_id=notif_data['user_id'],
                    title=notif_data['title'],
                    message=notif_data['message'],
                    type=notif_data['type'],
                    is_read=notif_data['is_read'],
                    link=notif_data.get('link'),
                    created_at=notif_data.get('created_at'),
                    read_at=notif_data.get('read_at')
                ), None
            
            return None, "Failed to create notification"
        except Exception as e:
            print(f"Error creating notification: {e}")
            return None, str(e)
    
    @staticmethod
    def get_by_user(user_id, unread_only=False, limit=50):
        """Get notifications for a user"""
        try:
            supabase = get_supabase()
            query = supabase.table('notifications').select('*').eq('user_id', user_id)
            
            if unread_only:
                query = query.eq('is_read', False)
            
            response = query.order('created_at', desc=True).limit(limit).execute()
            
            notifications = []
            for notif_data in response.data:
                notifications.append(Notification(
                    id=notif_data['id'],
                    user_id=notif_data['user_id'],
                    title=notif_data['title'],
                    message=notif_data['message'],
                    type=notif_data['type'],
                    is_read=notif_data['is_read'],
                    link=notif_data.get('link'),
                    created_at=notif_data.get('created_at'),
                    read_at=notif_data.get('read_at')
                ))
            
            return notifications
        except Exception as e:
            print(f"Error getting notifications: {e}")
            return []
    
    @staticmethod
    def get_unread_count(user_id):
        """Get count of unread notifications for a user"""
        try:
            supabase = get_supabase()
            response = supabase.table('notifications')\
                .select('id', count='exact')\
                .eq('user_id', user_id)\
                .eq('is_read', False)\
                .execute()
            
            return response.count if hasattr(response, 'count') else 0
        except Exception as e:
            print(f"Error getting unread count: {e}")
            return 0
    
    @staticmethod
    def mark_as_read(notification_id, user_id):
        """Mark a notification as read"""
        try:
            supabase = get_supabase()
            
            response = supabase.table('notifications').update({
                'is_read': True,
                'read_at': datetime.utcnow().isoformat()
            }).eq('id', notification_id).eq('user_id', user_id).execute()
            
            return response.data and len(response.data) > 0, None
        except Exception as e:
            print(f"Error marking notification as read: {e}")
            return False, str(e)
    
    @staticmethod
    def mark_all_as_read(user_id):
        """Mark all notifications as read for a user"""
        try:
            supabase = get_supabase()
            
            response = supabase.table('notifications').update({
                'is_read': True,
                'read_at': datetime.utcnow().isoformat()
            }).eq('user_id', user_id).eq('is_read', False).execute()
            
            return True, None
        except Exception as e:
            print(f"Error marking all as read: {e}")
            return False, str(e)
    
    @staticmethod
    def delete_notification(notification_id, user_id):
        """Delete a notification"""
        try:
            supabase = get_supabase()
            
            response = supabase.table('notifications')\
                .delete()\
                .eq('id', notification_id)\
                .eq('user_id', user_id)\
                .execute()
            
            return True, None
        except Exception as e:
            print(f"Error deleting notification: {e}")
            return False, str(e)
    
    @staticmethod
    def delete_all_read(user_id):
        """Delete all read notifications for a user"""
        try:
            supabase = get_supabase()
            
            response = supabase.table('notifications')\
                .delete()\
                .eq('user_id', user_id)\
                .eq('is_read', True)\
                .execute()
            
            return True, None
        except Exception as e:
            print(f"Error deleting read notifications: {e}")
            return False, str(e)
    
    # Helper methods for creating specific notification types
    
    @staticmethod
    def notify_leave_approved(user_id, leave_type, start_date, end_date):
        """Notify user that their leave was approved"""
        return Notification.create(
            user_id=user_id,
            title="Leave Request Approved",
            message=f"Your {leave_type} leave from {start_date} to {end_date} has been approved.",
            type='success',
            link='/employee/leaves'
        )
    
    @staticmethod
    def notify_leave_rejected(user_id, leave_type, start_date, end_date):
        """Notify user that their leave was rejected"""
        return Notification.create(
            user_id=user_id,
            title="Leave Request Rejected",
            message=f"Your {leave_type} leave from {start_date} to {end_date} has been rejected.",
            type='error',
            link='/employee/leaves'
        )
    
    @staticmethod
    def notify_payroll_generated(user_id, period_start, period_end, amount):
        """Notify user that payroll was generated"""
        return Notification.create(
            user_id=user_id,
            title="Payroll Generated",
            message=f"Your payroll for {period_start} to {period_end} has been generated. Amount: ${amount:.2f}",
            type='success',
            link='/employee/payroll'
        )
    
    @staticmethod
    def notify_attendance_reminder(user_id):
        """Remind user to clock in"""
        return Notification.create(
            user_id=user_id,
            title="Attendance Reminder",
            message="Don't forget to clock in for today!",
            type='info',
            link='/employee/clock-in'
        )
    
    @staticmethod
    def notify_late_clock_in(user_id, time_in):
        """Notify user about late clock in"""
        return Notification.create(
            user_id=user_id,
            title="Late Clock In",
            message=f"You clocked in late at {time_in}. Please try to arrive on time.",
            type='warning',
            link='/employee/attendance'
        )
