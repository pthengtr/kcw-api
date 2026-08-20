from __future__ import annotations

import threading
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.db.mssql_host import pick_mssql_server, tcp_open
from src.parts9_explorer.config import get_explorer_settings

_engines: dict[str, Engine] = {}
_engines_lock = threading.Lock()


def site_sql_host(site: str) -> str:
    settings = get_explorer_settings()
    key = (site or "hq").strip().lower()
    if key == "syp":
        return (settings.parts9_syp_server or "kss-pc").split(",")[0].strip() or "kss-pc"
    return (settings.pos_mssql_server or "KSS").split(",")[0].strip() or "KSS"


def format_sql_error(exc: BaseException, *, site: str) -> str:
    """Short operator-facing SQL error. Do not dump pyodbc HYT00 on the page."""
    text = str(exc)
    host = site_sql_host(site)
    lowered = text.lower()
    timeout = (
        "HYT00" in text
        or "login timeout" in lowered
        or "not reachable" in lowered
        or "timed out" in lowered
        or "timeout expired" in lowered
    )
    if timeout:
        return f"{site.upper()} SQL ไม่เชื่อมต่อ ({host} ปิดหรือเครือข่ายไม่ถึง)"
    if len(text) > 160:
        text = text[:157] + "..."
    return f"{site.upper()} SQL: {text}"


def _odbc_url(server: str, database: str) -> str:
    settings = get_explorer_settings()
    picked = pick_mssql_server(server)
    if not tcp_open(picked):
        raise ConnectionError("SQL Server port 1433 not reachable on %s" % picked)
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
    with _engines_lock:
        existing = _engines.get(key)
        if existing is not None:
            return existing
    settings = get_explorer_settings()
    if key == "syp":
        url = _odbc_url(settings.parts9_syp_server, settings.parts9_syp_database)
    else:
        url = _odbc_url(settings.pos_mssql_server, settings.pos_mssql_database)
    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=1,
        pool_timeout=8,
        connect_args={"timeout": 8},
    )
    with _engines_lock:
        existing = _engines.get(key)
        if existing is not None:
            try:
                engine.dispose()
            except Exception:
                pass
            return existing
        _engines[key] = engine
        return engine


def clear_explorer_engines() -> None:
    with _engines_lock:
        engines = list(_engines.values())
        _engines.clear()
    for eng in engines:
        try:
            eng.dispose()
        except Exception:
            pass
