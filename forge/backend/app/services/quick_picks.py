"""Static Quick Picks question bank for no-cost generated Solo topics.

The JSON bank file is bundled at app/data/quick_picks_questions.json.
If the file is absent (e.g. first deploy before the file was committed),
is_quick_pick_topic() still returns True for known topics, but
get_quick_pick_questions() will raise ValueError so the caller falls back
to Gemini generation. This keeps the app healthy even when the data file
is missing rather than crashing the WebSocket handler.
"""

from __future__ import annotations

import json
import logging
import random
from collections import defaultdict, deque
from pathlib import Path
from threading import RLock
from typing import Any

from app.models.quiz import Question

logger = logging.getLogger(__name__)

QUICK_PICK_TOPICS = (
    "Movies",
    "Space & Astronomy",
    "Video Games",
    "World Geography",
    "Science",
    "Biology",
    "AI & Tech",
    "Football",
    "Cricket",
    "General Knowledge",
)

_BANK_PATH = Path(__file__).resolve().parents[1] / "data" / "quick_picks_questions.json"
_lock = RLock()
_bank_cache: dict[str, list[dict[str, Any]]] | None = None
_bank_unavailable: bool = False          # set True after first failed load
_recent_questions: dict[str, deque[str]] = defaultdict(lambda: deque(maxlen=120))


def _normalise_topic(topic: str) -> str:
    """Return a comparison-safe topic key."""
    return " ".join(str(topic or "").strip().lower().replace("&", "and").split())


_TOPIC_ALIASES: dict[str, str] = {_normalise_topic(t): t for t in QUICK_PICK_TOPICS}
_TOPIC_ALIASES.update({
    "ai and tech":       "AI & Tech",
    "space and astronomy": "Space & Astronomy",
    "geography":         "World Geography",
    "world geography":   "World Geography",
    "general knowledge": "General Knowledge",
})


def canonical_quick_pick_topic(topic: str) -> str | None:
    """Return the canonical Quick Pick topic name, or None if not a static topic."""
    return _TOPIC_ALIASES.get(_normalise_topic(topic))


def is_quick_pick_topic(topic: str) -> bool:
    """
    Return whether the topic matches the static Quick Picks bank.

    This check is purely name-based — it never touches disk — so it is safe
    to call on every game start without worrying about file availability.
    """
    return canonical_quick_pick_topic(topic) is not None


def bank_topics_with_questions(min_count: int = 13) -> list[str]:
    """
    Return canonical topics that actually have at least `min_count` usable
    questions in the bank — the safe pool for modes (like Duels) that draw
    exclusively from the bank and have no Gemini fallback.
    """
    bank = _load_bank()
    return [
        t for t in QUICK_PICK_TOPICS
        if isinstance(bank.get(t), list) and len(bank[t]) >= min_count
    ]


def _load_bank() -> dict[str, list[dict[str, Any]]]:
    """
    Load and validate the Quick Picks bank once per process.

    Returns an empty dict if the file does not exist so callers can degrade
    gracefully to Gemini generation instead of crashing.
    """
    global _bank_cache, _bank_unavailable

    if _bank_cache is not None:
        return _bank_cache
    if _bank_unavailable:
        return {}

    with _lock:
        if _bank_cache is not None:
            return _bank_cache
        if _bank_unavailable:
            return {}

        if not _BANK_PATH.exists():
            logger.warning(
                "Quick Picks bank not found at %s — falling back to Gemini for static topics",
                _BANK_PATH,
            )
            _bank_unavailable = True
            return {}

        try:
            with open(_BANK_PATH, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load Quick Picks bank: %s", exc)
            _bank_unavailable = True
            return {}

        if not isinstance(raw, dict):
            logger.error("Quick Picks bank must be a JSON object, got %s", type(raw).__name__)
            _bank_unavailable = True
            return {}

        # Validate each known topic
        missing = []
        for topic in QUICK_PICK_TOPICS:
            rows = raw.get(topic)
            if not isinstance(rows, list) or len(rows) < 10:
                missing.append(topic)
                continue
            for i, item in enumerate(rows):
                try:
                    Question(**item)
                except Exception as exc:
                    logger.error("Quick Picks bank: invalid question %d for topic '%s': %s", i, topic, exc)

        if missing:
            logger.warning("Quick Picks bank missing/insufficient topics: %s", missing)

        _bank_cache = raw
        logger.info(
            "Quick Picks bank loaded: %d topics, %d total questions",
            len(raw),
            sum(len(v) for v in raw.values() if isinstance(v, list)),
        )
        return _bank_cache


def get_quick_pick_questions(topic: str, count: int = 10) -> list[Question]:
    """
    Return randomized static questions for a Quick Pick topic.

    Raises ValueError if the bank is unavailable or the topic has too few
    questions — the caller (websocket.py) catches this and falls back to
    Gemini generation so the game still starts.

    The recent-question tracker avoids repeats while enough unseen questions
    remain available. With ≥50 questions per topic this makes consecutive
    games feel fresh without per-user history or AI calls.
    """
    canonical = canonical_quick_pick_topic(topic)
    if not canonical:
        raise ValueError(f"Unknown Quick Picks topic: {topic!r}")

    bank = _load_bank()
    rows = bank.get(canonical, [])

    if len(rows) < count:
        raise ValueError(
            f"Quick Picks topic '{canonical}' has {len(rows)} questions, need {count}. "
            "Falling back to Gemini."
        )

    with _lock:
        recent     = _recent_questions[canonical]
        recent_set = set(recent)

        # Deduplicate rows by question text before anything else —
        # guards against duplicate entries in the JSON bank.
        seen_texts: set[str] = set()
        deduped: list[dict] = []
        for row in rows:
            q = row.get("question", "")
            if q not in seen_texts:
                seen_texts.add(q)
                deduped.append(row)

        fresh  = [row for row in deduped if row["question"] not in recent_set]
        pool   = fresh if len(fresh) >= count else deduped
        selected = random.sample(pool, count)
        for row in selected:
            recent.append(row["question"])
        return [Question(**row) for row in selected]