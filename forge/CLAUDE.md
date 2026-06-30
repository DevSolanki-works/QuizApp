Here's the content converted to a clean, readable Markdown format:

---

# CLAUDE.md — Forge: AI Trivia Showdown

> **Context Routine:** Paste this file at the start of every new conversation so Claude has full context.
> **Maintenance Protocol:** Claude updates this file after every major milestone and provides the new version.

---

## 🧠 Who I Am

- **Status:** 2nd-year CS AI/ML student (Strong Python background, currently learning full-stack).
- **Timeline:** Building this over a 1-month vacation.
- **Ultimate Goal:** Deploy to Google Play Store + monetize ($0 infrastructure constraint).
- **Hardware Architecture:** ARM64 machine.
- **Development Environment:** WSL (Ubuntu) on Windows; Python virtual environment located at `backend/.venv`.

---

## 🎮 Project Overview: Forge — AI Trivia Showdown

A real-time multiplayer mobile quiz game. Players enter **ANY** topic → AI generates a custom quiz → players compete live via WebSockets using a 4-digit room code.

---

## 🪓 STRATEGIC PIVOT (Milestone 31): Website vs App Workflow Split

> ⚠️ **CRITICAL ARCHITECTURAL NOTICE**
> Starting Milestone 31, the Website and App are split into two separate development tracks. They currently share the same `frontend/` codebase, but going forward, most active work occurs on the **App track**. Review this before starting any new session.

### The "Why"

- **The Website (`forgetrivia.online`):** Exists primarily for AdSense revenue + SEO discoverability. It is "done enough" for now and is completely frozen at its current feature set.
- **The App (Android via Capacitor):** Now the primary development priority. The goal is to drive Play Store downloads by turning the app into the full/premium experience, treating the website as a lighter teaser/funnel.

### ❄️ What Stays Frozen (Website Track)

- **Zero Feature Development:** No further feature work will be done on `forgetrivia.online` for the time being.
- **AdSense Compliance Stability:** Keep all AdSense-required pages exactly as they are: `landing.html`, `about.html`, `privacy.html`, `terms.html`, `contact.html`, `how-to-play.html`, `topic-guide.html`, `trivia-tips.html`, `multiplayer-quiz-guide.html`, `ai-trivia-questions.html`, `dev-log.html`, `sitemap.xml`, `robots.txt`, `ads.txt` / `app-ads.txt`.
- **Routing Security:** Do not touch `landing.html` boot routing, cookie consent settings, or AdSense script tags.
- **Timeline:** The Milestone 30 AdSense resubmission timeline (wait for GSC indexing, then 2–3 weeks) still applies independently of this pivot.

### 🔥 What Becomes Active (App Track)

- **Targeted UI Overhaul:** A major visual redesign targeted **ONLY** at the Capacitor/Android build (Milestone 31+).
- **New Visual Identity:** Transitioning to a **Neo-Brutalism** UI — dark charcoal backgrounds, thick black borders, hard offset shadows, and flat color blocking, per the dedicated section below.
- **Feature Pruning:** Heavy feature removals and strict feature-gating (detailed below).

### 📐 Architecture Decision — RESOLVED (June 19, 2026)

Resolved: **Forked frontend.** `frontend/` splits into `frontend/web/` (current site, frozen, untouched) and `frontend/app/` (new Capacitor target, active development). `capacitor.config.json`'s `webDir` points to `frontend/app`. Vercel's build root for the live site points to `frontend/web`.

This guarantees the website can't be affected by app UI work — separate files, not a shared tree gated by `data-forge-target`. The `platform.js` `data-app-only`/`data-web-only` machinery is retired going forward; a slim app-only variant may remain in `frontend/app/` solely for local-dev backend URL switching.

The **backend stays single and shared** — see "Backend Stays Unified" below. Only the frontend forks.

### ⚙️ Backend Stays Unified — No Backend Fork

The FastAPI backend is never forked or branched by client target. Web and app hit the exact same endpoints and WebSocket protocol. Team Mode and the leaderboard already exist server-side; access to them is gated **exclusively by withholding UI entry points on the website build**, never by backend logic. Do not add target/platform checks to backend code. If a future feature ever needs true server-side gating, treat that as a deliberate, separately-flagged decision — not the default pattern.

---

## 📱 App UI Direction — Neo-Brutalism Overhaul (Milestone 31+)

> **Reference Pivot (June 20, 2026):** The Clash Royale-inspired direction from the original Milestone 31 plan is superseded by **Neo-Brutalism**, modeled directly on a reference mockup (a "BRAIN BOOST QUIZ"-style home screen): dark charcoal backdrop, thick black borders, hard offset shadows with zero blur or glow, flat saturated color blocks, and bold poster-style typography. This is blueprint-level reference only — Forge keeps its own branding, content, and topic-driven gameplay; the mockup is a styling target, not literal content to copy.
>
> **Home Screen Composition — LOCKED (June 22, 2026):** Three structural directions were mocked up and compared. The locked direction, full code in `forge-neo-brutalism-home-final.html`, supersedes both the original button-stack layout and a zine/collage alternative that was explored and explicitly rejected (see "Decisions Log" below). Treat the structure in the "Locked Home Screen Composition" subsection as the actual target to implement against, not just a style mood board.

### Why the Switch

