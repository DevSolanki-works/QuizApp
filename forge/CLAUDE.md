# CLAUDE.md — Forge: AI Trivia Showdown

> **Context Routine:** Paste this file at the start of every new conversation so Claude has full context.
> **Maintenance Protocol:** Claude updates this file after every major milestone and provides the new version as a complete copyable block.

---

## 🧠 Who I Am

- **Status:** 2nd-year CS AI/ML student (Strong Python background, currently learning full-stack).
- **Timeline:** Building this over a 1-month vacation; continuing post-vacation as a live product.
- **Ultimate Goal:** Deploy to Google Play Store + monetize via AdMob rewarded ads + in-game economy. $0 infrastructure constraint.
- **Hardware Architecture:** ARM64 machine.
- **Development Environment:** WSL (Ubuntu) on Windows; Python virtual environment located at `backend/.venv`.

---

## 🎮 Project Overview: Forge — AI Trivia Showdown

A real-time multiplayer mobile quiz game. Players enter **ANY** topic → AI generates a custom quiz → players compete live via WebSockets using a 4-digit room code.

---

## 🪓 STRATEGIC PIVOT (Milestone 31): Website vs App Workflow Split

> ⚠️ **CRITICAL ARCHITECTURAL NOTICE**
> The Website and App are split into two separate development tracks sharing the same backend.

### The Split

- **Website (`forgetrivia.online`):** Frozen. Exists for AdSense revenue + SEO discoverability. Zero feature development.
- **App (Android via Capacitor):** Primary development priority. Full-featured premium tier.

### ❄️ What Stays Frozen (Website Track)

No feature work on `forgetrivia.online`. Keep all AdSense-required pages exactly as they are: `landing.html`, `about.html`, `privacy.html`, `terms.html`, `contact.html`, `how-to-play.html`, `topic-guide.html`, `trivia-tips.html`, `multiplayer-quiz-guide.html`, `ai-trivia-questions.html`, `dev-log.html`, `sitemap.xml`, `robots.txt`, `ads.txt` / `app-ads.txt`.

### ⚙️ Backend Stays Unified

The FastAPI backend is never forked. Web and app hit the same endpoints. Feature gating is UI-only — never backend-side.

### 📐 Architecture

- `frontend/web/` — frozen website
- `frontend/app/` — active Capacitor target, `capacitor.config.json` `webDir` points here
- Backend: single shared FastAPI service

---

## 📱 App UI Direction — Neo-Brutalism (Milestone 34+)

> **Locked June 22, 2026.** Dark charcoal backgrounds, thick black borders (2.5–3px), hard offset shadows (zero blur), flat green/red/cream color blocking, blocky low-radius corners. Archivo Black for hero wordmark only. Press Start 2P everywhere else.

### Design Tokens (App Track Only)

```css
:root {
  --nb-bg:         #181818;
  --nb-surface:    #1F1F1F;
  --nb-input:      #242424;
  --nb-black:      #0D0D0D;
  --nb-cream:      #EDE0C8;
  --nb-text:       #ECE7DA;
  --nb-text-dim:   rgba(236,231,218,0.5);
  --nb-green:      #3F6E52;
  --nb-green-dark: #2C4F3B;
  --nb-red:        #C0392B;
  --nb-red-dark:   #8E2A20;
  --nb-border-w:   3px;
  --nb-radius:     8px;
  --nb-shadow-sm:  4px 4px 0 var(--nb-black);
  --nb-shadow-lg:  6px 6px 0 var(--nb-black);
}
```

### Locked Home Screen Composition

Top to bottom: combined currency pill → hero zone (FORGE wordmark + trophy badge) → slim pill name entry → full-width SOLO PLAY button → 2-tile CREATE/JOIN row → inline join-by-code capsule → small utility row (Google sign-in, sound toggle) → meta footer.

**Firm rule:** functional inputs always render level. No rotation on fields the player must read or type into.

---

## 💰 Economy System — REDESIGNED (June 2026)

