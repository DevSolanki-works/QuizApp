"""
Forge — AI Trivia Showdown
FastAPI application entry point.

Registers all routers and configures CORS so the frontend
(served from a different origin during dev) can talk to us.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import http as http_router
# websocket router will be imported in Milestone 5
# from app.routers import websocket as ws_router

app = FastAPI(
    title="Forge — AI Trivia Showdown",
    description="Real-time multiplayer AI quiz game backend",
    version="0.3.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allow all origins in dev; tighten to your Cloud Run URL in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(http_router.router, tags=["rooms"])
# app.include_router(ws_router.router, tags=["websocket"])  # Milestone 5
