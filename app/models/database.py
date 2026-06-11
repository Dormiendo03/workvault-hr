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
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        # Simple client creation - compatible with all Supabase versions
        _supabase_client = create_client(url, key)
    
    return _supabase_client
