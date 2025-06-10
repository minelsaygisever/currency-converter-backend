# src/currency/service.py

import os
import time
import requests
from typing import Tuple, List, Dict
from .exceptions import CurrencyAPIError

FIXER_API_URL = "http://data.fixer.io/api/latest"

# ---------------------------------------------------
# in-memory cache:
#    { from: (timestamp_add, {to: rate, ...}) }
# ---------------------------------------------------
_CACHE: Dict[str, tuple[float, Dict[str, float]]] = {}
_CACHE_TTL = 3600  # saniye cinsinden: 1 saat

def get_conversion_rates_fixer(from_sym: str, to_syms: List[str]) -> Dict[str, float]:
    """
    - from_sym: "USD"
    - to_syms:  ["EUR","TRY","GBP",...]
    - return:   { "EUR": 0.92, "TRY": 8.56, "GBP": 0.78, ... }
    """
    
    # cache check:
    cache_entry = _CACHE.get(from_sym)
    if cache_entry:
        timestamp, cached_rates = cache_entry
        if (time.time() - timestamp) < _CACHE_TTL:
            # Cache hit
            return cached_rates

    api_key = os.getenv("FIXER_API_KEY")
    if not api_key:
        raise CurrencyAPIError(code=500, message="Server configuration error: missing FIXER_API_KEY.")

    to_syms_upper = [sym.upper() for sym in to_syms if sym.upper() != from_sym]
    all_symbols = [from_sym, "EUR"] + to_syms_upper
    unique_symbols = list(dict.fromkeys(all_symbols))

    params = {
        "access_key": api_key,
        "symbols": ",".join(unique_symbols)
    }

    try:
        response = requests.get(FIXER_API_URL, params=params, timeout=5)
        data = response.json()
    except requests.RequestException as e:
        raise CurrencyAPIError(code=502, message=f"External API request failed: {e}")
    except ValueError:
        raise CurrencyAPIError(code=502, message="External API returned invalid JSON.")

    if not data.get("success", False):
        error_info = data.get("error", {})
        code       = error_info.get("code", 0)
        info       = error_info.get("info", "No additional information")
        raise CurrencyAPIError(code=502, message=f"Fixer API error (code={code}): {info}")

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

    _CACHE[from_sym] = (time.time(), cross_rates)

    return cross_rates
