"""
config.py — Centralised settings loaded from environment variables.

WHY PYDANTIC SETTINGS:
  Pydantic's BaseSettings reads values from environment variables automatically.
  This means the same code works locally (via .env file) and on Cloud Run
  (via --set-env-vars flag) with zero code changes.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    All configurable values for the Forge backend.
    Add new env vars here — never hardcode secrets in source files.
    """

    # Gemini API key — optional for local fallback mode.
    GEMINI_API_KEY: str = ""

    # Optional: override the model name without redeploying
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Milestone 17: Google Auth
    GOOGLE_CLIENT_ID: str = ""

    class Config:
        # Load from a .env file when present (local dev).
        # In production (Cloud Run), real env vars take precedence automatically.
        env_file = ".env"
        env_file_encoding = "utf-8"


# Single shared instance — import this everywhere instead of re-instantiating.
settings = Settings()
