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

## 💰 Monetization Strategy

### Current Approach
1. **Google AdSense** (primary goal) — pending approval.
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
- [ ] AdSense manual review approval — PENDING (PAN card pending)

---

## 🗄️ Supabase (Added Milestone 27)

### Project
- **URL:** `https://ffstsbwkianjcjpqvmtv.supabase.co`
- **Anon key:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (full key in supabase-client.js)
- **Region:** Southeast Asia (Singapore)
- **Dashboard:** supabase.com → project `forge`

### Tables
| Table | Purpose |
|-------|---------|
| `leaderboard` | One row per player. `google_id` PK. Upserted on game end. |
| `donations` | One row per UPI claim. `status`: pending → approved → rejected. |
| `donor_leaderboard` | VIEW. Auto-sums approved donations per person. Read-only. |

### Key rules
- Leaderboard upsert fires in `applyUserEconomy()` (index.html) — fire-and-forget, never blocks UI
- `lbUpsertPlayer()` uses `onConflict: 'google_id'` — playing again updates the row, NEVER resets it
- The anon key only has permissions defined in RLS policies — safe to be in frontend
- Donation approval is 100% manual: Supabase dashboard → Table Editor → donations → edit row → set status to 'approved'
- `donor_leaderboard` view auto-updates — no action needed after approving a donation row

### Admin workflow (approving donations)
1. Go to supabase.com → your project → Table Editor → `donations`
2. Find rows with `status = pending`
3. Cross-check the `upi_txn_id` in your UPI app
4. Click the row → edit → change `status` to `approved` → save
5. The donor leaderboard at `/leaderboard.html` updates on next page load

### Supabase helper functions (supabase-client.js)
| Function | Purpose |
|----------|---------|
| `lbUpsertPlayer(id, name, coins, trophies)` | Upsert leaderboard row |
| `lbFetch(column, limit)` | Fetch top N by coins or trophies |
| `lbFetchDonors(limit)` | Fetch donor leaderboard |
| `donationSubmit(name, id, amount, txnId)` | Submit donation claim |

---

## 🏗️ Tech Stack (LOCKED — do not suggest changes)

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | HTML5 + Tailwind CSS + Vanilla JS | Stays portable for CapacitorJS |
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
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── app/
│       ├── core/         config.py, state.py, limiter.py
│       ├── models/       quiz.py
│       ├── routers/      http.py, websocket.py, auth.py
│       └── services/     ai.py, profiles.py
└── frontend/
    ├── index.html             ← App shell + Supabase SDK + upsert hook ✅
    ├── supabase-client.js     ← Supabase singleton + helper functions ✅ NEW
    ├── leaderboard.html       ← Public leaderboard (3 tabs + donation form) ✅ NEW
    ├── privacy.html
    ├── about.html
    ├── contact.html
    ├── terms.html
    ├── robots.txt
    ├── sitemap.xml            ← leaderboard.html added ✅
    └── screens/
        ├── landing.html
        ├── home.html          ← 🏆 trophy button (top-left) ✅
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
| Frontend | Vercel (auto-deploys from git push) |

### Re-deploy backend
```bash
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

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe |
| POST | `/rooms/create` | Create room |
| GET | `/rooms/{code}` | Inspect room |
| DELETE | `/rooms/{code}` | Remove room |
| POST | `/auth/google` | Verify Google ID token |
| POST | `/economy/reward` | Apply coin reward |

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

### Client → Server
```json
{ "action": "start_game", "topic": "...", "mode": "hard", "play_mode": "classic" }
{ "action": "answer",     "choice": 2,   "time_ms": 3400 }
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
| 28 | Play Store submission | 🔲 Blocked (needs ID) |

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
- Leaderboard page fetches once on load, no polling. Refresh page for latest data.

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