```markdown
# CLAUDE.md — Forge: AI Trivia Showdown

> **Context Routine:** Paste this file at the start of every new conversation so Claude has full context.
> **Maintenance Protocol:** Claude updates this file after every major milestone and provides the new version as a complete copyable block.

---

## 🧠 Who I Am

- **Status:** 2nd-year CS AI/ML student (Strong Python background, currently learning full-stack).
- **Current Phase:** App is LIVE on the Google Play Store in production. This is now a live product with real users, not a pre-launch project.
- **Ultimate Goal:** Sustainable Play Store growth + AdMob revenue + ongoing feature development. $0 infrastructure constraint.
- **Hardware Architecture:** ARM64 machine.
- **Development Environment:** WSL (Ubuntu) on Windows; Python virtual environment at `backend/.venv`; Android Studio + Gradle run on the Windows side.

---

## 🚨 CRITICAL: This Is a Live Product Now

**Real users have the app installed with real coins, trophies, tickets, and streaks.** This changes how every change must be approached:

- **Economy-changing backend changes are backward-compatibility risks.** A schema change, a renamed field, or altered gating logic can break the experience for users on an older client build who haven't updated yet — or silently corrupt their saved state on next sync.
- **Every `frontend/app/` release needs a version-mismatch safety net.** (See "Forced Update Screen" below — planned, not yet built as of this writing.)
- **Test on a real device via USB debug BEFORE shipping to production.** Never assume; localhost testing does not exercise WebSocket reconnect behavior, AdMob, Capacitor plugins, or real Google Sign-In token expiry.
- **Prefer Internal Testing track over direct-to-production** for anything touching economy, auth, or ads — near-instant propagation, no review wait, zero risk to live users.

---

## 🎮 Project Overview: Forge — AI Trivia Showdown

A real-time multiplayer mobile quiz game. Players enter **ANY** topic → AI generates a custom quiz → players compete live via WebSockets using a 4-digit room code. Live on Google Play Store, package ID `com.devsolanki.forge`.

---

## 🪓 STRATEGIC PIVOT (Milestone 31): Website vs App Workflow Split

> ⚠️ **CRITICAL ARCHITECTURAL NOTICE**
> The Website and App are split into two separate development tracks sharing the same backend.

### The Split

- **Website (`forgetrivia.online`):** Frozen. Exists for AdSense revenue + SEO discoverability. Zero feature development except `app-ads.txt` (actively maintained — required for AdMob app-ads.txt verification, distinct from web AdSense ads.txt).
- **App (Android via Capacitor):** Primary development priority. Full-featured premium tier.

### ❄️ What Stays Frozen (Website Track)

No feature work on `forgetrivia.online`. Keep all AdSense-required pages exactly as they are.

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

## 💰 Economy System

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
| Buy ticket | 25 coins | Shop screen |

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

#### Solo Trophy Rules

| Performance | Trophies |
|-------------|----------|
| < 4 correct | -2 |
| 4–5 correct | +1 |
| 6–10 correct | +2 per correct above 5 |

---

### 🎟️ Generation Tickets — REDESIGNED (July 2026)

> **Critical architecture note:** Tickets are now a pure, persistent balance — architecturally identical to coins. This was a deliberate fix after the old "3 free tickets/day, auto-resetting" design caused a cluster of real bugs (see Key Learnings below).

**How custom-topic generation is gated now:**

1. **Quick Pick topics** (Movies, Science, Cricket, etc.) — always free, always unlimited, no sign-in needed, in every mode.
2. **Custom typed topics** — first checks a **daily free-generation allowance**: 2 free generations per day, resetting at midnight, tracked in a single isolated counter (`free_generations_used_today` / `last_free_generation_date`), checked only inside `use_generation()`. This is the ONLY date-sensitive logic left in the whole ticket system, by design.
3. Once the daily free allowance is exhausted, custom generation spends 1 ticket from the player's persistent ticket balance.
4. Tickets are earned via: buying with coins (25 coins/ticket, Shop screen), rewarded ads (5/day cap via Shop), Daily Reward bonus tickets, and the Custom Topic Rewarded Interstitial (+1 free generation, not a ticket — see Ads System).

**Old design (deprecated, do not resurrect):** `tickets_today` auto-resetting to 3 every day. This caused a documented, painful bug — see Key Learnings.

### Daily Reward — 7-day cycle, now terminates after first full completion

Days 1–6: 10/20/30/40/50/60 coins + 1/1/1/1/2/3 tickets. Day 7: 100 coins + 5 tickets jackpot. **Once a player completes Day 7 once, the Daily Reward screen/prompt permanently stops showing for that account** (`reward_cycle_completed` flag, checked in `checkAndShowDailyReward()`). This does not loop back to Day 1 forever — intentional design change from the original spec.

---

## 📣 Ads System — LIVE, AdMob Integrated (July 2026)

> Real ads are live. `IS_TESTING` flags in `admob.js` reflect current production state per-format — check the file directly, don't assume.
> **Only rewarded and rewarded-interstitial ads in the app.** No banners, no plain interstitials on home/game screens. Players watch ads voluntarily in exchange for specific in-game value.

### Ad Formats In Use

Three distinct AdMob ad unit types are wired, each with its own wrapper object in `frontend/app/admob.js`:

1. **`RewardedAd`** — standard opt-in rewarded video (tap-to-watch).
2. **`RewardedInterstitial`** — auto-shows at natural transitions, no opt-in tap required, still pays a reward. Confirmed supported by `@capacitor-community/admob` via its `reward-interstitial/` module (`prepareRewardInterstitialAd` / `showRewardInterstitialAd`, events `onRewardedInterstitialAd*`). Requires a disclosure toast shown BEFORE the ad plays (Google policy requirement even without an opt-in tap) — current implementation shows a 3.5s toast, waits 3.5s, then fires the ad.
3. **`Interstitial`** — plain, non-rewarded, no disclosure needed. Used only as a monetization floor (every 2nd Quick Pick Solo game, or after 2 consecutive Custom Topic Rewarded Interstitial skips).

Each format needs its own distinct AdMob ad unit ID — do not reuse one ID across formats.

### Current Ad Triggers, By Mode

**Solo Mode:**
- **2X Coins / No Thanks** (`RewardedAd`) — replaces Play Again/Back Home on the results screen when the player earned coins (5+ correct). Immediate, tap-triggered.
- **Quick Pick interstitial** (`Interstitial`) — every 2nd Quick Pick Solo game, auto-fires 5s after results load, then counter resets. Watching the 2X Coins ad in the same session does NOT currently reset this counter (a planned addition, not yet built — confirm with Dev before assuming this exists).
- **Custom Topic Rewarded Interstitial** (`RewardedInterstitial`) — every 2nd Custom Topic Solo game, auto-fires 5s after results load (after the 3.5s disclosure toast). Reward: +1 free generation (backend: `POST /tickets/bonus-generation-grant`, service: `grant_bonus_generation()`). Two consecutive skips → next custom game gets a plain `Interstitial` instead as a floor.

**Classic & Team Mode:**
- **Entry Fee Recovery** (`RewardedAd`) — shown on loss in a paid room.
- **Double Winnings** (`RewardedAd`) — shown on win with a payout.

**Home Screen:**
- **Streak Saver** (`RewardedAd`) — NOT a front-page banner. Small pulsing "!" badge on the Day Streak stat (shown only if: signed in, haven't played today, streak ≥1, past 6pm local) — tap opens a modal with the watch-ad button. Moved off the front page deliberately for UX reasons (original banner placement looked unprofessional).

**Shop Screen:**
- **Watch Ad for Ticket** (`RewardedAd`) — capped at 5 grants/day server-side (hard cap, cannot be bypassed), PLUS a 2-minute client-side cooldown between individual grants (`localStorage`-based pacing/anti-farming friction, not a hard cap — can theoretically be bypassed by clearing app data, acceptable tradeoff).

### Planned / Not Yet Built

- **Daily Lucky Draw** (`RewardedAd`) — Once per day, a slot-machine animation spins and lands on a coin reward (25–200 coins, weighted toward 25). A second spin requires watching an ad.
- **Power-Up Refill** (`RewardedAd`) — Shown mid-game when a player uses their last power-up on a high-stakes question.
- Classic/Team mode interstitial/frequency-cap system.
- Quick Pick interstitial counter reset on 2X Coins engagement.

### What NOT to Do

- No banner ads anywhere in the app.
- No interstitial ads between screens (except the frequency-capped Solo flow above).
- No ad button on the home screen ("Earn Coins" as a static CTA is low-value and annoying).
- No Monetag, popunders, or any non-AdMob network.

### app-ads.txt

Lives at `forgetrivia.online/app-ads.txt` (root of the frozen web track, deployed via Vercel). Required for AdMob verification — ties the app to the Play Console "Developer website" field, which MUST match exactly (protocol + no trailing slash + no www mismatch) or verification silently fails with a generic "details don't match" error.

---

## 🌐 Online 1v1 Duel Mode — Design Spec

> **Implementation order:** Async Challenge first (no matchmaking needed), then Sync 1v1 (requires queue). No code exists for this yet.

### Topic Selection — Blind Draft System

Neither player knows whose topic was chosen until the game starts:

1. Both players independently submit 1 topic suggestion (30s window).
2. System randomly picks one from the two submissions.
3. "YOUR OPPONENT'S TOPIC: Medieval Warfare" reveal screen with 3s countdown.
4. Game starts on the chosen topic.

**Fallback:** If either player doesn't submit within 30s, their slot gets a random topic from 10 curated categories. If both time out, both get random.

### Scoring in 1v1

Same speed-based formula as Classic mode. No streak multipliers in 1v1 (keeps it cleaner for head-to-head). First to answer a question correctly gets a 50-point speed bonus on top of base score.

### Async Challenge Mode (implement first)

1. Player A completes any solo game → gets option "Challenge a friend to beat this score."
2. System generates a shareable link/code: "Can you beat my 8400 on Marvel Movies?"
3. Player B opens the link, plays the same questions (cached, generated once).
4. Player B's score vs. Player A's ghost (visual indicator showing where A was at each question).
5. 24-hour window. Result notified via push.

### Sync 1v1 Queue (implement second)

Backend matchmaking queue matching players within ±100 trophies. 30s wait max; if no match found, offer to play vs. a bot. Entry fee: 50 coins.

---

## 🎯 Engagement Systems

### Knowledge Domains / Specializations

Track per-topic-category win rates in Supabase. After enough games in a category, player earns a domain badge shown on leaderboard and in 1v1 rooms:

- 10 games in Science topics → "🔬 Science Enthusiast"
- 20 games + 60% win rate → "🔬 Science Expert"
- 50 games + 70% win rate → "🔬 Science Master"

### Topic Bounties (Weekly)

Every Monday, announce a "Bounty Topic." Players who play any game on that topic category during the week get 2x trophy multiplier on those games.

### Weekly Progression Layer

```
Daily  : Play any game → maintain streak → small coin bonus
Weekly : Win 10 games → "Weekly Champion" coin bonus (100 coins)
Monthly: Reach new trophy tier → cosmetic unlock (badge, name color)
```

### Tier-Up Ceremonies

Full-screen animation when reaching a new trophy tier. Shareable card generated: "I just reached CHAMPION in Forge — 200 Trophies! 🏆 Can you beat me?" This is the primary organic marketing mechanism.

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

### ⚠️ Router caches screens after first load

`goTo()` in `index.html` only fetches a screen's HTML once per page session (`el.dataset.loaded` guard). Editing a file under `screens/` requires a **hard reload** (Ctrl+Shift+R) to see changes — navigating back to a screen in the same tab shows stale cached DOM.

### On-device testing (USB debug — NOT Play Console)

Play Console tracks are for distribution, not iteration. For day-to-day testing including AdMob:
1. Enable USB debugging on phone, connect via USB.
2. `npx cap sync android`
3. Open `forge/android` in Android Studio (Windows side), select device, Run ▶.
4. `adb logcat` filtered for plugin name (e.g. `AdMob`) for debugging silent failures.

**Register your own device as an AdMob test device** (AdMob console → app settings) — this makes real ad unit IDs serve test ads automatically on that device regardless of `IS_TESTING` flag state, preventing accidental invalid-traffic self-clicks.

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
| Ads | AdMob (LIVE) | Rewarded + Rewarded-Interstitial + plain Interstitial floor |

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
leaderboard : google_id (PK), display_name, coins, trophies,
              daily_streak, last_played_date, updated_at,
              tickets_today, ad_tickets_used_today, last_ticket_date,
              free_generations_used_today, last_free_generation_date,
              last_reward_date, reward_day, reward_cycle_completed
donations   : id (PK), upi_txn_id, status, amount
donor_leaderboard : SQL VIEW - read only
```

