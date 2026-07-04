"""Thin REST endpoints for Forge room setup and health checks."""

import random
import string
import logging

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
from typing import Optional

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.core import state
from app.core.config import settings
from app.core.limiter import is_rate_limited, extract_real_ip
from app.models.quiz import DEFAULT_PLAY_MODE, GameStatus, PlayMode, Room

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request / response models ─────────────────────────────────────────────────

class CreateRoomRequest(BaseModel):
    host_name: str = "Host"
    play_mode: PlayMode = DEFAULT_PLAY_MODE
    user_id: str | None = None


class CreateRoomResponse(BaseModel):
    room_code: str
    host_name: str
    ws_url: str
    play_mode: PlayMode


class RewardRequest(BaseModel):
    user_id: str
    coins_delta: float = 20


class SyncRequest(BaseModel):
    user_id: str
    coins: float
    trophies: int


class BuyTicketsRequest(BaseModel):
    user_id: str
    num_tickets: int


class TicketUserRequest(BaseModel):
    user_id: str


class DailyRewardTicketRequest(BaseModel):
    user_id: str
    day: int


class SyncTicketsRequest(BaseModel):
    user_id: str
    tickets_today: int
    ad_tickets_used_today: int = 0
    last_ticket_date: str = ""

class DeleteAccountRequest(BaseModel):
    user_id: str

# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_room_code() -> str:
    """Generate a unique four-character alphanumeric room code."""
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        if code not in state.rooms:
            return code


def _verify_google_token(credential: str) -> str:
    """
    Verify a Google ID token and return the Google user ID (sub).

    Raises HTTPException 401 if the token is missing, expired, or tampered.
    This is used to prove that the caller owns the account they're modifying —
    preventing one user from manipulating another user's economy balance.
    """
    if not credential:
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        idinfo = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID if settings.GOOGLE_CLIENT_ID else None,
        )
        return idinfo["sub"]
    except ValueError as e:
        logger.warning("Invalid Google token on economy endpoint: %s", e)
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token.")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/health")
async def health_check():
    """Return a lightweight health response used for startup warming."""
    return {
        "status": "ok",
        "active_rooms": len(state.rooms),
    }


@router.post("/rooms/create", response_model=CreateRoomResponse)
async def create_room(body: CreateRoomRequest, request: Request):
    """Create a waiting solo or classic room in process memory."""
    ip = extract_real_ip(request)

    if is_rate_limited(ip, action="room"):
        logger.warning("Rate limit hit for IP %s (create_room)", ip)
        raise HTTPException(
            status_code=429,
            detail="Too many rooms created. Please wait a minute before starting another!",
        )

    code = _generate_room_code()
    room = Room(
        code=code,
        host=body.host_name,
        status=GameStatus.WAITING,
        play_mode=body.play_mode,
    )
    state.rooms[code] = room

    return CreateRoomResponse(
        room_code=code,
        host_name=body.host_name,
        ws_url=f"/ws/{code}/{body.host_name}",
        play_mode=body.play_mode,
    )


@router.get("/rooms/{code}")
async def get_room(code: str):
    """Return public room metadata for validation and debugging."""
    room = state.rooms.get(code.upper())
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    return {
        "code":             room.code,
        "host":             room.host,
        "status":           room.status,
        "play_mode":        room.play_mode,
        "phase":            room.phase,
        "players":          list(room.players.keys()),
        "locked":           room.locked,
        "teams":            dict(room.teams),
        "team_names":       dict(room.team_names),
        "team_topics":      dict(room.team_topics),
        "current_question": room.current_q_index,
    }


@router.delete("/rooms/{code}")
async def delete_room(code: str):
    """Manually remove a room for administration or local testing."""
    code = code.upper()
    if code not in state.rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    del state.rooms[code]
    return {"deleted": code}


@router.get("/tickets/{user_id}")
async def get_tickets(user_id: str):
    """Return the user's current generation ticket state."""
    from app.services.tickets import get_or_reset_tickets

    return get_or_reset_tickets(user_id)


@router.post("/tickets/buy")
async def buy_tickets(
    body: BuyTicketsRequest,
    authorization: Optional[str] = Header(default=None),
):
    """Buy generation tickets with coins after verifying account ownership."""
    credential = ""
    if authorization and authorization.startswith("Bearer "):
        credential = authorization[len("Bearer "):]

    verified_uid = _verify_google_token(credential)
    if verified_uid != body.user_id:
        raise HTTPException(
            status_code=403,
            detail="Token does not match the requested user account.",
        )

    try:
        from app.services.tickets import buy_tickets_with_coins
        return buy_tickets_with_coins(body.user_id, body.num_tickets)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Ticket purchase failed: %s", e)
        raise HTTPException(status_code=500, detail="Ticket purchase failed")


@router.post("/tickets/ad-grant")
async def grant_ticket_for_ad(
    body: TicketUserRequest,
    authorization: Optional[str] = Header(default=None),
):
    """Grant one generation ticket after a rewarded ad completes."""
    credential = ""
    if authorization and authorization.startswith("Bearer "):
        credential = authorization[len("Bearer "):]

    verified_uid = _verify_google_token(credential)
    if verified_uid != body.user_id:
        raise HTTPException(
            status_code=403,
            detail="Token does not match the requested user account.",
        )

    try:
        from app.services.tickets import grant_ad_ticket
        result = grant_ad_ticket(body.user_id)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail="Daily ad ticket cap reached.")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ad ticket grant failed: %s", e)
        raise HTTPException(status_code=500, detail="Ad ticket grant failed")


