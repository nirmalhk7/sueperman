from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    demo_mode: bool = True
    p1_enabled: bool = False
    p1_monitor_enabled: bool = False
    p1_monitor_poll_seconds: float = Field(default=60, ge=1, le=3600)
    diwali_enabled: bool = False
    diwali_operator_demo: bool = False
    diwali_live_authorized: bool = False
    band_enabled: bool = False
    band_credentials_file: str = ""
    lyzr_enabled: bool = False
    lyzr_api_key: str = ""
    lyzr_review_agent_id: str = ""
    finch_enabled: bool = False
    finch_skill_path: str = ""
    finch_skill_sha256: str = ""
    agent37_enabled: bool = False
    agent37_api_key: str = ""
    agent37_instance_id: str = ""
    diwali_max_messages_per_case: int = Field(default=12, ge=2, le=12)
    diwali_max_followups_per_case: int = Field(default=1, ge=0, le=1)
    diwali_max_lyzr_calls_per_run: int = Field(default=3, ge=0, le=3)
    diwali_remote_task_seconds: float = Field(default=10, gt=0, le=10)
    diwali_max_run_seconds: float = Field(default=90, gt=5, le=90)
    collaboration_live_enabled: bool = False
    collaboration_public_demo: bool = True
    collaboration_timeout_seconds: float = Field(default=90, gt=0, le=90)
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
