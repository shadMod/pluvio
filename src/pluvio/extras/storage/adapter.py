from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from datetime import date, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from pluvio.extras.storage.constants import EXPECTED_DATASET_MODEL_MAP
from pluvio.extras.storage.models import (
    PluvioBase,
    PluvioLocation,
    PluvioPrecipitation,
    PluvioSoilMoisture,
)
from pluvio.models import (
    PrecipitationRecord,
    PrecipitationResult,
    SoilMoistureRecord,
    SoilMoistureResult,
)

if TYPE_CHECKING:
    from pluvio.datasets.base import BaseDataset


class PluvioStorage:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create_tables(self) -> None:
        PluvioBase.metadata.create_all(self._engine)

    @contextmanager
    def _session(self) -> Generator[Session, None, None]:
        with Session(self._engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def add_location(self, name: str, lat: float, lon: float) -> int:
        with self._session() as session:
            loc = PluvioLocation(name=name, latitude=lat, longitude=lon)
            session.add(loc)
            session.flush()
            return loc.id

    def get_locations(self, active_only: bool = True) -> list[PluvioLocation]:
        with Session(self._engine) as session:
            q = session.query(PluvioLocation)
            if active_only:
                q = q.filter_by(active=True)
            return q.all()

    def deactivate_location(self, location_id: int) -> None:
        with self._session() as session:
            loc = session.get(PluvioLocation, location_id)
            if loc:
                loc.active = False

    def upsert(self, result: PrecipitationResult | SoilMoistureResult, location_id: int) -> int:
        """Dispatch upsert to the correct handler based on result type."""
        if isinstance(result, PrecipitationResult):
            return self.upsert_precipitation(result, location_id)
        if isinstance(result, SoilMoistureResult):
            return self.upsert_soil_moisture(result, location_id)
        raise TypeError(f"No storage handler registered for {type(result).__name__}")

    def missing_dates_for(
        self, dataset: BaseDataset, location_id: int, start_date: date, end_date: date
    ) -> list[date]:
        """Return dates not yet stored for a given dataset and location."""
        model = EXPECTED_DATASET_MODEL_MAP.get(type(dataset).__name__)
        if model is None:
            raise TypeError(f"No storage model registered for {type(dataset).__name__}")
        return self._missing_dates(location_id, start_date, end_date, model)

    def upsert_precipitation(self, result: PrecipitationResult, location_id: int) -> int:
        rows = [
            {
                "location_id": location_id,
                "date": r.date,
                "precipitation_mm": r.precipitation_mm,
                "rained": r.rained,
                "source": r.source,
            }
            for r in result.records
        ]
        with self._session() as session:
            return self._upsert_rows(
                session,
                PluvioPrecipitation,
                rows,
                update_columns=["precipitation_mm", "rained", "ingested_at"],
            )

    def get_precipitation(
        self, location_id: int, start_date: date, end_date: date
    ) -> PrecipitationResult | None:
        with Session(self._engine) as session:
            loc = session.get(PluvioLocation, location_id)
            if not loc:
                return None
            rows = (
                session.query(PluvioPrecipitation)
                .filter(
                    PluvioPrecipitation.location_id == location_id,
                    PluvioPrecipitation.date >= start_date,
                    PluvioPrecipitation.date <= end_date,
                )
                .order_by(PluvioPrecipitation.date)
                .all()
            )
            return PrecipitationResult(
                latitude=float(loc.latitude),
                longitude=float(loc.longitude),
                start_date=start_date,
                end_date=end_date,
                records=[
                    PrecipitationRecord(
                        date=r.date,
                        precipitation_mm=float(r.precipitation_mm)
                        if r.precipitation_mm is not None
                        else 0.0,
                        rained=r.rained,
                        source=r.source,
                    )
                    for r in rows
                ],
            )

    def missing_dates(self, location_id: int, start_date: date, end_date: date) -> list[date]:
        return self._missing_dates(location_id, start_date, end_date, PluvioPrecipitation)

    def upsert_soil_moisture(self, result: SoilMoistureResult, location_id: int) -> int:
        rows = [
            {
                "location_id": location_id,
                "date": r.date,
                "swvl1": r.swvl1,
                "swvl2": r.swvl2,
                "swvl3": r.swvl3,
                "source": r.source,
            }
            for r in result.records
        ]
        with self._session() as session:
            return self._upsert_rows(
                session,
                PluvioSoilMoisture,
                rows,
                update_columns=["swvl1", "swvl2", "swvl3", "ingested_at"],
            )

    def get_soil_moisture(
        self, location_id: int, start_date: date, end_date: date
    ) -> SoilMoistureResult | None:
        with Session(self._engine) as session:
            loc = session.get(PluvioLocation, location_id)
            if not loc:
                return None
            rows = (
                session.query(PluvioSoilMoisture)
                .filter(
                    PluvioSoilMoisture.location_id == location_id,
                    PluvioSoilMoisture.date >= start_date,
                    PluvioSoilMoisture.date <= end_date,
                )
                .order_by(PluvioSoilMoisture.date)
                .all()
            )
            return SoilMoistureResult(
                latitude=float(loc.latitude),
                longitude=float(loc.longitude),
                start_date=start_date,
                end_date=end_date,
                records=[
                    SoilMoistureRecord(
                        date=r.date,
                        swvl1=float(r.swvl1),
                        swvl2=float(r.swvl2) if r.swvl2 is not None else None,
                        swvl3=float(r.swvl3) if r.swvl3 is not None else None,
                        source=r.source,
                    )
                    for r in rows
                ],
            )

    def _missing_dates(
        self, location_id: int, start_date: date, end_date: date, model: type
    ) -> list[date]:
        all_dates = {
            start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)
        }
        with Session(self._engine) as session:
            stored = {
                row.date
                for row in session.query(model.date).filter(
                    model.location_id == location_id,
                    model.date >= start_date,
                    model.date <= end_date,
                )
            }
        return sorted(all_dates - stored)

    def _upsert_rows(
        self,
        session: Session,
        model_class: type,
        rows: list[dict],
        update_columns: list[str],
    ) -> int:
        if not rows:
            return 0

        dialect = session.get_bind().dialect.name  # type: ignore[union-attr]

        if dialect == "postgresql":
            from sqlalchemy.dialects.postgresql import insert
        elif dialect == "sqlite":
            from sqlalchemy.dialects.sqlite import insert
        else:
            return self._upsert_fallback(session, model_class, rows)

        stmt = insert(model_class).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["location_id", "date"],
            set_={col: stmt.excluded[col] for col in update_columns},
        )
        session.execute(stmt)
        return len(rows)

    def _upsert_fallback(self, session: Session, model_class: type, rows: list[dict]) -> int:
        for row in rows:
            existing = (
                session.query(model_class)
                .filter_by(location_id=row["location_id"], date=row["date"])
                .first()
            )
            if existing:
                for k, v in row.items():
                    setattr(existing, k, v)
            else:
                session.add(model_class(**row))
        return len(rows)
