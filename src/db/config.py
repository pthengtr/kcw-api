from dotenv import load_dotenv
import os

load_dotenv()


def _env(name: str) -> str | None:
    """Read env and strip accidental leading/trailing whitespace (common paste mistake)."""
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


DB_HOST = _env("SUPABASE_DB_HOST")
DB_PORT = _env("SUPABASE_DB_PORT")
DB_NAME = _env("SUPABASE_DB_NAME")
DB_USER = _env("SUPABASE_DB_USER")
DB_PASSWORD = _env("SUPABASE_DB_PASSWORD")

DATABASE_URL = (
    "postgresql+psycopg://"
    f"{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)