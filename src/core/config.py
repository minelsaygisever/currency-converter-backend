# src/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict

# Version bilgisi - Tek kaynak
VERSION = "1.0.0"

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Currency Converter API"
    APP_VERSION: str = VERSION
    APP_DESCRIPTION: str = "A modern currency conversion service with real-time rates"
    
    # Database
    DATABASE_URL: str = "sqlite:///./currency.db"
    
    # Fixer API
    FIXER_API_KEY: str
    FIXER_API_URL: str = "http://data.fixer.io/api/latest"
    
    # Cache
    CACHE_TTL_SECONDS: int = 3600  # 1 hour
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

settings = Settings()