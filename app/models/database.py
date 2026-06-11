from supabase import create_client, Client
from flask import current_app
import os

_supabase_client = None

def get_supabase() -> Client:
    """Get or create Supabase client"""
    global _supabase_client
    
    if _supabase_client is None:
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        
        if not url or not key:
            print(f"[DATABASE ERROR] Missing environment variables!")
            print(f"[DATABASE ERROR] SUPABASE_URL: {'SET' if url else 'NOT SET'}")
            print(f"[DATABASE ERROR] SUPABASE_KEY: {'SET' if key else 'NOT SET'}")
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        print(f"[DATABASE] Initializing Supabase client...")
        print(f"[DATABASE] URL: {url}")
        print(f"[DATABASE] Key length: {len(key)} characters")
        
        try:
            # Create client with only required parameters for v2.3.4 compatibility
            _supabase_client = create_client(
                supabase_url=url,
                supabase_key=key
            )
            print(f"[DATABASE] Supabase client initialized successfully!")
        except Exception as e:
            print(f"[DATABASE ERROR] Failed to create Supabase client: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    return _supabase_client
