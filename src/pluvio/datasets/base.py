from __future__ import annotations

import os
import tempfile
from abc import ABC, abstractmethod
from datetime import date
from typing import Any

from pluvio.client import PluvioClient
from pluvio.exceptions import DataNotAvailableError

# ERA5-Land ha un ritardo di ~5-6 giorni sul presente
ERA5_LAG_DAYS = 6


class BaseDataset(ABC):
    """
    Template base class for all Copernicus dataset ingesters.

    Subclasses must be implemented:
      - cds_dataset: str           the CDS dataset identifier
      - build_request(...)         returns the CDS API request dict
      - parse(nc_path, lat, lon)   parses the downloaded NetCDF and returns typed results
    """

    cds_dataset: str

    def __init__(self, client: PluvioClient | None = None) -> None:
        self._client = client or PluvioClient()

    @abstractmethod
    def build_request(
        self, lat: float, lon: float, start_date: date, end_date: date
    ) -> dict[str, Any]: ...

    @abstractmethod
    def parse(self, nc_path: str, lat: float, lon: float) -> Any: ...

    def fetch(self, lat: float, lon: float, start_date: date, end_date: date) -> Any:
        """Download, parse and return clean typed results. Temp file is cleaned up automatically."""
        self._validate_dates(start_date, end_date)

        fd, tmp_path = tempfile.mkstemp(suffix=".nc")
        os.close(fd)

        try:
            self._client.raw.retrieve(
                self.cds_dataset,
                self.build_request(lat, lon, start_date, end_date),
                tmp_path,
            )
            return self.parse(tmp_path, lat, lon)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _validate_dates(self, start_date: date, end_date: date) -> None:
        from datetime import date as dt
        from datetime import timedelta

        if start_date > end_date:
            raise ValueError("start_date must be before end_date")

        max_end = dt.today() - timedelta(days=ERA5_LAG_DAYS)
        if end_date > max_end:
            raise DataNotAvailableError(
                f"ERA5-Land data is only available up to {max_end} (current lag: {ERA5_LAG_DAYS} days). "
                f"Requested end_date: {end_date}"
            )
