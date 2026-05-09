import json
from sqlalchemy import text


def enqueue_job(
    engine,
    job_type: str,
    payload: dict | None = None,
    worker_name: str | None = None,
    requested_by: str | None = None,
    source: str | None = None,
    batch_id: str | None = None,
) -> dict:
    payload = payload or {}

    if batch_id:
        payload = {
            **payload,
            "batch_id": batch_id,
        }

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
            worker_name,
            requested_by,
            source,
            payload ->> 'batch_id' as batch_id,
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
            worker_name = :worker_name,
            result_message = null,
            error_message = null
        from next_job
        where q.id = next_job.id
        returning
            q.id,
            q.job_type,
            q.payload,
            q.status,
            q.worker_name,
            q.requested_by,
            q.source,
            q.payload ->> 'batch_id' as batch_id,
            q.requested_at,
            q.started_at
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
            payload ->> 'batch_id' as batch_id,
            result_message,
            error_message
        from ops.job_queue
        where id = :job_id
    """)

    with engine.begin() as conn:
        row = conn.execute(sql, {"job_id": job_id}).mappings().first()

    return dict(row) if row else None


def get_jobs_by_batch_id(engine, batch_id: str, limit: int = 12) -> list[dict]:
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
            payload ->> 'batch_id' as batch_id,
            result_message,
            error_message
        from ops.job_queue
        where payload ->> 'batch_id' = :batch_id
        order by requested_at, id
        limit :limit
    """)

    with engine.begin() as conn:
        rows = conn.execute(
            sql,
            {
                "batch_id": batch_id,
                "limit": limit,
            },
        ).mappings().all()

    return [dict(row) for row in rows]


def get_recent_jobs_for_requester(
    engine,
    requested_by: str,
    job_type: str,
    exclude_job_id: int,
    limit: int = 3,
) -> list[dict]:
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
            payload ->> 'batch_id' as batch_id,
            result_message,
            error_message
        from ops.job_queue
        where requested_by = :requested_by
          and job_type = :job_type
          and id <> :exclude_job_id
          and requested_at >= now() - interval '1 day'
        order by
            case when status in ('pending', 'running') then 0 else 1 end,
            requested_at desc,
            id desc
        limit :limit
    """)

    with engine.begin() as conn:
        rows = conn.execute(
            sql,
            {
                "requested_by": requested_by,
                "job_type": job_type,
                "exclude_job_id": exclude_job_id,
                "limit": limit,
            },
        ).mappings().all()

    return [dict(row) for row in rows]