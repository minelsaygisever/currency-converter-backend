# tests/currency/test_service.py
import pytest
from src.currency.service import get_conversion_rates_fixer
from src.currency.exceptions import CurrencyAPIError

@pytest.mark.asyncio
async def test_get_conversion_rates_successful(mocker):
    # 1. Arrange 
    mock_response = mocker.Mock()
    mock_response.json.return_value = {
        "success": True,
        "rates": {
            "USD": 1.08,  # 1 EUR = 1.08 USD
            "TRY": 35.0,  # 1 EUR = 35.0 TRY
            "EUR": 1.0
        }
    }

    mock_async_client = mocker.patch("httpx.AsyncClient.get", return_value=mock_response)

    # 2. Act 
    from_sym = "USD"
    to_syms = ["TRY"]
    result = await get_conversion_rates_fixer(from_sym, to_syms)

    # 3. Assert 
    assert "TRY" in result

    expected_rate = 35.0 / 1.08
    assert result["TRY"] == pytest.approx(expected_rate, rel=1e-6)

    mock_async_client.assert_called_once()