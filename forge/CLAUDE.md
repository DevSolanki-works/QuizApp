# CLAUDE.md — Forge: AI Trivia Showdown
> Paste this file at the start of every new conversation so Claude has full context.
> Claude updates this file after every major milestone and provides the new version.

---

## 🧠 Who I Am
- 2nd-year CS AI/ML student (strong Python, learning full-stack)
- Building this over a 1-month vacation
- Goal: deploy to Google Play Store + monetize
- Device: ARM64 architecture machine
- Dev environment: WSL (Ubuntu) on Windows, venv at backend/.venv

## 🎮 Project: Forge — AI Trivia Showdown
A real-time multiplayer mobile quiz game. Players enter ANY topic → AI generates a
quiz → players compete live via WebSockets using a 4-digit room code.

---

## 🏗️ Tech Stack (LOCKED — do not suggest changes)

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | HTML5 + Tailwind CSS + Vanilla JS | Stays portable for CapacitorJS wrapping |
| Mobile Wrapper | CapacitorJS → Android .aab | $0 — no React Native licenses |
| Backend | Python + FastAPI | Student knows Python well |
| AI | Gemini 2.0 Flash (`google-generativeai`) | $0 free tier, structured outputs |
| Real-time | FastAPI WebSockets | Built-in, no extra infra |
| State | In-memory Python dicts | $0 — NO Redis, NO database |
| Deployment | Docker → Google Cloud Run | $0 free tier, scale-to-zero |

### ⚠️ Hard Constraints
- **$0 infrastructure** — never suggest Redis, paid DBs, paid queues, etc.
- **ARM64 dev machine** — all local Docker builds use `docker buildx` for multi-arch (linux/amd64 target)
- **No heavy ORM** — plain Python dicts for in-memory state only
- **Structured AI outputs** — always use Pydantic models to validate Gemini responses
- **Android only** — iOS requires Mac + Xcode + $99/year Apple Developer account; out of scope

---

## 📁 Project Structure

```
forge/
├── CLAUDE.md
├── package.json               ← Capacitor npm root ✅
├── capacitor.config.json      ← Capacitor config (web-dir: frontend) ✅
├── node_modules/              ← Capacitor + dependencies ✅
├── android/                   ← Native Android project (Android Studio) ✅
│   ├── app/
│   │   └── build/outputs/apk/debug/app-debug.apk   ← Sideloadable debug APK ✅
│   ├── build.gradle
│   ├── gradlew
│   └── ...
├── docs/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                ← FastAPI entry point ✅
│   ├── test_websocket.py      ← Full game loop test script ✅
│   └── app/
│       ├── core/
│       │   ├── config.py      ← Env vars, GEMINI_API_KEY ✅
│       │   └── state.py       ← In-memory rooms dict ✅
│       ├── models/
│       │   └── quiz.py        ← Pydantic models ✅ (updated v2)
│       ├── routers/
│       │   ├── http.py        ← REST endpoints ✅
│       │   └── websocket.py   ← WS game loop ✅ (updated v2)
│       └── services/
│           └── ai.py          ← Gemini AI service ✅ (updated v2)
└── frontend/
    ├── index.html             ← App shell, router, shared styles/utils ✅
    ├── privacy.html           ← Privacy Policy page ✅
    ├── about.html             ← About page ✅
    ├── ads.txt                ← AdSense ads.txt ✅
    └── screens/
        ├── home.html          ← Home screen ✅
        ├── lobby.html         ← Lobby screen ✅ (updated v2)
        ├── game.html          ← Game screen ✅
        └── results.html       ← Results screen ✅
```

---

## 🚀 Live Deployment

| Property | Value |
|----------|-------|
| Platform | Google Cloud Run (us-central1) |
| Service name | `forge-backend` |
| **Service URL** | `https://forge-backend-878124462453.us-central1.run.app` |
| **Website** | `https://forgetrivia.online` |
| Health check | `GET /health` |
| Image registry | Artifact Registry → `us-central1-docker.pkg.dev` |
| Min instances | 0 (scale to zero) |
| Max instances | 3 |
| Memory | 512Mi |
| Timeout | 300s (required for WebSocket sessions) |
| Workers | 1 (intentional — in-memory state must not split across workers) |

### Re-deploy command (for future updates)
```bash
# From backend/ directory
docker buildx build \
  --platform linux/amd64 \
  --tag us-central1-docker.pkg.dev/YOUR_PROJECT_ID/forge/backend:latest \
  --push \
  .

gcloud run deploy forge-backend \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/forge/backend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_key_here,GEMINI_MODEL=gemini-2.5-flash \
  --min-instances 0 \
  --max-instances 3 \
  --memory 512Mi \
  --timeout 300
```

### Update env vars only (no redeploy needed)
```bash
gcloud run services update forge-backend \
  --region us-central1 \
  --update-env-vars GEMINI_API_KEY=YOUR_NEW_KEY_HERE,GEMINI_MODEL=gemini-2.5-flash
```

### Re-sync frontend into Android after any HTML/JS changes
```bash
# From forge/ root
npx cap sync android
# Then rebuild APK in Android Studio: Build → Build Bundle(s)/APK(s) → Build APK(s)
```

