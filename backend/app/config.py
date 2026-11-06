from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = (
        "postgresql+psycopg://referral:referral_local@127.0.0.1:5432/referrals"
    )

    gemini_enabled: bool = False
    referral_policy_path: Path = (
        Path(__file__).parent / "extraction" / "policies" / "default.json"
    )

    app_name: str = "Hospital Referral API"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    document_storage_dir: Path = Path(__file__).resolve().parents[1] / "var" / "documents"
    document_max_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    document_max_pages: int = Field(default=100, gt=0)
    document_max_text_chars: int = Field(default=2_000_000, gt=0)


settings = Settings()
