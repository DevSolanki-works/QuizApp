# CLAUDE.md — Forge: AI Trivia Showdown

> **Context Routine:** Paste this file at the start of every new conversation so Claude has full context.
> **Maintenance Protocol:** Claude updates this file after every major milestone and provides the new version as a complete copyable block.

---

## 🧠 Who I Am

- **Status:** 2nd-year CS AI/ML student (Strong Python background, currently learning full-stack).
- **Current Phase:** LIVE on Google Play Store with real ads, real economy, real (small) user base — mostly friends/family/close network so far. Core app + monetization is technically stable after a genuinely rough stabilization stretch (see Decisions Log). **Current bottleneck is growth/distribution, not features or stability.**
- **Ultimate Goal:** Sustainable Play Store growth + AdMob revenue + ongoing feature development.
- **Hardware Architecture:** ARM64 machine.
- **Development Environment:** WSL (Ubuntu) on Windows; Python virtual environment at `backend/.venv`; Android Studio + Gradle run on the Windows side.

---

## 🚨 CRITICAL: This Is a Live Product Now

**Real users have the app installed with real coins, trophies, tickets, and streaks — and real ad revenue is flowing.**

- **Economy-changing backend changes are backward-compatibility risks.** A schema change, a renamed field, or altered gating logic can break the experience for users on an older client build.
- **In-App Update system is now live** (see below) — but it only protects users on builds that already contain the update-checking code. See Decisions Log for the bootstrapping gap this creates for the current release.
- **Test on a real device via USB debug BEFORE shipping to production.** Localhost testing does not exercise WebSocket reconnect behavior, AdMob, Capacitor plugins, Firebase Analytics, or real Google Sign-In token expiry.
- **Prefer Internal Testing track over direct-to-production** for anything touching economy, auth, or ads.

---

## 🎮 Project Overview: Forge — AI Trivia Showdown

A real-time multiplayer mobile quiz game. Players enter **ANY** topic → AI generates a custom quiz → players compete live via WebSockets using a 4-digit room code. Live on Google Play Store, package ID `com.devsolanki.forge`.

---

## 🪓 Website vs App Workflow Split (unchanged)

- **Website (`forgetrivia.online`):** Frozen except for `app-ads.txt` (required for AdMob verification).
- **App (Android via Capacitor):** Primary development priority.
- **Backend Stays Unified:** Never forked. Feature gating is UI-only.

---

## 💰 Economy System (stable, unchanged this session)

- **Coins:** 200 starter, standard win/ad/pot sources, standard sinks. Pure balance, no reset logic.
- **Trophies:** 50 starter, never spent, standard tier/floor system.
- **Generation Tickets:** Pure persistent balance (architecturally identical to coins, redesigned July 2026). 2 free custom-topic generations/day (isolated counter, only date-sensitive logic in the whole system), then spends from ticket balance. Earned via coins (25/ticket), ads (5/day cap + 2-min cooldown), Daily Reward.
- **Daily Reward:** 7-day cycle, terminates permanently after first Day-7 completion (`reward_cycle_completed` flag).

Full mechanics unchanged from prior versions — see Supabase schema below for the authoritative field list.

---

## 📣 Ads System — LIVE, real revenue flowing (July 2026)

> Observed real-world data: ~$0.92 eCPM (India-heavy traffic — structurally normal for this market, not a technical problem, see Decisions Log). Low show rate (~22%) is expected given the preload-everywhere architecture, not a bug.

### Ad Formats

Wrappers live in `frontend/app/admob.js`, all via `@capacitor-community/admob`:

1. **`RewardedAd`** — standard opt-in rewarded video. Preloaded at boot.
2. **`Interstitial`** — plain, non-rewarded. Preloaded at boot. Now the ONLY interstitial format actually used (see below).
3. **`RewardedInterstitial`** — fully built and functional (confirmed exact plugin method/event names against `node_modules`), but **currently unused/dormant**. Real usage data showed poor player understanding/engagement with this format, and free generations are already abundant via other sources — not worth the added complexity right now. Code is intentionally left intact for future revival with a higher-value reward. **Do NOT auto-preload this at boot** — nothing calls it currently, preloading would be a 100% wasted ad request.

