"""
Duel matchmaking WebSocket endpoint (Sync 1v1 Duel Queue — Duel Phase 2).

Flow:
  Client connects to /ws/duel/queue?user_id=..&name=..&trophies=..
  → server tries an instant match against everyone already waiting
  → no match: player is queued, all waiters get live QUEUE_STATUS counts
  → match found: both sockets get MATCH_FOUND {room_code, opponent, h2h}
    then both clients disconnect here and join the duel room via the
    normal /ws/{room_code}/{player_name} endpoint (game loop lives there).
  Client actions: {"action": "request_bot"} → practice room vs bot,
                  {"action": "cancel"}      → leave the queue.

The queue is per-instance, same trust model as rooms — see duels.py.
"""

import json
import logging
import random

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.limiter import extract_real_ip_from_ws, is_rate_limited
from app.core.sanitize import sanitize_string, MAX_NAME_LEN
from app.services.duels import (
    QueueEntry,
    add_to_queue,
    create_bot_duel_room,
    create_duel_room,
    duel_queue,
    find_match,
    get_h2h,
    queue_size,
    remove_from_queue,
)
from app.services.profiles import ROOM_ENTRY_FEE, can_afford_entry, get_profile

logger = logging.getLogger(__name__)
router = APIRouter()


async def _send(ws: WebSocket, msg_type: str, data: dict) -> None:
    await ws.send_text(json.dumps({"type": msg_type, "data": data}))


async def _broadcast_queue_status() -> None:
    """Push the live waiting count to everyone still in the queue."""
    count = queue_size()
    for entry in list(duel_queue.values()):
        try:
            await _send(entry.websocket, "QUEUE_STATUS", {"waiting": count})
        except Exception:
            remove_from_queue(entry.user_id)


async def _announce_match(a: QueueEntry, b: QueueEntry) -> bool:
    """
    Create the duel room and tell both players. Returns True on success.

    If either socket is already dead, the room is torn down and the
    surviving player is re-queued so they never get stuck in a ghost match.
    """
    from app.core import state

    room = create_duel_room(a, b)
    h2h = get_h2h(a.user_id, b.user_id)
    payload_for = lambda me, opp: {
        "room_code":         room.code,
        "opponent_name":     opp.name,
        "opponent_trophies": opp.trophies,
        "your_trophies":     me.trophies,
        "h2h_you":           h2h.get(me.user_id, 0),
        "h2h_them":          h2h.get(opp.user_id, 0),
        "entry_fee":         ROOM_ENTRY_FEE,
    }
    try:
        await _send(a.websocket, "MATCH_FOUND", payload_for(a, b))
        await _send(b.websocket, "MATCH_FOUND", payload_for(b, a))
    except Exception as exc:
        logger.warning("Duel match announce failed, dissolving room %s: %s", room.code, exc)
        state.rooms.pop(room.code, None)
        return False
    logger.info("Duel matched: '%s' vs '%s' → room %s", a.name, b.name, room.code)
    return True


@router.websocket("/ws/duel/queue")
async def duel_queue_endpoint(
    websocket: WebSocket,
    user_id: str = "",
    name: str = "",
) -> None:
    """Hold a matchmaking socket open until matched, cancelled, or disconnected."""

    await websocket.accept()

    ip = extract_real_ip_from_ws(websocket)
    if is_rate_limited(ip, action="ws_join"):
        await _send(websocket, "ERROR", {"message": "Too many attempts. Please wait a moment."})
        await websocket.close()
        return

    clean_name = sanitize_string(name, MAX_NAME_LEN)
    if not user_id or not clean_name:
        await _send(websocket, "ERROR", {"message": "Sign in with Google to play Duels."})
        await websocket.close()
        return

    # Server-side balance check — the entry fee is charged when the duel
    # actually starts (in the room), but a player who can't afford it must
    # not be allowed to waste an opponent's time.
    if not can_afford_entry(user_id):
        await _send(websocket, "ERROR", {
            "message": f"You need {ROOM_ENTRY_FEE} coins to enter the Duel Arena.",
        })
        await websocket.close()
        return

    trophies = int(get_profile(user_id).get("trophies", 0))
    entry = QueueEntry(
        name=clean_name, user_id=user_id, trophies=trophies, ip=ip, websocket=websocket
    )

    # ── Instant-match attempt before queueing ─────────────────────────────────
    opponent = find_match(entry)
    if opponent:
        remove_from_queue(opponent.user_id)
        if await _announce_match(entry, opponent):
            await _broadcast_queue_status()
            # Keep this socket open briefly so the client reads MATCH_FOUND,
            # then let the client close it and join the duel room.
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                pass
            return
        # Announce failed because the opponent's socket died — fall through
        # into the queue as if they were never there.

    if not add_to_queue(entry):
        await _send(websocket, "ERROR", {"message": "You're already in the queue on another screen."})
        await websocket.close()
        return

    await _broadcast_queue_status()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            action = msg.get("action") if isinstance(msg, dict) else None

            if action == "cancel":
                remove_from_queue(user_id)
                await _broadcast_queue_status()
                await _send(websocket, "QUEUE_CANCELLED", {})
                await websocket.close()
                return

            if action == "request_bot":
                remove_from_queue(user_id)
                await _broadcast_queue_status()
                room = create_bot_duel_room(entry)
                await _send(websocket, "MATCH_FOUND", {
                    "room_code":         room.code,
                    "opponent_name":     room.duel_bot_name,
                    "opponent_trophies": max(0, trophies + random.randint(-20, 20)),
                    "your_trophies":     trophies,
                    "is_bot":            True,
                    "h2h_you":           0,
                    "h2h_them":          0,
                    "entry_fee":         0,
                })
                try:
                    await websocket.receive_text()
                except WebSocketDisconnect:
                    pass
                return

            if action == "retry_match":
                # Client-driven periodic poll: cheap, avoids a server timer.
                opponent = find_match(entry)
                if opponent and opponent.user_id in duel_queue:
                    remove_from_queue(opponent.user_id)
                    remove_from_queue(user_id)
                    if await _announce_match(entry, opponent):
                        await _broadcast_queue_status()
                        try:
                            await websocket.receive_text()
                        except WebSocketDisconnect:
                            pass
                        return
                    add_to_queue(entry)

    except WebSocketDisconnect:
        remove_from_queue(user_id)
        await _broadcast_queue_status()
        logger.info("Duel queue: '%s' disconnected", clean_name)
