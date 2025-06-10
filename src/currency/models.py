# src/modules/currency/models.py

from sqlmodel import SQLModel, Field

class Currency(SQLModel, table=True):
    code: str = Field(default=None, primary_key=True, index=True, max_length=3)
    name: str = Field(default=None, index=True, max_length=100)
    active: bool = Field(default=True, index=True)
    flag_url: str | None = Field(default=None, max_length=255)
