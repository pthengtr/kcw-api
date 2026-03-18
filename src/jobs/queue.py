import json
from sqlalchemy import text


def enqueue_job(
    engine,
    job_type: str,
    payload: dict | None = None,
    worker_name: str | None = None,   # ⭐ ADD THIS
    requested_by: str | None = None,
    source: str | None = None,
) -> dict:
    payload = payload or {}

    sql = text("""
        insert into ops.job_queue (
            job_type,
            payload,
            status,
            worker_name,
            requested_by,
            source
        )
        values (
            :job_type,
            cast(:payload as jsonb),
            'pending',
            :worker_name,
            :requested_by,
            :source
        )
        returning
            id,
            job_type,
            payload,
            status,
            requested_by,
            source,
            requested_at
    """)

    with engine.begin() as conn:
        row = conn.execute(
            sql,
            {
                "job_type": job_type,
                "payload": json.dumps(payload),
                "worker_name": worker_name,
                "requested_by": requested_by,
                "source": source,
            },
        ).mappings().first()

    return dict(row)


def claim_next_job(engine, worker_name: str) -> dict | None:
    sql = text("""
        with next_job as (
            select id
            from ops.job_queue
            where status = 'pending'
            and (worker_name is null or worker_name = :worker_name)
            order by requested_at
            for update skip locked
            limit 1
        )
        update ops.job_queue q
        set
            status = 'running',
            started_at = now(),
            worker_name = :worker_name
        from next_job
        where q.id = next_job.id
        returning q.*;
    """)

    with engine.begin() as conn:
        row = conn.execute(sql, {"worker_name": worker_name}).mappings().first()

    return dict(row) if row else None


def finish_job_success(engine, job_id: int, result_message: str | None = None):
    sql = text("""
        update ops.job_queue
        set
            status = 'done',
            finished_at = now(),
            result_message = :result_message,
            error_message = null
        where id = :job_id
    """)

    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "job_id": job_id,
                "result_message": result_message,
            },
        )


def finish_job_failed(engine, job_id: int, error_message: str):
    sql = text("""
        update ops.job_queue
        set
            status = 'failed',
            finished_at = now(),
            error_message = :error_message
        where id = :job_id
    """)

    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "job_id": job_id,
                "error_message": error_message[:4000],
            },
        )


def get_job_by_id(engine, job_id: int) -> dict | None:
    sql = text("""
        select
            id,
            job_type,
            payload,
            status,
            requested_by,
            source,
            requested_at,
            started_at,
            finished_at,
            worker_name,
            result_message,
            error_message
        from ops.job_queue
        where id = :job_id
    """)

    with engine.begin() as conn:
        row = conn.execute(sql, {"job_id": job_id}).mappings().first()

    return dict(row) if row else None