Clash Royale's glossy 3D-bevel look fights with Forge's existing flat pixel-arcade identity (Press Start 2P, hard-edged buttons that already use offset shadows). Neo-Brutalism keeps the things that already work in the codebase — solid color buttons, offset drop-shadows, press-to-flatten interactions — and pushes them further into a deliberate, graphic, high-contrast style instead of softening them into glassmorphism or gradients. It's also cheaper to build: flat colors and hard shadows don't require new gradient, blur, or 3D-bevel asset work.

### Core Visual Principles

- **Thick black borders everywhere.** Every interactive surface — buttons, inputs, cards, badges — gets a solid 2.5–3px black (or near-black) border. No 1px hairlines anywhere in the app track.
- **Hard offset shadows, zero blur.** Shadows are solid color blocks offset diagonally (e.g. `6px 6px 0 #000`), never blurred or glowing. On press, the element translates fully into its shadow (shadow collapses to `0 0 0`) rather than just shrinking partway — a harder, more "stamped" press feel than the original `.btn-primary` bottom-only drop.
- **Flat color blocking, no gradients or glassmorphism.** Backgrounds switch from radial blue gradients + `backdrop-filter: blur()` cards to solid charcoal backgrounds with solid-color (not translucent) panels. No frosted-glass anywhere in the app track.
- **Blocky corners, not pills.** Buttons and cards move from `var(--radius-pill)` (fully rounded) to a small fixed radius (~6–8px) — rectangular with just-rounded corners. Pill shapes are reserved for two specific cases only: the currency readout and the name-entry field (see below) — not buttons or cards.
- **Scattered icon badges.** Small square badges (star, question mark, etc.) with thick borders and hard shadows, slightly rotated, used as decorative accents around hero content.
- **Hierarchy through size and shape, not divider text.** No "SOLO MODE" / "MULTIPLAYER"-style caption dividers anywhere in the action area. A single dominant primary action, a secondary tile row, and a smaller/circular-or-reduced-scale utility row communicate priority on their own — this replaced the original web-track pattern of stacking same-sized buttons with text dividers between them.
- **Bold poster typography for hero text — RESOLVED.** The home screen's "FORGE" wordmark uses **Archivo Black**, rendered as a duotone stamp effect: green fill, black outline (`-webkit-text-stroke`), with a solid red copy of the same text offset 5px down-right behind it (no blur, hard edge only). This is reserved for the single hero wordmark. **Press Start 2P stays the typeface for every other piece of UI text** — buttons, labels, taglines, badges, footer meta — so the pixel-arcade identity isn't lost, it's just no longer used at poster scale.
- **Trophy iconography is a deliberate identity anchor, not just a decorative choice.** Trophy imagery already appears throughout the app (results screen, leaderboard, in-game economy) and must stay visually present on the home screen specifically — not folded away into a generic icon. The locked composition gives it its own badge in the hero, separate from (and in addition to) its functional appearance in the currency readout.

### Locked Home Screen Composition (June 22, 2026)

Full implementation reference: `forge-neo-brutalism-home-final.html`. Top to bottom:

1. **Top bar:** one combined currency pill (coins + trophies in a single pill, separated by a thin internal divider) — not two separate boxes.
2. **Hero zone:** 1–2 small rotated corner badges (star, question mark) → the "FORGE" wordmark (duotone stamp treatment, see above) → a small Press Start 2P tagline line → a dedicated **trophy badge** (cream block, thick border, hard shadow, gentle two-step "thump" bounce — `steps(2)` timing, not a smooth ease, to keep the motion blocky rather than arcade-soft) → a short plain-language subtext line.
3. **Name entry:** a single slim pill-shaped field, not a boxed labeled input block. Lower visual weight than the actions below it.
4. **Primary CTA:** one full-width "SOLO PLAY" button — the single biggest, boldest element in the action area.
5. **Secondary tile row:** "CREATE ROOM" / "JOIN ROOM" as two square-ish tiles side by side (green / red), icon stacked above label inside each — not a vertical list.
6. **Inline join-by-code capsule:** a compact code input + arrow button sitting directly under the tile row, sized only as large as it needs to be. No separate full bordered input block with its own label for this.
7. **Utility row:** small, visually de-emphasized icon tiles (Google sign-in, sound toggle) — same border/shadow language as everything above, just smaller scale. Priority is communicated by size alone, no text needed to mark these as secondary.
8. **Footer:** one short meta line (live room count + version), Press Start 2P, dim.

**Firm rule, not a style preference:** functional inputs (name field, room code field) always stay perfectly level. Any future decorative rotation, collage treatment, or tilt effect applies only to non-interactive/decorative elements and to buttons — never to a field the player has to read or type into.

### Proposed Design Tokens (App Track Only — `frontend/app/`)

```css
:root {
  /* Neo-Brutalism palette — replaces the blue/yellow pixel-arcade tokens for the app track only */
  --nb-bg:         #181818;   /* charcoal background, replaces --bg radial blue */
  --nb-surface:    #1F1F1F;   /* flat panel/card fill, replaces translucent glass cards */
  --nb-input:      #242424;   /* input field fill — one shade lighter than surface */
  --nb-black:      #0D0D0D;   /* border + shadow color */
  --nb-cream:      #EDE0C8;   /* primary button fill, headline highlight, trophy badge fill */
  --nb-text:       #ECE7DA;   /* default light text on dark backgrounds */
  --nb-text-dim:   rgba(236,231,218,0.5); /* secondary/dim text */
  --nb-green:      #3F6E52;
  --nb-green-dark: #2C4F3B;
  --nb-red:        #C0392B;
  --nb-red-dark:   #8E2A20;

  --nb-border-w:   3px;        /* 2.5px on smaller elements (badges, pills, inputs) */
  --nb-radius:     8px;
  --nb-shadow-sm:  4px 4px 0 var(--nb-black);
  --nb-shadow-lg:  6px 6px 0 var(--nb-black);
}
```

