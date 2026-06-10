"""
WebSocket endpoint and authoritative real-time game loop.

Streak/combo multiplier (Milestone 19):
  base = 500–1000 pts based on speed
  multiplier = min(1.0 + (streak // 3) * 0.5, 3.0)
  streak 0-2 → ×1.0 | 3-5 → ×1.5 | 6-8 → ×2.0 | 9-11 → ×2.5 | 12+ → ×3.0

Team mode (Milestone 20):
  Rooms are always created as 'classic' (so anyone can join via code).
  Inside the lobby, the host can toggle to 'team' mode. The set_lobby_mode
  action updates room.play_mode and broadcasts the change to all guests.
  Players self-assign via join_team. Topics are set per team via set_team_info.
  start_game accepts play_mode from the message to allow this override.

Security hardening (Milestone 29):
  - All WS inputs go through app.core.sanitize before use
  - action field validated against an explicit allowlist
  - topic validated for prompt-injection patterns
  - X-Forwarded-For uses last-IP (Cloud Run's insertion), not first
  - time_ms clamped to [0, time_limit_ms + 500ms grace]
"""

import asyncio
import json
import logging
import random
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.state import rooms
from app.core.limiter import is_rate_limited, extract_real_ip_from_ws
from app.core.sanitize import (
    validate_action,
    validate_topic,
    validate_choice,
    validate_time_ms,
    validate_team_id,
    validate_play_mode,
    validate_game_mode,
    sanitize_string,
    MAX_TOPIC_LEN,
    MAX_TEAM_NAME,
)
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
from app.services.ai import generate_questions, FALLBACK_QUESTIONS
from app.services.profiles import (
    ROOM_ENTRY_FEE,
    apply_delta,
    apply_batch_deltas,
    can_afford_entry,
    solo_rewards,
)

logger = logging.getLogger(__name__)
router = APIRouter()

BASE_POINTS                      = 1000
ANSWER_REVEAL_SECONDS            = 4
INTERMISSION_LEADERBOARD_SECONDS = 5
GENERATION_TIMEOUT_SECONDS       = 30

_round_timeout_tasks: dict[str, asyncio.Task] = {}


# ── Broadcast helpers ─────────────────────────────────────────────────────────

async def broadcast(room_code: str, message: dict[str, Any]) -> None:
    """Send a JSON message to every connected player in a room in parallel."""
    room = rooms.get(room_code)
    if not room:
        return

    encoded_message = json.dumps(message)
    tasks = []
    player_names = []

    for name, player in list(room.players.items()):
        if player.websocket is not None:
            tasks.append(player.websocket.send_text(encoded_message))
            player_names.append(name)

    if not tasks:
        return

    results = await asyncio.gather(*tasks, return_exceptions=True)

    dead: list[str] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            name = player_names[i]
            dead.append(name)
            logger.warning(
                "Failed to send message to '%s' in room '%s': %s", name, room_code, result
            )

    for name in dead:
        player = room.players.get(name)
        if player:
            player.websocket = None
        logger.warning(
            "Marked player '%s' as disconnected in room '%s' due to send failure",
            name,
            room_code,
        )


async def send_to(websocket: WebSocket, message: dict[str, Any]) -> None:
    """Send one JSON message to one WebSocket connection."""
    await websocket.send_text(json.dumps(message))


async def _delayed_room_cleanup(room_code: str, delay: int = 60) -> None:
    """Delete a room if it stays empty after a grace period."""
    await asyncio.sleep(delay)
    room = rooms.get(room_code)
    if not room:
        return
    if not any(p.websocket is not None for p in room.players.values()):
        _cancel_round_timeout(room_code)
        rooms.pop(room_code, None)
        logger.info("Room '%s' deleted after grace period", room_code)


def _cancel_round_timeout(room_code: str) -> None:
    task = _round_timeout_tasks.pop(room_code, None)
    if task and task is not asyncio.current_task():
        task.cancel()


