from pluvio.client import PluvioClient
from pluvio.datasets.cams.air_quality import CAMSEuropeAirQuality
from pluvio.datasets.era5_land.precipitation import ERA5LandPrecipitation
from pluvio.datasets.era5_land.soil_moisture import ERA5LandSoilMoisture
from pluvio.exceptions import CDSAuthError, DataNotAvailableError, MissingExtraError, PluvioError
from pluvio.models import (
    AirQualityRecord,
    AirQualityResult,
    PrecipitationRecord,
    PrecipitationResult,
    SoilMoistureRecord,
    SoilMoistureResult,
)

__version__ = "0.5.0"

__all__ = [
    "AirQualityRecord",
    "AirQualityResult",
    "CAMSEuropeAirQuality",
    "CDSAuthError",
    "DataNotAvailableError",
    "ERA5LandPrecipitation",
    "ERA5LandSoilMoisture",
    "MissingExtraError",
    "PluvioClient",
    "PluvioError",
    "PrecipitationRecord",
    "PrecipitationResult",
    "SoilMoistureRecord",
    "SoilMoistureResult",
]
