"""
config.py — Central settings for the Forge backend.

Uses pydantic-settings so every value can be overridden by an environment
variable (useful for Cloud Run where secrets are injected via env vars).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All runtime configuration lives here.
    Defaults are development-friendly; production values come from env vars.
    """

    # ── API keys ──────────────────────────────────────────────────────────────
    gemini_api_key: str = ""  # Set via GEMINI_API_KEY env var in production

    # ── Game tuning ───────────────────────────────────────────────────────────
    base_points: int = 1000          # Max points for a correct answer
    time_limit_ms: int = 15_000     # 15 seconds per question
    questions_per_game: int = 10

    # ── Server ────────────────────────────────────────────────────────────────
    app_version: str = "0.1.0"
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",          # loads a local .env in development
        env_file_encoding="utf-8",
        case_sensitive=False,     # GEMINI_API_KEY == gemini_api_key
    )


# Module-level singleton — import this everywhere:
#   from app.core.config import settings
settings = Settings()
