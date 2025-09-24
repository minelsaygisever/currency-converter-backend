# src/savings/models.py

from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4
from datetime import datetime
import sqlalchemy as sa

class SavingsEntry(SQLModel, table=True):
    __tablename__ = "savings_entries"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    user_id: str = Field(index=True, nullable=False)
    currency_code: str = Field(max_length=10, nullable=False)
    amount: float = Field(nullable=False)
    purchase_date: datetime = Field(
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False)
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False),
        sa_column_kwargs={"onupdate": datetime.utcnow}
    )