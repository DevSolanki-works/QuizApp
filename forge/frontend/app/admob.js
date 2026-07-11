/**
 * admob.js — Rewarded Ad wrapper for Forge
 *
 * WHY A WRAPPER:
 *   Every rewarded-ad trigger (Entry Fee Recovery, Daily Lucky Draw, Streak
 *   Saver, Double Winnings) needs the same load → show → reward-or-fail
 *   flow. Centralising it here means each trigger site only calls
 *   RewardedAd.show() and handles the boolean result.
 *
 *   Only rewarded ads are ever used in the app (see CLAUDE.md — Ads System).
 *   No banners, no interstitials.
 *
 * ⚠️ VERIFY BEFORE RELYING ON THIS:
 *   Event name strings and method names below match this plugin's stable
 *   history, but Capacitor community plugins do shift method/event names
 *   across majors. After `npm install`, open
 *   node_modules/@capacitor-community/admob/dist/esm/definitions.d.ts
 *   and confirm prepareRewardVideoAd / showRewardVideoAd and the
 *   RewardAdPluginEvents string values match what's used here before
 *   trusting this in production.
 */

const RewardedAd = {
  _initialized: false,
  _loaded: false,
  _loading: false,

  // Google's official Android test ad unit ID for rewarded ads.
  // Swap PROD_AD_UNIT_ID in once you create a real ad unit in AdMob.
  // Never ship IS_TESTING as true.
  TEST_AD_UNIT_ID: 'ca-app-pub-3940256099942544/5224354917',
  PROD_AD_UNIT_ID: 'ca-app-pub-4922314688440658/3665918421',

  IS_TESTING: false,

  get _adUnitId() {
    return this.IS_TESTING ? this.TEST_AD_UNIT_ID : this.PROD_AD_UNIT_ID;
  },

  get _plugin() {
    return window.Capacitor?.Plugins?.AdMob || null;
  },

  /** Call once at boot (native app only). Safe to call multiple times. */
  async init() {
    if (this._initialized) return;
    const plugin = this._plugin;
    if (!plugin || !window.Capacitor?.isNativePlatform?.()) return;

    try {
      await plugin.initialize({ initializeForTesting: this.IS_TESTING });
      this._initialized = true;
      this._preload();
    } catch (e) {
      console.warn('[AdMob] Initialize failed:', e);
    }
  },

  async _preload() {
    const plugin = this._plugin;
    if (!plugin || this._loading || this._loaded) return;
    this._loading = true;
    try {
      await plugin.prepareRewardVideoAd({
        adId: this._adUnitId,
        isTesting: this.IS_TESTING,
      });
      this._loaded = true;
    } catch (e) {
      console.warn('[AdMob] Preload failed:', e);
      this._loaded = false;
    } finally {
      this._loading = false;
    }
  },

  /**
   * Show a rewarded ad and wait for the outcome.
   * Resolves true only if the user watched to completion and earned
   * the reward. Resolves false on skip, failure, or on web/no-plugin.
   */
  async show() {
    const plugin = this._plugin;
    if (!plugin || !window.Capacitor?.isNativePlatform?.()) {
      console.warn('[AdMob] No plugin available (web build or plugin missing) — ad flow stubbed out, no real ad traffic generated');
      if (typeof Toast !== 'undefined') Toast.info('Ads only run on a real device build — this is stubbed out on localhost.');
      return false;
    }

    await this.init();
    if (!this._loaded) await this._preload();
    if (!this._loaded) {
      if (typeof Toast !== 'undefined') Toast.error('Ad not ready yet — try again in a moment.');
      return false;
    }

    return new Promise(async (resolve) => {
      let rewarded = false;
      let rewardedHandle, dismissedHandle, failHandle;

      const cleanup = async () => {
        await rewardedHandle?.remove();
        await dismissedHandle?.remove();
        await failHandle?.remove();
        this._loaded = false;
        this._preload();
      };

      rewardedHandle  = await plugin.addListener('onRewardedVideoAdReward', () => { rewarded = true; });
      dismissedHandle = await plugin.addListener('onRewardedVideoAdDismissed', async () => {
        await cleanup();
        resolve(rewarded);
      });
      failHandle = await plugin.addListener('onRewardedVideoAdFailedToShow', async () => {
        await cleanup();
        resolve(false);
      });

      try {
        await plugin.showRewardVideoAd();
      } catch (e) {
        console.warn('[AdMob] Show failed:', e);
        await cleanup();
        resolve(false);
      }
    });
  },
};

window.RewardedAd = RewardedAd;

/**
 * Interstitial — plain, non-rewarded, no reward disclosure needed.
 * Used as the Quick Pick "every 2nd game" placement and as the fallback
 * floor when a player consistently skips the Custom Topic Rewarded
 * Interstitial.
 */
