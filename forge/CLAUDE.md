# CLAUDE.md — Forge: AI Trivia Showdown
> Paste this file at the start of every new conversation so Claude has full context.
> Claude updates this file after every major milestone and provides the new version.

---

## 🧠 Who I Am
- 2nd-year CS AI/ML student (strong Python, learning full-stack)
- Building this over a 1-month vacation
- Goal: deploy to Google Play Store + monetize
- Device: ARM64 architecture machine

## 🎮 Project: Forge — AI Trivia Showdown
A real-time multiplayer mobile quiz game. Players enter ANY topic → AI generates a
10-question quiz → players compete live via WebSockets using a 4-digit room code.

---

## 🏗️ Tech Stack (LOCKED — do not suggest changes)

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | HTML5 + Tailwind CSS + Vanilla JS | Stays portable for CapacitorJS wrapping |
| Mobile Wrapper | CapacitorJS → Android .aab | $0 — no React Native licenses |
| Backend | Python + FastAPI | Student knows Python well |
| AI | Gemini 1.5 Flash (`google-genai`) | $0 free tier, structured outputs |
| Real-time | FastAPI WebSockets | Built-in, no extra infra |
| State | In-memory Python dicts | $0 — NO Redis, NO database |
| Deployment | Docker → Google Cloud Run | $0 free tier, scale-to-zero |

### ⚠️ Hard Constraints
- **$0 infrastructure** — never suggest Redis, paid DBs, paid queues, etc.
- **ARM64 dev machine** — all local Docker builds use `--platform linux/arm64` or multi-arch
- **No heavy ORM** — plain Python dicts for in-memory state only
- **Structured AI outputs** — always use Pydantic models to validate Gemini responses

---

## 📁 Project Structure

```
forge/
├── CLAUDE.md                  ← This file
├── docs/                      ← Architecture notes, API spec
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                ← FastAPI app entry point
│   └── app/
│       ├── core/
│       │   ├── config.py      ← Env vars, settings
│       │   └── state.py       ← In-memory game state (rooms dict)
│       ├── models/
│       │   └── quiz.py        ← Pydantic models (Question, Room, Player)
│       ├── routers/
│       │   ├── http.py        ← REST endpoints (create room, health)
│       │   └── websocket.py   ← WS endpoint + game loop logic
│       └── services/
│           └── ai.py          ← Gemini API call + structured output parsing
└── frontend/
    ├── index.html             ← App shell (loads Tailwind, all screens)
    ├── screens/
    │   ├── home.html          ← Landing: Create/Join buttons
    │   ├── lobby.html         ← Waiting room + room code display
    │   ├── game.html          ← Question display + answer buttons
    │   └── results.html       ← Final leaderboard
    ├── components/
    │   ├── timer.js           ← Countdown timer component
    │   └── leaderboard.js     ← Live score display component
    └── assets/
        ├── fonts/
        └── icons/
```

---

## 🔄 Core Game Loop (Server-side Truth)

```
1. POST /rooms/create
   → Server generates 4-digit code
   → Creates Room object in state.rooms dict
   → Returns { room_code, ws_url }

2. WS /ws/{room_code}/{player_name}
   → Player joins, server broadcasts PLAYER_JOINED to all in room

3. Host sends: { "action": "start_game", "topic": "Marvel Movies" }
   → Server calls Gemini → gets 10 structured questions
   → Stores in room.questions
   → Broadcasts: { "type": "QUESTION", "data": question_1, "index": 0 }

4. Player sends: { "action": "answer", "choice": 2, "time_ms": 3400 }
   → Server validates answer
   → Calculates score: base_pts - time_penalty
   → Updates room.scores
   → When ALL players answered → broadcast LEADERBOARD + next QUESTION

5. After Q10 → broadcast GAME_OVER with final scores
```

---

