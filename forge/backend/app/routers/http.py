"""
http.py — REST endpoints for Forge.

Endpoints defined here:
  GET  /health        → liveness probe (used by Cloud Run + app launch screen)
  POST /rooms/create  → create a new game room, return code + ws URL

WHY SEPARATE ROUTER:
  FastAPI routers let us split endpoints into logical files and mount them
  all in main.py with a prefix. Keeps files small and focused.
"""

import random
import string

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.core.state import rooms
from app.models.quiz import Room

router = APIRouter()


# ── Response schemas ──────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str


class CreateRoomResponse(BaseModel):
    room_code: str
    ws_url: str      # ws://… or wss://… — client connects here


# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_room_code() -> str:
    """
    Generate a unique 4-digit numeric room code.
    Keeps regenerating on collision (extremely rare with <10 concurrent rooms).
    """
    while True:
        code = "".join(random.choices(string.digits, k=4))
        if code not in rooms:
            return code


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["meta"])
async def health_check() -> HealthResponse:
    """
    Liveness probe.
    Cloud Run hits this to decide if the container is ready.
    The frontend pings this on launch to wake the container and show
    a 'Connecting…' spinner instead of a dead screen.
    """
    return HealthResponse(status="ok", version=settings.app_version)


@router.post("/rooms/create", response_model=CreateRoomResponse, tags=["rooms"])
async def create_room() -> CreateRoomResponse:
    """
    Create a new game room.

    Returns a 4-digit room code + the WebSocket URL the host should
    connect to. Other players will receive this code out-of-band (share
    it verbally or via the UI) and connect to the same WS path.

    Room creation is intentionally simple: no auth, no user accounts.
    The host is whoever connects first over WebSocket.
    """
    code = _generate_room_code()
    rooms[code] = Room(code=code)

    # Build the WS URL.
    # In development this will be ws://localhost:8000/ws/1234/{player_name}.
    # Cloud Run strips the path prefix so the URL stays the same shape.
    ws_url = f"/ws/{code}"   # relative — frontend prepends the host

    return CreateRoomResponse(room_code=code, ws_url=ws_url)
