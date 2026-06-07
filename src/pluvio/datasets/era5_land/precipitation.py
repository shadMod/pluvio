from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import xarray as xr

from pluvio.datasets.base import BaseDataset
from pluvio.models import PrecipitationRecord, PrecipitationResult

RAIN_THRESHOLD_MM = 0.1


class ERA5LandPrecipitation(BaseDataset):
    """
    Daily precipitation from Copernicus ERA5-Land reanalysis.
    Resolution: ~0.1° (~9km). Coverage: 1950-01-01 to ~5 days ago.
    """

    cds_dataset = "reanalysis-era5-land"

    def build_request(
        self, lat: float, lon: float, start_date: date, end_date: date
    ) -> dict[str, Any]:
        dates = [
            (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range((end_date - start_date).days + 1)
        ]
        return {
            "variable": "total_precipitation",
            "product_type": "reanalysis",
            "date": dates,
            "time": [f"{h:02d}:00" for h in range(24)],
            "area": [lat + 0.1, lon - 0.1, lat - 0.1, lon + 0.1],  # [N, W, S, E]
            "format": "netcdf",
        }

    def parse(self, nc_path: str, lat: float, lon: float) -> PrecipitationResult:
        ds = xr.open_dataset(nc_path)

        # ERA5-Land usa 'valid_time' nelle versioni recenti, 'time' nelle precedenti
        time_dim = "valid_time" if "valid_time" in ds.dims else "time"

        # tp è in metri → mm; somma ore → giorno
        daily = (ds["tp"] * 1000).resample({time_dim: "1D"}).sum()
        point = daily.sel(latitude=lat, longitude=lon, method="nearest")

        records = [
            PrecipitationRecord(
                date=date.fromisoformat(str(t)[:10]),
                precipitation_mm=val,
                rained=val > RAIN_THRESHOLD_MM,
            )
            for t in point[time_dim].values
            if (val := max(round(float(point.sel({time_dim: t}).values), 2), 0.0)) is not None
        ]

        ds.close()

        return PrecipitationResult(
            latitude=lat,
            longitude=lon,
            start_date=records[0].date if records else start_date,
            end_date=records[-1].date if records else end_date,
            records=records,
        )
