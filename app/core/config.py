
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
        self.SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
        self.SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()
        self.HANDSHAKE_SECRET = os.getenv("HANDSHAKE_SECRET", "").strip()

        self.OTP_RATE_LIMIT_WINDOW_SECONDS = int(
            os.getenv("OTP_RATE_LIMIT_WINDOW_SECONDS", "300")
        )
        self.OTP_MAX_SENDS_PER_WINDOW = int(
            os.getenv("OTP_MAX_SENDS_PER_WINDOW", "3")
        )
        self.EXPIRY_SWEEP_INTERVAL_SECONDS = int(
            os.getenv("EXPIRY_SWEEP_INTERVAL_SECONDS", "60")
        )

    def validate(self):
        required = {
            "SUPABASE_URL": self.SUPABASE_URL,
            "SUPABASE_KEY": self.SUPABASE_KEY,
            "SUPABASE_ANON_KEY": self.SUPABASE_ANON_KEY,
            "HANDSHAKE_SECRET": self.HANDSHAKE_SECRET,
        }

        missing = [name for name, value in required.items() if not value]

        if missing:
            raise RuntimeError(
                "Missing required environment variables: "
                + ", ".join(missing)
            )

        if not self.SUPABASE_URL.startswith("https://"):
            raise RuntimeError("SUPABASE_URL must be an HTTPS URL")

        secret = self.HANDSHAKE_SECRET

        if len(secret) < 32 or not secret.isascii():
            raise RuntimeError(
                "HANDSHAKE_SECRET must be at least 32 ASCII characters"
            )

        if secret.lower() in {
            "change-me",
            "your-secret-here",
            "replace-this-secret",
        }:
            raise RuntimeError("HANDSHAKE_SECRET cannot be a placeholder")

        if self.EXPIRY_SWEEP_INTERVAL_SECONDS < 15:
            raise RuntimeError(
                "EXPIRY_SWEEP_INTERVAL_SECONDS must be at least 15"
            )


settings = Settings()
