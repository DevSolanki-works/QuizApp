"""
Global in-memory state for Forge.

WHY a module-level singleton?
FastAPI runs in a single process (one Uvicorn worker for our use case).
A plain Python dict at module level is shared across ALL async handlers
in that process — no locking needed for our read/write patterns since
Python's GIL protects dict operations, and our game logic is sequential
per room (one question resolved before the next begins).

⚠️  State is lost on container restart — acceptable for MVP.
"""

from app.models.quiz import Room

# Master rooms registry: { "1234": Room(...), "5678": Room(...) }
rooms: dict[str, Room] = {}
