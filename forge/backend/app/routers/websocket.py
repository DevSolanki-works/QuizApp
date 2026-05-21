"""
websocket.py — WebSocket endpoint for Forge.

This file will grow significantly in Milestone 5 (full game loop).
For now it establishes the connection, registers the player, and echoes
a PLAYER_JOINED event so we can verify the WS pipeline end-to-end.

WHY WEBSOCKETS INSTEAD OF POLLING:
  - Real-time leaderboard updates require the server to push to all clients
    simultaneously. Polling would mean every client asking "any updates?" every
    second — wasteful and laggy.
  - FastAPI's WebSocket support is built on Starlette and handles async I/O
    natively with Python's asyncio event loop. No extra broker needed.
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.state import rooms
from app.models.quiz import Room

logger = logging.getLogger(__name__)
router = APIRouter()


async def _broadcast(room: Room, message: dict) -> None:
    """
    Send a JSON message to every connected player in a room.

    WHY GATHER IS NOT USED HERE:
      asyncio.gather() would be faster but makes error handling trickier —
      if one WebSocket is already closed, the whole gather raises.
      Sequential sends with individual try/except is safer for game state.
    """
    payload = json.dumps(message)
    disconnected = []

    for name, player in room.players.items():
        if player.websocket:
            try:
                await player.websocket.send_text(payload)
            except Exception:
                # Mark for cleanup — don't mutate dict while iterating
                disconnected.append(name)

    # Clean up any sockets that died during broadcast
    for name in disconnected:
        room.remove_player(name)
        logger.info("Removed disconnected player '%s' from room %s", name, room.code)


@router.websocket("/ws/{room_code}/{player_name}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_code: str,
    player_name: str,
) -> None:
    """
    Main WebSocket handler.

    URL: ws://<host>/ws/<room_code>/<player_name>
    Example: ws://localhost:8000/ws/1234/Alice

    Lifecycle:
      1. Accept connection
      2. Validate room exists
      3. Register player in room
      4. Broadcast PLAYER_JOINED to all
      5. Listen for messages until disconnect
    """
    await websocket.accept()

    # ── Validate room ─────────────────────────────────────────────────────────
    if room_code not in rooms:
        await websocket.send_text(
            json.dumps({"type": "ERROR", "data": {"message": "Room not found"}})
        )
        await websocket.close()
        return

    room = rooms[room_code]

    # ── Register player ───────────────────────────────────────────────────────
    room.add_player(player_name, websocket)
    logger.info("Player '%s' joined room %s (total: %d)", player_name, room_code, len(room.players))

    # ── Broadcast join event ──────────────────────────────────────────────────
    await _broadcast(room, {
        "type": "PLAYER_JOINED",
        "data": {"players": list(room.players.keys())},
    })

    # ── Message loop ──────────────────────────────────────────────────────────
    try:
        while True:
            raw = await websocket.receive_text()
            message = json.loads(raw)
            action = message.get("action")

            # Actions will be expanded in Milestone 5.
            # For now, log unrecognised actions and echo them back.
            logger.debug("Room %s | '%s' sent: %s", room_code, player_name, message)

            if action not in ("start_game", "answer"):
                await websocket.send_text(
                    json.dumps({"type": "ERROR", "data": {"message": f"Unknown action: {action}"}})
                )

    except WebSocketDisconnect:
        # ── Clean up on disconnect ────────────────────────────────────────────
        room.remove_player(player_name)
        logger.info("Player '%s' disconnected from room %s", player_name, room_code)

        if room.players:
            # Notify remaining players
            await _broadcast(room, {
                "type": "PLAYER_JOINED",
                "data": {"players": list(room.players.keys())},
            })
        else:
            # Empty room — remove it from state to free memory
            rooms.pop(room_code, None)
            logger.info("Room %s removed (empty)", room_code)

