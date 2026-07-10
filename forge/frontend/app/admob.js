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

  IS_TESTING: true,

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