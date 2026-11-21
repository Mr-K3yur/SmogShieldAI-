from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "SmogShield AI Backend"
    APP_ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Explicit Demo Mode Toggle (MUST be explicitly True to serve simulated data)
    DEMO_MODE: bool = False
    
    # Google Gemini API Configuration
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"
    
    # Operator Smoke-Test Authentication Token (strictly separate from GEMINI_API_KEY)
    ASSISTANT_SMOKE_TEST_TOKEN: str = ""

    # Optional Trusted Proxy IPs (for secure X-Forwarded-For resolution)
    TRUSTED_PROXY_IPS: List[str] = []
    
    # Official data.gov.in CPCB Real-time AQI Dataset Configuration
    # Resource: "Real-time Air Quality Index from various locations"
    DATA_GOV_IN_API_KEY: str = ""
    DATA_GOV_IN_RESOURCE_ID: str = "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
    DATA_GOV_IN_BASE_URL: str = "https://api.data.gov.in/resource"
    
    # OpenAQ API v3 Configuration
    OPENAQ_API_KEY: str = ""
    OPENAQ_BASE_URL: str = "https://api.openaq.org/v3"
    
    # HTTP Client Configuration
    HTTP_TIMEOUT_SECONDS: float = 10.0
    HTTP_MAX_RETRIES: int = 2
    
    # AQI Data Freshness Thresholds (in Hours)
    # Default application policy: Fresh <= 4h, Stale <= 24h, Expired > 24h
    FRESH_THRESHOLD_HOURS: float = 4.0
    STALE_THRESHOLD_HOURS: float = 24.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
