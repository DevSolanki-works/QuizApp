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
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"

    # Milestone 17: Google Auth
    GOOGLE_CLIENT_ID: str = ""

    # Duel Phase 1: Supabase REST access for Challenge storage. This is the
    # SAME public anon key already embedded client-side in
    # frontend/app/supabase-client.js — safe to default here since it's
    # gated by Row Level Security, not secrecy.
    SUPABASE_URL: str = "https://ffstsbwkianjcjpqvmtv.supabase.co"
    SUPABASE_ANON_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZmc3RzYndraWFuamNqcHF2bXR2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA1NTczMzYsImV4cCI6MjA5NjEzMzMzNn0.G04L8E8TD_C8GWyEBXf5eBWjvcIXXlF8WtlEVkmBhwo"

    # Push notifications (Duel Phase 1 follow-up): the full Firebase service
    # account JSON, injected as a single env var from the
    # FIREBASE_SERVICE_ACCOUNT_JSON GitHub secret at deploy time. Never
    # committed — empty string locally means push is silently disabled
    # (see main.py), not a startup failure.
    FIREBASE_SERVICE_ACCOUNT_JSON: str = ""

    # File-backed profile store. This keeps the $0 infra constraint while
    # giving Google users durable balances on the running service instance.
    PROFILE_STORE_PATH: str = "app/data/profiles.json"

    class Config:
        # Load from a .env file when present (local dev).
        # In production (Cloud Run), real env vars take precedence automatically.
        env_file = ".env"
        env_file_encoding = "utf-8"


# Single shared instance — import this everywhere instead of re-instantiating.
settings = Settings()
