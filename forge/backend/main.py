"""
main.py — Forge backend entry point.

This is the file uvicorn loads:  uvicorn main:app --reload

Responsibilities:
  - Create the FastAPI app instance
  - Mount all routers
  - Configure logging
  - Define startup/shutdown lifecycle hooks (for future use)
"""

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import http as http_router
from app.routers import websocket as ws_router

# ── Logging ───────────────────────────────────────────────────────────────────
# Send all logs to stdout so Cloud Run's logging driver captures them.
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ── App instance ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Forge — AI Trivia Showdown",
    version=settings.app_version,
    description="Real-time multiplayer quiz game powered by Gemini AI.",
    docs_url="/docs",       # Swagger UI at /docs (disable in production if desired)
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# WHY: The frontend (running as a local file via CapacitorJS, or from a CDN)
# will make fetch() calls to this API. Without CORS headers the browser blocks
# them. In production, replace "*" with your actual frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
# HTTP REST endpoints (health, room creation)
app.include_router(http_router.router)

# WebSocket endpoint (game real-time communication)
app.include_router(ws_router.router)


# ── Lifecycle hooks ───────────────────────────────────────────────────────────

@app.on_event("startup")
async def on_startup() -> None:
    """
    Runs once when uvicorn starts the process.
    Good place for: pre-warming Gemini client, loading assets, etc.
    """
    logger.info("🔥 Forge backend starting up — version %s", settings.app_version)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """
    Runs when the process is shutting down (SIGTERM from Cloud Run).
    In-memory state will be lost — acceptable for MVP.
    """
    logger.info("Forge backend shutting down. Active rooms lost (in-memory).")
