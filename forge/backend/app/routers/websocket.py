"""
WebSocket endpoint and authoritative real-time game loop.

The server owns each round phase so all clients see the same sequence:
question, answer reveal, an optional classic leaderboard intermission, then
the next question or results. A timeout task resolves unanswered rounds even
when no client sends a message at the deadline.
"""

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.state import rooms
from app.models.quiz import (
    DEFAULT_GAME_MODE,
    GameMode,
    GameStatus,
    PlayMode,
    Player,
    RoundPhase,
    time_limit_for_mode,
)
from app.services.ai import generate_questions

logger = logging.getLogger(__name__)
router = APIRouter()

BASE_POINTS = 1000
ANSWER_REVEAL_SECONDS = 4
INTERMISSION_LEADERBOARD_SECONDS = 5

_round_timeout_tasks: dict[str, asyncio.Task] = {}


async def broadcast(room_code: str, message: dict[str, Any]) -> None:
    """Send a JSON message to every connected player in a room."""

    room = rooms.get(room_code)
    if not room:
        return

    dead: list[str] = []
    for name, player in list(room.players.items()):
        try:
            await player.websocket.send_text(json.dumps(message))
        except Exception:
            dead.append(name)

    for name in dead:
        room.players.pop(name, None)
        logger.warning("Removed dead player '%s' from room '%s'", name, room_code)


async def send_to(websocket: WebSocket, message: dict[str, Any]) -> None:
    """Send one JSON message to one WebSocket connection."""

    await websocket.send_text(json.dumps(message))


def _cancel_round_timeout(room_code: str) -> None:
    """Cancel a room deadline task unless it is currently resolving itself."""

    task = _round_timeout_tasks.pop(room_code, None)
    if task and task is not asyncio.current_task():
        task.cancel()


def calculate_score(time_ms: int, time_limit_ms: int) -> int:
    """Calculate a correct-answer score between 500 and 1000 points."""

    clamped = max(0, min(time_ms, time_limit_ms))
    return int(BASE_POINTS * (1 - (clamped / time_limit_ms) * 0.5))


def _round_payload(room) -> dict[str, Any]:
    """Build shared answer and score data for reveal/intermission screens."""

    question = room.questions[room.current_q_index]
    return {
        "scores": {name: player.score for name, player in room.players.items()},
        "points_gained": dict(room.points_gained),
        "answers": dict(room.answers_this_round),
        "correct_index": question.correct_index,
        "play_mode": room.play_mode.value,
    }


async def _expire_question(room_code: str, question_index: int) -> None:
    """Resolve a question after its selected difficulty timer expires."""

    try:
        room = rooms.get(room_code)
        if not room:
            return
        await asyncio.sleep(room.time_limit_ms / 1000)
        await resolve_round(room_code, question_index)
    except asyncio.CancelledError:
        return


async def broadcast_question(room_code: str) -> None:
    """Start the current question, reset per-round data, and set its deadline."""

    room = rooms[room_code]
    question = room.questions[room.current_q_index]
    room.phase = RoundPhase.QUESTION
    room.answers_this_round = {}
    room.points_gained = {name: 0 for name in room.players}
    for player in room.players.values():
        player.answered = False
        player.last_answer = None

    await broadcast(
        room_code,
        {
            "type": "QUESTION",
            "data": {
                "index": room.current_q_index,
                "text": question.question,
                "options": question.options,
                "mode": room.mode.value,
                "play_mode": room.play_mode.value,
                "phase": room.phase.value,
                "time_limit_ms": room.time_limit_ms,
            },
        },
    )

    _cancel_round_timeout(room_code)
    _round_timeout_tasks[room_code] = asyncio.create_task(
        _expire_question(room_code, room.current_q_index)
    )