## 📐 Scoring Formula
```python
# Speed bonus: faster answer = more points
BASE_POINTS = 1000
TIME_LIMIT_MS = 15000
score = int(BASE_POINTS * (1 - (time_ms / TIME_LIMIT_MS) * 0.5))
# Wrong answer = 0 pts. Correct = 500–1000 pts depending on speed.
```

---

## 🎨 UI/UX Design Language
- **Background**: True black `#000000`
- **Primary accent**: Neon green `#00FF41` (Matrix green)
- **Secondary accent**: Neon cyan `#00D4FF`
- **Text**: `#E0E0E0` (light gray — NOT pure white)
- **Font**: `"Share Tech Mono"` (Google Fonts) — monospace hacker feel
- **Buttons**: Neon border glow effect, dark fill, uppercase text
- **Animations**: Subtle scanline effect on bg, glitch on transitions
- **Mobile-first**: All tap targets ≥ 48px, max-width 430px centered

---

## 🔌 WebSocket Message Protocol

### Server → Client messages
```json
{ "type": "PLAYER_JOINED",  "data": { "players": ["Alice", "Bob"] } }
{ "type": "GAME_STARTING",  "data": { "topic": "Marvel Movies", "total_questions": 10 } }
{ "type": "QUESTION",       "data": { "index": 0, "text": "...", "options": ["A","B","C","D"], "time_limit_ms": 15000 } }
{ "type": "LEADERBOARD",    "data": { "scores": {"Alice": 2300, "Bob": 1800}, "correct_index": 2 } }
{ "type": "GAME_OVER",      "data": { "final_scores": {"Alice": 9100, "Bob": 7200} } }
{ "type": "ERROR",          "data": { "message": "Room not found" } }
```

### Client → Server messages
```json
{ "action": "start_game", "topic": "Quantum Physics" }
{ "action": "answer",     "choice": 2, "time_ms": 3400 }
```

---

## 🤖 Gemini Prompt Strategy
```python
SYSTEM_PROMPT = """
You are a quiz generator. Return ONLY a JSON array of exactly 10 objects.
Each object: {"question": str, "options": [str, str, str, str], "correct_index": int (0-3)}
No markdown, no explanation, just the raw JSON array.
Topic: {topic}
Difficulty: medium. Make questions interesting and specific, not generic.
"""
```

---

## ✅ Milestones Tracker

| # | Milestone | Status |
|---|-----------|--------|
| 1 | Project structure + CLAUDE.md | ✅ Done |
| 2 | Backend: FastAPI skeleton + health endpoint | 🔲 Next |
| 3 | Backend: In-memory state + room creation | 🔲 |
| 4 | Backend: Gemini AI service + Pydantic models | 🔲 |
| 5 | Backend: WebSocket game loop (full) | 🔲 |
| 6 | Backend: Docker + Cloud Run deployment | 🔲 |
| 7 | Frontend: Home + Lobby screens | 🔲 |
| 8 | Frontend: Game screen + timer | 🔲 |
| 9 | Frontend: Results + leaderboard | 🔲 |
| 10 | CapacitorJS → .aab build | 🔲 |
| 11 | Play Store submission | 🔲 |

---

## 🐛 Known Issues / Decisions Log
- Cloud Run scales to zero — first request after idle has ~2s cold start.
  → Mitigation: show a "Connecting..." screen on app launch that pings /health
- In-memory state is lost on container restart.
  → Acceptable for MVP. Future: Cloud Firestore free tier if needed.
- ARM64 dev machine: always use `docker buildx` for multi-arch images.

---

## 📝 Claude's Instructions
1. Always write **clean, commented code** with docstrings on every function.
2. Explain the **"why"** behind async/WebSocket logic.
3. Provide code in **modular chunks** — one file or one concept at a time.
4. After each major milestone completion, provide an **updated CLAUDE.md**.
5. Never suggest paid services. Remind about $0 constraint if tempted.
6. ARM64 context: flag any library with ARM64 compat issues proactively.