### Current Ad Triggers, By Mode — FINAL architecture (tap-driven only, no background timers)

**Solo Mode (Quick Pick AND Custom Topic — both, per current spec):**
- **2X Coins / No Thanks** — replaces Play Again/Back Home on results screen when player earned coins (5+ correct). Tap-triggered, immediate.
- **"No Thanks" decline tracking** (`soloDeclineDouble()` in `results.html`) — separate persistent counters for Quick Pick vs Custom Topic (`forge_qp_declines` / `forge_custom_declines`). On the **2nd consecutive decline** for either topic type → plain `Interstitial` shows, then navigates home, counter resets. Tapping 2X Coins and watching it through resets that mode's decline counter to 0 as a "thank you," regardless of current count.
- **⚠️ Architecture note:** This flow is 100% tap-driven — there is NO background timer or automatic post-game check anymore. An earlier version used a 5-second `setTimeout` background check (`_runAdFlowCheck`) running independently of what the player tapped, which caused a real production bug: two ad systems could fire near-simultaneously (watch a coins ad, receive a ticket reward instead). This was fully removed and rebuilt as decline-based, eliminating the race condition by construction — only one ad-related action can ever be in flight per results screen now.

**Classic & Team Mode:**
- **Entry Fee Recovery** — shown on loss in a paid room.
- **Double Winnings** — shown on win with a payout.
- No interstitial/frequency-cap system exists for these modes — not built.

**Home Screen:**
- **Streak Saver** — badge+modal pattern (not a front-page banner), tap the "!" on Day Streak stat.

**Shop Screen:**
- **Watch Ad for Ticket** — 5/day server-side cap + 2-minute client-side cooldown.

### All five rewarded-ad-then-grant flows now have pre-ad staleness checks

`_isSessionLikelyStale()` (heuristic: signed in >50 min ago = likely stale token) is checked **before** every ad plays, not just after — eliminates the "watch a full ad, then get told it didn't count" experience. Applied to: Shop ad-for-ticket, Entry Fee Recovery, Double Winnings, Solo 2X Coins, Daily Reward claim.

### app-ads.txt

Lives at `forgetrivia.online/app-ads.txt`. Must match Play Console's "Developer website" field exactly (protocol + no trailing slash + no www mismatch) or verification fails.

---

## 📊 Analytics — Firebase Analytics, LIVE (July 2026)

**Chosen over PostHog** specifically because Firebase links directly to AdMob (AdMob Settings → Linked services), correlating ad revenue with retention/engagement in one dashboard — valuable given monetization is a core goal. PostHog has no AdMob awareness.

Wrapper: `frontend/app/analytics.js`, via `@capacitor-firebase/analytics`. Method names (`setUserId`, `setCurrentScreen`, `logEvent`) **confirmed correct** against actual installed `node_modules` definitions — no longer just assumed from docs.

**Requires native config**, unlike the ad plugins — `google-services.json` in `android/app/`, plus Gradle wiring (`classpath 'com.google.gms:google-services'` + `apply plugin` in `app/build.gradle`). Linked to AdMob via AdMob Console → Settings → Linked services → auto-creates a matching Firebase project.

**Events currently tracked:**
- Automatic screen views on every `goTo()` navigation.
- `game_started` (play_mode, is_quick_pick, difficulty) — Solo/Classic only, not Team.
- `game_completed` (play_mode, score, total_questions, is_quick_pick).
- `game_abandoned` (play_mode, question_index) — fires on Leave Game. Best available drop-off signal.
- `ad_reward_granted` (trigger, amount) — wired on all rewarded-ad success paths: `entry_fee_recovery`, `double_winnings`, `solo_double_coins`, `streak_saver`, `shop_watch_for_ticket`.
- `Analytics.identify(userId)` on sign-in, `Analytics.reset()` on sign-out.

**Not yet tracked:** Team mode game lifecycle, lobby abandonment (room created/joined but never started), Shop views without purchase, Daily Reward claims as a dedicated event, sign-in/sign-out as dedicated events.

---

## 🔄 In-App Updates — Google Play Core API, LIVE (July 2026)

