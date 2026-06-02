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
    HOME_VIGNETTE: 1 << 0,
    LOBBY_VIGNETTE: 1 << 1,
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
    this._currentScreen = "unknown";

    // Lobby vignette is only allowed when explicitly armed from a Home CTA
    this._lobbyVignetteArmed = false;
    this._resultsPopunderInjected = false;

    // Gameplay hard guard (block any late vignette/popunder injections)
    this._gameplayObserver = null;

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

    // Popunder kill-switch: stop infinite window.open storms after first popunder.
    this._origWindowOpen = null;
    this._openGate = null; // { remaining:number, expiresAt:number }
  }

  MonetagAdOps.prototype.init = function init() {
    if (this._initialized) return;
    this._initialized = true;

    // Capture original window.open once (best-effort)
    try {
      if (typeof globalObj.open === "function") this._origWindowOpen = globalObj.open.bind(globalObj);
    } catch (_) {}

    this._startBannerDefense();
    this._scrubBannersNow();
    this._log("init()");
  };

  MonetagAdOps.prototype.onLobbyEnter = function onLobbyEnter() {
    this._ensureInit();
    this._currentScreen = "lobby";
    if (this._locked) {
      this._phase = Phase.LOCKDOWN;
      return;
    }
    this._phase = Phase.LOBBY;
    this._scrubBannersNow();
    this._disableOpenGate(); // never allow popunder outside results
    if (this._lobbyVignetteArmed) {
      this._lobbyVignetteArmed = false;
      // Fire immediately on lobby enter so it cannot attach to the user's
      // first gameplay click (e.g. pressing START).
      this._fireVignetteOnce(Fired.LOBBY_VIGNETTE);
    }
  };

  // Call from Home CTAs (Solo / Create / Join) right before navigating to lobby.
  MonetagAdOps.prototype.armLobbyVignette = function armLobbyVignette() {
    this._ensureInit();
    if (this._locked) return;
    this._lobbyVignetteArmed = true;
  };

  MonetagAdOps.prototype.onHomeEnter = function onHomeEnter() {
    this._ensureInit();
    this._currentScreen = "home";
    if (this._locked) {
      this._phase = Phase.LOCKDOWN;
      return;
    }
    this._scrubBannersNow();
    this._disableOpenGate();
    // Home vignette is intentionally NOT fired here.
    // It is fired deterministically inside the Home CTA click (Solo/Create/Join)
    // so it cannot "spill" into gameplay.
  };

  MonetagAdOps.prototype.onGameStart = function onGameStart() {
    this._ensureInit();
    this._currentScreen = "game";
    // Absolutely ad-free gameplay.
    this._disableOpenGate();
    this._phase = Phase.GAMEPLAY;
    this._scrubBannersNow();
    this._startGameplayGuard();
  };

  MonetagAdOps.prototype.onGameEnd = function onGameEnd() {
    this._ensureInit();
    this._currentScreen = "results";
    if (this._locked) {
      this._phase = Phase.LOCKDOWN;
      return;
    }
    this._phase = Phase.RESULTS;
    this._scrubBannersNow();
    // Results: ONE popunder only (no vignette here).
    this._fireResultsPopunderOnce();

    this._lockdown();
  };

  // Call on every navigation so popunder cannot leak out of results.
  MonetagAdOps.prototype.onNavigate = function onNavigate(screenName) {
    this._ensureInit();
    this._currentScreen = String(screenName || "unknown");
    if (this._currentScreen !== "results") {
      this._disableOpenGate();
      // Remove any lingering popunder tag when leaving results
      removeAllScriptsWhere(function (s) {
        return matchesZoneScript(s, ZONES.POPUNDER.zone, ZONES.POPUNDER.src);
      });
      this._resultsPopunderInjected = false;
    }
    if (this._currentScreen !== "game") this._stopGameplayGuard();
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
        homeVignette: this._hasFired(Fired.HOME_VIGNETTE),
        lobbyVignette: this._hasFired(Fired.LOBBY_VIGNETTE),
        resultsPopunder: this._hasFired(Fired.RESULTS_POPUNDER),
      },
    });
  };

  MonetagAdOps.prototype.destroy = function destroy() {
    this._stopBannerDefense();
    this._removeInjectedScripts();
    this._disableOpenGate();
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
    // IMPORTANT: do NOT scrub popunder tags here; the popunder needs to remain
    // registered until the user's first click on the results screen.
  };

  MonetagAdOps.prototype._unlockAndResetBudget = function _unlockAndResetBudget() {
    this._locked = false;
    this._phase = Phase.IDLE;
    this._firedMask = 0;
    this._removeInjectedScripts();
    this._disableOpenGate();
    this._lobbyVignetteArmed = false;
    this._resultsPopunderInjected = false;
    this._stopGameplayGuard();
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

  MonetagAdOps.prototype._enableOpenGate = function _enableOpenGate(maxOpens, ttlMs) {
    // Allows exactly `maxOpens` calls to window.open until expiry; then blocks all further opens.
    // This prevents Monetag popunder from re-triggering on every click/navigation.
    try {
      if (!this._origWindowOpen) return;
      var remaining = typeof maxOpens === "number" ? maxOpens : 1;
      var expiresAt = nowMs() + (typeof ttlMs === "number" ? ttlMs : 600000); // default 10 min
      this._openGate = { remaining: remaining, expiresAt: expiresAt };

      var self = this;
      globalObj.open = function gatedWindowOpen(url, name, specs) {
        try {
          var u = url == null ? "" : String(url);
          // Allow app-safe schemes
          if (u.indexOf("mailto:") === 0 || u.indexOf("tel:") === 0) {
            return self._origWindowOpen(url, name, specs);
          }
          // Popunder is ONLY allowed while on results screen.
          if (self._currentScreen !== "results") return null;
          if (!self._openGate) return null;
          if (nowMs() > self._openGate.expiresAt) return null;
          if (self._openGate.remaining <= 0) return null;
          self._openGate.remaining -= 1;
          return self._origWindowOpen(url, name, specs);
        } catch (_) {
          return null;
        }
      };
    } catch (_) {}
  };

  MonetagAdOps.prototype._disableOpenGate = function _disableOpenGate() {
    try {
      if (this._origWindowOpen) globalObj.open = this._origWindowOpen;
    } catch (_) {}
    this._openGate = null;
  };

  MonetagAdOps.prototype._fireHomeVignette = function _fireHomeVignette() {
    // Vignette each time user returns to Home (debounced)
    if (nowMs() - this._lastHomeVignetteAt < 3000) return;
    this._lastHomeVignetteAt = nowMs();
    this._fireVignetteOnce(Fired.HOME_VIGNETTE);
    // Allow it again on next navigation by clearing the fired bit after a moment.
    var self = this;
    globalObj.setTimeout(function () { self._firedMask &= ~Fired.HOME_VIGNETTE; }, 1000);
  };

  MonetagAdOps.prototype._fireLobbyVignette = function _fireLobbyVignette() {
    if (nowMs() - this._lastLobbyVignetteAt < 3000) return;
    this._lastLobbyVignetteAt = nowMs();
    this._fireVignetteOnce(Fired.LOBBY_VIGNETTE);
    var self = this;
    globalObj.setTimeout(function () { self._firedMask &= ~Fired.LOBBY_VIGNETTE; }, 1000);
  };

  MonetagAdOps.prototype._fireResultsPopunderOnce = function _fireResultsPopunderOnce() {
    var self = this;
    if (this._hasFired(Fired.RESULTS_POPUNDER)) return;
    if (this._resultsPopunderInjected) return;

    // Allow exactly ONE open, and ONLY while on results.
    self._enableOpenGate(1, 5 * 60 * 1000);

    // Inject the popunder tag once. Monetag typically triggers on the next user click.
    try {
      self._appendZoneScript(ZONES.POPUNDER);
      self._markFired(Fired.RESULTS_POPUNDER);
      self._resultsPopunderInjected = true;
      // Do NOT auto-remove quickly; it can prevent the first click-triggered popunder.
      // Cleanup happens when leaving results (via onNavigate()) and on reset.
    } catch (_) {}
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

  MonetagAdOps.prototype._scrubVignetteTags = function _scrubVignetteTags() {
    removeAllScriptsWhere(function (s) {
      return matchesZoneScript(s, ZONES.VIGNETTE.zone, ZONES.VIGNETTE.src);
    });
  };

  MonetagAdOps.prototype._startGameplayGuard = function _startGameplayGuard() {
    var self = this;
    // During gameplay: remove any vignette/popunder tags and block future injections.
    self._scrubVignetteTags();
    self._scrubUnexpectedPopunderTags();
    try {
      if (this._gameplayObserver) this._gameplayObserver.disconnect();
    } catch (_) {}
    this._gameplayObserver = null;

    try {
      var obs = new MutationObserver(function (mutations) {
        for (var mi = 0; mi < mutations.length; mi++) {
          var m = mutations[mi];
          if (!m.addedNodes || !m.addedNodes.length) continue;
          for (var ni = 0; ni < m.addedNodes.length; ni++) {
            var node = m.addedNodes[ni];
            if (!node || node.nodeType !== 1) continue;
            if (isScriptEl(node)) {
              if (matchesZoneScript(node, ZONES.VIGNETTE.zone, ZONES.VIGNETTE.src) ||
                  matchesZoneScript(node, ZONES.POPUNDER.zone, ZONES.POPUNDER.src)) {
                removeNode(node);
              }
            }
          }
        }
      });
      obs.observe(globalObj.document.documentElement || globalObj.document.body, { childList: true, subtree: true });
      this._gameplayObserver = obs;
    } catch (_) {}
  };

  MonetagAdOps.prototype._stopGameplayGuard = function _stopGameplayGuard() {
    try {
      if (this._gameplayObserver) this._gameplayObserver.disconnect();
    } catch (_) {}
    this._gameplayObserver = null;
  };

  // Fired from Home CTA click to guarantee "first vignette on first arrival"
  MonetagAdOps.prototype.maybeShowHomeVignette = function maybeShowHomeVignette() {
    this._ensureInit();
    if (this._locked) return false;
    try {
      var key = "adops.home.vignette.shown.v3";
      var already = globalObj.sessionStorage && globalObj.sessionStorage.getItem(key) === "1";
      if (already) return false;
      globalObj.sessionStorage && globalObj.sessionStorage.setItem(key, "1");
    } catch (_) {
      if (this._hasFired(Fired.HOME_VIGNETTE)) return false;
    }
    this._currentScreen = "home";
    this._phase = Phase.IDLE;
    this._scrubVignetteTags();
    this._fireVignetteOnce(Fired.HOME_VIGNETTE);
    return true;
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

