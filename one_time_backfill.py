# one_time_backfill.py

import os
import time
import requests
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Set

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import func

from src.rate_history.models import CurrencyRateSnapshot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("backfill_script")

# ENVIRONMENT VARIABLES
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

API_KEY_1 = os.getenv("OXR_API_KEY_1")
API_KEY_2 = os.getenv("OXR_API_KEY_2")
API_KEY_3 = os.getenv("OXR_API_KEY_3")
API_KEY_4 = os.getenv("OXR_API_KEY_4")
API_KEY_5 = os.getenv("OXR_API_KEY_5") 

if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_NAME, API_KEY_1, API_KEY_2, API_KEY_3, API_KEY_4, API_KEY_5]):
    raise ValueError("Required environment variables (DB_*, OXR_API_KEY_*) are not set!")
    
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
API_KEYS = [API_KEY_1, API_KEY_2, API_KEY_3, API_KEY_4, API_KEY_5]

BASE_URL = "https://openexchangerates.org/api/historical/"
BASE_CURRENCY = "USD"
START_DATE = datetime(1999, 1, 1, tzinfo=timezone.utc)
END_DATE = datetime.now(timezone.utc)
MAX_REQUESTS_PER_RUN = 8500
BATCH_SIZE = 100

def fetch_historical_data():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = SessionLocal()

    logger.info("Checking for existing daily records in the database...")
    existing_dates_query = db_session.query(
        func.date(CurrencyRateSnapshot.effective_at)
    ).filter(
        CurrencyRateSnapshot.frequency == 'daily'
    )
    existing_dates: Set[datetime.date] = {d[0] for d in existing_dates_query.all()}
    logger.info(f"Found {len(existing_dates)} existing daily records in the database.")
    
    current_date = START_DATE
    request_count = 0
    
    logger.info(f"Starting historical data backfill from {START_DATE.date()} to {END_DATE.date()}.")

    while current_date <= END_DATE and request_count < MAX_REQUESTS_PER_RUN:
        date_str = current_date.strftime('%Y-%m-%d')
        
        if current_date.date() in existing_dates:
            current_date += timedelta(days=1)
            continue
            
        api_key_to_use = API_KEYS[request_count % len(API_KEYS)]
        
        url = f"{BASE_URL}{date_str}.json?app_id={api_key_to_use}&base={BASE_CURRENCY}"
        
        logger.info(f"Fetching data for missing date: {date_str} (Request: {request_count + 1})...")
        
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            stmt = pg_insert(CurrencyRateSnapshot.__table__).values(
                frequency="daily",
                effective_at=current_date.replace(hour=0, minute=0, second=0, microsecond=0),
                base_currency=data.get("base", BASE_CURRENCY),
                rates=data.get("rates", {})
            )
            on_conflict_stmt = stmt.on_conflict_do_update(
                constraint="uq_crs",
                set_={"rates": stmt.excluded.rates}
            )
            db_session.execute(on_conflict_stmt)
            db_session.commit()
            logger.info(f"Successfully upserted data for {date_str}.")

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch data for {date_str}. Error: {e}")
            db_session.rollback()

        current_date += timedelta(days=1)
        request_count += 1
        time.sleep(0.5)
        
    db_session.close()
    
    if request_count >= MAX_REQUESTS_PER_RUN:
        logger.warning(f"Maximum requests per run ({MAX_REQUESTS_PER_RUN}) reached. Please run the script again later to continue backfill.")
    else:
        logger.info("Historical data backfill completed successfully!")


if __name__ == "__main__":
    fetch_historical_data()