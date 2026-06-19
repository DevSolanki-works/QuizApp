# CLAUDE.md — Forge: AI Trivia Showdown

> **Context Routine:** Paste this file at the start of every new conversation so Claude has full context.
> **Maintenance Protocol:** Claude updates this file after every major milestone and provides the new version.

---

## 🧠 Who I Am

* **Status:** 2nd-year CS AI/ML student (Strong Python background, currently learning full-stack).
* **Timeline:** Building this over a 1-month vacation.
* **Ultimate Goal:** Deploy to Google Play Store + monetize ($0 infrastructure constraint).
* **Hardware Architecture:** ARM64 machine.
* **Development Environment:** WSL (Ubuntu) on Windows; Python virtual environment located at `backend/.venv`.

## 🎮 Project Overview: Forge — AI Trivia Showdown

A real-time multiplayer mobile quiz game. Players enter **ANY** topic $\rightarrow$ AI generates a custom quiz $\rightarrow$ players compete live via WebSockets using a 4-digit room code.

---

## 🪓 STRATEGIC PIVOT (Milestone 31): Website vs App Workflow Split

> ⚠️ **CRITICAL ARCHITECTURAL NOTICE**
> Starting Milestone 31, the Website and App are split into two separate development tracks. They currently share the same `frontend/` codebase, but going forward, most active work occurs on the **App track**. Review this before starting any new session.

### The "Why"

* **The Website (`forgetrivia.online`):** Exists primarily for AdSense revenue + SEO discoverability. It is "done enough" for now and is completely frozen at its current feature set.
* **The App (Android via Capacitor):** Now the primary development priority. The goal is to drive Play Store downloads by turning the app into the full/premium experience, treating the website as a lighter teaser/funnel.

### ❄️ What Stays Frozen (Website Track)

* **Zero Feature Development:** No further feature work will be done on `forgetrivia.online` for the time being.
* **AdSense Compliance Stability:** Keep all AdSense-required pages exactly as they are:
`landing.html`, `about.html`, `privacy.html`, `terms.html`, `contact.html`, `how-to-play.html`, `topic-guide.html`, `trivia-tips.html`, `multiplayer-quiz-guide.html`, `ai-trivia-questions.html`, `dev-log.html`, `sitemap.xml`, `robots.txt`, `ads.txt` / `app-ads.txt`.
* **Routing Security:** Do not touch `landing.html` boot routing, cookie consent settings, or AdSense script tags.
* **Timeline:** The Milestone 30 AdSense resubmission timeline (wait for GSC indexing, then 2–3 weeks) still applies independently of this pivot.

### 🔥 What Becomes Active (App Track)

* **Targeted UI Overhaul:** A major visual redesign targeted **ONLY** at the Capacitor/Android build (Milestone 31+).
* **New Visual Identity:** Transitioning to a *Clash Royale*-style mobile game UI.
* **Feature Pruning:** Heavy feature removals and strict feature-gating (detailed below).

### 📐 Architecture Decision — RESOLVED (June 19, 2026)

Resolved: **Forked frontend.** `frontend/` splits into `frontend/web/` (current site, frozen, untouched) and `frontend/app/` (new Capacitor target, active development). `capacitor.config.json`'s `webDir` points to `frontend/app`. Vercel's build root for the live site points to `frontend/web`.

This guarantees the website can't be affected by app UI work — separate files, not a shared tree gated by `data-forge-target`. The `platform.js` `data-app-only`/`data-web-only` machinery is retired going forward; a slim app-only variant may remain in `frontend/app/` solely for local-dev backend URL switching.

The **backend stays single and shared** — see "Backend Stays Unified" below. Only the frontend forks.

### ⚙️ Backend Stays Unified — No Backend Fork

The FastAPI backend is never forked or branched by client target. Web and app hit the exact same endpoints and WebSocket protocol. Team Mode and the leaderboard already exist server-side; access to them is gated **exclusively by withholding UI entry points on the website build**, never by backend logic. Do not add target/platform checks to backend code. If a future feature ever needs true server-side gating, treat that as a deliberate, separately-flagged decision — not the default pattern.

