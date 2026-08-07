-- Fixes the "leaderboard shows blank list, but my own row/rank still
-- updates" bug: the existing policy set (not shown in a prior migration
-- file, predates the tracked migrations) apparently permits row-scoped
-- upserts but never explicitly granted public SELECT across ALL rows,
-- which is required for the ranked-list queries in leaderboard.html.
-- Safe/non-destructive: only ADDS a read policy, does not touch any
-- existing write policy.
alter table public.leaderboard enable row level security;

drop policy if exists "leaderboard_public_read" on public.leaderboard;
create policy "leaderboard_public_read" on public.leaderboard
  for select
  using (true);