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

## 💰 Monetization Strategy (Updated — Milestone 25)

### Current Approach
The project has permanently shifted away from display/programmatic advertising
toward a cleaner, sustainable monetization model focused on:

1. **Google AdSense** (primary goal) — pending approval. All site architecture
   decisions are now filtered through AdSense compliance requirements.
2. **Chai4Me micro-donations** — `https://www.chai4.me/devsolankiworks`
   A non-intrusive "Buy the Dev a Chai" support button embedded on the home
   screen and landing page. Chai4Me official embed code used verbatim.
3. **In-game economy** — Coins and Trophies earned/spent through gameplay.
   No real-money transactions; economy exists for engagement and retention.

### ⛔ DEPRECATED — Forbidden Ad Technologies
The following ad integrations have been **permanently removed** and must **never
be re-added** under any circumstances:

| Network | Why Banned |
|---------|-----------|
| **Monetag** (all products) | $0.03 CPM, caused infinite loops that froze the UI, popunders destroyed retention, vignettes violated UX standards |
| Any **vignette / interstitial** ad | Blocks game access, violates AdSense policies on gameplay interference |
| Any **popunder / pop-up** ad | Universally rejected by premium ad networks, causes browser security warnings |
| Any **push notification** ad | Requires invasive browser permissions, flagged as malware-adjacent by ad quality audits |
| **Instant-approval** ad networks | By definition operate at low CPM and rely on low-quality traffic — incompatible with brand goals |

**Rule:** If an ad network approves a site within 24 hours of submission, it is
a low-tier network and must not be used. Premium networks (Google AdSense,
Media.net, Ezoic) take days to weeks to audit manually and pay 10–100× more.

### AdSense Compliance Checklist (Must maintain at all times)
- [x] AdSense script present on every crawlable HTML page (`index.html`,
      `about.html`, `privacy.html`)
- [x] Navigation links to Privacy Policy and About from every screen
- [x] Cookie consent banner with localStorage persistence and AdSense NPA (Non-Personalized Ads) support
- [x] `landing.html` — rich semantic content page satisfies "Low Value Content"
      automated rejection filter
- [x] No auto-play video, no deceptive ad placements, no ad-adjacent game elements
- [x] `robots.txt` and `sitemap.xml` present and up to date
- [x] Privacy Policy covers Google Gemini API data usage and AdSense cookies
- [ ] AdSense manual review approval — PENDING (payout identity verification
      pending PAN card arrival)

---

## 🏗️ Tech Stack (LOCKED — do not suggest changes)

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | HTML5 + Tailwind CSS + Vanilla JS | Stays portable for CapacitorJS wrapping |
| Mobile Wrapper | CapacitorJS → Android .aab | $0 — no React Native licenses |
| Backend | Python + FastAPI | Student knows Python well |
| AI | Gemini 2.5 Flash Lite (`google-generativeai`) | $0 free tier, with local fallback if unavailable |
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
│       │   └── quiz.py        ← Pydantic models ✅
│       ├── routers/
│       │   ├── http.py        ← REST endpoints ✅ (includes /economy/reward)
│       │   └── websocket.py   ← WS game loop ✅
│       └── services/
│           ├── ai.py          ← Gemini AI service ✅
│           └── profiles.py    ← File-backed economy ✅
└── frontend/
    ├── index.html             ← App shell, router + Cookie Banner Logic ✅
    ├── privacy.html           ← Privacy Policy page ✅
    ├── about.html             ← About page ✅
    ├── robots.txt             ← SEO crawler permissions ✅
    ├── sitemap.xml            ← Google Search Console sitemap ✅
    └── screens/
        ├── landing.html       ← Rich content entry page (AdSense/SEO) ✅ NEW
        ├── home.html          ← Game lobby (create/join/solo) + Chai4Me ✅
        ├── lobby.html         ← Waiting room + mode selector ✅
        ├── game.html          ← Active quiz screen ✅
        └── results.html       ← Final scoreboard ✅
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
  --timeout 600
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

### ADB install via PowerShell (Windows)
```powershell
& "C:\Users\$env:USERNAME\AppData\Local\Android\Sdk\platform-tools\adb.exe" devices
& "C:\Users\$env:USERNAME\AppData\Local\Android\Sdk\platform-tools\adb.exe" install "C:\QuizApp\forge\android\app\build\outputs\apk\debug\app-debug.apk"
```

---

## 🔄 Core Game Loop (Server-side Truth)

```
1. POST /rooms/create        ✅
2. WS /ws/{room_code}/{player_name}   ✅
3. Host sends: { "action": "start_game", "topic": "...", "mode": "hard" }   ✅
4. Player sends: { "action": "answer", "choice": 2, "time_ms": 3400 }   ✅
5. After final question → broadcast GAME_OVER   ✅
```

---

## 📐 Scoring Formula
```python
BASE_POINTS = 1000
score = int(BASE_POINTS * (1 - (time_ms / time_limit_ms) * 0.5))
score = max(500, min(1000, score))
multiplier = min(1.0 + (streak // 3) * 0.5, 3.0)
# streak 1–2 → ×1.0 | streak 3–5 → ×1.5 | streak 6–8 → ×2.0 | streak 9–11 → ×2.5 | streak 12+ → ×3.0
final_score = int(base_score * multiplier)
```

