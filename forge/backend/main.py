"""
main.py — Forge: AI Trivia Showdown
Entry point for the FastAPI application.

We use a lifespan context manager (modern FastAPI pattern) instead of
the deprecated @app.on_event("startup") decorator.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import http, websocket
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    WHY: FastAPI's lifespan handles startup + shutdown in one place.
    Everything before `yield` runs on startup, after yield runs on shutdown.
    """
    print(f"🔥 Forge server starting — env: {settings.ENV}")
    yield
    print("💀 Forge server shutting down — clearing state.")


app = FastAPI(
    title="Forge: AI Trivia Showdown",
    description="Real-time multiplayer quiz game powered by Gemini AI",
    version="0.1.0",
    lifespan=lifespan,
)

# --- CORS ---
# WHY: CapacitorJS wraps our HTML and runs it as a native app.
# The WebView origin is "capacitor://localhost" or "http://localhost" —
# we must allow it, or the browser will block our API calls.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(http.router)
app.include_router(websocket.router)