"""
app/routers/websocket.py — The heart of Forge: real-time WebSocket game loop.

WHY WebSockets instead of regular HTTP polling?
  - HTTP polling (client asks "any updates?" every second) wastes bandwidth
    and introduces 0-1s latency per event. Bad for a fast-paced quiz game.
  - WebSockets keep a PERSISTENT connection open. The server can PUSH data
    the moment something happens (question starts, someone answers, etc.).
  - FastAPI's WebSocket support is built on asyncio — no threads, handles
    many concurrent connections on a single process efficiently.

HOW asyncio works here (simplified):
  - Python normally runs one thing at a time (single-threaded).
  - `async def` + `await` lets Python PAUSE a function while waiting for I/O
    (network, AI call) and run OTHER functions in the meantime.
  - So 50 players connected = 50 coroutines, but only 1 runs at a time.
    Python switches between them at every `await` point. No thread overhead.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.state import game_state
from app.models.quiz import Player, RoomStatus, AnswerAction, StartGameAction
from app.services.ai import generate_quiz

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── Helper: broadcast to all players in a room ───

async def broadcast(room_code: str, message: dict) -> None:
    """
    Send a JSON message to EVERY connected player in a room.

    WHY gather()?
    asyncio.gather() runs multiple coroutines CONCURRENTLY.
    Without it, we'd send to player 1, WAIT, then send to player 2, WAIT...
    With gather(), we start all sends simultaneously. Much faster.
    """
    room = game_state.get_room(room_code)
    if not room:
        return

    payload = json.dumps(message)
    # Build a list of send coroutines, one per player
    send_tasks = [
        player.websocket.send_text(payload)
        for player in room.players.values()
    ]
    # Fire them all at once; return_exceptions=True means one failure
    # doesn't cancel the others (e.g., if one player disconnected mid-send)
    await asyncio.gather(*send_tasks, return_exceptions=True)


# ─── Helper: send to one specific player ───

async def send_to(websocket: WebSocket, message: dict) -> None:
    await websocket.send_text(json.dumps(message))


# ─── Scoring formula ───

def calculate_score(time_ms: int) -> int:
    """
    Award points based on speed. Faster = more points.
    Correct answer: 500–1000 pts. Wrong answer: 0 pts.
    """
    time_ratio = min(time_ms / settings.TIME_LIMIT_MS, 1.0)
    return int(settings.BASE_POINTS * (1 - time_ratio * 0.5))


# ─── Game flow functions ───

async def send_question(room_code: str) -> None:
    """Broadcast the current question to all players."""
    room = game_state.get_room(room_code)
    if not room:
        return

    q = room.questions[room.current_question_index]
    room.reset_answers()  # Clear answered flags for this new question

    await broadcast(room_code, {
        "type": "QUESTION",
        "data": {
            "index": room.current_question_index,
            "total": len(room.questions),
            "text": q.question,
            "options": q.options,
            "time_limit_ms": settings.TIME_LIMIT_MS,
        }
    })
    logger.info(f"📢 Room {room_code}: sent question {room.current_question_index + 1}")


async def handle_answer(room_code: str, player_name: str, action: AnswerAction) -> None:
    """
    Process a player's answer, update their score, and advance game if needed.

    RACE CONDITION awareness:
    Two players might submit answers within milliseconds of each other.
    asyncio is single-threaded, so `await` points are the only places where
    context switches happen. The score update logic (no await) is atomic.
    """
    room = game_state.get_room(room_code)
    if not room or room.status != RoomStatus.IN_GAME:
        return

    player = room.players.get(player_name)
    if not player or player.answered_current:
        return  # Already answered — ignore duplicate

    # Mark as answered FIRST (prevents double-scoring if two messages arrive)
    player.answered_current = True

    # Get the correct answer
    current_q = room.questions[room.current_question_index]
    is_correct = action.choice == current_q.correct_index

    if is_correct:
        player.score += calculate_score(action.time_ms)

    logger.info(f"  Player {player_name} answered {'✅' if is_correct else '❌'}, score: {player.score}")

    # Check if ALL players have now answered
    if room.all_answered():
        await advance_game(room_code)


async def advance_game(room_code: str) -> None:
    """
    Broadcast the leaderboard, then either send the next question or end the game.
    Called when all players have answered the current question.
    """
    room = game_state.get_room(room_code)
    if not room:
        return

    current_q = room.questions[room.current_question_index]

    # 1. Send leaderboard + reveal the correct answer
    await broadcast(room_code, {
        "type": "LEADERBOARD",
        "data": {
            "scores": room.get_scores(),
            "correct_index": current_q.correct_index,
            "question_index": room.current_question_index,
        }
    })

    # 2. Small pause so players can see the leaderboard (3 seconds)
    await asyncio.sleep(3)

    # 3. Next question or game over?
    room.current_question_index += 1

    if room.current_question_index >= len(room.questions):
        # Game over
        room.status = RoomStatus.FINISHED
        await broadcast(room_code, {
            "type": "GAME_OVER",
            "data": {"final_scores": room.get_scores()}
        })
        logger.info(f"🏁 Room {room_code}: game finished!")
        # Clean up room after a delay (give players time to see results)
        await asyncio.sleep(60)
        game_state.remove_room(room_code)
    else:
        await send_question(room_code)


# ─── Main WebSocket endpoint ───

@router.websocket("/ws/{room_code}/{player_name}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, player_name: str):
    """
    The main WebSocket handler.

    URL: ws://your-server/ws/F3K9/Alice
    
    Lifecycle:
    1. Client connects → we validate room, add player, broadcast join event
    2. Client sends messages → we dispatch to handlers (start_game, answer)
    3. Client disconnects → we remove player, broadcast departure
    """
    # --- 1. Accept connection ---
    await websocket.accept()

    room = game_state.get_room(room_code)

    # Validate room exists
    if not room:
        await send_to(websocket, {
            "type": "ERROR",
            "data": {"message": f"Room '{room_code}' not found. Check the code and try again."}
        })
        await websocket.close()
        return

    # Validate room isn't full
    if len(room.players) >= settings.MAX_PLAYERS_PER_ROOM:
        await send_to(websocket, {
            "type": "ERROR",
            "data": {"message": "Room is full!"}
        })
        await websocket.close()
        return

    # Validate game hasn't already started
    if room.status != RoomStatus.WAITING:
        await send_to(websocket, {
            "type": "ERROR",
            "data": {"message": "Game already in progress. Wait for the next round."}
        })
        await websocket.close()
        return

    # --- 2. Add player to room ---
    player = Player(name=player_name, websocket=websocket)
    room.players[player_name] = player
    logger.info(f"👤 {player_name} joined room {room_code} ({len(room.players)} players)")

    # Tell everyone someone joined
    await broadcast(room_code, {
        "type": "PLAYER_JOINED",
        "data": {
            "player_name": player_name,
            "players": list(room.players.keys()),
            "host": room.host_name,
        }
    })

    # --- 3. Message loop ---
    try:
        while True:
            # `await` here = pause THIS coroutine until client sends a message
            # While paused, other players' coroutines can run (asyncio magic!)
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await send_to(websocket, {
                    "type": "ERROR",
                    "data": {"message": "Invalid JSON payload."}
                })
                continue

            action = data.get("action")

            # ── Handle: start_game ──
            if action == "start_game" and player_name == room.host_name:
                if room.status != RoomStatus.WAITING:
                    continue  # Can't start twice

                try:
                    msg = StartGameAction.model_validate(data)
                except Exception:
                    await send_to(websocket, {
                        "type": "ERROR",
                        "data": {"message": "Invalid start_game payload."}
                    })
                    continue

                # Tell players the game is loading (AI call takes 2-5s)
                await broadcast(room_code, {
                    "type": "GAME_STARTING",
                    "data": {"topic": msg.topic, "total_questions": settings.QUESTION_COUNT}
                })

                room.status = RoomStatus.IN_GAME

                try:
                    room.questions = await generate_quiz(msg.topic)
                except ValueError as e:
                    room.status = RoomStatus.WAITING
                    await broadcast(room_code, {
                        "type": "ERROR",
                        "data": {"message": str(e)}
                    })
                    continue

                await send_question(room_code)

            # ── Handle: answer ──
            elif action == "answer":
                try:
                    ans = AnswerAction.model_validate(data)
                    await handle_answer(room_code, player_name, ans)
                except Exception as e:
                    logger.warning(f"Bad answer payload from {player_name}: {e}")

    # --- 4. Handle disconnection ---
    except WebSocketDisconnect:
        logger.info(f"👋 {player_name} disconnected from room {room_code}")
        room.players.pop(player_name, None)

        if room.players:
            await broadcast(room_code, {
                "type": "PLAYER_LEFT",
                "data": {
                    "player_name": player_name,
                    "players": list(room.players.keys()),
                }
            })

            # If game is running and disconnected player was the last to answer,
            # check if we should advance
            if room.status == RoomStatus.IN_GAME and room.all_answered():
                await advance_game(room_code)
        else:
            # Empty room — clean it up immediately
            game_state.remove_room(room_code)
            logger.info(f"🗑️  Room {room_code} removed (empty)")