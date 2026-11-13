from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    demo_mode: bool = True
    database_url: str = "sqlite:///./sueperman.db"
    frontend_origin: str = "http://localhost:3000"
    cpsc_live_enabled: bool = False
    gemini_enabled: bool = False
    brightdata_enabled: bool = False
    system_one_enabled: bool = False
    settlement_live_enabled: bool = False
    gemini_api_key: str = ""
    brightdata_api_token: str = ""
    system_one_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-lite"
    system_one_model: str = "decisions"
    openai_enabled: bool = False
    openai_api_key: str = ""
    openai_receipt_enabled: bool = False
    openai_receipt_model: str = "gpt-6-luna"
    openai_receipt_daily_limit: int = Field(default=10, ge=0, le=100)
    openai_decision_model: str = "gpt-6-luna"
    openai_max_calls_per_run: int = Field(default=3, ge=0, le=10)
    sentry_dsn: str = ""
    sentry_environment: str = "development"
