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

class HistoricalRatesResponse(BaseModel):
    rates: Dict[str, float]

class AdminStatusResponse(BaseModel):
    """
    A general status response for admin endpoints or job triggers.
    """
    status: str
    message: str | None = None