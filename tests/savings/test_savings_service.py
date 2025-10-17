# tests/savings/test_savings_service.py

import pytest
from uuid import uuid4
from sqlmodel import Session
from fastapi import HTTPException

from src.savings.service import SavingsService, MAX_FREE_ENTRIES
from src.savings.schemas import SavingsEntryCreate
from src.savings.models import SavingsEntry

# --- Test Data ---
USER_ID = "user_123"

# A database record belonging to User 
USER_ENTRY = SavingsEntry(
    id=uuid4(),
    user_id=USER_ID,
    amount=100,
    currency_code="USD",
    purchase_date="2025-10-17T10:00:00Z"
)

# --- Tests ---

@pytest.mark.asyncio
async def test_create_free_user_fails_at_limit(mocker):
    """
    Tests whether a free user is unable to create a new record and receives 
    a 403 error when the allowed limit (MAX_FREE_ENTRIES) is exceeded.
    """
    # Arrange
    # 1. Simulate user is not "Pro"
    mocker.patch.object(SavingsService, "_is_user_pro", return_value=False)
    
    # 2. Simulate that the database already has the limit of records
    mock_repo = mocker.patch("src.savings.service.repo")
    mock_repo.get_count_by_user.return_value = MAX_FREE_ENTRIES

    service = SavingsService(session=mocker.Mock(spec=Session))
    new_entry_data = SavingsEntryCreate(amount=50, currency_code="EUR", purchase_date="2025-10-18")

    # Act & Assert
    # Verify that a 403 HTTPException will be thrown
    with pytest.raises(HTTPException) as excinfo:
        await service.create(user_id=USER_ID, entry_data=new_entry_data)
    
    assert excinfo.value.status_code == 403
    
    # Verify that the write operation to the database is NEVER called
    mock_repo.create.assert_not_called()

@pytest.mark.asyncio
async def test_create_migration_bypasses_limits(mocker):
    """
    Tests whether a valid migration request successfully 
    creates a record, bypassing normal user limits.
    """
    # Arrange
    # 1. Simulate migration verification success
    mocker.patch.object(SavingsService, "_is_alias_valid", return_value=True)
    
    # 2. Follow the repo's create function
    mock_repo = mocker.patch("src.savings.service.repo")
    
    # 3. Create spies to verify that limit control functions will not be called
    spy_is_pro = mocker.spy(SavingsService, "_is_user_pro")
    
    service = SavingsService(session=mocker.Mock(spec=Session))
    migration_data = SavingsEntryCreate(
        amount=50, currency_code="EUR", purchase_date="2025-10-18",
        is_migration=True, previous_user_id="old_user_abc"
    )

    # Act
    await service.create(user_id=USER_ID, entry_data=migration_data)

    # Assert
    # 1. Verify that limit control functions are NEVER called
    spy_is_pro.assert_not_called()
    mock_repo.get_count_by_user.assert_not_called()
    
    # 2. Verify that the write operation to the database was called successfully
    mock_repo.create.assert_called_once()


def test_update_succeeds_for_own_entry(mocker):
    """
    Tests whether a user can successfully update a record belonging to them.
    """
    # Arrange
    # 1. Simulate that the repo will return a record for the correct user 
    mock_repo = mocker.patch("src.savings.service.repo")
    mock_repo.get_by_id.return_value = USER_ENTRY

    service = SavingsService(session=mocker.Mock(spec=Session))
    update_data = SavingsEntryCreate(amount=150, currency_code="USD", purchase_date="2025-10-17")

    # Act
    service.update(user_id=USER_ID, entry_id=USER_ENTRY.id, entry_data=update_data)

    # Assert
    # Verify that the database update function was called with the correct parameters
    mock_repo.update.assert_called_once_with(
        mocker.ANY,
        db_entry=USER_ENTRY,
        entry_data=update_data
    )