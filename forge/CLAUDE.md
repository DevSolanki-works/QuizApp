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
- **Trophies:** 50 starter, never spent, standard tier/floor system. **LIVE (July 2026):** Trophies are now exclusively earned/lost through Duel Mode (+8 win / −5 loss, floored at 0) — `solo_rewards()` grants coins only. Solo trophy grants removed.
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

## 🌐 Online Duel Mode — NOW ACTIVE DEVELOPMENT (July 2026)

> **Status change:** Moved from "design spec, not started" to actively being built — this is now the single biggest feature on the roadmap. Goal: a genuine second pillar for the game (competitive replay value) that also directly attacks the current growth bottleneck (near-zero conversion from LinkedIn/Instagram/Discord-indie-dev-group posting — wrong audiences for a casual mobile game, see Decisions Log) via built-in virality.

### Phase 1 — Async Challenge Mode (build first)

Player finishes a Solo game → **"Challenge a friend to beat this score"** → generates a shareable link/code → friend opens it → plays the **identical cached question set** the original player faced → sees their result immediately compared against the original player's "ghost" score → result window open for **24 hours** → push notification to both players when the challenge is completed/expires.

**Why this is priority 1:** reuses existing Solo infrastructure (question caching, scoring, results screen) — low build cost. Does NOT touch the live economy — low regression risk on a system that's had several real incidents this session. Built-in viral loop — every challenge sent is a personal, socially-charged invitation, stronger than any manual marketing post.

**Open design questions to resolve before coding:**
- Challenge link/code: short room-code-style string (reusing existing 4-char room code infra) vs full deep link (needs Android App Links / Play Store deferred-deep-linking setup)?
- Does the challenged friend need to sign in, or can they play as guest and only see results (no economy grant) unless they sign in afterward?
- Original player's economy/trophies if their score gets beaten — reward/penalty loop, or pure score-comparison with zero economy stakes (recommended for v1, keeps blast radius small)?
- Push notification delivery — reuse existing `@capacitor/local-notifications` (already wired for Streak Reminders) or needs something else for a friend-initiated notification?

### Phase 2 — Sync 1v1 Duel Queue (after Phase 1 ships and stabilizes)

Real-time matchmaking within ±100 trophies, 30-second wait window with **live online-in-queue count shown** (skip straight to bot-fallback offer if count is 0, rather than a fake 30s wait), 25-coin entry fee per player (pot = 50 coins, winner takes all — reuses the existing `ROOM_ENTRY_FEE`/`_charge_room_entry_fees`/pot-split pattern already proven in Classic/Team, same shape with exactly 2 players).

**Questions:** drawn from the static Quick Picks bank only (not live Gemini) — keeps Duel mode fully isolated from the ticket/generation economy, and guarantees both players get the identical question set for a fair match.

**Timer:** 15 seconds per question — shorter than standard Medium (20s) to keep real competitive pressure and reduce cheating window, but deliberately not shorter than existing Hard mode (10s) so it doesn't feel like pure reflexes over knowledge.

**Topic selection flow:** both players shown the same 3 random bank topics → each picks independently → same pick on both sides → 3–5s confirm pause → game starts on that topic. Different picks → reuse the existing Team Mode topic-randomizer spin UI directly (already built, no new UI needed) → lands on one of the two chosen topics → game starts.

**Tiebreaker:** if scores are exactly level after the final question, one extra bank question decides it (sudden death) — avoids an anticlimactic draw in a mode specifically about "who's better."

**Engagement add-ons (small, cheap, worth building alongside core mechanics):**
- One-tap Rematch on the results screen — re-queues the same two players directly, skips matchmaking.
- Opponent trophy count shown before match starts ("You: 73 🏆 vs Them: 68 🏆") — pure stakes-building, zero new backend needed.
- Preset emoji reactions at match end (👏 😤 🔥) — adds personality without the moderation risk of open chat between strangers. Deliberately NOT free-text chat.
- Lightweight head-to-head record shown if two players are matched again later ("2–1 vs this player") — proven retention hook in casual competitive games.
- Streak fire badge (already built for Solo) carried over into Duel for visual consistency, zero new UI cost.

