"""Static Quick Picks question bank for no-cost generated Solo topics."""

from __future__ import annotations

import json
import random
from collections import defaultdict, deque
from pathlib import Path
from threading import RLock
from typing import Any

from app.models.quiz import Question

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
_recent_questions: dict[str, deque[str]] = defaultdict(lambda: deque(maxlen=120))


def _normalise_topic(topic: str) -> str:
    """Return a comparison-safe topic key."""

    return " ".join(str(topic or "").strip().lower().replace("&", "and").split())


_TOPIC_ALIASES = {_normalise_topic(topic): topic for topic in QUICK_PICK_TOPICS}
_TOPIC_ALIASES.update({
    "ai and tech": "AI & Tech",
    "space and astronomy": "Space & Astronomy",
    "geography": "World Geography",
    "world geography": "World Geography",
    "general knowledge": "General Knowledge",
})


def canonical_quick_pick_topic(topic: str) -> str | None:
    """Return the canonical Quick Pick topic name, if this topic is static."""

    return _TOPIC_ALIASES.get(_normalise_topic(topic))


def is_quick_pick_topic(topic: str) -> bool:
    """Return whether the topic should use the static Quick Picks bank."""

    return canonical_quick_pick_topic(topic) is not None


def _load_bank() -> dict[str, list[dict[str, Any]]]:
    """Load and validate the Quick Picks bank once per process."""

    global _bank_cache
    if _bank_cache is not None:
        return _bank_cache

    with _lock:
        if _bank_cache is not None:
            return _bank_cache
        with open(_BANK_PATH, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        if not isinstance(raw, dict):
            raise ValueError("Quick Picks bank must be a category object.")
        for topic in QUICK_PICK_TOPICS:
            rows = raw.get(topic)
            if not isinstance(rows, list):
                raise ValueError(f"Missing Quick Picks topic: {topic}")
            for item in rows:
                Question(**item)
        _bank_cache = raw
        return _bank_cache


def get_quick_pick_questions(topic: str, count: int = 10) -> list[Question]:
    """
    Return randomized static questions for a Quick Pick topic.

    The recent-question tracker avoids repeats while enough unseen questions are
    available. With a large bank this makes consecutive games feel fresh without
    needing persistent per-user history or AI calls.
    """

    canonical = canonical_quick_pick_topic(topic)
    if not canonical:
        raise ValueError(f"Unknown Quick Picks topic: {topic}")

    bank = _load_bank()
    rows = bank.get(canonical, [])
    if len(rows) < count:
        raise ValueError(f"Quick Picks topic '{canonical}' needs at least {count} questions.")

    with _lock:
        recent = _recent_questions[canonical]
        recent_set = set(recent)
        fresh = [row for row in rows if row["question"] not in recent_set]
        pool = fresh if len(fresh) >= count else rows
        selected = random.sample(pool, count)
        for row in selected:
            recent.append(row["question"])
        return [Question(**row) for row in selected]
