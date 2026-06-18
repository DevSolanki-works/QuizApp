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

## 💻 Local Development

### ⚠️ CRITICAL: Run the frontend server from the RIGHT directory
```bash
# CORRECT — serve from forge/frontend/
cd forge/frontend && python3 -m http.server 8080

# WRONG — fetch('screens/landing.html') returns 404, blank screen
cd forge && python3 -m http.server 8080
```

### Start backend locally
```bash
cd forge/backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

### Local URLs
- Frontend: http://127.0.0.1:8080
- Backend API: http://127.0.0.1:8000
- API docs: http://127.0.0.1:8000/docs

### Known local dev quirk — Supabase defer race (FIXED Milestone 29)
`supabase-client.js` is loaded with `defer`. Returning signed-in users triggered
a "lbFetchProfile is not a function" crash in the boot IIFE, leaving a blank blue
screen. Fixed with `waitForSupabase()` polling helper in the boot block. First-time
visitors were never affected (they don't hit the profile sync path).

---

## 💰 Monetization Strategy

### Current Approach
1. **Google AdSense** (primary goal) — pending approval (PAN card pending).
2. **Chai4Me micro-donations** — `https://www.chai4.me/devsolankiworks`
3. **In-game economy** — Coins and Trophies earned through gameplay.

### ⛔ DEPRECATED — Forbidden Ad Technologies
Never re-add: Monetag, vignette/interstitial ads, popunders, push notification ads,
or any instant-approval ad network.

### AdSense Compliance Checklist
- [x] AdSense script on every crawlable HTML page
- [x] Navigation links to Privacy Policy and About from every screen
- [x] Cookie consent banner with localStorage + NPA support
- [x] `landing.html` — rich semantic content (Low Value Content filter)
- [x] `robots.txt` and `sitemap.xml` present and up to date
- [x] Landing page is the default entry point (bots see it first)
- [ ] AdSense manual review approval — PENDING (PAN card pending)

### ⚠️ AdSense Landing Page Rule — DO NOT BREAK
`landing.html` MUST remain the first screen served on a cold visit (`/#` or `/`).
The boot IIFE explicitly routes to `landing` as the default case (Case 3).
Never change this to `home` as the default — AdSense bots must see real content.

---

## 🔒 Security (Milestone 29)

