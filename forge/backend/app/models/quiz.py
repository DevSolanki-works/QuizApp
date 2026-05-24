"""
Pydantic models for Forge: AI Trivia Showdown.
Defines all data structures used across the game loop.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import WebSocket


class GameStatus(str, Enum):
    """Represents the current state of a game room."""
    WAITING   = "WAITING"    # Room created, waiting for players
    STARTING  = "STARTING"   # Host triggered start, AI generating questions
    ACTIVE    = "ACTIVE"     # Game in progress
    FINISHED  = "FINISHED"   # Game over


class Difficulty(str, Enum):
    """Difficulty level for AI-generated questions."""
    EASY   = "easy"    # Common knowledge, straightforward questions
    MEDIUM = "medium"  # Balanced — default behaviour
    HARD   = "hard"    # Specific, tricky, expert-level questions


class Question(BaseModel):
    """A single trivia question with 4 options and a correct answer index."""
    question:      str
    options:       list[str] = Field(..., min_length=4, max_length=4)
    correct_index: int = Field(..., ge=0, le=3)


class Player(BaseModel):
    """
    Represents a connected player in a room.
    The websocket field is excluded from JSON serialization so it
    never leaks into broadcast messages.
    """
    name:        str
    score:       int = 0
    answered:    bool = False
    last_answer: Optional[int] = None
    websocket:   Optional[WebSocket] = Field(default=None, exclude=True)

    class Config:
        # Allow arbitrary types so WebSocket can be stored on the model
        arbitrary_types_allowed = True


class Room(BaseModel):
    """
    Full state of a game room, stored in memory.
    One Room object per active 4-digit room code.
    """
    code:               str
    host:               str
    status:             GameStatus = GameStatus.WAITING
    players:            dict[str, Player] = {}
    questions:          list[Question] = []
    current_q_index:    int = 0
    answers_this_round: dict[str, int] = {}

    # ── New configurable fields ──────────────────────────────────────────────
    difficulty:       Difficulty = Difficulty.MEDIUM   # Easy / Medium / Hard
    total_questions:  int = Field(default=10, ge=5, le=20)  # 5–20 questions
    time_limit_ms:    int = 30000  # 30 seconds per question (was 15s)

    class Config:
        arbitrary_types_allowed = True
