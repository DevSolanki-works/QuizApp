"""
Generation ticket balances for Forge custom quiz creation.

Tickets live beside the existing file-backed profile balances so the backend
can enforce custom-room generation limits without adding paid infrastructure.
Supabase migrations mirror these fields for the app's long-term store.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.services import profiles

DAILY_FREE_TICKETS = 3
DAILY_AD_TICKET_CAP = 5
COINS_PER_TICKET = 50


class TicketError(ValueError):
    """Raised when a ticket operation cannot be completed."""


def _today() -> str:
    """Return today's UTC-local ISO date string for daily ticket checks."""

    return date.today().isoformat()


def _normalise_ticket_fields(profile: dict[str, Any]) -> dict[str, Any]:
    """Ensure a profile carries all ticket fields used by this module."""

    profile.setdefault("tickets_today", DAILY_FREE_TICKETS)
    profile.setdefault("ad_tickets_used_today", 0)
    profile.setdefault("last_ticket_date", "")
    profile.setdefault("last_signin_ticket_date", "")
    profile["tickets_today"] = max(0, int(profile.get("tickets_today", DAILY_FREE_TICKETS)))
    profile["ad_tickets_used_today"] = max(0, int(profile.get("ad_tickets_used_today", 0)))
    return profile


def _ticket_state(profile: dict[str, Any]) -> dict[str, Any]:
    """Return the public ticket payload for API consumers."""

    profile = _normalise_ticket_fields(profile)
    return {
        "user_id": profile["id"],
        "tickets_today": int(profile["tickets_today"]),
        "ad_tickets_used_today": int(profile["ad_tickets_used_today"]),
        "last_ticket_date": str(profile.get("last_ticket_date", "")),
        "daily_ad_cap": DAILY_AD_TICKET_CAP,
        "coins_per_ticket": COINS_PER_TICKET,
    }


def get_or_reset_tickets(user_id: str) -> dict[str, Any]:
    """Return current tickets, resetting the daily free/ad counters if needed."""

    today = _today()
    with profiles._lock:
        store = profiles._load_profiles()
        profile = store.get(user_id) or profiles._new_profile(user_id)
        profile = _normalise_ticket_fields(profile)
        if profile.get("last_ticket_date") != today:
            profile["tickets_today"] = DAILY_FREE_TICKETS
            profile["ad_tickets_used_today"] = 0
            profile["last_ticket_date"] = today
        store[user_id] = profile
        profiles._save_profiles(store)
        return _ticket_state(profile)


def spend_ticket(user_id: str) -> dict[str, Any]:
    """Spend one generation ticket or raise TicketError when none are available."""

    today = _today()
    with profiles._lock:
        store = profiles._load_profiles()
        profile = store.get(user_id) or profiles._new_profile(user_id)
        profile = _normalise_ticket_fields(profile)
        if profile.get("last_ticket_date") != today:
            profile["tickets_today"] = DAILY_FREE_TICKETS
            profile["ad_tickets_used_today"] = 0
            profile["last_ticket_date"] = today
        if int(profile["tickets_today"]) <= 0:
            raise TicketError("Out of generation tickets today.")
        profile["tickets_today"] = int(profile["tickets_today"]) - 1
        store[user_id] = profile
        profiles._save_profiles(store)
        return _ticket_state(profile)


def refund_ticket(user_id: str) -> dict[str, Any]:
    """Return one ticket after a failed generation attempt."""

    today = _today()
    with profiles._lock:
        store = profiles._load_profiles()
        profile = store.get(user_id) or profiles._new_profile(user_id)
        profile = _normalise_ticket_fields(profile)
        if profile.get("last_ticket_date") != today:
            profile["tickets_today"] = DAILY_FREE_TICKETS
            profile["ad_tickets_used_today"] = 0
            profile["last_ticket_date"] = today
        profile["tickets_today"] = int(profile["tickets_today"]) + 1
        store[user_id] = profile
        profiles._save_profiles(store)
        return _ticket_state(profile)


def grant_ad_ticket(user_id: str) -> dict[str, Any]:
    """Grant one rewarded-ad ticket while enforcing the daily ad cap."""

    today = _today()
    with profiles._lock:
        store = profiles._load_profiles()
        profile = store.get(user_id) or profiles._new_profile(user_id)
        profile = _normalise_ticket_fields(profile)
        if profile.get("last_ticket_date") != today:
            profile["tickets_today"] = DAILY_FREE_TICKETS
            profile["ad_tickets_used_today"] = 0
            profile["last_ticket_date"] = today
        if int(profile["ad_tickets_used_today"]) >= DAILY_AD_TICKET_CAP:
            return {"ok": False, **_ticket_state(profile)}
        profile["tickets_today"] = int(profile["tickets_today"]) + 1
        profile["ad_tickets_used_today"] = int(profile["ad_tickets_used_today"]) + 1
        store[user_id] = profile
        profiles._save_profiles(store)
        return {"ok": True, **_ticket_state(profile)}


def buy_tickets_with_coins(user_id: str, num_tickets: int) -> dict[str, Any]:
    """Buy generation tickets for 50 coins each, with no daily purchase cap."""

    if num_tickets <= 0:
        raise TicketError("num_tickets must be greater than zero.")

    cost = COINS_PER_TICKET * int(num_tickets)
    with profiles._lock:
        store = profiles._load_profiles()
        profile = store.get(user_id) or profiles._new_profile(user_id)
        profile = _normalise_ticket_fields(profile)
        coins = float(profile.get("coins", profiles.INITIAL_COINS))
        if coins < cost:
            raise TicketError("Insufficient coins.")
        profile["coins"] = coins - cost
        profile["tickets_today"] = int(profile["tickets_today"]) + int(num_tickets)
        store[user_id] = profile
        profiles._save_profiles(store)
        state = _ticket_state(profile)
        state.update({"coins": profile["coins"], "cost": cost})
        return state


def grant_signin_bonus(user_id: str) -> dict[str, Any]:
    """Grant one sign-in ticket once per day for the given user."""

    today = _today()
    with profiles._lock:
        store = profiles._load_profiles()
        profile = store.get(user_id) or profiles._new_profile(user_id)
        profile = _normalise_ticket_fields(profile)
        if profile.get("last_ticket_date") != today:
            profile["tickets_today"] = DAILY_FREE_TICKETS
            profile["ad_tickets_used_today"] = 0
            profile["last_ticket_date"] = today
        if profile.get("last_signin_ticket_date") == today:
            return {"ok": False, **_ticket_state(profile)}
        profile["tickets_today"] = int(profile["tickets_today"]) + 1
        profile["last_signin_ticket_date"] = today
        store[user_id] = profile
        profiles._save_profiles(store)
        return {"ok": True, **_ticket_state(profile)}