> **Critical distinction:** Coins and Trophies are completely separate systems with different purposes. They are never interchangeable.

### 🪙 Coins — Soft Currency (Spendable, Earnable)

Coins are the active economy. They are spent on entry fees and power-ups, earned through gameplay and rewarded ads, and have a real sink that gives them ongoing value.

**Starting balance:** 200 coins.

#### Coin Sources
| Source | Amount | Notes |
|--------|--------|-------|
| New profile | +200 | One-time starter balance |
| Solo win (≥5 correct) | +10 | Small passive income |
| Rewarded ad — Coin Bonus | +25–200 | Random lucky draw, once per day |
| Rewarded ad — Power-Up Refill | Free refill | See power-ups below |
| Rewarded ad — Entry Fee Recovery | Recover entry fee | Shown on loss, highest-motivation moment |
| Win Classic/Team room | +pot share | Redistributed entry fees |
| Pro Room win | +pot share + 10% house bonus | House adds 10% to the pot |

#### Coin Sinks
| Sink | Cost | Notes |
|------|------|-------|
| Classic/Team room entry | 25 coins | All rooms except Solo |
| Pro Room entry | 100 coins | Higher stakes tier |
| High Stakes room entry | 500 coins | Top tier, pot shared by top 3 |
| 1v1 Duel entry | 50 coins | Online mode (see below) |
| Power-up: Topic Veto | 50 coins | Reject one topic before game starts |
| Power-up: Lifeline (50/50) | 75 coins | Eliminate two wrong answers, one question |
| Power-up: Time Freeze | 60 coins | Pause timer 5s, one question |
| Power-up: Double Down | 100 coins | Double score on next question or zero it |

#### Tiered Room Stakes
Three room tiers create meaningful stakes without being pay-to-win:

- **Casual (25 coins):** Friendly, default entry. Winner takes pot.
- **Pro (100 coins):** House adds 10% bonus to pot. Winner takes pot + bonus.
- **High Stakes (500 coins):** Top 3 split pot proportionally (50%/30%/20%).

This tier system is the primary driver for players to watch rewarded ads (to refill their balance after losses).

### 🏆 Trophies — Ranked Progression (ELO-adjacent, never spent)

Trophies measure skill and competitive standing. They are **never spent** — only won or lost through ranked play. They gate trophy-room matchmaking and unlock cosmetic milestones.

**Starting balance:** 50 trophies.

#### Trophy Delta Formula
```
Win vs. higher trophy player  → +30 trophies
Win vs. equal trophy player   → +25 trophies
Win vs. lower trophy player   → +15 trophies
Loss vs. higher trophy player → -10 trophies
Loss vs. equal trophy player  → -20 trophies
Loss vs. lower trophy player  → -30 trophies
```

#### Trophy Floors
Trophies cannot drop below tier floors: 0, 100, 200, 500, 1000. Players cannot spiral into frustration below their earned tier.

#### Trophy Tiers (Rank Labels)
| Trophies | Rank |
|----------|------|
| 0–19 | ROOKIE |
| 20–49 | APPRENTICE |
| 50–99 | SKILLED |
| 100–199 | EXPERT |
| 200–499 | CHAMPION |
| 500–999 | MASTER |
| 1000+ | GRANDMASTER |

Tier-up events show a full-screen ceremonial animation + a shareable card ("I just reached CHAMPION in Forge!") — the primary organic marketing hook.

#### Solo Trophy Rules (unchanged)
| Performance | Trophies |
|-------------|----------|
| < 4 correct | -2 |
| 4–5 correct | +1 |
| 6–10 correct | +2 per correct above 5 |

---

## 📣 Ads System — AdMob Rewarded (App Only)

> **⚡ CRITICAL PRIORITY RULE:** The moment AdSense/AdMob approval is confirmed and ads can go live, ALL other milestone work pauses. The only focus becomes integrating ads into the existing codebase so monetization starts immediately. Resume normal milestones once ads are live and earning.

### Ad Types

