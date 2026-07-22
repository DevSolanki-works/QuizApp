"""
Sync 1v1 Duel Queue — matchmaking state and duel-specific rules (Duel Phase 2).

WHY IN-MEMORY, SAME AS ROOMS:
  The duel queue lives in process memory exactly like app.core.state.rooms.
  Matchmaking only works between two players whose queue WebSockets landed
  on the same Cloud Run instance — identical to how a friend joining a
  Classic room by code must hit the instance holding that room. At the
  current traffic level one instance is warm at a time, so this matches the
  existing multiplayer trust model without new infrastructure.

ECONOMY:
  Entry fee reuses ROOM_ENTRY_FEE (25 coins) → 50-coin winner-takes-all pot.
  Trophies move ONLY here (Solo no longer grants them): +8 win / −5 loss,
  floored at zero by apply_batch_deltas. Bot practice matches charge no fee,
  move no trophies, and pay a small consolation coin reward on a win so the
  mode stays playable (and rewarding) when the queue is empty.
"""

from __future__ import annotations

import os
import random
import string
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from app.core import state
from app.models.quiz import GameMode, GameStatus, PlayMode, Player, Room
from app.services.quick_picks import QUICK_PICK_TOPICS, bank_topics_with_questions

# ── Tunables ──────────────────────────────────────────────────────────────────

DUEL_TIME_LIMIT_MS      = 15_000  # between Medium (20s) and Hard (10s) — deliberate
DUEL_QUESTION_COUNT     = 10
DUEL_RESERVE_QUESTIONS  = 3       # sudden-death pool drawn alongside the main set
DUEL_SUDDEN_DEATH_MAX   = 3       # after this many tied extra questions → split pot
DUEL_TROPHY_WIN         = 8
DUEL_TROPHY_LOSS        = -5
DUEL_BOT_WIN_COINS      = 5.0     # consolation reward for beating the practice bot
DUEL_TOPIC_CHOICES      = 3       # options shown to both players
MATCH_TROPHY_WINDOW     = 100     # ±trophies for a fair match
MATCH_WIDEN_AFTER_SECS  = 15      # lift the trophy window once a player waits this long

# TEST-ONLY escape hatch: when DUEL_ALLOW_SAME_IP=1 the same-IP anti-farm guard
# is skipped, so two devices on one home network can duel each other for
# real-human testing. MUST stay unset in production — leaving it on re-opens the
# self-farming coin exploit. Defaults off; read once at import.
ALLOW_SAME_IP = os.getenv("DUEL_ALLOW_SAME_IP", "").strip() in ("1", "true", "yes")

BOT_NAMES = (
    "QuizBot 3000", "Trivia Titan", "Captain Cortex", "Professor Pixel",
    "Sir Answersalot", "The Quizzard", "Neura", "Brainiac Jr.",
)


# ── Queue state ───────────────────────────────────────────────────────────────

@dataclass
class QueueEntry:
    """One player waiting in the duel matchmaking queue."""

    name: str
    user_id: str
    trophies: int
    ip: str
    websocket: Any
    joined_at: float = field(default_factory=time.time)


# { user_id → QueueEntry } — dict keys double as the "already queued" guard.
duel_queue: dict[str, QueueEntry] = {}

# Head-to-head win records, per instance: { "uidA|uidB" (sorted) → {uid: wins} }
_h2h_records: dict[str, dict[str, int]] = {}


def queue_size() -> int:
    """Return how many players are currently waiting for a duel."""
    return len(duel_queue)


def add_to_queue(entry: QueueEntry) -> bool:
    """Add a player to the queue. Returns False if they are already waiting."""
    if entry.user_id in duel_queue:
        return False
    duel_queue[entry.user_id] = entry
    return True


def remove_from_queue(user_id: str) -> None:
    """Remove a player from the queue (cancel, disconnect, or matched)."""
    duel_queue.pop(user_id, None)


def find_match(entry: QueueEntry) -> Optional[QueueEntry]:
    """
    Find a fair opponent for `entry` among the other waiting players.

    Fairness rules, in order:
      - Never match a player against themselves (distinct user_id).
      - Same-IP pairs are refused outright — the basic anti-abuse guard
        against one person running two accounts on one device/network to
        farm the coin pot risk-free.
      - Trophy gap must be within ±MATCH_TROPHY_WINDOW, unless EITHER
        player has waited MATCH_WIDEN_AFTER_SECS — a tiny player base
        makes a strict window feel dead, so fairness degrades gracefully
        into "any opponent is better than no opponent".
    """
    now = time.time()
    entry_widened = (now - entry.joined_at) >= MATCH_WIDEN_AFTER_SECS

    best: Optional[QueueEntry] = None
    best_gap = 10 ** 9
    for other in duel_queue.values():
        if other.user_id == entry.user_id:
            continue
        if other.ip == entry.ip and not ALLOW_SAME_IP:
            continue
        gap = abs(other.trophies - entry.trophies)
        widened = entry_widened or (now - other.joined_at) >= MATCH_WIDEN_AFTER_SECS
        if gap > MATCH_TROPHY_WINDOW and not widened:
            continue
        if gap < best_gap:
            best, best_gap = other, gap
    return best


