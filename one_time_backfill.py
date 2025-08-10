# one_time_backfill.py

import os
import time
import requests
import logging
from datetime import datetime, timedelta
from typing import List

from sqlalchemy import create_engine, Column, DateTime, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("backfill_script")

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

API_KEY_1 = os.getenv("OXR_API_KEY_1")
API_KEY_2 = os.getenv("OXR_API_KEY_2")

if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_NAME, API_KEY_1, API_KEY_2]):
    raise ValueError("Gerekli ortam değişkenleri (DB_*, OXR_API_KEY_*) ayarlanmamış!")
    
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
API_KEYS = [API_KEY_1, API_KEY_2]

# --- Sabitler ---
BASE_URL = "https://openexchangerates.org/api/historical/"
BASE_CURRENCY = "USD"
START_DATE = datetime(2020, 8, 10)
END_DATE = datetime.now()
BATCH_SIZE = 100 

Base = declarative_base()

class CurrencyRateSnapshot(Base):
    __tablename__ = 'currency_rate_snapshots'
    id = Column(Integer, primary_key=True, autoincrement=True)
    frequency = Column(String, nullable=False)
    effective_at = Column(DateTime(timezone=True), nullable=False, index=True)
    base_currency = Column(String(3), nullable=False)
    rates = Column(JSONB, nullable=False)

def fetch_historical_data():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = SessionLocal()
    
    current_date = START_DATE
    day_count = 0
    snapshot_batch: List[CurrencyRateSnapshot] = []

    logger.info(f"Starting historical data backfill from {START_DATE.date()} to {END_DATE.date()}.")

    while current_date <= END_DATE:
        date_str = current_date.strftime('%Y-%m-%d')
        api_key_to_use = API_KEYS[day_count % len(API_KEYS)]
        
        url = f"{BASE_URL}{date_str}.json?app_id={api_key_to_use}&base={BASE_CURRENCY}"
        
        logger.info(f"Fetching data for {date_str}...")
        
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()

            new_snapshot = CurrencyRateSnapshot(
                frequency="daily",
                effective_at=current_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timedelta(0)),
                base_currency=data.get("base", BASE_CURRENCY),
                rates=data.get("rates", {})
            )
            snapshot_batch.append(new_snapshot)

            if len(snapshot_batch) >= BATCH_SIZE:
                try:
                    db_session.add_all(snapshot_batch)
                    db_session.commit()
                    logger.info(f"COMMITTED a batch of {len(snapshot_batch)} snapshots.")
                except IntegrityError:
                    logger.warning(f"Batch commit failed due to potential duplicates. Rolling back and inserting one by one.")
                    db_session.rollback()
                    for snapshot in snapshot_batch:
                        try:
                            db_session.add(snapshot)
                            db_session.commit()
                        except IntegrityError:
                            logger.warning(f"Duplicate entry for {snapshot.effective_at}. Skipping.")
                            db_session.rollback()
                finally:
                    snapshot_batch = [] # Batch'i temizle

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch data for {date_str}. Error: {e}")

        current_date += timedelta(days=1)
        day_count += 1
        time.sleep(0.5)

    if snapshot_batch:
        db_session.add_all(snapshot_batch)
        db_session.commit()
        logger.info(f"COMMITTED the final batch of {len(snapshot_batch)} snapshots.")

    db_session.close()
    logger.info("Historical data backfill completed successfully!")

if __name__ == "__main__":
    fetch_historical_data()