Wrapper: `frontend/app/app-update.js`, via `@capawesome/capacitor-app-update`. Zero new backend/infra — uses Google's own Play Core library and Play Console's existing per-release **"In-app update priority"** field (0–5, set at publish time).

- **Priority 0–3 (default):** Flexible flow — downloads in background while player keeps playing, small dismissible "restart to apply" toast once ready. Use for all normal polish/bugfix/content releases.
- **Priority 4–5:** Immediate flow — full-screen blocking update UI, rendered natively by Google (not custom-built). Use ONLY for genuinely unsafe-to-keep-running-old-version releases (e.g. economy-breaking changes).

**⚠️ Critical bootstrapping gap — read before using priority 4–5 for real:** The update-checking code only runs on devices that already have a build containing it. Users on pre-this-feature builds have NO listener for this at all — marking a release priority 4–5 does nothing for them; they still need Play's background auto-update or a manual Play Store visit to even reach the first build that contains the checker. **Do not mark a release priority 4–5 until Play Console → Statistics → version distribution confirms most active installs are already on a build that includes this feature.** The transitional release that ships this feature itself should stay at priority 0.

**OTA/Live Update (Capgo or similar) — explicitly evaluated, deliberately NOT implemented.** Would allow bypassing Play Store review entirely for JS/HTML/CSS-only changes, but requires either self-hosting real infrastructure ($0 constraint conflict) or a paid hosted tier, and removes Google's review safety net for an app whose economy has already had several real production incidents this session. Worth a dedicated future evaluation once release stability has a longer track record — not a casual add-on.

---

## 🌐 Online 1v1 Duel Mode — Design Spec (unchanged, still not started)

> **NEW PRIORITY CONTEXT (July 2026):** Given the current growth bottleneck (near-zero conversion from LinkedIn/Instagram/Discord-indie-dev-group posting — wrong audiences for a casual mobile game, see Decisions Log), **Async Challenge Mode specifically is now the top feature priority**, not because it was next in sequence, but because it's a built-in viral growth loop ("Can you beat my score?") that directly attacks the actual current bottleneck, reuses existing Solo infrastructure, and doesn't touch the live economy (low regression risk).

**Async Challenge Mode (build first):** Player completes a solo game → "Challenge a friend to beat this score" → shareable link/code → friend plays identical cached questions → sees their result against the original player's ghost score → 24-hour window, push notification on result.

**Sync 1v1 Queue (second, unchanged spec):** Matchmaking within ±100 trophies, 30s wait/bot fallback, 50-coin entry, Blind Draft topic selection.

No code exists for either yet.

---

## 📢 Growth & Distribution — new focus area (not code, but part of current priorities)

- Marketing channels tried (LinkedIn, Instagram static posts, Discord indie-dev groups) yielded near-zero conversion — **channel mismatch, not an app-quality signal.** LinkedIn/Discord-dev-groups reach the wrong audience (professionals/developers, not casual players); static Instagram posts get suppressed without engagement momentum.
- **Better-fit channels identified:** short gameplay clips (Reels/YouTube Shorts, NOT TikTok — banned in India) showing real fun moments rather than announcement posts; direct WhatsApp/Telegram sharing into college/friend groups (likely highest-leverage given current network); trivia-focused subreddits with genuine engagement; free Play Store ASO (screenshots/description/keywords).
- Video editing: CapCut (free, mobile, no editing background needed) — record via Android's built-in screen recorder, trim to 10–20s, auto-caption, export.

---

## 💻 Local Development (unchanged)

Frontend dir rule, router caching gotcha, USB debug testing flow, AdMob test-device registration — all unchanged from prior versions, see previous file revisions for exact commands.

---

## 🏗️ Technical Stack (unchanged, now includes analytics + update layers)

HTML/CSS/Vanilla JS frontend, FastAPI backend, Supabase mirror, Capacitor→Android, Gemini 2.5 Flash Lite, FastAPI WebSockets, Docker→Cloud Run, AdMob (LIVE), Firebase Analytics (LIVE, linked to AdMob), Google Play In-App Update API (LIVE).

---

## 🗄️ Supabase Schema (unchanged)

