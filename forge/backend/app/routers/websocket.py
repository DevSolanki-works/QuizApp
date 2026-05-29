"""
WebSocket endpoint and authoritative real-time game loop.

The server owns each round phase so all clients see the same sequence:
question, answer reveal, an optional classic/team leaderboard intermission,
then the next question or results. A timeout task resolves unanswered rounds
even when no client sends a message at the deadline.

Streak/combo multiplier (Milestone 19):
  base_score = 500–1000 based on speed
  multiplier = min(1.0 + (streak // 3) * 0.5, 3.0)
  streak 0-2 → ×1.0 | 3-5 → ×1.5 | 6-8 → ×2.0 | 9-11 → ×2.5 | 12+ → ×3.0
  Wrong answer or timeout resets streak to 0.
"""

import asyncio
import json
import logging
import random
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.state import rooms
from app.core.limiter import is_rate_limited
from app.models.quiz import (
    DEFAULT_GAME_MODE,
    Question,
    GameMode,
    GameStatus,
    PlayMode,
    Player,
    RoundPhase,
    time_limit_for_mode,
)
from app.services.ai import generate_questions
from app.services.ai import FALLBACK_QUESTIONS

logger = logging.getLogger(__name__)
router = APIRouter()

BASE_POINTS = 1000
ANSWER_REVEAL_SECONDS = 4
INTERMISSION_LEADERBOARD_SECONDS = 5
GENERATION_TIMEOUT_SECONDS = 30

_round_timeout_tasks: dict[str, asyncio.Task] = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def broadcast(room_code: str, message: dict[str, Any]) -> None:
    """Send a JSON message to every connected player in a room."""

    room = rooms.get(room_code)
    if not room:
        return

    dead: list[str] = []
    for name, player in list(room.players.items()):
        if player.websocket is None:
            continue
        try:
            await player.websocket.send_text(json.dumps(message))
        except Exception:
            dead.append(name)

    for name in dead:
        room.players.pop(name, None)
        logger.warning("Removed dead player '%s' from room '%s'", name, room_code)


async def _delayed_room_cleanup(room_code: str, delay: int = 60) -> None:
    """Delete a room if it remains empty after a grace period."""

    await asyncio.sleep(delay)
    room = rooms.get(room_code)
    if not room:
        return

    if not any(p.websocket is not None for p in room.players.values()):
        _cancel_round_timeout(room_code)
        rooms.pop(room_code, None)
        logger.info("Room '%s' deleted after grace period", room_code)


async def send_to(websocket: WebSocket, message: dict[str, Any]) -> None:
    """Send one JSON message to one WebSocket connection."""

    await websocket.send_text(json.dumps(message))


def _cancel_round_timeout(room_code: str) -> None:
    """Cancel a room deadline task unless it is currently resolving itself."""

    task = _round_timeout_tasks.pop(room_code, None)
    if task and task is not asyncio.current_task():
        task.cancel()


