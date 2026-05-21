"""
app/core/state.py — In-memory game state manager.

WHY in-memory instead of Redis?
  - Redis costs money and adds complexity. Cloud Run's free tier doesn't include it.
  - For a mobile game, rooms are short-lived (minutes). We don't need persistence.
  - A single FastAPI instance can handle hundreds of concurrent WS connections easily.

TRADEOFF to understand:
  - If the Cloud Run instance restarts, ALL active rooms are wiped.
  - Cloud Run tries to keep one instance alive if there's traffic.
  - This is acceptable for an MVP. Future fix: Cloud Firestore free tier.

DATA STRUCTURE:
  rooms: dict[str, Room]
    key = 4-digit room code (e.g. "4823")
    value = Room dataclass (defined in models/quiz.py)
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.quiz import Room


class GameState:
    """Singleton that holds all active game rooms in memory."""

    def __init__(self):
        # The entire game state lives here.
        # Key: room_code (str), Value: Room object
        self.rooms: dict[str, "Room"] = {}

    def add_room(self, room: "Room") -> None:
        self.rooms[room.code] = room

    def get_room(self, code: str) -> "Room | None":
        return self.rooms.get(code)

    def remove_room(self, code: str) -> None:
        self.rooms.pop(code, None)

    def room_exists(self, code: str) -> bool:
        return code in self.rooms


# Module-level singleton — import `game_state` everywhere, never re-create it.
# WHY module-level? Python caches module imports, so this object is shared
# across all coroutines in the same process — exactly what we need.
game_state = GameState()