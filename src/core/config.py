# src/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./currency.db"
    FIXER_API_KEY: str

    FIXER_API_URL: str = "http://data.fixer.io/api/latest"
    CACHE_TTL_SECONDS: int = 3600 

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

settings = Settings()