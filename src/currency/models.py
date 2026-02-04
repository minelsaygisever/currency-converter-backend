# src/modules/currency/models.py

from typing import List, TYPE_CHECKING, Dict, Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB

if TYPE_CHECKING:
    from .models import Currency

class CurrencyLocalization(SQLModel, table=True):
    __tablename__ = "currency_localizations"

    id: int | None = Field(default=None, primary_key=True)
    language_code: str = Field(index=True, max_length=5)
    name: str = Field(max_length=255)

    currency_code: str = Field(default=None, foreign_key="currency.code", index=True)
    
    currency: "Currency" = Relationship(back_populates="localizations")



class Currency(SQLModel, table=True):
    code: str = Field(default=None, primary_key=True, index=True, max_length=3)
    symbol: str = Field(default=None, max_length=10)
    active: bool = Field(default=True, index=True)
    flag_url: str | None = Field(default=None, max_length=255)
    decimal_places: int = Field(default=2)
    quick_rates: bool = Field(default=False, index=True)
    quick_rates_order: int | None = Field(default=None, index=True)

    localizations: List["CurrencyLocalization"] = Relationship(back_populates="currency")


class ExchangeRateCache(SQLModel, table=True):
    __tablename__ = "exchange_rate_cache"

    currency_base: str = Field(primary_key=True, max_length=10)
    rates: Dict[str, float] = Field(sa_column=Column(JSONB, nullable=False))
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False
        )
    )