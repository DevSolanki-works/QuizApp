/**
 * push.js — Firebase Cloud Messaging wrapper for Forge (Duel Phase 1
 * push follow-up).
 *
 * WHY A SEPARATE FILE FROM analytics.js:
 *   Both use @capacitor-firebase/*, but Analytics is fire-and-forget
 *   tracking with no user-facing behavior. Push involves a real OS
 *   permission prompt and a token that must be registered with the
 *   backend and re-synced on sign-in — different lifecycle, kept
 *   separate for clarity.
 *
 * ⚠️ VERIFY BEFORE RELYING ON THIS:
 *   Method/event names below match @capacitor-firebase/messaging's
 *   documented API as of writing — confirm against
 *   node_modules/@capacitor-firebase/messaging/dist/esm/definitions.d.ts
 *   after `npm install` before trusting this in production, same as
 *   admob.js and analytics.js already note.
 */

const Push = {
  _initialized: false,
  _listenersBound: false,

  get _plugin() {
    return window.Capacitor?.Plugins?.FirebaseMessaging || null;
  },

  /**
   * Request notification permission (if not already granted/denied) and
   * register the resulting device token with the backend. Safe to call
   * multiple times — no-ops if already initialized this session.
   *
   * Call this right after a successful sign-in, since the token is tied
   * to State.user.id server-side.
   */
  async initAndRegister() {
    const plugin = this._plugin;
    if (!plugin || !window.Capacitor?.isNativePlatform?.()) return;
    if (!State.user?.id) return;

    try {
      // Explicitly create the channel referenced by AndroidManifest.xml's
      // default_notification_channel_id. Some OEM Android builds (MIUI,
      // One UI, ColorOS) silently drop background/killed-app notification
      // delivery when a message references a channel that was never
      // actually created on-device — this ensures it exists before any
      // message can arrive.
      if (plugin.createChannel) {
        await plugin.createChannel({
          id: 'forge_challenges',
          name: 'Challenge Results',
          description: 'Notifies you when a friend completes your Forge challenge',
          importance: 4, // IMPORTANCE_HIGH — required for heads-up/tray display
          visibility: 1,
        }).catch(() => {}); // no-op if already exists or unsupported
      }

      const { receive } = await plugin.checkPermissions();
      if (receive !== 'granted') {
        const result = await plugin.requestPermissions();
        if (result.receive !== 'granted') {
          console.log('[Push] Permission denied — challenge completion notifications will not be delivered.');
          return;
        }
      }

      const { token } = await plugin.getToken();
      if (!token) return;

      await this._registerToken(token);
      this._bindListeners();
      this._initialized = true;
    } catch (e) {
      console.warn('[Push] Init/registration failed (non-fatal):', e);
    }
  },

  async _registerToken(token) {
    const credential = State.user?._credential;
    if (!credential || !State.user?.id) return;
    try {
      const r = await fetch(`${API_BASE}/push/register-token`, {
        method : 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${credential}` },
        body   : JSON.stringify({ user_id: State.user.id, fcm_token: token }),
      });
      if (!r.ok) throw new Error(await r.text());
    } catch (e) {
      console.warn('[Push] Token registration failed (non-fatal):', e);
    }
  },

  /** Bind token-refresh and notification-tap listeners once per app session. */
  _bindListeners() {
    const plugin = this._plugin;
    if (!plugin || this._listenersBound) return;
    this._listenersBound = true;

    // Token can rotate at any time (app reinstall, cleared data, etc.) —
    // re-register whenever that happens.
    plugin.addListener('tokenReceived', (event) => {
      if (event?.token) this._registerToken(event.token);
    });

    // User tapped the notification (app was backgrounded/closed).
    plugin.addListener('notificationActionPerformed', (event) => {
      const code = event?.notification?.data?.challenge_code;
      if (code) this._openChallengeResult(code);
    });

    // Notification arrived while the app was already open/foregrounded —
    // show it as a toast instead of relying on the OS tray, consistent
    // with how the rest of the app surfaces in-session events.
    plugin.addListener('notificationReceived', (event) => {
      const notif = event?.notification;
      if (notif?.body && typeof Toast !== 'undefined') {
        Toast.info(notif.body, 6000);
      }
    });
  },

  _openChallengeResult(code) {
    // Reuses the exact same "already completed" screen challenge.html
    // renders for anyone reopening a finished challenge link — no new
    // UI needed, this is just an alternate entry point into it.
    State._challengeCode = code;
    if (typeof goTo === 'function') goTo('challenge');
  },
};

window.Push = Push;