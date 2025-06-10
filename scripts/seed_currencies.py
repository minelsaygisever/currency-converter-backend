# scripts/seed_currencies.py

import os
import sys

# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)
# ------------------------------------------------------------

from sqlmodel import Session
from core.database import engine, init_db
from currency.models import Currency

def seed():

    init_db()
    print("Database tables created (if not existing).")

    manual_currencies = [
        {"code": "USD", "name": "United States Dollar", "active": True, "flag_url": None},
        {"code": "EUR", "name": "Euro", "active": True, "flag_url": None},
        {"code": "GBP", "name": "British Pound Sterling", "active": True, "flag_url": None},
        {"code": "JPY", "name": "Japanese Yen", "active": True, "flag_url": None},
        {"code": "TRY", "name": "Turkish Lira", "active": True, "flag_url": None},
        {"code": "AUD", "name": "Australian Dollar", "active": True, "flag_url": None},
        {"code": "CAD", "name": "Canadian Dollar", "active": True, "flag_url": None},
        {"code": "CHF", "name": "Swiss Franc", "active": True, "flag_url": None},
        {"code": "CNY", "name": "Chinese Yuan", "active": True, "flag_url": None},
        {"code": "SEK", "name": "Swedish Krona", "active": True, "flag_url": None},
        {"code": "NZD", "name": "New Zealand Dollar", "active": True, "flag_url": None},
    ]

    with Session(engine) as session:
        count = 0
        for entry in manual_currencies:
            currency = Currency(
                code=entry["code"],
                name=entry["name"],
                active=entry["active"],
                flag_url=entry["flag_url"]
            )
            session.merge(currency)
            count += 1
        session.commit()
        print(f"Seeded or updated {count} currency rows in SQLite database.")

if __name__ == "__main__":
    seed()