async def _finish_game(room_code: str) -> None:
    """Broadcast final scores and individual accuracy once all rounds finish."""

    room = rooms.get(room_code)
    if not room:
        return

    room.status = GameStatus.FINISHED
    room.phase = RoundPhase.COMPLETE
    total_questions = len(room.questions)
    final_scores = {name: player.score for name, player in room.players.items()}
    correct_answers = {
        name: player.correct_answers for name, player in room.players.items()
    }
    accuracy_percentages = {
        name: round((correct / total_questions) * 100) if total_questions else 0
        for name, correct in correct_answers.items()
    }
    await broadcast(
        room_code,
        {
            "type": "GAME_OVER",
            "data": {
                "final_scores": final_scores,
                "correct_answers": correct_answers,
                "accuracy_percentages": accuracy_percentages,
                "total_questions": total_questions,
                "play_mode": room.play_mode.value,
            },
        },
    )
    logger.info("Game finished in room '%s'. Scores: %s", room_code, final_scores)


async def resolve_round(room_code: str, question_index: int) -> None:
    """Lock the active question and progress through server-timed reveal states."""

    room = rooms.get(room_code)
    if (
        not room
        or room.status != GameStatus.ACTIVE
        or room.phase != RoundPhase.QUESTION
        or room.current_q_index != question_index
    ):
        return

    _cancel_round_timeout(room_code)
    room.phase = RoundPhase.ANSWER_REVEAL
    reveal_data = _round_payload(room)
    reveal_data.update(
        {"phase": room.phase.value, "hold_ms": ANSWER_REVEAL_SECONDS * 1000}
    )
    await broadcast(room_code, {"type": "ANSWER_REVEAL", "data": reveal_data})
    await asyncio.sleep(ANSWER_REVEAL_SECONDS)

    room = rooms.get(room_code)
    if not room or room.status != GameStatus.ACTIVE:
        return

    if room.play_mode == PlayMode.CLASSIC:
        room.phase = RoundPhase.INTERMISSION_LEADERBOARD
        intermission_data = _round_payload(room)
        intermission_data.update(
            {
                "phase": room.phase.value,
                "hold_ms": INTERMISSION_LEADERBOARD_SECONDS * 1000,
                "is_final": room.current_q_index + 1 >= len(room.questions),
            }
        )
        await broadcast(
            room_code,
            {"type": "INTERMISSION_LEADERBOARD", "data": intermission_data},
        )
        await asyncio.sleep(INTERMISSION_LEADERBOARD_SECONDS)

    room = rooms.get(room_code)
    if not room or room.status != GameStatus.ACTIVE:
        return

    if room.current_q_index + 1 >= len(room.questions):
        await _finish_game(room_code)
        return

    room.current_q_index += 1
    await broadcast_question(room_code)


