from pathlib import Path
import urllib.request
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv(Path(".env"), override=True)
from src.db import get_engine

for path in ("/stock-check/api/health", "/health"):
    try:
        body = urllib.request.urlopen(f"http://127.0.0.1:8787{path}", timeout=10).read().decode()
        print(path, body)
    except Exception as exc:  # noqa: BLE001
        print(path, "ERR", exc)

eng = get_engine()
with eng.connect() as conn:
    row = conn.execute(
        text(
            """
            select worker_name, status, public_base_url,
                   extract(epoch from (now() - last_seen))::int as seconds_ago
            from ops.worker_heartbeat
            where worker_name = 'HQ-PC'
            """
        )
    ).mappings().first()
    print("heartbeat", dict(row) if row else None)
