# src/rate_history/router.py

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

import logging

from .schemas import HistoricalSnapshotResponse
from src.core.database import get_session
from src.core.security import verify_api_key
from .service import HistoricalDataService
from .jobs import run_hourly_job, run_daily_job 

from src.core.redis_client import get_redis_client
import redis 

router = APIRouter(
    prefix="/history",
    tags=["History"],
    dependencies=[Depends(verify_api_key)] 
)

logger = logging.getLogger(__name__)

# Dependency to provide the service
def get_historical_service(session: Session = Depends(get_session)) -> HistoricalDataService:
    return HistoricalDataService(session)

@router.get("", response_model=HistoricalSnapshotResponse)
def get_historical_snapshots(
    range_: str = Query("1m", alias="range", description="Time range for data: 1d, 1w, 1m, 6m, 1y, 5y"),
    base: str = Query("USD", description="The base currency for the snapshots"),
    service: HistoricalDataService = Depends(get_historical_service),
):
    """
    Provides a list of raw historical snapshots (all rates vs. base) for a given range.
    The client is responsible for calculating the cross-rates.
    """
    return service.get_historical_data(range_str=range_, base_currency=base)

@router.post("/admin/clear-cache", summary="Clear a specific cache key in Redis")
def clear_specific_cache(
    cache_key: str = Query(..., description="The exact cache key to delete"),
    redis_client: redis.Redis = Depends(get_redis_client),
    _ = Depends(verify_api_key) 
):
    """
    Deletes a specific key from the Redis cache. 
    USE WITH CAUTION.
    """
    logger.info(f"Attempting to delete cache key: {cache_key}")
    deleted_count = redis_client.delete(cache_key)
    
    if deleted_count > 0:
        message = f"Successfully deleted cache key: '{cache_key}'"
        logger.info(message)
        return {"status": "success", "message": message}
    else:
        message = f"Cache key not found or already deleted: '{cache_key}'"
        logger.warning(message)
        return {"status": "not_found", "message": message}


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