@router.websocket("/ws/{room_code}/{player_name}")
async def websocket_endpoint(
    websocket: WebSocket, room_code: str, player_name: str
) -> None:
    """Accept a player and process room actions until the socket disconnects."""

    await websocket.accept()
    room = rooms.get(room_code)
    if not room:
        await send_to(websocket, {"type": "ERROR", "data": {"message": "Room not found"}})
        await websocket.close()
        return

    if room.status != GameStatus.WAITING:
        await send_to(
            websocket, {"type": "ERROR", "data": {"message": "Game already in progress"}}
        )
        await websocket.close()
        return

    if room.play_mode == PlayMode.SOLO and player_name != room.host:
        await send_to(
            websocket, {"type": "ERROR", "data": {"message": "Solo rooms are private"}}
        )
        await websocket.close()
        return

    if player_name in room.players:
        await send_to(
            websocket, {"type": "ERROR", "data": {"message": "Name already taken in this room"}}
        )
        await websocket.close()
        return

    room.players[player_name] = Player(name=player_name, websocket=websocket)
    logger.info("Player '%s' joined room '%s'", player_name, room_code)
    await broadcast(
        room_code,
        {"type": "PLAYER_JOINED", "data": {"players": list(room.players.keys())}},
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await send_to(
                    websocket, {"type": "ERROR", "data": {"message": "Invalid JSON"}}
                )
                continue

            action = msg.get("action")
            if action == "start_game":
                if player_name != room.host:
                    await send_to(
                        websocket,
                        {"type": "ERROR", "data": {"message": "Only the host can start the game"}},
                    )
                    continue
                if room.status != GameStatus.WAITING:
                    await send_to(
                        websocket,
                        {"type": "ERROR", "data": {"message": "Game already started"}},
                    )
                    continue

                requested_play_mode = str(
                    msg.get("play_mode", room.play_mode.value)
                ).lower()
                if requested_play_mode != room.play_mode.value:
                    await send_to(
                        websocket,
                        {"type": "ERROR", "data": {"message": "Room mode cannot be changed"}},
                    )
                    continue

                topic = str(msg.get("topic", "General Knowledge")).strip() or "General Knowledge"
                mode_value = str(msg.get("mode", DEFAULT_GAME_MODE.value)).strip().lower()
                try:
                    room.mode = GameMode(mode_value)
                except ValueError:
                    room.mode = DEFAULT_GAME_MODE
                room.time_limit_ms = time_limit_for_mode(room.mode)
                room.status = GameStatus.STARTING

                await broadcast(
                    room_code,
                    {
                        "type": "GAME_STARTING",
                        "data": {
                            "topic": topic,
                            "mode": room.mode.value,
                            "play_mode": room.play_mode.value,
                            "time_limit_ms": room.time_limit_ms,
                            "total_questions": 10,
                        },
                    },
                )

                try:
                    room.questions = await generate_questions(topic)
                except Exception as exc:
                    logger.error("Question generation failed for room '%s': %s", room_code, exc)
                    room.status = GameStatus.WAITING
                    room.phase = RoundPhase.LOBBY
                    await broadcast(
                        room_code,
                        {"type": "ERROR", "data": {"message": "Failed to generate questions. Try again."}},
                    )
                    continue

                for participant in room.players.values():
                    participant.score = 0
                    participant.correct_answers = 0
                room.status = GameStatus.ACTIVE
                room.current_q_index = 0
                await broadcast_question(room_code)

            elif action == "answer":
                if room.status != GameStatus.ACTIVE or room.phase != RoundPhase.QUESTION:
                    continue
                if player_name in room.answers_this_round:
                    continue

                choice = msg.get("choice")
                if not isinstance(choice, int) or choice not in range(4):
                    await send_to(
                        websocket, {"type": "ERROR", "data": {"message": "Invalid answer choice"}}
                    )
                    continue
                try:
                    time_ms = int(msg.get("time_ms", room.time_limit_ms))
                except (TypeError, ValueError):
                    time_ms = room.time_limit_ms

                question = room.questions[room.current_q_index]
                is_correct = choice == question.correct_index
                points = calculate_score(time_ms, room.time_limit_ms) if is_correct else 0
                player = room.players[player_name]
                player.score += points
                player.correct_answers += int(is_correct)
                player.answered = True
                player.last_answer = choice
                room.answers_this_round[player_name] = choice
                room.points_gained[player_name] = points

                if room.players and len(room.answers_this_round) >= len(room.players):
                    await resolve_round(room_code, room.current_q_index)

            else:
                await send_to(
                    websocket,
                    {"type": "ERROR", "data": {"message": f"Unknown action: '{action}'"}},
                )

    except WebSocketDisconnect:
        room.players.pop(player_name, None)
        logger.info("Player '%s' disconnected from room '%s'", player_name, room_code)
        if room.players:
            await broadcast(
                room_code,
                {"type": "PLAYER_JOINED", "data": {"players": list(room.players.keys())}},
            )
            if (
                room.status == GameStatus.ACTIVE
                and room.phase == RoundPhase.QUESTION
                and len(room.answers_this_round) >= len(room.players)
            ):
                asyncio.create_task(resolve_round(room_code, room.current_q_index))
        else:
            _cancel_round_timeout(room_code)
            rooms.pop(room_code, None)
            logger.info("Room '%s' deleted after its last player disconnected", room_code)
