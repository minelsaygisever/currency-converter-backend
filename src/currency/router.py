from fastapi import APIRouter, HTTPException, Query, Depends, Header
from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session, select
from typing import List, Optional

from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import and_
from sqlalchemy.sql.functions import coalesce

from .models import Currency, CurrencyLocalization
from .schemas import BatchConversionResponse, CurrencyRead, RateItem
from .service import get_conversion_rates
from .exceptions import CurrencyAPIError
from . import repo
from src.core.database import get_session
from src.core.security import verify_api_key
from src.core.rate_limiter import manual_rate_limiter
from src.core.schemas import ErrorDetail


router = APIRouter(
    tags=["Currency"],
    dependencies=[Depends(verify_api_key), Depends(manual_rate_limiter)] 
)

# --- A helper dependency to get the language ---
def get_language(accept_language: Optional[str] = Header(None)) -> str:
    """
    It parses the language from the 'Accept-Language' heading.
    It handles special cases of Chinese such as 'zh-Hans' and 'zh-Hant'.
    eg. tr-TR,tr;q=0.9,en-US;q=0.8
    """
    if not accept_language:
        return "en" # Default

    #'zh-Hans-CN,zh-Hans;q=0.9' -> 'zh-hans-cn'
    first_preference = accept_language.split(',')[0].lower()
    
    # Check Chinese special cases
    if first_preference.startswith("zh-hans"):
        return "zh-Hans"
    if first_preference.startswith("zh-hant"):
        return "zh-Hant" 
    
    # Portuguese special cases
    if first_preference.startswith("pt-br"):
        return "pt-BR"
    if first_preference.startswith("pt-pt"):
        return "pt-PT"
    
    # just get the main language code tr-TR -> tr
    return first_preference.split('-')[0]


# --- Endpoint for Currencies Resource ---
@router.get(
    "/currencies", 
    response_model=List[CurrencyRead], 
    response_model_exclude_defaults=False,
    responses={
        401: {"model": ErrorDetail, "description": "Invalid or missing API Key"},
        429: {"model": ErrorDetail, "description": "Rate limit exceeded"},
    }
)
async def get_all_active_currencies(
    session: Session = Depends(get_session),
    lang: str = Depends(get_language)):
    """
    Returns a list of all active currencies with names localized based on the 'Accept-Language' header.
    Defaults to English if the header is not provided or the language is not supported.
    """
    currencies = await run_in_threadpool(
        repo.get_active_currencies_with_localization, session, lang
    )    
    return currencies


# --- Endpoint for Rates Resource ---
@router.get(
        "/rates", 
        response_model=BatchConversionResponse, 
        summary="Get Latest Exchange Rates",
        responses={
            400: {"model": ErrorDetail, "description": "Unsupported, inactive, or invalid base currency"},
            401: {"model": ErrorDetail, "description": "Invalid or missing API Key"},
            429: {"model": ErrorDetail, "description": "Rate limit exceeded"},
            502: {"model": ErrorDetail, "description": "External currency API is unavailable or returned an error"},
        }
)
async def get_rates(
    from_symbol: str = Query(
        ..., 
        alias="from", 
        description="The base currency code to get rates for, e.g. USD"
    ),
    session: Session = Depends(get_session)
):
    """
    Returns the current exchange rates from a single base currency to all other
    active currencies.
    """
    base_sym = from_symbol.upper()

    currency_obj = await run_in_threadpool(repo.get_currency_by_code, session, base_sym)
    if not currency_obj or not currency_obj.active:
            raise HTTPException(status_code=400, detail=f"Unsupported or inactive base currency: {base_sym}")


    all_codes = await run_in_threadpool(repo.get_all_active_currency_codes, session)
    to_symbols = [code for code in all_codes if code != base_sym]

    if not to_symbols:
        return BatchConversionResponse(
            **{"from": base_sym, "rates": []}
        )

    try:
        cross_rates_map = await get_conversion_rates(base_sym, to_symbols)
        # cross_rates_map: Dict[to_symbol:str, rate:float]
    except CurrencyAPIError as e:
        raise HTTPException(
            status_code=e.code if e.code < 500 else 502,
            detail=e.message
        )

    rates_list = [RateItem(to=to_sym, rate=rate) for to_sym, rate in cross_rates_map.items()]

    response = BatchConversionResponse(
        **{"from": base_sym, "rates": rates_list}
    )
    return response