### Frontend local dev
```bash
cd /mnt/c/QuizApp/forge/frontend
python3 -m http.server 8080
# Open http://localhost:8080
```

### ADB install via PowerShell (Windows)
```powershell
& "C:\Users\$env:USERNAME\AppData\Local\Android\Sdk\platform-tools\adb.exe" devices
& "C:\Users\$env:USERNAME\AppData\Local\Android\Sdk\platform-tools\adb.exe" install "C:\QuizApp\forge\android\app\build\outputs\apk\debug\app-debug.apk"
```

---

## 🔄 Core Game Loop (Server-side Truth)

```
1. POST /rooms/create        ✅
   → Server generates 4-digit alphanumeric code
   → Creates Room object in state.rooms dict
   → Returns { room_code, host_name, ws_url }

2. WS /ws/{room_code}/{player_name}   ✅
   → Player joins, server broadcasts PLAYER_JOINED to all in room

3. Host sends: { "action": "start_game", "topic": "Marvel Movies",
                 "difficulty": "hard", "total_questions": 15 }   ✅
   → Server calls Gemini → gets structured questions
   → Stores in room.questions
   → Broadcasts: GAME_STARTING + first QUESTION

4. Player sends: { "action": "answer", "choice": 2, "time_ms": 3400 }   ✅
   → Server validates answer
   → Calculates score: speed-based 500–1000 pts
   → Updates room.scores
   → When ALL players answered → broadcast LEADERBOARD + next QUESTION

5. After final question → broadcast GAME_OVER with final scores   ✅
```

---

## 📐 Scoring Formula
```python
BASE_POINTS = 1000
score = int(BASE_POINTS * (1 - (time_ms / time_limit_ms) * 0.5))
score = max(500, min(1000, score))   # Clamped 500–1000
# Wrong answer = 0 pts. Correct = 500–1000 pts depending on speed.
```

---

## 🎮 Game Configuration Options (v2)

| Option | Values | Default |
|--------|--------|---------|
| Difficulty | `easy` / `medium` / `hard` | `easy` |
| Questions | 5 / 10 / 15 / 20 | `10` |
| Timer | 30000ms (30 seconds) | `30000` |

---

## 🎨 UI/UX Design Language
- **Background**: Deep blue `#0D1B8E` with radial gradient to `#2540CC` at top
- **Primary accent**: Yellow `#FFD93D` — buttons, highlights, scores
- **Answer options**: Kahoot-style 4-colour grid — Red `#E63946` / Blue `#2196F3` / Green `#06D6A0` / Purple `#9B5DE5`
- **Difficulty colours**: Easy `#06D6A0` / Medium `#FFD93D` / Hard `#E63946`
- **Correct answer**: `#06D6A0` green glow
- **Wrong answer**: greyed out / dimmed
- **Pixel font**: `"Press Start 2P"` — ALL UI chrome
- **Body font**: `"Nunito"` (weight 700–900) — questions, answers, player names
- **Buttons**: Chunky 3D with thick bottom shadow that "presses" on tap
- **Mobile-first**: All tap targets ≥ 56px, max-width 430px centred

---

## 🖥️ Frontend Architecture

### Routing (SPA pattern)
- Single `index.html` shell — screens lazy-loaded from `screens/*.html`
- `goTo(name)` handles navigation + calls `onXxxShow()` hook
- No framework — pure vanilla JS

### Global Objects
| Object | Purpose |
|--------|---------|
| `State` | `playerName, roomCode, isHost, topic, ws, players, scores, totalQ, timeLimitMs` |
| `API`   | `createRoom()`, `getRoom()`, `health()` |
| `WS`    | `connect()`, `send()`, `on(type,fn)`, `off(type)` |
| `Toast` | `Toast.error()`, `.success()`, `.info()` |
| `goTo(name)` | Screen router |

### Screen Flow
```
home.html → lobby.html → game.html → results.html
               ↑                           ↓
               └─────── Play Again ────────┘
```

---

## 🔌 WebSocket Message Protocol

### Server → Client
```json
{ "type": "PLAYER_JOINED",  "data": { "players": ["Alice", "Bob"] } }
{ "type": "GAME_STARTING",  "data": { "topic": "Marvel Movies", "total_questions": 10, "difficulty": "hard", "time_limit_ms": 30000 } }
{ "type": "QUESTION",       "data": { "index": 0, "text": "...", "options": ["A","B","C","D"], "time_limit_ms": 30000, "total": 10, "difficulty": "hard" } }
{ "type": "LEADERBOARD",    "data": { "scores": {"Alice": 2300, "Bob": 1800}, "correct_index": 2 } }
{ "type": "GAME_OVER",      "data": { "final_scores": {"Alice": 9100, "Bob": 7200} } }
{ "type": "ERROR",          "data": { "message": "Room not found" } }
```

### Client → Server
```json
{ "action": "start_game", "topic": "Quantum Physics", "difficulty": "hard", "total_questions": 15 }
{ "action": "answer",     "choice": 2, "time_ms": 3400 }
```

