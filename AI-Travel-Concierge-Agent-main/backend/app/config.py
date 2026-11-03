from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    APP_NAME: str = "Automated E-Commerce Concierge Agent"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api"
    
    # Database connection string.
    # Default is SQLite for self-contained execution; can be overridden via DATABASE_URL to PostgreSQL
    # e.g., postgresql+psycopg2://postgres:postgres@localhost:5432/concierge_db
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./concierge.db")
    
    # CORS Origins allowed to talk to backend
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:4173",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ]

    # Optional Travel Provider Configuration
    # Defaults to 'simulated' for deterministic academic demonstration
    PROVIDER_MODE: str = "simulated"
    AMADEUS_CLIENT_ID: str = ""
    AMADEUS_CLIENT_SECRET: str = ""
    AMADEUS_ENV: str = "test"
    AMADEUS_TIMEOUT_SECONDS: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
