"""
Pydantic models for Forge game entities.

Rooms and players live in memory for the duration of an active game.
Question objects validate structured AI output before it enters the game loop.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class GameStatus(str, Enum):
    """Lifecycle states a room can be in."""

    WAITING = "waiting"
    STARTING = "starting"
    ACTIVE = "active"
    FINISHED = "finished"


class GameMode(str, Enum):
    """Difficulty presets that set the question countdown duration."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class PlayMode(str, Enum):
    """Competition formats supported by a room."""

    SOLO = "solo"
    CLASSIC = "classic"
    TEAM = "team"


class RoundPhase(str, Enum):
    """Presentation state for the active round."""

    LOBBY = "lobby"
    QUESTION = "question"
    ANSWER_REVEAL = "answer_reveal"
    INTERMISSION_LEADERBOARD = "intermission_leaderboard"
    COMPLETE = "complete"


TIME_LIMIT_MS_BY_MODE = {
    GameMode.EASY: 30000,
    GameMode.MEDIUM: 20000,
    GameMode.HARD: 10000,
}

DEFAULT_GAME_MODE = GameMode.MEDIUM
DEFAULT_PLAY_MODE = PlayMode.CLASSIC


def time_limit_for_mode(mode: str | GameMode) -> int:
    """Return the round timer for the selected difficulty."""

    try:
        value = mode.value if isinstance(mode, GameMode) else str(mode).lower()
        return TIME_LIMIT_MS_BY_MODE[GameMode(value)]
    except (TypeError, ValueError):
        return TIME_LIMIT_MS_BY_MODE[DEFAULT_GAME_MODE]


class Question(BaseModel):
    """A single validated quiz question."""

    question: str = Field(..., description="The question text")
    options: list[str] = Field(..., min_length=4, max_length=4)
    correct_index: int = Field(..., ge=0, le=3)


class Player(BaseModel):
    """Represents one connected player in a room."""

    name: str
    score: int = 0
    correct_answers: int = 0
    streak: int = 0          # consecutive correct answers; resets on wrong/timeout
    answered: bool = False
    last_answer: Optional[int] = None
    websocket: Optional[object] = Field(default=None, exclude=True)

    model_config = {"arbitrary_types_allowed": True}


class Room(BaseModel):
    """The full in-memory state of one game room."""

    code: str
    host: str
    status: GameStatus = GameStatus.WAITING
    play_mode: PlayMode = DEFAULT_PLAY_MODE
    mode: GameMode = DEFAULT_GAME_MODE
    time_limit_ms: int = TIME_LIMIT_MS_BY_MODE[DEFAULT_GAME_MODE]
    phase: RoundPhase = RoundPhase.LOBBY
    players: dict[str, Player] = Field(default_factory=dict)
    questions: list[Question] = Field(default_factory=list)
    current_q_index: int = 0
    answers_this_round: dict[str, int] = Field(default_factory=dict)
    points_gained: dict[str, int] = Field(default_factory=dict)
    locked: bool = False  # If True, no more players can join

    # ── Team mode fields ───────────────────────────────────────────────────────
    # teams: { player_name → team_id }  where team_id is "A" or "B"
    teams: dict[str, str] = Field(default_factory=dict)
    # team_names: { "A" → "Red Dragons", "B" → "Blue Phoenix" }
    team_names: dict[str, str] = Field(
        default_factory=lambda: {"A": "Team A", "B": "Team B"}
    )
    # team_topics: { "A" → "Marvel Movies", "B" → "Cricket" }
    # Host triggers a random pick; the winner becomes room.topic
    team_topics: dict[str, str] = Field(default_factory=dict)
    # The resolved topic after randomisation (also used by classic/solo)
    topic: str = ""

    model_config = {"arbitrary_types_allowed": True}
