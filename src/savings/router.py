# src/savings/router.py

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlmodel import Session, select
from typing import List
from uuid import UUID

from src.core.database import get_session
from src.core.security import verify_api_key
from src.core.schemas import ErrorDetail
from .schemas import SavingsEntryCreate, SavingsEntryRead, SavingsEntryUpdate
from .service import SavingsService 

router = APIRouter(
    prefix="/savings", 
    tags=["Savings"],
    dependencies=[Depends(verify_api_key)]
)

def get_savings_service(session: Session = Depends(get_session)) -> SavingsService:
    return SavingsService(session=session)


def get_user_id(x_app_user_id: str = Header(..., description="RevenueCat App User ID")) -> str:
    if not x_app_user_id:
        raise HTTPException(status_code=400, detail="X-App-User-ID header must not be empty.")
    return x_app_user_id


@router.get(
        "", 
        response_model=List[SavingsEntryRead],
        responses={
            400: {"model": ErrorDetail, "description": "X-App-User-ID header is missing or empty"},
            401: {"model": ErrorDetail, "description": "Invalid or missing API Key"},
        }
)
def get_user_savings(
    user_id: str = Depends(get_user_id),
    service: SavingsService = Depends(get_savings_service)
):
    return service.get_all_by_user(user_id=user_id)


@router.post(
        "", 
        response_model=SavingsEntryRead, 
        status_code=201,
        responses={
            400: {"model": ErrorDetail, "description": "X-App-User-ID header is missing or empty"},
            401: {"model": ErrorDetail, "description": "Invalid or missing API Key"},
            403: {"model": ErrorDetail, "description": "User limit exceeded or invalid migration request"},
            422: {"model": ErrorDetail, "description": "Validation Error (e.g., invalid request body)"},
        }
)
async def create_saving_entry(
    entry_data: SavingsEntryCreate,
    user_id: str = Depends(get_user_id),
    service: SavingsService = Depends(get_savings_service)
):
    return await service.create(user_id=user_id, entry_data=entry_data)


@router.put(
        "/{entry_id}", 
        response_model=SavingsEntryRead,
        responses={
            400: {"model": ErrorDetail, "description": "X-App-User-ID header is missing or empty"},
            401: {"model": ErrorDetail, "description": "Invalid or missing API Key"},
            404: {"model": ErrorDetail, "description": "Entry not found or user does not own it"},
            422: {"model": ErrorDetail, "description": "Validation Error (e.g., invalid UUID or request body)"},
        }
)
def update_saving_entry(
    entry_id: UUID,
    entry_data: SavingsEntryUpdate,
    user_id: str = Depends(get_user_id),
    service: SavingsService = Depends(get_savings_service)
):
    return service.update(user_id=user_id, entry_id=entry_id, entry_data=entry_data)


@router.delete(
        "/{entry_id}", 
        status_code=204,
        responses={
            400: {"model": ErrorDetail, "description": "X-App-User-ID header is missing or empty"},
            401: {"model": ErrorDetail, "description": "Invalid or missing API Key"},
            404: {"model": ErrorDetail, "description": "Entry not found or user does not own it"},
            422: {"model": ErrorDetail, "description": "Validation Error (e.g., invalid UUID)"},
        }
)
def delete_saving_entry(
    entry_id: UUID,
    user_id: str = Depends(get_user_id),
    service: SavingsService = Depends(get_savings_service)
):
    return service.delete(user_id=user_id, entry_id=entry_id)