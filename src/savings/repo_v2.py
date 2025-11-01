from sqlmodel import Session, select, func
from typing import List
from uuid import UUID

from .models import SavingsEntryV2
from .schemas import SavingsEntryCreate, SavingsEntryUpdate


def get_all_by_user(session: Session, *, user_id: str) -> List[SavingsEntryV2]:
    statement = select(SavingsEntryV2).where(SavingsEntryV2.user_id == user_id)
    return list(session.exec(statement).all())

def get_count_by_user(session: Session, *, user_id: str) -> int:
    statement = select(func.count(SavingsEntryV2.id)).where(SavingsEntryV2.user_id == user_id)
    return session.exec(statement).one()

def get_by_id(session: Session, *, entry_id: UUID) -> SavingsEntryV2 | None:
    return session.get(SavingsEntryV2, entry_id)


def create(session: Session, *, user_id: str, entry_data: SavingsEntryCreate) -> SavingsEntryV2:
    new_entry = SavingsEntryV2.model_validate(entry_data, update={"user_id": user_id})
    session.add(new_entry)
    session.commit()
    session.refresh(new_entry)
    return new_entry

def update(session: Session, *, db_entry: SavingsEntryV2, entry_data: SavingsEntryUpdate) -> SavingsEntryV2:
    update_data = entry_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_entry, key, value)
    
    session.add(db_entry)
    session.commit()
    session.refresh(db_entry)
    return db_entry

def delete(session: Session, *, db_entry: SavingsEntryV2) -> None:
    session.delete(db_entry)
    session.commit()
    return