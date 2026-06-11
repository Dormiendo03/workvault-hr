"""
Create or update admin user with correct password hash
Run this script to fix login issues
"""

from werkzeug.security import generate_password_hash
from supabase import create_client
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get Supabase credentials
SUPABASE_URL = os.getenv('https://odqfkcfyvaammapfssma.supabase.co')
SUPABASE_KEY = os.getenv('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9kcWZrY2Z5dmFhbW1hcGZzc21hIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAxODkxODgsImV4cCI6MjA5NTc2NTE4OH0.oNnSwIqF1gqJtmPL9VOouB9Fw7uQLYUcPn1f1sNXbdg')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
    exit(1)

# Create Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Admin credentials
admin_email = "admin@workvault.com"
admin_password = "admin123"
admin_name = "System Administrator"

# Generate password hash
password_hash = generate_password_hash(admin_password)

print(f"Creating/updating admin user...")
print(f"Email: {admin_email}")
print(f"Password: {admin_password}")
print(f"Password Hash: {password_hash}")
print()

try:
    # Check if admin exists
    response = supabase.table('users').select('*').eq('email', admin_email).execute()
    
    if response.data and len(response.data) > 0:
        # Update existing admin
        print("Admin user exists. Updating password...")
        update_response = supabase.table('users').update({
            'password_hash': password_hash,
            'name': admin_name,
            'role': 'admin',
            'is_active': True
        }).eq('email', admin_email).execute()
        
        if update_response.data:
            print("✅ Admin password updated successfully!")
        else:
            print("❌ Failed to update admin password")
    else:
        # Create new admin
        print("Admin user doesn't exist. Creating...")
        from datetime import datetime
        
        insert_response = supabase.table('users').insert({
            'email': admin_email,
            'password_hash': password_hash,
            'name': admin_name,
            'role': 'admin',
            'leave_balance': 15,
            'is_active': True,
            'created_at': datetime.utcnow().isoformat()
        }).execute()
        
        if insert_response.data:
            print("✅ Admin user created successfully!")
        else:
            print("❌ Failed to create admin user")
    
    print()
    print("You can now login with:")
    print(f"  Email: {admin_email}")
    print(f"  Password: {admin_password}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print()
    print("Make sure:")
    print("1. Your .env file has correct SUPABASE_URL and SUPABASE_KEY")
    print("2. You've run database_schema.sql in Supabase")
    print("3. The 'users' table exists in Supabase")
