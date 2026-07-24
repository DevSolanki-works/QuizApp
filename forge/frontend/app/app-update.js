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
    // Play Core (and this plugin) is Android/Play-Store-only — there is no
    // iOS equivalent API. App Store's own update prompting is entirely
    // OS-level and outside app control, so this must no-op cleanly on iOS
    // rather than attempt a call the native plugin can't fulfill there.
    if (window.Capacitor?.getPlatform?.() === 'ios') return;
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
        // Completing an immediate update restarts the app automatically —
        // if we're still executing past this line, treat it as cancelled.
      } catch (e) {
        console.warn('[AppUpdate] Immediate update cancelled or failed:', e);
      }
      // Re-check: if the update still isn't installed, block the app
      // instead of silently letting the player continue on the old build.
      let recheck;
      try {
        recheck = await plugin.getAppUpdateInfo();
      } catch (_) {
        recheck = null;
      }
      if (recheck?.updateAvailability === 2) {
        this._showBlockingOverlay();
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

  /**
   * Full-screen, non-dismissible block shown when a priority 4/5 update
   * was cancelled by the player (back button) instead of completed.
   * Genuinely blocks play — no close button, no background-click dismiss.
   */
  _showBlockingOverlay() {
    const el = document.getElementById('force-update-overlay');
    if (el) el.style.display = 'flex';
  },

  /** Retry button inside the blocking overlay. */
  async retryImmediateUpdate() {
    const plugin = this._plugin;
    if (!plugin) return;
    try {
      await plugin.performImmediateUpdate();
      const info = await plugin.getAppUpdateInfo();
      if (info.updateAvailability !== 2) {
        const el = document.getElementById('force-update-overlay');
        if (el) el.style.display = 'none';
      }
    } catch (e) {
      console.warn('[AppUpdate] Retry cancelled/failed:', e);
      // Overlay stays visible — player must complete the update to proceed.
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
window.appUpdateRetry = () => AppUpdate.retryImmediateUpdate();