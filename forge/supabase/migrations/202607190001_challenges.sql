create table if not exists public.challenges (
  code text primary key,
  creator_name text not null,
  creator_user_id text,
  topic text not null,
  mode text not null,
  time_limit_ms int not null,
  questions jsonb not null,
  creator_score int not null,
  creator_correct_answers int not null,
  created_at double precision not null,
  expires_at double precision not null,
  challenger_name text,
  challenger_user_id text,
  challenger_score int,
  challenger_correct_answers int,
  completed_at double precision
);

alter table public.challenges enable row level security;

-- Public, no-auth read/write — challenges carry no economy stakes and no
-- private data, same trust model as the existing public leaderboard
-- table. The /complete endpoint's completed_at=is.null filter (not RLS)
-- is what actually enforces one-shot-per-challenge, atomically, at the
-- database level.
create policy "challenges_public_all" on public.challenges
  for all
  using (true)
  with check (true);