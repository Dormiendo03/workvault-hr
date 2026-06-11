from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.database import get_supabase
from datetime import datetime

class User(UserMixin):
    """User model for authentication and authorization"""
    
    def __init__(self, id, email, name, role, department=None, salary=None, 
                 leave_balance=None, active=True, created_at=None):
        self.id = id
        self.email = email
        self.name = name
        self.role = role  # 'admin', 'hr', 'employee'
        self.department = department
        self.salary = salary
        self.leave_balance = leave_balance or 15  # Default 15 days
        self._active = active  # Use _active internally
        self.created_at = created_at
    
    @property
    def is_active(self):
        """Flask-Login requires is_active property"""
        return self._active
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID"""
        try:
            supabase = get_supabase()
            response = supabase.table('users').select('*').eq('id', user_id).execute()
            
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                return User(
                    id=user_data['id'],
                    email=user_data['email'],
                    name=user_data['name'],
                    role=user_data['role'],
                    department=user_data.get('department'),
                    salary=user_data.get('salary'),
                    leave_balance=user_data.get('leave_balance', 15),
                    active=user_data.get('is_active', True),
                    created_at=user_data.get('created_at')
                )
            return None
        except Exception as e:
            print(f"Error getting user by ID: {e}")
            return None
    
    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        try:
            supabase = get_supabase()
            response = supabase.table('users').select('*').eq('email', email).execute()
            
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                return User(
                    id=user_data['id'],
                    email=user_data['email'],
                    name=user_data['name'],
                    role=user_data['role'],
                    department=user_data.get('department'),
                    salary=user_data.get('salary'),
                    leave_balance=user_data.get('leave_balance', 15),
                    active=user_data.get('is_active', True),
                    created_at=user_data.get('created_at')
                )
            return None
        except Exception as e:
            print(f"Error getting user by email: {e}")
            return None
    
    @staticmethod
    def authenticate(email, password):
        """Authenticate user with email and password"""
        try:
            supabase = get_supabase()
            response = supabase.table('users').select('*').eq('email', email).execute()
            
            print(f"[AUTH DEBUG] Attempting login for: {email}")
            
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                stored_hash = user_data['password_hash']
                
                print(f"[AUTH DEBUG] User found in database")
                print(f"[AUTH DEBUG] Stored hash starts with: {stored_hash[:20]}...")
                print(f"[AUTH DEBUG] Password provided: {password}")
                
                # Try to verify password
                try:
                    password_valid = check_password_hash(stored_hash, password)
                    print(f"[AUTH DEBUG] Password check result: {password_valid}")
                except Exception as hash_error:
                    print(f"[AUTH DEBUG] Password check error: {hash_error}")
                    password_valid = False
                
                if password_valid:
                    print(f"[AUTH DEBUG] Authentication successful!")
                    return User(
                        id=user_data['id'],
                        email=user_data['email'],
                        name=user_data['name'],
                        role=user_data['role'],
                        department=user_data.get('department'),
                        salary=user_data.get('salary'),
                        leave_balance=user_data.get('leave_balance', 15),
                        active=user_data.get('is_active', True),
                        created_at=user_data.get('created_at')
                    )
                else:
                    print(f"[AUTH DEBUG] Password verification failed")
            else:
                print(f"[AUTH DEBUG] No user found with email: {email}")
            
            return None
        except Exception as e:
            print(f"[AUTH DEBUG] Error authenticating user: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def create(email, password, name, role, department=None, salary=None):
        """Create a new user"""
        try:
            supabase = get_supabase()
            
            if not supabase:
                print("[USER CREATE ERROR] Supabase client is None")
                return None
            
            password_hash = generate_password_hash(password)
            print(f"[USER CREATE] Generated password hash for {email}")
            
            data = {
                'email': email,
                'password_hash': password_hash,
                'name': name,
                'role': role,
                'department': department,
                'salary': salary,
                'leave_balance': 15,
                'is_active': True,
                'created_at': datetime.utcnow().isoformat()
            }
            
            print(f"[USER CREATE] Inserting data: {data}")
            response = supabase.table('users').insert(data).execute()
            print(f"[USER CREATE] Response: {response}")
            
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                print(f"[USER CREATE] User created successfully: {user_data['id']}")
                return User(
                    id=user_data['id'],
                    email=user_data['email'],
                    name=user_data['name'],
                    role=user_data['role'],
                    department=user_data.get('department'),
                    salary=user_data.get('salary'),
                    leave_balance=user_data.get('leave_balance', 15),
                    active=user_data.get('is_active', True),
                    created_at=user_data.get('created_at')
                )
            else:
                print(f"[USER CREATE ERROR] No data in response or empty response")
            return None
        except Exception as e:
            print(f"[USER CREATE ERROR] Exception: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def get_all(role=None):
        """Get all users, optionally filtered by role"""
        try:
            supabase = get_supabase()
            query = supabase.table('users').select('*')
            
            if role:
                query = query.eq('role', role)
            
            response = query.execute()
            
            users = []
            for user_data in response.data:
                users.append(User(
                    id=user_data['id'],
                    email=user_data['email'],
                    name=user_data['name'],
                    role=user_data['role'],
                    department=user_data.get('department'),
                    salary=user_data.get('salary'),
                    leave_balance=user_data.get('leave_balance', 15),
                    active=user_data.get('is_active', True),
                    created_at=user_data.get('created_at')
                ))
            
            return users
        except Exception as e:
            print(f"Error getting all users: {e}")
            return []
    
    def update(self, **kwargs):
        """Update user fields"""
        try:
            supabase = get_supabase()
            response = supabase.table('users').update(kwargs).eq('id', self.id).execute()
            
            if response.data and len(response.data) > 0:
                # Update instance attributes
                for key, value in kwargs.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
                return True
            return False
        except Exception as e:
            print(f"Error updating user: {e}")
            return False
    
    def has_role(self, *roles):
        """Check if user has any of the specified roles"""
        return self.role in roles
