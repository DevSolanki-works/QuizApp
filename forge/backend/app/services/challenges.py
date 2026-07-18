"""
File-backed storage for Async Challenge Mode (Online Duel — Phase 1).

WHY A SEPARATE STORE FROM profiles.py:
  Challenges are ephemeral (24h TTL) and have nothing to do with account
  balances — keeping them in their own file means a corrupt/huge
  challenges.json can never take down coin/trophy reads, and vice versa.

WHY NOT app.core.state.rooms:
  Live rooms are in-memory and die with the process by design (see
  state.py). Challenges must survive a Cloud Run scale-to-zero cycle for
  the full 24h window, so they need the same disk-backed durability
  pattern as profiles.py, not the in-memory rooms registry.

Expiry is swept lazily (on create + on read) rather than via a background
task — consistent with the project's $0-infra, no-cron constraint.
"""

from __future__ import annotations

import json
import os
import random
import string
import time
from threading import RLock
from typing import Any, Optional

from app.core.config import settings
from app.models.challenge import Challenge

CHALLENGE_TTL_SECONDS = 24 * 60 * 60
CODE_LENGTH = 5  # 5 chars keeps collision odds low without a live-room registry to check against

_lock = RLock()


def _store_path() -> str:
    """Reuse the same data directory as profiles.json, different filename."""

    profile_path = settings.PROFILE_STORE_PATH
    directory = os.path.dirname(profile_path) or "."
    return os.path.join(directory, "challenges.json")


def _load_all() -> dict[str, dict[str, Any]]:
    path = _store_path()
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError:
            return {}
    return data if isinstance(data, dict) else {}


def _save_all(challenges: dict[str, dict[str, Any]]) -> None:
    path = _store_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(challenges, fh, ensure_ascii=True, indent=2, sort_keys=True)
    os.replace(tmp_path, path)


def _sweep_expired(challenges: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Drop any challenge past its expires_at. Called under the lock only."""

    now = time.time()
    return {
        code: c for code, c in challenges.items()
        if float(c.get("expires_at", 0)) > now
    }


def _generate_code(existing: dict[str, Any]) -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choices(alphabet, k=CODE_LENGTH))
        if code not in existing:
            return code


def create_challenge(
    creator_name: str,
    creator_user_id: Optional[str],
    topic: str,
    mode: str,
    time_limit_ms: int,
    questions: list[dict[str, Any]],
    creator_score: int,
    creator_correct_answers: int,
) -> Challenge:
    """Freeze a just-finished Solo game into a shareable challenge."""

    with _lock:
        store = _sweep_expired(_load_all())
        code = _generate_code(store)
        now = time.time()

        challenge = Challenge(
            code=code,
            creator_name=creator_name,
            creator_user_id=creator_user_id,
            topic=topic,
            mode=mode,
            time_limit_ms=time_limit_ms,
            questions=questions,
            creator_score=creator_score,
            creator_correct_answers=creator_correct_answers,
            created_at=now,
            expires_at=now + CHALLENGE_TTL_SECONDS,
        )

        store[code] = json.loads(challenge.model_dump_json())
        _save_all(store)
        return challenge


def get_challenge(code: str) -> Optional[Challenge]:
    """Fetch a still-valid challenge, or None if missing/expired."""

    with _lock:
        store = _sweep_expired(_load_all())
        raw = store.get(code.upper())
        if raw is None:
            return None
        # Persist the sweep result so expired entries don't linger on disk
        # forever just because nobody happened to fetch them.
        _save_all(store)
        return Challenge(**raw)


def complete_challenge(
    code: str,
    challenger_name: str,
    challenger_user_id: Optional[str],
    challenger_score: int,
    challenger_correct_answers: int,
) -> Challenge:
    """
    Record the challenger's result. One-shot — raises ValueError if the
    challenge is missing, expired, or already completed.
    """

    with _lock:
        store = _sweep_expired(_load_all())
        code = code.upper()
        raw = store.get(code)
        if raw is None:
            raise ValueError("Challenge not found or expired.")
        if raw.get("completed_at") is not None:
            raise ValueError("This challenge has already been completed.")

        raw["challenger_name"] = challenger_name
        raw["challenger_user_id"] = challenger_user_id
        raw["challenger_score"] = challenger_score
        raw["challenger_correct_answers"] = challenger_correct_answers
        raw["completed_at"] = time.time()

        store[code] = raw
        _save_all(store)
        return Challenge(**raw)