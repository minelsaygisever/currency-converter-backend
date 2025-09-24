# src/savings/models.py

from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import func
from typing import Optional

class SavingsEntry(SQLModel, table=True):
    __tablename__ = "savings_entries"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    user_id: str = Field(index=True, nullable=False)
    currency_code: str = Field(max_length=10, nullable=False)
    amount: float = Field(nullable=False)
    purchase_date: datetime = Field(
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False)
    )
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=sa.Column(
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=func.now()
        )
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=sa.Column(
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now()
        )
    )