These are a starting point, not final — confirm exact hex values against the reference mockup once implementation starts, and leave the website's existing blue/yellow tokens completely untouched (frozen track, never shared).

### What Carries Over From the Clash Royale Plan

- **Persistent currency bar:** Still wanted — now a single combined pill rather than two separate boxes (see Locked Composition above), restyled flat brutalist instead of glossy 3D-bevel.
- **Card-based panels for menus:** Still wanted — but flat-filled cards with thick borders instead of glass/chest-style cards.
- **Reward-reveal sequence at `GAME_OVER`:** Still under consideration — adapt to a "stamp" or "punch-in" reveal animation (hard snap + shadow pop) instead of a glossy chest-crack animation.
- **Audio constraint:** Unchanged — Web Audio API synthesized sounds only, $0-cost.

### What's Dropped From the Clash Royale Plan

- Glossy 3D-bevel button gradients and soft drop shadows.
- Arena-style saturated gradient backgrounds — replaced by flat charcoal + color-block panels.
- Any glassmorphism/blur treatment on cards or panels in the app track.
- The original web-track pattern of vertically stacking same-sized buttons separated by text dividers ("SOLO MODE" / "MULTIPLAYER" captions) — superseded by the size/shape hierarchy described in Locked Composition above.

---

## 🚫 App-Only Removals (Planned, Not Yet Implemented)

- **Removed from app build (Done):** `about.html`, `how-to-play.html`, `topic-guide.html`, `trivia-tips.html`, `multiplayer-quiz-guide.html`, `ai-trivia-questions.html`, `dev-log.html`, `contact.html`, `screens/landing.html`, `ads.txt`, `app-ads.txt`, `robots.txt`, `sitemap.xml`. `index.html` boot logic rewritten to default straight to `home` (no landing/crawler routing needed in-app).
- **Chai4Me button:** Removed from `home.html` top-left actions.
- **Leaderboard:** External `leaderboard.html` page kept (not deleted) but flagged for conversion — Supabase fetch logic (`loadScores`, tab-switching) will be reused, but the standalone-page wrapper, donor/Chai4Me tab, and styling will be rebuilt as an in-app menu screen once the new nav is designed. Corner pill button removed from `home.html` in the meantime.
- **Footer nav (`#app-footer`):** Removed from `index.html` — it only linked to now-deleted pages.

---

## 🔒 Web vs App Feature Gating (Planned, Not Yet Implemented)

To incentivize app installation, the **app** will be treated as the full-featured tier, while the **website** acts as a restricted teaser layout.

- **Leaderboard Access:** Currently public and free on the website via `leaderboard.html`. Plan: Restrict or entirely pull this entry point from the web layout, making global leaderboard inspection an app-exclusive experience.
- **Advanced Game Modes:** Team Mode (and all future game modes) will become app-exclusive features. The web track remains frozen on Classic and Solo modes.
- **Teaser UX UI:** The web front-end should actively tease locked content (e.g., *"Team Mode & Global Leaderboards are available in the app"* alongside an explicit Play Store badge link) instead of hiding components silently.
- **Gating Implementation:** Extend the functional `data-app-only` / `appOnlyFeaturesEnabled` pattern within `platform.js`.
- **Backend Verification:** A future architecture check is required to ensure the WebSocket `set_lobby_mode` action drops or rejects `mode: "team"` server-side if the incoming connection is verified as originating from a web-client agent.
- **Rationale:** Gating Team Mode and the global leaderboard to the app is the primary install-driver for Play Store downloads, which monetizes better long-term than additional AdSense traffic on the frozen website.

---

## 💻 Local Development

### ⚠️ CRITICAL: Frontend Directory Rule

Always serve the local HTTP server explicitly from the `forge/frontend/` working subdirectory. Serving from the root directory will break routing logic (`404` errors on screens).

```bash
# ✅ CORRECT PATHWAY
cd forge/frontend && python3 -m http.server 8080

# ❌ INCORRECT PATHWAY (Breaks absolute asset routing)
cd forge && python3 -m http.server 8080
```

### Start Backend Locally

```bash
cd forge/backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

### Local Environment URLs

- **Frontend Application:** `http://127.0.0.1:8080`
- **Backend Core API:** `http://127.0.0.1:8000`
- **Interactive API Documentation:** `http://127.0.0.1:8000/docs`

### 🔧 Known Local Development Quirks

- **Supabase Defer Race Condition (FIXED - M29):** Because `supabase-client.js` loads asynchronously via `defer`, returning authenticated users previously triggered an `"lbFetchProfile is not a function"` crash during the application's boot block initialization. This has been resolved via a `waitForSupabase()` polling helper function.

---

## 💰 Monetization Strategy