Full column list confirmed current as of this writing — no missing columns, no pending migrations outstanding.

### Implemented Schema Additions

```sql
alter table public.leaderboard
  add column if not exists tickets_today int default 3,
  add column if not exists ad_tickets_used_today int default 0,
  add column if not exists last_ticket_date text default '';
```

**Future additions under consideration:**
- `domain_stats` table: `google_id, category, games_played, wins, badge_level`
- `challenges` table: `id, challenger_id, opponent_id, topic, questions_json, challenger_score, expires_at`
- `power_up_purchases` table: `google_id, power_up_type, purchased_at` (analytics only)

---

## 📁 Project Structure

```text
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
│       ├── models/            ← quiz.py (generation_source field added)
│       ├── routers/           ← http.py (/account/delete, /tickets/bonus-generation-grant added), websocket.py, auth.py
│       └── services/          ← ai.py, profiles.py (delete_profile() added), tickets.py (FULL REWRITE — pure balance model)
└── frontend/
    ├── web/                   ← FROZEN. Never touched by app work.
    │   └── app-ads.txt        ← actively maintained (AdMob requirement)
    └── app/                   ← ACTIVE. Capacitor target.
        ├── index.html         ← _markLocalEconomyWrite(), refreshUserProfile() grace window, _isAuthError()/_promptReauth() helpers
        ├── app.js
        ├── platform.js
        ├── supabase-client.js ← lbUpsertPlayer() fixed (was silently throwing), lbDeleteProfile() added
        ├── admob.js           ← RewardedAd, RewardedInterstitial, Interstitial wrappers
        ├── components/
        │   ├── leaderboard.js
        │   └── timer.js
        └── screens/
            ├── home.html      ← Streak Saver moved to badge+modal (was front-page banner)
            ├── lobby.html
            ├── game.html
            ├── results.html   ← 2X Coins solo flow, ad-flow frequency check (_runAdFlowCheck)
            ├── leaderboard.html
            ├── shop.html      ← watch-ad-for-ticket wired, 2-min cooldown added
            └── settings.html  ← Delete Account flow added (Danger Zone section)
```

