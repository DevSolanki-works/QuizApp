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
| AI | Gemini Flash 1.5 8B (`google-generativeai`) | $0 free tier, with local fallback if unavailable |
| Real-time | FastAPI WebSockets | Built-in, no extra infra |
| State | In-memory Python dicts | $0 — NO Redis, NO database |
| Deployment | Docker → Google Cloud Run | $0 free tier, scale-to-zero |

### ⚠️ Hard Constraints
- **$0 infrastructure** — never suggest Redis, paid DBs, paid queues, etc.
- **ARM64 dev machine** — all local Docker builds use `docker buildx` for multi-arch (linux/amd64 target)
- **No heavy ORM** — plain Python dicts for in-memory state only
- **Structured AI outputs** — always validate Gemini responses with Pydantic
- **Backend must still boot without Gemini** — local fallback questions are acceptable for dev and crash recovery
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
    ├── sw.js                  ← Monetag Service Worker ✅
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
  --tag us-central1-docker.pkg.dev/quiz-app-forge/forge/backend:latest \
  --push \
  .

gcloud run deploy forge-backend \
  --image us-central1-docker.pkg.dev/quiz-app-forge/forge/backend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_key_here,GEMINI_MODEL=gemini-2.5-flash-lite,GOOGLE_CLIENT_ID=878124462453-g7skbojds4uqg442hb9d31ftrlll095r.apps.googleusercontent.com \
  --min-instances 0 \
  --max-instances 3 \
  --memory 512Mi \
  --timeout 300
```

### Update env vars only (no redeploy needed)
```bash
gcloud run services update forge-backend \
  --region us-central1 \
  --update-env-vars GEMINI_API_KEY=YOUR_NEW_KEY_HERE,GEMINI_MODEL=gemini-2.5-flash-lite,GOOGLE_CLIENT_ID=878124462453-g7skbojds4uqg442hb9d31ftrlll095r.apps.googleusercontent.com
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
# Open http://127.0.0.1:8080
```

Current frontend behavior:
- When opened from `localhost`, `127.0.0.1`, or `file:`, the app points to local backend `http://127.0.0.1:8000`.
- In production, it uses the Cloud Run backend URL.

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
                 "mode": "hard" }   ✅
   → Server sets timer from mode: Easy 30s, Medium 20s, Hard 10s
   → Server calls Gemini (or local fallback) → gets 10 questions
   → Stores in room.questions
   → Broadcasts: GAME_STARTING + first QUESTION

4. Player sends: { "action": "answer", "choice": 2, "time_ms": 3400 }   ✅
   → Server validates answer
   → Calculates score: speed-based 500–1000 pts using current mode timer
   → Updates room.scores
   → When ALL players answered:
     - broadcast ANSWER_REVEAL first
     - then broadcast LEADERBOARD
     - then next QUESTION after a short delay