1. **Google AdSense (Primary Web Driver):** Web track deployment only. Pending manual configuration review approval (Blocked: PAN card pending verification).
2. **Chai4Me Micro-Donations:** Web track deployment only. Profile endpoint: `https://www.chai4.me/devsolankiworks`
3. **In-Game Soft Currency:** Engagement loop powered by virtual Coins and Trophies accumulated dynamically across gameplay sessions (Web + App shared data).
4. **App Acquisition Funnel:** Driving app store traction by gating premier content (Team mode, global ranking metrics) behind the native wrapper build.

### ⛔ DEPRECATED — Forbidden Ad Technologies

> **Hard Prohibition:** Never integrate low-tier, high-intrusion monetization tools. This includes: Monetag, vignette/interstitial ads, popunders, force-push notification monetization assets, or any instant-approval programmatic platforms.

### AdSense Compliance Checklist (Website Only)

- [x] AdSense core script tags integrated into every single crawlable HTML node.
- [x] Clear global navigation elements to explicit Privacy Policy and About screens available on every viewport.
- [x] Functional localized cookie consent banner with embedded `localStorage` tracking and NPA capability.
- [x] High semantic text quality across `landing.html` to robustly counter "Low Value Content" rejections.
- [x] Updated structural mapping index assets (`robots.txt` and `sitemap.xml`) served dynamically from root.
- [x] Strict routing enforcement ensuring cold crawlers drop directly onto semantic rich content (`landing.html`).
- [ ] Manual application review sign-off → **PENDING** (Awaiting identification/PAN clearance).

### ⚠️ AdSense Landing Page Enforcements

`landing.html` **MUST** remain the explicit entry screen served during a baseline cold initialization address (`/#` or `/`) on the **website infrastructure**. The initialization script guarantees this deployment sequence via Case 3 processing routing configurations. Never change this routing order for the web tier; crawlers must interact with semantic copy.

---

## 🔒 Security Hardening (Milestone 29)

### Core Architectural Changes

| Source File Target | Nature of Modifications / Security Patch |
| --- | --- |
| `app/core/sanitize.py` | **NEW:** Explicit structural input schema validation module parsing all incoming WebSocket frames. |
| `app/core/limiter.py` | XFF header configurations updated to target and trust the final IP array string index (Cloud Run signature verification) to neutralize upstream client spoofing risks. |
| `app/routers/http.py` | Secured `/economy/sync` and `/economy/reward` routers; endpoints now strictly demand a valid `Authorization: Bearer <id_token>` structure. |
| `app/routers/websocket.py` | Passed all functional ingestion vectors through validation logic; setup fixed action allowlist filters; rate-limited connection setups. |
| `index.html` (Boot block) | Integrated `waitForSupabase()` async polling logic to resolve racing execution paths; wrapped logic inside global `try/catch` safety parameters. |
| `index.html` (`goTo()`) | Implemented strict `SCREEN_GUARDS` checks to mitigate direct access attempts to unauthorized routes (e.g., trying to access `/#results` or `/#game` directly via URI strings). |
| `index.html` (API Object) | Configured frontend profiling calls to automatically sign data packets out with the required `Authorization: Bearer` token payload string. |
| `index.html` (`handleGoogleLogin()`) | Updated user object mappings to retain `user._credential` within the local lifecycle layer to handle authenticated communication requirements smoothly. |

### Security Model Architecture

- **WebSocket Ingestion:** Every client message is parsed against an absolute action filter configuration key allowlist (`sanitize.VALID_ACTIONS`).
- **Prompt Injection Defense:** Topics undergo pattern evaluation via regex-based blocklists prior to triggering downstream LLM generations via Gemini.
- **Financial Protection Layer:** Economy modification calls require an unexpired, authentic Google JWT mapping cleanly to the payload's `user_id`.
- **Rate Limiting Engine:** Enforces connection and action quotas on a per-IP basis, using securely extracted cloud load-balancer signatures.
- **Navigation Route Interceptors:** Strict frontend validation guards access to operational routes: `lobby` demands verified parameters (`roomCode`, `playerName`), `game` requires an active WebSocket channel, and `results` checks for population metrics.
- **Timestamp Calibration:** Latency tracking values (`time_ms`) undergo backend boundary checking, clamping values to `[0, time_limit_ms + 500ms]` to eliminate manual speed hacks.

---

## 🗄️ Supabase Persistence Engine (Milestone 27)

### Project Instance Configuration

- **Endpoint URL:** `https://ffstsbwkianjcjpqvmtv.supabase.co`
- **Access Control:** Public Anon Key (Refer to explicit token strings within `supabase-client.js`)
- **Regional Hosting:** Southeast Asia (Singapore Data Center Hub)

### Database Schemas

```
┌───────────────────┐             ┌───────────────────┐
│    leaderboard    │             │     donations     │
├───────────────────┤             ├───────────────────┤
│ google_id (PK)    │             │ id (PK)           │
│ name              │             │ upi_txn_id        │
│ coins             │             │ status            │
│ trophies          │             │ amount            │
└───────────────────┘             └───────────────────┘
         │
         ▼ (SQL VIEW)
┌───────────────────┐
│ donor_leaderboard │
└───────────────────┘
```

| Database Node Object | Structural Intent & Operational Behavior |
| --- | --- |
| `leaderboard` | Flat user storage node matrix. Uses `google_id` as the Primary Key. Upserts occur during game-ending sequences. |
| `donations` | Ledger tracking micro-transactions / incoming UPI claims. Transitions states: `pending` → `approved` → `rejected`. |
| `donor_leaderboard` | **SQL VIEW.** Read-only node compilation. Aggregates and displays mathematical calculations summing approved transaction tallies. |


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

