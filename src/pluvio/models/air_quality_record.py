from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, computed_field

from pluvio.helpers.utils import aqi_category
from pluvio.types import AqiCategory


class AirQualityRecord(BaseModel):
    date: date
    pm10_ugm3: float | None = Field(None, ge=0.0, description="PM10 daily mean, µg/m³")
    pm2p5_ugm3: float | None = Field(None, ge=0.0, description="PM2.5 daily mean, µg/m³")
    no2_ugm3: float | None = Field(None, ge=0.0, description="NO₂ daily mean, µg/m³")
    so2_ugm3: float | None = Field(None, ge=0.0, description="SO₂ daily mean, µg/m³")
    o3_ugm3: float | None = Field(None, ge=0.0, description="O₃ daily mean, µg/m³")
    source: str = "CAMS-EU-AQ-REANALYSIS"

    @computed_field
    @property
    def aqi_pm10(self) -> AqiCategory | None:
        return aqi_category(self.pm10_ugm3, "pm10")

    @computed_field
    @property
    def aqi_no2(self) -> AqiCategory | None:
        return aqi_category(self.no2_ugm3, "no2")

    @computed_field
    @property
    def overall_aqi(self) -> AqiCategory | None:
        """Worst-case category across all available pollutants."""
        order: list[AqiCategory] = ["very_poor", "poor", "moderate", "good"]
        categories = [
            aqi_category(self.pm10_ugm3, "pm10"),
            aqi_category(self.pm2p5_ugm3, "pm2p5"),
            aqi_category(self.no2_ugm3, "no2"),
            aqi_category(self.so2_ugm3, "so2"),
            aqi_category(self.o3_ugm3, "o3"),
        ]
        valid = [c for c in categories if c is not None]
        if not valid:
            return None
        return min(valid, key=lambda c: order.index(c))
