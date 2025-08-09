# src/rate_history/router.py

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from src.core.database import get_session
from src.core.security import verify_api_key
from .service import HistoricalDataService
from .schemas import HistoricalDataResponse
from .jobs import run_hourly_job, run_daily_job # Keep job triggers

router = APIRouter(
    prefix="/history",
    tags=["History"],
    dependencies=[Depends(verify_api_key)] # Apply security to all routes in this router
)

# Dependency to provide the service
def get_historical_service(session: Session = Depends(get_session)) -> HistoricalDataService:
    return HistoricalDataService(session)

@router.get(
    "",
    response_model=HistoricalDataResponse,
    response_model_by_alias=True 
)
def get_historical_rates(
    from_symbol: str = Query(..., alias="from", description="Source currency code, e.g., USD"),
    to_symbol: str = Query(..., alias="to", description="Target currency code, e.g., EUR"),
    range_: str = Query(
        "1m", 
        alias="range",
        description="Time range for data: 1d, 1w, 1m, 6m, 1y, 5y"
    ),
    service: HistoricalDataService = Depends(get_historical_service),
):
    """
    Provides historical exchange rate data for a currency pair over a specified range.
    
    - **1d, 1w ranges**: Return hourly data points.
    - **1m, 6m, 1y, 5y ranges**: Return daily data points.
    
    Results are cached to improve performance.
    """
    return service.get_historical_data(
        from_symbol=from_symbol, to_symbol=to_symbol, range_str=range_
    )


# --- Manual Job Triggers ---

@router.post("/jobs/trigger-hourly", summary="Manually Trigger Hourly Job")
async def trigger_hourly(_: str = Depends(verify_api_key)):
    """Manually triggers the job to fetch and store the latest hourly rates."""
    await run_hourly_job()
    return {"status": "Hourly job triggered successfully."}

@router.post("/jobs/trigger-daily", summary="Manually Trigger Daily Job")
async def trigger_daily(_: str = Depends(verify_api_key)):
    """Manually triggers the job to consolidate the daily rate from hourly data."""
    await run_daily_job()
    return {"status": "Daily job triggered successfully."}