This phase DOES touch the live economy (entry fees, payouts) — treat with the same caution as the existing Classic/Team entry-fee system. Do not start Phase 2 implementation until Phase 1 has been live and stable for a real stretch.

### Phase 3 — Ticket Duel Mode (future, after Phase 1 + 2 are live and stable)

A second, distinct duel variant using **Generation Tickets** instead of coins as the stake — entry: 1 ticket per player, pot: 2–5 tickets depending on stake tier (mirrors the planned Casual/Pro/High Stakes coin room tiers).

**Unique mechanic (not a reskin of Phase 2):** both players each pick one topic; the match draws **5 questions from each player's chosen topic** (10 total), rather than a single randomly-chosen topic. This makes both players' topic choice matter for the whole match, not just a coin-flip randomizer outcome — a genuinely different competitive shape from Phase 2, not just a different currency skin.

**Requires bank support for partial draws** — `get_quick_pick_questions()` currently returns a full 10-question set per call; this mode needs it callable for exactly 5 from two different topics and interleaved/shuffled together, which is a small extension to `quick_picks.py`, not a rewrite.

Since this uses tickets (not coins), it's naturally isolated from the coin economy — reduces blast radius risk relative to Phase 2, similar reasoning to why Phase 1 avoided touching the coin economy at all.

### Tickets Leaderboard — reconsidered, now conditionally justified

Previously recommended against (tickets were purely a spend-gate resource, no skill signal — ranking on it would reward hoarding, not skill). **Revisit once Phase 3 ships**: at that point, ticket count reflects competitive duel success, not just accumulation — the original objection no longer applies. Do NOT add a Tickets tab to the leaderboard before Phase 3 exists; it would still just reward hoarding today.

### Explicitly not decided yet — do not assume defaults, ask before building

