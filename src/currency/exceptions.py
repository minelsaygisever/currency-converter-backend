# src/currency/exceptions.py

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

class CurrencyAPIError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)

async def currency_api_exception_handler(request: Request, exc: CurrencyAPIError):
    return JSONResponse(
        status_code=502,
        content={"error_code": exc.code, "error_message": exc.message}
    )