**Only rewarded ads in the app.** No banners, no interstitials, no intrusive formats. Players watch ads voluntarily in exchange for specific in-game value.

### Rewarded Ad Triggers (contextually motivated moments)

These are placed at moments of high psychological motivation, never as generic buttons:

1. **Entry Fee Recovery** — Shown immediately after losing a Casual/Pro/High Stakes room. "Watch an ad to recover your [X] coin entry fee." Highest-motivation placement. Loss aversion drives completion rates.

2. **Power-Up Refill** — Shown mid-game when a player uses their last power-up on a high-stakes question. "Watch an ad to get one more Lifeline." Offered only once per game.

3. **Daily Lucky Draw** — Once per day, a slot-machine animation spins and lands on a coin reward (25–200 coins, weighted toward 25). A second spin requires watching an ad. The randomness makes this feel like play, not a transaction.

4. **Streak Saver** — If a player's daily streak is about to break (hasn't played today, it's after 6pm), push notification + in-app prompt: "Watch an ad to bank a streak freeze." Keeps streak alive without playing. Extremely high motivation.

5. **Double Winnings** — After winning a room, offer to double coin winnings by watching an ad. "You won 150 coins. Watch an ad to make it 300." Post-win euphoria drives completion.

### What NOT to Do

- No banner ads anywhere in the app.
- No interstitial ads between screens.
- No ad button on the home screen ("Earn Coins" as a static CTA is low-value and annoying).
- No Monetag, popunders, or any non-AdMob network.

### AdMob Integration Checklist (activate when approved)

- [ ] Add AdMob dependency to `android/app/build.gradle`
- [ ] Add App ID to `AndroidManifest.xml`
- [ ] Add `@admob/capacitor-admob` or `capacitor-community/admob` plugin
- [ ] Add AdMob App ID to `capacitor.config.json`
- [ ] Implement `RewardedAd` class wrapper in `frontend/app/admob.js`
- [ ] Wire Entry Fee Recovery trigger in `results.html` `_renderEconomyResult()`
- [ ] Wire Daily Lucky Draw trigger in `home.html` `onHomeShow()`
- [ ] Wire Power-Up Refill trigger in `game.html` power-up usage handler
- [ ] Wire Double Winnings trigger in `results.html` winner path
- [ ] Wire Streak Saver trigger in notification + home screen
- [ ] Test all placements with test ad unit IDs before going live
- [ ] Replace test IDs with production IDs
- [ ] Submit updated APK to Amazon App Store

---

## 🌐 Online 1v1 Duel Mode — Design Spec

> **Implementation order:** Async Challenge first (no matchmaking needed), then Sync 1v1 (requires queue).

### Topic Selection — Blind Draft System

Neither player knows whose topic was chosen until the game starts:

1. Both players independently submit 1 topic suggestion (30s window).
2. System randomly picks one from the two submissions.
3. "YOUR OPPONENT'S TOPIC: Medieval Warfare" reveal screen with 3s countdown.
4. Game starts on the chosen topic.

This prevents the "study your niche" exploit because you don't know if your topic gets picked. The reveal moment creates genuine tension.

**Fallback:** If either player doesn't submit within 30s, their slot gets a random topic from 10 curated categories. If both time out, both get random.

### Scoring in 1v1

Same speed-based formula as Classic mode. No streak multipliers in 1v1 (keeps it cleaner for head-to-head). First to answer a question correctly gets a 50-point speed bonus on top of base score.

### Power-ups in 1v1

Power-ups are visible to both players (transparency prevents frustration). Both players see "[Name] used a Lifeline!" notification. This makes power-ups a strategic layer rather than a hidden exploit.

### Async Challenge Mode (implement first)

No live coordination required — highest-value feature for launch:

1. Player A completes any solo game → gets option "Challenge a friend to beat this score."
2. System generates a shareable link/code: "Can you beat my 8400 on Marvel Movies?"
3. Player B opens the link, plays the same questions (cached, generated once).
4. Player B's score vs. Player A's ghost (visual indicator showing where A was at each question).
5. 24-hour window. Result notified via push.

