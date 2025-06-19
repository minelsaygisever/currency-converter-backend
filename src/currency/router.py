from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session, select
from typing import List

from .models import Currency
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

# --- Endpoint for Currencies Resource ---
@router.get("/currencies", response_model=List[CurrencyRead], response_model_exclude_defaults=False)
async def get_all_active_currencies(session: Session = Depends(get_session)):
    """
    Returns a list of all currencies that are marked as active in the system.
    """
    def get_all_currencies_from_db():
        return session.exec(
            select(Currency).where(Currency.active == True).order_by(Currency.code)
        ).all()

    currencies = await run_in_threadpool(get_all_currencies_from_db)
    
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
        select(Currency).where(Currency.active == True).order_by(Currency.code)
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