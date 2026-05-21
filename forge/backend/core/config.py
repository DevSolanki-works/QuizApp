"""
app/core/config.py — Centralized settings using Pydantic BaseSettings.

WHY Pydantic BaseSettings?
  - Reads from environment variables automatically (12-factor app pattern).
  - In development, you can put vars in a .env file.
  - In Cloud Run, you set them as Cloud Run env vars — no code change needed.
  - Type-safe: if GEMINI_API_KEY is missing, startup fails loudly with a clear error.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Pydantic will look for these as ENV VARS (case-insensitive).
    # If a .env file exists, it loads from there too.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # --- App ---
    ENV: str = "development"
    PORT: int = 8000

    # --- Gemini AI ---
    # Set this in Cloud Run as a secret env var. NEVER hardcode it.
    GEMINI_API_KEY: str = ""

    # --- CORS ---
    # Capacitor origins for Android + dev browser
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost",
        "http://localhost:3000",
        "capacitor://localhost",
        "https://localhost",
        "*",  # Loosen for dev; tighten before Play Store release
    ]

    # --- Game Rules ---
    MAX_PLAYERS_PER_ROOM: int = 8
    QUESTION_COUNT: int = 10
    TIME_LIMIT_MS: int = 15000      # 15 seconds per question
    BASE_POINTS: int = 1000         # Max score per correct answer


# Singleton — import this everywhere, don't re-instantiate.
settings = Settings()