Ghost system: during Player B's game, a ghost bar shows Player A's progress at the equivalent question. "You're 200 points ahead of Dev's ghost." This creates competition without simultaneous play.

### Sync 1v1 Queue (implement second)

Backend matchmaking queue matching players within ±100 trophies. 30s wait max; if no match found, offer to play vs. a bot (same questions, bot answers at random speed to simulate human). Entry fee: 50 coins.

---

## 🎯 Engagement Systems

### Knowledge Domains / Specializations

Track per-topic-category win rates in Supabase. After enough games in a category, player earns a domain badge shown on leaderboard and in 1v1 rooms:

- 10 games in Science topics → "🔬 Science Enthusiast"
- 20 games + 60% win rate → "🔬 Science Expert"
- 50 games + 70% win rate → "🔬 Science Master"

These are free to implement, create player identity, and give a reason to specialize.

### Topic Bounties (Weekly)

Every Monday, announce a "Bounty Topic" (e.g., "Ancient Egypt this week"). Players who play any game on that topic category during the week get 2x trophy multiplier on those games. Drives content discovery + gives a weekly notification hook that isn't spammy.

### Weekly Progression Layer

```
Daily  : Play any game → maintain streak → small coin bonus
Weekly : Win 10 games → "Weekly Champion" coin bonus (100 coins)
Monthly: Reach new trophy tier → cosmetic unlock (badge, name color)
```

### Tier-Up Ceremonies

Full-screen animation when reaching a new trophy tier. Shareable card generated: "I just reached CHAMPION in Forge — 200 Trophies! 🏆 Can you beat me?" This is the primary organic marketing mechanism.

### Forge Challenges (Async 1v1 — see above)

---

## 💻 Local Development

### ⚠️ CRITICAL: Frontend Directory Rule

```bash
# ✅ CORRECT — always serve from app subdirectory
cd forge/frontend/app && python3 -m http.server 8080

# ❌ INCORRECT — breaks absolute asset routing
cd forge && python3 -m http.server 8080
```

### Start Backend

```bash
cd forge/backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

### Local URLs

- Frontend: `http://127.0.0.1:8080`
- Backend: `http://127.0.0.1:8000`
- API Docs: `http://127.0.0.1:8000/docs`

---

## 🏗️ Technical Stack


| Layer | Selection | Notes |
|-------|-----------|-------|
| Frontend | HTML5 / CSS3 / Vanilla JS | No bundler, Capacitor-compatible |
| Database | Supabase (Postgres) | Free tier, display/cross-session mirror |
| Mobile | CapacitorJS -> Android | Package ID: `com.devsolanki.forge` |
| Backend | Python 3 / FastAPI | Async WebSocket game loop |
| AI | Gemini 2.5 Flash Lite | Free tier, fallback question bank |
| Real-time | FastAPI WebSockets | Low-latency state sync |
| Runtime State | In-memory rooms + file-backed profiles | Backend runtime truth for economy/tickets |
| Deployment | Docker -> Cloud Run | Serverless, $0 infrastructure |
| Ads | AdMob (pending approval) | Rewarded ads only in app |

---

## Monetization Strategy

1. **Google AdSense (Primary Web Driver):** Web track deployment only. Pending manual configuration review approval.
2. **Chai4Me Micro-Donations:** Web track deployment only.
3. **In-Game Soft Currency:** Coins and trophies accumulated across gameplay sessions.
4. **App Acquisition Funnel:** Drive Play Store downloads by making the app the full-featured tier.
5. **AdMob:** Rewarded ads only in app after approval.

### Deprecated / Forbidden Ad Technologies

Never integrate low-tier, high-intrusion monetization tools: Monetag, vignette/interstitial ads, popunders, force-push notification monetization assets, or instant-approval programmatic platforms.

### AdSense Landing Page Enforcement

