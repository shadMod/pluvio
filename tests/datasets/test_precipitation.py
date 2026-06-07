from datetime import date
from unittest.mock import patch

import pytest

from pluvio.exceptions import DataNotAvailableError
from pluvio.models import PrecipitationResult


def test_computed_fields(sample_result: PrecipitationResult):
    assert sample_result.total_precipitation_mm == 18.0
    assert sample_result.rainy_days == 2
    assert sample_result.missing_days == 0


def test_computed_fields(sample_result: PrecipitationResult):
    assert sample_result.total_precipitation_mm == 18.0
    assert sample_result.rainy_days == 2
    assert sample_result.missing_days == 0


def test_missing_days(sample_result: PrecipitationResult):
    sample_result.end_date = date(2024, 1, 5)
    assert sample_result.missing_days == 2


def test_to_frame_without_polars(sample_result: PrecipitationResult):
    with patch.dict("sys.modules", {"polars": None}):
        from pluvio.exceptions import MissingExtraError

        with pytest.raises(MissingExtraError):
            sample_result.to_frame()


def test_validate_dates_raises_on_future():
    from datetime import timedelta

    from pluvio.datasets.era5_land.precipitation import ERA5LandPrecipitation

    dataset = ERA5LandPrecipitation.__new__(ERA5LandPrecipitation)

    future = date.today() + timedelta(days=10)
    with pytest.raises(DataNotAvailableError):
        dataset._validate_dates(date(2024, 1, 1), future)


def test_build_request_structure():
    from pluvio.datasets.era5_land.precipitation import ERA5LandPrecipitation

    dataset = ERA5LandPrecipitation.__new__(ERA5LandPrecipitation)

    req = dataset.build_request(45.4, 11.9, date(2024, 1, 1), date(2024, 1, 3))

    assert req["variable"] == "total_precipitation"
    assert len(req["date"]) == 3
    assert req["area"] == [45.5, 11.8, 45.3, 12.0]
    assert len(req["time"]) == 24
