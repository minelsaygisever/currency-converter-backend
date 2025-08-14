# src/rate_history/service.py

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List

from sqlmodel import Session
from . import repo
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
        cache_key = f"raw_snapshots:{frequency}:{days_to_fetch}d"
        
        if self.redis:
            cached_data = self.redis.get(cache_key)
            if cached_data:
                logger.info(f"RAW CACHE HIT for key: {cache_key}")
                snapshot_dicts = json.loads(cached_data)
                return [CurrencyRateSnapshot.model_validate(d) for d in snapshot_dicts]

        logger.info(f"RAW CACHE MISS for key: {cache_key}. Fetching from DB.")
        
        end_date = datetime.now(timezone.utc).replace(minute=59, second=59, microsecond=999999)
        start_date = end_date - timedelta(days=days_to_fetch)

        db_rows = repo.get_range(
            self.session, frequency=frequency, start=start_date, end=end_date, base_currency="USD"
        )
        
        if self.redis and db_rows:
            ttl_seconds = 3600 if frequency == 'hourly' else 86400
            snapshot_dicts = [row.model_dump(mode='json') for row in db_rows]
            self.redis.set(cache_key, json.dumps(snapshot_dicts), ex=ttl_seconds)
            logger.info(f"RAW CACHE SET for key: {cache_key} with TTL: {ttl_seconds}s")

        return db_rows
    
    def _aggregate_monthly(self, daily_data: List[CurrencyRateSnapshot]) -> List[CurrencyRateSnapshot]:
        """Aggregates daily data to monthly by taking the last day of each month."""
        monthly_points = {}
        for snapshot in daily_data:
            month_identifier = snapshot.effective_at.strftime('%Y-%m')
            monthly_points[month_identifier] = snapshot
        
        return sorted(list(monthly_points.values()), key=lambda x: x.effective_at)


    def _aggregate_weekly(self, daily_data: List[CurrencyRateSnapshot]) -> List[CurrencyRateSnapshot]:
        """Aggregates daily data to weekly by taking the last day of each week."""
        weekly_points = {}
        for snapshot in daily_data:
            week_identifier = snapshot.effective_at.strftime('%Y-%U')
            weekly_points[week_identifier] = snapshot
        
        return sorted(list(weekly_points.values()), key=lambda x: x.effective_at)

    def _aggregate_8hourly(self, hourly_data: List[CurrencyRateSnapshot]) -> List[CurrencyRateSnapshot]:
        """Aggregates hourly data by taking the last record of each 8-hour period."""
        eight_hourly_points = {}
        for snapshot in hourly_data:
            day = snapshot.effective_at.strftime('%Y-%m-%d')
            time_slot = snapshot.effective_at.hour // 8 
            slot_identifier = f"{day}-{time_slot}"
            eight_hourly_points[slot_identifier] = snapshot
            
        return sorted(list(eight_hourly_points.values()), key=lambda x: x.effective_at)
    
    def _aggregate_every_n_days(self, daily_data: List[CurrencyRateSnapshot], n: int) -> List[CurrencyRateSnapshot]:
        """Aggregates daily data by taking the last day of each N-day period."""
        if n <= 1:
            return daily_data
            
        aggregated_points = {}
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        for snapshot in daily_data:
            days_since_epoch = (snapshot.effective_at - epoch).days
            period_identifier = days_since_epoch // n
            aggregated_points[period_identifier] = snapshot
        
        return sorted(list(aggregated_points.values()), key=lambda x: x.effective_at)


    def get_historical_data(self, range_str: str, base_currency: str = "USD") -> List[CurrencyRateSnapshot]:
        frequency = "hourly" if range_str in ("1d", "1w") else "daily"
        days = {"1d": 1, "1w": 7, "1m": 30, "6m": 182, "1y": 365, "5y": 365*5}.get(range_str, 30)
        
        raw_snapshots = self._get_raw_snapshots_with_cache(
            frequency=frequency,
            days_to_fetch=days
        )
        
        if range_str == "5y":
            logger.info(f"Aggregating {len(raw_snapshots)} daily points to monthly for '5y' range.")
            return self._aggregate_monthly(raw_snapshots)
            
        elif range_str == "1y":
            logger.info(f"Aggregating {len(raw_snapshots)} daily points to weekly for '1y' range.")
            return self._aggregate_weekly(raw_snapshots)

        elif range_str == "6m":
            logger.info(f"Aggregating {len(raw_snapshots)} daily points to every 2 days for '6m' range.")
            return self._aggregate_every_n_days(raw_snapshots, n=2)
        
        elif range_str == "1w":
            logger.info(f"Aggregating {len(raw_snapshots)} hourly points to 8-hourly for '1w' range.")
            return self._aggregate_8hourly(raw_snapshots)
        
        else:
            return raw_snapshots
        