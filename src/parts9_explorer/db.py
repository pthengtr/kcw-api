from __future__ import annotations

from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.db.mssql_host import pick_mssql_server
from src.parts9_explorer.config import get_explorer_settings

_engines: dict[str, Engine] = {}


def _odbc_url(server: str, database: str) -> str:
    settings = get_explorer_settings()
    picked = pick_mssql_server(server)
    odbc = (
        f"DRIVER={{{settings.pos_mssql_driver}}};"
        f"SERVER={picked};"
        f"DATABASE={database};"
        f"UID={settings.pos_mssql_username};"
        f"PWD={settings.pos_mssql_password};"
        "TrustServerCertificate=yes;"
        "Connection Timeout=8;"
    )
    return "mssql+pyodbc:///?odbc_connect=" + quote_plus(odbc)


def get_site_engine(site: str) -> Engine:
    key = (site or "hq").strip().lower()
    if key not in ("hq", "syp"):
        key = "hq"
    if key not in _engines:
        settings = get_explorer_settings()
        if key == "syp":
            url = _odbc_url(settings.parts9_syp_server, settings.parts9_syp_database)
        else:
            url = _odbc_url(settings.pos_mssql_server, settings.pos_mssql_database)
        _engines[key] = create_engine(
            url,
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=1,
            pool_timeout=8,
            connect_args={"timeout": 8},
        )
    return _engines[key]


def clear_explorer_engines() -> None:
    for eng in list(_engines.values()):
        try:
            eng.dispose()
        except Exception:
            pass
    _engines.clear()