5. After final question → broadcast GAME_OVER with final scores   ✅
```

---

## 📐 Scoring Formula
```python
BASE_POINTS = 1000
score = int(BASE_POINTS * (1 - (time_ms / time_limit_ms) * 0.5))
score = max(500, min(1000, score))   # Clamped 500–1000
# Streak/combo multiplier (streak resets on wrong answer or timeout)
multiplier = min(1.0 + (streak // 3) * 0.5, 3.0)
# streak 1–2 → ×1.0 | streak 3–5 → ×1.5 | streak 6–8 → ×2.0 | streak 9–11 → ×2.5 | streak 12+ → ×3.0
final_score = int(base_score * multiplier)
# Wrong answer or timeout = 0 pts, streak resets to 0.
```

---

## 🎮 Game Configuration Options (current)

| Option | Values | Default |
|--------|--------|---------|
| Mode | `easy` / `medium` / `hard` | `medium` |
| Questions | fixed `10` | `10` |
| Timer | `30000ms` / `20000ms` / `10000ms` | `20000ms` |

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
| `State` | `playerName, roomCode, isHost, topic, mode, timeLimitMs, ws, players, scores, totalQ` |
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

Lobby now only asks for topic + mode. Question count is fixed at 10.

---

## 🔌 WebSocket Message Protocol

### Server → Client
```json
{ "type": "PLAYER_JOINED",  "data": { "players": ["Alice", "Bob"] } }
{ "type": "GAME_STARTING",  "data": { "topic": "Marvel Movies", "mode": "hard", "total_questions": 10, "time_limit_ms": 10000 } }
{ "type": "QUESTION",       "data": { "index": 0, "text": "...", "options": ["A","B","C","D"], "time_limit_ms": 10000, "mode": "hard" } }
{ "type": "ANSWER_REVEAL",  "data": { "phase": "answer_reveal", "hold_ms": 4000, "correct_index": 2, "scores": {}, "points_gained": {}, "answers": {}, "streaks": {"Alice": 3, "Bob": 0}, "play_mode": "classic" } }
{ "type": "LEADERBOARD",    "data": { "scores": {"Alice": 2300, "Bob": 1800}, "correct_index": 2 } }
{ "type": "GAME_OVER",      "data": { "final_scores": {"Alice": 9100, "Bob": 7200} } }
{ "type": "ERROR",          "data": { "message": "Room not found" } }
```

### Client → Server
```json
{ "action": "start_game", "topic": "Quantum Physics", "mode": "hard" }
{ "action": "answer",     "choice": 2, "time_ms": 3400 }
```

---

## 🤖 Gemini Config
- Model: `GEMINI_MODEL` env var, default currently `gemini-2.5-flash-lite`
- max_output_tokens: 2048 in current service
- temperature: 0.8
- AI service falls back to local questions if Gemini cannot be imported or is not configured

---

## 🗄️ Data Models (app/models/quiz.py)

```
GameStatus  (Enum)    → WAITING | STARTING | ACTIVE | FINISHED
GameMode    (Enum)    → easy | medium | hard
Question    (Model)   → question, options x4, correct_index
Player      (Model)   → name, score, correct_answers, streak, answered, last_answer, websocket(excluded)
Room        (Model)   → code, host, status, mode, time_limit_ms,
                         players, questions, current_q_index,
                         answers_this_round
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
| Monetag Ads | ✅ Active (Vignette: End of Game | Popunder: Navigation | Banner: Top) |
| sw.js | ✅ Service Worker at `frontend/sw.js` (Zone: 11086444) |
| Layout | ✅ Persistent 60px Top Banner Header in `index.html` |
| Frequency | ✅ Once per quiz (Room-based tracking) |
| Identity verify | ⏳ Physical PAN arriving in ~15 days |
| Play Store | ⏳ On hold until physical ID document available |

---

## Milestone 19 - Monetag Strategic Integration (June 1, 2026)

Re-integrated Monetag with a focus on user experience and visibility.

### Changes Made

**`frontend/index.html`**
- Defined `--header-h: 60px` and reserved persistent `<header id="app-header">` at the top.
- Adjusted `.screen` layout to calculate height minus both header and footer, preventing overlap.
- Repositioned mute button to avoid conflict with top banner ads.
- Injected persistent In-Page/Banner script into the new header container.

**`frontend/screens/results.html`**
- Added `_triggerPopunder()` to the results show hook, ensuring ads only fire after a full game.

**`frontend/screens/home.html`**
- Added `_triggerInPageAd()` to the home show hook for non-intrusive ad delivery on the main menu.

### Monetization Checklist
| Requirement | Status |
|-------------|--------|
| Popunder Ad | ✅ Results Screen |
| In-Page Ad | ✅ Home Screen |
| Top Banner Ad | ✅ Persistent (60px) |
| Site-wide sw.js | ✅ frontend/sw.js |

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
| 11 | Game improvements: mode timer + fixed 10 questions + reveal/leaderboard flow | ✅ Done |
| 12 | Local dev / production routing cleanup | ✅ Done |
| 13 | Play Store submission | 🔲 Blocked (needs ID) |
| 14 | Solo/Classic modes + Authoritative Round Phases | ✅ Done |
| 15 | In-memory Rate Limiting (3 quizes/min) | ✅ Done |
| 16 | Session Persistence & Hash Routing | ✅ Done |
| 17 | Google Authentication | ✅ Done |
| 19 | Streak/Combo Multiplier (×1.5 at 3, ×2.0 at 6, cap ×3.0) + combo sound | ✅ Done |
---

## 🐛 Known Issues / Decisions Log
- Cloud Run scales to zero — ~2s cold start after idle. Mitigation: /health ping on app launch.
- In-memory state lost on container restart. Acceptable for MVP.
- ARM64 dev machine: always `docker buildx --platform linux/amd64 --push`.
- `Player.websocket` uses `exclude=True` — never leaks into JSON.
- Room codes: 4-char UPPERCASE alphanumeric (36^4 = ~1.6M possibilities).
- Gemini is optional at runtime right now; if missing or misconfigured, local fallback questions keep the backend running.
- Current game flow is 10 fixed questions, no question-count picker.
- Mode only affects timer length; it does not change question difficulty.
- Correct answer is shown first, then leaderboard, then next question.
- Cloud Run timeout must be 300s — default 60s kills WS sessions.
- `--workers 1` is intentional — multiple workers split in-memory state.
- Frontend local dev: serve from frontend/ dir, open http://localhost:8080.
- Frontend bundled inside Android .aab via CapacitorJS — NOT deployed separately.
- WSL ADB cannot see USB devices — always use Windows PowerShell ADB.
- After any frontend change: `npx cap sync android` then rebuild APK.
- Gemini API key was exposed in git history on May 24 2026 — rotated and updated in Cloud Run.
- AdSense identity verification (PAN) pending — earnings accumulate, payouts unlock when verified.
- Timer now depends on mode: Easy 30s / Medium 20s / Hard 10s.
- Difficulty colors still map to mode in UI: Easy (green) / Medium (yellow) / Hard (red).
- Streak multiplier applies AFTER the base score calculation. Points shown in `points_gained` already reflect the multiplier so the leaderboard "+1350" is accurate. Timed-out players (no answer sent) have streak reset server-side in `resolve_round` before `_round_payload` reads streaks, ensuring the broadcast is always correct.
---

## 🚀 Recent Feature Updates (Milestone 21-22)

### 1. Room Locking System
- **Mandatory Finalization**: The Host must now click **"LOCK ROOM"** before the **Team Mode** toggle becomes available.
- **Join Prevention**: Once locked, no new players can enter the room, ensuring a stable player list for team configuration.
- **Toggleable**: The host can unlock the room at any time. Unlocking while in Team Mode automatically reverts the room to **Classic Mode** for safety.

### 2. Team Host System
- **Team Leadership**: The first person to join **Team A** becomes the **Host of Team A**. Same for **Team B**.
- **Topic Restrictions**: Only the Team Host can write or edit the topic suggestion for their team. Other members see a waiting message.
- **Main Host Enjection**: The Room Creator (Main Host) is now required to join a team before the Team Mode game can be started.

### 3. Team Swapping
- **Flexibility**: Regular players (non-Team Hosts) can now use the **"SWAP TEAM"** button to switch sides if they joined the wrong team by mistake.
- **Stability**: Team Hosts cannot swap teams; they must remain to lead their team's topic selection.

### 4. Input Stability (The "Typing Fix")
- **Focus Preservation**: The lobby UI now preserves input focus and cursor position during real-time re-renders.
- **Debounced Updates**: Team names and topics are updated via WebSockets with a 400ms debounce to prevent network congestion and UI stutter.

---

## 📋 Technical Guidelines
- **Real-time Sync**: Use `PLAYER_JOINED` broadcasts to sync all lobby state (Mode, Teams, Locking).
- **Frontend State**: Initialize `lobby.html` state from global `State` to ensure instant UI sync for late-joiners.
- **Clean Transitions**: Always ensure `_applyModeUI()` is called when mode or lock status changes.
- **Security**: Prevent non-hosts from sending privileged actions (`lock_room`, `set_lobby_mode`).

## ✅ Compliance Checklist
- [x] Room Locking for Team Mode stability.
- [x] Team Host role for topic selection.
- [x] Team Swapping for regular players.
- [x] Input focus preservation & debouncing.
- [x] Late-join synchronization logic.
- [x] Privacy/Policy links and mobile responsive UI.
1. Always write **clean, commented code** with docstrings on every function.
2. Explain the **"why"** behind async/WebSocket logic.
3. Provide code in **modular chunks** — one file at a time.
4. After each major milestone, provide an **updated CLAUDE.md**.
5. Never suggest paid services. $0 constraint always applies.
6. ARM64 context: flag any ARM64 compat issues proactively.
7. When user pastes error output, fix root cause — don't patch symptoms.
8. Always assume existing files are correct unless user pastes them.
9. Frontend production build must point to live Cloud Run URL; local dev auto-switches to `http://127.0.0.1:8000` when opened from `localhost` or `file:`.
10. Design language: blue/white quiz-game theme, Press Start 2P for UI chrome,
    Nunito for body text, yellow #FFD93D accent, Kahoot-style answer buttons.
    Do NOT revert to hacker/neon/dark theme.
11. ADB commands must use Windows PowerShell, not WSL terminal.
12. Website is live at forgetrivia.online — frontend deployed on Vercel,
    connected via Namecheap DNS (A record + CNAME to Vercel).

---

## Milestone 14 - Solo/Classic Modes and Authoritative Round Phases (May 26, 2026)

This section supersedes earlier game-loop and WebSocket flow notes where they
conflict.

### Current Game Setup
- Main menu exposes `solo` and `classic` play modes.
- Solo creates a private one-player room through the existing in-memory
  WebSocket pipeline; it does not expose a room code or intermission standings.
- Classic creates or joins a sharable room and shows competitive standings.
- Difficulty is selected before starting: `easy` = 30000 ms, `medium` =
  20000 ms, and `hard` = 10000 ms.
- The timer ring, number, duration label, warning styling, and server deadline
  all use the selected difficulty limit.

### Authoritative Phase Flow
```
classic: QUESTION -> ANSWER_REVEAL (4000 ms)
                  -> INTERMISSION_LEADERBOARD (5000 ms)
                  -> next QUESTION or GAME_OVER

solo:    QUESTION -> ANSWER_REVEAL (4000 ms)
                  -> next QUESTION or GAME_OVER
```

- The server enters reveal when every connected player answers or when the
  selected question timer expires.
- `RoundPhase` values are `lobby`, `question`, `answer_reveal`,
  `intermission_leaderboard`, and `complete`.
- The game partial stays mounted while phase visuals change, preserving the
  selected answer and correct/wrong highlights.
- The question phase contains no standings list. Classic standings are only
  populated in the full-screen intermission view, including per-round gains.

### State and Models
- `PlayMode` values are `solo` and `classic`.
- `Room` additionally stores `play_mode`, `phase`, and `points_gained`.
- `Player` additionally stores `correct_answers` for final accuracy.
- Solo results display final score, accuracy, and a per-difficulty personal
  best stored locally on the device; classic results retain final standings.

### Current WebSocket Protocol
```json
{ "action": "start_game", "topic": "Space", "mode": "hard", "play_mode": "classic" }
{ "type": "GAME_STARTING", "data": { "topic": "Space", "mode": "hard", "play_mode": "classic", "time_limit_ms": 10000, "total_questions": 10 } }
{ "type": "QUESTION", "data": { "index": 0, "text": "...", "options": ["A", "B", "C", "D"], "phase": "question", "mode": "hard", "play_mode": "classic", "time_limit_ms": 10000 } }
{ "type": "ANSWER_REVEAL", "data": { "phase": "answer_reveal", "hold_ms": 4000, "correct_index": 2, "scores": {}, "points_gained": {}, "answers": {}, "play_mode": "classic" } }
{ "type": "INTERMISSION_LEADERBOARD", "data": { "phase": "intermission_leaderboard", "hold_ms": 5000, "is_final": false, "scores": {}, "points_gained": {}, "play_mode": "classic" } }
{ "type": "GAME_OVER", "data": { "final_scores": {}, "correct_answers": {}, "accuracy_percentages": {}, "total_questions": 10, "play_mode": "classic" } }
```

### Implementation Notes
- `frontend/index.html` queues messages received before a lazy-loaded screen
  registers its handler, preventing loss of the first question.
- `backend/app/routers/websocket.py` owns deadline tasks and phase guards so
  late or duplicate answers cannot advance a resolved round twice.
- Milestone 14: game mode menu, difficulty-aware timer, fixed reveal and
  intermission timing, solo results, and server timeout resolution are done.
- Desktop home layout uses a grid at widths of 1024 px and above so the
  expanded mode menu cannot overlap the feature strip.
- Capacitor's `https://localhost` asset origin is treated as native app
  routing; only desktop `http://localhost` or file-based development targets
  the local FastAPI server at `127.0.0.1:8000`.

---

## Milestone 15 - In-memory Rate Limiting (May 27, 2026)

To prevent resource abuse and Gemini API spam, the backend now enforces simple
sliding-window rate limits based on client IP.

### Limits
- **Room Creation**: 5 per minute per IP (`POST /rooms/create`)
- **Quiz Generation**: 3 per minute per IP (`WS start_game`)

### Implementation Details
- `app/core/state.py` tracks timestamps in a `quiz_rate_limits` dictionary.
- `app/core/limiter.py` provides the `is_rate_limited` utility.
- Both HTTP and WebSocket routers extract the real client IP from the
  `X-Forwarded-For` header (if present via proxy) or the direct connection.
- Rate limit hits return a `429 Too Many Requests` for HTTP or an `ERROR`
  WebSocket message.

---

## Milestone 16 - Session Persistence & Hash Routing (May 27, 2026)

The web app now survives refreshes and supports browser navigation (back/forward).

### Frontend Routing
- `goTo(name)` updates `window.location.hash` (e.g. `/#lobby`).
- `hashchange` listener handles manual URL edits or browser navigation.
- App boot sequence restores the last known screen from the URL hash.

### Session Persistence
- `Session` utility saves/loads `playerName`, `roomCode`, `isHost`, and `playMode` to `localStorage`.
- On boot, if a session exists, the app automatically attempts to re-validate the
  room and reconnect to the WebSocket if the user is on a game-related screen.

### Backend Re-join Support
- Players are no longer immediately removed from rooms on `WebSocketDisconnect`.
- Disconnected players can re-join `ACTIVE` rooms if their name matches an
  existing player with a `None` websocket.
- Empty rooms (no connected players) are deleted after a **60-second grace period**.

---

## Milestone 17 - Google Authentication (May 27, 2026)

Professional Google Login is now integrated into the Forge ecosystem.

### Frontend Integration
- **Google Identity Services**: Loaded via script in `index.html`.
- **UI Components**: Standard "Sign in with Google" button and a professional user
  profile badge (avatar + name) on the home screen.
- **Auto-fill**: Successfully logging in automatically pre-fills the "YOUR NAME"
  field for faster room entry.
- **Persistence**: User profile is saved to `localStorage` alongside the session.

### Backend Verification
- **Token Verification**: New `/auth/google` POST endpoint in `app/routers/auth.py`.
- **Security**: Uses the `google-auth` library to verify the integrity and audience
  of Google ID tokens received from the frontend.
- **Configuration**: Added `GOOGLE_CLIENT_ID` to `app/core/config.py` and
  `.env.example`.

### How to Configure
1. Create a project in the [Google Cloud Console](https://console.cloud.google.com/).
2. Create an **OAuth 2.0 Client ID** for a "Web application".
3. Add `http://localhost:8080` (dev) and your production domain to the **Authorized JavaScript origins**.
4. Update `GOOGLE_CLIENT_ID` in `frontend/index.html` and your backend `.env` file.

---

## Milestone 18 - Regulatory Compliance & Navigation (May 28, 2026)

Improved navigation and user transparency.

### Changes Made

**`frontend/index.html`**
- Added persistent `<nav id="app-footer">` bar with links to About, Privacy Policy,
  and contact email — visible on all screens except during active gameplay
- Footer auto-hides during the game screen (`game-active` CSS class) so it
  never overlaps answer buttons

**`frontend/privacy.html`**
- Added `rel="noopener noreferrer"` to all external links (Google, Vercel)
- Styled the contact email as a prominent call-out card
- Added mention of `localStorage` usage (mute, high scores) to the cookies section

### Compliance Checklist
| Requirement | Status |
|-------------|--------|
| Privacy Policy page | ✅ /privacy.html |
| Privacy Policy link accessible from main app | ✅ Footer nav |
| About page | ✅ /about.html |
| Contact info visible | ✅ Footer nav + privacy page |
| No prohibited content | ✅ |

---

## Milestone 23 - Solo Isolation + Coins/Trophies Economy (June 1, 2026)

Restored Solo Mode boundaries after the Team Mode rollout and added Google-linked
economy persistence.

### Solo Mode Isolation
- Solo lobby now forces the local lobby renderer to the classic setup panel and
  clears team-only local state (`teams`, `team_topics`, `myTeamId`) on entry and
  on `PLAYER_JOINED` refreshes.
- Solo start now sends `play_mode: "solo"` to the server instead of accidentally
  promoting the game to classic.
- The backend rejects stale client attempts to override an existing solo room
  into classic/team mode.

### Economy Rules
- New Google profiles initialize with exactly **200 coins** and **50 trophies**.
- Room games require signed-in players and charge **25 coins** per connected
  player when the game starts.
- Room winners receive the full entry-fee coin pool; tied winners split the pool
  equally, including fractional coin splits when needed to preserve the full
  pool exactly.
- Solo rewards are based on correct answers:
  - `>= 5` correct: `+10 coins`
  - `< 4` correct: `-2 trophies`, clamped at `0`
  - `4` or `5` correct: `+1 trophy`
  - `6-10` correct: `+2 trophies` per correct answer above 5

### Persistence Implementation
- Added `backend/app/services/profiles.py`, a lightweight JSON profile store at
  `PROFILE_STORE_PATH` (default `app/data/profiles.json`) to preserve balances
  without paid infrastructure.
- Google Sign-In now returns saved `coins` and `trophies` to the frontend.
- WebSocket connections include the signed-in Google profile ID so the server can
  apply authoritative game-end economy deltas.
- Results and home screens render the synced balances and game-end deltas.

## Milestone 23 — CI/CD Pipeline (GitHub Actions)

Every push to `main` that touches `forge/backend/**` automatically:
1. Builds a `linux/amd64` Docker image on GitHub's native runners (no QEMU).
2. Pushes `:latest` + `:<commit-sha>` tags to Artifact Registry.
3. Deploys to Cloud Run with all env vars injected from GitHub Secrets.

### Required GitHub Secrets
| Secret | Value |
|---|---|
| `GCP_SA_KEY` | Full JSON of `github-actions` service account key |
| `GEMINI_API_KEY` | Gemini API key |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |

### Rollback
```bash
gcloud run deploy forge-backend \
  --image us-central1-docker.pkg.dev/quiz-app-forge/forge/backend:<sha> \
  --region us-central1
```

### Local deploys (emergency only)
Still works as before — but prefer pushing to main and letting CI/CD handle it.