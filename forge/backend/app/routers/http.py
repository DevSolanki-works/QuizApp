"""
HTTP REST endpoints for Forge.

Kept intentionally thin — heavy game logic lives in websocket.py.
HTTP layer only handles: health check, room creation, room info.
"""

import random
import string
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core import state
from app.models.quiz import Room, GameStatus

router = APIRouter()


# ── Request / Response schemas ────────────────────────────────────────────────

class CreateRoomRequest(BaseModel):
    """Body expected when a player creates a new room."""
    host_name: str = "Host"


class CreateRoomResponse(BaseModel):
    """What the client receives after room creation."""
    room_code: str
    host_name: str
    ws_url:    str   # Fully-formed WS path so the client doesn't have to build it


# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_room_code() -> str:
    """
    Generate a unique 4-digit alphanumeric room code.

    Uses uppercase letters + digits for easy verbal sharing ("room ALPHA-4").
    Retries until it finds a code not already in use (collision is extremely
    rare with 36^4 = 1.6M possibilities vs. typical concurrent rooms).
    """
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        if code not in state.rooms:
            return code


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/health")
async def health_check():
    """
    Lightweight liveness probe.

    Cloud Run hits this to know the container is alive.
    Also used by the frontend on app-launch to warm up the instance
    and show 'Connecting...' while the cold-start completes.
    """
    return {
        "status": "ok",
        "active_rooms": len(state.rooms),
    }


@router.post("/rooms/create", response_model=CreateRoomResponse)
async def create_room(body: CreateRoomRequest):
    """
    Create a new game room and register it in memory.

    Flow:
      1. Generate unique 4-digit code
      2. Instantiate Room with host as first player
      3. Store in state.rooms
      4. Return code + ready-to-use WS URL to the client
    """
    code = _generate_room_code()

    room = Room(
        code=code,
        host=body.host_name,
        status=GameStatus.WAITING,
    )
    state.rooms[code] = room

    return CreateRoomResponse(
        room_code=code,
        host_name=body.host_name,
        # Client plugs this straight into new WebSocket(ws_url)
        ws_url=f"/ws/{code}/{body.host_name}",
    )


@router.get("/rooms/{code}")
async def get_room(code: str):
    """
    Return current state of a room (for debugging / reconnect use).

    Raises 404 if the code doesn't exist, so the client can show
    'Room not found' before even attempting a WS connection.
    """
    room = state.rooms.get(code.upper())
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    return {
        "code":    room.code,
        "host":    room.host,
        "status":  room.status,
        "players": list(room.players.keys()),
        "current_question": room.current_q_index,
    }


@router.delete("/rooms/{code}")
async def delete_room(code: str):
    """
    Manually delete a room (admin/testing convenience).

    In production, rooms are cleaned up when all WebSocket
    connections close (handled in websocket.py).
    """
    code = code.upper()
    if code not in state.rooms:
        raise HTTPException(status_code=404, detail="Room not found")

    del state.rooms[code]
    return {"deleted": code}