---

## 🚀 Production Infrastructure

| Property | Value |
|----------|-------|
| Website | `https://forgetrivia.online` |
| Backend | `https://forge-backend-878124462453.us-central1.run.app` |
| Frontend CI/CD | Vercel (auto-deploy on push to `main`) |
| App Distribution | Google Play Store (Internal Testing + Production) |
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
  --min-instances 0 --max-instances 3 --memory 512Mi --timeout 3600
```

---

## ✅ Milestone Tracker

| # | Description | Status |
|---|-------------|--------|
| 1–16 | Initial architecture through session persistence | Done |
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
| 28 | Play Store pipeline | Done — LIVE |
| 29 | Security hardening | Done |
| 29.5 | App branding assets (icons/splash) | Done |
| 30 | AdSense compliance expansion | Done |
| 31 | Strategic pivot - frontend fork resolved | Done |
| 31.5 | Physical folder split (`frontend/web` + `frontend/app`) | Done |
| 32 | App: remove out-of-scope compliance assets | Done |
| 33 | App: feature gating (web restricted) | Done |
| 34 | App: Neo-Brutalism home screen | Done |
| 35 | Generation Tickets - Real Spendable Currency | Done |
| 36 | Quick Picks question bank (JSON, 50q/topic, duplicate-safe) | Paused (temporarily using AI) |
| 37 | Daily Login Reward (7-day cycle, Supabase-backed) | Done |
| 38 | Notification permission flow + 4-slot daily reminders | Done |
| 39 | Reconnect resilience (mid-game resync) + uniform ticket gating | Done |
| 40 | Generation ticket UI — home topbar pill, ticket detail sheet, lobby auto-suggest | Done |
| 41 | Shop screen — buy tickets with coins (25/ticket), disabled watch-ad placeholder | Done |
| 42 | How to Play onboarding screen | Done |
| 43 | Play Store production launch | Done — LIVE |
| 44 | Account deletion (backend endpoint + Supabase mirror delete + Settings UI) | Done |
| 45 | AdMob integration — RewardedAd (4 triggers: Entry Fee Recovery, Double Winnings, Streak Saver, Watch-Ad-for-Ticket) | Done |
| 46 | Ticket economy full rewrite — pure balance model, 2 free generations/day, Daily Reward cycle termination | Done |
| 47 | Critical bug fix: `lbUpsertPlayer` silently throwing, causing granted rewards to revert | Done |
| 48 | Critical bug fix: profile-refresh race condition clobbering fresh local writes | Done |
| 49 | Solo Mode 2X Coins / No Thanks post-game flow | Done |
| 50 | RewardedInterstitial + plain Interstitial ad types — Quick Pick & Custom Topic frequency-capped flow (Solo only) | Done |
| 51 | Shop ad-for-ticket: 2-minute cooldown between grants | Done |
| — | Forced Update Screen (economy-breaking version mismatch → prompt to update via Play Store, else guest-only fallback) | **Not started — next priority** |
| — | Classic/Team mode interstitial system | Not started |
| — | Daily Lucky Draw (slot machine + rewarded ad second spin) | Not started |
| — | Power-Up system + Power-Up Refill ad trigger | Not started |
| — | Online 1v1 Duel Mode (Async Challenge first, Sync 1v1 second) | Not started |
| — | Repo migration to native Linux filesystem (`~/forge`) | Not started |
| — | Domain badges / Knowledge specializations | Not started |
| — | Weekly topic bounties | Not started |

---

## Decisions Log & Known Issues

- **Ticket economy root-cause (July 2026):** The old `tickets_today` auto-reset-daily design required date-sensitive logic duplicated across six separate functions. This was the direct root cause of "coins update, tickets don't" symptoms — NOT a Supabase schema issue as initially suspected (the schema was always complete). Redesigned so tickets behave exactly like coins: a pure persistent balance, zero reset logic. The only remaining daily-reset logic is isolated to a single function (`use_generation()`) gating a separate `free_generations_used_today` counter.
- **`lbUpsertPlayer` bug (July 2026):** A previous edit accidentally pasted daily-reward-claim variable names (`today`, `day`, `baseCoins`) into the general-purpose `lbUpsertPlayer()` function, causing it to throw a `ReferenceError` on every single call — silently, since callers used fire-and-forget `.catch(() => {})`. This meant NO economy grant (ad rewards, ticket purchases, refunds) was ever actually reaching the Supabase mirror, even though the backend write always succeeded. Symptom: granted rewards would flash correctly in the UI, then revert a few seconds later once `refreshUserProfile()` read the never-updated Supabase value on next screen navigation. Fixed by rewriting the function to only use its actual parameters. **Lesson: never leave a mirror-sync write as pure fire-and-forget with a swallowed catch — at minimum log the error, ideally await it and surface a "sync failed" state to the user.**
- **`.single()` vs `.maybeSingle()` (recurring issue, fixed again July 2026):** Found and fixed a second instance of this exact mismatch in `lbFetchProfile()`. Standardize on `.maybeSingle()` everywhere in `supabase-client.js` — `.single()` throws on missing rows in ways that are easy to mishandle.
- **Auth token expiry (July 2026):** Google ID tokens expire (~1hr) but the session persists indefinitely in `localStorage` with no refresh logic. Any Bearer-gated backend call (`/tickets/*`, `/economy/sync`, `/account/delete`) made long after last sign-in fails silently while Supabase-direct writes (coins/trophies via anon key) keep working — this is why "coins work, tickets don't" can ALSO be an auth symptom, not just a ticket-logic symptom. Mitigated with `_isAuthError()`/`_promptReauth()` helpers that detect this specific failure and prompt re-sign-in rather than showing a generic error. A real token-refresh system is still not built — this is a patch, not a fix.
- **AdMob device testing:** Registering your own device as an AdMob test device makes real ad unit IDs auto-serve test ads on that device — this is the correct way to test production ad units without invalid-traffic risk, rather than toggling `IS_TESTING` per-format.
- **Rewarded Interstitial plugin support confirmed (July 2026):** `@capacitor-community/admob` DOES support this format via its `reward-interstitial/` module — verified by inspecting `node_modules/@capacitor-community/admob/dist/esm/reward-interstitial/*.d.ts` directly rather than assuming. Exact method names: `prepareRewardInterstitialAd()` / `showRewardInterstitialAd()`. Exact events: `onRewardedInterstitialAdLoaded/FailedToLoad/Showed/FailedToShow/Dismissed/Reward`. **Lesson: always verify third-party plugin capability against the actual installed `node_modules` type definitions before designing a feature around it — don't assume from documentation alone, and don't run `grep` from the wrong working directory (cost real debugging time this session).**
- **Gradle/AGP `getDefaultProguardFile` build failure (July 2026):** AGP 9 removed support for `proguard-android.txt`, which `@capacitor-community/admob`'s bundled `build.gradle` (inside `node_modules`) still references. Fixed via `android.r8.proguardAndroidTxt.disallowed=false` in `gradle.properties` — a project-level flag, NOT a hand-edit inside `node_modules` (which gets wiped on every install/sync). Described by Google as a temporary compatibility flag that may be removed in a future AGP version — watch for the plugin publishing a proper fix and upgrade when available.
- **AndroidManifest AD_ID permission errors are often stale-build artifacts, not source errors:** If Play Console flags a missing `com.google.android.gms.permission.AD_ID` permission despite it being present in the manifest source, check the **Merged Manifest** tab in Android Studio before assuming the XML is wrong — a stale build/cache is a common cause. Clean + Rebuild, generate a fresh `.aab`, don't reuse an old build artifact.
- **Play Store production access questionnaire** is separate from the Data Safety/Content Rating forms — it's the 3-part "About your closed test / About your app / Production readiness" form unlocked after 14 continuous days with 12+ opted-in testers. Specific, evidence-backed answers (real bugs found/fixed, real changes shipped) are much stronger than vague ones.
- **Account deletion is a hard Play Store requirement**, not optional, for any app with account creation — needs BOTH a public web page describing the process AND an in-app option to initiate deletion. A "contact developer" page alone does not satisfy the in-app requirement.
- **Ads jump the queue:** AdMob is now live and integrated — this rule has been fulfilled.
- **Workflow Split Decision (June 18, 2026):** The website codebase is frozen. App builds are the active frontier.
- **Frontend Fork Decision (June 19, 2026):** Frontend physically splits into `frontend/web/` and `frontend/app/`; backend remains single and shared across both targets.
- **Cloud Run state:** Runtime file storage is ephemeral. `profiles.json` is the backend runtime source of truth during a live process, and Supabase mirrors long-term display data after client sync.
- **Rewarded ad timing rule:** Never show a rewarded ad prompt during an active game. Only in lobby, post-game results, home screen, or shop.
- **Fire OS / Google Sign-In:** Fire OS has no Google Play Services; guest play is shown instead.
- **BGM unlock:** `AudioContext.resume()` must be called synchronously within a direct user gesture handler.
- **WSL `/mnt/c` friction:** Repo at `/mnt/c/QuizApp/forge` has caused silent `mv` failures and broken npm symlinks. Long-term: relocate to `~/forge`.
- **New APK checklist:** Any `frontend/app/` or `android/` change -> `npx cap sync` -> versionCode bump -> Generate Signed Bundle -> Play Console upload. Backend-only changes never need a new APK.
- **Keystore:** `keystore.properties` lives at `forge/android/keystore.properties`.
- **Frontend local dev server:** Must run from `forge/frontend/app/`, not `forge/`. Screens load through `index.html`.
- **Visual Identity Pivot (June 20, 2026):** Neo-Brutalism supersedes the older Clash Royale-inspired direction.
- **No Rotating Functional Inputs:** Name-entry and room-code fields must always render level.
- **Quick Picks (temporary policy, July 2026):** Quick Picks topics are still **free** (no generation ticket cost), but they are temporarily generated by **Gemini** instead of using the bundled static JSON bank. This avoids players seeing the same fixed set of questions while the per-topic question bank is being built. Once the question bank is ready, switch Quick Picks back to bank-backed questions.
- **Ticket price** set to 25 coins/ticket for launch.
- **Critical production bug fixes (July 2026), all confirmed working post-fix:**
  1. Splash screen could hang forever on first app open — notification-permission sheet was z-indexed below the splash and boot awaited it before dismissing. Fixed: splash dismissal is now unconditional, permission prompt fires after home renders.
  2. Coins/trophies/rank flickered or reverted — multiple independent call sites each fired their own Supabase profile fetch and overwrote State.user on resolution with no ordering guarantee. Fixed: consolidated into one shared, de-duplicated `refreshUserProfile()`.
  3. Daily Reward screen could show "unclaimed" right after a successful claim — the check path used `.single()` (throws on non-exactly-one-row, swallows all errors into null) while the claim path used `.maybeSingle()`. Same row, two query shapes, two different answers. Standardized on `.maybeSingle()` everywhere in supabase-client.js.
  4. Daily Reward's ticket grant (separate backend call from the coin grant) could fail silently on a Cloud Run cold start, leaving coins granted but tickets not. Fixed: one retry + visible error toast on final failure.
- **Supabase leaderboard columns** `tickets_today`/`ad_tickets_used_today`/`last_ticket_date` must exist for profile fetches to succeed at all — missing columns silently broke unrelated fields (coins, trophies, last_reward_date) too, since the profile fetch is a single combined query. Confirmed present.
- **Auth token expiry mitigation (July 2026, follow-up):** The original `_isAuthError()`/`_promptReauth()` helpers existed but several `API.*` methods in `index.html` (`syncProfile`, `syncTickets`, `grantDailyRewardTickets`, `grantBonusGeneration`) were throwing hardcoded generic error strings (e.g. `"Economy sync failed"`) instead of the real backend error text — this silently broke `_isAuthError()`'s string-matching detection for those specific calls, so users hit confusing "sync failed, try again" messages that retrying could never fix (retrying with the same stale token just fails again). Fixed by making all `API.*` error paths surface `await r.text()` (the real backend detail) instead of a fixed string.
- **Wasted-ad-watch bug (July 2026):** Rewarded-ad-then-grant flows (Shop ticket purchase/watch, Entry Fee Recovery, Double Winnings, Solo 2X Coins, Custom Topic Rewarded Interstitial) only discovered an expired token AFTER the user finished watching a full ad, since the token is only actually validated when the grant call fires post-ad. Added `_isSessionLikelyStale()` — a client-side heuristic (Google ID tokens last ~1hr, so anything signed in >50 minutes ago is treated as stale) — checked BEFORE every ad is shown, not just after. This is a heuristic, not real validation (no client-side way to check JWT expiry without the backend), but it eliminates the "watch a full ad, then get told it didn't count" experience in the common case.
- **⚠️ NOT A PERMANENT FIX — real fix still needed post-launch stabilization:** The underlying problem is architectural — Forge uses Google's simple `id_token` sign-in flow, which has no refresh token and can't be silently renewed. A genuine fix requires migrating to OAuth authorization-code flow (new consent scopes, server-side refresh token storage, a `/auth/refresh` endpoint) so sessions renew silently instead of requiring the user to re-tap sign-in roughly every hour of continuous play. This is a real scope of work, not a quick patch — schedule it as a dedicated milestone once other launch-critical items are stable, not squeezed in alongside unrelated features.
---

## Implementation Guidelines

1. **This is a live product with real users — treat every economy/auth/backend change as a compatibility risk, not just a feature to ship.**
2. **Code standards:** Self-documenting code with Python typing and descriptive docstrings.
3. **Workflow:** Keep changes scoped; avoid touching frozen website assets except `app-ads.txt`.
4. **Economy integrity:** File-backed backend state is runtime truth; Supabase mirrors display/cross-session data through explicit sync paths. Never leave mirror-sync writes as unawaited fire-and-forget with swallowed errors.
5. **$0 infrastructure:** No paid cloud integrations. Free tiers only (AdMob revenue is the exception — that's the point).
6. **ARM64 builds:** Always use `docker buildx --platform linux/amd64 --push` for Cloud Run images.
7. **Visual split:** Website uses the frozen blue/yellow pixel-arcade palette. App uses active Neo-Brutalism direction.
8. **Ads are contextual, never intrusive:** Rewarded/Rewarded-Interstitial preferred over plain Interstitial. Frequency-cap everything. Disclose rewards before Rewarded Interstitial auto-shows. No banners anywhere.
9. **Verify third-party plugin capabilities against actual `node_modules` type definitions before building around them — don't assume from docs or memory.**
10. **Test on a real device via USB debug before any production/Internal Testing release, especially for anything touching AdMob, WebSockets, or auth.**
11. **Database protection:** Keep RLS active on Supabase tables.
12. **Context maintenance:** Update `CLAUDE.md` after major milestones — this file should always reflect current reality, not the original spec.
13. **Device operations:** Execute native terminal commands using Windows PowerShell exclusively; WSL for Node/npm/Python only.
```