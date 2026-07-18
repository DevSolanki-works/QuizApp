"""
REST endpoints for Async Challenge Mode (Online Duel — Phase 1).

Deliberately plain REST, not WebSocket — this is turn-based (creator
plays, then later a challenger plays), not live, so it doesn't need any
of the room/game-loop machinery in websocket.py. No economy, no entry
fees, no ticket gating.

WHY room_code INSTEAD OF client-submitted questions:
  The frontend never retains the full 10-question array client-side —
  game.html only ever holds one question in memory at a time via WS
  messages. Pulling from app.core.state.rooms (the authoritative source,
  already populated at game start) avoids both that gap and the need to
  trust a client-submitted question list.

  This does mean a challenge can only be created within the room's
  cleanup grace window (60s after the last player disconnects — see
  _delayed_room_cleanup in websocket.py). Results screen closes the
  socket almost immediately, so this is a tight but workable window for
  v1; worth revisiting if players report missing the button in time.
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.limiter import is_rate_limited, extract_real_ip
from app.core.sanitize import sanitize_string, MAX_NAME_LEN
from app.models.quiz import PlayMode
from app.services.challenges import (
    complete_challenge,
    create_challenge,
    get_challenge,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateChallengeRequest(BaseModel):
    room_code: str
    creator_user_id: str | None = None


class CreateChallengeResponse(BaseModel):
    code: str
    expires_at: float


class CompleteChallengeRequest(BaseModel):
    challenger_name: str
    challenger_user_id: str | None = None
    score: int
    correct_answers: int


@router.post("/challenges/create", response_model=CreateChallengeResponse)
async def create_challenge_endpoint(body: CreateChallengeRequest, request: Request):
    """Freeze a just-finished Solo game (still in memory) as a shareable challenge."""

    ip = extract_real_ip(request)
    if is_rate_limited(ip, action="room"):  # reuse the room-creation bucket — same abuse shape
        raise HTTPException(
            status_code=429,
            detail="Too many challenges created. Please wait a minute.",
        )

    from app.core.state import rooms

    room = rooms.get(body.room_code.upper())
    if not room:
        raise HTTPException(
            status_code=404,
            detail="That game session has expired. Challenges must be created shortly after the game ends.",
        )
    if room.play_mode != PlayMode.SOLO:
        raise HTTPException(status_code=400, detail="Challenges can only be created from Solo games.")
    if not room.questions:
        raise HTTPException(status_code=400, detail="This room has no question set to challenge with.")

    creator_name = room.host
    player = room.players.get(creator_name)
    if not player:
        raise HTTPException(status_code=404, detail="Creator player not found in room.")

    challenge = create_challenge(
        creator_name=creator_name,
        creator_user_id=body.creator_user_id,
        topic=room.topic or "General Knowledge",
        mode=room.mode.value,
        time_limit_ms=room.time_limit_ms,
        questions=[q.model_dump() for q in room.questions],
        creator_score=player.score,
        creator_correct_answers=player.correct_answers,
    )

    return CreateChallengeResponse(code=challenge.code, expires_at=challenge.expires_at)


@router.get("/challenges/{code}")
async def get_challenge_endpoint(code: str):
    """Return challenge metadata + questions for the challenger to play."""

    challenge = get_challenge(code)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found or expired.")

    return {
        "code":                        challenge.code,
        "creator_name":                challenge.creator_name,
        "topic":                       challenge.topic,
        "mode":                        challenge.mode,
        "time_limit_ms":               challenge.time_limit_ms,
        "questions":                   [q.model_dump() for q in challenge.questions],
        "creator_score":               challenge.creator_score,
        "creator_correct_answers":     challenge.creator_correct_answers,
        "expires_at":                  challenge.expires_at,
        "is_completed":                challenge.is_completed,
        "challenger_name":             challenge.challenger_name,
        "challenger_score":            challenge.challenger_score,
        "challenger_correct_answers":  challenge.challenger_correct_answers,
    }


@router.post("/challenges/{code}/complete")
async def complete_challenge_endpoint(code: str, body: CompleteChallengeRequest):
    """Submit the challenger's result. One-shot per challenge."""

    name = sanitize_string(body.challenger_name, MAX_NAME_LEN) or "Player"

    try:
        challenge = complete_challenge(
            code=code,
            challenger_name=name,
            challenger_user_id=body.challenger_user_id,
            challenger_score=body.score,
            challenger_correct_answers=body.correct_answers,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "creator_name":     challenge.creator_name,
        "creator_score":    challenge.creator_score,
        "challenger_name":  challenge.challenger_name,
        "challenger_score": challenge.challenger_score,
        "winner": (
            "challenger" if challenge.challenger_score > challenge.creator_score
            else "creator" if challenge.challenger_score < challenge.creator_score
            else "tie"
        ),
    }