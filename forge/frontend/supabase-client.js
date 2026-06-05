/**
 * supabase-client.js — Shared Supabase connection for Forge
 *
 * Uses the lightweight REST+realtime client loaded from CDN.
 * The anon key is safe here — Row Level Security on the database
 * ensures it can only read public data and write its own rows.
 *
 * HOW TO USE FROM ANY SCREEN:
 *   const { data, error } = await Supabase.from('leaderboard').select('*');
 */

const SUPABASE_URL = 'https://ffstsbwkianjcjpqvmtv.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZmc3RzYndraWFuamNqcHF2bXR2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA1NTczMzYsImV4cCI6MjA5NjEzMzMzNn0.G04L8E8TD_C8GWyEBXf5eBWjvcIXXlF8WtlEVkmBhwo';

// window.Supabase is set by the CDN script loaded in index.html.
// This module just re-exports the configured client as a global.
function _initSupabase() {
  if (window._forgeSupabase) return window._forgeSupabase;
  if (!window.supabase) {
    console.warn('[Supabase] SDK not loaded yet — ensure CDN script is in index.html');
    return null;
  }
  window._forgeSupabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
  return window._forgeSupabase;
}

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Upsert (insert-or-update) a player's coins and trophies.
 * Called at the end of every game from the GAME_OVER handler.
 * Safe to call multiple times — always updates, never duplicates.
 *
 * @param {string} googleId   - The player's Google sub (unique ID)
 * @param {string} name       - Display name shown on leaderboard
 * @param {number} coins      - Current coin balance
 * @param {number} trophies   - Current trophy count
 */
async function lbUpsertPlayer(googleId, name, coins, trophies) {
  const db = _initSupabase();
  if (!db) return;
  const { error } = await db.from('leaderboard').upsert({
    google_id:    googleId,
    display_name: name,
    coins:        Number(coins)    || 0,
    trophies:     Number(trophies) || 0,
    updated_at:   new Date().toISOString(),
  }, { onConflict: 'google_id' });
  if (error) console.error('[Supabase] Leaderboard upsert failed:', error.message);
}

/**
 * Fetch the top N players sorted by a given column.
 * Returns an array of row objects, or [] on error.
 *
 * @param {'coins'|'trophies'} column - Sort column
 * @param {number} limit              - Max rows to return
 */
async function lbFetch(column = 'coins', limit = 50) {
  const db = _initSupabase();
  if (!db) return [];
  const { data, error } = await db
    .from('leaderboard')
    .select('display_name, coins, trophies, updated_at')
    .order(column, { ascending: false })
    .limit(limit);
  if (error) { console.error('[Supabase] Leaderboard fetch failed:', error.message); return []; }
  return data || [];
}

/**
 * Fetch the donor leaderboard (approved donations only, summed per person).
 * Returns an array sorted by total_donated desc.
 */
async function lbFetchDonors(limit = 50) {
  const db = _initSupabase();
  if (!db) return [];
  const { data, error } = await db
    .from('donor_leaderboard')
    .select('display_name, total_donated, donation_count, last_donated_at')
    .limit(limit);
  if (error) { console.error('[Supabase] Donor fetch failed:', error.message); return []; }
  return data || [];
}

/**
 * Submit a donation claim for manual verification.
 * Status starts as 'pending' — you approve in the Supabase dashboard.
 *
 * @param {string} displayName - Claimant's in-game name
 * @param {string} googleId    - Their Google ID (optional but links to profile)
 * @param {number} amountInr   - Amount they claim to have paid
 * @param {string} upiTxnId    - UPI / GPay reference number
 */
async function donationSubmit(displayName, googleId, amountInr, upiTxnId) {
  const db = _initSupabase();
  if (!db) throw new Error('Supabase not available');
  const { error } = await db.from('donations').insert({
    display_name: displayName,
    google_id:    googleId || null,
    amount_inr:   Number(amountInr),
    upi_txn_id:   upiTxnId.trim(),
  });
  if (error) {
    // Unique constraint on upi_txn_id catches duplicate submissions
    if (error.code === '23505') throw new Error('DUPLICATE');
    throw new Error(error.message);
  }
}

// Expose globally so all screen files can call them without imports
window.lbUpsertPlayer  = lbUpsertPlayer;
window.lbFetch         = lbFetch;
window.lbFetchDonors   = lbFetchDonors;
window.donationSubmit  = donationSubmit;
window._initSupabase   = _initSupabase;