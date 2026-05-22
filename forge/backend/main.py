"""
Forge — AI Trivia Showdown
FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import http as http_router
from app.routers import websocket as ws_router          # Milestone 5

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
app.include_router(ws_router.router, tags=["websocket"])  # Milestone 5