### Operational Logic

- **Asynchronous Updates:** Ranking data updates run concurrently inside `applyUserEconomy()` via fire-and-forget patterns.
- **Conflict Resolution:** `lbUpsertPlayer()` runs explicit conflict checks on `google_id` configurations to guarantee playing records append to existing rows instead of resetting current scores.
- **Manual Verification:** Financial data auditing flows are fully manual: verification happens via the Supabase admin interface by transitioning values to `approved` only after reviewing physical banking notifications.

---

## 🏗️ Technical Stack Constraints (LOCKED)

| Technology Layer | Selection | Rationale & Boundaries |
| --- | --- | --- |
| **Frontend Framework** | HTML5 / CSS3 / Vanilla JavaScript | Retains clean portability requirements for seamless compilation into native systems using CapacitorJS. |
| **Database Solution** | Supabase (Postgres Engine) | Free tier pricing model satisfies $0 operational resource guidelines perfectly. |
| **Mobile Deployment** | CapacitorJS → Android Application Bundle | Free, robust, automated wrapper pipelines matching local workflow parameters without compounding expenses. |
| **Backend Architecture** | Python 3 / FastAPI Engine | Excellent fit for rapid asynchronous handling; maximizes development velocity. |
| **Artificial Intelligence** | Gemini 2.5 Flash Lite | Leverages high-performance inference at a $0 API price point. |
| **Real-time Pipeline** | Native FastAPI WebSocket Implementations | Low-latency state sync features built directly into core framework layers. |
| **State Persistence** | Transient In-Memory Python Dictionary Objects | Minimizes architecture footprint; avoids complex local hosting overhead. |
| **Deployment Platform** | Containerized Docker → Google Cloud Run | Scalable serverless tier accommodating the $0 infrastructure cap. |

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
│       ├── core/              ← (config.py, state.py, limiter.py, sanitize.py)
│       ├── models/            ← (quiz.py)
│       ├── routers/           ← (http.py, websocket.py, auth.py)
│       └── services/          ← (ai.py, profiles.py)
└── frontend/
    ├── web/                          ← Frozen — exact pre-split site, never touched by app work
    │   ├── index.html, app.js, platform.js, supabase-client.js
    │   ├── ads.txt, app-ads.txt, robots.txt, sitemap.xml
    │   ├── about.html, contact.html, dev-log.html, how-to-play.html,
    │   │   topic-guide.html, trivia-tips.html, multiplayer-quiz-guide.html,
    │   │   ai-trivia-questions.html, leaderboard.html, privacy.html, terms.html
    │   ├── components/ (leaderboard.js, timer.js)
    │   └── screens/ (landing.html, home.html, lobby.html, game.html, results.html)
    └── app/                          ← Active — Capacitor target, Neo-Brutalism home composition locked
        ├── index.html, app.js, platform.js, supabase-client.js
        ├── privacy.html, terms.html   ← kept per Play Store requirement, to become external links
        ├── leaderboard.html           ← PENDING CONVERSION: Supabase fetch logic reusable,
        │                                wrapper/styling/donor-tab to be rebuilt as in-app menu screen
        ├── components/ (leaderboard.js, timer.js)
        └── screens/ (home.html, lobby.html, game.html, results.html)
            ↳ landing.html removed; index.html boots straight to home
            ↳ home.html pending rebuild against the locked composition in
              "Locked Home Screen Composition" above
```

---

## 🚀 Live Production & Infrastructure Deployment

| Deployment Property | Active Target Value |
| --- | --- |
| **Public Website Target** | `https://forgetrivia.online` |
| **Global Leaderboard Endpoint** | `https://forgetrivia.online/leaderboard.html` |
| **Backend Core Serverless Base** | `https://forge-backend-878124462453.us-central1.run.app` |
| **Frontend Automated Build Engine** | Vercel Pipelines (Automated deployment matching pushes to `main`) |

### Backend Service Re-Deployment Compilation Script

```bash
cd forge/backend

# Build image architecture targets for Google Cloud Infrastructure platforms
docker buildx build \
  --platform linux/amd64 \
  --tag us-central1-docker.pkg.dev/quiz-app-forge/forge/backend:latest \
  --push .

# Trigger revision rollout across managed instance environments
gcloud run deploy forge-backend \
  --image us-central1-docker.pkg.dev/quiz-app-forge/forge/backend:latest \
  --platform managed --region us-central1 --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_key,GEMINI_MODEL=gemini-2.5-flash-lite,GOOGLE_CLIENT_ID=878124462453-g7skbojds4uqg442hb9d31ftrlll095r.apps.googleusercontent.com \
  --min-instances 0 --max-instances 3 --memory 512Mi --timeout 600
```

---

## 🔄 Core Game Loop Execution Lifecycle

```
[Client] ─── (POST /rooms/create) ───> [Backend HTTP Router]
                │
[Client] <─── (Establishes Connection) ─── [WS /ws/{code}/{name}]
                │
                ├── [Host Action Frame] ───> { action: start_game, topic, mode }
                └── [Player Input Frame] ───> { action: answer, choice, time_ms }
                │
                (Game Completion)
                │
                ▼
         applyUserEconomy()
                │
                ▼
         lbUpsertPlayer() [Supabase]
```

