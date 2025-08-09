from fastapi import FastAPI
import logging
from datetime import datetime

from src.currency.router import router as currency_router
from src.rate_history.router import router as history_router
from src.core.database import init_db
from src.core.redis_client import get_redis_client

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Currency Converter API...")

    init_db()
    logger.info("Database initialized successfully")

    # Check Redis connection
    redis_client = get_redis_client()
    if redis_client:
        try:
            redis_client.ping()
            logger.info("Redis connection verified.")
        except Exception as e:
            logger.error(f"Could not verify Redis connection on startup: {e}")
    else:
        logger.warning("Redis client is not available.")

    yield

    logger.info("Shutting down Currency Converter API...")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Currency Converter API",
    version="1.0.0",
    description="A simple service for converting currencies",
    lifespan=lifespan
)

app.include_router(currency_router, prefix="/currency-converter/v1")
app.include_router(history_router, prefix="/currency-converter/v1")

@app.get("/", tags=["health"])
def read_root():
    """
    Root endpoint: returns a simple JSON message to verify the API is running.
    """
    return {"message": "Currency Converter API is up and running!"}

# Request logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    start_time = datetime.utcnow()
    response = await call_next(request)
    duration = (datetime.utcnow() - start_time).total_seconds()
    
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {duration:.3f}s"
    )
    
    return response