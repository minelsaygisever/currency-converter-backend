# src/rate_history/service.py

import json
import logging
from datetime import datetime, timedelta, timezone
from datetime import date as date_obj
from typing import List
from fastapi import HTTPException

from sqlmodel import Session
from . import repo
from src.core.memory_cache import memory_cache
from .models import CurrencyRateSnapshot
from .schemas import HistoricalRatesResponse


logger = logging.getLogger(__name__)

class HistoricalDataService:
    def __init__(self, session: Session):
        self.session = session
        self.cache = memory_cache

    def _get_cached_or_fetch(
        self, 
        range_str: str, 
        ttl_seconds: int,
        fetch_func
    ) -> List[CurrencyRateSnapshot]:
        cache_key = f"history:{range_str}"
        
        cached_data = self.cache.get(cache_key)
        if cached_data:
            snapshot_dicts = json.loads(cached_data)
            return [CurrencyRateSnapshot.model_validate(d) for d in snapshot_dicts]

        logger.info(f"HISTORY CACHE MISS: {cache_key}. Fetching from DB...")
        
        data = fetch_func()
        
        if data:
            snapshot_dicts = [row.model_dump(mode='json') for row in data]
            self.cache.set(cache_key, json.dumps(snapshot_dicts), ex=ttl_seconds)
            logger.info(f"HISTORY CACHE SET: {cache_key} (TTL: {ttl_seconds}s)")
            
        return data
    
    def _aggregate_monthly(self, daily_data: List[CurrencyRateSnapshot]) -> List[CurrencyRateSnapshot]:
        """Aggregates daily data to monthly by taking the last day of each month."""
        monthly_points = {}
        for snapshot in daily_data:
            month_identifier = snapshot.effective_at.strftime('%Y-%m')
            monthly_points[month_identifier] = snapshot
        
        return sorted(list(monthly_points.values()), key=lambda x: x.effective_at)

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
        target_base = "USD" 
        end_date = datetime.now(timezone.utc)
        
        if range_str == "1d":
            return self._get_cached_or_fetch(
                range_str="1d",
                ttl_seconds=3600, # 1 H
                fetch_func=lambda: repo.get_range(
                    self.session, frequency="hourly", 
                    start=end_date - timedelta(days=1), end=end_date, 
                    base_currency=target_base
                )
            )

        elif range_str == "1w":
            def fetch_1w():
                raw = repo.get_range(
                    self.session, frequency="hourly", 
                    start=end_date - timedelta(days=7), end=end_date, 
                    base_currency=target_base
                )
                return self._aggregate_8hourly(raw)

            return self._get_cached_or_fetch(
                range_str="1w",
                ttl_seconds=3600, # 1 H
                fetch_func=fetch_1w
            )

        else: 
            ttl_long = 86400 # 24 H
            days = {"1m": 30, "6m": 182, "1y": 365, "5y": 365*5}.get(range_str, 30)
            start_date = end_date - timedelta(days=days)
            
            def fetch_long_range():
                raw_snapshots = repo.get_range(
                    self.session, frequency="daily", 
                    start=start_date, end=end_date, 
                    base_currency=target_base
                )
                
                if range_str == "1m": return raw_snapshots
                elif range_str == "6m": return self._aggregate_every_n_days(raw_snapshots, n=3)
                elif range_str == "1y": return self._aggregate_every_n_days(raw_snapshots, n=7)
                elif range_str == "5y": return self._aggregate_monthly(raw_snapshots)
                return raw_snapshots

            return self._get_cached_or_fetch(
                range_str=range_str,
                ttl_seconds=ttl_long,
                fetch_func=fetch_long_range
            )
        
    
    def get_rate_for_date(self, date_str: str) -> HistoricalRatesResponse:
        """
        Fetches and returns the raw USD-based rates for a specific date.
        """
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

        # Find the daily snapshot for the requested date (or the closest one before it)
        snapshot = repo.get_daily_snapshot_for_date(self.session, target_date, "USD")

        # If there is no daily data and the requested date is today, search for the latest hourly data
        if not snapshot and target_date.date() == date_obj.today():
            print(f"No daily snapshot for {date_str}, searching for latest hourly snapshot...")
            snapshot = repo.get_latest_hourly_for_date(self.session, target_date, "USD")


        if not snapshot:
            raise HTTPException(status_code=404, detail=f"No historical rate data found on or before {date_str}.")
                    
        return HistoricalRatesResponse(rates=snapshot.rates)
    