---

## 🎮 Game Configuration Options

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
- **Pixel font**: `"Press Start 2P"` — ALL UI chrome
- **Body font**: `"Nunito"` (weight 700–900) — questions, answers, player names
- **Mobile-first**: All tap targets ≥ 56px, max-width 430px centred

---

## 🖥️ Frontend Architecture

### Routing (SPA pattern)
- Single `index.html` shell — screens lazy-loaded from `screens/*.html`
- `goTo(name)` handles navigation + calls `onXxxShow()` hook
- **Default entry point is now `landing` (not `home`)**
  - First-time visitors and direct URL hits → `landing`
  - Returning players with `#home` in the URL → `home` (skip landing)
  - In-progress room sessions → restored directly to `lobby`/`game`/`results`
- No framework — pure vanilla JS

### Cookie Consent (AdSense Compliance)
- `CookieConsent` object in `index.html` manages banner visibility and persistence.
- Choice stored in `localStorage` under `forge_cookie_consent`.
- Supports Personalised vs Non-Personalised ads toggle (`window.__adsenseNPA`).
- 1.8s delayed appearance to minimize layout shift.

### Screen Flow
```
landing ──(Play Now)──► home ──(Create/Join)──► lobby ──► game ──► results
                          ▲                                            │
                          └────────────────(Play Again / Go Home)─────┘
```

### Global Objects
| Object | Purpose |
|--------|---------|
| `State` | `playerName, roomCode, isHost, topic, mode, timeLimitMs, ws, players, scores, totalQ, user, teams, teamNames, teamScores` |
| `API`   | `createRoom()`, `getRoom()`, `health()`, `verifyGoogleToken()` |
| `WS`    | `connect()`, `send()`, `on(type,fn)`, `off(type)` |
| `Toast` | `Toast.error()`, `.success()`, `.info()` |
| `Session` | `save()`, `load()`, `clear()` — persists to localStorage |
| `goTo(name)` | Screen router |

---

## 🔌 WebSocket Message Protocol

### Server → Client
```json
{ "type": "PLAYER_JOINED",  "data": { "players": [], "lobby_mode": "classic", "locked": false } }
{ "type": "GAME_STARTING",  "data": { "topic": "...", "mode": "hard", "play_mode": "classic", "total_questions": 10, "time_limit_ms": 10000 } }
{ "type": "QUESTION",       "data": { "index": 0, "text": "...", "options": ["A","B","C","D"], "time_limit_ms": 10000, "mode": "hard" } }
{ "type": "ANSWER_REVEAL",  "data": { "phase": "answer_reveal", "hold_ms": 4000, "correct_index": 2, "scores": {}, "points_gained": {}, "answers": {}, "streaks": {} } }
{ "type": "LEADERBOARD",    "data": { "scores": {}, "correct_index": 2 } }
{ "type": "GAME_OVER",      "data": { "final_scores": {}, "economy": {} } }
{ "type": "ERROR",          "data": { "message": "Room not found" } }
```

### Client → Server
```json
{ "action": "start_game", "topic": "Quantum Physics", "mode": "hard", "play_mode": "classic" }
{ "action": "answer",     "choice": 2, "time_ms": 3400 }
```

---

## 🤖 Gemini Config
- Model: `GEMINI_MODEL` env var, default `gemini-2.5-flash-lite`
- max_output_tokens: 1024, temperature: 0.8
- Falls back to local hardcoded questions if Gemini unavailable

---

## 🗄️ Data Models (app/models/quiz.py)

```
GameStatus  (Enum)    → WAITING | STARTING | ACTIVE | FINISHED
GameMode    (Enum)    → easy | medium | hard
PlayMode    (Enum)    → solo | classic | team
RoundPhase  (Enum)    → lobby | question | answer_reveal | intermission_leaderboard | complete
Question    (Model)   → question, options x4, correct_index
Player      (Model)   → name, score, correct_answers, streak, answered, last_answer, websocket(excluded)
Room        (Model)   → code, host, status, mode, time_limit_ms, players, questions,
                        current_q_index, answers_this_round, teams, team_names, team_topics,
                        topic, locked, entry_fees, economy_finalized
```

---

## 🌐 REST API (app/routers/http.py)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe |
| POST | `/rooms/create` | Create room |
| GET | `/rooms/{code}` | Inspect room |
| DELETE | `/rooms/{code}` | Remove room |
| POST | `/auth/google` | Verify Google ID token, return profile |
| POST | `/economy/reward` | Apply coin reward |

---

## 💰 Economy Rules

| Situation | Coins | Trophies |
|-----------|-------|---------|
| New account | +200 | +50 |
| Room entry fee | -25 | — |
| Room winner | +pool | — |
| Solo ≥5 correct | +10 | — |
| Solo 4–5 correct | — | +1 |
| Solo 6–10 correct | — | +2 per above 5 |
| Solo <4 correct | — | -2 (floor 0) |

---

