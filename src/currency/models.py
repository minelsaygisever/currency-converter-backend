# src/modules/currency/models.py

from sqlmodel import SQLModel, Field

class Currency(SQLModel, table=True):
    code: str = Field(default=None, primary_key=True, index=True, max_length=3)
    name: str = Field(default=None, index=True, max_length=100)
    symbol: str = Field(default=None, max_length=10)
    active: bool = Field(default=True, index=True)
    flag_url: str | None = Field(default=None, max_length=255)
    decimal_places: int = Field(default=2)
    quick_rates: bool = Field(default=False, index=True)
    quick_rates_order: int | None = Field(default=None, index=True)
