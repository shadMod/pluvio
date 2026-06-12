from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from pluvio.datasets.base import ERA5_LAG_DAYS, BaseDataset
from pluvio.extras.scheduler.utils import group_consecutive_dates
from pluvio.extras.storage.adapter import PluvioStorage

logger = logging.getLogger("pluvio.scheduler")


def run_nightly_ingest(storage: PluvioStorage, dataset: BaseDataset) -> dict[str, Any]:
    end_date = date.today() - timedelta(days=ERA5_LAG_DAYS)
    start_date = date(2020, 1, 1)

    locations = storage.get_locations(active_only=True)
    summary: dict[str, Any] = {}

    for loc in locations:
        loc_key = f"{loc.name} (id={loc.id})"
        try:
            missing = storage.missing_dates_for(dataset, loc.id, start_date, end_date)

            if not missing:
                logger.info("%s — up to date", loc_key)
                summary[loc_key] = {"status": "up_to_date", "days_ingested": 0}
                continue

            days_ingested = 0
            for range_start, range_end in group_consecutive_dates(missing):
                result = dataset.fetch(
                    lat=float(loc.latitude),
                    lon=float(loc.longitude),
                    start_date=range_start,
                    end_date=range_end,
                )
                days_ingested += storage.upsert(result, loc.id)
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

    return nightly_ingest