---

## 📐 Scoring Formula Calculation

```python
# Base Calculation
base = max(500, min(1000, int(1000 * (1 - (time_ms / time_limit_ms) * 0.5))))

# Streak Multiplier Tiers
multi = min(1.0 + (streak // 3) * 0.5, 3.0)

# Final Point Assignment Output
final = int(base * multi)

# Architectural Tier Reference Matrix:
# streak 0-2  -> × 1.0
# streak 3-5  -> × 1.5
# streak 6-8  -> × 2.0
# streak 9-11 -> × 2.5
# streak 12+  -> × 3.0
```

---

## 💰 Economy State Management Rules

| Context / Gameplay Condition | Virtual Coin Adjustments | Trophy Allocation Adjustments |
| --- | --- | --- |
| **New Profile Initialization** | +200 | +50 |
| **Multiplayer Room Entrance Fee** | -25 | — |
| **Multiplayer Match Champion** | +Collected Pool | — |
| **Solo Performance (≥ 5 Correct)** | +10 | — |
| **Solo Performance (4–5 Correct)** | — | +1 |
| **Solo Performance (6–10 Correct)** | — | +2 per correct answer over baseline 5 |
| **Solo Performance (< 4 Correct)** | — | -2 (Floor constraint enforced at 0) |

> **Client State Synchronization:** The operational local database state key `forge_economy_{user_id}` serves as the definitive source of truth across user clients.

---

## 🌐 Rest HTTP Application Interfaces

| Verbs | Endpoint Request Targets | Auth Requirements | Purpose & Operational Execution Parameters |
| --- | --- | --- | --- |
| `GET` | `/health` | None | Core service liveness probe monitoring. |
| `POST` | `/rooms/create` | None | Instantiates volatile game loop room states. |
| `GET` | `/rooms/{code}` | None | Inspects active player connections inside an existing room. |
| `DELETE` | `/rooms/{code}` | None | Drops a dead or deserted game room layout. |
| `POST` | `/auth/google` | None | Processes and verifies inbound Google identity tokens. |
| `POST` | `/economy/reward` | Bearer JWT Required | Records transaction increments following match verification. |
| `POST` | `/economy/sync` | Bearer JWT Required | Refreshes and returns authoritative account data profiles from database. |

---

## 🔌 WebSocket Communication Message Protocol

### Server → Client Communication Payloads

```json
// Event: PLAYER_JOINED
{ 
  "type": "PLAYER_JOINED", 
  "data": { "players": ["Dev", "Alex"], "lobby_mode": "classic", "locked": false } 
}

// Event: GAME_STARTING
{ 
  "type": "GAME_STARTING", 
  "data": { "topic": "Quantum Computing", "mode": "hard", "play_mode": "classic", "total_questions": 10 } 
}

// Event: QUESTION
{ 
  "type": "QUESTION", 
  "data": { "index": 0, "text": "Identify the primary unit of quantum information.", "options": ["Bit", "Qubit", "Byte", "Node"], "time_limit_ms": 10000 } 
}

// Event: ANSWER_REVEAL
{ 
  "type": "ANSWER_REVEAL", 
  "data": { "correct_index": 1, "scores": { "Dev": 850 }, "streaks": { "Dev": 3 } } 
}

// Event: INTERMISSION_LEADERBOARD
{ 
  "type": "INTERMISSION_LEADERBOARD", 
  "data": { "scores": { "Dev": 2450 }, "is_final": false } 
}

// Event: GAME_OVER
{ 
  "type": "GAME_OVER", 
  "data": { "final_scores": { "Dev": 7800 }, "economy": { "coins": 450, "trophies": 62 } } 
}

// Event: ERROR
{ 
  "type": "ERROR", 
  "data": { "message": "The requested room action could not be completed." } 
}
```

### Client → Server Communication Payloads (Validated via `sanitize.py`)

```json
// Action: start_game
{ "action": "start_game", "topic": "History", "mode": "hard", "play_mode": "classic" }

// Action: answer
{ "action": "answer", "choice": 1, "time_ms": 3400 }

// Action: join_team
{ "action": "join_team", "team_id": "A" }

// Action: set_team_info
{ "action": "set_team_info", "name_a": "Alpha", "name_b": "Beta", "topic_a": "Tech", "topic_b": "Bio" }

// Action: set_lobby_mode
{ "action": "set_lobby_mode", "mode": "team" }

// Action: Lock/Unlock Room State
{ "action": "lock_room" }
{ "action": "unlock_room" }
```

---

## ✅ Project Milestones Tracker

