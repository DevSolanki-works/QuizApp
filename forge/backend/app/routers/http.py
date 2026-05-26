"""Thin REST endpoints for Forge room setup and health checks."""

import random
import string

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core import state
from app.models.quiz import DEFAULT_PLAY_MODE, GameStatus, PlayMode, Room

router = APIRouter()


class CreateRoomRequest(BaseModel):
    """Body expected when a player creates a new room."""

    host_name: str = "Host"
    play_mode: PlayMode = DEFAULT_PLAY_MODE


class CreateRoomResponse(BaseModel):
    """Room details returned to the creating player."""

    room_code: str
    host_name: str
    ws_url: str
    play_mode: PlayMode


def _generate_room_code() -> str:
    """Generate a unique four-character alphanumeric room code."""

    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        if code not in state.rooms:
            return code


@router.get("/health")
async def health_check():
    """Return a lightweight health response used for startup warming."""

    return {
        "status": "ok",
        "active_rooms": len(state.rooms),
    }


@router.post("/rooms/create", response_model=CreateRoomResponse)
async def create_room(body: CreateRoomRequest):
    """Create a waiting solo or classic room in process memory."""

    code = _generate_room_code()
    room = Room(
        code=code,
        host=body.host_name,
        status=GameStatus.WAITING,
        play_mode=body.play_mode,
    )
    state.rooms[code] = room

    return CreateRoomResponse(
        room_code=code,
        host_name=body.host_name,
        ws_url=f"/ws/{code}/{body.host_name}",
        play_mode=body.play_mode,
    )


@router.get("/rooms/{code}")
async def get_room(code: str):
    """Return public room metadata for validation and debugging."""

    room = state.rooms.get(code.upper())
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    return {
        "code": room.code,
        "host": room.host,
        "status": room.status,
        "play_mode": room.play_mode,
        "phase": room.phase,
        "players": list(room.players.keys()),
        "current_question": room.current_q_index,
    }


@router.delete("/rooms/{code}")
async def delete_room(code: str):
    """Manually remove a room for administration or local testing."""

    code = code.upper()
    if code not in state.rooms:
        raise HTTPException(status_code=404, detail="Room not found")

    del state.rooms[code]
    return {"deleted": code}
