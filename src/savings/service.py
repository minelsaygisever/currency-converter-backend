import httpx
import os
from sqlmodel import Session
from fastapi import HTTPException
from typing import List
from uuid import UUID
from datetime import datetime, timezone

from . import repo

from src.core.config import settings
from .models import SavingsEntry
from .schemas import SavingsEntryCreate, SavingsEntryRead, SavingsEntryUpdate

REVENUECAT_API_KEY = settings.REVENUECAT_API_KEY
PRO_ENTITLEMENT_IDENTIFIER = "pro" 
MAX_PRO_ENTRIES = 200
MAX_FREE_ENTRIES = 1

class SavingsService:
    def __init__(self, session: Session):
        self.session = session

    async def _is_user_pro(self, user_id: str) -> bool:
        url = f"{settings.REVENUECAT_API_URL}/subscribers/{user_id}"
        headers = {"Authorization": f"Bearer {REVENUECAT_API_KEY}"}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers)
                if response.status_code == 404:
                    return False
                response.raise_for_status()
                data = response.json()
                
                entitlements = data.get("subscriber", {}).get("entitlements", {})
                pro_entitlement = entitlements.get(PRO_ENTITLEMENT_IDENTIFIER)
                
                if not pro_entitlement or "expires_date" not in pro_entitlement:
                    return False

                expires_str = pro_entitlement.get("expires_date")
                if expires_str is None: 
                    return True
                
                expires_date = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
                
                return expires_date > datetime.now(timezone.utc)
                
            except Exception as e:
                print(f"RevenueCat API check failed: {e}")
                return False

    def get_all_by_user(self, user_id: str) -> List[SavingsEntry]:
        return repo.get_all_by_user(self.session, user_id=user_id)

    async def create(self, user_id: str, entry_data: SavingsEntryCreate) -> SavingsEntry:
        is_pro = await self._is_user_pro(user_id)
        current_count = repo.get_count_by_user(self.session, user_id=user_id)

        if is_pro:
            if current_count >= MAX_PRO_ENTRIES:
                raise HTTPException(status_code=403, detail=f"Pro users cannot have more than {MAX_PRO_ENTRIES} entries.")
        else:
            if current_count >= MAX_FREE_ENTRIES:
                raise HTTPException(status_code=403, detail=f"Free users can only have {MAX_FREE_ENTRIES} entry.")

        return repo.create(self.session, user_id=user_id, entry_data=entry_data)

    def update(self, user_id: str, entry_id: UUID, entry_data: SavingsEntryUpdate) -> SavingsEntry:
        db_entry = repo.get_by_id(self.session, entry_id=entry_id)
        
        if not db_entry or db_entry.user_id != user_id:
            raise HTTPException(status_code=404, detail="Entry not found.")

        return repo.update(self.session, db_entry=db_entry, entry_data=entry_data)

    def delete(self, user_id: str, entry_id: UUID):
        db_entry = repo.get_by_id(self.session, entry_id=entry_id)
        
        if not db_entry or db_entry.user_id != user_id:
            raise HTTPException(status_code=404, detail="Entry not found.")

        repo.delete(self.session, db_entry=db_entry)
        return