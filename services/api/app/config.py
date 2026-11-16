from pathlib import Path

from pydantic import Field, SecretStr
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
    collaboration_live_enabled: bool = False
    band_enabled: bool = False
    agent37_enabled: bool = False
    adal_enabled: bool = False
    finch_enabled: bool = False
    lyzr_enabled: bool = False
    band_room_id: str = ""
    band_identities: dict[str, str] = Field(default_factory=dict)
    band_api_keys: dict[str, SecretStr] = Field(default_factory=dict)
    agent37_api_key: SecretStr = SecretStr("")
    agent37_instance_id: str = ""
    agent37_worker_revision: str = ""
    agent37_isolation_verified: bool = False
    adal_runtime_path: str = ""
    adal_runtime_sha256: str = ""
    adal_isolation_verified: bool = False
    adal_sandbox_image: str = ""
    adal_bundle_dir: str = ""
    adal_bundle_sha256: str = ""
    adal_auth_directory: str = ""
    adal_allowed_hosts: str = ""
    finch_manifest_path: str = ""
    finch_package_path: str = ""
    lyzr_api_key: SecretStr = SecretStr("")
    lyzr_chat_url: str = ""
    lyzr_agent_id: str = ""
    lyzr_user_id: str = ""
    lyzr_api_profile: str = ""
    collaboration_run_seconds: int = Field(default=90, ge=1, le=90)
    collaboration_daily_limit: int = Field(default=30, ge=0, le=100)
    sentry_dsn: str = ""
    sentry_environment: str = "development"
