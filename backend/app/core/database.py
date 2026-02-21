"""
Database connections: Supabase client setup.
"""

from functools import lru_cache
from supabase import create_client, Client

from app.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    """Get the Supabase client (singleton).
    
    Uses the anon key for standard operations.
    Uses service_role key for admin operations (bypasses RLS).
    """
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


@lru_cache
def get_supabase_admin_client() -> Client:
    """Get the Supabase admin client (service_role key, bypasses RLS).
    
    Only use for operations that require elevated privileges.
    """
    settings = get_settings()
    if not settings.SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_SERVICE_KEY not configured")
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
