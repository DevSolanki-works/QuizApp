-- Duel Phase 1 (push follow-up): one FCM device token per signed-in user.
-- Latest-token-wins model — if someone signs in on a second device, the
-- newest token overwrites the old one. Good enough for now; multi-device
-- fan-out is a future upgrade, not needed for the current single-device
-- Challenge notification use case.
create table if not exists public.push_tokens (
  user_id    text primary key,
  fcm_token  text not null,
  updated_at timestamptz not null default now()
);

alter table public.push_tokens enable row level security;

-- Same public-anon trust model as challenges.py: gated by server-side
-- Google token ownership checks at the API layer, not by RLS.
create policy "push_tokens_public_all" on public.push_tokens
  for all
  using (true)
  with check (true);