/**
 * appleauth.js — Sign in with Apple wrapper for Forge (Guideline 4.8).
 *
 * Native iOS only — Apple's own plugin has no meaningful web/Android
 * implementation and Guideline 4.8 only applies to the App Store build.
 * Mirrors the shape of the Google Sign-In wrappers already in index.html
 * so the two flows are easy to compare/maintain side by side.
 */

const AppleAuth = {
  get _plugin() {
    return window.Capacitor?.Plugins?.SignInWithApple || null;
  },

  isAvailable() {
    return !!(
      window.Capacitor?.isNativePlatform?.() &&
      document.documentElement.dataset.forgeOs === 'ios' &&
      this._plugin
    );
  },

  /** Cryptographically random raw nonce, hex-encoded. */
  _randomNonce(len = 32) {
    const bytes = new Uint8Array(len);
    crypto.getRandomValues(bytes);
    return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
  },

  /** SHA-256 hash of a string, hex-encoded — what Apple's nonce param expects. */
  async _sha256Hex(input) {
    const data = new TextEncoder().encode(input);
    const digest = await crypto.subtle.digest('SHA-256', data);
    return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, '0')).join('');
  },

  /**
   * Runs the native Apple sign-in sheet and returns everything the caller
   * needs to complete a Supabase signInWithIdToken() exchange.
   * Throws on cancel/failure — callers should catch and show a toast,
   * same pattern as nativeGoogleSignIn().
   */
  async signIn() {
    if (!this.isAvailable()) {
      throw new Error('Sign in with Apple is only available on iOS.');
    }
    const rawNonce = this._randomNonce();
    const hashedNonce = await this._sha256Hex(rawNonce);

    const result = await this._plugin.authorize({
      clientId: 'com.devsolanki.forge',
      scopes: 'email name',
      nonce: hashedNonce,
    });

    const identityToken = result?.response?.identityToken || result?.identityToken;
    if (!identityToken) {
      throw new Error('Apple Sign-In returned no identity token.');
    }

    // Apple only ever returns the name/email on the FIRST authorization
    // for a given app — subsequent sign-ins omit them entirely. Capture
    // whatever is present now; later sign-ins will just reuse whatever
    // display name Supabase already has stored for this account.
    const r = result?.response || result || {};
    const givenName  = r.givenName  || '';
    const familyName = r.familyName || '';
    const fullName   = [givenName, familyName].filter(Boolean).join(' ').trim();

    return {
      identityToken,
      rawNonce,
      email: r.email || '',
      fullName,
    };
  },
};

window.AppleAuth = AppleAuth;