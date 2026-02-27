from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    environment: str = "development"
    debug: bool = False

    class Config:
        env_file = str(Path(__file__).parent.parent.parent.parent.parent / ".env")

settings = Settings()