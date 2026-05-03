import os

from src.jobs.queue import enqueue_job


def enqueue_sync_inventory_jobs(
    engine,
    requested_by: str | None = None,
    source: str | None = None,
    allowed_workers: set[str] | None = None,
) -> list[dict]:
    jobs = []

    targets = [
        {"site": "HQ", "worker_name": "HQ-PC"},
        {"site": "SYP", "worker_name": "SYP-PC"},
    ]

    for target in targets:
        if allowed_workers is not None and target["worker_name"] not in allowed_workers:
            continue

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


def enqueue_sync_product_images_jobs(
    engine,
    requested_by: str | None = None,
    source: str | None = None,
    allowed_workers: set[str] | None = None,
) -> list[dict]:
    jobs = []

    targets = [
        {"site": "HQ", "worker_name": "HQ-PC"},
        {"site": "SYP", "worker_name": "SYP-PC"},
    ]

    for target in targets:
        if allowed_workers is not None and target["worker_name"] not in allowed_workers:
            continue

        job = enqueue_job(
            engine=engine,
            job_type="sync_product_images",
            payload={
                "task": "sync_product_images",
                "site": target["site"],
                "bucket": "pictures",
                "base_folder": "product",
            },
            worker_name=target["worker_name"],
            requested_by=requested_by,
            source=source,
        )

        jobs.append(job)

    return jobs