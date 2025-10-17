# src/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field, PostgresDsn
from urllib.parse import quote_plus

VERSION = "1.0.0"

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Currency & Savings API"
    APP_VERSION: str = VERSION
    APP_DESCRIPTION: str = "An API for real-time currency conversion and personal savings tracking."
    
    # Database
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        encoded_password = quote_plus(self.DB_PASSWORD)        
        
        return f"postgresql+psycopg2://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


    # Redis
    REDIS_HOST: str
    REDIS_PORT: int

    # Security
    API_SECRET_KEY: str
    
    # Open Exchange Rates API
    OPEN_EXCHANGE_RATES_API_KEY: str
    OPEN_EXCHANGE_RATES_API_URL: str = "https://openexchangerates.org/api/latest.json"

    # RevenueCat API
    REVENUECAT_API_KEY: str
    REVENUECAT_API_URL: str = "https://api.revenuecat.com/v1"
    
    # Cache
    CACHE_TTL_SECONDS: int
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

settings = Settings()