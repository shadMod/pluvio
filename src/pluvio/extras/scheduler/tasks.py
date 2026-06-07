from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from pluvio.datasets.base import ERA5_LAG_DAYS, BaseDataset
from pluvio.extras.scheduler.utils import group_consecutive_dates
from pluvio.extras.storage.adapter import PluvioStorage

logger = logging.getLogger("pluvio.scheduler")


def run_nightly_ingest(storage: PluvioStorage, dataset: BaseDataset) -> dict[str, Any]:
    """
    Core ingestion logic — usable standalone or wrapped in a Celery task.

    For each active location:
      1. Finds missing dates via storage.missing_dates()
      2. Groups them into contiguous ranges
      3. Fetches from CDS only what's needed
      4. Upserts into storage

    Returns a summary dict with results per location.
    """
    end_date = date.today() - timedelta(days=ERA5_LAG_DAYS)
    start_date = date(2020, 1, 1)  # default history start

    locations = storage.get_locations(active_only=True)
    summary: dict[str, Any] = {}

    for loc in locations:
        loc_key = f"{loc.name} (id={loc.id})"

        try:
            missing = storage.missing_dates(loc.id, start_date, end_date)

            if not missing:
                logger.info("%s — up to date", loc_key)
                summary[loc_key] = {"status": "up_to_date", "days_ingested": 0}
                continue

            ranges = group_consecutive_dates(missing)
            days_ingested = 0

            for range_start, range_end in ranges:
                result = dataset.fetch(
                    lat=float(loc.latitude),
                    lon=float(loc.longitude),
                    start_date=range_start,
                    end_date=range_end,
                )
                days_ingested += storage.upsert_precipitation(result, loc.id)
                logger.info("%s — ingested %s → %s", loc_key, range_start, range_end)

            summary[loc_key] = {"status": "ok", "days_ingested": days_ingested}

        except Exception as exc:
            logger.error("%s — failed: %s", loc_key, exc, exc_info=True)
            summary[loc_key] = {"status": "error", "error": str(exc)}

    return summary


def setup_pluvio(
    celery_app: Any,
    storage: PluvioStorage,
    dataset: BaseDataset,
    schedule: Any = None,
    task_name: str = "pluvio.nightly_ingest",
) -> Any:
    """
    Register the pluvio nightly ingest task on an existing Celery app.

    Usage:
        from celery import Celery
        from celery.schedules import crontab
        from pluvio import ERA5LandPrecipitation
        from pluvio.extras.storage import PluvioStorage
        from pluvio.extras.scheduler import setup_pluvio

        celery_app = Celery(...)
        storage = PluvioStorage(engine)
        dataset = ERA5LandPrecipitation()

        setup_pluvio(celery_app, storage=storage, dataset=dataset)
        # default schedule: every night at 02:00 Europe/Rome

        # Custom schedule:
        setup_pluvio(..., schedule=crontab(hour=3, minute=30))
    """
    from celery.schedules import crontab

    if schedule is None:
        schedule = crontab(hour=2, minute=0)

    @celery_app.task(name=task_name, bind=True, max_retries=3, default_retry_delay=60 * 15)
    def nightly_ingest(self: Any) -> dict[str, Any]:
        try:
            return run_nightly_ingest(storage, dataset)
        except Exception as exc:
            logger.error("pluvio nightly ingest failed, retrying: %s", exc)
            raise self.retry(exc=exc)

    celery_app.conf.beat_schedule[task_name] = {
        "task": task_name,
        "schedule": schedule,
    }

    logger.info("pluvio: registered task '%s' on %s", task_name, celery_app)
    return nightly_ingest
