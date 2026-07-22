/**
 * analytics.js — Firebase Analytics wrapper for Forge
 *
 * WHY FIREBASE OVER POSTHOG:
 *   Linked to AdMob (via AdMob Settings → Linked services), Firebase
 *   correlates ad revenue directly with retention/engagement data in one
 *   dashboard — which PostHog has no visibility into at all. Given
 *   monetization is a core goal, this beats a general-purpose analytics
 *   tool for Forge specifically.
 *
 * ⚠️ VERIFY BEFORE RELYING ON THIS:
 *   Method names below match @capacitor-firebase/analytics's documented
 *   API as of writing, but confirm against the actual installed version
 *   before trusting screen-tracking calls in production:
 *   node_modules/@capacitor-firebase/analytics/dist/esm/definitions.d.ts
 */

const Analytics = {
  _ready: false,

  get _plugin() {
    return window.Capacitor?.Plugins?.FirebaseAnalytics || null;
  },

  async init() {
    if (this._ready) return;
    const plugin = this._plugin;
    if (!plugin || !window.Capacitor?.isNativePlatform?.()) return;
    try {
      await plugin.setEnabled({ enabled: true });
      this._ready = true;
    } catch (e) {
      console.warn('[Analytics] init failed:', e);
    }
  },

  /** Log a named event with optional params. */
  async track(eventName, params = {}) {
    const plugin = this._plugin;
    if (!plugin || !this._ready) return;
    try {
      await plugin.logEvent({ name: eventName, params });
    } catch (e) {
      console.warn('[Analytics] track failed:', eventName, e);
    }
  },

  /** Alias for track() — several screens call logEvent; keep both valid. */
  async logEvent(eventName, params = {}) {
    return this.track(eventName, params);
  },

  /** Tag events with the signed-in Google account. */
  async identify(userId) {
    const plugin = this._plugin;
    if (!plugin || !this._ready || !userId) return;
    try {
      await plugin.setUserId({ userId });
    } catch (e) {
      console.warn('[Analytics] identify failed:', e);
    }
  },

  /** Call on sign-out so subsequent events aren't misattributed. */
  async reset() {
    const plugin = this._plugin;
    if (!plugin || !this._ready) return;
    try {
      await plugin.setUserId({ userId: null });
    } catch (e) {
      console.warn('[Analytics] reset failed:', e);
    }
  },

  /** Log a screen view — call this from the router. */
  async screen(screenName) {
    const plugin = this._plugin;
    if (!plugin || !this._ready) return;
    try {
      await plugin.setCurrentScreen({ screenName });
    } catch (e) {
      console.warn('[Analytics] screen failed:', e);
    }
  },
};

window.Analytics = Analytics;