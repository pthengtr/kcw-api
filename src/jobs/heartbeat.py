import socket
from sqlalchemy import text


def upsert_worker_heartbeat(
    engine,
    worker_name: str,
    hostname: str | None = None,
    status: str = "idle",
    public_base_url: str | None = None,
) -> None:
    hostname = hostname or socket.gethostname()

    sql = text("""
        insert into ops.worker_heartbeat (
            worker_name,
            last_seen,
            hostname,
            status,
            public_base_url,
            updated_at
        )
        values (
            :worker_name,
            now(),
            :hostname,
            :status,
            :public_base_url,
            now()
        )
        on conflict (worker_name)
        do update set
            last_seen = now(),
            hostname = excluded.hostname,
            status = excluded.status,
            public_base_url = coalesce(excluded.public_base_url, ops.worker_heartbeat.public_base_url),
            updated_at = now()
    """)

    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "worker_name": worker_name,
                "hostname": hostname,
                "status": status,
                "public_base_url": (public_base_url or "").strip() or None,
            },
        )


def get_all_worker_status(engine, offline_after_seconds: int = 30) -> list[dict]:
    sql = text("""
        select
            worker_name,
            hostname,
            status as worker_state,
            public_base_url,
            last_seen,
            case
                when last_seen >= now() - (:offline_after_seconds || ' seconds')::interval
                    then 'online'
                else 'offline'
            end as online_status,
            extract(epoch from (now() - last_seen))::int as seconds_ago
        from ops.worker_heartbeat
        order by worker_name
    """)

    with engine.begin() as conn:
        rows = conn.execute(
            sql,
            {"offline_after_seconds": offline_after_seconds},
        ).mappings().all()

    return [dict(r) for r in rows]