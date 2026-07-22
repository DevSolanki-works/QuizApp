"""
File-backed Google profile balances for Forge.

The project intentionally avoids paid infrastructure and heavy databases. This
module keeps a tiny JSON document keyed by Google account ID so coins and
trophies can survive normal app navigation and server-process lifetime.
"""

from __future__ import annotations

import json
import os
from threading import RLock
from typing import Any

from app.core.config import settings

INITIAL_TROPHIES = 50
INITIAL_COINS = 200
ROOM_ENTRY_FEE = 25
SOLO_PASSING_COIN_REWARD = 10

_lock = RLock()


def _store_path() -> str:
    """Return the configured profile JSON path."""

    return settings.PROFILE_STORE_PATH


def _load_profiles() -> dict[str, dict[str, Any]]:
    """Load all profiles from disk, returning an empty store if absent."""

    path = _store_path()
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError:
            return {}
    return data if isinstance(data, dict) else {}


def _save_profiles(profiles: dict[str, dict[str, Any]]) -> None:
    """Atomically write all profile balances to disk."""

    path = _store_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(profiles, fh, ensure_ascii=True, indent=2, sort_keys=True)
    os.replace(tmp_path, path)


def _new_profile(user_id: str, email: str = "", name: str = "", picture: str = "") -> dict[str, Any]:
    """Create a fresh profile with the required starter economy."""

    return {
        "id": user_id,
        "email": email,
        "name": name,
        "picture": picture,
        "coins": float(INITIAL_COINS),
        "trophies": INITIAL_TROPHIES,
    }


def get_or_create_profile(
    user_id: str,
    email: str = "",
    name: str = "",
    picture: str = "",
) -> dict[str, Any]:
    """Return a Google profile, creating it with starter balances if needed."""

    with _lock:
        profiles = _load_profiles()
        profile = profiles.get(user_id)
        if not profile:
            profile = _new_profile(user_id, email, name, picture)
        else:
            profile.setdefault("coins", float(INITIAL_COINS))
            profile.setdefault("trophies", INITIAL_TROPHIES)
            if email:
                profile["email"] = email
            if name:
                profile["name"] = name
            if picture:
                profile["picture"] = picture
        profiles[user_id] = profile
        _save_profiles(profiles)
        return dict(profile)


def get_profile(user_id: str) -> dict[str, Any]:
    """Return an existing profile or initialize a minimal one."""

    return get_or_create_profile(user_id)


def sync_profile(user_id: str, coins: float, trophies: int) -> dict[str, Any]:
    """Force-update a profile to match external state (e.g. Supabase sync)."""

    with _lock:
        profiles = _load_profiles()
        profile = profiles.get(user_id) or _new_profile(user_id)
        profile["coins"] = float(coins)
        profile["trophies"] = int(trophies)
        profiles[user_id] = profile
        _save_profiles(profiles)
        return dict(profile)

def delete_profile(user_id: str) -> bool:
    """Permanently remove a user's profile from the file-backed store.

    This also removes generation-ticket fields, since tickets.py stores
    them as keys inside the same profile dict rather than a separate file.
    Returns True if a profile existed and was removed, False if there was
    nothing to delete.
    """

    with _lock:
        profiles = _load_profiles()
        existed = user_id in profiles
        profiles.pop(user_id, None)
        _save_profiles(profiles)
        return existed

def can_afford_entry(user_id: str) -> bool:
    """Return whether a profile has enough coins for a room entry fee."""

    profile = get_profile(user_id)
    return float(profile.get("coins", 0)) >= ROOM_ENTRY_FEE


def apply_delta(user_id: str, coins_delta: float = 0, trophies_delta: int = 0) -> dict[str, Any]:
    """Apply an economy delta and clamp trophies so they never drop below zero."""

    return apply_batch_deltas({user_id: {"coins_delta": coins_delta, "trophies_delta": trophies_delta}})[user_id]


def apply_batch_deltas(deltas: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """
    Apply multiple economy deltas in a single read/write cycle.
    deltas: { user_id: { "coins_delta": float, "trophies_delta": int } }
    """

    with _lock:
        profiles = _load_profiles()
        results = {}

        for user_id, delta in deltas.items():
            profile = profiles.get(user_id) or _new_profile(user_id)

            coins_delta = float(delta.get("coins_delta", 0))
            trophies_delta = int(delta.get("trophies_delta", 0))

            profile["coins"] = float(profile.get("coins", INITIAL_COINS)) + coins_delta
            trophies = int(profile.get("trophies", INITIAL_TROPHIES)) + trophies_delta
            profile["trophies"] = max(0, trophies)

            profiles[user_id] = profile
            results[user_id] = dict(profile)

        _save_profiles(profiles)
        return results


def solo_rewards(correct_answers: int) -> tuple[float, int]:
    """Calculate Solo Mode rewards from correct-answer count.

    Solo grants coins only. Trophies are a competitive rank earned/lost
    exclusively through Duel Mode matchmaking, so the trophy delta here is
    always zero (decided July 2026).
    """

    coins_delta = SOLO_PASSING_COIN_REWARD if correct_answers >= 5 else 0
    return float(coins_delta), 0
