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


    def _aggregate_weekly_relative(
        self, daily_data: List[CurrencyRateSnapshot], request_time: datetime
    ) -> List[CurrencyRateSnapshot]:
        """
        Aggregates daily data into weekly points, where 'week end' is relative
        to the day of the request.
        """
        target_weekday = request_time.weekday() # Monday is 0 and Sunday is 6
        weekly_points = {}
        for snapshot in reversed(daily_data):
            week_identifier = snapshot.effective_at.strftime('%Y-%U')
            if week_identifier not in weekly_points and snapshot.effective_at.weekday() == target_weekday:
                weekly_points[week_identifier] = snapshot
        
        # weekly_points'in value'larını alıp tarihe göre sırala
        return sorted(list(weekly_points.values()), key=lambda x: x.effective_at)


    def _aggregate_8hourly_relative(
        self, hourly_data: List[CurrencyRateSnapshot], request_time: datetime
    ) -> List[CurrencyRateSnapshot]:
        """
        Picks hourly snapshots at roughly 8-hour intervals, relative to the request time.
        """
        points = []
        for i in range(21): 
            target_time = request_time - timedelta(hours=i * 8)
            closest_snapshot = min(
                hourly_data, 
                key=lambda x: abs(x.effective_at - target_time),
                default=None
            )
            if closest_snapshot:
                points.append(closest_snapshot)
        
        unique_points = sorted(
            list({p.id: p for p in points}.values()),
            key=lambda x: x.effective_at
        )
        return unique_points

    def get_historical_data(
        self, from_symbol: str, to_symbol: str, range_str: str
    ) -> HistoricalDataResponse:
        
        request_time = datetime.now(timezone.utc)
        from_upper = from_symbol.upper()
        to_upper = to_symbol.upper()
        
        aggregated_snapshots = []
        final_frequency = ""

        if range_str == "1w":
            final_frequency = "8-hourly"
            hourly_snapshots = self._get_raw_snapshots_with_cache(frequency="hourly", days_to_fetch=7)
            aggregated_snapshots = self._aggregate_8hourly_relative(hourly_snapshots, request_time)

        elif range_str == "5y":
            final_frequency = "weekly"
            daily_snapshots = self._get_raw_snapshots_with_cache(frequency="daily", days_to_fetch=5*365)
            aggregated_snapshots = self._aggregate_weekly_relative(daily_snapshots, request_time)
            
        else:
            final_frequency = "daily" if range_str != "1d" else "hourly"
            days = {"1d": 1, "1m": 30, "6m": 182, "1y": 365}.get(range_str, 30)
            aggregated_snapshots = self._get_raw_snapshots_with_cache(frequency=final_frequency, days_to_fetch=days)


        points: List[HistoricalDataPoint] = []
        for row in aggregated_snapshots:
            if from_upper in row.rates and to_upper in row.rates:
                from_rate = row.rates.get(from_upper, 1.0)
                if from_rate == 0: continue
                
                cross_rate = row.rates[to_upper] / from_rate
                points.append(HistoricalDataPoint(ts=row.effective_at, rate=cross_rate))
        
        return HistoricalDataResponse(
            **{
                "from": from_upper,
                "to": to_upper,
                "frequency": final_frequency,
                "points": points,
            }
        )