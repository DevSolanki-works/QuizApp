/* Monetag AdOps — 3-Ad Lifecycle Budget (Forge)
 *
 * Guarantees EXACTLY 3 ad interactions per full game loop:
 *  - Lobby:    1× Vignette
 *  - Gameplay: 0 ads
 *  - Results:  1× Vignette then 1× Popunder
 * After Results, the engine hard-locks and ignores all further calls until a
 * brand-new match is explicitly started via `onPlayAgain()`.
 *
 * Also actively scrubs and blocks Monetag banner/inpage zone 11087172.
 */

(function MonetagAdOpsIIFE(globalObj) {
  "use strict";

  var ZONES = Object.freeze({
    VIGNETTE: { zone: "11087559", src: "https://n6wxm.com/vignette.min.js" },
    POPUNDER: { zone: "11087153", src: "https://al5sm.com/tag.min.js" },
    BANNER_DISABLED: { zone: "11087172", src: "https://nap5k.com/tag.min.js" },
  });

  var Phase = Object.freeze({
    IDLE: "IDLE",
    LOBBY: "LOBBY",
    GAMEPLAY: "GAMEPLAY",
    RESULTS: "RESULTS",
    LOCKDOWN: "LOCKDOWN",
  });

  var Fired = Object.freeze({
    GAME_VIGNETTE: 1 << 0,
    RESULTS_VIGNETTE: 1 << 1,
    RESULTS_POPUNDER: 1 << 2,
  });

  function nowMs() {
    try {
      return globalObj.performance && globalObj.performance.now ? globalObj.performance.now() : Date.now();
    } catch (_) {
      return Date.now();
    }
  }

  function safeLog(enabled) {
    if (!enabled) return function () {};
    return function () {
      try {
        // eslint-disable-next-line no-console
        console.log.apply(console, ["[AdOps]"].concat([].slice.call(arguments)));
      } catch (_) {}
    };
  }

  function removeNode(node) {
    try {
      if (node && node.parentNode) node.parentNode.removeChild(node);
    } catch (_) {}
  }

  function isScriptEl(node) {
    return !!node && node.nodeType === 1 && String(node.tagName).toUpperCase() === "SCRIPT";
  }

  function matchesZoneScript(scriptEl, zone, srcContains) {
    if (!scriptEl) return false;
    var dsZone = "";
    try {
      dsZone = scriptEl.dataset && scriptEl.dataset.zone ? String(scriptEl.dataset.zone) : "";
    } catch (_) {}
    var src = "";
    try {
      src = scriptEl.src ? String(scriptEl.src) : "";
    } catch (_) {}
    if (zone && dsZone === String(zone)) return true;
    if (srcContains && src.indexOf(String(srcContains)) !== -1) return true;
    return false;
  }

  function removeAllScriptsWhere(predicate) {
    try {
      var scripts = globalObj.document.querySelectorAll("script");
      for (var i = 0; i < scripts.length; i++) {
        var s = scripts[i];
        if (predicate(s)) removeNode(s);
      }
    } catch (_) {}
  }

  function nodeContainsBannedBanner(node) {
    if (!node || node.nodeType !== 1) return false;
    if (isScriptEl(node) && matchesZoneScript(node, ZONES.BANNER_DISABLED.zone, ZONES.BANNER_DISABLED.src)) return true;
    try {
      var scripts = node.querySelectorAll ? node.querySelectorAll("script") : [];
      for (var i = 0; i < scripts.length; i++) {
        if (matchesZoneScript(scripts[i], ZONES.BANNER_DISABLED.zone, ZONES.BANNER_DISABLED.src)) return true;
      }
    } catch (_) {}
    return false;
  }

  function MonetagAdOps(opts) {
    opts = opts || {};
    this._debug = !!opts.debug;
    this._log = safeLog(this._debug);

    this._phase = Phase.IDLE;
    this._firedMask = 0;
    this._locked = false;

    this._busy = false;
    this._lastInjectAt = 0;
    this._cooldownMs = typeof opts.injectionCooldownMs === "number" ? opts.injectionCooldownMs : 1500;

    this._injectedScripts = new Set();

    this._bannerObserver = null;
    this._bannerScrubTimer = null;
    this._bannerScrubStopTimer = null;
    this._bannerScrubIntervalMs = typeof opts.bannerScrubIntervalMs === "number" ? opts.bannerScrubIntervalMs : 2000;
    this._bannerScrubDurationMs = typeof opts.bannerScrubDurationMs === "number" ? opts.bannerScrubDurationMs : 20000;

    this._initialized = false;
  }

  MonetagAdOps.prototype.init = function init() {
    if (this._initialized) return;
    this._initialized = true;

    this._startBannerDefense();
    this._scrubBannersNow();
    this._log("init()");
  };

  MonetagAdOps.prototype.onLobbyEnter = function onLobbyEnter() {
    this._ensureInit();
    if (this._locked) {
      this._phase = Phase.LOCKDOWN;
      return;
    }
    this._phase = Phase.LOBBY;
    this._scrubBannersNow();
    // Intentionally does NOT fire any ads.
    // Lobby must stay clean and undisturbed.
  };

  MonetagAdOps.prototype.onGameStart = function onGameStart() {
    this._ensureInit();
    if (this._locked) {
      this._phase = Phase.LOCKDOWN;
      return;
    }
    this._scrubBannersNow();
    // Fire exactly ONE vignette per match on the game screen, then lock to GAMEPLAY.
    // This avoids lobby disruption and reduces "mid-quiz" interference.
    if (!this._hasFired(Fired.GAME_VIGNETTE)) {
      this._phase = Phase.LOBBY; // allow injection (not GAMEPLAY yet)
      this._fireVignetteOnce(Fired.GAME_VIGNETTE);
    }
    this._phase = Phase.GAMEPLAY;
  };

  MonetagAdOps.prototype.onGameEnd = function onGameEnd() {
    this._ensureInit();
    if (this._locked) {
      this._phase = Phase.LOCKDOWN;
      return;
    }
    this._phase = Phase.RESULTS;
    this._scrubBannersNow();
    // Fire results ads atomically (vignette then popunder) so cooldown cannot block #3.
    this._fireResultsPair();

    this._lockdown();
  };

  MonetagAdOps.prototype.onPlayAgain = function onPlayAgain() {
    this._ensureInit();
    this._unlockAndResetBudget();
    this._phase = Phase.LOBBY;
    this._scrubBannersNow();
  };

  MonetagAdOps.prototype.getSnapshot = function getSnapshot() {
    return Object.freeze({
      initialized: this._initialized,
      phase: this._phase,
      locked: this._locked,
      firedMask: this._firedMask,
      fired: {
        gameVignette: this._hasFired(Fired.GAME_VIGNETTE),
        resultsVignette: this._hasFired(Fired.RESULTS_VIGNETTE),
        resultsPopunder: this._hasFired(Fired.RESULTS_POPUNDER),
      },
    });
  };

  MonetagAdOps.prototype.destroy = function destroy() {
    this._stopBannerDefense();
    this._removeInjectedScripts();
    this._initialized = false;
    this._phase = Phase.IDLE;
    this._firedMask = 0;
    this._locked = false;
  };

  MonetagAdOps.prototype._ensureInit = function _ensureInit() {
    if (!this._initialized) this.init();
  };

  MonetagAdOps.prototype._hasFired = function _hasFired(flag) {
    return (this._firedMask & flag) === flag;
  };

  MonetagAdOps.prototype._markFired = function _markFired(flag) {
    this._firedMask |= flag;
  };

  MonetagAdOps.prototype._lockdown = function _lockdown() {
    this._locked = true;
    this._phase = Phase.LOCKDOWN;
    this._scrubBannersNow();
    this._scrubUnexpectedPopunderTags();
  };

  MonetagAdOps.prototype._unlockAndResetBudget = function _unlockAndResetBudget() {
    this._locked = false;
    this._phase = Phase.IDLE;
    this._firedMask = 0;
    this._removeInjectedScripts();
    this._scrubBannersNow();
  };

  MonetagAdOps.prototype._canInject = function _canInject() {
    if (this._locked) return false;
    if (this._phase === Phase.GAMEPLAY) return false;
    if (this._busy) return false;
    var t = nowMs();
    if (t - this._lastInjectAt < this._cooldownMs) return false;
    return true;
  };

  MonetagAdOps.prototype._withInjectLock = function _withInjectLock(fn) {
    if (!this._canInject()) return false;
    this._busy = true;
    this._lastInjectAt = nowMs();
    try {
      fn();
      return true;
    } finally {
      this._busy = false;
    }
  };

  MonetagAdOps.prototype._appendZoneScript = function _appendZoneScript(zoneObj) {
    var doc = globalObj.document;
    var parent = [doc.documentElement, doc.body].filter(Boolean).pop();
    if (!parent) return null;
    var s = doc.createElement("script");
    s.dataset.zone = zoneObj.zone;
    s.src = zoneObj.src;
    parent.appendChild(s);
    this._injectedScripts.add(s);
    return s;
  };

  MonetagAdOps.prototype._scheduleZoneTagCleanup = function _scheduleZoneTagCleanup(zone, delayMs) {
    var self = this;
    globalObj.setTimeout(function () {
      removeAllScriptsWhere(function (s) {
        return matchesZoneScript(s, zone, null);
      });
      self._pruneDeadScriptRefs();
    }, delayMs);
  };

  MonetagAdOps.prototype._pruneDeadScriptRefs = function _pruneDeadScriptRefs() {
    try {
      this._injectedScripts.forEach(function (s) {
        if (!s || !s.parentNode) this._injectedScripts.delete(s);
      }, this);
    } catch (_) {}
  };

  MonetagAdOps.prototype._fireVignetteOnce = function _fireVignetteOnce(flag) {
    var self = this;
    if (this._hasFired(flag)) return;
    this._withInjectLock(function () {
      if (self._locked || self._hasFired(flag)) return;
      if (self._phase === Phase.GAMEPLAY) return;
      self._appendZoneScript(ZONES.VIGNETTE);
      self._markFired(flag);
      self._scheduleZoneTagCleanup(ZONES.VIGNETTE.zone, 15000);
    });
  };

  MonetagAdOps.prototype._firePopunderOnce = function _firePopunderOnce(flag) {
    var self = this;
    if (this._hasFired(flag)) return;
    this._withInjectLock(function () {
      if (self._locked || self._hasFired(flag)) return;
      if (self._phase !== Phase.RESULTS) return;
      self._appendZoneScript(ZONES.POPUNDER);
      self._markFired(flag);
      self._scheduleZoneTagCleanup(ZONES.POPUNDER.zone, 15000);
    });
  };

  MonetagAdOps.prototype._fireResultsPair = function _fireResultsPair() {
    var self = this;
    if (this._hasFired(Fired.RESULTS_VIGNETTE) && this._hasFired(Fired.RESULTS_POPUNDER)) return;
    // Bypass cooldown by doing both injections within a single lock.
    this._withInjectLock(function () {
      if (self._locked) return;
      if (self._phase !== Phase.RESULTS) return;

      if (!self._hasFired(Fired.RESULTS_VIGNETTE)) {
        self._appendZoneScript(ZONES.VIGNETTE);
        self._markFired(Fired.RESULTS_VIGNETTE);
        self._scheduleZoneTagCleanup(ZONES.VIGNETTE.zone, 15000);
      }

      // Allow immediate popunder injection (no cooldown check here).
      if (!self._hasFired(Fired.RESULTS_POPUNDER)) {
        self._appendZoneScript(ZONES.POPUNDER);
        self._markFired(Fired.RESULTS_POPUNDER);
        self._scheduleZoneTagCleanup(ZONES.POPUNDER.zone, 15000);
      }
    });
  };

  MonetagAdOps.prototype._removeInjectedScripts = function _removeInjectedScripts() {
    try {
      this._injectedScripts.forEach(function (s) {
        removeNode(s);
      });
    } catch (_) {}
    try {
      this._injectedScripts.clear();
    } catch (_) {}
  };

  MonetagAdOps.prototype._scrubUnexpectedPopunderTags = function _scrubUnexpectedPopunderTags() {
    if (!this._locked) return;
    removeAllScriptsWhere(function (s) {
      return matchesZoneScript(s, ZONES.POPUNDER.zone, ZONES.POPUNDER.src);
    });
  };

  MonetagAdOps.prototype._scrubBannersNow = function _scrubBannersNow() {
    removeAllScriptsWhere(function (s) {
      return matchesZoneScript(s, ZONES.BANNER_DISABLED.zone, ZONES.BANNER_DISABLED.src);
    });

    // Remove any wrapper nodes that contain the banned banner script.
    try {
      var nodes = globalObj.document.querySelectorAll("body *");
      for (var i = 0; i < nodes.length; i++) {
        var el = nodes[i];
        if (nodeContainsBannedBanner(el)) removeNode(el);
      }
    } catch (_) {}
  };

  MonetagAdOps.prototype._startBannerDefense = function _startBannerDefense() {
    var self = this;

    // 1) MutationObserver: blocks banner zone on insertion.
    try {
      var obs = new MutationObserver(function (mutations) {
        for (var mi = 0; mi < mutations.length; mi++) {
          var m = mutations[mi];
          if (!m.addedNodes || !m.addedNodes.length) continue;
          for (var ni = 0; ni < m.addedNodes.length; ni++) {
            var node = m.addedNodes[ni];
            if (!node || node.nodeType !== 1) continue;
            if (nodeContainsBannedBanner(node)) {
              self._log("Blocked banner injection (11087172)");
              removeNode(node);
              continue;
            }
            if (isScriptEl(node) && matchesZoneScript(node, ZONES.BANNER_DISABLED.zone, ZONES.BANNER_DISABLED.src)) {
              self._log("Blocked banner <script> (11087172)");
              removeNode(node);
            }
          }
        }
      });
      obs.observe(globalObj.document.documentElement || globalObj.document.body, { childList: true, subtree: true });
      this._bannerObserver = obs;
    } catch (_) {}

    // 2) Short interval scrub (covers late-load insertions).
    try {
      this._bannerScrubTimer = globalObj.setInterval(function () {
        self._scrubBannersNow();
      }, this._bannerScrubIntervalMs);
      this._bannerScrubStopTimer = globalObj.setTimeout(function () {
        if (self._bannerScrubTimer) globalObj.clearInterval(self._bannerScrubTimer);
        self._bannerScrubTimer = null;
      }, this._bannerScrubDurationMs);
    } catch (_) {}
  };

  MonetagAdOps.prototype._stopBannerDefense = function _stopBannerDefense() {
    try {
      if (this._bannerObserver) this._bannerObserver.disconnect();
    } catch (_) {}
    this._bannerObserver = null;
    try {
      if (this._bannerScrubTimer) globalObj.clearInterval(this._bannerScrubTimer);
      if (this._bannerScrubStopTimer) globalObj.clearTimeout(this._bannerScrubStopTimer);
    } catch (_) {}
    this._bannerScrubTimer = null;
    this._bannerScrubStopTimer = null;
  };

  // Expose a singleton by default; can be replaced if needed.
  try {
    globalObj.MonetagAdOps = MonetagAdOps;
    if (!globalObj.AdOps) globalObj.AdOps = new MonetagAdOps({ debug: false });
  } catch (_) {}
})(typeof window !== "undefined" ? window : globalThis);

