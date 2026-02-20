import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(
        extra="ignore",
        env_file=os.path.join(os.path.dirname(__file__), "..", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    database_url: str
    deepgram_api_key: str
    gemini_api_key: str
    
    # Redis configuration for Celery
    redis_host: str = "localhost"
    redis_port: int = 6379
    
    # S3 Configuration
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket: str = ""
    aws_region: str = "us-east-1"


settings = Settings()  # loads from .env by default
