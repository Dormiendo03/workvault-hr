from app.models.database import get_supabase
from datetime import datetime

class Leave:
    """Leave management model"""
    
    def __init__(self, id, user_id, leave_type, start_date, end_date, 
                 days_count, reason, status='pending', approved_by=None, 
                 approved_at=None, created_at=None):
        self.id = id
        self.user_id = user_id
        self.leave_type = leave_type  # 'sick', 'vacation', 'personal', 'emergency'
        self.start_date = start_date
        self.end_date = end_date
        self.days_count = days_count
        self.reason = reason
        self.status = status  # 'pending', 'approved', 'rejected'
        self.approved_by = approved_by
        self.approved_at = approved_at
        self.created_at = created_at
    
    @staticmethod
    def create(user_id, leave_type, start_date, end_date, days_count, reason):
        """Create a new leave request"""
        try:
            supabase = get_supabase()
            
            data = {
                'user_id': user_id,
                'leave_type': leave_type,
                'start_date': start_date,
                'end_date': end_date,
                'days_count': days_count,
                'reason': reason,
                'status': 'pending',
                'created_at': datetime.utcnow().isoformat()
            }
            
            response = supabase.table('leaves').insert(data).execute()
            
            if response.data and len(response.data) > 0:
                leave_data = response.data[0]
                
                # Create notification for HR/Admin
                try:
                    from app.models.notification import Notification
                    
                    # Get user name for notification
                    user_response = supabase.table('users').select('name').eq('id', user_id).execute()
                    user_name = user_response.data[0]['name'] if user_response.data else 'Employee'
                    
                    # Get all HR and Admin users
                    hr_admin_response = supabase.table('users').select('id')\
                        .in_('role', ['hr', 'admin'])\
                        .execute()
                    
                    # Create notification for each HR/Admin
                    for hr_user in hr_admin_response.data:
                        Notification.create(
                            user_id=hr_user['id'],
                            type='leave_request',
                            title='New Leave Request',
                            message=f'{user_name} requested {leave_type} leave from {start_date} to {end_date} ({days_count} days)',
                            related_id=leave_data['id']
                        )
                except Exception as notif_error:
                    print(f"Error creating leave notification: {notif_error}")
                    # Don't fail the leave creation if notification fails
                
                return Leave(
                    id=leave_data['id'],
                    user_id=leave_data['user_id'],
                    leave_type=leave_data['leave_type'],
                    start_date=leave_data['start_date'],
                    end_date=leave_data['end_date'],
                    days_count=leave_data['days_count'],
                    reason=leave_data['reason'],
                    status=leave_data['status'],
                    approved_by=leave_data.get('approved_by'),
                    approved_at=leave_data.get('approved_at'),
                    created_at=leave_data.get('created_at')
                ), None
            
            return None, "Failed to create leave request"
        except Exception as e:
            print(f"Error creating leave: {e}")
            return None, str(e)
    
    @staticmethod
    def get_by_id(leave_id):
        """Get leave by ID"""
        try:
            supabase = get_supabase()
            response = supabase.table('leaves').select('*').eq('id', leave_id).execute()
            
            if response.data and len(response.data) > 0:
                leave_data = response.data[0]
                return Leave(
                    id=leave_data['id'],
                    user_id=leave_data['user_id'],
                    leave_type=leave_data['leave_type'],
                    start_date=leave_data['start_date'],
                    end_date=leave_data['end_date'],
                    days_count=leave_data['days_count'],
                    reason=leave_data['reason'],
                    status=leave_data['status'],
                    approved_by=leave_data.get('approved_by'),
                    approved_at=leave_data.get('approved_at'),
                    created_at=leave_data.get('created_at')
                )
            return None
        except Exception as e:
            print(f"Error getting leave: {e}")
            return None
    
    @staticmethod
    def get_by_user(user_id):
        """Get all leave requests for a user"""
        try:
            supabase = get_supabase()
            response = supabase.table('leaves').select('*')\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)\
                .execute()
            
            leaves = []
            for leave_data in response.data:
                leaves.append(Leave(
                    id=leave_data['id'],
                    user_id=leave_data['user_id'],
                    leave_type=leave_data['leave_type'],
                    start_date=leave_data['start_date'],
                    end_date=leave_data['end_date'],
                    days_count=leave_data['days_count'],
                    reason=leave_data['reason'],
                    status=leave_data['status'],
                    approved_by=leave_data.get('approved_by'),
                    approved_at=leave_data.get('approved_at'),
                    created_at=leave_data.get('created_at')
                ))
            
            return leaves
        except Exception as e:
            print(f"Error getting user leaves: {e}")
            return []
    
    @staticmethod
    def get_all(status=None):
        """Get all leave requests, optionally filtered by status"""
        try:
            supabase = get_supabase()
            # Specify which relationship to use for the join
            query = supabase.table('leaves').select('*, users!leaves_user_id_fkey(name, email, department)')
            
            if status:
                query = query.eq('status', status)
            
            response = query.order('created_at', desc=True).execute()
            return response.data
        except Exception as e:
            print(f"Error getting all leaves: {e}")
            return []
    
    def approve(self, approved_by_id):
        """Approve leave request"""
        try:
            supabase = get_supabase()
            
            # Update leave status
            response = supabase.table('leaves').update({
                'status': 'approved',
                'approved_by': approved_by_id,
                'approved_at': datetime.utcnow().isoformat()
            }).eq('id', self.id).execute()
            
            if response.data and len(response.data) > 0:
                # Update user's leave balance
                user_response = supabase.table('users').select('leave_balance')\
                    .eq('id', self.user_id).execute()
                
                if user_response.data and len(user_response.data) > 0:
                    current_balance = user_response.data[0]['leave_balance']
                    new_balance = max(0, current_balance - self.days_count)
                    
                    supabase.table('users').update({
                        'leave_balance': new_balance
                    }).eq('id', self.user_id).execute()
                
                # Create notification for employee
                try:
                    from app.models.notification import Notification
                    Notification.create(
                        user_id=self.user_id,
                        type='leave_approved',
                        title='Leave Request Approved',
                        message=f'Your {self.leave_type} leave request from {self.start_date} to {self.end_date} has been approved',
                        related_id=self.id
                    )
                except Exception as notif_error:
                    print(f"Error creating approval notification: {notif_error}")
                
                self.status = 'approved'
                self.approved_by = approved_by_id
                self.approved_at = datetime.utcnow().isoformat()
                return True, "Leave approved successfully"
            
            return False, "Failed to approve leave"
        except Exception as e:
            print(f"Error approving leave: {e}")
            return False, str(e)
    
    def reject(self, approved_by_id):
        """Reject leave request"""
        try:
            supabase = get_supabase()
            
            response = supabase.table('leaves').update({
                'status': 'rejected',
                'approved_by': approved_by_id,
                'approved_at': datetime.utcnow().isoformat()
            }).eq('id', self.id).execute()
            
            if response.data and len(response.data) > 0:
                # Create notification for employee
                try:
                    from app.models.notification import Notification
                    Notification.create(
                        user_id=self.user_id,
                        type='leave_rejected',
                        title='Leave Request Rejected',
                        message=f'Your {self.leave_type} leave request from {self.start_date} to {self.end_date} has been rejected',
                        related_id=self.id
                    )
                except Exception as notif_error:
                    print(f"Error creating rejection notification: {notif_error}")
                
                self.status = 'rejected'
                self.approved_by = approved_by_id
                self.approved_at = datetime.utcnow().isoformat()
                return True, "Leave rejected"
            
            return False, "Failed to reject leave"
        except Exception as e:
            print(f"Error rejecting leave: {e}")
            return False, str(e)