`landing.html` must remain the explicit entry screen for cold website loads. Do not change website crawler routing.

---

## Security Hardening (Milestone 29)

| Source File Target | Nature of Modifications / Security Patch |
| --- | --- |
| `app/core/sanitize.py` | Structural WebSocket input validation. |
| `app/core/limiter.py` | XFF handling targets Cloud Run's trusted final IP. |
| `app/routers/http.py` | `/economy/sync`, `/economy/reward`, and ticket spend-side endpoints require matching Google identity where relevant. |
| `app/routers/websocket.py` | Validated action allowlist, sanitized topics, and rate-limited connection setup. |
| `frontend/app/index.html` | Route guards and backend sync calls with Google bearer token where required. |

### Security Model

- **WebSocket ingestion:** Every client message is validated against an allowlist.
- **Prompt injection defense:** Topics are checked before Gemini generation.
- **Financial protection:** Economy-changing HTTP calls require Google token ownership checks.
- **Rate limiting:** Connection and action quotas are enforced per IP.
- **Route guards:** Frontend blocks direct navigation to game/results without valid session state.
- **Timestamp calibration:** `time_ms` is clamped server-side.

---

## Supabase Persistence Engine (Milestone 27)

- **Endpoint URL:** `https://ffstsbwkianjcjpqvmtv.supabase.co`
- **Regional Hosting:** Southeast Asia (Singapore)
- **Purpose:** Long-term display/cross-session mirror for leaderboard and profile-adjacent data.

Runtime rooms and economy/ticket enforcement stay backend-side; Supabase mirrors the values the client syncs after gameplay.

---

## 📁 Project Structure

```
forge/
├── CLAUDE.md
├── package.json
├── capacitor.config.json
├── android/
├── assets/                    ← Master branding assets
│   ├── icon.png
│   ├── icon-foreground.png
│   ├── icon-background.png
│   └── splash.png
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── app/
│       ├── core/              ← config.py, state.py, limiter.py, sanitize.py
│       ├── models/            ← quiz.py
│       ├── routers/           ← http.py, websocket.py, auth.py
│       └── services/          ← ai.py, profiles.py
└── frontend/
    ├── web/                   ← FROZEN. Never touched by app work.
    │   └── [full pre-split site]
    └── app/                   ← ACTIVE. Capacitor target.
        ├── index.html
        ├── app.js
        ├── platform.js
        ├── supabase-client.js
        ├── admob.js            ← TO CREATE when ads approved
        ├── privacy.html
        ├── terms.html
        ├── leaderboard.html   ← Pending conversion to in-app screen
        ├── components/
        │   ├── leaderboard.js
        │   └── timer.js
        └── screens/
            ├── home.html
            ├── lobby.html
            ├── game.html
            ├── results.html
            ├── leaderboard.html
            └── settings.html
```

---

## 🚀 Production Infrastructure

| Property | Value |
|----------|-------|
| Website | `https://forgetrivia.online` |
| Backend | `https://forge-backend-878124462453.us-central1.run.app` |
| Frontend CI/CD | Vercel (auto-deploy on push to `main`) |
| App Distribution | Amazon App Store (APK, not AAB) |
| Auth / DB | Supabase `ffstsbwkianjcjpqvmtv` |
| Google Client ID | `878124462453-g7skbojds4uqg442hb9d31ftrlll095r.apps.googleusercontent.com` |
| AdSense Publisher | `ca-pub-4922314688440658` (web only) |

### Backend Redeploy

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

## 🔌 WebSocket Protocol

### Server → Client

```json
{ "type": "PLAYER_JOINED",  "data": { "players": [...], "lobby_mode": "classic", "locked": false } }
{ "type": "GAME_STARTING",  "data": { "topic": "...", "mode": "medium", "play_mode": "classic", "total_questions": 10 } }
{ "type": "QUESTION",       "data": { "index": 0, "text": "...", "options": [...], "time_limit_ms": 20000 } }
{ "type": "ANSWER_REVEAL",  "data": { "correct_index": 1, "scores": {...}, "streaks": {...} } }
{ "type": "INTERMISSION_LEADERBOARD", "data": { "scores": {...}, "is_final": false } }
{ "type": "GAME_OVER",      "data": { "final_scores": {...}, "economy": {...} } }
{ "type": "ERROR",          "data": { "message": "..." } }
```

