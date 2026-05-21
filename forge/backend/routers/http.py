"""
app/routers/http.py — REST HTTP endpoints.

Only two endpoints here (MVP):
  GET  /health    → Health check for Cloud Run (required!)
  POST /rooms     → Create a new game room, returns room code

WHY Cloud Run needs /health:
  Cloud Run sends periodic GET /health requests. If it returns non-200,
  Cloud Run thinks the container is broken and restarts it. ALWAYS have this.
"""

import random
import string

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.state import game_state
from app.models.quiz import Room

router = APIRouter()


def _generate_room_code() -> str:
    """
    Generate a unique 4-digit alphanumeric room code.
    We keep regenerating until we get one that isn't already in use.
    Collision probability is extremely low (36^4 = 1.6M combinations).
    """
    while True:
        # Uppercase letters + digits, looks cool on a mobile screen
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        if not game_state.room_exists(code):
            return code


# ─── Request / Response schemas ───

class CreateRoomRequest(BaseModel):
    host_name: str


class CreateRoomResponse(BaseModel):
    room_code: str
    message: str


# ─── Endpoints ───

@router.get("/health", tags=["System"])
async def health_check():
    """
    Cloud Run health probe. Must return 200 quickly.
    We also return the active room count for debugging.
    """
    return {
        "status": "ok",
        "active_rooms": len(game_state.rooms),
    }


@router.post("/rooms", response_model=CreateRoomResponse, tags=["Rooms"])
async def create_room(body: CreateRoomRequest):
    """
    Create a new game room.
    The host calls this first, gets a room code, then connects via WebSocket.
    
    Returns:
      room_code: 4-character code (e.g. "F3K9") players use to join
    """
    if not body.host_name.strip():
        raise HTTPException(status_code=400, detail="host_name cannot be empty")

    code = _generate_room_code()
    room = Room(code=code, host_name=body.host_name.strip())
    game_state.add_room(room)

    return CreateRoomResponse(
        room_code=code,
        message=f"Room {code} created. Share this code with your friends!",
    )