```text
leaderboard : google_id (PK), display_name, coins, trophies,
              daily_streak, last_played_date, updated_at,
              tickets_today, ad_tickets_used_today, last_ticket_date,
              free_generations_used_today, last_free_generation_date,
              last_reward_date, reward_day, reward_cycle_completed
donations   : id (PK), upi_txn_id, status, amount
donor_leaderboard : SQL VIEW - read only
```

---

## 📁 Project Structure (updated)
forge/
├── CLAUDE.md
├── android/
│   └── app/
│       ├── google-services.json      ← Firebase config (native, not in JS)
│       └── build.gradle              ← google-services plugin applied
├── backend/app/
│   ├── models/quiz.py                ← generation_source field
│   ├── routers/http.py               ← /account/delete, /tickets/bonus-generation-grant
│   └── services/
│       ├── profiles.py               ← delete_profile()
│       └── tickets.py                ← pure balance model
└── frontend/
├── web/app-ads.txt               ← actively maintained
└── app/
├── admob.js                  ← RewardedAd, Interstitial (active); RewardedInterstitial (dormant, kept)
├── analytics.js              ← Firebase Analytics wrapper
├── app-update.js             ← Google Play In-App Update wrapper
├── index.html                ← _isSessionLikelyStale(), _markLocalEconomyWrite(), all API.* error paths fixed
├── supabase-client.js        ← lbUpsertPlayer() fixed, lbDeleteProfile() added
└── screens/
├── results.html          ← soloDeclineDouble() tap-driven ad flow (replaced old timer-based system)
├── daily-reward.html     ← payload bug fixed, pre-claim staleness check added
├── shop.html             ← 2-min ad cooldown, staleness check
└── settings.html         ← Delete Account flow

---

## ✅ Milestone Tracker

| # | Description | Status |
|---|-------------|--------|
| 1–51 | (see prior versions — architecture through Shop ad cooldown) | Done |
| 52 | Firebase Analytics integration — screen tracking + game/ad event tracking | Done |
| 53 | Critical bug fix: Daily Reward claim `ReferenceError` (undefined `payload`) causing every claim to silently fail | Done |
| 54 | Auth-staleness hardening round 2 — fixed 4 `API.*` methods swallowing real error text, added pre-ad `_isSessionLikelyStale()` checks across all 5 rewarded-ad flows | Done |
| 55 | Solo ad-flow architecture rebuild — removed race-condition-prone background timer, replaced with tap-driven decline counter | Done |
| 56 | Custom Topic decline flow simplified: RewardedInterstitial → plain Interstitial (real engagement data), RewardedInterstitial kept dormant | Done |
| 57 | Google Play In-App Update API integration — flexible/immediate via Play Console priority field, zero new backend | Done |
| — | **Async Challenge Mode (viral growth loop)** | **Not started — NEW top priority** |
| — | Classic/Team mode interstitial system | Not started |
| — | Daily Lucky Draw | Not started |
| — | Power-Up system | Not started |
| — | Sync 1v1 Duel Queue | Not started |
| — | OTA/Live updates (Capgo) | Deliberately deferred — see notes above |
| — | Repo migration to `~/forge` | Not started |

---

## Decisions Log & Known Issues (appended this session)

