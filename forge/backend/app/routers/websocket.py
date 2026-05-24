"""
WebSocket router for Forge: AI Trivia Showdown.
Handles the full real-time game loop:
  connect → start_game → questions → answers → leaderboard → game_over
"""

import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.state import rooms
from app.models.quiz import GameStatus, Player, Difficulty
from app.services.ai import generate_questions

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────────

async def broadcast(room_code: str, message: dict):
    """Send a message to every connected player in a room."""
    room = rooms.get(room_code)
    if not room:
        return
    for player in room.players.values():
        if player.websocket:
            try:
                await player.websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to {player.name}: {e}")


async def send_question(room_code: str):
    """
    Broadcast the current question to all players.
    Resets per-round answer tracking before sending.
    """
    room = rooms[room_code]
    question = room.questions[room.current_q_index]

    # Reset answer tracking for this round
    room.answers_this_round = {}
    for player in room.players.values():
        player.answered = False
        player.last_answer = None

    await broadcast(room_code, {
        "type": "QUESTION",
        "data": {
            "index":        room.current_q_index,
            "text":         question.question,
            "options":      question.options,
            "time_limit_ms": room.time_limit_ms,   # Uses room's configured timer
            "total":        room.total_questions,
            "difficulty":   room.difficulty.value,
        }
    })


async def check_round_complete(room_code: str):
    """
    Called after every answer submission.
    If all players have answered, broadcast leaderboard + advance to next question.
    """
    room = rooms.get(room_code)
    if not room:
        return

    all_answered = all(p.answered for p in room.players.values())

    if not all_answered:
        return  # Still waiting for remaining players

    correct_index = room.questions[room.current_q_index].correct_index

    # 1. Broadcast leaderboard with correct answer revealed
    await broadcast(room_code, {
        "type": "LEADERBOARD",
        "data": {
            "scores":        {n: p.score for n, p in room.players.items()},
            "correct_index": correct_index,
        }
    })

    # 2. Pause the game loop for 5 seconds so the UI can display the scores
    await asyncio.sleep(5)

    # 3. Re-fetch room in case it was deleted during the sleep (e.g., everyone quit)
    room = rooms.get(room_code)
    if not room:
        return

    # 4. Advance the index
    room.current_q_index += 1

    # 5. Route to Next Question or Game Over
    if room.current_q_index >= room.total_questions:
        # All questions done — end the game
        room.status = GameStatus.FINISHED
        await broadcast(room_code, {
            "type": "GAME_OVER",
            "data": {
                "final_scores": {n: p.score for n, p in room.players.items()}
            }
        })
    else:
        # Send the next question
        await send_question(room_code)

# ── Scoring ───────────────────────────────────────────────────────────────────

def calculate_score(time_ms: int, time_limit_ms: int) -> int:
    """
    Speed-based scoring formula.
    Correct answer: 500–1000 pts depending on how fast the player answered.
    Wrong answer:   0 pts (caller's responsibility not to call this).

    Args:
        time_ms:       How many milliseconds the player took to answer.
        time_limit_ms: The configured time limit for the room.

    Returns:
        Integer score between 500 and 1000.
    """
    BASE_POINTS = 1000
    score = int(BASE_POINTS * (1 - (time_ms / time_limit_ms) * 0.5))
    return max(500, min(1000, score))  # Clamp between 500–1000


# ── Main WebSocket endpoint ───────────────────────────────────────────────────

@router.websocket("/ws/{room_code}/{player_name}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, player_name: str):
    """
    Main WebSocket handler. One connection per player per room.

    Flow:
      1. Player connects → added to room → PLAYER_JOINED broadcast
      2. Host sends start_game → AI generates questions → GAME_STARTING + Q1
      3. Players send answers → scores updated → LEADERBOARD after all answer
      4. After final question → GAME_OVER broadcast
    """
    await websocket.accept()

    # Validate room exists
    if room_code not in rooms:
        await websocket.send_json({
            "type": "ERROR",
            "data": {"message": "Room not found"}
        })
        await websocket.close()
        return

    room = rooms[room_code]

    # Register player in the room
    room.players[player_name] = Player(name=player_name, websocket=websocket)
    logger.info(f"Player '{player_name}' joined room {room_code}")

    # Notify everyone about the new player
    await broadcast(room_code, {
        "type": "PLAYER_JOINED",
        "data": {"players": list(room.players.keys())}
    })

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            # ── start_game ────────────────────────────────────────────────────
            if action == "start_game":
                topic = data.get("topic", "General Knowledge").strip()

                # Read optional config from host message, fall back to room defaults
                difficulty_raw = data.get("difficulty", room.difficulty.value)
                try:
                    room.difficulty = Difficulty(difficulty_raw)
                except ValueError:
                    room.difficulty = Difficulty.MEDIUM

                total_q = data.get("total_questions", room.total_questions)
                # Clamp to valid range 5–20
                room.total_questions = max(5, min(20, int(total_q)))

                room.status = GameStatus.STARTING

                await broadcast(room_code, {
                    "type": "GAME_STARTING",
                    "data": {
                        "topic":            topic,
                        "total_questions":  room.total_questions,
                        "difficulty":       room.difficulty.value,
                        "time_limit_ms":    room.time_limit_ms,
                    }
                })

                # Generate questions via Gemini
                room.questions = await generate_questions(
                    topic=topic,
                    total_questions=room.total_questions,
                    difficulty=room.difficulty,
                )

                room.status = GameStatus.ACTIVE
                room.current_q_index = 0
                await send_question(room_code)

            # ── answer ────────────────────────────────────────────────────────
            elif action == "answer":
                if room.status != GameStatus.ACTIVE:
                    continue  # Ignore stale answers

                player = room.players.get(player_name)
                if not player or player.answered:
                    continue  # Already answered this round

                choice  = int(data.get("choice", -1))
                time_ms = int(data.get("time_ms", room.time_limit_ms))

                player.answered    = True
                player.last_answer = choice

                correct = room.questions[room.current_q_index].correct_index
                if choice == correct:
                    player.score += calculate_score(time_ms, room.time_limit_ms)

                await check_round_complete(room_code)

    except WebSocketDisconnect:
        logger.info(f"Player '{player_name}' disconnected from room {room_code}")
        room.players.pop(player_name, None)

        # Notify remaining players
        if room.players:
            await broadcast(room_code, {
                "type": "PLAYER_JOINED",
                "data": {"players": list(room.players.keys())}
            })
        else:
            # Empty room — clean up
            rooms.pop(room_code, None)
            logger.info(f"Room {room_code} removed (empty)")
