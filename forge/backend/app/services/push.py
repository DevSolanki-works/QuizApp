"""
services/push.py — Firebase Cloud Messaging for Forge.

Stores each signed-in user's current FCM device token in Supabase
(push_tokens table, anon-key REST access — same pattern as challenges.py)
and sends notifications via the Firebase Admin SDK.

WHY EVERY SEND CALL IS WRAPPED IN try/except:
  A push notification is always a "nice to have" side effect of something
  that already succeeded (e.g. a challenge was already recorded as
  completed before we try to notify the creator). A push failure — no
  token on file, an expired token, FCM being briefly unreachable — must
  never surface as an error on the caller's actual request.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_TABLE = "push_tokens"


def _headers() -> dict[str, str]:
    return {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }


def _rest_url() -> str:
    return f"{settings.SUPABASE_URL}/rest/v1/{_TABLE}"


async def register_token(user_id: str, fcm_token: str) -> None:
    """Upsert a user's current device token — latest sign-in wins."""

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            _rest_url(),
            headers={**_headers(), "Prefer": "resolution=merge-duplicates"},
            params={"on_conflict": "user_id"},
            json={"user_id": user_id, "fcm_token": fcm_token},
        )
        resp.raise_for_status()


async def _get_token(user_id: str) -> Optional[str]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            _rest_url(),
            headers=_headers(),
            params={"user_id": f"eq.{user_id}", "select": "fcm_token"},
        )
        resp.raise_for_status()
        rows = resp.json()
        return rows[0]["fcm_token"] if rows else None


async def send_challenge_completed(
    creator_user_id: str,
    challenger_name: str,
    challenger_score: int,
    creator_score: int,
    topic: str,
    challenge_code: str,
) -> None:
    """Notify a challenge creator that their friend just finished it."""

    try:
        import firebase_admin
        from firebase_admin import messaging

        if not firebase_admin._apps:
            return  # Push disabled (no credential configured) — silent no-op

        token = await _get_token(creator_user_id)
        if not token:
            return  # User never registered a device, or hasn't opened the native app

        won = creator_score > challenger_score
        body = (
            f"{challenger_name} scored {challenger_score} on your \"{topic}\" "
            f"challenge — you {'won' if won else 'got beaten'}!"
        )

        message = messaging.Message(
            notification=messaging.Notification(
                title="🎯 Your challenge was completed!",
                body=body,
            ),
            data={
                "type": "challenge_completed",
                "challenge_code": challenge_code,
            },
            token=token,
        )
        messaging.send(message)
        logger.info("Push sent to %s for challenge %s", creator_user_id, challenge_code)

    except Exception as exc:
        # Covers: bad/expired token, FCM outage, firebase_admin not
        # installed/initialized, malformed data — none of these should
        # ever bubble up to the caller (complete_challenge already
        # succeeded by the time this runs).
        logger.warning("Push send failed for challenge %s: %s", challenge_code, exc)