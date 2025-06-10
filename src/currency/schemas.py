from typing import List
from pydantic import BaseModel, Field, ConfigDict

class RateItem(BaseModel):
    to: str = Field(..., description="Target currency code (to), e.g.: EUR")
    rate: float = Field(..., description="Cross rate from `from` → `to`")

    model_config = ConfigDict(from_attributes=True)

class BatchConversionResponse(BaseModel):
    from_symbol: str = Field(..., alias="from", description="Source currency code, e.g.: USD")
    rates: List[RateItem] = Field(..., description="List of {to, rate} pairs for each target currency")

    model_config = ConfigDict(
        validate_by_name=True,
        populate_by_name=True,
        from_attributes=True
    )

class CurrencyRead(BaseModel):
    code: str
    name: str
    active: bool
    flag_url: str | None

    model_config = ConfigDict(from_attributes=True)