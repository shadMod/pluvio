from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import xarray
import xarray as xr

from pluvio import PluvioClient
from pluvio.datasets.base import BaseDataset
from pluvio.datasets.era5_land.constants import LAYER_VARIABLES
from pluvio.helpers.utils import round_data_array
from pluvio.models import SoilMoistureRecord, SoilMoistureResult


class ERA5LandSoilMoisture(BaseDataset):
    """Daily mean volumetric soil water from Copernicus ERA5-Land.

    Layers:
        1 → 0–7 cm    (most responsive to rain/drought cycles)
        2 → 7–28 cm   (mid-root zone)
        3 → 28–100 cm (deep, slow response — pipe bedding zone)

    Typical values (m³/m³):
        < 0.10  very dry — high soil shrinkage risk
        0.10–0.20  dry
        0.20–0.35  normal
        > 0.35  wet
    """

    cds_dataset = "reanalysis-era5-land"

    def __init__(self, layers: list[int] | None = None, client: PluvioClient | None = None) -> None:
        super().__init__(client)
        invalid = set(layers) - LAYER_VARIABLES.keys() if layers else True
        if invalid:
            raise ValueError(f"Invalid layers: {invalid}. Valid: {list(LAYER_VARIABLES)}")
        self._layers = layers

    def build_request(
        self, lat: float, lon: float, start_date: date, end_date: date
    ) -> dict[str, Any]:
        dates = [
            (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range((end_date - start_date).days + 1)
        ]
        # TODO: check-me - Soil moisture changes slowly (4 samples/day is enough for a reliable daily mean)
        return {
            "variable": [LAYER_VARIABLES[layer] for layer in self._layers],
            "product_type": "reanalysis",
            "date": dates,
            "time": ["00:00", "06:00", "12:00", "18:00"],
            "area": [lat + 0.1, lon - 0.1, lat - 0.1, lon + 0.1],
            "format": "netcdf",
        }

    def parse(self, nc_path: str, lat: float, lon: float) -> SoilMoistureResult:
        with xr.open_dataset(nc_path) as ds:
            time_dim = "valid_time" if "valid_time" in ds.dims else "time"

            def daily_mean_at_point(var: str) -> xarray.DataArray:
                if var not in ds:
                    return None
                return (
                    ds[var]
                    .resample({time_dim: "1D"})
                    .mean()
                    .sel(latitude=lat, longitude=lon, method="nearest")
                )

            swvl1 = daily_mean_at_point("swvl1")
            swvl2 = daily_mean_at_point("swvl2")
            swvl3 = daily_mean_at_point("swvl3")

            records = [
                SoilMoistureRecord(
                    date=date.fromisoformat(str(t)[:10]),
                    swvl1=round_data_array(swvl1.sel({time_dim: t}), 6, False),
                    swvl2=round_data_array(swvl2.sel({time_dim: t}), 6),
                    swvl3=round_data_array(swvl3.sel({time_dim: t}), 6),
                )
                for t in swvl1[time_dim].values
            ]

        return SoilMoistureResult(
            latitude=lat,
            longitude=lon,
            start_date=records[0].date if records else date.today(),
            end_date=records[-1].date if records else date.today(),
            records=records,
        )