## 🛠️ Economy Persistence Fix (Milestone 24)

Cloud Run is ephemeral — `profiles.json` is wiped on container restart/scale-zero.
Fix: `localStorage` is the source of truth for coins/trophies on the client.

- Key: `forge_economy_{user_id}`
- On `handleGoogleLogin`: take `MAX(localStorage_coins, backend_coins)` — never overwrites better local value
- On `applyUserEconomy`: always write back to both `State.user` and localStorage
- Backend is still updated for game transactions but client never trusts a lower value from it

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
| 15 | In-memory Rate Limiting (3 quizzes/min) | ✅ Done |
| 16 | Session Persistence & Hash Routing | ✅ Done |
| 17 | Google Authentication | ✅ Done |
| 18 | Regulatory Compliance & Navigation | ✅ Done |
| 19 | Streak/Combo Multiplier + combo sound | ✅ Done |
| 20 | Team Mode (lock/unlock, team hosts, topic randomizer) | ✅ Done |
| 21 | Room Locking System + Team Host System + Team Swapping | ✅ Done |
| 22 | Input Stability (typing fix, debounced WS updates) | ✅ Done |
| 23 | Solo Isolation + Coins/Trophies Economy + CI/CD Pipeline | ✅ Done |
| 24 | Economy persistence fix (localStorage source of truth) + Made App Ad-Free | ✅ Done |
| 25 | Monetization pivot: Monetag removed, AdSense landing page + Chai4Me support | ✅ Done |
| 26 | AdSense Compliance: Cookie Consent Banner + NPA logic | ✅ Done |

---

## 🐛 Known Issues / Decisions Log
- Cloud Run scales to zero — ~2s cold start after idle. Mitigation: /health ping on app launch.
- In-memory state lost on container restart. Acceptable for MVP.
- ARM64 dev machine: always `docker buildx --platform linux/amd64 --push`.
- `Player.websocket` uses `exclude=True` — never leaks into JSON.
- Room codes: 4-char UPPERCASE alphanumeric (36^4 = ~1.6M possibilities).
- Gemini is optional at runtime; if missing or misconfigured, local fallback questions keep backend running.
- Current game flow is 10 fixed questions.
- Mode only affects timer length; it does not change question difficulty.
- Cloud Run timeout must be 600s — default 60s kills WS sessions.
- `--workers 1` is intentional — multiple workers split in-memory state.
- Frontend local dev: serve from frontend/ dir, open http://localhost:8080.
- Frontend bundled inside Android .aab via CapacitorJS — NOT deployed separately.
- WSL ADB cannot see USB devices — always use Windows PowerShell ADB.
- After any frontend change: `npx cap sync android` then rebuild APK.
- Gemini API key was exposed in git history on May 24 2026 — rotated and updated in Cloud Run.
- **The app is completely ad-free** of disruptive ad formats. Monetag and all low-tier ad scripts have been permanently removed.
- profiles.json is ephemeral on Cloud Run — localStorage is client-side source of truth for economy.
- All AdOps.* and ADS.* references have been removed from all screen files.
- **Landing screen (`screens/landing.html`) is the new default entry point.** It is a content-rich, semantic HTML5 page designed to pass Google AdSense's automated "Low Value Content" rejection filter. It contains deep textual descriptions of all game modes, the scoring system, difficulty levels, tech stack, and FAQ. The "Play Now" CTA navigates to the actual game (`home` screen).
- **Chai4Me support embed** is placed on `screens/home.html` below the feature pills. It uses the official embed code from chai4.me verbatim and opens in a new tab (`target="_blank"`).
- **Cookie Consent Banner (`index.html`)**: Implemented Task 4 of the AdSense compliance audit. The banner sits just above the footer, uses the pixel font theme, and persists choices in `localStorage`. It explicitly signals `__adsenseNPA` to respect user choice regarding personalized ads.

---

## 📋 Technical Guidelines
1. Always write **clean, commented code** with docstrings on every function.
2. Explain the **"why"** behind async/WebSocket logic.
3. Provide code in **modular chunks** — one file at a time.
4. After each major milestone, provide an **updated CLAUDE.md**.
5. Never suggest paid services. $0 constraint always applies.
6. ARM64 context: flag any ARM64 compat issues proactively.
7. When user pastes error output, fix root cause — don't patch symptoms.
8. Always assume existing files are correct unless user pastes them.
9. Frontend production build must point to live Cloud Run URL; local dev auto-switches to `http://127.0.0.1:8000`.
10. Design language: blue/white quiz-game theme, Press Start 2P for UI chrome, Nunito for body text, yellow #FFD93D accent, Kahoot-style answer buttons. Do NOT revert to hacker/neon/dark theme.
11. ADB commands must use Windows PowerShell, not WSL terminal.
12. Website is live at forgetrivia.online — frontend deployed on Vercel, connected via Namecheap DNS.
13. **Never re-introduce any ad network scripts** without explicit approval. If a monetization option is being considered, it must first be evaluated against AdSense policy compatibility, CPM floor (minimum $0.50 effective CPM to be worth the UX cost), and user retention impact before any code is written.