### Client → Server

```json
{ "action": "start_game",   "topic": "...", "mode": "hard", "play_mode": "classic" }
{ "action": "answer",       "choice": 1, "time_ms": 3400 }
{ "action": "join_team",    "team_id": "A" }
{ "action": "set_team_info","name_a": "...", "name_b": "...", "topic_a": "...", "topic_b": "..." }
{ "action": "set_lobby_mode","mode": "team" }
{ "action": "lock_room" }
{ "action": "unlock_room" }
```

---

## 📐 Scoring Formula


```python
# Base (speed-based)
base = max(500, min(1000, int(1000 * (1 - (time_ms / time_limit_ms) * 0.5))))

# Streak multiplier
multi = min(1.0 + (streak // 3) * 0.5, 3.0)
# streak 0-2 -> x1.0 | 3-5 -> x1.5 | 6-8 -> x2.0 | 9-11 -> x2.5 | 12+ -> x3.0

final = int(base * multi)
```

---

## 🗄️ Supabase Schema


```text
leaderboard        : google_id (PK), display_name, coins, trophies,
                     daily_streak, last_played_date, updated_at,
                     tickets_today, ad_tickets_used_today, last_ticket_date
donations          : id (PK), upi_txn_id, status, amount
donor_leaderboard  : SQL VIEW - read only
question_bank      : id (PK), category, question, options, correct_idx,
                     difficulty, times_used, created_at
```

### Implemented Schema Additions

```sql
alter table public.leaderboard
  add column if not exists tickets_today int default 3,
  add column if not exists ad_tickets_used_today int default 0,
  add column if not exists last_ticket_date text default '';
```

```sql
create table if not exists public.question_bank (
  id uuid primary key default gen_random_uuid(),
  category text not null,
  question text not null,
  options jsonb not null,
  correct_idx int not null,
  difficulty text default 'medium',
  times_used int default 0,
  created_at timestamptz default now()
);

create index if not exists idx_question_bank_category
  on public.question_bank (category);

alter table public.question_bank enable row level security;
```

**Future additions under consideration:**
- `domain_stats` table: `google_id, category, games_played, wins, badge_level`
- `challenges` table: `id, challenger_id, opponent_id, topic, questions_json, challenger_score, expires_at`
- `power_up_purchases` table: `google_id, power_up_type, purchased_at` (analytics only)

---

## ✅ Milestone Tracker


| # | Description | Status |
|---|-------------|--------|
| 1-16 | Initial architecture through session persistence | Done |
| 17 | Google Federated Authentication | Done |
| 18 | Compliance pages & base navigation | Done |
| 19 | Streaks and multiplier scoring | Done |
| 20 | Team Mode | Done |
| 21 | Room locking | Done |
| 22 | UI input stabilization | Done |
| 23 | Solo mode + coin economy + CI/CD | Done |
| 24 | LocalStorage economy persistence | Done |
| 25 | Monetization setup (landing + Chai4Me) | Done |
| 26 | Cookie consent | Done |
| 27 | Supabase global leaderboard | Done |
| 28 | Play Store pipeline | Blocked (PAN verification) |
| 29 | Security hardening | Done |
| 29.5 | App branding assets (icons/splash) | Done |
| 29.6 | Amazon App Store submission | Done |
| 30 | AdSense compliance expansion | Done |
| 31 | Strategic pivot - frontend fork resolved | Done |
| 31.5 | Physical folder split (`frontend/web` + `frontend/app`) | Done |
| 32 | App: remove out-of-scope compliance assets | Done |
| 33 | App: feature gating (web restricted) | Queued |
| 34 | App: Neo-Brutalism home screen | Done |
| 35 | Generation Tickets - Real Spendable Currency | Done |
| 36 | Seed Question Bank data layer | In Progress |

