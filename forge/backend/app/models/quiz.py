"""
Pydantic models for Forge's game entities.

Why Pydantic?
- Auto-validates data from Gemini (catches malformed AI output early)
- Gives us typed, IDE-friendly objects instead of raw dicts
- .model_dump() makes JSON serialization trivial for WS messages
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import WebSocket


class GameStatus(str, Enum):
    """Lifecycle states a room can be in."""
    WAITING   = "waiting"    # Created, host hasn't started yet
    STARTING  = "starting"   # AI is generating questions
    ACTIVE    = "active"     # Quiz is in progress
    FINISHED  = "finished"   # All questions done


class Question(BaseModel):
    """A single quiz question as returned (and validated) from Gemini."""
    question:      str           = Field(..., description="The question text")
    options:       list[str]     = Field(..., min_length=4, max_length=4)
    correct_index: int           = Field(..., ge=0, le=3)


class Player(BaseModel):
    """Represents one connected player in a room."""
    name:            str
    score:           int = 0
    answered:        bool = False   # Has this player answered the CURRENT question?
    last_answer:     Optional[int] = None   # Index they chose (for showing correct/wrong)

    # WebSocket connection — excluded from JSON serialization
    # (WebSocket objects can't be serialised; we manage them separately)
    websocket: Optional[object] = Field(default=None, exclude=True)

    model_config = {"arbitrary_types_allowed": True}


class Room(BaseModel):
    """
    The full state of one game room.

    Lives entirely in memory (state.rooms dict). No DB writes.
    One Room = one 4-digit code = one game session.
    """
    code:             str
    host:             str                        # Player name of whoever created the room
    status:           GameStatus = GameStatus.WAITING
    players:          dict[str, Player] = {}     # keyed by player name
    questions:        list[Question] = []
    current_q_index:  int = 0                    # Which question is active right now
    answers_this_round: dict[str, int] = {}      # name → choice index for current Q

    model_config = {"arbitrary_types_allowed": True}
