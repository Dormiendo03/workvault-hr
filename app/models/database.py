from supabase import create_client, Client
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
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        print(f"[DATABASE] Initializing Supabase client...")
        print(f"[DATABASE] URL: {url}")
        
        try:
            # Use positional arguments only - most compatible
            _supabase_client = create_client(url, key)
            print(f"[DATABASE] Supabase client initialized successfully!")
        except Exception as e:
            print(f"[DATABASE ERROR] Failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    return _supabase_client
