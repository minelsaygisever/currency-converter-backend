# src/rate_history/jobs.py

import json
import logging
from datetime import datetime, timezone, timedelta
from sqlmodel import select
from sqlalchemy import text

from src.core.database import get_session
from src.core.redis_client import get_redis_client
from src.currency.service import _get_all_rates_from_usd
from src.currency.exceptions import CurrencyAPIError
from .models import CurrencyRateSnapshot
from .repo import upsert_snapshot, get_latest

logger = logging.getLogger(__name__)

def floor_to_hour(dt: datetime) -> datetime:
    """Floors a datetime object to the beginning of the hour in UTC."""
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.replace(minute=0, second=0, microsecond=0)

async def run_hourly_job():
    """
    Fetches latest rates, saves them as an hourly snapshot, and cleans up old data.
    If the external API fails, it forward-fills from the last known snapshot.
    """
    bucket = floor_to_hour(datetime.now(timezone.utc))
    rates = None

    # 1) Fetch from external API
    try:
        rates = await _get_all_rates_from_usd()
        logger.info(f"Successfully fetched rates from external API for hourly job at {bucket}.")
    except CurrencyAPIError as e:
        logger.warning(f"External API failed for hourly job: {e}. Attempting to forward-fill.")
        with next(get_session()) as session:
            latest_snapshot = get_latest(session, frequency="hourly", base_currency="USD")
            if latest_snapshot:
                rates = latest_snapshot.rates
                logger.info("Successfully forward-filled rates from the last hourly snapshot.")
            else:
                logger.error("External API failed AND no previous snapshot found. Cannot proceed.")
                return

    if not rates:
        logger.error("No rates could be determined for the hourly job. Aborting.")
        return

    # 2) DB upsert and retention
    with next(get_session()) as session:
        upsert_snapshot(
            session=session,
            frequency="hourly",
            effective_at=bucket,
            base_currency="USD",
            rates=rates,
        )
        logger.info(f"Upserted hourly snapshot for {bucket}.")
        
        # Retention: Delete hourly data older than 30 days
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        stmt = text("DELETE FROM currency_rate_snapshots WHERE frequency='hourly' AND effective_at < :cutoff")
        result = session.exec(stmt, {"cutoff": thirty_days_ago})
        session.commit()
        if result.rowcount > 0:
            logger.info(f"Deleted {result.rowcount} old hourly snapshots.")

    # 3) Update live cache in Redis (TTL should be less than an hour)
    redis_client = get_redis_client()
    if redis_client:
        # TTL is 55 mins to ensure it expires before the next job, forcing a refresh
        redis_client.set("latest_usd_rates", json.dumps(rates), ex=55 * 60)
        logger.info("Updated 'latest_usd_rates' cache in Redis with TTL 55 minutes.")

async def run_daily_job():
    """
    Creates a daily snapshot using the last hourly snapshot of the previous day.
    """
    utc_now = datetime.now(timezone.utc)
    # Target yesterday's data
    yesterday_start_utc = (utc_now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_end_utc = yesterday_start_utc + timedelta(days=1) - timedelta(microseconds=1)

    with next(get_session()) as session:
        # Find the last hourly record from yesterday
        last_hour_of_yesterday = session.exec(
            select(CurrencyRateSnapshot)
            .where(
                CurrencyRateSnapshot.frequency == "hourly",
                CurrencyRateSnapshot.base_currency == "USD",
                CurrencyRateSnapshot.effective_at >= yesterday_start_utc,
                CurrencyRateSnapshot.effective_at <= yesterday_end_utc,
            )
            .order_by(CurrencyRateSnapshot.effective_at.desc())
            .limit(1)
        ).first()

        # If yesterday had no data, fall back to the absolute latest hourly data we have
        if not last_hour_of_yesterday:
            last_hour_of_yesterday = get_latest(session, frequency="hourly", base_currency="USD")
            logger.warning(f"No hourly data for {yesterday_start_utc.date()}. Using latest available snapshot for daily job.")

        if not last_hour_of_yesterday:
            logger.error("Could not find any hourly snapshot to create a daily record. Aborting daily job.")
            return

        # Create the daily snapshot for yesterday
        upsert_snapshot(
            session=session,
            frequency="daily",
            effective_at=yesterday_start_utc, # The timestamp represents the beginning of the day
            base_currency="USD",
            rates=last_hour_of_yesterday.rates,
        )
        logger.info(f"Upserted daily snapshot for {yesterday_start_utc.date()}.")
        
        # Retention: Delete daily data older than 5 years
        five_years_ago = utc_now - timedelta(days=5*365)

        stmt = text("DELETE FROM currency_rate_snapshots WHERE frequency='daily' AND effective_at < :cutoff")
        result = session.exec(stmt, {"cutoff": five_years_ago})
        
        session.commit()
        if result.rowcount > 0:
            logger.info(f"Deleted {result.rowcount} old daily snapshots.")