### Files changed
| File | What changed |
|------|-------------|
| `app/core/sanitize.py` | NEW — input validation module for all WS messages |
| `app/core/limiter.py` | XFF now trusts last IP (Cloud Run's insertion), not first (spoofable) |
| `app/routers/http.py` | `/economy/sync` and `/economy/reward` require `Authorization: Bearer <id_token>` |
| `app/routers/websocket.py` | All inputs via sanitize module; action allowlist; WS join rate-limited |
| `index.html` boot IIFE | `waitForSupabase()` fixes defer race; try/catch safety net |
| `index.html` goTo() | SCREEN_GUARDS block direct `/#results`, `/#game` URL access |
| `index.html` API object | `syncProfile()` sends `Authorization: Bearer` header |
| `index.html` handleGoogleLogin() | Stores `user._credential` for authenticated backend calls |

### Security model summary
- **WS actions**: validated against explicit allowlist in `sanitize.VALID_ACTIONS`
- **Topics**: checked against prompt-injection regex blocklist before Gemini call
- **Economy endpoints**: require live Google JWT matching the `user_id` in body
- **Rate limiting**: per-IP, per-action, using last XFF entry (not first)
- **Screen guards**: `lobby` requires roomCode+playerName; `game` requires active WS; `results` requires non-empty scores
- **time_ms**: clamped to `[0, time_limit_ms + 500ms]` — can't claim 0ms for max points

### Known remaining attack surfaces (acceptable for MVP)
- Leaderboard inflation via direct Supabase REST — blocked only by RLS policies
- Score advantage from `time_ms: 1` partially mitigated (clamped, not server-clock verified)
- Room code brute-force impractical (15 WS joins/min/IP rate limit)

---

## 🗄️ Supabase (Milestone 27)

### Project
- **URL:** `https://ffstsbwkianjcjpqvmtv.supabase.co`
- **Anon key:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (full key in supabase-client.js)
- **Region:** Southeast Asia (Singapore)

### Tables
| Table | Purpose |
|-------|---------|
| `leaderboard` | One row per player. `google_id` PK. Upserted on game end. |
| `donations` | One row per UPI claim. `status`: pending → approved → rejected. |
| `donor_leaderboard` | VIEW. Auto-sums approved donations per person. Read-only. |

### Key rules
- Leaderboard upsert fires in `applyUserEconomy()` (index.html) — fire-and-forget
- `lbUpsertPlayer()` uses `onConflict: 'google_id'` — never resets on play-again
- Donation approval is 100% manual: Supabase dashboard → donations → set status = 'approved'
- `donor_leaderboard` is a SQL VIEW — never try to insert into it

### Admin workflow (approving donations)
1. Go to supabase.com → your project → Table Editor → `donations`
2. Find rows with `status = pending`
3. Cross-check the `upi_txn_id` in your UPI app
4. Click the row → edit → change `status` to `approved` → save

---

## 🏗️ Tech Stack (LOCKED — do not suggest changes)

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | HTML5 + CSS + Vanilla JS | Stays portable for CapacitorJS |
| Database | Supabase (PostgreSQL, free tier) | Leaderboard + donations, $0 |
| Mobile Wrapper | CapacitorJS → Android .aab | $0 |
| Backend | Python + FastAPI | Student knows Python well |
| AI | Gemini 2.5 Flash Lite | $0 free tier |
| Real-time | FastAPI WebSockets | Built-in |
| State | In-memory Python dicts | $0 |
| Deployment | Docker → Google Cloud Run | $0 free tier |

### ⚠️ Hard Constraints
- **$0 infrastructure** — Supabase free tier fits comfortably (500MB, 50k MAU)
- **ARM64 dev machine** — all local Docker builds use `docker buildx`
- **No heavy ORM** — plain Python dicts for game state
- **Android only** — iOS out of scope

---

## 📁 Project Structure

```
forge/
├── CLAUDE.md
├── package.json
├── capacitor.config.json
├── android/
├── assets/                    ← Master branding assets (M29.5)
│   ├── icon.png
│   ├── icon-foreground.png
│   ├── icon-background.png
│   └── splash.png
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── app/
│       ├── core/ (config.py, state.py, limiter.py, sanitize.py)
│       ├── models/ (quiz.py)
│       ├── routers/ (http.py, websocket.py, auth.py)
│       └── services/ (ai.py, profiles.py)
└── frontend/
    ├── index.html             ← boot fix + screen guards + auth API (M29)
    ├── platform.js            ← AdSense loader
    ├── app.js                 ← Core game logic (multiplayer)
    ├── supabase-client.js     ← DB interactions (leaderboard/economy)
    ├── ads.txt / app-ads.txt
    ├── robots.txt / sitemap.xml
    ├── about.html
    ├── contact.html
    ├── privacy.html
    ├── terms.html
    ├── how-to-play.html
    ├── topic-guide.html
    ├── trivia-tips.html
    ├── ai-trivia-questions.html
    ├── dev-log.html
    ├── multiplayer-quiz-guide.html
    ├── leaderboard.html
    ├── assets/ (fonts, icons)
    ├── components/
    │   ├── leaderboard.js
    │   └── timer.js
    └── screens/
        ├── landing.html       ← DEFAULT entry point (AdSense requirement)
        ├── home.html
        ├── lobby.html
        ├── game.html
        └── results.html
```

---

## 🚀 Live Deployment

| Property | Value |
|----------|-------|
| **Website** | `https://forgetrivia.online` |
| **Leaderboard** | `https://forgetrivia.online/leaderboard.html` |
| Backend URL | `https://forge-backend-878124462453.us-central1.run.app` |
| Frontend | Vercel (auto-deploys from git push to main) |

### Re-deploy backend
```bash
cd forge/backend

docker buildx build \
  --platform linux/amd64 \
  --tag us-central1-docker.pkg.dev/quiz-app-forge/forge/backend:latest \
  --push .

gcloud run deploy forge-backend \
  --image us-central1-docker.pkg.dev/quiz-app-forge/forge/backend:latest \
  --platform managed --region us-central1 --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_key,GEMINI_MODEL=gemini-2.5-flash-lite,GOOGLE_CLIENT_ID=878124462453-g7skbojds4uqg442hb9d31ftrlll095r.apps.googleusercontent.com \
  --min-instances 0 --max-instances 3 --memory 512Mi --timeout 600
```

---

## 🔄 Core Game Loop
```
1. POST /rooms/create
2. WS /ws/{room_code}/{player_name}
3. Host: { action: start_game, topic, mode }
4. Player: { action: answer, choice, time_ms }
5. GAME_OVER → applyUserEconomy() → lbUpsertPlayer() [Supabase]
```

---

## 📐 Scoring Formula
```python
base  = max(500, min(1000, int(1000 * (1 - (time_ms / time_limit_ms) * 0.5))))
multi = min(1.0 + (streak // 3) * 0.5, 3.0)
final = int(base * multi)
# streak 0-2→×1.0 | 3-5→×1.5 | 6-8→×2.0 | 9-11→×2.5 | 12+→×3.0
```

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

Economy localStorage key: `forge_economy_{user_id}` — source of truth on client.

---

## 🌐 REST API

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Liveness probe |
| POST | `/rooms/create` | None | Create room |
| GET | `/rooms/{code}` | None | Inspect room |
| DELETE | `/rooms/{code}` | None | Remove room |
| POST | `/auth/google` | None | Verify Google ID token |
| POST | `/economy/reward` | Bearer JWT | Apply coin reward |
| POST | `/economy/sync` | Bearer JWT | Sync coins/trophies from Supabase |

---

## 🔌 WebSocket Message Protocol

### Server → Client
```json
{ "type": "PLAYER_JOINED",            "data": { "players": [], "lobby_mode": "classic", "locked": false } }
{ "type": "GAME_STARTING",            "data": { "topic": "...", "mode": "hard", "play_mode": "classic", "total_questions": 10 } }
{ "type": "QUESTION",                 "data": { "index": 0, "text": "...", "options": ["A","B","C","D"], "time_limit_ms": 10000 } }
{ "type": "ANSWER_REVEAL",            "data": { "correct_index": 2, "scores": {}, "streaks": {} } }
{ "type": "INTERMISSION_LEADERBOARD", "data": { "scores": {}, "is_final": false } }
{ "type": "GAME_OVER",                "data": { "final_scores": {}, "economy": {} } }
{ "type": "ERROR",                    "data": { "message": "..." } }
```

### Client → Server (all validated via sanitize.py)
```json
{ "action": "start_game", "topic": "...", "mode": "hard", "play_mode": "classic" }
{ "action": "answer",     "choice": 2,   "time_ms": 3400 }
{ "action": "join_team",  "team_id": "A" }
{ "action": "set_team_info", "name_a": "...", "name_b": "...", "topic_a": "...", "topic_b": "..." }
{ "action": "set_lobby_mode", "mode": "team" }
{ "action": "lock_room" }
{ "action": "unlock_room" }
```

---

## ✅ Milestones Tracker

| # | Milestone | Status |
|---|-----------|--------|
| 1–16 | Project setup through session persistence | ✅ Done |
| 17 | Google Authentication | ✅ Done |
| 18 | Regulatory Compliance & Navigation | ✅ Done |
| 19 | Streak/Combo Multiplier | ✅ Done |
| 20 | Team Mode | ✅ Done |
| 21 | Room Locking + Team Host System | ✅ Done |
| 22 | Input Stability fixes | ✅ Done |
| 23 | Solo Isolation + Economy + CI/CD | ✅ Done |
| 24 | Economy persistence (localStorage source of truth) | ✅ Done |
| 25 | Monetization pivot: landing page + Chai4Me | ✅ Done |
| 26 | AdSense Compliance: Cookie Consent Banner | ✅ Done |
| 27 | Supabase Leaderboard + Donation System | ✅ Done |
| 28 | Play Store submission | 🔲 Blocked (needs PAN card) |
| 29 | Security Hardening | ✅ Done |
| 29.5 | Branding Assets (Icons/Splash) Generated | ✅ Done |
| 30 | Question count selector (5/10/15/20) + Results share button | 🔲 Next |

---

## 🐛 Known Issues / Decisions Log
- Cloud Run scales to zero — ~2s cold start. Mitigation: /health ping on launch.
- In-memory state lost on container restart. Acceptable for MVP.
- ARM64: always `docker buildx --platform linux/amd64 --push`.
- `Player.websocket` excluded from JSON serialization.
- Gemini optional — fallback question bank keeps backend running.
- WSL ADB cannot see USB devices — use Windows PowerShell ADB.
- After any frontend change: `npx cap sync android` then rebuild APK.
- profiles.json is ephemeral on Cloud Run — localStorage is client-side source of truth.
- **Supabase leaderboard is secondary truth** — localStorage wins for active session,
  Supabase is the persistent cross-session store updated at game end.
- Donation approval is intentionally manual — no webhook or automated verification.
- `donor_leaderboard` is a SQL VIEW, not a table — never try to insert into it.
- **Local dev server MUST be run from `forge/frontend/`** — not `forge/`.
- **supabase-client.js defer race** — fixed in M29 with `waitForSupabase()` polling.
- `/economy/sync` and `/economy/reward` now require Bearer JWT — frontend passes
  `State.user._credential` which is only available in the same browser session
  (not after page reload). Supabase boot-sync handles the reload case instead.

---

## 📋 Technical Guidelines
1. Clean, commented code with docstrings.
2. Explain the "why" behind async/WebSocket logic.
3. Modular chunks — one file at a time.
4. Updated CLAUDE.md after each milestone.
5. Never suggest paid services. $0 constraint always applies.
6. ARM64: flag any compat issues proactively.
7. Fix root cause, not symptoms.
8. Frontend production points to live Cloud Run URL; local dev auto-switches.
9. Design language: blue/white, Press Start 2P, Nunito, yellow #FFD93D, Kahoot buttons.
10. ADB commands: Windows PowerShell only.
11. Never re-introduce banned ad networks.
12. Supabase RLS must always be enabled — never disable it.
13. Landing page must always be the default boot destination — AdSense requirement.
14. File contents over reconstruction — paste current files at session start.