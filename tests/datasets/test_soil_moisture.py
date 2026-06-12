from datetime import date

import pytest

from pluvio.models import SoilMoistureRecord, SoilMoistureResult


@pytest.fixture
def sample_result() -> SoilMoistureResult:
    return SoilMoistureResult(
        latitude=45.4,
        longitude=11.9,
        start_date=date(2024, 7, 1),
        end_date=date(2024, 7, 3),
        records=[
            SoilMoistureRecord(date=date(2024, 7, 1), swvl1=0.08, swvl2=0.18, swvl3=0.28),
            SoilMoistureRecord(date=date(2024, 7, 2), swvl1=0.15, swvl2=0.22, swvl3=0.30),
            SoilMoistureRecord(date=date(2024, 7, 3), swvl1=0.38, swvl2=0.35, swvl3=0.33),
        ],
    )


def test_dryness_categories(sample_result: SoilMoistureResult):
    categories = [r.dryness_category for r in sample_result.records]
    assert categories == ["very_dry", "dry", "wet"]


def test_dry_days(sample_result: SoilMoistureResult):
    assert sample_result.dry_days == 2


def test_missing_days(sample_result: SoilMoistureResult):
    assert sample_result.missing_days == 0


def test_build_request_variables():
    from pluvio.datasets.era5_land.soil_moisture import ERA5LandSoilMoisture

    dataset = ERA5LandSoilMoisture.__new__(ERA5LandSoilMoisture)
    dataset._layers = [1, 2]

    req = dataset.build_request(45.4, 11.9, date(2024, 1, 1), date(2024, 1, 1))

    assert "volumetric_soil_water_layer_1" in req["variable"]
    assert "volumetric_soil_water_layer_2" in req["variable"]
    assert "volumetric_soil_water_layer_3" not in req["variable"]
    assert req["time"] == ["00:00", "06:00", "12:00", "18:00"]


def test_invalid_layers():
    from pluvio.datasets.era5_land.soil_moisture import ERA5LandSoilMoisture

    with pytest.raises(ValueError, match="Invalid layers"):
        ERA5LandSoilMoisture(layers=[1, 99])


def test_storage_upsert_and_get_soil_moisture(sample_result: SoilMoistureResult):
    from sqlalchemy import create_engine

    from pluvio.extras.storage import PluvioStorage

    engine = create_engine("sqlite:///:memory:")
    storage = PluvioStorage(engine)
    storage.create_tables()
    loc_id = storage.add_location("Test", lat=45.4, lon=11.9)

    count = storage.upsert_soil_moisture(sample_result, loc_id)
    assert count == 3

    result = storage.get_soil_moisture(loc_id, date(2024, 7, 1), date(2024, 7, 3))
    assert result is not None
    assert result.dry_days == 2
    assert len(result.records) == 3


def test_generic_upsert_dispatch(sample_result: SoilMoistureResult):
    from sqlalchemy import create_engine

    from pluvio.extras.storage import PluvioStorage

    engine = create_engine("sqlite:///:memory:")
    storage = PluvioStorage(engine)
    storage.create_tables()
    loc_id = storage.add_location("Test", lat=45.4, lon=11.9)

    count = storage.upsert(sample_result, loc_id)
    assert count == 3
