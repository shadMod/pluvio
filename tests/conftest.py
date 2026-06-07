from datetime import date
from unittest.mock import patch

import pytest

from pluvio.models import PrecipitationRecord, PrecipitationResult


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


@pytest.fixture
def mock_client():
    with patch("pluvio.client.cdsapi.Client") as mock:
        yield mock