| Index | Milestone Module Target Description | Project Status |
| --- | --- | --- |
| **1–16** | Initial foundational architecture up through implementation of session persistence. | ✅ Done |
| **17** | Integration of Secure Google Federated Authentication. | ✅ Done |
| **18** | Configuration of Regulatory Compliance paths & Base Navigation layers. | ✅ Done |
| **19** | Mathematical processing logic implementation for Streaks and Multiplier components. | ✅ Done |
| **20** | Execution and deployment of Multiplayer Team Mode routers. | ✅ Done |
| **21** | Deployment of Host Room Locking systems. | ✅ Done |
| **22** | UI input field stabilization refactor layers. | ✅ Done |
| **23** | Solo Isolation Modes, Soft Currency Economy, and integration of CI/CD systems. | ✅ Done |
| **24** | Local Storage persistence architecture for local economy modules. | ✅ Done |
| **25** | Monetization setup: dynamic structural landing configuration + Chai4Me paths. | ✅ Done |
| **26** | AdSense Regulatory Compliance: Cookie Consent Mechanism integration. | ✅ Done |
| **27** | Supabase Global Leaderboard infrastructure configuration. | ✅ Done |
| **28** | Production Play Store Deployment Pipeline Execution. | 🔲 Blocked *(Awaiting Verification)* |
| **29** | Ingestion Engine Hardening and Security Layer configuration. | ✅ Done |
| **29.5** | Generation and alignment of Master App Branding Graphic Vectors (Icons/Splash screens). | ✅ Done |
| **29.6** | Submission processing to the Amazon Appstore. | ✅ Done |
| **30** | AdSense dynamic footprint verification processing expansion (Compliance pages + sitemap). | ✅ Done |
| **31** | **Strategic Pivot:** Architecture decision resolved June 19, 2026 — forked frontend (`web/` + `app/`), backend stays unified. | ✅ Resolved |
| **31.5** | Physical folder split execution: move current `frontend/` → `frontend/web/`, scaffold `frontend/app/`, repoint `capacitor.config.json` and Vercel build root. | 🔲 Next |
| **32** | App Stream: Removal of out-of-scope compliance assets & Chai4Me logic from native wrapper. | ✅ Done |
| **33** | App Stream: Realization of feature-gating routes blocking web access to premier arrays. | 🔲 Next |
| **34** | App Stream: Neo-Brutalism visual skin implementation. Home screen composition **locked** June 22, 2026 (see "Locked Home Screen Composition") — ready to implement against `screens/home.html`. Remaining screens (lobby, game, results) still need their own composition pass before full milestone completion. | 🔄 In Progress |
| **35** | Generation Tickets — Real Spendable Currency. | ✅ Done |
| **36** | Seed Question Bank data layer. Schema + reviewable seed file are complete; Quick Play UI remains future work. | 🔄 In Progress |

---

## 🐛 Defect Registry & Critical Architecture Decisions Log

- **Workflow Split Decision (June 18, 2026):** The website codebase is now entirely frozen. App builds represent the active frontier moving forward.
- **Amazon Appstore Submission status (June 18, 2026):** Initial package validation phase complete.
- **Play Store Release Pipeline Requirements:** When compiling the application for production delivery, execute the following actions precisely:
  1. Synchronize the native file layer tree: `npx cap sync android`
  2. Clean and compile the production bundle via Gradle: `./gradlew.bat clean bundleRelease` (Uses local encrypted configuration keys via `keystore.properties`).
  3. Manually verify that the `versionCode` configuration inside `app/build.gradle` has been properly incremented.
