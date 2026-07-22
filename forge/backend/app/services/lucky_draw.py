"""
Daily Lucky Draw for Forge.

One free spin per calendar day per signed-in user, plus one optional
rewarded-ad respin per day. The server rolls the prize (never the client),
applies it atomically to the profile store, and returns the result.

Prize wheel has 8 fixed segments so the frontend can animate the wheel
landing on the exact server-chosen segment index.
"""

from __future__ import annotations

import random
import time
from datetime import date
from typing import Any

from app.services import profiles

# One free spin per calendar day; each ad respin unlocks another spin after a
# fixed cooldown (rather than a hard once-per-day cap), so an engaged player can
# earn a few extra spins across a day while ads stay tap-driven per CLAUDE.md.
RESPIN_COOLDOWN_SECONDS = 3600  # 1 hour

# (kind, amount, weight, label) — order matters: index == wheel segment.
WHEEL_SEGMENTS: list[dict[str, Any]] = [
    {"kind": "coins", "amount": 5, "weight": 24, "label": "5 COINS"},
    {"kind": "coins", "amount": 10, "weight": 22, "label": "10 COINS"},
    {"kind": "tickets", "amount": 1, "weight": 14, "label": "1 TICKET"},
    {"kind": "coins", "amount": 15, "weight": 16, "label": "15 COINS"},
    {"kind": "coins", "amount": 25, "weight": 10, "label": "25 COINS"},
    {"kind": "tickets", "amount": 2, "weight": 6, "label": "2 TICKETS"},
    {"kind": "coins", "amount": 50, "weight": 6, "label": "50 COINS"},
    {"kind": "coins", "amount": 200, "weight": 2, "label": "JACKPOT 200"},
]

_TOTAL_WEIGHT = sum(s["weight"] for s in WHEEL_SEGMENTS)


class LuckyDrawError(ValueError):
    """Raised when a spin cannot be performed."""


def _today() -> str:
    return date.today().isoformat()


def _normalise(profile: dict[str, Any]) -> dict[str, Any]:
    profile.setdefault("last_lucky_draw_date", "")
    profile.setdefault("last_lucky_respin_at", 0.0)
    return profile


def _respin_remaining(profile: dict[str, Any]) -> int:
    """Seconds left on the ad-respin cooldown (0 = a respin is available)."""
    last = float(profile.get("last_lucky_respin_at", 0.0) or 0.0)
    if last <= 0:
        return 0
    elapsed = time.time() - last
    return max(0, int(RESPIN_COOLDOWN_SECONDS - elapsed))


def _state(profile: dict[str, Any]) -> dict[str, Any]:
    today = _today()
    free_used = profile.get("last_lucky_draw_date") == today
    remaining = _respin_remaining(profile)
    return {
        "free_spin_available": not free_used,
        # A respin is offered only after the free spin is spent and the
        # cooldown from the previous respin has elapsed.
        "respin_available": free_used and remaining == 0,
        "respin_cooldown_seconds": remaining,
        "segments": [{"kind": s["kind"], "amount": s["amount"], "label": s["label"]} for s in WHEEL_SEGMENTS],
    }


def _roll() -> int:
    pick = random.uniform(0, _TOTAL_WEIGHT)
    acc = 0.0
    for i, seg in enumerate(WHEEL_SEGMENTS):
        acc += seg["weight"]
        if pick <= acc:
            return i
    return len(WHEEL_SEGMENTS) - 1


def get_state(user_id: str) -> dict[str, Any]:
    """Return spin availability + wheel layout for the UI."""

    with profiles._lock:
        store = profiles._load_profiles()
        profile = store.get(user_id) or profiles._new_profile(user_id)
        profile = _normalise(profile)
        store[user_id] = profile
        profiles._save_profiles(store)
        return _state(profile)


def spin(user_id: str, is_respin: bool = False) -> dict[str, Any]:
    """
    Perform a spin. `is_respin=True` consumes the once-daily ad respin
    (client only calls it after a completed rewarded ad). Raises
    LuckyDrawError if the relevant allowance is already used today.
    """

    today = _today()
    with profiles._lock:
        store = profiles._load_profiles()
        profile = store.get(user_id) or profiles._new_profile(user_id)
        profile = _normalise(profile)

        if is_respin:
            if profile.get("last_lucky_draw_date") != today:
                raise LuckyDrawError("Use your free spin first.")
            remaining = _respin_remaining(profile)
            if remaining > 0:
                mins = (remaining + 59) // 60
                raise LuckyDrawError(f"Next respin available in ~{mins} min.")
            profile["last_lucky_respin_at"] = time.time()
        else:
            if profile.get("last_lucky_draw_date") == today:
                raise LuckyDrawError("Free spin already used today. Come back tomorrow!")
            profile["last_lucky_draw_date"] = today

        idx = _roll()
        seg = WHEEL_SEGMENTS[idx]
        if seg["kind"] == "coins":
            profile["coins"] = float(profile.get("coins", profiles.INITIAL_COINS)) + seg["amount"]
        else:
            profile["tickets_today"] = max(0, int(profile.get("tickets_today", 0))) + seg["amount"]

        store[user_id] = profile
        profiles._save_profiles(store)

        return {
            "segment_index": idx,
            "kind": seg["kind"],
            "amount": seg["amount"],
            "label": seg["label"],
            "coins": float(profile.get("coins", 0)),
            "tickets_today": int(profile.get("tickets_today", 0)),
            **_state(profile),
        }
