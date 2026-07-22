"""
Power-Ups for Forge — coin-purchased, inventory-held, used mid-game.

DESIGN (July 2026):
  Power-ups are a pure COIN SINK — the first recurring one in the economy
  (coins previously only left via room entry fees). Players buy them in the
  Shop, hold them as an inventory dict inside the file-backed profile store
  (same pattern as tickets), and spend them in-game via the room WebSocket's
  "use_powerup" action.

MODE RULES (enforced in websocket.py, catalogued here):
  - Solo / Classic / Team: FIFTY_FIFTY, TIME_FREEZE, DOUBLE_POINTS.
    Each type usable at most once per question per player.
  - Duel: all four types incl. the duel-exclusive TIME_STEAL, but a player
    may use at most TWO power-ups per match and never the same type twice —
    keeps duels primarily a skill contest, not a wallet contest.

The server is authoritative for every effect: 50/50 reveals wrong indices
only server-side, DOUBLE_POINTS doubles at scoring time, TIME_FREEZE
extends the server round timeout, TIME_STEAL is broadcast server-side.
"""

from __future__ import annotations

from typing import Any

from app.services import profiles

# id → catalog entry. `duel_only` types never appear in other modes;
# `modes` lists where the power-up may be used.
POWERUP_CATALOG: dict[str, dict[str, Any]] = {
    "fifty_fifty": {
        "name": "50/50",
        "icon": "➗",
        "price": 30,
        "desc": "Removes two wrong answers on the current question.",
        "modes": ["solo", "classic", "team", "duel"],
    },
    "time_freeze": {
        "name": "Time Freeze",
        "icon": "❄️",
        "price": 25,
        "desc": "Adds 5 bonus seconds to your clock on the current question.",
        "modes": ["solo", "classic", "team", "duel"],
    },
    "double_points": {
        "name": "Double Points",
        "icon": "✨",
        "price": 40,
        "desc": "Your next correct answer scores 2x points.",
        "modes": ["solo", "classic", "team", "duel"],
    },
    "time_steal": {
        "name": "Time Steal",
        "icon": "⏳",
        "price": 35,
        "desc": "Steals 5 seconds from your opponent's clock. Duels only!",
        "modes": ["duel"],
    },
}

# Duel fairness caps (see module docstring).
DUEL_MAX_POWERUPS_PER_MATCH = 2
FREEZE_BONUS_SECONDS = 5
STEAL_SECONDS = 5


class PowerupError(ValueError):
    """Raised when a purchase or consumption cannot be performed."""


def _inventory(profile: dict[str, Any]) -> dict[str, int]:
    inv = profile.setdefault("powerups", {})
    if not isinstance(inv, dict):
        inv = profile["powerups"] = {}
    return inv


def catalog_payload() -> list[dict[str, Any]]:
    """Catalog in a stable, client-renderable shape."""
    return [
        {"id": pid, **{k: v for k, v in entry.items()}}
        for pid, entry in POWERUP_CATALOG.items()
    ]


def get_state(user_id: str) -> dict[str, Any]:
    """Return the catalog plus this user's owned counts."""
    with profiles._lock:
        store = profiles._load_profiles()
        profile = store.get(user_id) or profiles._new_profile(user_id)
        inv = _inventory(profile)
        return {
            "catalog": catalog_payload(),
            "inventory": {pid: int(inv.get(pid, 0)) for pid in POWERUP_CATALOG},
        }


def buy(user_id: str, powerup_id: str) -> dict[str, Any]:
    """Buy one power-up with coins. Raises PowerupError on any failure."""
    entry = POWERUP_CATALOG.get(powerup_id)
    if not entry:
        raise PowerupError("Unknown power-up.")

    with profiles._lock:
        store = profiles._load_profiles()
        profile = store.get(user_id) or profiles._new_profile(user_id)
        coins = float(profile.get("coins", profiles.INITIAL_COINS))
        price = float(entry["price"])
        if coins < price:
            raise PowerupError(f"Not enough coins — {entry['name']} costs {entry['price']} 🪙.")

        profile["coins"] = coins - price
        inv = _inventory(profile)
        inv[powerup_id] = int(inv.get(powerup_id, 0)) + 1

        store[user_id] = profile
        profiles._save_profiles(store)
        return {
            "coins": float(profile["coins"]),
            "inventory": {pid: int(inv.get(pid, 0)) for pid in POWERUP_CATALOG},
        }


def consume(user_id: str, powerup_id: str) -> bool:
    """
    Spend one owned power-up. Returns True if one was available and consumed,
    False otherwise (never raises — the WS caller turns False into an ERROR).
    """
    if powerup_id not in POWERUP_CATALOG:
        return False
    with profiles._lock:
        store = profiles._load_profiles()
        profile = store.get(user_id)
        if not profile:
            return False
        inv = _inventory(profile)
        if int(inv.get(powerup_id, 0)) < 1:
            return False
        inv[powerup_id] = int(inv[powerup_id]) - 1
        store[user_id] = profile
        profiles._save_profiles(store)
        return True


def allowed_in_mode(powerup_id: str, play_mode: str) -> bool:
    """True if this power-up may be used in the given play mode."""
    entry = POWERUP_CATALOG.get(powerup_id)
    return bool(entry and play_mode in entry["modes"])
