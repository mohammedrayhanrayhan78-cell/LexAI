from __future__ import annotations

import sys
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator
import json

_WEAK_SECRETS = {
    "secret", "changeme", "your_secret", "your-secret",
    "ci_test_secret_key_123456789", "ci_test_refresh_key_123456789",
}


class Settings(BaseSettings):
    DATABASE_URL: str
    ENVIRONMENT: str = "production"
    ALLOWED_ORIGINS: List[str] = ["http://localhost", "http://localhost:80"]

    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str

    @model_validator(mode="after")
    def _guard_prod_secrets(self) -> "Settings":
        if self.ENVIRONMENT.lower() == "production":
            for name, val in [
                ("JWT_SECRET_KEY", self.JWT_SECRET_KEY),
                ("JWT_REFRESH_SECRET_KEY", self.JWT_REFRESH_SECRET_KEY),
            ]:
                if not val or val.lower().strip() in _WEAK_SECRETS or len(val) < 32:
                    print(
                        f"[LexAI] FATAL: {name} is weak or missing in production. "
                        "Set a strong random value (≥32 chars) in .env.",
                        file=sys.stderr,
                    )
                    sys.exit(1)
        return self
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    # LLM Provider Configuration
    DEFAULT_LLM_PROVIDER: str = "groq"
    LLM_TIMEOUT_SECONDS: int = 30
    
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_WHISPER_MODEL: str = "whisper-large-v3"

    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"

    # Embedding & RAG Configuration
    EMBEDDING_PROVIDER: str = "gemini"
    EMBEDDING_MODEL: str = "gemini-embedding-2"
    EMBEDDING_DIMENSIONS: int = 768
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K_RETRIEVAL: int = 4

    # Voice Configuration
    ENABLE_TTS: bool = False
    WHISPER_PROVIDER: str = "groq"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str):
            return json.loads(v)
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()