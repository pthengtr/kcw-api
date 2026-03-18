from src.jobs.queue import enqueue_job
from sqlalchemy import text


def get_worker_status(engine, worker_name: str, threshold_seconds: int = 120) -> dict:
    sql = text("""
        select
            max(coalesce(finished_at, started_at)) as last_seen
        from ops.job_queue
        where worker_name = :worker_name
    """)

    with engine.begin() as conn:
        row = conn.execute(sql, {"worker_name": worker_name}).mappings().first()

    last_seen = row["last_seen"]

    if not last_seen:
        return {
            "worker_name": worker_name,
            "status": "offline",
            "last_seen": None,
        }

    # compute online in python
    sql2 = text("select now()")
    with engine.begin() as conn:
        now = conn.execute(sql2).scalar()

    delta = (now - last_seen).total_seconds()

    status = "online" if delta <= threshold_seconds else "offline"

    return {
        "worker_name": worker_name,
        "status": status,
        "last_seen": last_seen,
        "seconds_ago": int(delta),
    }

def get_all_worker_status(engine) -> list[dict]:
    workers = ["HQ-PC", "SYP-PC"]

    result = []

    for w in workers:
        result.append(get_worker_status(engine, w))

    return result

def enqueue_sync_inventory_jobs(
    engine,
    requested_by: str | None = None,
    source: str | None = None,
) -> list[dict]:
    jobs = []

    targets = [
        {"site": "HQ", "worker_name": "HQ-PC"},
        {"site": "SYP", "worker_name": "SYP-PC"},
    ]

    for target in targets:
        job = enqueue_job(
            engine=engine,
            job_type="sync_inventory",
            payload={"site": target["site"]},
            worker_name=target["worker_name"],
            requested_by=requested_by,
            source=source,
        )
        jobs.append(job)

    return jobs