---

## 🤖 Gemini Config
- Model: `gemini-2.5-flash` (GEMINI_MODEL env var)
- max_output_tokens: 8192
- temperature: 0.8
- Difficulty injected into prompt via DIFFICULTY_PROMPTS dict in ai.py

---

## 🗄️ Data Models (app/models/quiz.py)

```
GameStatus  (Enum)    → WAITING | STARTING | ACTIVE | FINISHED
Difficulty  (Enum)    → easy | medium | hard          ← NEW
Question    (Model)   → question, options x4, correct_index
Player      (Model)   → name, score, answered, last_answer, websocket (excluded)
Room        (Model)   → code, host, status, players, questions,
                         current_q_index, answers_this_round,
                         difficulty, total_questions, time_limit_ms   ← NEW
```

---

## 🌐 REST API (app/routers/http.py)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe |
| POST | `/rooms/create` | Create room |
| GET | `/rooms/{code}` | Inspect room |
| DELETE | `/rooms/{code}` | Remove room |

---

## 💰 Monetization

| Channel | Status |
|---------|--------|
| Google AdSense | ✅ Applied — review pending (1–3 days) |
| AdSense code | Added to all 7 frontend HTML files |
| ads.txt | ✅ Live at forgetrivia.online/ads.txt |
| Identity verify (PAN) | ⏳ Physical PAN arriving in ~15 days — earnings accumulate until then |
| Play Store | ⏳ On hold until physical ID document available |

---

## ✅ Milestones Tracker

| # | Milestone | Status |
|---|-----------|--------|
| 1 | Project structure + CLAUDE.md | ✅ Done |
| 2 | Backend: FastAPI skeleton + health endpoint | ✅ Done |
| 3 | Backend: In-memory state + room creation | ✅ Done |
| 4 | Backend: Gemini AI service + Pydantic models | ✅ Done |
| 5 | Backend: WebSocket game loop (full) | ✅ Done |
| 6 | Backend: Docker + Cloud Run deployment | ✅ Done |
| 7 | Frontend: All 4 screens | ✅ Done |
| 8 | CapacitorJS setup → Android APK | ✅ Done |
| 9 | Website live at forgetrivia.online | ✅ Done |
| 10 | Google AdSense applied | ✅ Done |
| 11 | Game improvements: difficulty + question count + 30s timer | ✅ Done |
| 12 | Solo mode | 🔲 Next |
| 13 | Play Store submission | 🔲 Blocked (needs ID) |

---

## 🐛 Known Issues / Decisions Log
- Cloud Run scales to zero — ~2s cold start after idle. Mitigation: /health ping on app launch.
- In-memory state lost on container restart. Acceptable for MVP.
- ARM64 dev machine: always `docker buildx --platform linux/amd64 --push`.
- `Player.websocket` uses `exclude=True` — never leaks into JSON.
- Room codes: 4-char UPPERCASE alphanumeric (36^4 = ~1.6M possibilities).
- Gemini model: `gemini-2.0-flash` — `gemini-1.5-flash` returns 404.
- max_output_tokens must be 8192+ — 2048 causes JSON truncation.
- WebSocket test script must be event-driven, not sleep-based.
- Cloud Run timeout must be 300s — default 60s kills WS sessions.
- `--workers 1` is intentional — multiple workers split in-memory state.
- Frontend local dev: serve from frontend/ dir, open http://localhost:8080.
- Frontend bundled inside Android .aab via CapacitorJS — NOT deployed separately.
- WSL ADB cannot see USB devices — always use Windows PowerShell ADB.
- After any frontend change: `npx cap sync android` then rebuild APK.
- Gemini API key was exposed in git history on May 24 2026 — rotated and updated in Cloud Run.
- AdSense identity verification (PAN) pending — earnings accumulate, payouts unlock when verified.
- Timer increased from 15s to 30s per question for better UX.
- Difficulty levels: Easy (green) / Medium (yellow) / Hard (red) — colour-coded in UI.
- Question count: configurable 5/10/15/20 — sent by host in start_game action.

---

## 📝 Claude's Instructions
1. Always write **clean, commented code** with docstrings on every function.
2. Explain the **"why"** behind async/WebSocket logic.
3. Provide code in **modular chunks** — one file at a time.
4. After each major milestone, provide an **updated CLAUDE.md**.
5. Never suggest paid services. $0 constraint always applies.
6. ARM64 context: flag any ARM64 compat issues proactively.
7. When user pastes error output, fix root cause — don't patch symptoms.
8. Always assume existing files are correct unless user pastes them.
9. Frontend must point to live Cloud Run URL for all API/WS calls:
   `https://forge-backend-878124462453.us-central1.run.app`
10. Design language: blue/white quiz-game theme, Press Start 2P for UI chrome,
    Nunito for body text, yellow #FFD93D accent, Kahoot-style answer buttons.
    Do NOT revert to hacker/neon/dark theme.
11. ADB commands must use Windows PowerShell, not WSL terminal.
12. Website is live at forgetrivia.online — frontend deployed on Vercel,
    connected via Namecheap DNS (A record + CNAME to Vercel).