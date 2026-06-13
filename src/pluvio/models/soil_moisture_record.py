from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, computed_field

from pluvio.types import DrynessCategory


class SoilMoistureRecord(BaseModel):
    date: date
    swvl1: float = Field(
        ge=0.0, le=1.0, description="Volumetric soil water layer 1 (0–7 cm), m³/m³"
    )
    swvl2: float | None = Field(None, ge=0.0, le=1.0, description="Layer 2 (7–28 cm), m³/m³")
    swvl3: float | None = Field(None, ge=0.0, le=1.0, description="Layer 3 (28–100 cm), m³/m³")
    source: str = "ERA5-LAND-CDS"

    @computed_field
    @property
    def dryness_category(self) -> DrynessCategory:
        if self.swvl1 < 0.10:
            return "very_dry"
        if self.swvl1 < 0.20:
            return "dry"
        if self.swvl1 < 0.35:
            return "normal"
        return "wet"
