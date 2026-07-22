"""
Forge — AI Trivia Showdown
FastAPI application entry point.
"""
import json
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import http as http_router
from app.routers import websocket as ws_router          # Milestone 5
from app.routers import auth as auth_router            # Milestone 17
from app.routers import challenges as challenges_router  # Duel Phase 1
from app.routers import duel_queue as duel_queue_router   # Duel Phase 2 (1v1 queue)
from app.routers import push as push_router               # Push notifications
from app.core.config import settings

logger = logging.getLogger(__name__)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ── Firebase Admin init (push notifications) ──────────────────────────────
# Guarded so a missing/empty credential (e.g. local dev without the secret)
# disables push silently rather than crashing the whole backend — every
# push-send call checks firebase_admin._apps before attempting to send.
if settings.FIREBASE_SERVICE_ACCOUNT_JSON:
    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            cred_dict = json.loads(settings.FIREBASE_SERVICE_ACCOUNT_JSON)
            firebase_admin.initialize_app(credentials.Certificate(cred_dict))
            logger.info("Firebase Admin initialized — push notifications enabled")
    except Exception as exc:
        logger.error("Firebase Admin init failed — push notifications disabled: %s", exc)
else:
    logger.warning("FIREBASE_SERVICE_ACCOUNT_JSON not set — push notifications disabled")

app = FastAPI(
    title="Forge — AI Trivia Showdown",
    description="Real-time multiplayer AI quiz game backend",
    version="0.5.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(http_router.router, tags=["rooms"])
# Duel queue MUST register before the generic room WS — otherwise
# /ws/{room_code}/{player_name} captures /ws/duel/queue as room "duel".
app.include_router(duel_queue_router.router, tags=["duel"])        # Duel Phase 2
app.include_router(ws_router.router, tags=["websocket"])  # Milestone 5
app.include_router(auth_router.router, prefix="/auth", tags=["auth"])  # Milestone 17
app.include_router(challenges_router.router, tags=["challenges"])  # Duel Phase 1
app.include_router(push_router.router, tags=["push"])       # Push notifications