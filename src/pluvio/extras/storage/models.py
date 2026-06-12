from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class PluvioBase(DeclarativeBase):
    # TODO: put here __tablename__ and __table_args__ as Meta like django model.

    pass


class PluvioLocation(PluvioBase):
    __tablename__ = "pluvio_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    latitude: Mapped[float] = mapped_column(Numeric(8, 5))
    longitude: Mapped[float] = mapped_column(Numeric(8, 5))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    precipitations: Mapped[list[PluvioPrecipitation]] = relationship(back_populates="location")
    soil_moistures: Mapped[list[PluvioSoilMoisture]] = relationship(back_populates="location")


class PluvioPrecipitation(PluvioBase):
    __tablename__ = "pluvio_precipitation_daily"
    __table_args__ = (
        UniqueConstraint("location_id", "date", name="uq_pluvio_precipitation_location_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("pluvio_locations.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    precipitation_mm: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    rained: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="ERA5-LAND-CDS")
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    location: Mapped[PluvioLocation] = relationship(back_populates="precipitations")


class PluvioSoilMoisture(PluvioBase):
    __tablename__ = "pluvio_soil_moisture_daily"
    __table_args__ = (
        UniqueConstraint("location_id", "date", name="uq_pluvio_soil_moisture_location_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("pluvio_locations.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    swvl1: Mapped[float] = mapped_column(Numeric(8, 6), nullable=False)
    swvl2: Mapped[float | None] = mapped_column(Numeric(8, 6), nullable=True)
    swvl3: Mapped[float | None] = mapped_column(Numeric(8, 6), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="ERA5-LAND-CDS")
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    location: Mapped[PluvioLocation] = relationship(back_populates="soil_moistures")
