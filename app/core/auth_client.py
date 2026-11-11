
from supabase import Client, create_client

from app.core.config import (
    SUPABASE_URL,
    SUPABASE_ANON_KEY,
)

auth_supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_ANON_KEY,
)
