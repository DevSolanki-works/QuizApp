"""
Generation ticket balances for Forge custom quiz creation.

REDESIGNED (July 2026): Tickets are now a pure, persistent balance —
architecturally identical to coins. They never reset on a calendar basis.
The daily-limited allowance (2 free custom-topic generations/day) is a
completely separate counter, checked only at the moment a custom-topic
game is started (see use_generation()). This intentionally isolates the
one piece of genuinely date-sensitive logic in the whole ticket system
into a single function, rather than smearing "is this a new day?" checks
across every ticket-touching function like the old design did.

The `tickets_today` field name is kept as-is (rather than renamed to
`tickets`) purely to avoid an extra Supabase column-rename migration —
despite the name, it is now a persistent balance with no reset semantics,
exactly like `coins`.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.services import profiles

DAILY_FREE_GENERATIONS = 2
DAILY_AD_TICKET_CAP = 5
COINS_PER_TICKET = 25
DAILY_REWARD_TICKETS = {
    1: 1,
    2: 1,
    3: 1,
    4: 1,
    5: 2,
    6: 3,
    7: 5,
}


class TicketError(ValueError):
    """Raised when a ticket or free-generation operation cannot be completed."""


def _today() -> str:
    """Return today's UTC-local ISO date string for daily-reset checks."""

    return date.today().isoformat()


def _normalise_ticket_fields(profile: dict[str, Any]) -> dict[str, Any]:
    """Ensure a profile carries all ticket/generation fields used by this module."""

    profile.setdefault("tickets_today", 0)
    profile.setdefault("ad_tickets_used_today", 0)
    profile.setdefault("last_ticket_date", "")
    profile.setdefault("free_generations_used_today", 0)
    profile.setdefault("last_free_generation_date", "")
    profile["tickets_today"] = max(0, int(profile.get("tickets_today", 0)))
    profile["ad_tickets_used_today"] = max(0, int(profile.get("ad_tickets_used_today", 0)))
    profile["free_generations_used_today"] = max(0, int(profile.get("free_generations_used_today", 0)))
    return profile


def _reset_ad_cap_if_new_day(profile: dict[str, Any]) -> dict[str, Any]:
    """Reset the rewarded-ad daily cap counter — NOT the ticket balance itself."""

    today = _today()
    if profile.get("last_ticket_date") != today:
        profile["ad_tickets_used_today"] = 0
        profile["last_ticket_date"] = today
    return profile


def _reset_free_generations_if_new_day(profile: dict[str, Any]) -> dict[str, Any]:
    """Reset the free-generation allowance. The only daily-reset logic left."""

    today = _today()
    if profile.get("last_free_generation_date") != today:
        profile["free_generations_used_today"] = 0
        profile["last_free_generation_date"] = today
    return profile


def _ticket_state(profile: dict[str, Any]) -> dict[str, Any]:
    """Return the public ticket + free-generation payload for API consumers."""

    profile = _normalise_ticket_fields(profile)
    profile = _reset_ad_cap_if_new_day(profile)
    profile = _reset_free_generations_if_new_day(profile)
    return {
        "user_id": profile["id"],
        "tickets_today": int(profile["tickets_today"]),  # persistent balance despite the name
        "ad_tickets_used_today": int(profile["ad_tickets_used_today"]),
        "last_ticket_date": str(profile.get("last_ticket_date", "")),
        "free_generations_used_today": int(profile["free_generations_used_today"]),
        "daily_free_generations": DAILY_FREE_GENERATIONS,
        "daily_ad_cap": DAILY_AD_TICKET_CAP,
        "coins_per_ticket": COINS_PER_TICKET,
    }


def get_or_reset_tickets(user_id: str) -> dict[str, Any]:
    """
    Return current ticket + free-generation state, resetting only the two
    daily-limited counters (ad cap, free generations) if needed. The ticket
    balance itself is never touched here.
    """

    with profiles._lock:
        store = profiles._load_profiles()
        profile = store.get(user_id) or profiles._new_profile(user_id)
        profile = _normalise_ticket_fields(profile)
        profile = _reset_ad_cap_if_new_day(profile)
        profile = _reset_free_generations_if_new_day(profile)
        store[user_id] = profile
        profiles._save_profiles(store)
        return _ticket_state(profile)


def sync_tickets(
    user_id: str,
    tickets_today: int,
    ad_tickets_used_today: int,
    last_ticket_date: str,
) -> dict[str, Any]:
    """Force-update the ticket balance from the saved Supabase profile mirror."""

    with profiles._lock:
        store = profiles._load_profiles()
        profile = store.get(user_id) or profiles._new_profile(user_id)
        profile = _normalise_ticket_fields(profile)
        profile["tickets_today"] = max(0, int(tickets_today))
        profile["ad_tickets_used_today"] = max(0, int(ad_tickets_used_today))
        profile["last_ticket_date"] = str(last_ticket_date or "")
        store[user_id] = profile
        profiles._save_profiles(store)
        return _ticket_state(profile)


