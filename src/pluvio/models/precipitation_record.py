from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    pass


class PrecipitationRecord(BaseModel):
    date: date
    precipitation_mm: float = Field(ge=0.0)
    rained: bool
    source: str = "ERA5-LAND-CDS"
