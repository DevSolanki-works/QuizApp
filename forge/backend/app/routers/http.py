"""Thin REST endpoints for Forge room setup and health checks."""

import random
import string
import logging

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
from typing import Optional

import jwt as pyjwt
from jwt import PyJWKClient

_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    """Lazily fetch + cache Supabase's public signing-key set."""
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json")
    return _jwks_client

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


class LuckySpinRequest(BaseModel):
    user_id: str
    is_respin: bool = False


class BuyPowerupRequest(BaseModel):
    user_id: str
    powerup_id: str

# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_room_code() -> str:
    """Generate a unique four-character alphanumeric room code."""
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        if code not in state.rooms:
            return code


def _verify_google_token(credential: str) -> str:
    """
    Verify a Supabase-issued access token and return the original Google
    user ID (sub) — NOT Supabase's own internal user UUID.

    WHY THIS SHAPE (July 2026 — replaces raw Google ID token verification):
      Native Google Sign-In ID tokens are short-lived (~1hr) with no
      reliable silent-refresh path on the installed Capacitor plugin
      version, which caused repeated forced-reauth interruptions in
      production. Supabase Auth's own session model (signInWithIdToken)
      solves this: supabase-js manages long-lived refresh entirely
      client-side, silently, forever — the backend just needs to verify
      whatever access token that session currently holds.

      Supabase's JWT `sub` claim is Supabase's OWN user UUID, not
      Google's — but the original Google sub survives, unchanged, inside
      user_metadata.sub (confirmed against a real decoded token). Every
      existing profiles.json / leaderboard.google_id / challenge record
      is keyed on the Google sub, so THIS function must keep returning
      that exact same value — not Supabase's UUID — to avoid treating
      every existing user as a brand-new account.

    Raises HTTPException 401 if the token is missing, expired, or tampered.
    """
    if not credential:
        raise HTTPException(status_code=401, detail="Authentication required.")

    try:
        # Supabase's actual token header (confirmed against a real decoded
        # token, July 2026) uses ES256 with a rotating asymmetric signing
        # key, identified by 'kid' — NOT the legacy HS256 shared secret
        # the dashboard's "JWT Secret" field suggests. Fetch the matching
        # public key from Supabase's JWKS endpoint (cached by PyJWKClient
        # after the first call) and verify against that.
        signing_key = _get_jwks_client().get_signing_key_from_jwt(credential)
        payload = pyjwt.decode(
            credential,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
        )
        user_metadata = payload.get("user_metadata", {}) or {}
        app_metadata = payload.get("app_metadata", {}) or {}
        provider = str(app_metadata.get("provider") or "").lower()

        raw_sub = user_metadata.get("sub") or user_metadata.get("provider_id")
        if not raw_sub:
            logger.warning("Supabase token verified but no provider sub found in user_metadata.")
            raise HTTPException(status_code=401, detail="Token missing account identity.")

        # Apple Sign-In accounts get a distinct, prefixed ID namespace so
        # they can never collide with an existing Google-sub-keyed profile
        # (Google subs are pure digits; this makes the two spaces provably
        # disjoint regardless). Every downstream store — profiles.json,
        # Supabase leaderboard.google_id, challenges, push_tokens — is
        # keyed on whatever string this function returns, so this is the
        # ONLY place that needs to know about the distinction. Deliberately
        # not merged with a same-email Google account — see resubmission
        # plan doc for why.
        if provider == "apple":
            return f"apple:{raw_sub}"
        return raw_sub
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token.")
    except pyjwt.InvalidTokenError as e:
        logger.warning("Invalid Supabase token on economy endpoint: %s", e)
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


@router.post("/tickets/bonus-generation-grant")
async def grant_bonus_generation_endpoint(
    body: TicketUserRequest,
    authorization: Optional[str] = Header(default=None),
):
    """Grant one bonus free generation from the Custom Topic Rewarded Interstitial."""
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
        from app.services.tickets import grant_bonus_generation
        return grant_bonus_generation(body.user_id)
    except Exception as e:
        logger.error("Bonus generation grant failed: %s", e)
        raise HTTPException(status_code=500, detail="Bonus generation grant failed")


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


@router.post("/lucky-draw/state")
async def lucky_draw_state(
    body: TicketUserRequest,
    authorization: Optional[str] = Header(default=None),
):
    """Return today's spin availability + wheel layout."""
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
        from app.services.lucky_draw import get_state
        return get_state(body.user_id)
    except Exception as e:
        logger.error("Lucky draw state failed: %s", e)
        raise HTTPException(status_code=500, detail="Lucky draw state failed")


