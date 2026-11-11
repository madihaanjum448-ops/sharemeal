
from supabase import Client, create_client

from app.core.config import (
    SUPABASE_URL,
    SUPABASE_KEY,
    validate_settings,
)

validate_settings()

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


def get_supabase() -> Client:
    """Return the shared Supabase client."""
    return supabase
