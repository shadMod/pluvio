from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import xarray as xr

from pluvio import PluvioClient
from pluvio.datasets.base import BaseDataset
from pluvio.datasets.cams.constants import DEFAULT_VARIABLES, VARIABLE_MAP
from pluvio.helpers.utils import get_date_range_from_records
from pluvio.models import AirQualityRecord, AirQualityResult


class CAMSEuropeAirQuality(BaseDataset):
    """Daily mean air quality concentrations from CAMS European Air Quality Reanalysis.

    Dataset: cams-europe-air-quality-reanalyses
    Resolution: ~0.1° (~10km) over Europe. Coverage: 2013-present (~5 day lag).
    Units: µg/m³ (all variables, already converted by CAMS).

    Relevant for water utilities:
      - PM10/PM2.5: dry deposition on open water surfaces and catchment areas
      - NO2: atmospheric nitrogen load on watersheds (eutrophication risk)
      - SO2: acid rain precursor, affects water pH

    Usage:
        dataset = CAMSEuropeAirQuality() # PM10, PM2.5, NO2
        dataset = CAMSEuropeAirQuality(variables=["ozone", "sulphur_dioxide"])
    """

    cds_dataset = "cams-europe-air-quality-reanalyses"

    def __init__(
        self, variables: list[str] | None = None, client: PluvioClient | None = None
    ) -> None:
        super().__init__(client)
        _variables = variables or DEFAULT_VARIABLES

        invalid = set(variables) - VARIABLE_MAP.keys()
        if invalid:
            raise ValueError(f"Invalid variables: {invalid}.\nValid: {list(VARIABLE_MAP)}")
        self._variables = variables

    def build_request(
        self, lat: float, lon: float, start_date: date, end_date: date
    ) -> dict[str, Any]:
        dates = [
            (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range((end_date - start_date).days + 1)
        ]
        return {
            "variable": self._variables,
            "model": "ensemble",
            "level": "0",
            "type": "reanalysis",
            "date": dates,
            "time": [f"{h:02d}:00" for h in range(24)],
            "area": [lat + 0.1, lon - 0.1, lat - 0.1, lon + 0.1],
            "format": "netcdf",
        }

    def parse(self, nc_path: str, lat: float, lon: float) -> AirQualityResult:
        with xr.open_dataset(nc_path) as ds:
            time_dim = "valid_time" if "valid_time" in ds.dims else "time"

            # Build a dict of daily means per output field, keyed by date
            daily_values: dict[date, dict[str, float | None]] = {}

            for cds_var, (nc_var, output_field) in VARIABLE_MAP.items():
                if cds_var not in self._variables:
                    continue

                # Try both possible NetCDF variable names (CAMS can vary)
                raw = ds.get(nc_var) or ds.get(nc_var.replace("_conc", ""))
                if raw is None:
                    continue

                daily = raw.resample({time_dim: "1D"}).mean()
                point = daily.sel(latitude=lat, longitude=lon, method="nearest")

                for t in point[time_dim].values:
                    d = date.fromisoformat(str(t)[:10])
                    daily_values.setdefault(d, {})[output_field] = round(
                        max(float(point.sel({time_dim: t}).values), 0.0), 4
                    )

        records = [AirQualityRecord(date=d, **fields) for d, fields in sorted(daily_values.items())]

        start_date, end_date = get_date_range_from_records(records)
        return AirQualityResult(
            latitude=lat,
            longitude=lon,
            start_date=start_date,
            end_date=end_date,
            records=records,
        )
