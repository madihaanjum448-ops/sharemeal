from supabase import Client, create_client
from app.core.config import settings

auth_supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_ANON_KEY,
)