from datetime import datetime, timedelta

import xarray

from pluvio.constants import AQI_THRESHOLDS
from pluvio.models import PrecipitationRecord
from pluvio.types import AqiCategory


def round_data_array(
    val_array: xarray.DataArray, n_digits: int, fail_silently: bool = True
) -> float | None:
    """Round a numpy array to n_digits.

    Args:
        val_array (xarray.DataArray): array to round.
        n_digits (int): Number of digits to round to.
        fail_silently (bool, optional): Raise exception if True. Defaults to True.

    Returns:
        float | None: Return round a numpy array. If rounding fails, return None if fail_silently is True,
                        otherwise raise.
    """
    try:
        return round(float(val_array), n_digits)
    except Exception:
        if fail_silently:
            return None
        raise


def get_date_range_from_records(records: list[PrecipitationRecord]):
    if records:
        return records[0].date, records[-1].date

    end_date = datetime.now()
    return end_date - timedelta(days=1), end_date


def aqi_category(value: float | None, pollutant: str) -> AqiCategory | None:
    if value is None or pollutant not in AQI_THRESHOLDS:
        return None
    moderate, poor, very_poor = AQI_THRESHOLDS[pollutant]
    if value < moderate:
        return "good"
    if value < poor:
        return "moderate"
    if value < very_poor:
        return "poor"
    return "very_poor"
