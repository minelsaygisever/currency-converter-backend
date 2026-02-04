# src/currency/repository.py

from datetime import datetime
from typing import List, Optional, Dict
from sqlmodel import Session, select
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import and_
from sqlalchemy.sql.functions import coalesce
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .models import Currency, CurrencyLocalization, ExchangeRateCache
from .schemas import CurrencyRead

def get_active_currencies_with_localization(session: Session, lang: str) -> List[CurrencyRead]:
    """
    Retrieves all active currencies from the database with names localized 
    based on the provided language, with a fallback to English.
    """
    
    loc_preferred = aliased(CurrencyLocalization, name="loc_preferred")
    loc_default = aliased(CurrencyLocalization, name="loc_default")

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


def get_currency_by_code(session: Session, code: str) -> Optional[Currency]:
    """
    Retrieves a single currency by its code from the database.
    """
    return session.get(Currency, code)


def get_all_active_currency_codes(session: Session) -> List[str]:
    """
    Retrieves a list of all active currency codes from the database.
    """
    statement = (
        select(Currency.code)
        .where(Currency.active == True)
        .order_by(
            Currency.quick_rates_order.asc().nullslast(), 
            Currency.code.asc()
        )
    )
    return session.exec(statement).all()

def get_exchange_rate_cache(session: Session, base_currency: str) -> Optional[ExchangeRateCache]:
    """
    Retrieves the cache record from the database for the specified currency.
    """
    return session.get(ExchangeRateCache, base_currency)

def upsert_exchange_rate_cache(session: Session, base_currency: str, rates: Dict[str, float]):
    """
    It writes to the cache table atomically (updates if it exists, adds to it if it doesn't).
    """
    insert_stmt = pg_insert(ExchangeRateCache).values(
        currency_base=base_currency,
        rates=rates,
        updated_at=datetime.utcnow()
    )
    
    do_update_stmt = insert_stmt.on_conflict_do_update(
        index_elements=['currency_base'],
        set_=dict(rates=insert_stmt.excluded.rates, updated_at=datetime.utcnow())
    )

    session.exec(do_update_stmt)
    session.commit()