## 📱 App UI Direction — Mobile-Game-Inspired Overhaul (Milestone 31+)

* **Clarification:** Clash Royale is a reference point for navigation feel — chunky tactile buttons and a clear menu/leaderboard/shop-style navigation pattern — not a visual template to replicate. Blueprint-level inspiration, not a skin clone.

* **Juicy Interactive Elements:** Chunky, glossy, "3D-bevel" buttons featuring strong drop shadows instead of flat pixel elements. Provides larger, clearer tap targets and exaggerated press states.
* **Card-Based Panels:** Menus (room creation, mode select, results) will migrate toward tactile card/chest panels rather than translucent glassmorphism cards.
* **Persistent Currency Bar:** A dedicated header row layout mimicking a mobile game currency bar (Coin/Trophy icons + count pills, always visible at the top of the screen with an animated count-up on state change).
* **Arena Backgrounds:** Vibrant, highly saturated gradient themes per screen. Retain the existing particle/confetti bursts but make them punchier.
* **Reward Sequences:** Potential implementation of chest/reward-reveal animations during the `GAME_OVER` / results screen phase.
* **Audio Constraints:** Sound stays limited to the existing synthesized Web Audio API setups ($0-cost constraint), but visual feedback on interactions must feel significantly heavier.

---

## 🚫 App-Only Removals (Planned, Not Yet Implemented)

These components exist on the web strictly for monetization, SEO, or compliance reasons that don't apply inside a native wrapper. They will be entirely stripped from the **app build only**:

* **Chai4Me Micro-Donations:** Remove the `chai-link` donation button completely from `home.html`'s top-left actions within the app.
* **SEO Boilerplate Pages:** Entirely drop pages created to satisfy AdSense's "Low Value Content" criteria (`landing.html` copy, `about.html`, `how-to-play.html`, `topic-guide.html`, `trivia-tips.html`, `multiplayer-quiz-guide.html`, `ai-trivia-questions.html`, `dev-log.html`).
* **Navigation Pruning:** Strip out the persistent footer navbar (`#app-footer`) linking to the legal/explainer pages.
* **Legal Redirects:** `privacy.html` and `terms.html` must remain accessible to satisfy Play Store regulations, but should be transformed into clean external links pointing to the website rather than bloating native screens.
* **Ad Verification:** AdSense scripts are already skipped for `target === "app"` via `platform.js`. Ensure this mechanism remains untouched.

---

## 🔒 Web vs App Feature Gating (Planned, Not Yet Implemented)

To incentivize app installation, the **app** will be treated as the full-featured tier, while the **website** acts as a restricted teaser layout.

* **Leaderboard Access:** Currently public and free on the website via `leaderboard.html`. Plan: Restrict or entirely pull this entry point from the web layout, making global leaderboard inspection an app-exclusive experience.
* **Advanced Game Modes:** Team Mode (and all future game modes) will become app-exclusive features. The web track remains frozen on Classic and Solo modes.
* **Teaser UX UI:** The web front-end should actively tease locked content (e.g., *"Team Mode & Global Leaderboards are available in the app"* alongside an explicit Play Store badge link) instead of hiding components silently.
* **Gating Implementation:** Extend the functional `data-app-only` / `appOnlyFeaturesEnabled` pattern within `platform.js`.
* **Backend Verification:** A future architecture check is required to ensure the WebSocket `set_lobby_mode` action drops or rejects `mode: "team"` server-side if the incoming connection is verified as originating from a web-client agent.
* **Rationale:** Gating Team Mode and the global leaderboard to the app is the primary install-driver for Play Store downloads, which monetizes better long-term than additional AdSense traffic on the frozen website.

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

* **Frontend Application:** `http://127.0.0.1:8080`
* **Backend Core API:** `http://127.0.0.1:8000`
* **Interactive API Documentation:** `http://127.0.0.1:8000/docs`

