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
 * @param {object} tickets    - Optional file-backed generation ticket state
 */
async function lbUpsertPlayer(googleId, name, coins, trophies, tickets = null) {
  const db = _initSupabase();
  if (!db) throw new Error('Supabase not available');
  const coinValue = Number(coins);
  const trophyValue = Number(trophies);
  if (!Number.isFinite(coinValue) || !Number.isFinite(trophyValue)) {
    throw new Error('Refusing to upsert invalid economy values');
  }
  const payload = {
      google_id:        State.user.id,
      display_name:     State.user.name || 'PLAYER',
      last_reward_date: today,
      reward_day:       day,
      coins:            baseCoins + coins,
      trophies:         baseTrophies,
      updated_at:       new Date().toISOString(),
    };
    if (day === 7) {
      payload.reward_cycle_completed = true;
    }
  if (tickets) {
    payload.tickets_today = Number(tickets.tickets_today) || 0;
    payload.ad_tickets_used_today = Number(tickets.ad_tickets_used_today) || 0;
    payload.last_ticket_date = tickets.last_ticket_date || '';
  }
  let { error } = await db.from('leaderboard').upsert(payload, { onConflict: 'google_id' });
  // Ticket mirror columns may not exist until the Supabase migration is applied.
  if (error && tickets && /column .* does not exist/i.test(error.message || '')) {
    delete payload.tickets_today;
    delete payload.ad_tickets_used_today;
    delete payload.last_ticket_date;
    ({ error } = await db.from('leaderboard').upsert(payload, { onConflict: 'google_id' }));
  }
  if (error) throw new Error(error.message || 'Leaderboard upsert failed');
  return true;
}

/**
 * Fetch a single player's profile from the leaderboard.
 * Used on page load to sync coins/trophies across devices.
 *
 * @param {string} googleId - The player's unique Google ID
 */
async function lbFetchProfile(googleId) {
  const db = _initSupabase();
  if (!db) return null;

  // Core economy columns — always required for sign-in and gameplay sync.
  const { data, error } = await db
    .from('leaderboard')
    .select('coins, trophies, display_name, last_reward_date, reward_day')
    .eq('google_id', googleId)
    .single();

  if (error) {
    if (error.code !== 'PGRST116') { // PGRST116 is "no rows found"
      console.error('[Supabase] Profile fetch failed:', error.message);
    }
    return null;
  }

  // Ticket mirror columns are optional until migration 202606300001 is applied.
  const { data: ticketRow, error: ticketErr } = await db
    .from('leaderboard')
    .select('tickets_today, ad_tickets_used_today, last_ticket_date, reward_cycle_completed')
    .eq('google_id', googleId)
    .maybeSingle();
  if (!ticketErr && ticketRow) Object.assign(data, ticketRow);

  return data;
}

/**
 * Permanently delete a player's row from the Supabase leaderboard mirror.
 * Called as part of full account deletion, after the backend file-backed
 * profile (coins/trophies/tickets) has already been removed.
 *
 * @param {string} googleId - The player's unique Google ID
 */
async function lbDeleteProfile(googleId) {
  const db = _initSupabase();
  if (!db) throw new Error('Supabase not available');
  const { error } = await db.from('leaderboard').delete().eq('google_id', googleId);
  if (error) throw new Error(error.message || 'Leaderboard delete failed');
  return true;
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
/**
 * Call once at the end of every game (any mode).
 * - If last_played_date is today         → streak unchanged (already played today)
 * - If last_played_date was yesterday    → streak + 1
 * - If last_played_date was 2+ days ago  → streak resets to 1
 * - If never played before               → streak = 1
 *
 * Returns the new streak value, or null on error.
 *
 * @param {string} googleId - The player's Google sub
 */
async function lbUpdateDailyStreak(googleId) {
  const db = _initSupabase();
  if (!db || !googleId) return null;

  try {
    const todayStr     = _todayDateString();
    const yesterdayStr = _yesterdayDateString();

    // Fetch current streak state — handle missing row gracefully
    const { data, error } = await db
      .from('leaderboard')
      .select('daily_streak, last_played_date, display_name, coins, trophies')
      .eq('google_id', googleId)
      .maybeSingle();                    // ← maybeSingle() returns null data instead of error when no row

    if (error) {
      console.error('[Streak] Fetch failed:', error.message);
      return null;
    }

    const lastPlayed    = data?.last_played_date || null;
    const currentStreak = Number(data?.daily_streak || 0);

    // Already played today — nothing to do
    if (lastPlayed === todayStr) {
      return currentStreak;
    }

    const newStreak = lastPlayed === yesterdayStr
      ? currentStreak + 1   // consecutive day
      : 1;                  // missed a day or first game ever

    // Build full upsert payload — include all non-null columns
    // so this works even if the row doesn't exist yet
    const payload = {
      google_id:        googleId,
      daily_streak:     newStreak,
      last_played_date: todayStr,
      updated_at:       new Date().toISOString(),
      display_name:     data?.display_name || window.State?.user?.name  || 'PLAYER',
    };
    const coins = Number(data?.coins ?? window.State?.user?.coins);
    const trophies = Number(data?.trophies ?? window.State?.user?.trophies);
    if (Number.isFinite(coins)) payload.coins = coins;
    if (Number.isFinite(trophies)) payload.trophies = trophies;

    const { error: upsertErr } = await db
      .from('leaderboard')
      .upsert(payload, { onConflict: 'google_id' });

    if (upsertErr) {
      console.error('[Streak] Upsert failed:', upsertErr.message);
      return null;
    }

    console.log(`[Streak] Updated to ${newStreak} for ${googleId}`);
    return newStreak;

  } catch (e) {
    console.error('[Streak] Unexpected error:', e);
    return null;
  }
}

/**
 * Fetch the current daily streak for a player without modifying it.
 * Used on home screen load to display the streak badge.
 *
 * @param {string} googleId
 * @returns {number} streak count, or 0 on error/not found
 */
async function lbGetDailyStreak(googleId) {
  const db = _initSupabase();
  if (!db || !googleId) return { streak: 0, lastPlayedDate: null };

  try {
    const { data, error } = await db
      .from('leaderboard')
      .select('daily_streak, last_played_date')
      .eq('google_id', googleId)
      .maybeSingle();

    if (error || !data) return { streak: 0, lastPlayedDate: null };

    // If they haven't played today or yesterday, streak is effectively broken
    // but we still show what's stored — the reset happens on next game end
    return { streak: Number(data.daily_streak || 0), lastPlayedDate: data.last_played_date || null };
  } catch (e) {
    return { streak: 0, lastPlayedDate: null };
  }
}

/** Returns today's date as YYYY-MM-DD in local time */
function _todayDateString() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}

/** Returns yesterday's date as YYYY-MM-DD in local time */
function _yesterdayDateString() {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}

// Expose globally so all screen files can call them without imports
window.lbUpsertPlayer  = lbUpsertPlayer;
window.lbFetchProfile  = lbFetchProfile;
window.lbFetch         = lbFetch;
window.lbFetchDonors   = lbFetchDonors;
window.donationSubmit  = donationSubmit;
window._initSupabase   = _initSupabase;
window.lbUpdateDailyStreak = lbUpdateDailyStreak;
window.lbGetDailyStreak    = lbGetDailyStreak;
window.lbDeleteProfile = lbDeleteProfile;