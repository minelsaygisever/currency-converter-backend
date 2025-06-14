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
        {"code": "USD", "name": "United States Dollar", "symbol": "$", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "EUR", "name": "Euro", "symbol": "€", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "GBP", "name": "British Pound Sterling", "symbol": "£", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "JPY", "name": "Japanese Yen", "symbol": "¥", "flag_url": None, "active": True, "decimal_places": 0},
        {"code": "TRY", "name": "Turkish Lira", "symbol": "₺", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "AUD", "name": "Australian Dollar", "symbol": "A$", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "CAD", "name": "Canadian Dollar", "symbol": "C$", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "CHF", "name": "Swiss Franc", "symbol": "CHF", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "CNY", "name": "Chinese Yuan", "symbol": "¥", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "SEK", "name": "Swedish Krona", "symbol": "kr", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "NZD", "name": "New Zealand Dollar", "symbol": "NZ$", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "NOK", "name": "Norwegian Krone", "symbol": "kr", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "MXN", "name": "Mexican Peso", "symbol": "$", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "SGD", "name": "Singapore Dollar", "symbol": "S$", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "HKD", "name": "Hong Kong Dollar", "symbol": "HK$", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "INR", "name": "Indian Rupee", "symbol": "₹", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "KRW", "name": "South Korean Won", "symbol": "₩", "flag_url": None, "active": True, "decimal_places": 0},
        {"code": "ZAR", "name": "South African Rand", "symbol": "R", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "BRL", "name": "Brazilian Real", "symbol": "R$", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "RUB", "name": "Russian Ruble", "symbol": "₽", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "PLN", "name": "Polish Złoty", "symbol": "zł", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "THB", "name": "Thai Baht", "symbol": "฿", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "MYR", "name": "Malaysian Ringgit", "symbol": "RM", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "PHP", "name": "Philippine Peso", "symbol": "₱", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "IDR", "name": "Indonesian Rupiah", "symbol": "Rp", "flag_url": None, "active": True, "decimal_places": 0},
        {"code": "CZK", "name": "Czech Koruna", "symbol": "Kč", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "HUF", "name": "Hungarian Forint", "symbol": "Ft", "flag_url": None, "active": True, "decimal_places": 0},
        {"code": "ILS", "name": "Israeli New Shekel", "symbol": "₪", "flag_url": None, "active": True, "decimal_places": 2},
        {"code": "CLP", "name": "Chilean Peso", "symbol": "$", "flag_url": None, "active": True, "decimal_places": 0},
        {"code": "PKR", "name": "Pakistani Rupee", "symbol": "₨", "flag_url": None, "active": True, "decimal_places": 2},
    ]

    with Session(engine) as session:
        count = 0
        for entry in manual_currencies:
            currency = Currency(
                code=entry["code"],
                name=entry["name"],
                symbol=entry["symbol"],
                active=entry["active"],
                flag_url=entry.get("flag_url"),
                decimal_places=entry.get("decimal_places", 2)
            )
            session.merge(currency)
            count += 1
        session.commit()
        print(f"Seeded or updated {count} currency rows in SQLite database.")

if __name__ == "__main__":
    seed()