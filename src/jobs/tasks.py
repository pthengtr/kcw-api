from src.jobs.queue import enqueue_job

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