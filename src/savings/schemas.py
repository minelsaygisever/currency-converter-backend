# src/savings/schemas.py

from sqlmodel import SQLModel
from uuid import UUID
from datetime import date

class SavingsEntryCreate(SQLModel):
    currency_code: str
    amount: float
    purchase_date: date 

class SavingsEntryUpdate(SQLModel):
    currency_code: str | None = None
    amount: float | None = None
    purchase_date: date | None = None

class SavingsEntryRead(SQLModel):
    id: UUID
    currency_code: str
    amount: float
    purchase_date: date