def calculate_score(time_ms: int, time_limit_ms: int, streak: int) -> int:
    """
    Calculate a correct-answer score with streak/combo multiplier.

    Base score: 500–1000 based on answer speed.
    Multiplier: ×1.0 (streak 0-2) → ×1.5 (3-5) → ×2.0 (6-8) → ×2.5 (9-11) → ×3.0 (12+)
    """

    clamped = max(0, min(time_ms, time_limit_ms))
    base = int(BASE_POINTS * (1 - (clamped / time_limit_ms) * 0.5))
    base = max(500, min(1000, base))

    multiplier = min(1.0 + (streak // 3) * 0.5, 3.0)
    return int(base * multiplier)


def _team_scores(room) -> dict[str, int]:
    """Aggregate individual player scores into team totals."""

    totals: dict[str, int] = {tid: 0 for tid in room.team_names}
    for player_name, player in room.players.items():
        team_id = room.teams.get(player_name)
        if team_id in totals:
            totals[team_id] += player.score
    return totals


def _round_payload(room) -> dict[str, Any]:
    """Build shared answer and score data for reveal/intermission screens."""

    question = room.questions[room.current_q_index]
    payload: dict[str, Any] = {
        "scores": {name: player.score for name, player in room.players.items()},
        "points_gained": dict(room.points_gained),
        "answers": dict(room.answers_this_round),
        "correct_index": question.correct_index,
        "play_mode": room.play_mode.value,
        "streaks": {name: player.streak for name, player in room.players.items()},
    }
    if room.play_mode == PlayMode.TEAM:
        payload["team_scores"] = _team_scores(room)
        payload["teams"] = dict(room.teams)
        payload["team_names"] = dict(room.team_names)
    return payload


# ── Round lifecycle ───────────────────────────────────────────────────────────

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

    msg_data: dict[str, Any] = {
        "index": room.current_q_index,
        "text": question.question,
        "options": question.options,
        "mode": room.mode.value,
        "play_mode": room.play_mode.value,
        "phase": room.phase.value,
        "time_limit_ms": room.time_limit_ms,
    }
    if room.play_mode == PlayMode.TEAM:
        msg_data["team_scores"] = _team_scores(room)
        msg_data["teams"] = dict(room.teams)
        msg_data["team_names"] = dict(room.team_names)

    await broadcast(room_code, {"type": "QUESTION", "data": msg_data})

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

    game_over_data: dict[str, Any] = {
        "final_scores": final_scores,
        "correct_answers": correct_answers,
        "accuracy_percentages": accuracy_percentages,
        "total_questions": total_questions,
        "play_mode": room.play_mode.value,
    }
    if room.play_mode == PlayMode.TEAM:
        game_over_data["team_scores"] = _team_scores(room)
        game_over_data["teams"] = dict(room.teams)
        game_over_data["team_names"] = dict(room.team_names)

    await broadcast(room_code, {"type": "GAME_OVER", "data": game_over_data})
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

    # Reset streak for players who did NOT answer (timeout = wrong)
    for name, player in room.players.items():
        if name not in room.answers_this_round:
            player.streak = 0

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

    if room.play_mode in (PlayMode.CLASSIC, PlayMode.TEAM):
        room.phase = RoundPhase.INTERMISSION_LEADERBOARD
        intermission_data = _round_payload(room)
        is_final = room.current_q_index + 1 >= len(room.questions)
        hold_seconds = 2 if is_final else INTERMISSION_LEADERBOARD_SECONDS
        intermission_data.update(
            {
                "phase": room.phase.value,
                "hold_ms": hold_seconds * 1000,
                "is_final": is_final,
            }
        )
        await broadcast(
            room_code,
            {"type": "INTERMISSION_LEADERBOARD", "data": intermission_data},
        )
        await asyncio.sleep(hold_seconds)

    room = rooms.get(room_code)
    if not room or room.status != GameStatus.ACTIVE:
        return

    if room.current_q_index + 1 >= len(room.questions):
        await _finish_game(room_code)
        return

    room.current_q_index += 1
    await broadcast_question(room_code)


# ── WebSocket endpoint ────────────────────────────────────────────────────────

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

    # RE-JOIN LOGIC:
    # If the player was already in the room but their socket is gone, allow re-join.
    existing_player = room.players.get(player_name)

    if existing_player:
        if existing_player.websocket is not None:
            await send_to(
                websocket,
                {"type": "ERROR", "data": {"message": "Name already taken in this room"}},
            )
            await websocket.close()
            return
        else:
            existing_player.websocket = websocket
            logger.info("Player '%s' re-joined room '%s'", player_name, room_code)
    else:
        if room.status != GameStatus.WAITING:
            await send_to(
                websocket,
                {"type": "ERROR", "data": {"message": "Game already in progress"}},
            )
            await websocket.close()
            return

        if room.play_mode == PlayMode.SOLO and player_name != room.host:
            await send_to(
                websocket,
                {"type": "ERROR", "data": {"message": "Solo rooms are private"}},
            )
            await websocket.close()
            return

        room.players[player_name] = Player(name=player_name, websocket=websocket)
        logger.info("Player '%s' joined room '%s'", player_name, room_code)

    # Build PLAYER_JOINED payload (include team state for team rooms)
    joined_data: dict[str, Any] = {"players": list(room.players.keys())}
    if room.play_mode == PlayMode.TEAM:
        joined_data["teams"] = dict(room.teams)
        joined_data["team_names"] = dict(room.team_names)
        joined_data["team_topics"] = dict(room.team_topics)

    await broadcast(room_code, {"type": "PLAYER_JOINED", "data": joined_data})

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

            # ── join_team ──────────────────────────────────────────────────────
            if action == "join_team":
                if room.play_mode != PlayMode.TEAM:
                    continue
                team_id = str(msg.get("team_id", "")).upper()
                if team_id not in ("A", "B"):
                    await send_to(
                        websocket,
                        {"type": "ERROR", "data": {"message": "Team must be A or B"}},
                    )
                    continue
                room.teams[player_name] = team_id
                team_update: dict[str, Any] = {
                    "players": list(room.players.keys()),
                    "teams": dict(room.teams),
                    "team_names": dict(room.team_names),
                    "team_topics": dict(room.team_topics),
                }
                await broadcast(room_code, {"type": "PLAYER_JOINED", "data": team_update})

            # ── set_team_info (host only) ──────────────────────────────────────
            elif action == "set_team_info":
                if room.play_mode != PlayMode.TEAM or player_name != room.host:
                    continue
                name_a = str(msg.get("name_a", "Team A")).strip()[:20] or "Team A"
                name_b = str(msg.get("name_b", "Team B")).strip()[:20] or "Team B"
                topic_a = str(msg.get("topic_a", "")).strip()[:60]
                topic_b = str(msg.get("topic_b", "")).strip()[:60]
                room.team_names = {"A": name_a, "B": name_b}
                if topic_a:
                    room.team_topics["A"] = topic_a
                if topic_b:
                    room.team_topics["B"] = topic_b
                info_update: dict[str, Any] = {
                    "players": list(room.players.keys()),
                    "teams": dict(room.teams),
                    "team_names": dict(room.team_names),
                    "team_topics": dict(room.team_topics),
                }
                await broadcast(room_code, {"type": "PLAYER_JOINED", "data": info_update})

            # ── start_game ────────────────────────────────────────────────────
            elif action == "start_game":
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

                # Rate limit check
                ip = websocket.client.host
                forwarded = websocket.headers.get("X-Forwarded-For")
                if forwarded:
                    ip = forwarded.split(",")[0].strip()

                if is_rate_limited(ip, action="quiz", limit=3):
                    logger.warning("Rate limit hit for IP %s (start_game)", ip)
                    await send_to(
                        websocket,
                        {"type": "ERROR", "data": {"message": "Quiz generation limit reached. Wait a minute!"}},
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

                mode_value = str(msg.get("mode", DEFAULT_GAME_MODE.value)).strip().lower()
                try:
                    room.mode = GameMode(mode_value)
                except ValueError:
                    room.mode = DEFAULT_GAME_MODE
                room.time_limit_ms = time_limit_for_mode(room.mode)

                # ── Topic resolution ───────────────────────────────────────────
                if room.play_mode == PlayMode.TEAM:
                    # Pick randomly from whichever team topics have been submitted
                    candidates = [t for t in room.team_topics.values() if t]
                    if not candidates:
                        # Fallback: use a generic topic if no one submitted
                        topic = "General Knowledge"
                        chosen_team_id = None
                    else:
                        topic = random.choice(candidates)
                        # Figure out which team "won" the randomiser
                        chosen_team_id = next(
                            (tid for tid, t in room.team_topics.items() if t == topic),
                            None,
                        )
                    room.topic = topic
                else:
                    topic = str(msg.get("topic", "General Knowledge")).strip() or "General Knowledge"
                    room.topic = topic
                    chosen_team_id = None

                room.status = GameStatus.STARTING

                starting_data: dict[str, Any] = {
                    "topic": topic,
                    "mode": room.mode.value,
                    "play_mode": room.play_mode.value,
                    "time_limit_ms": room.time_limit_ms,
                    "total_questions": 10,
                }
                if room.play_mode == PlayMode.TEAM:
                    starting_data["chosen_team_id"] = chosen_team_id
                    starting_data["team_names"] = dict(room.team_names)
                    starting_data["team_topics"] = dict(room.team_topics)
                    starting_data["teams"] = dict(room.teams)

                await broadcast(room_code, {"type": "GAME_STARTING", "data": starting_data})

                try:
                    room.questions = await asyncio.wait_for(
                        generate_questions(topic), timeout=GENERATION_TIMEOUT_SECONDS
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "Question generation timed out for room '%s'; using fallback",
                        room_code,
                    )
                    room.questions = [Question(**q) for q in FALLBACK_QUESTIONS]
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
                    participant.streak = 0
                room.status = GameStatus.ACTIVE
                room.current_q_index = 0
                await broadcast_question(room_code)

            # ── answer ────────────────────────────────────────────────────────
            elif action == "answer":
                if room.status != GameStatus.ACTIVE or room.phase != RoundPhase.QUESTION:
                    continue
                if player_name in room.answers_this_round:
                    continue

                choice = msg.get("choice")
                if not isinstance(choice, int) or choice not in range(4):
                    await send_to(
                        websocket,
                        {"type": "ERROR", "data": {"message": "Invalid answer choice"}},
                    )
                    continue
                try:
                    time_ms = int(msg.get("time_ms", room.time_limit_ms))
                except (TypeError, ValueError):
                    time_ms = room.time_limit_ms

                question = room.questions[room.current_q_index]
                is_correct = choice == question.correct_index
                player = room.players[player_name]

                if is_correct:
                    player.streak += 1
                    points = calculate_score(time_ms, room.time_limit_ms, player.streak)
                    player.correct_answers += 1
                else:
                    player.streak = 0
                    points = 0

                player.score += points
                player.answered = True
                player.last_answer = choice
                room.answers_this_round[player_name] = choice
                room.points_gained[player_name] = points

                connected_players = [
                    p for p in room.players.values() if p.websocket is not None
                ]
                if len(room.answers_this_round) >= len(connected_players):
                    await resolve_round(room_code, room.current_q_index)

            else:
                await send_to(
                    websocket,
                    {"type": "ERROR", "data": {"message": f"Unknown action: '{action}'"}},
                )

    except WebSocketDisconnect:
        player = room.players.get(player_name)
        if player:
            player.websocket = None

        logger.info("Player '%s' disconnected from room '%s'", player_name, room_code)

        any_connected = any(p.websocket is not None for p in room.players.values())

        if any_connected:
            dc_data: dict[str, Any] = {"players": list(room.players.keys())}
            if room.play_mode == PlayMode.TEAM:
                dc_data["teams"] = dict(room.teams)
                dc_data["team_names"] = dict(room.team_names)
                dc_data["team_topics"] = dict(room.team_topics)
            await broadcast(room_code, {"type": "PLAYER_JOINED", "data": dc_data})

            connected_players = [p for p in room.players.values() if p.websocket is not None]
            if (
                room.status == GameStatus.ACTIVE
                and room.phase == RoundPhase.QUESTION
                and len(room.answers_this_round) >= len(connected_players)
            ):
                asyncio.create_task(resolve_round(room_code, room.current_q_index))
        else:
            asyncio.create_task(_delayed_room_cleanup(room_code))