const Interstitial = {
  _loaded: false,
  _loading: false,
  TEST_AD_UNIT_ID: 'ca-app-pub-3940256099942544/1033173712',
  PROD_AD_UNIT_ID: 'ca-app-pub-4922314688440658/3840946730',
  IS_TESTING: false,

  get _adUnitId() {
    return this.IS_TESTING ? this.TEST_AD_UNIT_ID : this.PROD_AD_UNIT_ID;
  },
  get _plugin() {
    return window.Capacitor?.Plugins?.AdMob || null;
  },

  async _preload() {
    const plugin = this._plugin;
    if (!plugin || this._loading || this._loaded) return;
    this._loading = true;
    try {
      await plugin.prepareInterstitial({ adId: this._adUnitId, isTesting: this.IS_TESTING });
      this._loaded = true;
    } catch (e) {
      console.warn('[Interstitial] Preload failed:', e);
      this._loaded = false;
    } finally {
      this._loading = false;
    }
  },

  async show() {
    const plugin = this._plugin;
    if (!plugin || !window.Capacitor?.isNativePlatform?.()) return false;
    if (!this._loaded) await this._preload();
    if (!this._loaded) return false;
    try {
      await plugin.showInterstitial();
      this._loaded = false;
      this._preload();
      return true;
    } catch (e) {
      console.warn('[Interstitial] Show failed:', e);
      this._loaded = false;
      this._preload();
      return false;
    }
  },
};
window.Interstitial = Interstitial;

/**
 * RewardedInterstitial — auto-shows (no opt-in tap) at natural transitions,
 * still pays out a reward on completion. Used for the Custom Topic "watch
 * to get +1 free generation" flow. Google's own reward-ad policies still
 * require the reward be disclosed BEFORE the ad plays even though there's
 * no tap-to-opt-in step — callers of show() are responsible for surfacing
 * that disclosure themselves before calling this.
 */
const RewardedInterstitial = {
  _initialized: false,
  _loaded: false,
  _loading: false,

  // Google's official Android test ad unit ID for rewarded interstitials.
  TEST_AD_UNIT_ID: 'ca-app-pub-3940256099942544/5354046379',
  PROD_AD_UNIT_ID: 'ca-app-pub-4922314688440658/2971130886',

  IS_TESTING: false,

  get _adUnitId() {
    return this.IS_TESTING ? this.TEST_AD_UNIT_ID : this.PROD_AD_UNIT_ID;
  },

  get _plugin() {
    return window.Capacitor?.Plugins?.AdMob || null;
  },

  async init() {
    if (this._initialized) return;
    const plugin = this._plugin;
    if (!plugin || !window.Capacitor?.isNativePlatform?.()) return;
    this._initialized = true;
    this._preload();
  },

  async _preload() {
    const plugin = this._plugin;
    if (!plugin || this._loading || this._loaded) return;
    this._loading = true;
    try {
      await plugin.prepareRewardInterstitialAd({
        adId: this._adUnitId,
        isTesting: this.IS_TESTING,
      });
      this._loaded = true;
    } catch (e) {
      console.warn('[RewardedInterstitial] Preload failed:', e);
      this._loaded = false;
    } finally {
      this._loading = false;
    }
  },

  /**
   * Show the rewarded interstitial. Resolves true only if the reward
   * event fired before dismissal. Resolves false on skip/fail/web.
   */
  async show() {
    const plugin = this._plugin;
    if (!plugin || !window.Capacitor?.isNativePlatform?.()) {
      console.warn('[RewardedInterstitial] No plugin available (web build) — stubbed out');
      return false;
    }

    await this.init();
    if (!this._loaded) await this._preload();
    if (!this._loaded) {
      console.warn('[RewardedInterstitial] Not ready — skipping this trigger silently');
      return false;
    }

    return new Promise(async (resolve) => {
      let rewarded = false;
      let rewardedHandle, dismissedHandle, failHandle;

      const cleanup = async () => {
        await rewardedHandle?.remove();
        await dismissedHandle?.remove();
        await failHandle?.remove();
        this._loaded = false;
        this._preload();
      };

      rewardedHandle  = await plugin.addListener('onRewardedInterstitialAdReward', () => { rewarded = true; });
      dismissedHandle = await plugin.addListener('onRewardedInterstitialAdDismissed', async () => {
        await cleanup();
        resolve(rewarded);
      });
      failHandle = await plugin.addListener('onRewardedInterstitialAdFailedToShow', async () => {
        await cleanup();
        resolve(false);
      });

      try {
        await plugin.showRewardInterstitialAd();
      } catch (e) {
        console.warn('[RewardedInterstitial] Show failed:', e);
        await cleanup();
        resolve(false);
      }
    });
  },
};

window.RewardedInterstitial = RewardedInterstitial;