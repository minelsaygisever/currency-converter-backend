# src/rate_history/schemas.py

from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

class HistoricalDataPoint(BaseModel):
    """Represents a single data point in a time series (timestamp and rate)."""
    ts: datetime = Field(..., description="The timestamp for the data point (UTC).")
    rate: float = Field(..., description="The calculated exchange rate at this timestamp.")

class HistoricalDataResponse(BaseModel):
    """The response model for a historical data request."""
    from_symbol: str = Field(..., alias="from", description="Source currency code.")
    to_symbol: str = Field(..., alias="to", description="Target currency code.")
    frequency: str = Field(..., description="The frequency of data points ('hourly' or 'daily').")
    points: List[HistoricalDataPoint] = Field(..., description="List of historical data points.")
    
    class Config:
        populate_by_name = True # Allows using 'from' as an argument
        json_encoders = {
            datetime: lambda v: v.isoformat().replace('+00:00', 'Z')
        }