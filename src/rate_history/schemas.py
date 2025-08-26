# src/rate_history/schemas.py

from pydantic import BaseModel, Field
from typing import Dict, List
from datetime import datetime

class HistoricalSnapshot(BaseModel):
    effective_at: datetime
    rates: Dict[str, float]

    class Config:
        from_attributes = True

HistoricalSnapshotResponse = List[HistoricalSnapshot]

class HistoricalRateData(BaseModel):
    from_currency: str
    to_currency: str
    date: str
    rate: float