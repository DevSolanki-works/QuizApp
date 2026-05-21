"""
state.py — Global in-memory game state.

WHY A PLAIN DICT instead of a database:
  - $0 infrastructure requirement. No Redis, no Postgres.
  - All game state is ephemeral: a room lives ~15 minutes then is irrelevant.
  - FastAPI runs in a single process (uvicorn), so one dict is shared by every
    request handler and WebSocket coroutine inside that process.
  - Cloud Run scale-to-zero resets state — acceptable for MVP (all players
    reconnect on the same container via sticky sessions or simply start a new room).

Structure of `rooms`:
  {
    "1234": Room(...)   # keyed by the 4-digit room code string
  }
"""

from typing import Dict
from app.models.quiz import Room

# The one and only source of truth for all active game rooms.
# Every router and service imports this dict by reference.
rooms: Dict[str, Room] = {}