# ── Scoring ───────────────────────────────────────────────────────────────────

def calculate_score(time_ms: int, time_limit_ms: int, streak: int) -> int:
    """
    Base score 500–1000 (speed-based) × streak multiplier.

    Multiplier thresholds (streak // 3):
      0 (0-2)  → ×1.0
      1 (3-5)  → ×1.5
      2 (6-8)  → ×2.0
      3 (9-11) → ×2.5
      4+ (12+) → ×3.0
    """
    clamped = max(0, min(time_ms, time_limit_ms))
    base = int(BASE_POINTS * (1 - (clamped / time_limit_ms) * 0.5))
    base = max(500, min(1000, base))
    multiplier = min(1.0 + (streak // 3) * 0.5, 3.0)
    return int(base * multiplier)


# ── Team helpers ──────────────────────────────────────────────────────────────

def _team_scores(room) -> dict[str, int]:
    """Aggregate individual player scores into per-team totals."""
    totals: dict[str, int] = {tid: 0 for tid in room.team_names}
    for pname, player in room.players.items():
        tid = room.teams.get(pname)
        if tid in totals:
            totals[tid] += player.score
    return totals


def _round_payload(room) -> dict[str, Any]:
    """Common answer/score payload for ANSWER_REVEAL and INTERMISSION_LEADERBOARD."""
    question = room.questions[room.current_q_index]
    payload: dict[str, Any] = {
        "scores":        {n: p.score for n, p in room.players.items()},
        "points_gained": dict(room.points_gained),
        "answers":       dict(room.answers_this_round),
        "correct_index": question.correct_index,
        "play_mode":     room.play_mode.value,
        "streaks":       {n: p.streak for n, p in room.players.items()},
    }
    if room.play_mode == PlayMode.TEAM:
        payload["team_scores"] = _team_scores(room)
        payload["teams"]       = dict(room.teams)
        payload["team_names"]  = dict(room.team_names)
    return payload


def _connected_players(room) -> list[Player]:
    """Return players who are currently attached to an open WebSocket."""
    return [p for p in room.players.values() if p.websocket is not None]


def _missing_profile_names(room) -> list[str]:
    """Return connected players without a Google profile ID."""
    return [p.name for p in _connected_players(room) if not p.user_id]


def _insufficient_coin_names(room) -> list[str]:
    """Return connected players who cannot pay the room entry fee."""
    names: list[str] = []
    for player in _connected_players(room):
        if player.user_id and not can_afford_entry(player.user_id):
            names.append(player.name)
    return names


def _charge_room_entry_fees(room) -> None:
    """Deduct the multiplayer entry fee once at session start."""
    room.entry_fees = {}
    for player in _connected_players(room):
        if not player.user_id:
            continue
        apply_delta(player.user_id, coins_delta=-ROOM_ENTRY_FEE)
        room.entry_fees[player.name] = float(ROOM_ENTRY_FEE)


def _refund_room_entry_fees(room) -> None:
    """Refund all charged entry fees if quiz startup fails."""
    for name, fee in room.entry_fees.items():
        player = room.players.get(name)
        if player and player.user_id:
            apply_delta(player.user_id, coins_delta=fee)
    room.entry_fees = {}


def _finalize_economy(
    room, final_scores: dict[str, int], correct_answers: dict[str, int]
) -> dict[str, Any]:
    """Apply end-of-game economy rules and return per-player UI payloads."""
    if room.economy_finalized:
        return {}

    economy: dict[str, Any] = {}
    deltas_to_apply = {}

    if room.play_mode == PlayMode.SOLO:
        for name, player in room.players.items():
            if not player.user_id:
                continue
            correct = int(correct_answers.get(name, 0))
            coins_delta, trophies_delta = solo_rewards(correct)
            deltas_to_apply[player.user_id] = {
                "coins_delta":    coins_delta,
                "trophies_delta": trophies_delta,
                "player_name":    name,
            }
    elif room.play_mode in (PlayMode.CLASSIC, PlayMode.TEAM):
        pool = float(sum(room.entry_fees.values()))
        paid_scores = {
            name: final_scores.get(name, 0)
            for name in room.entry_fees
            if name in final_scores
        }
        if paid_scores and pool > 0:
            top_score = max(paid_scores.values())
            winners   = [n for n, s in paid_scores.items() if s == top_score]
            payout    = pool / len(winners) if winners else 0
            for name in winners:
                player = room.players.get(name)
                if not player or not player.user_id:
                    continue
                entry_fee = room.entry_fees.get(name, 0)
                deltas_to_apply[player.user_id] = {
                    "coins_delta":    payout,
                    "trophies_delta": 0,
                    "player_name":    name,
                    "is_winner":      True,
                    "payout":         payout,
                    "entry_fee":      entry_fee,
                }
            for name, fee in room.entry_fees.items():
                player = room.players.get(name)
                if not player or not player.user_id or player.user_id in deltas_to_apply:
                    continue
                deltas_to_apply[player.user_id] = {
                    "coins_delta":    0,
                    "trophies_delta": 0,
                    "player_name":    name,
                    "is_winner":      False,
                    "entry_fee":      fee,
                }

    if deltas_to_apply:
        from app.services.profiles import get_profile
        profiles_before  = {uid: get_profile(uid) for uid in deltas_to_apply}
        updated_profiles = apply_batch_deltas(deltas_to_apply)

        for user_id, profile_after in updated_profiles.items():
            info           = deltas_to_apply[user_id]
            name           = info["player_name"]
            profile_before = profiles_before[user_id]
            if room.play_mode == PlayMode.SOLO:
                economy[name] = {
                    "coins_delta":    info["coins_delta"],
                    "trophies_delta": profile_after["trophies"] - profile_before["trophies"],
                    "coins":          profile_after["coins"],
                    "trophies":       profile_after["trophies"],
                }
            else:
                if info.get("is_winner"):
                    economy[name] = {
                        "coins_delta":    info["payout"] - info["entry_fee"],
                        "trophies_delta": 0,
                        "coins":          profile_after["coins"],
                        "trophies":       profile_after["trophies"],
                        "entry_fee":      info["entry_fee"],
                        "payout":         info["payout"],
                    }
                else:
                    economy[name] = {
                        "coins_delta":    -info["entry_fee"],
                        "trophies_delta": 0,
                        "coins":          profile_after["coins"],
                        "trophies":       profile_after["trophies"],
                        "entry_fee":      info["entry_fee"],
                    }

    room.economy_finalized = True
    return economy


# ── Round lifecycle ───────────────────────────────────────────────────────────

async def _expire_question(room_code: str, question_index: int) -> None:
    """Resolve a round when the timer runs out server-side."""
    try:
        room = rooms.get(room_code)
        if not room:
            return
        await asyncio.sleep((room.time_limit_ms / 1000) + 3)
        await resolve_round(room_code, question_index)
    except asyncio.CancelledError:
        return


async def broadcast_question(room_code: str) -> None:
    """Broadcast the current question and arm the server-side timeout."""
    room     = rooms[room_code]
    question = room.questions[room.current_q_index]
    room.phase = RoundPhase.QUESTION
    room.answers_this_round = {}
    room.points_gained = {name: 0 for name in room.players}
    for player in room.players.values():
        player.answered    = False
        player.last_answer = None

    msg_data: dict[str, Any] = {
        "index":         room.current_q_index,
        "text":          question.question,
        "options":       question.options,
        "mode":          room.mode.value,
        "play_mode":     room.play_mode.value,
        "phase":         room.phase.value,
        "time_limit_ms": room.time_limit_ms,
    }
    if room.play_mode == PlayMode.TEAM:
        msg_data["team_scores"] = _team_scores(room)
        msg_data["teams"]       = dict(room.teams)
        msg_data["team_names"]  = dict(room.team_names)

    await broadcast(room_code, {"type": "QUESTION", "data": msg_data})
    _cancel_round_timeout(room_code)
    _round_timeout_tasks[room_code] = asyncio.create_task(
        _expire_question(room_code, room.current_q_index)
    )


async def resolve_round(room_code: str, question_index: int) -> None:
    """Lock the round and drive the reveal → intermission → next-question sequence."""
    room = rooms.get(room_code)
    if (
        not room
        or room.status != GameStatus.ACTIVE
        or room.phase  != RoundPhase.QUESTION
        or room.current_q_index != question_index
    ):
        return

    _cancel_round_timeout(room_code)

    for name, player in room.players.items():
        if name not in room.answers_this_round:
            player.streak = 0

    room.phase   = RoundPhase.ANSWER_REVEAL
    reveal_data  = _round_payload(room)
    reveal_data.update({"phase": room.phase.value, "hold_ms": ANSWER_REVEAL_SECONDS * 1000})
    await broadcast(room_code, {"type": "ANSWER_REVEAL", "data": reveal_data})
    await asyncio.sleep(ANSWER_REVEAL_SECONDS)

    room = rooms.get(room_code)
    if not room or room.status != GameStatus.ACTIVE:
        return

    if room.play_mode in (PlayMode.CLASSIC, PlayMode.TEAM):
        room.phase = RoundPhase.INTERMISSION_LEADERBOARD
        is_final   = room.current_q_index + 1 >= len(room.questions)
        hold_secs  = 2 if is_final else INTERMISSION_LEADERBOARD_SECONDS
        inter_data = _round_payload(room)
        inter_data.update({
            "phase":    room.phase.value,
            "hold_ms":  hold_secs * 1000,
            "is_final": is_final,
        })
        await broadcast(room_code, {"type": "INTERMISSION_LEADERBOARD", "data": inter_data})
        await asyncio.sleep(hold_secs)

    room = rooms.get(room_code)
    if not room or room.status != GameStatus.ACTIVE:
        return

    if room.current_q_index + 1 >= len(room.questions):
        await _finish_game(room_code)
        return

    room.current_q_index += 1
    await broadcast_question(room_code)


async def _finish_game(room_code: str) -> None:
    """Broadcast final results once all questions are done."""
    room = rooms.get(room_code)
    if not room:
        return
    room.status = GameStatus.FINISHED
    room.phase  = RoundPhase.COMPLETE
    total           = len(room.questions)
    final_scores    = {n: p.score           for n, p in room.players.items()}
    correct_answers = {n: p.correct_answers for n, p in room.players.items()}
    accuracy_pct    = {
        n: round((c / total) * 100) if total else 0
        for n, c in correct_answers.items()
    }
    economy   = _finalize_economy(room, final_scores, correct_answers)
    game_over: dict[str, Any] = {
        "final_scores":         final_scores,
        "correct_answers":      correct_answers,
        "accuracy_percentages": accuracy_pct,
        "total_questions":      total,
        "play_mode":            room.play_mode.value,
        "economy":              economy,
    }
    if room.play_mode == PlayMode.TEAM:
        game_over["team_scores"] = _team_scores(room)
        game_over["teams"]       = dict(room.teams)
        game_over["team_names"]  = dict(room.team_names)
    await broadcast(room_code, {"type": "GAME_OVER", "data": game_over})
    logger.info("Game over in room '%s'. Scores: %s", room_code, final_scores)


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@router.websocket("/ws/{room_code}/{player_name}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_code: str,
    player_name: str,
    user_id: str | None = None,
) -> None:
    """Accept a player and process room actions until the socket disconnects."""

    await websocket.accept()

    # ── Rate-limit new WS connections ─────────────────────────────────────────
    ip = extract_real_ip_from_ws(websocket)
    if is_rate_limited(ip, action="ws_join"):
        await send_to(websocket, {
            "type": "ERROR",
            "data": {"message": "Too many connection attempts. Please wait a moment."},
        })
        await websocket.close()
        return

    room = rooms.get(room_code)
    if not room:
        await send_to(websocket, {"type": "ERROR", "data": {"message": "Room not found"}})
        await websocket.close()
        return

    # Sanitize the player name from the URL path
    clean_name = sanitize_string(player_name, 20)
    if not clean_name:
        await send_to(websocket, {"type": "ERROR", "data": {"message": "Invalid player name."}})
        await websocket.close()
        return
    player_name = clean_name

    # Re-join support: player reconnects after disconnect
    existing = room.players.get(player_name)
    if existing:
        if existing.websocket is not None:
            await send_to(websocket, {
                "type": "ERROR",
                "data": {"message": "Name already taken in this room"},
            })
            await websocket.close()
            return
        existing.websocket = websocket
        if user_id:
            existing.user_id = user_id
        logger.info("Player '%s' re-joined room '%s'", player_name, room_code)
    else:
        if room.status != GameStatus.WAITING:
            await send_to(websocket, {
                "type": "ERROR",
                "data": {"message": "Game already in progress"},
            })
            await websocket.close()
            return
        if room.locked:
            await send_to(websocket, {
                "type": "ERROR",
                "data": {"message": "Room is locked by host"},
            })
            await websocket.close()
            return
        if room.play_mode == PlayMode.SOLO and player_name != room.host:
            await send_to(websocket, {
                "type": "ERROR",
                "data": {"message": "Solo rooms are private"},
            })
            await websocket.close()
            return
        room.players[player_name] = Player(
            name=player_name, user_id=user_id, websocket=websocket
        )
        logger.info("Player '%s' joined room '%s'", player_name, room_code)

    joined_data: dict[str, Any] = {
        "players":    list(room.players.keys()),
        "lobby_mode": room.play_mode.value,
        "locked":     room.locked,
    }
    if room.play_mode == PlayMode.TEAM:
        joined_data["teams"]       = dict(room.teams)
        joined_data["team_names"]  = dict(room.team_names)
        joined_data["team_topics"] = dict(room.team_topics)
    await broadcast(room_code, {"type": "PLAYER_JOINED", "data": joined_data})

    try:
        while True:
            raw = await websocket.receive_text()

            # ── Parse JSON ────────────────────────────────────────────────────
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await send_to(websocket, {"type": "ERROR", "data": {"message": "Invalid JSON"}})
                continue

            if not isinstance(msg, dict):
                await send_to(websocket, {"type": "ERROR", "data": {"message": "Message must be a JSON object"}})
                continue

            # ── Validate action against allowlist ─────────────────────────────
            action = validate_action(msg.get("action"))
            if action is None:
                raw_action = msg.get("action")
                # Only log if it looks like a real unknown action (not noise)
                if isinstance(raw_action, str):
                    logger.warning(
                        "Unknown/invalid action '%s' from '%s' in room '%s'",
                        raw_action[:64], player_name, room_code,
                    )
                await send_to(websocket, {
                    "type": "ERROR",
                    "data": {"message": "Unknown or invalid action."},
                })
                continue

            # ═════════════════════════════════════════════════════════════════
            # ACTION HANDLERS
            # ═════════════════════════════════════════════════════════════════

            # ── lock_room ─────────────────────────────────────────────────────
            if action == "lock_room":
                if player_name != room.host:
                    continue
                room.locked = True
                await broadcast(room_code, {
                    "type": "PLAYER_JOINED",
                    "data": {
                        "players":     list(room.players.keys()),
                        "lobby_mode":  room.play_mode.value,
                        "locked":      True,
                        "teams":       dict(room.teams),
                        "team_names":  dict(room.team_names),
                        "team_topics": dict(room.team_topics),
                    },
                })

            # ── unlock_room ───────────────────────────────────────────────────
            elif action == "unlock_room":
                if player_name != room.host:
                    continue
                room.locked    = False
                room.play_mode = PlayMode.CLASSIC
                await broadcast(room_code, {
                    "type": "LOBBY_MODE_CHANGED",
                    "data": {
                        "mode":       room.play_mode.value,
                        "locked":     False,
                        "team_names": dict(room.team_names),
                        "teams":      dict(room.teams),
                    },
                })
                await broadcast(room_code, {
                    "type": "PLAYER_JOINED",
                    "data": {
                        "players":     list(room.players.keys()),
                        "lobby_mode":  room.play_mode.value,
                        "locked":      False,
                        "teams":       dict(room.teams),
                        "team_names":  dict(room.team_names),
                        "team_topics": dict(room.team_topics),
                    },
                })

            # ── set_lobby_mode ────────────────────────────────────────────────
            elif action == "set_lobby_mode":
                if player_name != room.host:
                    continue
                if room.status != GameStatus.WAITING:
                    continue
                requested = validate_play_mode(msg.get("mode"), allowed=("classic", "team"))
                if requested is None:
                    await send_to(websocket, {
                        "type": "ERROR",
                        "data": {"message": "Invalid mode. Must be 'classic' or 'team'."},
                    })
                    continue
                if requested == "team" and not room.locked:
                    await send_to(websocket, {
                        "type": "ERROR",
                        "data": {"message": "Lock room first to enable Team Mode"},
                    })
                    continue
                room.play_mode = PlayMode(requested)
                name_a = sanitize_string(msg.get("name_a", room.team_names.get("A", "Team A")), MAX_TEAM_NAME) or "Team A"
                name_b = sanitize_string(msg.get("name_b", room.team_names.get("B", "Team B")), MAX_TEAM_NAME) or "Team B"
                room.team_names = {"A": name_a, "B": name_b}
                await broadcast(room_code, {
                    "type": "LOBBY_MODE_CHANGED",
                    "data": {
                        "mode":       room.play_mode.value,
                        "locked":     room.locked,
                        "team_names": dict(room.team_names),
                        "teams":      dict(room.teams),
                    },
                })
                await broadcast(room_code, {
                    "type": "PLAYER_JOINED",
                    "data": {
                        "players":     list(room.players.keys()),
                        "lobby_mode":  room.play_mode.value,
                        "locked":      room.locked,
                        "teams":       dict(room.teams),
                        "team_names":  dict(room.team_names),
                        "team_topics": dict(room.team_topics),
                    },
                })

            # ── join_team ─────────────────────────────────────────────────────
            elif action == "join_team":
                if room.play_mode != PlayMode.TEAM:
                    continue
                team_id = validate_team_id(msg.get("team_id"))
                if team_id is None:
                    await send_to(websocket, {
                        "type": "ERROR",
                        "data": {"message": "Team must be A or B"},
                    })
                    continue
                room.teams[player_name] = team_id
                await broadcast(room_code, {
                    "type": "PLAYER_JOINED",
                    "data": {
                        "players":     list(room.players.keys()),
                        "lobby_mode":  room.play_mode.value,
                        "teams":       dict(room.teams),
                        "team_names":  dict(room.team_names),
                        "team_topics": dict(room.team_topics),
                    },
                })

            # ── set_team_info ─────────────────────────────────────────────────
            elif action == "set_team_info":
                if room.play_mode != PlayMode.TEAM:
                    continue
                name_a  = sanitize_string(msg.get("name_a",  room.team_names.get("A", "Team A")), MAX_TEAM_NAME) or "Team A"
                name_b  = sanitize_string(msg.get("name_b",  room.team_names.get("B", "Team B")), MAX_TEAM_NAME) or "Team B"
                # Validate topics through the injection filter
                raw_topic_a = msg.get("topic_a", "")
                raw_topic_b = msg.get("topic_b", "")
                topic_a, _ = validate_topic(raw_topic_a) if raw_topic_a else ("", None)
                topic_b, _ = validate_topic(raw_topic_b) if raw_topic_b else ("", None)
                room.team_names = {"A": name_a, "B": name_b}
                if topic_a:
                    room.team_topics["A"] = topic_a
                if topic_b:
                    room.team_topics["B"] = topic_b
                await broadcast(room_code, {
                    "type": "PLAYER_JOINED",
                    "data": {
                        "players":     list(room.players.keys()),
                        "lobby_mode":  room.play_mode.value,
                        "teams":       dict(room.teams),
                        "team_names":  dict(room.team_names),
                        "team_topics": dict(room.team_topics),
                    },
                })

            # ── start_game ────────────────────────────────────────────────────
            elif action == "start_game":
                if player_name != room.host:
                    await send_to(websocket, {
                        "type": "ERROR",
                        "data": {"message": "Only the host can start the game"},
                    })
                    continue
                if room.status != GameStatus.WAITING:
                    await send_to(websocket, {
                        "type": "ERROR",
                        "data": {"message": "Game already started"},
                    })
                    continue

                # Rate-limit quiz generation (uses last-IP)
                if is_rate_limited(ip, action="quiz"):
                    await send_to(websocket, {
                        "type": "ERROR",
                        "data": {"message": "Quiz generation limit reached. Wait a minute!"},
                    })
                    continue

                # Resolve play mode
                if room.play_mode != PlayMode.SOLO:
                    raw_pm = validate_play_mode(msg.get("play_mode"), allowed=("classic", "team"))
                    if raw_pm:
                        try:
                            room.play_mode = PlayMode(raw_pm)
                        except ValueError:
                            room.play_mode = PlayMode.CLASSIC

                if room.play_mode in (PlayMode.CLASSIC, PlayMode.TEAM):
                    missing_profiles = _missing_profile_names(room)
                    if missing_profiles:
                        await send_to(websocket, {
                            "type": "ERROR",
                            "data": {"message": "All players must sign in with Google before room games."},
                        })
                        continue
                    broke_players = _insufficient_coin_names(room)
                    if broke_players:
                        await send_to(websocket, {
                            "type": "ERROR",
                            "data": {"message": f"Not enough coins: {', '.join(broke_players)}"},
                        })
                        continue
                    _charge_room_entry_fees(room)

                # Validate difficulty
                raw_mode = validate_game_mode(msg.get("mode"))
                if raw_mode:
                    try:
                        room.mode = GameMode(raw_mode)
                    except ValueError:
                        room.mode = DEFAULT_GAME_MODE
                else:
                    room.mode = DEFAULT_GAME_MODE
                room.time_limit_ms = time_limit_for_mode(room.mode)
                room.status        = GameStatus.STARTING

                # ── Topic resolution ──────────────────────────────────────────
                if room.play_mode == PlayMode.TEAM:
                    candidates = [t for t in room.team_topics.values() if t.strip()]
                    if not candidates:
                        topic          = "General Knowledge"
                        chosen_team_id: str | None = None
                    else:
                        topic          = random.choice(candidates)
                        chosen_team_id = next(
                            (tid for tid, t in room.team_topics.items() if t == topic), None
                        )
                    room.topic = topic
                else:
                    raw_topic = msg.get("topic", "General Knowledge")
                    topic, topic_err = validate_topic(raw_topic)
                    if topic_err:
                        # Refund any charged fees before bailing
                        if room.entry_fees:
                            _refund_room_entry_fees(room)
                        room.status = GameStatus.WAITING
                        await send_to(websocket, {
                            "type": "ERROR",
                            "data": {"message": topic_err},
                        })
                        continue
                    if not topic:
                        topic = "General Knowledge"
                    room.topic     = topic
                    chosen_team_id = None

                starting_data: dict[str, Any] = {
                    "topic":           topic,
                    "mode":            room.mode.value,
                    "play_mode":       room.play_mode.value,
                    "time_limit_ms":   room.time_limit_ms,
                    "total_questions": 10,
                }
                if room.play_mode == PlayMode.TEAM:
                    starting_data["chosen_team_id"] = chosen_team_id
                    starting_data["team_names"]     = dict(room.team_names)
                    starting_data["team_topics"]    = dict(room.team_topics)
                    starting_data["teams"]          = dict(room.teams)

                await broadcast(room_code, {"type": "GAME_STARTING", "data": starting_data})

                # ── Generate questions ────────────────────────────────────────
                try:
                    room.questions = await asyncio.wait_for(
                        generate_questions(topic),
                        timeout=GENERATION_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "Question generation timed out for room '%s'; using fallback", room_code
                    )
                    room.questions = [Question(**q) for q in FALLBACK_QUESTIONS]
                except Exception as exc:
                    logger.error(
                        "Question generation failed for room '%s': %s", room_code, exc
                    )
                    if room.entry_fees:
                        _refund_room_entry_fees(room)
                    room.status = GameStatus.WAITING
                    room.phase  = RoundPhase.LOBBY
                    await broadcast(room_code, {
                        "type": "ERROR",
                        "data": {"message": "Failed to generate questions. Try again."},
                    })
                    continue

                for p in room.players.values():
                    p.score = 0; p.correct_answers = 0; p.streak = 0
                room.status          = GameStatus.ACTIVE
                room.current_q_index = 0
                await broadcast_question(room_code)

            # ── answer ────────────────────────────────────────────────────────
            elif action == "answer":
                if room.status != GameStatus.ACTIVE or room.phase != RoundPhase.QUESTION:
                    continue
                if player_name in room.answers_this_round:
                    continue

                choice = validate_choice(msg.get("choice"))
                if choice is None:
                    await send_to(websocket, {
                        "type": "ERROR",
                        "data": {"message": "Invalid answer choice"},
                    })
                    continue

                time_ms  = validate_time_ms(msg.get("time_ms"), room.time_limit_ms)
                question = room.questions[room.current_q_index]
                is_correct = choice == question.correct_index
                player     = room.players[player_name]

                if is_correct:
                    player.streak += 1
                    points = calculate_score(time_ms, room.time_limit_ms, player.streak)
                    player.correct_answers += 1
                else:
                    player.streak = 0
                    points = 0

                player.score      += points
                player.answered    = True
                player.last_answer = choice
                room.answers_this_round[player_name] = choice
                room.points_gained[player_name]      = points

                connected = _connected_players(room)
                if len(room.answers_this_round) >= len(connected):
                    await resolve_round(room_code, room.current_q_index)

    except WebSocketDisconnect:
        player = room.players.get(player_name)
        if player:
            player.websocket = None
        logger.info("Player '%s' disconnected from room '%s'", player_name, room_code)

        any_connected = any(p.websocket is not None for p in room.players.values())
        if any_connected:
            dc_data: dict[str, Any] = {
                "players":    list(room.players.keys()),
                "lobby_mode": room.play_mode.value,
            }
            if room.play_mode == PlayMode.TEAM:
                dc_data["teams"]       = dict(room.teams)
                dc_data["team_names"]  = dict(room.team_names)
                dc_data["team_topics"] = dict(room.team_topics)
            await broadcast(room_code, {"type": "PLAYER_JOINED", "data": dc_data})

            connected = _connected_players(room)
            if (
                room.status == GameStatus.ACTIVE
                and room.phase == RoundPhase.QUESTION
                and len(room.answers_this_round) >= len(connected)
            ):
                asyncio.create_task(resolve_round(room_code, room.current_q_index))
        else:
            asyncio.create_task(_delayed_room_cleanup(room_code))