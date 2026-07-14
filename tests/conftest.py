import os

import pytest

os.environ.setdefault("TIGER_PAY_CLIENT_SECRET", "test-tiger-pay-secret")
os.environ.setdefault("TIGER_PAY_CLIENT_ID", "test-client-id")
os.environ.setdefault("TIGER_PAY_API_HOST", "")
os.environ.setdefault("SUPABASE_URL", "https://placeholder.supabase.co")
os.environ.setdefault("SUPABASE_DB_URL", "https://placeholder.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("TIGER_PAY_MAX_BODY_BYTES", "5242880")
os.environ.setdefault("OPENAI_API_KEY", "placeholder")
os.environ.setdefault("SUPABASE_DB_HOST", "localhost")
os.environ.setdefault("SUPABASE_DB_PASSWORD", "placeholder")

from src.tiger_pay.config import get_tiger_pay_settings

get_tiger_pay_settings.cache_clear()

@pytest.fixture(autouse=True)
def reset_tiger_pay_caches():
    get_tiger_pay_settings.cache_clear()
    from src.tiger_pay.client import get_tiger_pay_supabase_client

    get_tiger_pay_supabase_client.cache_clear()
    yield
    get_tiger_pay_settings.cache_clear()
    get_tiger_pay_supabase_client.cache_clear()
