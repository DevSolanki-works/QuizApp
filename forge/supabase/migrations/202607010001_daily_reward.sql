-- Daily login reward tracking
-- last_reward_date : ISO date string of last claimed reward (YYYY-MM-DD)
-- reward_day       : which day in the 7-day cycle was last claimed (1-7)
alter table public.leaderboard
  add column if not exists last_reward_date text default '',
  add column if not exists reward_day       int  default 0;