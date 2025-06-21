# src/currency/service.py

import time
import json
import logging
from typing import List, Dict

from src.core.config import settings
from src.core.redis_client import get_redis_client # Import our Redis client
from .exceptions import CurrencyAPIError
import httpx 

logger = logging.getLogger(__name__)

async def _get_all_rates_from_usd() -> Dict[str, float]:
    """
    Fetches all available currency rates against the base currency (USD)
    from the external API and caches the result in Redis.
    This function is the single point of contact with the external API.
    """
    
    # 1. Cache Check: All exchange rates will be stored under a single key.
    cache_key = "latest_usd_rates"
    redis_client = get_redis_client()
    if redis_client:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            logger.info(f"CACHE HIT: Found all rates under key '{cache_key}'.")
            return json.loads(cached_data)

    # 2. Cache miss, pull it from API.
    logger.info(f"CACHE MISS: Key '{cache_key}' not found. Fetching from OpenExchangeRates API.")
    

    if not settings.OPEN_EXCHANGE_RATES_API_KEY:
        raise CurrencyAPIError(code=500, message="Server configuration error: missing OPEN_EXCHANGE_RATES_API_KEY.")

    api_url = f"{settings.OPEN_EXCHANGE_RATES_API_URL}?app_id={settings.OPEN_EXCHANGE_RATES_API_KEY}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except httpx.RequestError as e:
        raise CurrencyAPIError(code=502, message=f"External API request failed: {e}")
    except ValueError:
        raise CurrencyAPIError(code=502, message="External API returned invalid JSON.")

    if "error" in data:
        raise CurrencyAPIError(code=data.get("status"), message=data.get("description"))

    rates = data.get("rates", {}) # {"AED": 3.67, "AFN": 71.8,... "USD": 1.0, ...}

    # 3. Save the new result to redis
    if redis_client and rates:
        redis_client.set(cache_key, json.dumps(rates), ex=settings.CACHE_TTL_SECONDS)
        logger.info(f"CACHE SET: Saved all rates to key '{cache_key}'.")
        
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
        cross_rates[to_sym_upper] = round(cross_rate, 6)
        
    return cross_rates