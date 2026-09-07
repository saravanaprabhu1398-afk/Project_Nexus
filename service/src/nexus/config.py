"""Environment-based configuration (NX-001).

Secrets are never read from this file's defaults in a deployed environment;
they are injected from the secret manager (SDD 10.2).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NEXUS_", env_file=".env", extra="ignore")

    env: str = "local"
    log_level: str = "INFO"

    database_url: str = "sqlite+aiosqlite:///./nexus.db"
    redis_url: str = "redis://localhost:6379/0"

    model_provider: str = "echo"

    # Budgets - SDD 9.6
    budget_wall_clock_ms: int = 300_000
    budget_tool_calls: int = 25
    budget_plan_steps: int = 15
    budget_replans: int = 2
    budget_tokens_in: int = 150_000
    budget_tokens_out: int = 20_000
    tool_fanout: int = 4

    # Retention - ADR-11
    retention_raw_payload_days: int = 30
    retention_evidence_days: int = 90
    retention_trace_days: int = 365

    # Kill switch - SDD 8.4
    disabled: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