- **Cloud Run Cold Start Penalty:** Inactive infrastructure scales completely down to zero instances, which can cause a ≈ 2s latency penalty on cold requests. Mitigated by firing a warm-up `/health` ping immediately when the application launches.
- **Volatile Session Memory Behavior:** In-memory application objects are cleared whenever Cloud Run containers recycle. This is an acceptable limitation for the current project MVP.
- **Cross-Compilation Architecture Guidelines:** When deploying from ARM64 machines, always use buildx platform targets explicitly: `docker buildx --platform linux/amd64 --push`.
- **JSON Serialization Adjustments:** Exclude `Player.websocket` data properties from JSON transformation tasks to avoid serialization faults.
- **Fallback Content Engine Strategy:** LLM service access is structured with fallbacks; if the Gemini service encounters rate caps, a static fallback question registry takes over to keep matches running.
- **WSL Android Debug Bridge (ADB) Disconnection Issues:** Windows Subsystem for Linux instances cannot naturally discover raw USB endpoint paths. Execute all native ADB commands through Windows PowerShell hosts.
- **Asset Tracking Protocol:** After making changes to any asset files within the frontend folder directory trees, run `npx cap sync android` before building test packages.
- **Profile Sync Precedence:** `profiles.json` data on ephemeral instances is volatile. Treat local client storage configurations as the definitive operational source of truth.
- **Leaderboard Sync Behavior:** The Supabase leaderboard acts as a secondary, long-term cross-session storage node updated at game end. In-game sessions rely primarily on `localStorage`.
- **Verification Audits:** Donation validations remain fully manual to keep the infrastructure footprint lean. Do not write programmatic webhooks or processing scripts to automate payment validation.
- **Database Views Execution Bounds:** The `donor_leaderboard` relation is an encapsulated SQL View asset; structural update or insertion tasks target checking rules incorrectly and will fail.
- **Local Identity Life Cycle Limitations:** Client-side token caches (`State.user._credential`) exist strictly within active browser memory contexts and do not survive page reloads. The initialization block handles profile syncing across page reloads via dedicated Supabase calls instead.
- **Generation Tickets & Question Bank Data Layer (June 30, 2026):** Custom Room generation ticket refund-on-failure follows the same pattern as entry fee refunds in the WebSocket startup flow. The rewarded-ad ticket cap is enforced server-side in `backend/app/services/tickets.py`, not only by future client UI. The reviewable question bank seed file lives at `supabase/seeds/seed_question_bank.py`.
- **Frontend Fork Decision (June 19, 2026):** Resolved the Milestone 31 architecture question — frontend physically splits into `web/` and `app/`; backend remains single and shared across both targets; gating of premium features (Team mode, leaderboard) is UI-only, never backend-side.
- **Visual Identity Pivot (June 20, 2026):** The Milestone 31 Clash Royale-inspired UI direction is superseded. New target: Neo-Brutalism, modeled on a reference mockup (dark charcoal background, thick black borders, hard offset shadows, flat green/red/cream color blocking).
- **Home Screen Structure Exploration (June 22, 2026):** Three structural directions were mocked up against the Neo-Brutalism palette: (1) a direct reskin of the original stacked-button list with brutalist borders/shadows — rejected, felt like a reskin rather than a real structural change; (2) a restructured version with a single dominant primary CTA, a two-tile Create/Join row, and a de-emphasized utility row — **selected as the base direction**; (3) a zine/collage variant adding a torn zigzag section divider, a giant translucent "?" watermark, taped sticker badges, a ticket-notched CTA, alternating-rotation tiles, and a scrolling marquee footer — explored, but explicitly **not selected**; logged here so it isn't re-proposed from scratch. Direction (2) was finalized with one adjustment: the decorative retro-monitor icon was swapped for a dedicated trophy badge, since trophy iconography is a core identity element used across results, leaderboard, and the economy, and needed to stay visually present on the home hero rather than be replaced by a generic icon. See "Locked Home Screen Composition" above for the final structure and `forge-neo-brutalism-home-final.html` for the implementation reference.
- **Typography Decision — Hero Wordmark (June 22, 2026):** Resolved the open question from the original Neo-Brutalism plan. Archivo Black is used for the "FORGE" hero wordmark only, with a green-fill/black-stroke/red-offset-shadow duotone stamp treatment. Press Start 2P remains the typeface for every other UI element (buttons, labels, taglines, badges, footer) — it is not being phased out, just no longer used at poster scale.
- **Usability Rule — No Rotating Functional Inputs (June 22, 2026):** Firm rule, not a style preference: name-entry and room-code fields must always render perfectly level regardless of any decorative rotation/collage treatment applied elsewhere on a screen. This rule should carry forward to lobby, game, and results screens as their own Neo-Brutalism passes happen.
- **`/mnt/c` WSL Friction (June 2026):** Repo lives at `/mnt/c/QuizApp/forge`. This filesystem bridge has twice caused tooling failures invisible from the Linux side: (1) directory-level `mv`/rename operations hitting silent `Permission denied` with no useful diagnostic, (2) `npx cap sync android` failing with a corrupted `.bin` shim due to broken symlinks (`rm -rf node_modules package-lock.json && npm install` fixed it). If either recurs, suspect the `/mnt/c` bridge before suspecting the command itself. Long-term fix under consideration: relocate repo to `~/forge` on the native Linux filesystem.

---

## 📋 Technical Implementation Guidelines

1. **Code Standards:** Maintain highly structured, self-documenting code supported by clean Python typing and descriptive docstrings.
2. **Asynchronous Patterns:** Document the underlying reasoning behind any asynchronous code patterns or WebSocket message transitions clearly.
3. **Modular Strategy:** Build software components through small, isolated modules. Focus on modifying one target file at a time.
4. **Context Maintenance:** Keep this `CLAUDE.md` documentation file updated as milestones are met.
5. **Infrastructure Costs:** Maintain a strict $0 infrastructure cost model. Do not implement paid cloud integrations.
6. **Architecture Compatibility:** Flag potential dependencies or compatibility blocks related to ARM64 execution proactively.
7. **Problem Resolution:** Identify and resolve systemic roots of codebase defects rather than patching superficial symptoms.
8. **Environment Swapping:** Production distributions point directly to active cloud cluster paths; local testing environments switch endpoints automatically based on the host routing origin.
9. **Visual Design Matrix:**
   - **Website Styling Blueprint:** Blue/White base color schemes, *Press Start 2P* and *Nunito* typography layouts, Accent Gold components (`#FFD93D`), flat Kahoot-style buttons. (Frozen — never touched by app-track style work.)
   - **App Styling Blueprint:** **Neo-Brutalism.** Charcoal backgrounds, thick black borders (2.5–3px) on every interactive surface, hard offset drop-shadows with zero blur, flat green/red/cream color blocking (no gradients), blocky low-radius buttons and tiles (pills reserved only for the currency readout and name field), Archivo Black for the hero wordmark only, Press Start 2P everywhere else. Home screen composition locked — see "Locked Home Screen Composition" above.
10. **Device Operations:** Execute native terminal commands using Windows PowerShell exclusively.
11. **Advertising Integrity:** Never integrate low-tier, high-intrusion ad networks.
12. **Database Protection:** Ensure Row-Level Security (RLS) configurations remain active on all Supabase tables at all times; never disable them.
13. **AdSense Entry Constraint:** The web application track must always land unauthenticated cold users directly onto `landing.html` to ensure crawler compliance. This routing constraint does not apply to native app builds once they fork from the web workflow.
14. **Context Provision over Drafting:** Provide complete file contents instead of abbreviated code placeholders during context transitions.
15. **Production Build Protocol:** Always execute a full refresh and synchronization process before submitting software builds to the app stores. This guarantees the latest frontend optimizations match your deployed native runtime layers.
16. **Website Freeze Rule:** The website branch is frozen as of Milestone 31. Do not introduce feature changes to web-track assets unless explicitly instructed to do so. Treat all general development requests as targeting the app track by default.