@router.post("/tickets/daily-reward-grant")
async def grant_daily_reward_tickets_endpoint(
    body: DailyRewardTicketRequest,
    authorization: Optional[str] = Header(default=None),
):
    """Grant the ticket part of a claimed daily reward after ownership check."""
    credential = ""
    if authorization and authorization.startswith("Bearer "):
        credential = authorization[len("Bearer "):]

    verified_uid = _verify_google_token(credential)
    if verified_uid != body.user_id:
        raise HTTPException(
            status_code=403,
            detail="Token does not match the requested user account.",
        )

    try:
        from app.services.tickets import grant_daily_reward_tickets
        return grant_daily_reward_tickets(body.user_id, body.day)
    except Exception as e:
        logger.error("Daily reward ticket grant failed: %s", e)
        raise HTTPException(status_code=500, detail="Daily reward ticket grant failed")


@router.post("/tickets/sync")
async def sync_tickets_endpoint(
    body: SyncTicketsRequest,
    authorization: Optional[str] = Header(default=None),
):
    """Hydrate backend ticket counters from the saved Supabase profile."""
    credential = ""
    if authorization and authorization.startswith("Bearer "):
        credential = authorization[len("Bearer "):]

    verified_uid = _verify_google_token(credential)
    if verified_uid != body.user_id:
        raise HTTPException(
            status_code=403,
            detail="Token does not match the requested user account.",
        )

    try:
        from app.services.tickets import sync_tickets
        return sync_tickets(
            body.user_id,
            body.tickets_today,
            body.ad_tickets_used_today,
            body.last_ticket_date,
        )
    except Exception as e:
        logger.error("Ticket sync failed: %s", e)
        raise HTTPException(status_code=500, detail="Ticket sync failed")


@router.post("/economy/reward")
async def ad_coin_reward(
    body: RewardRequest,
    authorization: Optional[str] = Header(default=None),
):
    """
    Apply a small coin reward (e.g. ad-watch bonus).

    Requires a valid Google ID token in the Authorization header so the
    caller can only reward their own account.

    Header format:  Authorization: Bearer <google_id_token>
    """
    credential = ""
    if authorization and authorization.startswith("Bearer "):
        credential = authorization[len("Bearer "):]

    verified_uid = _verify_google_token(credential)

    # Ensure the token belongs to the account being rewarded
    if verified_uid != body.user_id:
        raise HTTPException(
            status_code=403,
            detail="Token does not match the requested user account.",
        )

    try:
        from app.services.profiles import apply_delta
        profile = apply_delta(body.user_id, coins_delta=body.coins_delta)
        return {"coins": profile["coins"], "trophies": profile["trophies"]}
    except Exception as e:
        logger.error("Economy reward failed: %s", e)
        return {"ok": True}   # silent fail — frontend already applied locally


@router.post("/economy/sync")
async def sync_profile_endpoint(
    body: SyncRequest,
    authorization: Optional[str] = Header(default=None),
):
    """
    Force the backend profile store to match the client's Supabase state.

    SECURITY: Requires a valid Google ID token (Bearer scheme) that matches
    the user_id being synced. Without this check, any caller who knows a
    Google user ID (a 21-digit number that is not truly secret) could
    arbitrarily inflate another player's balance.

    Header format:  Authorization: Bearer <google_id_token>
    """
    credential = ""
    if authorization and authorization.startswith("Bearer "):
        credential = authorization[len("Bearer "):]

    verified_uid = _verify_google_token(credential)

    if verified_uid != body.user_id:
        raise HTTPException(
            status_code=403,
            detail="Token does not match the requested user account.",
        )

    # Clamp values to sane bounds — defence in depth even after auth
    coins    = max(0.0, min(float(body.coins),    1_000_000.0))
    trophies = max(0,   min(int(body.trophies),   100_000))

    try:
        from app.services.profiles import sync_profile
        profile = sync_profile(body.user_id, coins, trophies)
        return {"coins": profile["coins"], "trophies": profile["trophies"]}
    except Exception as e:
        logger.error("Economy sync failed: %s", e)
        raise HTTPException(status_code=500, detail="Sync failed")

@router.post("/account/delete")
async def delete_account(
    body: DeleteAccountRequest,
    authorization: Optional[str] = Header(default=None),
):
    """
    Permanently delete a user's backend profile: coins, trophies, and
    generation tickets. Requires a valid Google ID token proving ownership
    of the account being deleted — same check used by /economy/sync and
    the /tickets/* endpoints.

    This only removes the backend file-backed profile. The client is
    responsible for also removing the Supabase leaderboard mirror row,
    since writes to that table already happen client-side with the anon
    key (see supabase-client.js).
    """
    credential = ""
    if authorization and authorization.startswith("Bearer "):
        credential = authorization[len("Bearer "):]

    verified_uid = _verify_google_token(credential)
    if verified_uid != body.user_id:
        raise HTTPException(
            status_code=403,
            detail="Token does not match the requested user account.",
        )

    try:
        from app.services.profiles import delete_profile
        delete_profile(body.user_id)
        return {"deleted": True}
    except Exception as e:
        logger.error("Account deletion failed: %s", e)
        raise HTTPException(status_code=500, detail="Account deletion failed")