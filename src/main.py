from fastapi import FastAPI
from src.currency.router import router as currency_router
from src.core.database import init_db

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Currency Converter API",
    version="0.1.0",
    description="A simple service for converting currencies",
    lifespan=lifespan
)

app.include_router(currency_router)

@app.get("/")
def read_root():
    """
    Root endpoint: returns a simple JSON message to verify the API is running.
    """
    return {"message": "Currency Converter API is up and running!"}