# ── Head-to-head records ──────────────────────────────────────────────────────

def _h2h_key(uid_a: str, uid_b: str) -> str:
    return "|".join(sorted((uid_a, uid_b)))


def record_h2h_win(winner_uid: str, loser_uid: str) -> None:
    """Record a duel win for the head-to-head tally between two players."""
    key = _h2h_key(winner_uid, loser_uid)
    rec = _h2h_records.setdefault(key, {})
    rec[winner_uid] = rec.get(winner_uid, 0) + 1


def get_h2h(uid_a: str, uid_b: str) -> dict[str, int]:
    """Return {uid: wins} for two players' prior duels (empty if first meeting)."""
    return dict(_h2h_records.get(_h2h_key(uid_a, uid_b), {}))


# ── Room construction ─────────────────────────────────────────────────────────

def _generate_room_code() -> str:
    """Generate a unique four-character room code (same alphabet as HTTP rooms)."""
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        if code not in state.rooms:
            return code


def _duel_topic_options() -> list[str]:
    """
    Pick the topic choices from topics the bank can actually serve.

    Duels draw 13 questions (10 + 3 sudden-death reserves) purely from the
    static bank with NO Gemini fallback, so a topic that exists in name but
    has too few questions (e.g. an empty 'General Knowledge' entry) would
    hard-fail the game start. Filter by real question counts, not the name
    list.
    """
    pool = bank_topics_with_questions(DUEL_QUESTION_COUNT + DUEL_RESERVE_QUESTIONS)
    if len(pool) < DUEL_TOPIC_CHOICES:
        pool = list(QUICK_PICK_TOPICS)  # bank missing entirely — degraded, but never crash here
    return random.sample(pool, DUEL_TOPIC_CHOICES)


def create_duel_room(p1: QueueEntry, p2: QueueEntry) -> Room:
    """
    Create a locked 2-player duel room for a matched pair.

    Both players are pre-registered (websocket=None) so the room's join
    path can recognise them by name; the room is locked so nobody else can
    slip in through the normal join-by-code flow.
    """
    code = _generate_room_code()
    room = Room(
        code=code,
        host=p1.name,
        status=GameStatus.WAITING,
        play_mode=PlayMode.DUEL,
        mode=GameMode.MEDIUM,          # difficulty label is irrelevant for duels
        time_limit_ms=DUEL_TIME_LIMIT_MS,
        locked=True,
        duel_topic_options=_duel_topic_options(),
    )
    room.players[p1.name] = Player(name=p1.name, user_id=p1.user_id)
    room.players[p2.name] = Player(name=p2.name, user_id=p2.user_id)
    state.rooms[code] = room
    return room


def create_bot_duel_room(entry: QueueEntry) -> Room:
    """
    Create an unranked practice duel vs a bot for an empty-queue fallback.

    No entry fee, no trophies — the bot exists so the mode never feels dead
    with a small player base, not as a coin faucet.
    """
    code = _generate_room_code()
    bot_name = random.choice(BOT_NAMES)
    room = Room(
        code=code,
        host=entry.name,
        status=GameStatus.WAITING,
        play_mode=PlayMode.DUEL,
        mode=GameMode.MEDIUM,
        time_limit_ms=DUEL_TIME_LIMIT_MS,
        locked=True,
        duel_is_bot=True,
        duel_bot_name=bot_name,
        duel_bot_accuracy=random.uniform(0.5, 0.7),
        duel_topic_options=_duel_topic_options(),
    )
    room.players[entry.name] = Player(name=entry.name, user_id=entry.user_id)
    room.players[bot_name] = Player(name=bot_name, user_id=None)
    state.rooms[code] = room
    return room


# ── Duel outcome helpers ──────────────────────────────────────────────────────

def duel_winner_name(room: Room) -> Optional[str]:
    """
    Return the winning player's name, or None for a still-tied duel.

    Forfeit beats score: if a player abandoned an active duel, the player
    who stayed wins regardless of the scoreboard at that moment.
    """
    if room.duel_forfeit_winner:
        return room.duel_forfeit_winner
    names = list(room.players.keys())
    if len(names) != 2:
        return None
    a, b = names
    sa, sb = room.players[a].score, room.players[b].score
    if sa == sb:
        return None
    return a if sa > sb else b


def bot_answer_choice(room: Room, correct_index: int) -> int:
    """Pick the bot's answer: correct with the room's per-match accuracy."""
    if random.random() < room.duel_bot_accuracy:
        return correct_index
    wrong = [i for i in range(4) if i != correct_index]
    return random.choice(wrong)


def bot_answer_delay_secs() -> float:
    """A human-feeling answer delay within the 15-second duel timer."""
    return random.uniform(3.0, 11.0)
