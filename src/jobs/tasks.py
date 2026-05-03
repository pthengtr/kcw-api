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


def enqueue_sync_product_images_job(
    engine,
    requested_by: str | None = None,
    source: str | None = None,
    allowed_workers: set[str] | None = None,
) -> dict | None:
    """
    Enqueue product image sync.

    Worker execution is controlled by worker .env:

    WORKER_JOB_SYNC_PRODUCT_IMAGES_COMMAND=...
    WORKER_JOB_SYNC_PRODUCT_IMAGES_CWD=...

    API/cloud side can optionally target a specific worker via:

    SYNC_PRODUCT_IMAGES_WORKER_NAME=SYP-PC

    If SYNC_PRODUCT_IMAGES_WORKER_NAME is blank, the job is queued with
    worker_name=None, meaning any worker can claim it.
    """
    target_worker = (os.getenv("SYNC_PRODUCT_IMAGES_WORKER_NAME") or "").strip() or None

    if target_worker and allowed_workers is not None and target_worker not in allowed_workers:
        return None

    if not target_worker and allowed_workers is not None and not allowed_workers:
        return None

    return enqueue_job(
        engine=engine,
        job_type="sync_product_images",
        payload={
            "task": "sync_product_images",
            "bucket": "pictures",
            "base_folder": "product",
        },
        worker_name=target_worker,
        requested_by=requested_by,
        source=source,
    )