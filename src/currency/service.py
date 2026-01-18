# src/currency/service.py

import time
import json
import logging
from typing import List, Dict, Set
from sqlmodel import Session

from src.core.config import settings
from src.core.redis_client import get_redis_client 
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


async def _get_all_rates_from_usd() -> Dict[str, float]:
    cache_key = "latest_usd_rates"
    redis_client = get_redis_client()
    
    if redis_client:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            logger.info("CACHE HIT: Rates found in Redis.")
            return json.loads(cached_data)

    logger.info("CACHE MISS: Initiating API fetch sequence (Primary: OER, Secondary: CDN)...")
    
    
    required_codes: Set[str] = set()
    try:
        with Session(engine) as session:
            db_codes = repo.get_all_active_currency_codes(session)
            required_codes = {code.upper() for code in db_codes}
        logger.info(f"Required currencies from DB: {len(required_codes)}")
    except Exception as e:
        logger.error(f"DB Error (fetching codes): {e}")

    rates = {}
    primary_failed = False

    try:
        rates = await _fetch_primary_oer()
        if rates:
            logger.info(f"Primary API (OER) returned {len(rates)} currencies.")
        else:
            logger.warning("Primary API returned empty list.")
            primary_failed = True
    except Exception as e:
        logger.error(f"Primary API failed: {e}")
        primary_failed = True
        rates = {}

    fetched_keys = set(rates.keys())
    missing_currencies = required_codes - fetched_keys
    
    should_use_secondary = False
    
    if primary_failed:
        logger.warning("Primary API failed. Switching to Secondary.")
        should_use_secondary = True
    elif missing_currencies:
        logger.warning(f"Primary API OK but missing codes: {missing_currencies}. Fetching Secondary to fill gaps.")
        should_use_secondary = True
    else:
        logger.info("Primary API provided all required currencies. No need for Secondary.")

    if should_use_secondary:
        try:
            secondary_rates = await _fetch_secondary_cdn()
            
            if secondary_rates:
                filled_count = 0
                for code, rate in secondary_rates.items():
                    if code not in rates:
                        rates[code] = rate
                        filled_count += 1
                
                logger.info(f"Secondary Merge Complete: Added {filled_count} missing currencies.")
            else:
                logger.warning("Secondary API returned empty rates.")

        except Exception as e:
            logger.error(f"Secondary API failed: {e}")

    if not rates:
        raise CurrencyAPIError(code=502, message="All currency data sources are unavailable.")

    if redis_client:
        redis_client.set(cache_key, json.dumps(rates), ex=settings.CACHE_TTL_SECONDS)
    
    return rates


async def get_conversion_rates(from_sym: str, to_syms: List[str]) -> Dict[str, float]:
    """
    Calculates conversion rates using a cached master list of USD-based rates.
    It does NOT make an external API call directly.
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
    """
    Manually deletes the exchange rates cache key from Redis.
    Forces the next request to fetch fresh data from the external API.
    """
    cache_key = "latest_usd_rates"
    redis_client = get_redis_client()
    
    if redis_client:
        redis_client.delete(cache_key)
        logger.info(f"CACHE CLEARED: Key '{cache_key}' was manually deleted.")
        return True
    
    logger.warning("CACHE CLEAR FAILED: Redis client not available.")
    return False