def use_generation(user_id: str) -> dict[str, Any]:
    """
    Consume one custom-topic generation for a game start.

    Prefers the free daily allowance (DAILY_FREE_GENERATIONS/day); falls
    back to spending one ticket from the balance if the free allowance is
    exhausted. Raises TicketError if neither is available.

    This is the ONLY place free-generation state changes, and the only
    place a game start actually spends anything — keeping the date-
    sensitive logic isolated to a single, easy-to-reason-about function.

    Returns the resulting state plus a "source" key: "free" or "ticket",
    so the caller can refund the correct thing if generation later fails.
    """

    with profiles._lock:
        store = profiles._load_profiles()
        profile = store.get(user_id) or profiles._new_profile(user_id)
        profile = _normalise_ticket_fields(profile)
        profile = _reset_free_generations_if_new_day(profile)

        if int(profile["free_generations_used_today"]) < DAILY_FREE_GENERATIONS:
            profile["free_generations_used_today"] = int(profile["free_generations_used_today"]) + 1
            store[user_id] = profile
            profiles._save_profiles(store)
            return {"source": "free", **_ticket_state(profile)}

        if int(profile["tickets_today"]) > 0:
            profile["tickets_today"] = int(profile["tickets_today"]) - 1
            store[user_id] = profile
            profiles._save_profiles(store)
            return {"source": "ticket", **_ticket_state(profile)}

        raise TicketError("Out of free generations and tickets today.")


def grant_bonus_generation(user_id: str) -> dict[str, Any]:
    """
    Grant one extra free generation for today, from the Custom Topic
    Rewarded Interstitial flow. Distinct from refund_generation() — this
    adds a genuinely new allowance rather than undoing a failed spend, so
    it can push free_generations_used_today negative (safe: use_generation
    just checks < DAILY_FREE_GENERATIONS, and a negative used-count means
    "more free generations than usual today," exactly as intended).
    """

    with profiles._lock:
        store = profiles._load_profiles()
        profile = store.get(user_id) or profiles._new_profile(user_id)
        profile = _normalise_ticket_fields(profile)
        profile = _reset_free_generations_if_new_day(profile)
        profile["free_generations_used_today"] = int(profile["free_generations_used_today"]) - 1
        store[user_id] = profile
        profiles._save_profiles(store)
        return _ticket_state(profile)


def refund_generation(user_id: str, source: str) -> dict[str, Any]:
    """Undo use_generation() after a failed quiz generation. `source` is
    the value returned by use_generation() — "free" or "ticket"."""

    with profiles._lock:
        store = profiles._load_profiles()
        profile = store.get(user_id) or profiles._new_profile(user_id)
        profile = _normalise_ticket_fields(profile)
        if source == "free":
            profile["free_generations_used_today"] = max(0, int(profile["free_generations_used_today"]) - 1)
        else:
            profile["tickets_today"] = int(profile["tickets_today"]) + 1
        store[user_id] = profile
        profiles._save_profiles(store)
        return _ticket_state(profile)


def grant_ad_ticket(user_id: str) -> dict[str, Any]:
    """Grant one rewarded-ad ticket into the balance, enforcing the daily ad cap."""

    with profiles._lock:
        store = profiles._load_profiles()
        profile = store.get(user_id) or profiles._new_profile(user_id)
        profile = _normalise_ticket_fields(profile)
        profile = _reset_ad_cap_if_new_day(profile)
        if int(profile["ad_tickets_used_today"]) >= DAILY_AD_TICKET_CAP:
            return {"ok": False, **_ticket_state(profile)}
        profile["tickets_today"] = int(profile["tickets_today"]) + 1
        profile["ad_tickets_used_today"] = int(profile["ad_tickets_used_today"]) + 1
        store[user_id] = profile
        profiles._save_profiles(store)
        return {"ok": True, **_ticket_state(profile)}


def buy_tickets_with_coins(user_id: str, num_tickets: int) -> dict[str, Any]:
    """Buy tickets into the balance for coins, with no daily purchase cap."""

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


def grant_daily_reward_tickets(user_id: str, day: int) -> dict[str, Any]:
    """Grant the ticket portion of the daily reward once per calendar day."""

    today = _today()
    reward_day = max(1, min(int(day), 7))
    granted = DAILY_REWARD_TICKETS[reward_day]
    with profiles._lock:
        store = profiles._load_profiles()
        profile = store.get(user_id) or profiles._new_profile(user_id)
        profile = _normalise_ticket_fields(profile)
        if profile.get("last_daily_reward_ticket_date") == today:
            state = _ticket_state(profile)
            state.update({"ok": False, "granted": 0})
            return state
        profile["tickets_today"] = int(profile["tickets_today"]) + granted
        profile["last_daily_reward_ticket_date"] = today
        profile["last_daily_reward_ticket_day"] = reward_day
        store[user_id] = profile
        profiles._save_profiles(store)
        state = _ticket_state(profile)
        state.update({"ok": True, "granted": granted})
        return state