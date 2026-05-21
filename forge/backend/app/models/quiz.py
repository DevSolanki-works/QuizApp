"""
quiz.py — Pydantic data models for Forge.

WHY PYDANTIC:
  - Validates Gemini's JSON output at the boundary — if AI hallucinates a bad
    structure we get a clear ValidationError instead of a cryptic KeyError later.
  - Auto-generates JSON schemas which serve as implicit API docs.
  - All models are immutable-friendly (use model_copy() to update).
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from fastapi import WebSocket
from pydantic import BaseModel, Field, field_validator


# ── Question (Gemini output unit) ────────────────────────────────────────────

class Question(BaseModel):
    """
    One quiz question as returned by Gemini (after JSON parsing).
    correct_index is 0-based: 0=A, 1=B, 2=C, 3=D.
    """
    question: str
    options: List[str] = Field(..., min_length=4, max_length=4)
    correct_index: int = Field(..., ge=0, le=3)

    @field_validator("options")
    @classmethod
    def options_must_have_four(cls, v: List[str]) -> List[str]:
        """Gemini occasionally returns 3 or 5 options — reject early."""
        if len(v) != 4:
            raise ValueError(f"Expected 4 options, got {len(v)}")
        return v


# ── Room state machine ────────────────────────────────────────────────────────

class RoomStatus(str, Enum):
    """
    Lifecycle of a game room.
    LOBBY  → players joining, waiting for host to start
    ACTIVE → questions are being served
    DONE   → game finished, scores final
    """
    LOBBY = "lobby"
    ACTIVE = "active"
    DONE = "done"


class Player(BaseModel):
    """
    Represents one connected player.
    The WebSocket object is excluded from serialisation (it can't be JSON-ified).
    """
    name: str
    score: int = 0
    answered_current: bool = False   # reset each question
    # websocket is stored but not part of any JSON output
    websocket: Optional[object] = Field(default=None, exclude=True)

    model_config = {"arbitrary_types_allowed": True}


class Room(BaseModel):
    """
    Everything the server needs to run one game session.

    questions       — populated when host calls start_game
    current_q_index — which question we're on (0-based)
    host_name       — first player to join; only they can start the game
    """
    code: str                                    # "1234"
    status: RoomStatus = RoomStatus.LOBBY
    host_name: str = ""
    topic: str = ""
    players: Dict[str, Player] = Field(default_factory=dict)   # keyed by name
    questions: List[Question] = Field(default_factory=list)
    current_q_index: int = 0

    model_config = {"arbitrary_types_allowed": True}

    # ── Helpers ───────────────────────────────────────────────────────────────

    def add_player(self, name: str, websocket: object) -> Player:
        """Register a new player (or reconnect an existing one)."""
        player = Player(name=name, websocket=websocket)
        self.players[name] = player
        if not self.host_name:
            self.host_name = name   # first joiner is host
        return player

    def remove_player(self, name: str) -> None:
        """Remove a player on disconnect."""
        self.players.pop(name, None)

    def all_answered(self) -> bool:
        """True when every connected player has submitted an answer."""
        return all(p.answered_current for p in self.players.values())

    def reset_answers(self) -> None:
        """Clear per-question answer flags before sending next question."""
        for player in self.players.values():
            player.answered_current = False

    def active_websockets(self) -> list:
        """Return all live WebSocket connections in this room."""
        return [p.websocket for p in self.players.values() if p.websocket]

    @property
    def current_question(self) -> Optional[Question]:
        """The question currently being played, or None if not started."""
        if self.questions and 0 <= self.current_q_index < len(self.questions):
            return self.questions[self.current_q_index]
        return None

