/**
 * app-update.js — In-app update wrapper for Forge
 *
 * Wraps @capawesome/capacitor-app-update (Google Play Core under the hood).
 * Two flows:
 *   - FLEXIBLE: downloads in the background, user keeps playing, small
 *     "restart to apply" prompt appears once ready. Used for normal
 *     polish/content updates.
 *   - IMMEDIATE: full-screen blocking update, app can't proceed until
 *     done. Used only when Play Console's "in-app update priority" for
 *     the release is set to 4 or 5 (Google's own threshold for
 *     "critical" — set this per-release in Play Console, no extra
 *     backend needed).
 *
 * Android only — iOS has no equivalent API, falls back to an App Store
 * link (irrelevant right now since Forge has no iOS target).
 */

const AppUpdate = {
  get _plugin() {
    return window.Capacitor?.Plugins?.AppUpdate || null;
  },

  /**
   * Check for an update and act on it automatically:
   *   - No update available → no-op.
   *   - Update available, priority >= 4 → immediate (blocking) update.
   *   - Update available, priority < 4 → flexible (background) update,
   *     with a small toast prompting restart once it's downloaded.
   */
  async checkAndPrompt() {
    const plugin = this._plugin;
    if (!plugin || !window.Capacitor?.isNativePlatform?.()) return;

    let info;
    try {
      info = await plugin.getAppUpdateInfo();
    } catch (e) {
      console.warn('[AppUpdate] Check failed:', e);
      return;
    }

    // updateAvailability: 1 = unknown, 2 = update available, 3 = not available
    if (info.updateAvailability !== 2) return;

    const isCritical = (info.updatePriority || 5) >= 4;

    if (isCritical && info.immediateUpdateAllowed) {
      try {
        await plugin.performImmediateUpdate();
      } catch (e) {
        console.warn('[AppUpdate] Immediate update failed/cancelled:', e);
      }
      return;
    }

    if (info.flexibleUpdateAllowed) {
      try {
        await plugin.startFlexibleUpdate();
        const listener = await plugin.addListener('onFlexibleUpdateStateChange', async (state) => {
          // installStatus: 11 = downloaded, ready to apply
          if (state.installStatus === 11) {
            if (typeof Toast !== 'undefined') {
              Toast.info('Update downloaded — tap to restart and apply it.', 6000);
            }
            await listener.remove();
          }
        });
      } catch (e) {
        console.warn('[AppUpdate] Flexible update failed:', e);
      }
    }
  },

  /** Call this from wherever the "restart to apply" prompt is tapped. */
  async completeFlexibleUpdate() {
    const plugin = this._plugin;
    if (!plugin) return;
    try {
      await plugin.completeFlexibleUpdate();
    } catch (e) {
      console.warn('[AppUpdate] Completing flexible update failed:', e);
    }
  },
};

window.AppUpdate = AppUpdate;