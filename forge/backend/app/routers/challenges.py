"""
REST endpoints for Async Challenge Mode (Online Duel — Phase 1).

WHY THIS DOES NOT LOOK UP app.core.state.rooms:
  An earlier version fetched the just-finished room from in-memory state
  by room_code. That breaks on Cloud Run whenever more than one instance
  is warm (--max-instances 3): the WebSocket that ran the game stays
  pinned to one instance, but the follow-up POST /challenges/create is a
  new HTTP request that the load balancer can route to ANY instance —
  including one that never held that room in memory, causing a false
  "session expired" 404 even seconds after the game ended.

  Instead, the client submits the frozen question set directly, sourced
  from the GAME_OVER WebSocket payload it already received (see
  websocket.py _finish_game). This makes challenge creation fully
  independent of which instance happens to serve the request.
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.limiter import is_rate_limited, extract_real_ip
from app.core.sanitize import sanitize_string, MAX_NAME_LEN, MAX_TOPIC_LEN
from app.models.quiz import GameMode, Question, time_limit_for_mode
from app.services.challenges import (
    complete_challenge,
    create_challenge,
    get_challenge,
)
from app.services.push import send_challenge_completed

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateChallengeRequest(BaseModel):
    creator_name: str
    creator_user_id: str | None = None
    topic: str
    mode: GameMode
    questions: list[Question]
    score: int
    correct_answers: int


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
    """Freeze a just-finished Solo game (from its own GAME_OVER payload) as a shareable challenge."""

    ip = extract_real_ip(request)
    if is_rate_limited(ip, action="room"):  # reuse the room-creation bucket — same abuse shape
        raise HTTPException(
            status_code=429,
            detail="Too many challenges created. Please wait a minute.",
        )

    if len(body.questions) != 10:
        raise HTTPException(status_code=400, detail="A challenge requires exactly 10 questions.")

    name  = sanitize_string(body.creator_name, MAX_NAME_LEN) or "Player"
    topic = sanitize_string(body.topic, MAX_TOPIC_LEN) or "General Knowledge"

    challenge = await create_challenge(
        creator_name=name,
        creator_user_id=body.creator_user_id,
        topic=topic,
        mode=body.mode.value,
        time_limit_ms=time_limit_for_mode(body.mode),
        questions=[q.model_dump() for q in body.questions],
        creator_score=body.score,
        creator_correct_answers=body.correct_answers,
    )

    return CreateChallengeResponse(code=challenge.code, expires_at=challenge.expires_at)


@router.get("/challenges/{code}")
async def get_challenge_endpoint(code: str):
    """Return challenge metadata + questions for the challenger to play."""

    challenge = await get_challenge(code)
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
        challenge = await complete_challenge(
            code=code,
            challenger_name=name,
            challenger_user_id=body.challenger_user_id,
            challenger_score=body.score,
            challenger_correct_answers=body.correct_answers,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if challenge.creator_user_id:
        try:
            await send_challenge_completed(
                creator_user_id=challenge.creator_user_id,
                challenger_name=challenge.challenger_name or "Someone",
                challenger_score=challenge.challenger_score or 0,
                creator_score=challenge.creator_score,
                topic=challenge.topic,
                challenge_code=challenge.code,
            )
        except Exception as e:
            logger.warning("Push notification failed (non-fatal): %s", e)

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