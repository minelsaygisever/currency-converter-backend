# src/currency/service.py

import time
import json
import logging
from typing import List, Dict, Set
from sqlmodel import Session
from datetime import datetime, timezone, timedelta

from src.core.config import settings
from src.core.memory_cache import memory_cache 
from src.core.database import engine
from src.currency import repo
from .exceptions import CurrencyAPIError
import httpx 

logger = logging.getLogger(__name__)

async def _fetch_primary_oer() -> dict:
    if not settings.OPEN_EXCHANGE_RATES_API_KEY:
        logger.warning("Primary API Key (OER) is missing.")
        return {}

    url = f"{settings.OPEN_EXCHANGE_RATES_API_URL}?app_id={settings.OPEN_EXCHANGE_RATES_API_KEY}"
    logger.info("Fetching from PRIMARY API (OpenExchangeRates)...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("rates", {})

async def _fetch_secondary_cdn() -> dict:
    url = settings.CURRENCY_API_URL_SECONDARY 
    logger.info(f"Fetching from SECONDARY API (CDN Gap Filler): {url}")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        raw_rates = data.get("usd", {})
        standardized_rates = {k.upper(): v for k, v in raw_rates.items()}
        
        if "USD" not in standardized_rates:
            standardized_rates["USD"] = 1.0
            
        return standardized_rates

async def _fetch_and_merge_api_data() -> Dict[str, float]:
    """
    It generates data by combining Primary and Secondary APIs.
    """
    required_codes: Set[str] = set()
    try:
        with Session(engine) as session:
            db_codes = repo.get_all_active_currency_codes(session)
            required_codes = {code.upper() for code in db_codes}
    except Exception as e:
        logger.error(f"DB Error (fetching codes): {e}")

    rates = {}
    primary_failed = False

    # 1. Primary Fetch
    try:
        rates = await _fetch_primary_oer()
        if not rates:
            primary_failed = True
    except Exception as e:
        logger.error(f"Primary API failed: {e}")
        primary_failed = True

    # 2. Check Gaps
    fetched_keys = set(rates.keys())
    missing_currencies = required_codes - fetched_keys
    should_use_secondary = primary_failed or bool(missing_currencies)

    # 3. Secondary Fetch (if needed)
    if should_use_secondary:
        try:
            secondary_rates = await _fetch_secondary_cdn()
            if secondary_rates:
                for code, rate in secondary_rates.items():
                    if code not in rates:
                        rates[code] = rate
            else:
                logger.warning("Secondary API returned empty rates.")
        except Exception as e:
            logger.error(f"Secondary API failed: {e}")

    return rates


async def _get_all_rates_from_usd() -> Dict[str, float]:
    cache_key = "latest_usd_rates"

    cached_data = memory_cache.get(cache_key)
    if cached_data:
        logger.info("CACHE HIT: Rates found in Memory.")
        return json.loads(cached_data)

    logger.info("CACHE MISS: Checking Database backup before external API...")

    rates = {}

    try:
        with Session(engine) as session:
            cache_entry = repo.get_exchange_rate_cache(session, base_currency="USD")
            
            if cache_entry and cache_entry.updated_at:
                last_update = cache_entry.updated_at
                if last_update.tzinfo is None:
                    last_update = last_update.replace(tzinfo=timezone.utc)
                
                age = datetime.now(timezone.utc) - last_update
                
                if age < timedelta(minutes=65):
                    logger.info(f"DB FALLBACK: Found fresh data (Age: {age}). Loading to Memory.")
                    rates = cache_entry.rates
                else:
                    logger.info(f"DB data is too old (Age: {age}). Need fresh data.")

    except Exception as e:
        logger.error(f"DB Fallback failed: {e}")

    if not rates:
        logger.warning("Fetching from External API...")
        
        rates = await _fetch_and_merge_api_data()
        
        if rates:
            try:
                with Session(engine) as session:
                    repo.upsert_exchange_rate_cache(session, base_currency="USD", rates=rates)
                    logger.info("Saved fresh rates to Postgres DB backup via Repo.")
            except Exception as e:
                logger.error(f"Could not save backup to DB: {e}")

    if not rates:
        raise CurrencyAPIError(code=502, message="All currency data sources are unavailable.")

    memory_cache.set(cache_key, json.dumps(rates), ex=settings.CACHE_TTL_SECONDS) 

    return rates


async def get_conversion_rates(from_sym: str, to_syms: List[str]) -> Dict[str, float]:
    """
    Calculates conversion rates using a cached master list of USD-based rates.
    """

    all_rates_vs_usd = await _get_all_rates_from_usd()

    from_sym_upper = from_sym.upper()

    # the exchange rate of the desired 'from' currency against USD
    usd_to_from_rate = all_rates_vs_usd.get(from_sym_upper)
    if usd_to_from_rate is None:
        raise CurrencyAPIError(code=400, message=f"Base currency '{from_sym_upper}' is not supported.")

    cross_rates: Dict[str, float] = {}
    for to_sym in to_syms:
        to_sym_upper = to_sym.upper()
        if to_sym_upper == from_sym_upper:
            continue

        # the exchange rate of the desired 'to' currency against USD
        usd_to_to_rate = all_rates_vs_usd.get(to_sym_upper)
        if usd_to_to_rate is None:
            logger.warning(f"Target currency '{to_sym_upper}' not found in rate list. Skipping.")
            continue
            
        # Cross rate calculation
        # EUR -> TRY = (USD -> TRY) / (USD -> EUR)
        cross_rate = usd_to_to_rate / usd_to_from_rate
        cross_rates[to_sym_upper] = cross_rate
        
    return cross_rates


async def invalidate_rates_cache():
    cache_key = "latest_usd_rates"

    memory_cache.delete(cache_key)
    logger.info(f"CACHE CLEARED: Key '{cache_key}' was manually deleted.")
    return True