from datetime import date

import pytest
from sqlalchemy import create_engine

from pluvio.extras.storage import PluvioStorage
from pluvio.models import PrecipitationRecord, PrecipitationResult


@pytest.fixture
def storage() -> PluvioStorage:
    engine = create_engine("sqlite:///:memory:")
    s = PluvioStorage(engine)
    s.create_tables()
    return s


@pytest.fixture
def location_id(storage: PluvioStorage) -> int:
    return storage.add_location("Impianto Test", lat=45.4, lon=11.9)


@pytest.fixture
def sample_result() -> PrecipitationResult:
    return PrecipitationResult(
        latitude=45.4,
        longitude=11.9,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 3),
        records=[
            PrecipitationRecord(date=date(2024, 1, 1), precipitation_mm=5.2, rained=True),
            PrecipitationRecord(date=date(2024, 1, 2), precipitation_mm=0.0, rained=False),
            PrecipitationRecord(date=date(2024, 1, 3), precipitation_mm=12.8, rained=True),
        ],
    )


def test_create_tables_is_idempotent(storage: PluvioStorage):
    storage.create_tables()  # seconda chiamata non deve esplodere
    storage.create_tables()
    storage.create_tables()


def test_add_and_get_locations(storage: PluvioStorage):
    loc_id = storage.add_location("Impianto Nord", lat=45.0, lon=12.0)
    locations = storage.get_locations()
    assert any(loc.id == loc_id for loc in locations)


def test_deactivate_location(storage: PluvioStorage, location_id: int):
    storage.deactivate_location(location_id)
    assert storage.get_locations(active_only=True) == []


def test_upsert_and_get_precipitation(
    storage: PluvioStorage, location_id: int, sample_result: PrecipitationResult
):
    count = storage.upsert_precipitation(sample_result, location_id)
    assert count == 3

    result = storage.get_precipitation(location_id, date(2024, 1, 1), date(2024, 1, 3))
    assert result is not None
    assert result.rainy_days == 2
    assert result.total_precipitation_mm == 18.0


def test_upsert_is_idempotent(
    storage: PluvioStorage, location_id: int, sample_result: PrecipitationResult
):
    storage.upsert_precipitation(sample_result, location_id)
    storage.upsert_precipitation(sample_result, location_id)  # non deve duplicare

    result = storage.get_precipitation(location_id, date(2024, 1, 1), date(2024, 1, 3))
    assert result is not None
    assert len(result.records) == 3


def test_missing_dates(
    storage: PluvioStorage, location_id: int, sample_result: PrecipitationResult
):
    storage.upsert_precipitation(sample_result, location_id)
    missing = storage.missing_dates(location_id, date(2024, 1, 1), date(2024, 1, 5))
    assert missing == [date(2024, 1, 4), date(2024, 1, 5)]


def test_get_precipitation_unknown_location(storage: PluvioStorage):
    result = storage.get_precipitation(999, date(2024, 1, 1), date(2024, 1, 3))
    assert result is None
