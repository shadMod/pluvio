from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine

from pluvio.extras.scheduler.tasks import run_nightly_ingest
from pluvio.extras.scheduler.utils import group_consecutive_dates
from pluvio.extras.storage import PluvioStorage
from pluvio.models import PrecipitationRecord, PrecipitationResult

# ── utils ─────────────────────────────────────────────────────────────────────


def test_group_consecutive_single_range():
    dates = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
    assert group_consecutive_dates(dates) == [(date(2024, 1, 1), date(2024, 1, 3))]


def test_group_consecutive_multiple_ranges():
    dates = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 5), date(2024, 1, 6)]
    assert group_consecutive_dates(dates) == [
        (date(2024, 1, 1), date(2024, 1, 2)),
        (date(2024, 1, 5), date(2024, 1, 6)),
    ]


def test_group_consecutive_empty():
    assert group_consecutive_dates([]) == []


def test_group_consecutive_single_date():
    assert group_consecutive_dates([date(2024, 1, 1)]) == [(date(2024, 1, 1), date(2024, 1, 1))]


# ── run_nightly_ingest ────────────────────────────────────────────────────────


@pytest.fixture
def storage_with_location():
    engine = create_engine("sqlite:///:memory:")
    storage = PluvioStorage(engine)
    storage.create_tables()
    loc_id = storage.add_location("Test", lat=45.4, lon=11.9)
    return storage, loc_id


def make_result(start: date, end: date) -> PrecipitationResult:
    days = (end - start).days + 1
    return PrecipitationResult(
        latitude=45.4,
        longitude=11.9,
        start_date=start,
        end_date=end,
        records=[
            PrecipitationRecord(
                date=start + timedelta(days=i),
                precipitation_mm=float(i),
                rained=i > 0,
            )
            for i in range(days)
        ],
    )


def test_run_nightly_ingest_ok(storage_with_location):
    storage, _ = storage_with_location

    mock_dataset = MagicMock()
    mock_dataset.fetch.return_value = make_result(date(2020, 1, 1), date(2020, 1, 3))

    with patch("pluvio.extras.scheduler.tasks.date") as mock_date:
        mock_date.today.return_value = date(2020, 1, 10)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        summary = run_nightly_ingest(storage, mock_dataset)

    assert any(v["status"] == "ok" for v in summary.values())
    assert mock_dataset.fetch.called


def test_run_nightly_ingest_up_to_date(storage_with_location):
    storage, loc_id = storage_with_location

    # Pre-populate so nothing is missing
    result = make_result(date(2020, 1, 1), date(2020, 1, 3))
    storage.upsert_precipitation(result, loc_id)

    mock_dataset = MagicMock()

    with patch("pluvio.extras.scheduler.tasks.date") as mock_date:
        mock_date.today.return_value = date(2020, 1, 9)  # end = today - 6 = 2020-01-03
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        summary = run_nightly_ingest(storage, mock_dataset)

    mock_dataset.fetch.assert_not_called()
    assert any(v["status"] == "up_to_date" for v in summary.values())


def test_run_nightly_ingest_location_error(storage_with_location):
    storage, _ = storage_with_location

    mock_dataset = MagicMock()
    mock_dataset.fetch.side_effect = RuntimeError("CDS down")

    with patch("pluvio.extras.scheduler.tasks.date") as mock_date:
        mock_date.today.return_value = date(2020, 1, 10)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        summary = run_nightly_ingest(storage, mock_dataset)

    assert any(v["status"] == "error" for v in summary.values())