- **Ad-flow race condition (July 2026):** A background 5-second `setTimeout` check running independently of user taps caused two ad systems to fire near-simultaneously — watching a 2X Coins ad could grant a ticket reward instead. Root-caused and fixed by removing all background ad timers entirely; every ad-related action is now triggered directly by a tap, making the collision structurally impossible rather than just less likely. **Lesson: any ad/reward flow with real economic stakes should be tap-driven only — background timers checking "should an ad fire now" independent of user action are a recurring source of this exact class of bug.**
- **RewardedInterstitial underperformed with real users:** Built correctly, plugin methods verified, worked technically — but real analytics showed players didn't understand/engage with the auto-show format, and tickets were already abundant via other sources. Swapped to plain Interstitial for the Custom Topic decline flow. Code kept intact and dormant rather than deleted, in case a higher-value reward makes it worth reviving later. **Lesson: a format performing well in AdMob's own marketing material doesn't guarantee it fits a specific app's specific reward economy — verify against real usage before assuming a "better" format is actually better for you.**
- **Auth-staleness error messages were being silently discarded (round 2):** `syncProfile`, `syncTickets`, `grantDailyRewardTickets`, `grantBonusGeneration` all threw hardcoded generic strings instead of the real backend error text, breaking `_isAuthError()`'s string-matching for those specific calls. Fixed by making all `API.*` methods surface `await r.text()`. **Lesson: when building error-detection logic that pattern-matches on error message content, audit every call site that could produce that error — a single swallowed/generic message anywhere in the chain silently breaks detection for that path only, which is easy to miss since other paths keep working fine.**
- **India eCPM is structurally low, confirmed via real data + industry benchmarks:** Observed ~$0.92 eCPM against a mostly-India user base is normal and expected — India (along with Brazil, Philippines, Indonesia) sits consistently multiple times lower than US/UK/Australia/South Korea across every ad format. Not a technical misconfiguration. Low show rate (~22%) is explained by the preload-everywhere architecture (every ad format preloads proactively; most sessions don't hit every trigger condition) and is unrelated to eCPM — a request that never becomes an impression simply doesn't enter the eCPM calculation.
- **eCPM optimization is low-leverage at current scale:** Revenue ≈ users × sessions × ads-watched × eCPM. With near-zero real users, the eCPM term is the smallest lever available — doubling it moves absolute revenue by cents. Growth/distribution is the actual current bottleneck, not ad tuning or mediation (mediation itself was evaluated and deferred for the same reason — needs real traffic volume to pay off at all).
- **Marketing channel mismatch identified:** LinkedIn (professional audience, not gamers), static Instagram posts (algorithmically suppressed without existing engagement), Discord indie-dev groups (developers, not target players) all yielded near-zero conversion — not a signal the app itself is unappealing. Reframed toward channels with actual audience overlap: short gameplay clips over announcement posts, direct WhatsApp/Telegram sharing into existing social graphs (likely highest-leverage given current network), and free Play Store ASO.
- **In-App Update bootstrapping gap:** The Play Core update-checking code can only detect/prompt updates on devices where it's already running — meaning the very first release that ships this feature cannot force-update anyone, since no prior build has the listener. Must wait for version-distribution data to confirm broad adoption of a build containing this feature before ever using priority 4–5 for real on a future release.
- (All auth-token-expiry, `lbUpsertPlayer`, `.single()` vs `.maybeSingle()`, Gradle/AGP, and Play Store questionnaire lessons from prior sessions remain valid and unchanged — see earlier CLAUDE.md revisions if needed for full detail, condensed here for length.)

---

## Implementation Guidelines

1. **This is a live product with real users and real ad revenue — treat every economy/auth/backend/ad change as a compatibility and revenue risk, not just a feature to ship.**
2. **Ad-adjacent flows must be tap-driven, never background-timer-driven** — this was a real, shipped bug this session. Any new ad trigger design should default to "fires only from a direct user action."
3. **Code standards:** Self-documenting code with Python typing and descriptive docstrings.
4. **Economy integrity:** File-backed backend state is runtime truth; Supabase mirrors display data through explicit, awaited sync paths with real error surfacing — never a swallowed generic error string.
5. **$0 infrastructure by default** — AdMob revenue and Firebase Analytics (free tier) are the exceptions; any future paid tooling (mediation, OTA hosting) needs a deliberate cost/benefit pass, not a casual add.
6. **Verify third-party plugin capabilities against actual `node_modules` type definitions before building around them.**
7. **Test on a real device via USB debug before any production/Internal Testing release**, especially for anything touching AdMob, Firebase, WebSockets, or auth.
8. **Growth is the current bottleneck, not features.** New feature work should be evaluated against "does this help distribution/virality" before "is this fun to build" — Async Challenge Mode is prioritized specifically for this reason.
9. **Database protection:** Keep RLS active on Supabase tables.
10. **Context maintenance:** Update `CLAUDE.md` after major milestones.
11. **Device operations:** Windows PowerShell for native terminal commands; WSL for Node/npm/Python only.