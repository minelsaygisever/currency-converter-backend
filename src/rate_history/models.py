from __future__ import annotations
from typing import Dict
from datetime import datetime
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import UniqueConstraint

class CurrencyRateSnapshot(SQLModel, table=True):
    __tablename__ = "currency_rate_snapshots"
    __table_args__ = (
        UniqueConstraint("frequency", "effective_at", "base_currency", name="uq_crs"),
    )

    id: int | None = Field(default=None, primary_key=True)
    frequency: str = Field(index=True, description="hourly | daily")
    effective_at: datetime = Field(index=True, description="UTC bucket time")
    base_currency: str = Field(default="USD", index=True)
    rates: Dict[str, float] = Field(sa_column=Column(JSON), description="USD->X map")