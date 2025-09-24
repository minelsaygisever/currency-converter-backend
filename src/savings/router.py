# src/savings/router.py

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlmodel import Session, select
from typing import List
from uuid import UUID

from src.core.database import get_session
from src.core.security import verify_api_key
from .models import SavingsEntry
from .schemas import SavingsEntryCreate, SavingsEntryRead, SavingsEntryUpdate

router = APIRouter(
    prefix="/savings", 
    tags=["Savings"],
    dependencies=[Depends(verify_api_key)]
)

def get_user_id(x_app_user_id: str = Header(..., description="RevenueCat App User ID")) -> str:
    if not x_app_user_id:
        raise HTTPException(status_code=400, detail="X-App-User-ID header is required.")
    return x_app_user_id

@router.get("/", response_model=List[SavingsEntryRead])
def get_user_savings(
    user_id: str = Depends(get_user_id),
    session: Session = Depends(get_session)
):
    statement = select(SavingsEntry).where(SavingsEntry.user_id == user_id)
    entries = session.exec(statement).all()
    return entries

@router.post("/", response_model=SavingsEntryRead, status_code=201)
def create_saving_entry(
    entry_data: SavingsEntryCreate,
    user_id: str = Depends(get_user_id),
    session: Session = Depends(get_session)
):
    new_entry = SavingsEntry.model_validate(entry_data, update={"user_id": user_id})
    session.add(new_entry)
    session.commit()
    session.refresh(new_entry)
    return new_entry

@router.put("/{entry_id}", response_model=SavingsEntryRead)
def update_saving_entry(
    entry_id: UUID,
    entry_data: SavingsEntryUpdate,
    user_id: str = Depends(get_user_id),
    session: Session = Depends(get_session)
):
    db_entry = session.get(SavingsEntry, entry_id)
    if not db_entry or db_entry.user_id != user_id:
        raise HTTPException(status_code=404, detail="Entry not found.")

    update_data = entry_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_entry, key, value)

    session.add(db_entry)
    session.commit()
    session.refresh(db_entry)
    return db_entry

@router.delete("/{entry_id}", status_code=204)
def delete_saving_entry(
    entry_id: UUID,
    user_id: str = Depends(get_user_id),
    session: Session = Depends(get_session)
):
    db_entry = session.get(SavingsEntry, entry_id)
    if not db_entry or db_entry.user_id != user_id:
        raise HTTPException(status_code=404, detail="Entry not found.")

    session.delete(db_entry)
    session.commit()
    return