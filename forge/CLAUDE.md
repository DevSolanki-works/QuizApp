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
| Database | Supabase (Postgres) | Free tier, $0 constraint |
| Mobile | CapacitorJS → Android | Package ID: `com.devsolanki.forge` |
| Backend | Python 3 / FastAPI | Async WebSocket game loop |
| AI | Gemini 2.5 Flash Lite | Free tier, fallback question bank |
| Real-time | FastAPI WebSockets | Low-latency state sync |
| State | In-memory Python dict | Ephemeral, acceptable for MVP |
| Deployment | Docker → Cloud Run | Serverless, $0 infrastructure |
| Ads | AdMob (pending approval) | Rewarded ads only in app |

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
# streak 0-2 → ×1.0 | 3-5 → ×1.5 | 6-8 → ×2.0 | 9-11 → ×2.5 | 12+ → ×3.0

final = int(base * multi)
```

---

## 🗄️ Supabase Schema

```
leaderboard        : google_id (PK), display_name, coins, trophies,
                     daily_streak, last_played_date, updated_at
donations          : id (PK), upi_txn_id, status, amount
donor_leaderboard  : SQL VIEW — read only
```

**Future additions needed:**
- `domain_stats` table: `google_id, category, games_played, wins, badge_level`
- `challenges` table: `id, challenger_id, opponent_id, topic, questions_json, challenger_score, expires_at`
- `power_up_purchases` table: `google_id, power_up_type, purchased_at` (for analytics)

---

## ✅ Milestone Tracker

| # | Description | Status |
|---|-------------|--------|
| 1–16 | Initial architecture through session persistence | ✅ Done |
| 17 | Google Federated Authentication | ✅ Done |
| 18 | Compliance pages & base navigation | ✅ Done |
| 19 | Streaks and multiplier scoring | ✅ Done |
| 20 | Team Mode | ✅ Done |
| 21 | Room locking | ✅ Done |
| 22 | UI input stabilization | ✅ Done |
| 23 | Solo mode + coin economy + CI/CD | ✅ Done |
| 24 | LocalStorage economy persistence | ✅ Done |
| 25 | Monetization setup (landing + Chai4Me) | ✅ Done |
| 26 | Cookie consent | ✅ Done |
| 27 | Supabase global leaderboard | ✅ Done |
| 28 | Play Store pipeline | 🔲 Blocked (PAN verification) |
| 29 | Security hardening | ✅ Done |
| 29.5 | App branding assets (icons/splash) | ✅ Done |
| 29.6 | Amazon App Store submission | ✅ Done |
| 30 | AdSense compliance expansion | ✅ Done |
| 31 | Strategic pivot — frontend fork resolved | ✅ Done |
| 31.5 | Physical folder split (web/ + app/) | 🔲 Next |
| 32 | App: remove out-of-scope compliance assets | ✅ Done |
| 33 | App: feature gating (web restricted) | 🔲 Queued |
| 34 | App: Neo-Brutalism home screen | ✅ Done |
| **ADS** | **⚡ AdMob integration — JUMPS QUEUE when approved** | ⏳ Awaiting approval |
| 35 | Tiered room stakes (Casual/Pro/High Stakes entry fees) | 🔲 Queued |
| 36 | Power-up system (Topic Veto, Lifeline, Time Freeze, Double Down) | 🔲 Queued |
| 37 | Trophy ELO redesign (delta formula + floors + tier labels) | 🔲 Queued |
| 38 | Trophy tier-up ceremony (full-screen animation + shareable card) | 🔲 Queued |
| 39 | Async Challenge Mode (ghost system, cached questions, share link) | 🔲 Queued |
| 40 | Daily Lucky Draw (slot machine UI, rewarded ad second spin) | 🔲 Queued |
| 41 | Knowledge Domain badges (per-category win tracking, Supabase) | 🔲 Queued |
| 42 | Weekly Topic Bounties (2x trophy multiplier, weekly notification) | 🔲 Queued |
| 43 | Sync 1v1 Duel Mode (Blind Draft topic system, matchmaking queue) | 🔲 Queued |
| 44 | Bot opponent fallback for unmatched 1v1 queue | 🔲 Queued |
| 45 | Weekly progression rewards (10 wins → 100 coin bonus) | 🔲 Queued |
| 46 | Cosmetic unlocks (name color, badge frames at trophy milestones) | 🔲 Queued |
| 47 | Google Play Store submission (pending PAN clearance) | 🔲 Blocked |

---

## 🐛 Decisions Log & Known Issues

- **Ads jump the queue:** When AdMob approval comes through, stop everything else and integrate ads first. One focused session to wire all 5 rewarded ad placements, test with test IDs, switch to production IDs, push APK. Resume normal milestones after first ad impression confirmed.
- **Economy source of truth:** Supabase is authoritative. The backend `profiles.json` is a secondary cache that syncs from Supabase. `localStorage` is for ephemeral UI state only — never the economy ground truth.
- **Power-ups are pre-purchase, not in-game purchases:** Player buys power-ups before a game starts (from lobby), not mid-round. This avoids timing complexity in the WebSocket game loop.
- **Async Challenge questions cached:** When Player A starts a challenge, Gemini generates questions once and stores them in Supabase `challenges` table. Player B gets identical questions. Never re-generate.
- **1v1 matchmaking tolerance:** ±100 trophies within 30s wait. If no match, offer bot. Never force a wildly mismatched game.
- **Trophy floors are local UI only:** Backend enforces floors via `max(floor, trophies - delta)`. Frontend never shows negative deltas past the floor.
- **Domain badges are display only:** Never gate gameplay behind domain badges. They are identity/cosmetic only.
- **Rewarded ad timing rule:** Never show a rewarded ad prompt during an active game. Only in lobby, post-game results, or home screen.
- **Fire OS / Google Sign-In:** Fire OS detected via user agent (`/\bKF[A-Z]{2,4}\b/`); guest play shown instead since Fire OS has no Google Play Services.
- **BGM unlock:** `AudioContext.resume()` must be called synchronously within a direct user gesture handler. No workarounds work reliably on Capacitor WebView.
- **WSL `/mnt/c` friction:** Repo at `/mnt/c/QuizApp/forge`. This bridge has caused silent `mv` failures and broken npm symlinks. Long-term: relocate to `~/forge`.
- **New APK checklist:** Any `frontend/app/` or `android/` change → `npx cap sync` → versionCode bump → Generate Signed Bundle → store upload. Backend-only changes never need a new APK.
- **Cloud Run state:** Ephemeral filesystem. `profiles.json` wipes on scale-to-zero. Supabase is the real persistence layer.
- **Keystore:** `keystore.properties` (not `key.properties`) at `forge/android/keystore.properties`.
- **Amazon App Store:** Strips and re-signs APKs. No Play App Signing needed. Same APK goes to both stores.
- **Gemini reliability:** Wrapped in `asyncio.timeout` (12s) with silent fallback to local question bank.
- **Frontend local dev server:** Must run from `forge/frontend/app/`, not `forge/`. Screens load via `goTo()` / `fetch()` through `index.html`. Always develop via `index.html#home`.

---

## 📋 Implementation Guidelines

1. **Code standards:** Self-documenting code with Python typing and descriptive docstrings.
2. **Deliverable format:** Complete file replacements, not diffs or snippets. Gemini CLI used to apply.
3. **Workflow:** Architectural plan reviewed before implementation. Explicit confirmation before any destructive operation.
4. **Ads first rule:** AdMob approval → pause everything → integrate ads → resume milestones.
5. **Economy integrity:** Never award coins or trophies outside the defined rule table. No shortcuts.
6. **Power-ups are cosmetic difficulty modifiers, not pay-to-win:** Both players have equal access. Both players see when a power-up is used.
7. **$0 infrastructure:** No paid cloud integrations. Free tiers only.
8. **ARM64 builds:** Always use `docker buildx --platform linux/amd64 --push`.
9. **Visual split:** Website uses blue/yellow/pixel-arcade palette (frozen). App uses Neo-Brutalism palette (active).
10. **Website freeze:** All general development targets the app track by default unless explicitly instructed otherwise.
11. **No over-engineering:** Async Challenge Mode before Sync 1v1. Simple systems before complex ones.
12. **Ads are contextual, never intrusive:** Rewarded only. No banners, no interstitials, no forced views.