@router.post("/lucky-draw/spin")
async def lucky_draw_spin(
    body: LuckySpinRequest,
    authorization: Optional[str] = Header(default=None),
):
    """Roll the daily lucky draw server-side and apply the prize."""
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
        from app.services.lucky_draw import LuckyDrawError, spin
        return spin(body.user_id, is_respin=bool(body.is_respin))
    except LuckyDrawError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Lucky draw spin failed: %s", e)
        raise HTTPException(status_code=500, detail="Lucky draw spin failed")


@router.post("/powerups/state")
async def powerups_state(
    body: TicketUserRequest,
    authorization: Optional[str] = Header(default=None),
):
    """Return the power-up catalog plus this user's owned counts."""
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
        from app.services.powerups import get_state
        return get_state(body.user_id)
    except Exception as e:
        logger.error("Power-up state failed: %s", e)
        raise HTTPException(status_code=500, detail="Power-up state failed")


@router.post("/powerups/buy")
async def powerups_buy(
    body: BuyPowerupRequest,
    authorization: Optional[str] = Header(default=None),
):
    """Buy one power-up with coins (server-authoritative balance check)."""
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
        from app.services.powerups import PowerupError, buy
        return buy(body.user_id, body.powerup_id)
    except PowerupError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Power-up purchase failed: %s", e)
        raise HTTPException(status_code=500, detail="Power-up purchase failed")


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


@router.post("/tutorial/claim-reward")
async def tutorial_claim_reward(
    body: DeleteAccountRequest,  # reuses the simple {user_id} shape
    authorization: Optional[str] = Header(default=None),
):
    """
    One-time tutorial completion reward, gated server-side per account
    (not per-device) so uninstall/reinstall cannot be used to farm this
    repeatedly with the same Google account.
    """
    credential = ""
    if authorization and authorization.startswith("Bearer "):
        credential = authorization[len("Bearer "):]

    verified_uid = _verify_google_token(credential)
    if verified_uid != body.user_id:
        raise HTTPException(status_code=403, detail="Token does not match the requested user account.")

    try:
        from app.services.profiles import get_profile, apply_delta

        profile = get_profile(body.user_id)
        if profile.get("tutorial_reward_claimed"):
            return {"ok": False, "already_claimed": True, "coins": profile["coins"], "trophies": profile["trophies"]}

        updated = apply_delta(body.user_id, coins_delta=20)
        from app.services.profiles import _load_profiles, _save_profiles, _lock
        with _lock:
            store = _load_profiles()
            store[body.user_id]["tutorial_reward_claimed"] = True
            _save_profiles(store)

        return {"ok": True, "already_claimed": False, "coins": updated["coins"], "trophies": updated["trophies"]}
    except Exception as e:
        logger.error("Tutorial reward claim failed: %s", e)
        raise HTTPException(status_code=500, detail="Reward claim failed")


@router.post("/tutorial/claim-reward")
async def tutorial_claim_reward(
    body: DeleteAccountRequest,  # reuses the simple {user_id} shape
    authorization: Optional[str] = Header(default=None),
):
    """
    One-time tutorial completion reward, gated server-side per account
    (not per-device) so uninstall/reinstall cannot be used to farm this
    repeatedly with the same Google account.
    """
    credential = ""
    if authorization and authorization.startswith("Bearer "):
        credential = authorization[len("Bearer "):]

    verified_uid = _verify_google_token(credential)
    if verified_uid != body.user_id:
        raise HTTPException(status_code=403, detail="Token does not match the requested user account.")

    try:
        from app.services.profiles import get_profile, apply_delta

        profile = get_profile(body.user_id)
        if profile.get("tutorial_reward_claimed"):
            return {"ok": False, "already_claimed": True, "coins": profile["coins"], "trophies": profile["trophies"]}

        updated = apply_delta(body.user_id, coins_delta=20)
        from app.services.profiles import _load_profiles, _save_profiles, _lock
        with _lock:
            store = _load_profiles()
            store[body.user_id]["tutorial_reward_claimed"] = True
            _save_profiles(store)

        return {"ok": True, "already_claimed": False, "coins": updated["coins"], "trophies": updated["trophies"]}
    except Exception as e:
        logger.error("Tutorial reward claim failed: %s", e)
        raise HTTPException(status_code=500, detail="Reward claim failed")


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