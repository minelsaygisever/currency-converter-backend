from sqlmodel import Session, select, func
from typing import List
from uuid import UUID

from .models import SavingsEntry
from .schemas import SavingsEntryCreate, SavingsEntryUpdate


def get_all_by_user(session: Session, *, user_id: str) -> List[SavingsEntry]:
    statement = select(SavingsEntry).where(SavingsEntry.user_id == user_id)
    return list(session.exec(statement).all())

def get_count_by_user(session: Session, *, user_id: str) -> int:
    statement = select(func.count(SavingsEntry.id)).where(SavingsEntry.user_id == user_id)
    return session.exec(statement).one()

def get_by_id(session: Session, *, entry_id: UUID) -> SavingsEntry | None:
    return session.get(SavingsEntry, entry_id)


def create(session: Session, *, user_id: str, entry_data: SavingsEntryCreate) -> SavingsEntry:
    new_entry = SavingsEntry.model_validate(entry_data, update={"user_id": user_id})
    session.add(new_entry)
    session.commit()
    session.refresh(new_entry)
    return new_entry

def update(session: Session, *, db_entry: SavingsEntry, entry_data: SavingsEntryUpdate) -> SavingsEntry:
    update_data = entry_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_entry, key, value)
    
    session.add(db_entry)
    session.commit()
    session.refresh(db_entry)
    return db_entry

def delete(session: Session, *, db_entry: SavingsEntry) -> None:
    session.delete(db_entry)
    session.commit()
    return