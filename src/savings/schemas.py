# src/savings/schemas.py

from sqlmodel import SQLModel
from uuid import UUID
from datetime import date, datetime

class SavingsEntryCreate(SQLModel):
    currency_code: str
    amount: float
    purchase_date: date 
    is_migration: bool = False
    previous_user_id: str | None = None 

class SavingsEntryUpdate(SQLModel):
    currency_code: str | None = None
    amount: float | None = None
    purchase_date: date | None = None

class SavingsEntryRead(SQLModel):
    id: UUID
    currency_code: str
    amount: float
    purchase_date: date
    created_at: datetime
    updated_at: datetime