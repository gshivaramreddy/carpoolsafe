from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/carpool_db"
    SECRET_KEY: str = "change-this-secret-key-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    GOOGLE_MAPS_API_KEY: str = "AIzaSyBawP8iV6Dbc7SlPl2JTDgVUoLXhxNTQ0M"
    REDIS_URL: Optional[str] = None
    BACKEND_URL: str = "http://localhost:8000"
    
    # Safety thresholds
    MAX_ROUTE_DEVIATION_KM: float = 0.5
    STALL_DETECTION_MINUTES: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
