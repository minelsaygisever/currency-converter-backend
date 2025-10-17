# tests/rate_history/test_service.py

import pytest
from datetime import datetime, timedelta, timezone
from sqlmodel import Session
from fastapi import HTTPException

from src.rate_history.service import HistoricalDataService
from src.rate_history.models import CurrencyRateSnapshot

# --- Test Data ---
# Fake database records we will use throughout the tests
# Contains hourly data for yesterday and today
FAKE_NOW = datetime(2025, 10, 17, 15, 30, 0, tzinfo=timezone.utc)
YESTERDAY = FAKE_NOW - timedelta(days=1)

HOURLY_SNAPSHOTS = [
    # Yesterday's last hours
    CurrencyRateSnapshot(effective_at=YESTERDAY.replace(hour=22), frequency="hourly", rates={"USD": 1.0, "TRY": 32.1}),
    CurrencyRateSnapshot(effective_at=YESTERDAY.replace(hour=23), frequency="hourly", rates={"USD": 1.0, "TRY": 32.2}), 
    # Today's hours
    CurrencyRateSnapshot(effective_at=FAKE_NOW.replace(hour=13), frequency="hourly", rates={"USD": 1.0, "TRY": 33.1}),
    CurrencyRateSnapshot(effective_at=FAKE_NOW.replace(hour=14), frequency="hourly", rates={"USD": 1.0, "TRY": 33.2}), 
]

DAILY_SNAPSHOT_FOR_YESTERDAY = CurrencyRateSnapshot(
    effective_at=YESTERDAY.replace(hour=0, minute=0, second=0, microsecond=0),
    frequency="daily",
    rates={"USD": 1.0, "TRY": 32.2}
)

# --- Tests ---

def test_get_rate_for_date_happy_path(mocker):
    """
    Tests the "happy path" scenario, where the get_rate_for_date function 
    finds a daily snapshot for the requested date.
    """
    # Arrange
    mock_repo = mocker.patch("src.rate_history.service.repo")
    mock_repo.get_daily_snapshot_for_date.return_value = DAILY_SNAPSHOT_FOR_YESTERDAY
    
    mock_session = mocker.Mock(spec=Session)
    service = HistoricalDataService(mock_session)

    # Act
    result = service.get_rate_for_date(date_str=YESTERDAY.strftime("%Y-%m-%d"))

    # Assert
    assert result.rates["TRY"] == 32.2
    mock_repo.get_daily_snapshot_for_date.assert_called_once()


@pytest.mark.freeze_time(FAKE_NOW)
def test_get_rate_for_date_fallback_to_hourly_for_today(mocker):
    """
    When the requested date is "today" and there is no daily snapshot yet, 
    it tests that the system correctly fallbacks to the latest hourly data of the day.
    """
    # Arrange
    mock_repo = mocker.patch("src.rate_history.service.repo")
    mock_repo.get_daily_snapshot_for_date.return_value = None
    latest_hourly_for_today = HOURLY_SNAPSHOTS[-1]
    mock_repo.get_latest_hourly_for_date.return_value = latest_hourly_for_today

    mock_session = mocker.Mock(spec=Session)
    service = HistoricalDataService(mock_session)
    
    # Act
    result = service.get_rate_for_date(date_str=FAKE_NOW.strftime("%Y-%m-%d"))

    # Assert
    assert result.rates["TRY"] == 33.2
    mock_repo.get_daily_snapshot_for_date.assert_called_once()
    mock_repo.get_latest_hourly_for_date.assert_called_once()


def test_get_rate_for_date_not_found(mocker):
    """
    Tests whether the system correctly throws a 404 HTTPException 
    when no data (neither daily nor hourly) is found for the requested date.
    """
    # Arrange
    mock_repo = mocker.patch("src.rate_history.service.repo")
    mock_repo.get_daily_snapshot_for_date.return_value = None
    mock_repo.get_latest_hourly_for_date.return_value = None

    mock_session = mocker.Mock(spec=Session)
    service = HistoricalDataService(mock_session)
    
    # Act & Assert
    with pytest.raises(HTTPException) as excinfo:
        service.get_rate_for_date(date_str="2020-01-01")
    
    assert excinfo.value.status_code == 404

