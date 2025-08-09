# src/rate_history/service.py

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Tuple, List, Dict

from sqlmodel import Session
from . import repo
from .schemas import HistoricalDataResponse, HistoricalDataPoint
from src.core.redis_client import get_redis_client
from .models import CurrencyRateSnapshot

logger = logging.getLogger(__name__)

class HistoricalDataService:
    def __init__(self, session: Session):
        self.session = session
        self.redis = get_redis_client()


    def _get_raw_snapshots_with_cache(
        self, frequency: str, days_to_fetch: int
    ) -> List[CurrencyRateSnapshot]:
        """
        Fetches a list of raw snapshots (daily/hourly) from cache or DB.
        The cache TTL is now dynamic based on the data's update frequency.
        """
        cache_key = f"raw_snapshots:{frequency}:{days_to_fetch}d"
        
        # 1. Check cache for the raw data
        if self.redis:
            cached_data = self.redis.get(cache_key)
            if cached_data:
                logger.info(f"RAW CACHE HIT for key: {cache_key}")
                snapshot_dicts = json.loads(cached_data)
                return [CurrencyRateSnapshot.model_validate(d) for d in snapshot_dicts]

        logger.info(f"RAW CACHE MISS for key: {cache_key}. Fetching from DB.")
        
        # 2. If miss, fetch from DB
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=days_to_fetch)
        db_rows = repo.get_range(
            self.session, frequency=frequency, start=start_date, end=now, base_currency="USD"
        )
        
        # 3. Save the raw data to cache with the CORRECT TTL
        if self.redis and db_rows:
            if frequency == 'hourly':
                ttl_seconds = 3600  
            elif frequency == 'daily':
                ttl_seconds = 86400 
            else:
                ttl_seconds = 3600 

            snapshot_dicts = [row.model_dump(mode='json') for row in db_rows]
            self.redis.set(cache_key, json.dumps(snapshot_dicts), ex=ttl_seconds)
            logger.info(f"RAW CACHE SET for key: {cache_key} with TTL: {ttl_seconds}s")

        return db_rows

    def get_historical_data(self, range_str: str, base_currency: str = "USD") -> List[CurrencyRateSnapshot]:
        frequency = "hourly" if range_str in ("1d", "1w") else "daily"
        days = {"1d": 1, "1w": 7, "1m": 30, "6m": 182, "1y": 365, "5y": 365*5}.get(range_str, 30)
        
        raw_snapshots = self._get_raw_snapshots_with_cache(
            frequency=frequency,
            days_to_fetch=days
        )
        
        return raw_snapshots