### 🔧 Known Local Development Quirks

* **Supabase Defer Race Condition (FIXED - M29):** Because `supabase-client.js` loads asynchronously via `defer`, returning authenticated users previously triggered an `"lbFetchProfile is not a function"` crash during the application's boot block initialization. This has been resolved via a `waitForSupabase()` polling helper function.

---

## 💰 Monetization Strategy

1. **Google AdSense (Primary Web Driver):** Web track deployment only. Pending manual configuration review approval (Blocked: PAN card pending verification).
2. **Chai4Me Micro-Donations:** Web track deployment only. Profile endpoint: `https://www.chai4.me/devsolankiworks`
3. **In-Game Soft Currency:** Engagement loop powered by virtual Coins and Trophies accumulated dynamically across gameplay sessions (Web + App shared data).
4. **App Acquisition Funnel:** Driving app store traction by gating premier content (Team mode, global ranking metrics) behind the native wrapper build.

### ⛔ DEPRECATED — Forbidden Ad Technologies

> **Hard Prohibition:** Never integrate low-tier, high-intrusion monetization tools. This includes: Monetag, vignette/interstitial ads, popunders, force-push notification monetization assets, or any instant-approval programmatic platforms.

### AdSense Compliance Checklist (Website Only)

* [x] AdSense core script tags integrated into every single crawlable HTML node.
* [x] Clear global navigation elements to explicit Privacy Policy and About screens available on every viewport.
* [x] Functional localized cookie consent banner with embedded `localStorage` tracking and NPA capability.
* [x] High semantic text quality across `landing.html` to robustly counter "Low Value Content" rejections.
* [x] Updated structural mapping index assets (`robots.txt` and `sitemap.xml`) served dynamically from root.
* [x] Strict routing enforcement ensuring cold crawlers drop directly onto semantic rich content (`landing.html`).
* [ ] Manual application review sign-off $\rightarrow$ **PENDING** (Awaiting identification/PAN clearance).

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

* **WebSocket Ingestion:** Every client message is parsed against an absolute action filter configuration key allowlist (`sanitize.VALID_ACTIONS`).
* **Prompt Injection Defense:** Topics undergo pattern evaluation via regex-based blocklists prior to triggering downstream LLM generations via Gemini.
* **Financial Protection Layer:** Economy modification calls require an unexpired, authentic Google JWT mapping cleanly to the payload's `user_id`.
* **Rate Limiting Engine:** Enforces connection and action quotas on a per-IP basis, using securely extracted cloud load-balancer signatures.
* **Navigation Route Interceptors:** Strict frontend validation guards access to operational routes: `lobby` demands verified parameters (`roomCode`, `playerName`), `game` requires an active WebSocket channel, and `results` checks for population metrics.
* **Timestamp Calibration:** Latency tracking values (`time_ms`) undergo backend boundary checking, clamping values to `[0, time_limit_ms + 500ms]` to eliminate manual speed hacks.

---

## 🗄️ Supabase Persistence Engine (Milestone 27)

### Project Instance Configuration

* **Endpoint URL:** `https://ffstsbwkianjcjpqvmtv.supabase.co`
* **Access Control:** Public Anon Key (Refer to explicit token strings within `supabase-client.js`)
* **Regional Hosting:** Southeast Asia (Singapore Data Center Hub)

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
| `donations` | Ledger tracking micro-transactions / incoming UPI claims. Transitions states: `pending` $\rightarrow$ `approved` $\rightarrow$ `rejected`. |
| `donor_leaderboard` | **SQL VIEW.** Read-only node compilation. Aggregates and displays mathematical calculations summing approved transaction tallies. |

### Operational Logic

* **Asynchronous Updates:** Ranking data updates run concurrently inside `applyUserEconomy()` via fire-and-forget patterns.
* **Conflict Resolution:** `lbUpsertPlayer()` runs explicit conflict checks on `google_id` configurations to guarantee playing records append to existing rows instead of resetting current scores.
* **Manual Verification:** Financial data auditing flows are fully manual: verification happens via the Supabase admin interface by transitioning values to `approved` only after reviewing physical banking notifications.

