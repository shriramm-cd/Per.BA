from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    """
    Application configurations parsed from env variables or .env file.
    """
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/ba_accelerator")
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    
    GROQ_API_KEY: str = Field(default="")
    GROQ_API_KEY_PRIMARY: str = Field(default="")
    GROQ_API_KEY_FALLBACK: str = Field(default="")
    OPENROUTER_API_KEY: str = Field(default="")
    GEMINI_API_KEY: str = Field(default="")
    GEMINI_API_KEY_PRIMARY: str = Field(default="")
    GEMINI_API_KEY_FALLBACK: str = Field(default="")
    
    S3_ENDPOINT_URL: str = Field(default="http://localhost:9000")
    S3_ACCESS_KEY: str = Field(default="minioadmin")
    S3_SECRET_KEY: str = Field(default="minioadmin")
    S3_BUCKET_NAME: str = Field(default="ba-requirements")
    
    API_KEY: str = Field(default="ba-accelerator-secure-api-key-12345")
    
    # Third party connectors configuration
    JIRA_API_URL: Optional[str] = Field(default=None)
    JIRA_USERNAME: Optional[str] = Field(default=None)
    JIRA_API_TOKEN: Optional[str] = Field(default=None)
    
    CONFLUENCE_API_URL: Optional[str] = Field(default=None)
    CONFLUENCE_USERNAME: Optional[str] = Field(default=None)
    CONFLUENCE_API_TOKEN: Optional[str] = Field(default=None)
    
    SHAREPOINT_SITE_URL: Optional[str] = Field(default=None)
    SHAREPOINT_CLIENT_ID: Optional[str] = Field(default=None)
    SHAREPOINT_CLIENT_SECRET: Optional[str] = Field(default=None)
    
    GOOGLE_DRIVE_CREDENTIALS_JSON: Optional[str] = Field(default=None)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# INTEGRATION NOTE
# This module leverages Pydantic settings to guarantee environment state verification.
# Ensure that config.py is imported in api, ingestion, db, and agents rather than loading env directly.