- Whether ranked ladder/seasonal reset applies to Duel mode at all, or if it's purely casual.
- Whether Duel results feed into the existing trophy tier system or need their own separate rating.
- Anti-abuse: entry-fee duels (Phase 2 and 3) create a real incentive for someone to run two accounts on one device and "duel themselves" to farm coins/tickets risk-free. Known open question, not yet mitigated — worth a fraud-detection pass before Phase 2 goes live with real stakes.

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
| 58 | Solo trophy removal — `solo_rewards()` grants coins only; trophies now Duel-exclusive | **Done — NOT device-tested** |
| 59 | **Sync 1v1 Duel Queue (Duel Phase 2)** — full build: matchmaking WS (`/ws/duel/queue`, ±100 trophies widening after 15s, same-IP block, live queue count), unranked bot fallback (no fee/trophies, 5-coin win consolation), 25-coin entry / 50-coin pot, bank-only questions (10 + 3 sudden-death reserves), 15s timer, topic pick + spin, forfeit-beats-score with 25s grace, rematch, emoji reactions, head-to-head record, `duel.html` + home card + game/results integration | **Done — NOT device-tested** |
| 60 | **Daily Lucky Draw** — server-rolled 8-segment wheel (`/lucky-draw/spin`, once/day gate + one rewarded-ad respin/day in profile store), coin prizes 5–50 + 1–2 tickets + rare 200-coin jackpot, `lucky-draw.html` wheel animation lands on server-chosen segment, home banner, `lucky_draw_spin` + `ad_reward_granted` analytics | **Done — NOT device-tested** |
| 61 | **Duel in-game emoji reactions** — reusable emoji bar on the game screen (duel only, 5 presets 👏😤🔥😂🤯 matching the server allowlist in `websocket.py`'s `duel_reaction` handler), 2.5s client-side spam cooldown, own reactions float from YOUR side of the VS banner / opponent's from theirs; results-screen reaction row expanded from 3 → 5 to match. Zero backend changes — the existing `duel_reaction` action already had no game-phase gating. | **Done — NOT device-tested** |
| — | **Async Challenge Mode (Duel Phase 1 — viral growth loop)** | Built + user-tested, working |
| — | **Emoji economy (future):** purchasable emoji packs (coin sink!) and/or level/trophy-tier unlock emojis — extend the preset allowlist server-side per-user; keeps preset-only moderation model | Not started — design when Duel is device-tested |
| 62 | **Real Profile page** — new `screens/profile.html` (avatar, name/email, rank tier badge + progress bar to next tier, coins/trophies/tickets/streak/solo-win-rate/games-played grid, lifetime Duel W/L/T record, sign out). PROFILE nav now routes here when signed in (old bottom sheet superseded; sign-in modal still used when logged out). Duel record tracked client-side in localStorage (`forge_duel_wins/losses/ties`), human matches only, counted once per match via `State._duelRecordCounted` guard in `results.html`. Router: `profile` registered in `Screens` + `SCREEN_GUARDS` (requires sign-in). Future: owned emoji packs surface here | **Done — NOT device-tested** |
| — | Duel results screen polish (richer win/loss presentation) | Partially done — revisit after device test |
| — | Ticket Duel Mode (Duel Phase 3 — dual-topic 5+5 mechanic) | Not started — after Phase 2 stable |
| — | Tickets Leaderboard tab | Deferred — contingent on Phase 3 shipping first |
| — | Classic/Team mode interstitial system | Not started |
| — | Daily Lucky Draw | Done (see #60) |
| 63 | **Power-Up system v1** — first recurring coin sink. 4 types: 50/50 (30🪙, removes 2 wrong), Time Freeze (25🪙, +5s), Double Points (40🪙, 2x next answer — consumed even if wrong), Time Steal (35🪙, duel-ONLY, −5s opponent clock). Bought in Shop (`/powerups/state` + `/powerups/buy`, Google-token-verified), inventory in profile store (`powerups` dict, same pattern as tickets). Used in-game via `use_powerup` WS action (added to sanitize allowlist): server-authoritative — 50/50 wrong-indices sent privately, freeze re-arms the server round timeout, double applied at scoring time, steal broadcast to opponent socket. **Duel caps: max 2 power-ups/match, never the same type twice** (`duel_powerups_used` on Room). All modes get the bar; `POWERUP_USED` broadcast shows everyone who used what (never the effect internals). `powerups.py` service + Shop grid UI + game.html floating bar (raised above the duel emoji bar) | **Done — NOT device-tested** |
| — | Power-Up system | Done (see #63) |
| 64 | **Duel tiered scoring + match drama** — duels no longer use the 500–1000 continuous speed curve (made exact ties, and thus sudden death, practically impossible). Duel-only: correct = 100 + speed-tier bonus (fast ≤⅓ timer +50, mid ≤⅔ +25, slow +0), NO streak multiplier — scores land on 25-point steps so equal-skill matches genuinely tie. Solo/Classic/Team scoring untouched (blast-radius rule). **Final Stretch:** last 3 main questions worth 2x (comeback mechanic; announced via banner + persistent tag; never applies to sudden-death extras). Frontend: live score-gap chip under VS banner (▲ AHEAD BY N / ▼ BEHIND / ⚡ TIED), full-screen sudden-death flash + red pulsing timer, speed-tier chip on reveal (⚡ FAST +150 etc. — teaches the new scoring). Server sends `speed_tiers` + `final_stretch` in duel reveal payloads, `final_stretch` on QUESTION. `round_speed_tiers` field on Room | **Done — NOT device-tested** |
| 65 | **Duel rank badges + Classic/Team interstitial + analytics** — (a) VS intro now shows each fighter's trophy tier (ROOKIE→GRANDMASTER, mirrors PF_TIERS; opponent shows 'PRACTICE BOT' for bot duels) for stakes-building. (b) Classic/Team results HOME exit now fires a tap-driven, frequency-capped interstitial (`_maybeShowMultiplayerInterstitial`, every 2nd multiplayer exit via `forge_mp_exit_count`) — the only mode pair that previously had zero interstitial revenue; **skipped if a rewarded ad (Double Winnings / Entry Fee Recovery) already played on that screen** so ads never stack. (c) New analytics: `duel_completed` (outcome/forfeit/sudden_death_rounds/my_score), `sudden_death_reached`, `interstitial_shown`. (d) **Bug fix:** `analytics.js` only defined `track()` but 7 call sites used `Analytics.logEvent(...)` (power-up buy/use, lucky draw, new duel events) — would throw `TypeError` at runtime; added a `logEvent` alias forwarding to `track` | **Done — NOT device-tested** |
| — | OTA/Live updates (Capgo) | Deliberately deferred — see notes above |
| — | Repo migration to `~/forge` | Not started |
| 66 | **Web build gating** — `frontend/web/screens/home.html` now blocks Solo/Create/Join behind a "Get the App" CTA + Play Store link when `ForgePlatform.config.isWebsite` is true. Closes the loophole where any web visitor could play unlimited full games with zero ad/economy gating. Challenge Mode recipients (`challenge.html`, separate screen) are unaffected — still get their one free game as designed | Done |
| 67 | **Force-update blocking overlay** — `app-update.js`'s immediate-update flow previously let players silently continue on the old build if they tapped Android's back button during a priority-4/5 update prompt (Play Core resolves back-button-cancel as a rejected promise, not a hard block). Added a genuine full-screen, non-dismissible overlay (`#force-update-overlay` in `index.html`) shown when a re-check after cancellation confirms the update still isn't installed. Also re-checks on every app `resume`, not just cold boot | Done |
| 68 | **AdMob Mediation — Unity Ads** — Unity Ads adapter (`com.google.ads.mediation:unity:4.18.1.0`) added to `android/app/build.gradle`, two mediation groups (Rewarded, Interstitial) created in AdMob Console, both confirmed "Active" with Unity correctly appearing as a bidding-mode ad source. Verified structurally correct via AdMob's Ads Activity report (Unity row present, 0 wins so far — expected at low volume, not a bug). AppLovin MAX account created, pending their manual app-review approval before it can be added as a second mediation source | Done — Unity live, AppLovin pending approval |
| 69 | **Power-up repricing** — Original prices (25–40 coins) sat *above* the Generation Ticket's 25-coin anchor despite power-ups being single-round, mostly-cosmetic consumables. Repriced below the ticket, scaled by real impact: Time Freeze 10, 50/50 15, Double Points 15, Time Steal (Duel-only) 20 — still costs roughly a full Solo win, avoiding both "too expensive to bother" and "cheap enough to spam" | Done |
| — | **Duel Phase 2 + Lucky Draw + Profile page — now device-tested** | Confirmed working on Internal Testing after fixing a branch/deploy mismatch (see Decisions Log) — Milestones 59–60 upgraded from "Done — NOT device-tested" |

---

## 📱 iOS — Planned, No Mac Required (via Codemagic)

**Status: Planning stage, not started.** Dev has no Mac; will use Codemagic (cloud macOS CI) instead of a local/GitHub Actions build, and a borrowed iPhone (parent's) for Apple ID 2FA + TestFlight testing only — never for building.

### Real requirements (cost + hardware honesty)
- **Apple Developer Program: $99/year, mandatory.** No workaround exists.
- **Codemagic free tier** (500 build min/month) — expected sufficient at current build frequency; reassess if it becomes a bottleneck.
- **A Mac is never touched directly** — Codemagic's cloud macOS runners do all compiling/signing. `npx cap add ios` and `npx cap sync ios` both run fine from the existing WSL/Windows setup, since they only generate/copy project template files, not compile anything.

### Plan, in order
1. **Enroll in Apple Developer Program** (developer.apple.com) — pay $99/yr, use borrowed iPhone for 2FA during account setup.
2. **Add the iOS platform**: `npx cap add ios` + `npx cap sync ios`, run locally from WSL — safe, does not require macOS.
3. **Per-plugin native iOS config** (the part most often underestimated — each plugin needs separate iOS-side setup, distinct from its Android config):
   - `GoogleService-Info.plist` (Firebase iOS equivalent of `google-services.json`)
   - iOS AdMob App ID in `Info.plist`
   - Separate Google Sign-In iOS OAuth client (distinct from the existing Android client ID)
   - `@capawesome/capacitor-app-update` is **Android/Play-Store-only** — needs a conditional no-op guard on iOS (Apple has no equivalent in-app-update API; App Store's own update prompting is OS-level and outside app control)
   - Various `Info.plist` usage-description strings, required by Apple review even for permissions the app doesn't actively use
4. **Codemagic setup**: connect GitHub repo, generate an App Store Connect API key (done entirely via browser, no Mac) so Codemagic can auto-manage signing certificates without manual cert/profile handling.
5. **First build → TestFlight**: Codemagic builds + signs + uploads to TestFlight automatically; install TestFlight on the borrowed iPhone to verify a real build.
6. **App Store submission**: once TestFlight testing passes, submit via App Store Connect for review.

### Explicitly not decided yet
- Whether iOS ships with full feature parity on day one, or a reduced scope (e.g., AdMob mediation partners may have separate iOS SDK integration work not yet scoped) — decide once Phase 3-4 above are underway and the real plugin-by-plugin iOS gap list is known.
- Pricing/monetization parity — Apple's 30% IAP cut (if ever adding IAP) vs Android's Play Billing terms differ; not relevant yet since Forge has no IAP, only AdMob, but worth remembering if that changes.

---

## Decisions Log & Known Issues (appended this session)

- **Duel Phase 2 shipped ahead of Phase 1 stabilizing (July 2026, deliberate):** User chose to build Sync 1v1 Duel now (credits expiring). Key architecture: per-instance in-memory matchmaking queue (`duels.py` — same trust model as rooms, fine at max-instances 3 scale), matchmaking WS hands off to the normal room WS, all duel state on the Room model, client-driven `retry_match` polling (no server timers). Anti-abuse: same-IP matches blocked (basic guard only — two devices on different networks can still farm; revisit if real abuse appears). Bot fallback is explicitly unranked: no entry fee, no trophies, 5-coin win consolation — so trophies stay a pure human-vs-human signal.
- **Lucky Draw prize roll is server-side by design:** the client never picks or claims a prize — `/lucky-draw/spin` rolls, applies, and returns `segment_index`; the wheel animation just lands there. Prize is committed before the animation starts, so a mid-spin app kill can't lose it. Daily gate + respin gate are date fields inside the backend profile store (same pattern as ticket daily counters). Ad respin is tap-driven per the standing ad rule.
- **⚠️ Milestones 58–60: backend integration-tested locally, NO device testing yet** — full local backend tests passed (Lucky Draw gates + prize distribution, duel matchmaking rules incl. same-IP block and coin check, bot duel end-to-end, human duel end-to-end with verified coin/trophy deltas). Frontend screens (duel.html, lucky-draw.html, results duel branch) have NOT been run in a browser or on device. MUST be tested on a real device via USB before any release, per standing rule. Three bugs were found and fixed during local testing: missing httpx dep in venv (dev-only), duel queue router had to register before the generic room WS route, and duels could offer 'General Knowledge' (0 questions in bank) — now filtered via bank_topics_with_questions(13).

- **Duel same-IP test bypass (July 2026):** `DUEL_ALLOW_SAME_IP=1` env var in `duels.py` skips the same-IP matchmaking guard so two devices on one home network can duel each other during testing. **MUST stay unset in production** — leaving it on re-opens the self-farm coin exploit the guard exists for. Also this session: duel-exit interstitial on results HOME tap, Lucky Draw ad-respin moved from once/day to 1hr cooldown (`last_lucky_respin_at` timestamp replaces `lucky_respin_used_date` — economy change, wants Internal Testing), duel Q10 freeze fixed (blocking Supabase streak call + `isQuickPickTopic` ReferenceError), topic-spin race fixed, DUEL_PLAYER_ANSWERED "LOCKED IN" cue + live VS score banner added.
- **Ad-flow race condition (July 2026):** A background 5-second `setTimeout` check running independently of user taps caused two ad systems to fire near-simultaneously — watching a 2X Coins ad could grant a ticket reward instead. Root-caused and fixed by removing all background ad timers entirely; every ad-related action is now triggered directly by a tap, making the collision structurally impossible rather than just less likely. **Lesson: any ad/reward flow with real economic stakes should be tap-driven only — background timers checking "should an ad fire now" independent of user action are a recurring source of this exact class of bug.**
- **RewardedInterstitial underperformed with real users:** Built correctly, plugin methods verified, worked technically — but real analytics showed players didn't understand/engage with the auto-show format, and tickets were already abundant via other sources. Swapped to plain Interstitial for the Custom Topic decline flow. Code kept intact and dormant rather than deleted, in case a higher-value reward makes it worth reviving later. **Lesson: a format performing well in AdMob's own marketing material doesn't guarantee it fits a specific app's specific reward economy — verify against real usage before assuming a "better" format is actually better for you.**
- **Auth-staleness error messages were being silently discarded (round 2):** `syncProfile`, `syncTickets`, `grantDailyRewardTickets`, `grantBonusGeneration` all threw hardcoded generic strings instead of the real backend error text, breaking `_isAuthError()`'s string-matching for those specific calls. Fixed by making all `API.*` methods surface `await r.text()`. **Lesson: when building error-detection logic that pattern-matches on error message content, audit every call site that could produce that error — a single swallowed/generic message anywhere in the chain silently breaks detection for that path only, which is easy to miss since other paths keep working fine.**
- **India eCPM is structurally low, confirmed via real data + industry benchmarks:** Observed ~$0.92 eCPM against a mostly-India user base is normal and expected — India (along with Brazil, Philippines, Indonesia) sits consistently multiple times lower than US/UK/Australia/South Korea across every ad format. Not a technical misconfiguration. Low show rate (~22%) is explained by the preload-everywhere architecture (every ad format preloads proactively; most sessions don't hit every trigger condition) and is unrelated to eCPM — a request that never becomes an impression simply doesn't enter the eCPM calculation.
- **eCPM optimization is low-leverage at current scale:** Revenue ≈ users × sessions × ads-watched × eCPM. With near-zero real users, the eCPM term is the smallest lever available — doubling it moves absolute revenue by cents. Growth/distribution is the actual current bottleneck, not ad tuning or mediation (mediation itself was evaluated and deferred for the same reason — needs real traffic volume to pay off at all).
- **Marketing channel mismatch identified:** LinkedIn (professional audience, not gamers), static Instagram posts (algorithmically suppressed without existing engagement), Discord indie-dev groups (developers, not target players) all yielded near-zero conversion — not a signal the app itself is unappealing. Reframed toward channels with actual audience overlap: short gameplay clips over announcement posts, direct WhatsApp/Telegram sharing into existing social graphs (likely highest-leverage given current network), and free Play Store ASO.
- **In-App Update bootstrapping gap:** The Play Core update-checking code can only detect/prompt updates on devices where it's already running — meaning the very first release that ships this feature cannot force-update anyone, since no prior build has the listener. Must wait for version-distribution data to confirm broad adoption of a build containing this feature before ever using priority 4–5 for real on a future release.
- **In-App Update was not actually blocking (found + fixed):** the original `performImmediateUpdate()` call treated a player tapping Android's back button as just a caught exception, logged and ignored — nothing stopped them from continuing to use the old build. Google's Play Core immediate-update flow only *requests* the block; the app is responsible for verifying it actually completed and enforcing a real stop otherwise. Fixed with a re-check-after-cancel + genuine non-dismissible full-screen overlay, also re-checked on every `resume`, not just cold boot. **Lesson: any "blocking" native flow (update, permission, paywall) needs the app to verify the outcome, not just fire the request and assume compliance.**
- **Localhost-tested backend features shipped to Internal Testing without a real deploy (found + fixed):** Duel Phase 2 and Lucky Draw were built and tested entirely against a local `uvicorn` backend on a feature branch, then a signed `.aab` was built from that same branch and uploaded to Internal Testing. Since local testing only proves the code is correct — never that it reached the actual Cloud Run service — the deployed app was calling backend routes (`/ws/duel/queue`, `/lucky-draw/*`) that didn't exist yet in production. Fixed by merging to `main` (which correctly triggered the GitHub Actions backend deploy) and rebuilding the `.aab` from `main` afterward. **Lesson, same shape as the earlier Challenge Mode branch/deploy mismatch this session: always confirm a backend-touching feature has an actual green production deploy before building and shipping the native app that depends on it — "works on localhost" and "works in the shipped app" are proving two completely different things.**
- **Power-up pricing was anchored wrong:** original prices (25-40 coins) sat above the Generation Ticket's 25-coin reference price despite being single-round consumable effects with far less lasting value than a full AI-generated quiz. Repriced below the ticket, scaled by real in-game impact rather than round numbers. **Lesson: every new priced item needs to be checked against the existing economy's anchor price(s), not priced in isolation.**
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