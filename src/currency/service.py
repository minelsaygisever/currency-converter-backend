# src/currency/service.py

import time
import json
import logging
from typing import List, Dict

from src.core.config import settings
from src.core.redis_client import redis_client # Import our Redis client
from .exceptions import CurrencyAPIError
import httpx 

logger = logging.getLogger(__name__)

async def get_conversion_rates_fixer(from_sym: str, to_syms: List[str]) -> Dict[str, float]:
    """
    Fetches conversion rates. First, it checks for a cached result in Redis.
    If not found, it fetches from the Fixer API and caches the result in Redis.
    
    - from_sym: "USD"
    - to_syms:  ["EUR","TRY","GBP",...]
    - return:   { "EUR": 0.92, "TRY": 32.85, "GBP": 0.78, ... }
    """
    
    # redis cache check:
    cache_key = f"rates:{from_sym}"

    if redis_client:
        cached_rates = redis_client.get(cache_key)
        if cached_rates:
            logger.info(f"Cache HIT for key: {cache_key}")
            # The data in Redis is stored as a JSON string, so we need to decode it.
            return json.loads(cached_rates)

    logger.info(f"Cache MISS for key: {cache_key}. Fetching from Fixer API.")

    if not settings.FIXER_API_KEY:
        raise CurrencyAPIError(code=500, message="Server configuration error: missing FIXER_API_KEY.")

    to_syms_upper = [sym.upper() for sym in to_syms if sym.upper() != from_sym]
    all_symbols = [from_sym, "EUR"] + to_syms_upper
    unique_symbols = list(dict.fromkeys(all_symbols))

    params = {
        "access_key": settings.FIXER_API_KEY,
        "symbols": ",".join(unique_symbols)
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(settings.FIXER_API_URL, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
    except httpx.RequestException as e:
        raise CurrencyAPIError(code=502, message=f"External API request failed: {e}")
    except ValueError:
        raise CurrencyAPIError(code=502, message="External API returned invalid JSON.")

    if not data.get("success", False):
        error_info = data.get("error", {})
        raise CurrencyAPIError(code=502, message=f"Fixer API error: {error_info.get('info')}")

    rates = data.get("rates", {})  # {"EUR":1.0,"USD":1.08,"TRY":19.53,...}
    eur_to_from = rates.get(from_sym.upper())
    if eur_to_from is None:
        raise CurrencyAPIError(code=502, message=f"Fixer API did not return rate for {from_sym}")

    cross_rates: Dict[str, float] = {}
    for to_sym in to_syms:
        eur_to_to = rates.get(to_sym)
        if eur_to_to is None:
            raise CurrencyAPIError(code=502, message=f"Fixer API did not return rate for {to_sym}")

        cross_rate = eur_to_to / eur_to_from
        cross_rates[to_sym] = round(cross_rate, 6)

    #  Save the new result to redis
    if redis_client and cross_rates:
        redis_client.set(cache_key, json.dumps(cross_rates), ex=settings.CACHE_TTL_SECONDS)
        logger.info(f"Saved new rates to cache for key: {cache_key}")

    return cross_rates
