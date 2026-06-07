from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from datetime import date

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from pluvio.extras.storage.models import PluvioBase, PluvioLocation, PluvioPrecipitation
from pluvio.models import PrecipitationRecord, PrecipitationResult


class PluvioStorage:
    """SQLAlchemy storage adapter for pluvio datasets.

    Works with PostgreSQL (recommended for production) and SQLite (dev/test).
    Uses dialect-aware upsert: ON CONFLICT DO UPDATE on both engines.

    Usage:
        from sqlalchemy import create_engine
        from pluvio.extras.storage import PluvioStorage

        storage = PluvioStorage(create_engine("postgresql://..."))
        storage.create_tables()

        location_id = storage.add_location("Impianto Nord", lat=45.4, lon=11.9)
        storage.upsert_precipitation(result, location_id)
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create_tables(self) -> None:
        """Create pluvio_* tables. Safe to call multiple times (CREATE IF NOT EXISTS)."""
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
        """Insert a new monitored location and return its id."""
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

    def upsert_precipitation(self, result: PrecipitationResult, location_id: int) -> int:
        """
        Upsert all records from a PrecipitationResult.
        Returns the number of rows written.
        """
        if not result.records:
            return 0

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
            return self._upsert(session, rows)

    def get_precipitation(
        self,
        location_id: int,
        start_date: date,
        end_date: date,
    ) -> PrecipitationResult | None:
        """
        Query stored precipitation for a location and date range.
        Returns None if the location does not exist.
        """
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
        """Return dates in [start_date, end_date] not yet stored for a location."""
        from datetime import timedelta

        all_dates = {
            start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)
        }

        with Session(self._engine) as session:
            stored = {
                row.date
                for row in session.query(PluvioPrecipitation.date).filter(
                    PluvioPrecipitation.location_id == location_id,
                    PluvioPrecipitation.date >= start_date,
                    PluvioPrecipitation.date <= end_date,
                )
            }

        return sorted(all_dates - stored)

    def _upsert(self, session: Session, rows: list[dict]) -> int:
        dialect = session.get_bind().dialect.name  # type: ignore[union-attr]

        if dialect == "postgresql":
            from sqlalchemy.dialects.postgresql import insert
        elif dialect == "sqlite":
            from sqlalchemy.dialects.sqlite import insert
        else:
            return self._upsert_fallback(session, rows)

        stmt = insert(PluvioPrecipitation).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["location_id", "date"],
            set_={
                "precipitation_mm": stmt.excluded.precipitation_mm,
                "rained": stmt.excluded.rained,
                "ingested_at": stmt.excluded.ingested_at,
            },
        )
        session.execute(stmt)
        return len(rows)

    def _upsert_fallback(self, session: Session, rows: list[dict]) -> int:
        """Generic upsert for databases without ON CONFLICT support."""
        for row in rows:
            existing = (
                session.query(PluvioPrecipitation)
                .filter_by(location_id=row["location_id"], date=row["date"])
                .first()
            )
            if existing:
                for k, v in row.items():
                    setattr(existing, k, v)
            else:
                session.add(PluvioPrecipitation(**row))
        return len(rows)
