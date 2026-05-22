"""
websocket.py — WebSocket endpoint and real-time game loop.

WHY WEBSOCKETS:
  HTTP is request/response — the server can't push to clients.
  WebSockets keep a persistent connection open so the server can
  broadcast questions, scores, and events to all players instantly.

FLOW PER CONNECTION:
  1. Player connects → added to room → PLAYER_JOINED broadcast
  2. Host sends start_game → Gemini generates questions → game begins
  3. Players send answers → server scores them
  4. When ALL players answered → LEADERBOARD broadcast → next question
  5. After Q10 → GAME_OVER broadcast
"""

import asyncio
import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.state import rooms
from app.models.quiz import GameStatus, Player
from app.services.ai import generate_questions

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Scoring constants (mirrors CLAUDE.md spec) ────────────────────────────────
BASE_POINTS = 1000
TIME_LIMIT_MS = 15000


# ── Helpers ───────────────────────────────────────────────────────────────────

async def broadcast(room_code: str, message: Dict[str, Any]) -> None:
    """
    Send a JSON message to every connected player in a room.

    WHY WE TRACK DEAD CONNECTIONS:
      If a player's socket closed unexpectedly, send_text() raises an exception.
      We collect those players and remove them after the loop so we don't mutate
      the dict while iterating over it.
    """
    if room_code not in rooms:
        return

    dead = []
    for name, player in rooms[room_code].players.items():
        try:
            await player.websocket.send_text(json.dumps(message))
        except Exception:
            dead.append(name)

    for name in dead:
        rooms[room_code].players.pop(name, None)
        logger.warning("Removed dead connection for player '%s' in room '%s'", name, room_code)


async def send_to(websocket: WebSocket, message: Dict[str, Any]) -> None:
    """Send a JSON message to a single WebSocket connection."""
    await websocket.send_text(json.dumps(message))


async def broadcast_question(room_code: str) -> None:
    """
    Broadcast the current question to all players and reset round state.

    Called both at the start of the game and after each leaderboard reveal.
    """
    room = rooms[room_code]
    q = room.questions[room.current_q_index]

    # Reset per-round tracking before sending so no race conditions
    room.answers_this_round = {}
    for p in room.players.values():
        p.answered = False

    await broadcast(room_code, {
        "type": "QUESTION",
        "data": {
            "index": room.current_q_index,
            "text": q.question,
            "options": q.options,
            "time_limit_ms": TIME_LIMIT_MS,
        }
    })


def calculate_score(time_ms: int) -> int:
    """
    Speed bonus formula from CLAUDE.md spec.
    Correct answer in 0ms  → 1000 pts
    Correct answer in 15s  → 500 pts
    Wrong answer           → 0 pts (handled by caller)
    """
    clamped = max(0, min(time_ms, TIME_LIMIT_MS))
    return int(BASE_POINTS * (1 - (clamped / TIME_LIMIT_MS) * 0.5))


# ── Main WebSocket endpoint ───────────────────────────────────────────────────

