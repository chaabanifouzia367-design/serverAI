"""
Supabase Configuration

Supabase client initialization and management.
"""
from supabase import create_client, Client
import logging

logger = logging.getLogger(__name__)

# Global client instance
_supabase_client: Client = None


def init_supabase(config) -> Client:
    """
    Initialize Supabase client.
    
    Args:
        config: Config object with SUPABASE_URL and SUPABASE_KEY
        
    Returns:
        Supabase client instance
        
    Raises:
        ValueError: If credentials are missing
        Exception: If initialization fails
    """
    global _supabase_client
    
    try:
        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            raise ValueError("Missing Supabase credentials in environment")
        
        _supabase_client = create_client(
            config.SUPABASE_URL,
            config.SUPABASE_KEY
        )
        
        logger.info("✅ Supabase client initialized successfully")
        return _supabase_client
        
    except Exception as e:
        logger.error(f"❌ Supabase initialization failed: {e}")
        raise


def get_supabase() -> Client:
    """
    Get Supabase client instance.
    
    Returns:
        Supabase client
        
    Raises:
        RuntimeError: If client not initialized
    """
    if _supabase_client is None:
        raise RuntimeError("Supabase not initialized. Call init_supabase() first.")
    return _supabase_client
