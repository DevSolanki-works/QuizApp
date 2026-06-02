/**
 * monetag-ads.js — Forge Ad Lifecycle Controller
 *
 * Exactly 3 ad events per quiz cycle, in order:
 *   1. HOME    → 1× Vignette  (fires when leaving Home via any CTA)
 *   2. LOBBY   → 1× Vignette  (fires on Lobby enter)
 *   3. RESULTS → 1× Popunder  (fires on Results enter)
 *
 * After Results, the cycle resets:
 *   - "Play Again" → user lands in Lobby → fires Lobby Vignette (step 2)
 *   - "Go Home"    → user lands in Home  → fires Home Vignette on next CTA (step 1)
 *
 * During GAME: hard block — zero ads, any stray injections are removed.
 *
 * HOW TO USE (from each screen):
 *   AdOps.onHome()    — call inside onHomeShow()
 *   AdOps.onLobby()   — call inside onLobbyShow()
 *   AdOps.onGame()    — call inside onGameShow()
 *   AdOps.onResults() — call inside onResultsShow()
 *   AdOps.onPlayAgain() — call when "Play Again" is tapped (before goTo lobby)
 *
 * That's it. No arms, no maybes, no gates.
 */

(function (win) {
  "use strict";

  // ── Monetag zone configs ────────────────────────────────────────────────────
  var VIGNETTE_SRC = "https://n6wxm.com/vignette.min.js";
  var POPUNDER_SRC = "https://al5sm.com/tag.min.js";

  // ── State machine ───────────────────────────────────────────────────────────
  //  IDLE → HOME → LOBBY → GAME → RESULTS → (reset) → HOME or LOBBY
  var State = { IDLE: 0, HOME: 1, LOBBY: 2, GAME: 3, RESULTS: 4 };
  var _state    = State.IDLE;
  var _vigFired = false;  // home vignette fired this cycle
  var _lbFired  = false;  // lobby vignette fired this cycle
  var _puFired  = false;  // results popunder fired this cycle

  // Track injected script nodes so we can remove them cleanly
  var _injected = [];

  // Save original window.open so we can restore it during GAME
  var _origOpen = win.open ? win.open.bind(win) : null;
  var _openGated = false;

  // ── Helpers ─────────────────────────────────────────────────────────────────

  function _inject(src) {
    try {
      var doc = win.document;
      var s = doc.createElement("script");
      s.src = src;
      (doc.body || doc.documentElement).appendChild(s);
      _injected.push(s);
      return s;
    } catch (e) { return null; }
  }

  function _removeAll(src) {
    // Remove both tracked and any stray scripts matching the src
    try {
      var scripts = win.document.querySelectorAll('script[src*="' + _srcKey(src) + '"]');
      for (var i = 0; i < scripts.length; i++) scripts[i].parentNode && scripts[i].parentNode.removeChild(scripts[i]);
    } catch (e) {}
    _injected = _injected.filter(function (s) { return s && s.parentNode; });
  }

  function _srcKey(src) {
    // Extract the hostname part for robust matching
    try { return new URL(src).hostname; } catch (e) { return src.split("/")[2] || src; }
  }

  function _blockWindowOpen() {
    // During GAME: replace window.open so popunder can't fire on stray clicks
    if (_openGated) return;
    _openGated = true;
    win.open = function guardedOpen(url, name, specs) {
      // Always allow mailto / tel; block everything else during game
      if (url && (String(url).indexOf("mailto:") === 0 || String(url).indexOf("tel:") === 0)) {
        return _origOpen ? _origOpen(url, name, specs) : null;
      }
      return null; // blocked
    };
  }

  function _restoreWindowOpen() {
    if (!_openGated) return;
    _openGated = false;
    try { if (_origOpen) win.open = _origOpen; } catch (e) {}
  }

  function _reset() {
    _vigFired = false;
    _lbFired  = false;
    _puFired  = false;
    _removeAll(VIGNETTE_SRC);
    _removeAll(POPUNDER_SRC);
    _restoreWindowOpen();
  }

  // ── Public API ───────────────────────────────────────────────────────────────

  var AdOps = {

    /**
     * Call inside onHomeShow().
     * Restores window.open and waits — the vignette fires when the user
     * taps a CTA (Solo / Create / Join), NOT immediately on page load.
     */
    onHome: function () {
      _state = State.HOME;
      _restoreWindowOpen();
      _removeAll(POPUNDER_SRC); // clean up any stray popunder from results
    },

    /**
     * Call from inside each Home CTA (Solo / Create / Join) BEFORE navigating.
     * Fires the Home Vignette exactly once per cycle.
     */
    homeCtaTapped: function () {
      if (_state !== State.HOME) return;
      if (_vigFired) return;
      _vigFired = true;
      _inject(VIGNETTE_SRC);
      // Auto-remove the tag after 12 s — it's already registered, keeping it
      // in the DOM any longer risks double-fires on future navigations.
      var src = VIGNETTE_SRC;
      win.setTimeout(function () { _removeAll(src); }, 12000);
    },

    /**
     * Call inside onLobbyShow().
     * Fires the Lobby Vignette exactly once per cycle.
     * Safe to call from both "new game" and "play again" paths.
     */
    onLobby: function () {
      _state = State.LOBBY;
      _restoreWindowOpen();
      if (_lbFired) return; // already fired this cycle (e.g. navigated away & back)
      _lbFired = true;
      _inject(VIGNETTE_SRC);
      var src = VIGNETTE_SRC;
      win.setTimeout(function () { _removeAll(src); }, 12000);
    },

    /**
     * Call inside onGameShow().
     * Blocks ALL ad injections and kills window.open for the entire game.
     */
    onGame: function () {
      _state = State.GAME;
      _removeAll(VIGNETTE_SRC);
      _removeAll(POPUNDER_SRC);
      _blockWindowOpen();
    },

    /**
     * Call inside onResultsShow().
     * Fires the Popunder exactly once, then locks the cycle.
     */
    onResults: function () {
      _state = State.RESULTS;
      _restoreWindowOpen(); // allow window.open for the popunder
      if (_puFired) return;
      _puFired = true;
      _inject(POPUNDER_SRC);
      // Popunder fires on first user click — keep tag alive for 60 s
      var src = POPUNDER_SRC;
      win.setTimeout(function () { _removeAll(src); }, 60000);
    },

    /**
     * Call when "Play Again" is tapped (before navigating to lobby).
     * Resets ONLY the lobby + game + results flags so the cycle continues
     * correctly from Lobby (step 2) — the home vignette is NOT reset since
     * the user didn't go back to Home.
     */
    onPlayAgain: function () {
      // Keep _vigFired = true (home was already shown this cycle)
      _lbFired = false; // allow lobby vignette again
      _puFired = false; // allow popunder again after next game
      _removeAll(VIGNETTE_SRC);
      _removeAll(POPUNDER_SRC);
      _restoreWindowOpen();
      // _state will be set by onLobby() when lobby loads
    },

    /**
     * Call "Go Home" button path (before navigating to home).
     * Full reset — next visit to Home will fire the vignette again on CTA tap.
     */
    onGoHome: function () {
      _reset();
      // _state will be set by onHome() when home loads
    },
  };

  // Expose globally
  try { win.AdOps = AdOps; } catch (e) {}

})(typeof window !== "undefined" ? window : globalThis);