---

## 🏗️ Technical Stack Constraints (LOCKED)

| Technology Layer | Selection | Rationale & Boundaries |
| --- | --- | --- |
| **Frontend Framework** | HTML5 / CSS3 / Vanilla JavaScript | Retains clean portability requirements for seamless compilation into native systems using CapacitorJS. |
| **Database Solution** | Supabase (Postgres Engine) | Free tier pricing model satisfies $0 operational resource guidelines perfectly. |
| **Mobile Deployment** | CapacitorJS $\rightarrow$ Android Application Bundle | Free, robust, automated wrapper pipelines matching local workflow parameters without compounding expenses. |
| **Backend Architecture** | Python 3 / FastAPI Engine | Excellent fit for rapid asynchronous handling; maximizes development velocity. |
| **Artificial Intelligence** | Gemini 2.5 Flash Lite | Leverages high-performance inference at a $0 API price point. |
| **Real-time Pipeline** | Native FastAPI WebSocket Implementations | Low-latency state sync features built directly into core framework layers. |
| **State Persistence** | Transient In-Memory Python Dictionary Objects | Minimizes architecture footprint; avoids complex local hosting overhead. |
| **Deployment Platform** | Containerized Docker $\rightarrow$ Google Cloud Run | Scalable serverless tier accommodating the $0 infrastructure cap. |

---

## 📁 Project Structure

