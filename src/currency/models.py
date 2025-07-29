# src/modules/currency/models.py

from typing import List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

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

