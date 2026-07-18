"""
Supabase-backed storage for Async Challenge Mode (Online Duel — Phase 1).

WHY SUPABASE INSTEAD OF A LOCAL JSON FILE:
  The original design stored challenges in a local file, mirroring
  profiles.py. That works for profiles because the client always has a
  fresh Google ID token to re-sync from if a different instance doesn't
  have a user's row yet. Challenges have no such fallback: a challenge
  created on Instance A is invisible to Instance B/C, so a friend's GET
  or PATCH landing on a different instance than the one that created it
  returns a false "not found" — not a rare edge case at
  --max-instances 3, but something that happens constantly under real
  traffic. Supabase is reachable identically from every instance, so it
  removes the cross-instance problem entirely with zero new infra.

WHY THE ANON KEY:
  Same public key already used client-side (supabase-client.js) — safe
  to reuse since it's gated by Row Level Security, not secrecy. The
  `/complete` write below uses a `completed_at=is.null` filter, which is
  what actually enforces one-shot-per-challenge atomically at the
  database level, not RLS.
"""

from __future__ import annotations

import logging
import random
import string
import time
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.models.challenge import Challenge

logger = logging.getLogger(__name__)

CHALLENGE_TTL_SECONDS = 24 * 60 * 60
CODE_LENGTH = 5
MAX_CODE_ATTEMPTS = 5
_TABLE = "challenges"


def _headers() -> dict[str, str]:
    return {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }


def _rest_url() -> str:
    return f"{settings.SUPABASE_URL}/rest/v1/{_TABLE}"


def _generate_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choices(alphabet, k=CODE_LENGTH))


async def create_challenge(
    creator_name: str,
    creator_user_id: Optional[str],
    topic: str,
    mode: str,
    time_limit_ms: int,
    questions: list[dict[str, Any]],
    creator_score: int,
    creator_correct_answers: int,
) -> Challenge:
    """Freeze a just-finished Solo game into a shareable challenge row."""

    now = time.time()

    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(MAX_CODE_ATTEMPTS):
            code = _generate_code()
            payload = {
                "code": code,
                "creator_name": creator_name,
                "creator_user_id": creator_user_id,
                "topic": topic,
                "mode": mode,
                "time_limit_ms": time_limit_ms,
                "questions": questions,
                "creator_score": creator_score,
                "creator_correct_answers": creator_correct_answers,
                "created_at": now,
                "expires_at": now + CHALLENGE_TTL_SECONDS,
            }
            resp = await client.post(
                _rest_url(),
                headers={**_headers(), "Prefer": "return=representation"},
                json=payload,
            )
            if resp.status_code in (200, 201):
                row = resp.json()[0]
                return Challenge(**row)
            if resp.status_code == 409:
                # Code collision (primary key conflict) — extremely rare
                # at 36^5 combinations, but regenerate and retry.
                logger.warning("Challenge code collision on attempt %d: %s", attempt, code)
                continue
            logger.error("Challenge create failed: %s %s", resp.status_code, resp.text)
            resp.raise_for_status()

        raise RuntimeError("Could not generate a unique challenge code after several attempts.")


async def get_challenge(code: str) -> Optional[Challenge]:
    """Fetch a still-valid (non-expired) challenge, or None if missing/expired."""

    now = time.time()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            _rest_url(),
            headers=_headers(),
            params={"code": f"eq.{code.upper()}", "select": "*"},
        )
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            return None
        challenge = Challenge(**rows[0])
        if challenge.expires_at <= now:
            return None
        return challenge


async def complete_challenge(
    code: str,
    challenger_name: str,
    challenger_user_id: Optional[str],
    challenger_score: int,
    challenger_correct_answers: int,
) -> Challenge:
    """
    Record the challenger's result. One-shot, enforced atomically by
    Postgres via the completed_at=is.null filter — if two requests race
    for the same challenge, only the first PATCH matches any rows; the
    second gets zero rows back and is rejected here.
    """

    code = code.upper()
    now = time.time()

    existing = await get_challenge(code)
    if existing is None:
        raise ValueError("Challenge not found or expired.")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.patch(
            _rest_url(),
            headers={**_headers(), "Prefer": "return=representation"},
            params={"code": f"eq.{code}", "completed_at": "is.null"},
            json={
                "challenger_name": challenger_name,
                "challenger_user_id": challenger_user_id,
                "challenger_score": challenger_score,
                "challenger_correct_answers": challenger_correct_answers,
                "completed_at": now,
            },
        )
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            raise ValueError("This challenge has already been completed.")
        return Challenge(**rows[0])