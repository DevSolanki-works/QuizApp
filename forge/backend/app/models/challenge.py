"""
Pydantic model for Async Challenge Mode (Online Duel — Phase 1).

A Challenge freezes a completed Solo game's question set under a short
code so a friend can play the identical quiz and have their score
compared against the original player's. Deliberately isolated from the
live economy — no coins, trophies, or tickets are touched by anything
in this module.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.models.quiz import GameMode, Question


class Challenge(BaseModel):
    """A frozen Solo question set, playable once by a challenger within 24h."""

    code: str
    creator_name: str
    creator_user_id: Optional[str] = None
    topic: str
    mode: GameMode
    time_limit_ms: int
    questions: list[Question] = Field(default_factory=list)

    creator_score: int
    creator_correct_answers: int

    created_at: float
    expires_at: float

    challenger_name: Optional[str] = None
    challenger_user_id: Optional[str] = None
    challenger_score: Optional[int] = None
    challenger_correct_answers: Optional[int] = None
    completed_at: Optional[float] = None

    model_config = {"arbitrary_types_allowed": True}

    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None