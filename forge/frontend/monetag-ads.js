/**
 * monetag-ads.js — Forge Ad Lifecycle Controller
 *
 * Ad cycle per quiz loop:
 *   1. LOBBY   → 1× Vignette  (fires immediately when lobby screen loads)
 *   2. RESULTS → 1× Popunder  (fires on user's first click after results load)
 *
 * GAME: hard block — zero ads, window.open patched closed.
 *
 * Cycle reset:
 *   - "Play Again" → back to Lobby → Vignette fires again (step 1)
 *   - "Go Home"    → back to Home  → next Lobby visit fires Vignette (step 1)
 *
 * USAGE — one call per screen hook, nothing else needed:
 *   AdOps.onHome()      inside onHomeShow()
 *   AdOps.onLobby()     inside onLobbyShow()
 *   AdOps.onGame()      inside onGameShow()
 *   AdOps.onResults()   inside onResultsShow()
 *   AdOps.onPlayAgain() when Play Again tapped
 *   AdOps.onGoHome()    when Go Home tapped
 */

(function (win) {
  "use strict";

  // ── Zone config — update if Monetag gives you new URLs ─────────────────────
  var VIGNETTE = { src: "https://n6wxm.com/vignette.min.js",  zone: "11087559" };
  var POPUNDER = { src: "https://al5sm.com/tag.min.js",        zone: "11087153" };

  // ── Internal state ──────────────────────────────────────────────────────────
  var _vigFired = false;   // vignette shown this cycle
  var _puFired  = false;   // popunder registered this cycle
  var _inGame   = false;   // true while game screen is active

  var _origOpen = null;    // saved window.open reference
  var _openPatched = false;

  // ── Core helpers ────────────────────────────────────────────────────────────

  /**
   * Inject a Monetag script tag with the required data-zone attribute.
   * This is the ONLY correct way — without data-zone the script loads
   * but Monetag doesn't know which zone to serve.
   */
  function _inject(cfg) {
    try {
      var doc = win.document;
      // Don't double-inject
      if (doc.querySelector('script[data-zone="' + cfg.zone + '"]')) return;
      var s = doc.createElement("script");
      s.src = cfg.src;
      s.setAttribute("data-zone", cfg.zone);
      s.async = true;
      (doc.body || doc.documentElement).appendChild(s);
    } catch (e) {}
  }

  /** Remove all script tags for a given zone */
  function _remove(cfg) {
    try {
      var tags = win.document.querySelectorAll('script[data-zone="' + cfg.zone + '"]');
      for (var i = 0; i < tags.length; i++) {
        if (tags[i].parentNode) tags[i].parentNode.removeChild(tags[i]);
      }
    } catch (e) {}
  }

  /** Patch window.open to a no-op (used during gameplay) */
  function _blockOpen() {
    if (_openPatched) return;
    try {
      _origOpen = win.open.bind(win);
      win.open = function (url) {
        // Always pass through mailto/tel; block everything else
        var u = String(url || "");
        if (u.indexOf("mailto:") === 0 || u.indexOf("tel:") === 0) {
          return _origOpen.apply(win, arguments);
        }
        return null;
      };
      _openPatched = true;
    } catch (e) {}
  }

  /** Restore original window.open */
  function _unblockOpen() {
    if (!_openPatched) return;
    try { win.open = _origOpen; } catch (e) {}
    _openPatched = false;
  }

  /** Full cycle reset */
  function _reset() {
    _vigFired = false;
    _puFired  = false;
    _inGame   = false;
    _remove(VIGNETTE);
    _remove(POPUNDER);
    _unblockOpen();
  }

  // ── Public API ───────────────────────────────────────────────────────────────

  win.AdOps = {

    /** Home screen loaded — just clean up, no ad here */
    onHome: function () {
      _inGame = false;
      _unblockOpen();
      _remove(POPUNDER); // clean any stray popunder tag from results
    },

    /**
     * Lobby screen loaded — fire vignette once per cycle.
     * Called from onLobbyShow(). Works for both fresh games and Play Again.
     */
    onLobby: function () {
      _inGame = false;
      _unblockOpen();
      if (_vigFired) return;
      _vigFired = true;
      _inject(VIGNETTE);
    },

    /**
     * Game screen loaded — hard block all ads.
     * Removes any scripts that somehow got in, patches window.open shut.
     */
    onGame: function () {
      _inGame = true;
      _remove(VIGNETTE);
      _remove(POPUNDER);
      _blockOpen();
    },

    /**
     * Results screen loaded — register popunder once per cycle.
     * The popunder fires on the player's first click (Play Again / Go Home).
     * We restore window.open here so that click can actually open the tab.
     */
    onResults: function () {
      _inGame = false;
      _unblockOpen(); // MUST come before inject so window.open works
      if (_puFired) return;
      _puFired = true;
      _inject(POPUNDER);
    },

    /**
     * "Play Again" tapped.
     * User goes Lobby → (skipping Home) so:
     *   - Reset vignette flag so lobby vignette fires again
     *   - Reset popunder flag so results popunder fires again
     *   - Remove old scripts
     */
    onPlayAgain: function () {
      _vigFired = false;
      _puFired  = false;
      _inGame   = false;
      _remove(VIGNETTE);
      _remove(POPUNDER);
      _unblockOpen();
    },

    /**
     * "Go Home" tapped — full reset.
     * Next lobby visit will fire vignette fresh.
     */
    onGoHome: function () {
      _reset();
    },
  };

})(typeof window !== "undefined" ? window : globalThis);