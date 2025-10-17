# tests/currency/test_service.py
import pytest
from src.currency.service import get_conversion_rates
from src.currency.exceptions import CurrencyAPIError

@pytest.mark.asyncio
async def test_get_conversion_rates_successful(mocker):
    # 1. Arrange 
    mock_usd_rates = {
        "EUR": 1.08,  # 1 USD = 1.08 EUR
        "TRY": 35.0,  # 1 USD = 35.0 TRY
        "USD": 1.0
    }

    mocker.patch(
        "src.currency.service._get_all_rates_from_usd",
        return_value=mock_usd_rates
    )

    # 2. Act 
    from_sym = "EUR"
    to_syms = ["TRY"]
    result = await get_conversion_rates(from_sym, to_syms)

    # 3. Assert 
    assert "TRY" in result

    expected_rate = 35.0 / 1.08
    assert result["TRY"] == pytest.approx(expected_rate, rel=1e-6)


@pytest.mark.asyncio
async def test_get_conversion_rates_invalid_from_symbol(mocker):
    # Arrange
    mock_usd_rates = { "EUR": 1.08, "TRY": 35.0 }
    mocker.patch(
        "src.currency.service._get_all_rates_from_usd", 
        return_value=mock_usd_rates
    )
    
    from_sym = "USS" # Invalid currency
    to_syms = ["TRY"]

    # Act & Assert
    with pytest.raises(CurrencyAPIError) as excinfo:
        await get_conversion_rates(from_sym, to_syms)
    
    assert "Base currency 'USS' is not supported" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_conversion_rates_skips_invalid_to_symbol(mocker):
    # Arrange
    mock_usd_rates = {"USD": 1.0, "EUR": 1.08} 
    mocker.patch(
        "src.currency.service._get_all_rates_from_usd", 
        return_value=mock_usd_rates
    )
    
    from_sym = "USD"
    to_syms = ["EUR", "TRR"] # TRR is invalid

    # Act
    result = await get_conversion_rates(from_sym, to_syms)
    
    # Assert
    assert "EUR" in result
    assert "TRR" not in result
    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_all_rates_from_usd_cache_hit(mocker):
    # Arrange
    cached_rates = '{"USD": 1.0, "TRY": 30.0}'
    mock_redis_client = mocker.Mock()
    mock_redis_client.get.return_value = cached_rates
    mocker.patch("src.currency.service.get_redis_client", return_value=mock_redis_client)

    mock_httpx_get = mocker.patch("httpx.AsyncClient.get")

    # Act
    from src.currency.service import _get_all_rates_from_usd
    result = await _get_all_rates_from_usd()

    # Assert
    # 1. Verify that the result is the same as the data from the cache
    assert result == {"USD": 1.0, "TRY": 30.0}
    # 2. Verify that Redis' get method is called
    mock_redis_client.get.assert_called_once_with("latest_usd_rates")
    # 3. Verify that the external API is never called
    mock_httpx_get.assert_not_called()