```text
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
    ├── web/                      ← Frozen — exact current site, never touched by app work
    │   ├── index.html, platform.js, supabase-client.js, ads.txt, robots.txt, sitemap.xml...
    │   └── screens/ (landing, home, lobby, game, results) — unchanged Kahoot/pixel skin
    └── app/                      ← Active — Capacitor target, new mobile-game-inspired UI
        ├── index.html
        ├── platform-app.js       ← trimmed: just local-dev backend URL switching
        └── screens/ (rebuilt visually, same WS message contracts as backend)
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
| **New Profile Initialization** | $+200$ | $+50$ |
| **Multiplayer Room Entrance Fee** | $-25$ | — |
| **Multiplayer Match Champion** | $+\text{Collected Pool}$ | — |
| **Solo Performance ($\ge 5$ Correct)** | $+10$ | — |
| **Solo Performance ($4-5$ Correct)** | — | $+1$ |
| **Solo Performance ($6-10$ Correct)** | — | $+2 \text{ per correct answer over baseline } 5$ |
| **Solo Performance ($< 4$ Correct)** | — | $-2 \text{ (Floor constraint enforced at } 0\text{)}$ |

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

### Server $\rightarrow$ Client Communication Payloads

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

### Client $\rightarrow$ Server Communication Payloads (Validated via `sanitize.py`)

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
| **32** | App Stream: Removal of out-of-scope compliance assets & Chai4Me logic from native wrapper. | 🔲 Next |
| **33** | App Stream: Realization of feature-gating routes blocking web access to premier arrays. | 🔲 Next |
| **34** | App Stream: *Clash Royale*-style asset skinning implementation. | 🔲 Next |
| **35** | Query management configurations (5/10/15/20 count array filters) + Social Share tooling. | 🔲 Backlog |

---

## 🐛 Defect Registry & Critical Architecture Decisions Log

* **Workflow Split Decision (June 18, 2026):** The website codebase is now entirely frozen. App builds represent the active frontier moving forward.
* **Open Architecture Question (Blocks Milestone 34):** Decide between a shared codebase with complex theme-swapping, or splitting the project into separate `frontend/app` and `frontend/web` directories. Resolve this before implementing the *Clash Royale* UI skin.
* **Amazon Appstore Submission status (June 18, 2026):** Initial package validation phase complete.
* **Play Store Release Pipeline Requirements:** When compiling the application for production delivery, execute the following actions precisely:
1. Synchronize the native file layer tree: `npx cap sync android`
2. Clean and compile the production bundle via Gradle: `./gradlew.bat clean bundleRelease` (Uses local encrypted configuration keys via `keystore.properties`).
3. Manually verify that the `versionCode` configuration inside `app/build.gradle` has been properly incremented.


* **Cloud Run Cold Start Penalty:** Inactive infrastructure scales completely down to zero instances, which can cause a $\approx 2\text{s}$ latency penalty on cold requests. Mitigated by firing a warm-up `/health` ping immediately when the application launches.
* **Volatile Session Memory Behavior:** In-memory application objects are cleared whenever Cloud Run containers recycle. This is an acceptable limitation for the current project MVP.
* **Cross-Compilation Architecture Guidelines:** When deploying from ARM64 machines, always use buildx platform targets explicitly: `docker buildx --platform linux/amd64 --push`.
* **JSON Serialization Adjustments:** Exclude `Player.websocket` data properties from JSON transformation tasks to avoid serialization faults.
* **Fallback Content Engine Strategy:** LLM service access is structured with fallbacks; if the Gemini service encounters rate caps, a static fallback question registry takes over to keep matches running.
* **WSL Android Debug Bridge (ADB) Disconnection Issues:** Windows Subsystem for Linux instances cannot naturally discover raw USB endpoint paths. Execute all native ADB commands through Windows PowerShell hosts.
* **Asset Tracking Protocol:** After making changes to any asset files within the frontend folder directory trees, run `npx cap sync android` before building test packages.
* **Profile Sync Precedence:** `profiles.json` data on ephemeral instances is volatile. Treat local client storage configurations as the definitive operational source of truth.
* **Leaderboard Sync Behavior:** The Supabase leaderboard acts as a secondary, long-term cross-session storage node updated at game end. In-game sessions rely primarily on `localStorage`.
* **Verification Audits:** Donation validations remain fully manual to keep the infrastructure footprint lean. Do not write programmatic webhooks or processing scripts to automate payment validation.
* **Database Views Execution Bounds:** The `donor_leaderboard` relation is an encapsulated SQL View asset; structural update or insertion tasks target checking rules incorrectly and will fail.
* **Local Identity Life Cycle Limitations:** Client-side token caches (`State.user._credential`) exist strictly within active browser memory contexts and do not survive page reloads. The initialization block handles profile syncing across page reloads via dedicated Supabase calls instead.
* **Frontend Fork Decision (June 19, 2026):** Resolved the Milestone 31 architecture question — frontend physically splits into `web/` and `app/`; backend remains single and shared across both targets; gating of premium features (Team mode, leaderboard) is UI-only, never backend-side.

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
* **Website Styling Blueprint:** Blue/White base color schemes, *Press Start 2P* and *Nunito* typography layouts, Accent Gold components (`#FFD93D`), flat Kahoot-style buttons.
* **App Styling Blueprint (Milestone 31+):** *Clash Royale*-style game UI. Chunky 3D-bevel buttons, card-based panels, dedicated currency-bar layouts, and high-saturation arena gradient layers.


10. **Device Operations:** Execute native terminal commands using Windows PowerShell exclusively.
11. **Advertising Integrity:** Never integrate low-tier, high-intrusion ad networks.
12. **Database Protection:** Ensure Row-Level Security (RLS) configurations remain active on all Supabase tables at all times; never disable them.
13. **AdSense Entry Constraint:** The web application track must always land unauthenticated cold users directly onto `landing.html` to ensure crawler compliance. This routing constraint does not apply to native app builds once they fork from the web workflow.
14. **Context Provision over Drafting:** Provide complete file contents instead of abbreviated code placeholders during context transitions.
15. **Production Build Protocol:** Always execute a full refresh and synchronization process before submitting software builds to the app stores. This guarantees the latest frontend optimizations match your deployed native runtime layers.
16. **Website Freeze Rule:** The website branch is frozen as of Milestone 31. Do not introduce feature changes to web-track assets unless explicitly instructed to do so. Treat all general development requests as targeting the app track by default.