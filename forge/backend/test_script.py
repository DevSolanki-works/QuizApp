"""
Tests app/models/quiz.py and app/core/state.py
"""
from app.models.quiz import Question, Player, Room, GameStatus
from app.core.state import rooms

print("--- Models ---")

# Question model
q = Question(
    question="What is 2+2?",
    options=["1", "2", "3", "4"],
    correct_index=3
)
print(f"Question OK: {q.question}")

# Player model
p = Player(name="Alice")
print(f"Player OK: name={p.name}, score={p.score}")

# Room model
r = Room(code="TEST", host="Alice")
print(f"Room OK: code={r.code}, status={r.status}")

print("\n--- State ---")

# Add a room to global state
rooms["TEST"] = r
print(f"Room stored: {rooms['TEST'].code}")

# Add player to room
rooms["TEST"].players["Alice"] = p
print(f"Player in room: {list(rooms['TEST'].players.keys())}")

# Check default status
assert r.status == GameStatus.WAITING, "Status should be WAITING"
print(f"Status OK: {r.status}")

print("\n✅ All good — ready for Milestone 5")