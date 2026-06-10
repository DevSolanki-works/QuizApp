"""
sanitize.py — Input validation and sanitization for WebSocket messages.

WHY THIS MODULE EXISTS
======================
WebSocket messages arrive as raw JSON from the client. Even with Pydantic
models guarding the REST API, the WS endpoint processes messages manually
via a dict-based switch. This module centralises all input cleaning so
every field has a single, auditable validation path.

Key threats addressed:
  - Type confusion: sending {"action": {"$ne": null}} instead of a string
  - Topic prompt injection: trying to hijack the Gemini prompt via the topic
  - Oversized payloads that could bloat in-memory state
  - Control character injection in display strings
"""

import re
import unicodedata

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_TOPIC_LEN   = 60
MAX_NAME_LEN    = 20
MAX_TEAM_NAME   = 20
MAX_ACTION_LEN  = 32   # longest valid action string is "intermission_leaderboard" (24)

# Phrases that attempt to hijack the Gemini prompt.
# We block the room start rather than silently stripping — the host will see
# an error and can pick a real topic.
_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous|above|prior)\s+instructions?", re.I),
    re.compile(r"forget\s+(all\s+)?(previous|above|prior)\s+instructions?", re.I),
    re.compile(r"you\s+are\s+now", re.I),
    re.compile(r"system\s*:", re.I),
    re.compile(r"<\s*system\s*>", re.I),
    re.compile(r"act\s+as\s+", re.I),
    re.compile(r"disregard\s+", re.I),
    re.compile(r"jailbreak", re.I),
    re.compile(r"DAN\b"),          # "Do Anything Now" jailbreak keyword
    re.compile(r"prompt\s+injection", re.I),
]

# Valid action names — an explicit allowlist is safer than a blocklist
VALID_ACTIONS: frozenset[str] = frozenset({
    "start_game",
    "answer",
    "join_team",
    "set_team_info",
    "set_lobby_mode",
    "lock_room",
    "unlock_room",
})


# ── Public helpers ─────────────────────────────────────────────────────────────

def sanitize_string(value: object, max_len: int = 100) -> str:
    """
    Coerce a value to a clean string.

    - Non-string types (dict, list, int…) are rejected → returns ""
    - Unicode control characters are stripped
    - Leading/trailing whitespace removed
    - Truncated to max_len
    """
    if not isinstance(value, str):
        return ""
    # Strip Unicode control characters (category "C" covers Cc, Cf, Cs, Co, Cn)
    cleaned = "".join(
        ch for ch in value
        if unicodedata.category(ch)[0] != "C"
    )
    return cleaned.strip()[:max_len]


def validate_action(raw: object) -> str | None:
    """
    Return the action string if it's in the allowlist, else None.
    Rejects non-string types, oversized strings, and unknown actions.
    """
    if not isinstance(raw, str):
        return None
    action = raw.strip()[:MAX_ACTION_LEN]
    return action if action in VALID_ACTIONS else None


def validate_topic(raw: object) -> tuple[str, str | None]:
    """
    Validate and clean a quiz topic string.

    Returns (cleaned_topic, error_message).
    If error_message is not None, the topic should be rejected.

    Checks (in order):
      1. Must be a string
      2. Must not be empty after cleaning
      3. Must not contain prompt-injection patterns
      4. Truncated to MAX_TOPIC_LEN
    """
    if not isinstance(raw, str):
        return "", "Topic must be a string."

    topic = sanitize_string(raw, MAX_TOPIC_LEN)

    if not topic:
        return "", "Topic cannot be empty."

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(topic):
            return "", "Topic contains disallowed content. Please choose a real trivia subject."

    return topic, None


def validate_choice(raw: object) -> int | None:
    """
    Validate an answer choice. Must be an integer 0–3.
    Returns None if invalid (do NOT default to 0 — that would auto-answer).
    """
    if not isinstance(raw, int) or isinstance(raw, bool):
        return None
    return raw if raw in (0, 1, 2, 3) else None


def validate_time_ms(raw: object, time_limit_ms: int) -> int:
    """
    Validate a client-reported answer time in milliseconds.

    Clamps to [0, time_limit_ms + 500ms grace] to prevent:
      - Negative times (impossible, likely spoofed)
      - Times way beyond the limit (another spoof vector)
    The 500ms grace window accommodates network latency on the final tick.
    """
    try:
        ms = int(raw)
    except (TypeError, ValueError):
        return time_limit_ms  # treat as slowest possible — no bonus

    return max(0, min(ms, time_limit_ms + 500))


def validate_team_id(raw: object) -> str | None:
    """Return 'A' or 'B', or None if invalid."""
    if not isinstance(raw, str):
        return None
    tid = raw.strip().upper()
    return tid if tid in ("A", "B") else None


def validate_play_mode(raw: object, allowed: tuple[str, ...] = ("classic", "team", "solo")) -> str | None:
    """Return the play mode string if valid, else None."""
    if not isinstance(raw, str):
        return None
    mode = raw.strip().lower()
    return mode if mode in allowed else None


def validate_game_mode(raw: object, allowed: tuple[str, ...] = ("easy", "medium", "hard")) -> str | None:
    """Return the difficulty mode string if valid, else None."""
    if not isinstance(raw, str):
        return None
    mode = raw.strip().lower()
    return mode if mode in allowed else None


