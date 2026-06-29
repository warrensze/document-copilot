from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    database_url: str

    ollama_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "llama3.2:3b"
    embedding_model: str = "nomic-embed-text"
    embedding_dimensions: int = 768

    allowed_origins: str = "http://localhost:5173"


settings = Settings()
