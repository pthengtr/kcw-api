from uuid import uuid4

from src.jobs.queue import enqueue_job


def enqueue_sync_inventory_jobs(
    engine,
    requested_by: str | None = None,
    source: str | None = None,
    allowed_workers: set[str] | None = None,
) -> list[dict]:
    jobs = []
    batch_id = str(uuid4())

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
            batch_id=batch_id,
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
    batch_id = str(uuid4())

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
            batch_id=batch_id,
        )

        jobs.append(job)

    return jobs

def enqueue_sync_online_sales_jobs(
    engine,
    requested_by: str | None = None,
    source: str | None = None,
    allowed_workers: set[str] | None = None,
) -> list[dict]:
    jobs = []
    batch_id = str(uuid4())

    target = {"site": "HQ", "worker_name": "HQ-PC"}

    if allowed_workers is not None and target["worker_name"] not in allowed_workers:
        return jobs

    job = enqueue_job(
        engine=engine,
        job_type="sync_online_sales",
        payload={
            "task": "sync_online_sales",
            "site": target["site"],
            "notebooks": [
                "71_online_shopee.ipynb",
                "72_online_lazada.ipynb",
                "73_online_tiktok.ipynb",
            ],
        },
        worker_name=target["worker_name"],
        requested_by=requested_by,
        source=source,
        batch_id=batch_id,
    )

    jobs.append(job)
    return jobs


def _enqueue_single_worker_job(
    engine,
    *,
    job_type: str,
    site: str,
    worker_name: str,
    task: str,
    requested_by: str | None = None,
    source: str | None = None,
    allowed_workers: set[str] | None = None,
) -> list[dict]:
    if allowed_workers is not None and worker_name not in allowed_workers:
        return []

    batch_id = str(uuid4())
    job = enqueue_job(
        engine=engine,
        job_type=job_type,
        payload={
            "task": task,
            "site": site,
        },
        worker_name=worker_name,
        requested_by=requested_by,
        source=source,
        batch_id=batch_id,
    )
    return [job]


def enqueue_syp_raw_jobs(
    engine,
    requested_by: str | None = None,
    source: str | None = None,
    allowed_workers: set[str] | None = None,
) -> list[dict]:
    return _enqueue_single_worker_job(
        engine,
        job_type="syp_raw",
        site="SYP",
        worker_name="SYP-PC",
        task="syp_raw",
        requested_by=requested_by,
        source=source,
        allowed_workers=allowed_workers,
    )


def enqueue_hq_raw_jobs(
    engine,
    requested_by: str | None = None,
    source: str | None = None,
    allowed_workers: set[str] | None = None,
) -> list[dict]:
    return _enqueue_single_worker_job(
        engine,
        job_type="hq_raw",
        site="HQ",
        worker_name="HQ-PC",
        task="hq_raw",
        requested_by=requested_by,
        source=source,
        allowed_workers=allowed_workers,
    )


def enqueue_hq_full_jobs(
    engine,
    requested_by: str | None = None,
    source: str | None = None,
    allowed_workers: set[str] | None = None,
) -> list[dict]:
    return _enqueue_single_worker_job(
        engine,
        job_type="hq_full",
        site="HQ",
        worker_name="HQ-PC",
        task="hq_full",
        requested_by=requested_by,
        source=source,
        allowed_workers=allowed_workers,
    )


def enqueue_sync_pomas_podet_jobs(
    engine,
    requested_by: str | None = None,
    source: str | None = None,
    allowed_workers: set[str] | None = None,
) -> list[dict]:
    jobs = []
    batch_id = str(uuid4())

    targets = [
        {"site": "HQ", "worker_name": "HQ-PC"},
        {"site": "SYP", "worker_name": "SYP-PC"},
    ]

    for target in targets:
        if allowed_workers is not None and target["worker_name"] not in allowed_workers:
            continue

        job = enqueue_job(
            engine=engine,
            job_type="sync_pomas_podet",
            payload={
                "task": "sync_pomas_podet",
                "site": target["site"],
            },
            worker_name=target["worker_name"],
            requested_by=requested_by,
            source=source,
            batch_id=batch_id,
        )

        jobs.append(job)

    return jobs


def enqueue_sync_iclow_jobs(
    engine,
    requested_by: str | None = None,
    source: str | None = None,
    allowed_workers: set[str] | None = None,
) -> list[dict]:
    jobs = []
    batch_id = str(uuid4())

    targets = [
        {"site": "HQ", "worker_name": "HQ-PC"},
        {"site": "SYP", "worker_name": "SYP-PC"},
    ]

    for target in targets:
        if allowed_workers is not None and target["worker_name"] not in allowed_workers:
            continue

        job = enqueue_job(
            engine=engine,
            job_type="sync_iclow",
            payload={
                "task": "sync_iclow",
                "site": target["site"],
            },
            worker_name=target["worker_name"],
            requested_by=requested_by,
            source=source,
            batch_id=batch_id,
        )

        jobs.append(job)

    return jobs


def enqueue_sync_icmas_jobs(
    engine,
    requested_by: str | None = None,
    source: str | None = None,
    allowed_workers: set[str] | None = None,
) -> list[dict]:
    jobs = []
    batch_id = str(uuid4())

    targets = [
        {"site": "HQ", "worker_name": "HQ-PC"},
        {"site": "SYP", "worker_name": "SYP-PC"},
    ]

    for target in targets:
        if allowed_workers is not None and target["worker_name"] not in allowed_workers:
            continue

        job = enqueue_job(
            engine=engine,
            job_type="sync_icmas",
            payload={
                "task": "sync_icmas",
                "site": target["site"],
            },
            worker_name=target["worker_name"],
            requested_by=requested_by,
            source=source,
            batch_id=batch_id,
        )

        jobs.append(job)

    return jobs


def enqueue_bank_statement_import_jobs(
    engine,
    requested_by: str | None = None,
    source: str | None = None,
    allowed_workers: set[str] | None = None,
) -> list[dict]:
    """Enqueue one job assigned to HQ-PC only."""
    return _enqueue_single_worker_job(
        engine,
        job_type="bank_statement_import",
        site="HQ",
        worker_name="HQ-PC",
        task="bank_statement_import",
        requested_by=requested_by,
        source=source,
        allowed_workers=allowed_workers,
    )


def enqueue_sync_po_related_jobs(
    engine,
    requested_by: str | None = None,
    source: str | None = None,
    allowed_workers: set[str] | None = None,
) -> list[dict]:
    """Enqueue one unassigned job; any online worker can claim it."""
    known_workers = {"HQ-PC", "SYP-PC"}

    if allowed_workers is not None:
        eligible = known_workers & allowed_workers
        if not eligible:
            return []

    batch_id = str(uuid4())
    job = enqueue_job(
        engine=engine,
        job_type="sync_po_related",
        payload={
            "task": "sync_po_related",
        },
        worker_name=None,
        requested_by=requested_by,
        source=source,
        batch_id=batch_id,
    )
    return [job]