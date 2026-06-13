from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from pydantic import BaseModel, computed_field

from .air_quality_record import AirQualityRecord

if TYPE_CHECKING:
    import polars as pl


class AirQualityResult(BaseModel):
    latitude: float
    longitude: float
    start_date: date
    end_date: date
    records: list[AirQualityRecord]

    @computed_field
    @property
    def poor_air_days(self) -> int:
        return sum(1 for r in self.records if r.overall_aqi in ("poor", "very_poor"))

    @computed_field
    @property
    def missing_days(self) -> int:
        return (self.end_date - self.start_date).days + 1 - len(self.records)

    def to_frame(self) -> pl.DataFrame:
        try:
            import polars as pl
        except ImportError:
            from pluvio.exceptions import MissingExtraError

            raise MissingExtraError("polars", "polars")
        return pl.DataFrame([r.model_dump() for r in self.records]).with_columns(
            pl.col("date").cast(pl.Date)
        )
