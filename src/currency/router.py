from fastapi import APIRouter, HTTPException, Query, Depends
from sqlmodel import Session, select
from typing import List

from .models import Currency
from .schemas import BatchConversionResponse, CurrencyRead, RateItem
from .service import get_conversion_rates_fixer
from .exceptions import CurrencyAPIError
from src.core.database import get_session


router = APIRouter(
    prefix="/currency",
    tags=["currency"]
)

@router.get("/symbols", response_model=List[CurrencyRead])
def get_symbols(session: Session = Depends(get_session)):
    currencies = session.exec(
        select(Currency).where(Currency.active == True).order_by(Currency.code)
    ).all()
    return currencies


@router.get("/convert", response_model=BatchConversionResponse)
def convert(
    from_symbol: str = Query(
        ..., 
        alias="from", 
        description="Source currency code, e.g. USD"
    ),
    session: Session = Depends(get_session)
):
    from_sym = from_symbol.upper()

    # Basit bir sembol kontrolü
    currency_obj = session.get(Currency, from_sym)
    if not currency_obj or not currency_obj.active:
        raise HTTPException(status_code=400, detail=f"Unsupported or inactive from_symbol: {from_sym}")


    rows = session.exec(
        select(Currency).where(Currency.active == True).order_by(Currency.code)
    ).all()
    to_symbols = [c.code for c in rows if c.code != from_sym]

    if not to_symbols:
        return BatchConversionResponse(
            **{"from": from_sym, "rates": []}
        )

    try:
        cross_rates_map = get_conversion_rates_fixer(from_sym, to_symbols)
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
        **{"from": from_sym, "rates": rates_list}
    )
    return response