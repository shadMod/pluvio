from __future__ import annotations

from pluvio.extras.storage.models import PluvioAirQuality, PluvioPrecipitation, PluvioSoilMoisture

EXPECTED_DATASET_MODEL_MAP: dict[str, type] = {
    "ERA5LandPrecipitation": PluvioPrecipitation,
    "ERA5LandSoilMoisture": PluvioSoilMoisture,
    "CAMSEuropeAirQuality": PluvioAirQuality,
}
