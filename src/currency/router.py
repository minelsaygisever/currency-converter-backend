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
from src.core.database import get_session
from src.core.security import verify_api_key
from src.core.rate_limiter import manual_rate_limiter


router = APIRouter(
    tags=["API"],
    dependencies=[Depends(verify_api_key), Depends(manual_rate_limiter)] 
)

# --- A helper dependency to get the language ---
def get_language(accept_language: Optional[str] = Header(None)) -> str:
    """
    Parses the primary language from the 'Accept-Language' header.
    If the header is missing or empty, it returns 'en' by default.
    """
    if accept_language:
        # Simplifies a header like 'tr-TR,tr;q=0.9,en-US;q=0.8' to 'tr'.
        return accept_language.split(',')[0].split('-')[0].lower()
    return "en" # Default language

# --- Endpoint for Currencies Resource ---
@router.get("/currencies", response_model=List[CurrencyRead], response_model_exclude_defaults=False)
async def get_all_active_currencies(
    session: Session = Depends(get_session),
    lang: str = Depends(get_language)):
    """
    Returns a list of all active currencies with names localized based on the 'Accept-Language' header.
    Defaults to English if the header is not provided or the language is not supported.
    """

    loc_preferred = aliased(CurrencyLocalization, name="loc_preferred")
    loc_default = aliased(CurrencyLocalization, name="loc_default")

    def get_localized_currencies_from_db():
        statement = (
            select(
                Currency.code,
                Currency.symbol,
                Currency.active,
                Currency.flag_url,
                Currency.decimal_places,
                Currency.quick_rates,
                Currency.quick_rates_order,
                coalesce(loc_preferred.name, loc_default.name, Currency.code).label("name")
            )
            .select_from(Currency)
            .outerjoin(loc_preferred, and_(
                loc_preferred.currency_code == Currency.code,
                loc_preferred.language_code == lang
            ))
            .outerjoin(loc_default, and_(
                loc_default.currency_code == Currency.code,
                loc_default.language_code == 'en'
            ))
            .where(Currency.active == True)
            .order_by(
                Currency.quick_rates_order.asc().nullslast(),
                Currency.code.asc()
            )
        )
        results = session.exec(statement).all()
        return [CurrencyRead.model_validate(row) for row in results]

    currencies = await run_in_threadpool(get_localized_currencies_from_db)
    
    return currencies


# --- Endpoint for Rates Resource ---
@router.get("/rates", response_model=BatchConversionResponse, summary="Get Latest Exchange Rates")
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

    currency_obj = session.get(Currency, base_sym)
    if not currency_obj or not currency_obj.active:
        raise HTTPException(status_code=400, detail=f"Unsupported or inactive base currency: {base_sym}")


    rows = session.exec(
        select(Currency)
        .where(Currency.active == True)
        .order_by(
            Currency.quick_rates_order.asc().nullslast(), 
            Currency.code.asc()
        )
    ).all()
    
    to_symbols = [c.code for c in rows if c.code != base_sym]

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

    rates_list = []
    for to_sym, rate in cross_rates_map.items():
        rates_list.append(RateItem(to=to_sym, rate=rate))

    response = BatchConversionResponse(
        **{"from": base_sym, "rates": rates_list}
    )
    return response