---

## Decisions Log & Known Issues

- **Ads jump the queue:** When AdMob approval comes through, stop everything else and integrate ads first. One focused session to wire rewarded ad placements, test with test IDs, switch to production IDs, and push APK.
- **Workflow Split Decision (June 18, 2026):** The website codebase is frozen. App builds are the active frontier.
- **Frontend Fork Decision (June 19, 2026):** Frontend physically splits into `frontend/web/` and `frontend/app/`; backend remains single and shared across both targets.
- **Ticket Sync Source-of-Truth (June 30, 2026):** Generation tickets follow the same pattern as coins and trophies: the backend file-backed profile store is runtime truth, and Supabase `leaderboard` is only a display mirror. The mirror update lives in `frontend/app/index.html` inside `applyUserEconomy()`, which fetches `GET /tickets/{user_id}` and passes the result into `frontend/app/supabase-client.js` `lbUpsertPlayer()`.
- **Generation Tickets & Question Bank Data Layer (June 30, 2026):** Custom Room generation ticket refund-on-failure follows the same pattern as entry fee refunds. The rewarded-ad ticket cap is enforced server-side in `backend/app/services/tickets.py`. The reviewable question bank seed file lives at `supabase/seeds/seed_question_bank.py`.
- **Cloud Run state:** Runtime file storage is ephemeral. `profiles.json` is the backend runtime source of truth during a live process, and Supabase mirrors long-term display data after client sync.
- **Leaderboard Sync Behavior:** The Supabase leaderboard is a secondary cross-session/display mirror updated at game end.
- **Rewarded ad timing rule:** Never show a rewarded ad prompt during an active game. Only in lobby, post-game results, or home screen.
- **Fire OS / Google Sign-In:** Fire OS has no Google Play Services; guest play is shown instead.
- **BGM unlock:** `AudioContext.resume()` must be called synchronously within a direct user gesture handler.
- **WSL `/mnt/c` friction:** Repo at `/mnt/c/QuizApp/forge` has caused silent `mv` failures and broken npm symlinks. Long-term: relocate to `~/forge`.
- **New APK checklist:** Any `frontend/app/` or `android/` change -> `npx cap sync` -> versionCode bump -> Generate Signed Bundle -> store upload. Backend-only changes never need a new APK.
- **Keystore:** `keystore.properties` lives at `forge/android/keystore.properties`.
- **Amazon App Store:** Strips and re-signs APKs. No Play App Signing needed.
- **Gemini reliability:** Generation is timeout-wrapped with fallback questions.
- **Frontend local dev server:** Must run from `forge/frontend/app/`, not `forge/`. Screens load through `index.html`.
- **Visual Identity Pivot (June 20, 2026):** Neo-Brutalism supersedes the older Clash Royale-inspired direction.
- **No Rotating Functional Inputs:** Name-entry and room-code fields must always render level.

---

## Implementation Guidelines

1. **Code standards:** Self-documenting code with Python typing and descriptive docstrings.
2. **Workflow:** Keep changes scoped and avoid touching frozen website assets unless explicitly requested.
3. **Economy integrity:** File-backed backend state is runtime truth; Supabase mirrors display/cross-session data through explicit sync paths.
4. **$0 infrastructure:** No paid cloud integrations. Free tiers only.
5. **ARM64 builds:** Always use `docker buildx --platform linux/amd64 --push` for Cloud Run images.
6. **Visual split:** Website uses the frozen blue/yellow pixel-arcade palette. App uses active Neo-Brutalism direction.
7. **Ads are contextual, never intrusive:** Rewarded only. No banners, interstitials, popunders, or forced views.
8. **Database protection:** Keep RLS active on Supabase tables.
9. **Context maintenance:** Update `CLAUDE.md` after major milestones.
10. **Device operations:** Execute native terminal commands using Windows PowerShell exclusively.
