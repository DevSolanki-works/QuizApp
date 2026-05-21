"""
app/models/quiz.py — All Pydantic data models for Forge.

WHY Pydantic?
  1. VALIDATION: If Gemini returns a bad response, Pydantic raises a clear error
     instead of letting bad data silently corrupt our game state.
  2. STRUCTURED OUTPUTS: We'll tell Gemini to match this exact schema.
  3. SERIALIZATION: .model_dump() gives us clean dicts ready to send over WebSocket.

TWO CATEGORIES of models here:
  A) AI-output models: What we expect from Gemini (Question, Quiz)
  B) Game-state models: What we store in memory (Player, Room)
"""

from dataclasses import dataclass, field
from enum import Enum
from fastapi import WebSocket
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# A) AI OUTPUT MODELS (Pydantic — for validation)
# ─────────────────────────────────────────────

class Question(BaseModel):
    """One quiz question as returned by Gemini."""
    question: str = Field(..., description="The question text")
    options: list[str] = Field(..., min_length=4, max_length=4, description="Exactly 4 answer choices")
    correct_index: int = Field(..., ge=0, le=3, description="Index of the correct option (0-3)")


class Quiz(BaseModel):
    """A full 10-question quiz as returned by Gemini."""
    questions: list[Question] = Field(..., min_length=1, max_length=10)


# ─────────────────────────────────────────────
# B) GAME STATE MODELS (dataclasses — lightweight, mutable)
# WHY dataclasses here instead of Pydantic?
#   - Game state is mutable (scores change constantly).
#   - We don't need validation on internal state — only on external input (AI / WS messages).
#   - Dataclasses are faster and simpler for plain data containers.
# ─────────────────────────────────────────────

class RoomStatus(str, Enum):
    WAITING = "waiting"       # Room created, not enough players or host hasn't started
    IN_GAME = "in_game"       # Game is active
    FINISHED = "finished"     # All questions answered, showing results


@dataclass
class Player:
    name: str
    websocket: WebSocket
    score: int = 0
    answered_current: bool = False  # Has this player answered the current question?


@dataclass
class Room:
    code: str
    host_name: str
    status: RoomStatus = RoomStatus.WAITING

    # Players dict: name → Player object
    players: dict[str, Player] = field(default_factory=dict)

    # Quiz data (populated when game starts)
    questions: list[Question] = field(default_factory=list)
    current_question_index: int = 0

    def get_scores(self) -> dict[str, int]:
        """Return a clean {name: score} dict ready to broadcast."""
        return {name: p.score for name, p in self.players.items()}

    def all_answered(self) -> bool:
        """Check if every connected player has answered the current question."""
        return all(p.answered_current for p in self.players.values())

    def reset_answers(self) -> None:
        """Clear answered flags before a new question starts."""
        for player in self.players.values():
            player.answered_current = False


# ─────────────────────────────────────────────
# C) WEBSOCKET MESSAGE SCHEMAS (for incoming client messages)
# ─────────────────────────────────────────────

class StartGameAction(BaseModel):
    action: str  # Must be "start_game"
    topic: str = Field(..., min_length=2, max_length=100)


class AnswerAction(BaseModel):
    action: str  # Must be "answer"
    choice: int = Field(..., ge=0, le=3)
    time_ms: int = Field(..., ge=0, le=20000)