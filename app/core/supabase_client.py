from supabase import Client, create_client
from app.core.config import settings

# Validate settings at startup
settings.validate()

supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_KEY
)

def get_supabase() -> Client:
    """Return the shared Supabase client."""
    return supabase