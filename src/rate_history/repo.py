# src/rate_history/repo.py

from datetime import datetime
from typing import List, Dict
from sqlmodel import Session, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .models import CurrencyRateSnapshot

def upsert_snapshot(
    session: Session,
    *,
    frequency: str,
    effective_at: datetime,
    base_currency: str,
    rates: Dict[str, float]
) -> CurrencyRateSnapshot:
    """
    Atomically inserts a new snapshot or updates an existing one for the same
    frequency, timestamp, and base currency using PostgreSQL's ON CONFLICT.
    """
    # 1. Values to insert or update
    values_to_insert = {
        "frequency": frequency,
        "effective_at": effective_at,
        "base_currency": base_currency,
        "rates": rates
    }

    # 2. Build the "INSERT ... ON CONFLICT" statement
    stmt = pg_insert(CurrencyRateSnapshot).values(values_to_insert)
    
    # 3. Define what to do on conflict (update the 'rates' column)
    # The conflict target is the unique constraint 'uq_crs' we defined in the model.
    stmt = stmt.on_conflict_do_update(
        constraint="uq_crs",
        set_={"rates": stmt.excluded.rates}
    )

    # 4. Execute and commit
    session.execute(stmt)
    session.commit()
    
    # 5. Return the newly inserted/updated object
    return session.exec(
        select(CurrencyRateSnapshot).where(
            CurrencyRateSnapshot.frequency == frequency,
            CurrencyRateSnapshot.effective_at == effective_at,
            CurrencyRateSnapshot.base_currency == base_currency
        )
    ).one()


def get_range(
    session: Session,
    *,
    frequency: str,
    start: datetime,
    end: datetime,
    base_currency: str = "USD"
) -> List[CurrencyRateSnapshot]:
    """
    Fetches a range of snapshots for a given frequency and time window.
    """
    stmt = (
        select(CurrencyRateSnapshot)
        .where(
            CurrencyRateSnapshot.frequency == frequency,
            CurrencyRateSnapshot.base_currency == base_currency,
            CurrencyRateSnapshot.effective_at >= start,
            CurrencyRateSnapshot.effective_at <= end,
        )
        .order_by(CurrencyRateSnapshot.effective_at)
    )
    return list(session.exec(stmt).all())

def get_latest(session: Session, *, frequency: str, base_currency: str = "USD") -> CurrencyRateSnapshot | None:
    """
    Fetches the single most recent snapshot for a given frequency.
    """
    stmt = (
        select(CurrencyRateSnapshot)
        .where(
            CurrencyRateSnapshot.frequency == frequency,
            CurrencyRateSnapshot.base_currency == base_currency,
        )
        .order_by(CurrencyRateSnapshot.effective_at.desc())
        .limit(1)
    )
    return session.exec(stmt).first()