@router.websocket("/ws/{room_code}/{player_name}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, player_name: str):
    """
    Single entry point for all player connections.

    Each player (including the host) connects here. The host is identified by
    matching player_name against room.host — no separate endpoint needed.
    """

    # ── Pre-connection validation ─────────────────────────────────────────────
    # Must accept() before sending anything, even error messages.
    await websocket.accept()

    if room_code not in rooms:
        await send_to(websocket, {"type": "ERROR", "data": {"message": "Room not found"}})
        await websocket.close()
        return

    room = rooms[room_code]

    if room.status != GameStatus.WAITING:
        await send_to(websocket, {"type": "ERROR", "data": {"message": "Game already in progress"}})
        await websocket.close()
        return

    if player_name in room.players:
        await send_to(websocket, {"type": "ERROR", "data": {"message": "Name already taken in this room"}})
        await websocket.close()
        return

    # ── Register player ───────────────────────────────────────────────────────
    room.players[player_name] = Player(name=player_name, websocket=websocket)
    logger.info("Player '%s' joined room '%s' (%d players)", player_name, room_code, len(room.players))

    await broadcast(room_code, {
        "type": "PLAYER_JOINED",
        "data": {"players": list(room.players.keys())}
    })

    # ── Message loop ──────────────────────────────────────────────────────────
    try:
        while True:
            raw = await websocket.receive_text()

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await send_to(websocket, {"type": "ERROR", "data": {"message": "Invalid JSON"}})
                continue

            action = msg.get("action")

            # ── ACTION: start_game ────────────────────────────────────────────
            if action == "start_game":
                # Only the host can trigger this
                if player_name != room.host:
                    await send_to(websocket, {
                        "type": "ERROR",
                        "data": {"message": "Only the host can start the game"}
                    })
                    continue

                if room.status != GameStatus.WAITING:
                    await send_to(websocket, {
                        "type": "ERROR",
                        "data": {"message": "Game already started"}
                    })
                    continue

                if len(room.players) < 1:
                    await send_to(websocket, {
                        "type": "ERROR",
                        "data": {"message": "Need at least 1 player to start"}
                    })
                    continue

                topic = msg.get("topic", "General Knowledge").strip() or "General Knowledge"
                room.status = GameStatus.STARTING

                # Tell everyone we're generating questions
                await broadcast(room_code, {
                    "type": "GAME_STARTING",
                    "data": {"topic": topic, "total_questions": 10}
                })

                # Call Gemini — takes 1-3 seconds
                # We stay in STARTING status during this time so no one can
                # send answers while questions are being fetched.
                try:
                    room.questions = await generate_questions(topic)
                except Exception as e:
                    logger.error("Question generation failed for room '%s': %s", room_code, e)
                    room.status = GameStatus.WAITING
                    await broadcast(room_code, {
                        "type": "ERROR",
                        "data": {"message": "Failed to generate questions. Try again."}
                    })
                    continue

                # Game is live — send first question
                room.status = GameStatus.ACTIVE
                room.current_q_index = 0
                await broadcast_question(room_code)

            # ── ACTION: answer ────────────────────────────────────────────────
            elif action == "answer":
                if room.status != GameStatus.ACTIVE:
                    continue

                # Ignore duplicate answers from same player this round
                if player_name in room.answers_this_round:
                    continue

                choice = msg.get("choice")
                time_ms = int(msg.get("time_ms", TIME_LIMIT_MS))

                current_q = room.questions[room.current_q_index]
                is_correct = (choice == current_q.correct_index)

                # Score and record the answer
                pts = calculate_score(time_ms) if is_correct else 0
                room.players[player_name].score += pts
                room.players[player_name].answered = True
                room.answers_this_round[player_name] = choice

                logger.debug(
                    "Room %s | %s answered %s (%s) +%d pts",
                    room_code, player_name, choice,
                    "correct" if is_correct else "wrong", pts
                )

                # Check if every connected player has answered
                if len(room.answers_this_round) >= len(room.players):
                    scores = {name: p.score for name, p in room.players.items()}

                    # Reveal correct answer + current scores
                    await broadcast(room_code, {
                        "type": "LEADERBOARD",
                        "data": {
                            "scores": scores,
                            "correct_index": current_q.correct_index,
                        }
                    })

                    # Give players 3 seconds to read the leaderboard
                    await asyncio.sleep(3)

                    room.current_q_index += 1

                    if room.current_q_index >= len(room.questions):
                        # All 10 questions done
                        room.status = GameStatus.FINISHED
                        await broadcast(room_code, {
                            "type": "GAME_OVER",
                            "data": {"final_scores": scores}
                        })
                        logger.info("Game finished in room '%s'. Scores: %s", room_code, scores)
                    else:
                        # Send next question
                        await broadcast_question(room_code)

            else:
                await send_to(websocket, {
                    "type": "ERROR",
                    "data": {"message": f"Unknown action: '{action}'"}
                })

    # ── Disconnect handling ───────────────────────────────────────────────────
    except WebSocketDisconnect:
        room.players.pop(player_name, None)
        logger.info("Player '%s' disconnected from room '%s'", player_name, room_code)

        if room.players:
            # Notify remaining players
            await broadcast(room_code, {
                "type": "PLAYER_JOINED",
                "data": {"players": list(room.players.keys())}
            })
        else:
            # Last player left — clean up the room
            rooms.pop(room_code, None)
            logger.info("Room '%s' deleted (all players disconnected)", room_code)
