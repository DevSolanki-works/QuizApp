alter table public.leaderboard
  add column if not exists tickets_today int default 3,
  add column if not exists ad_tickets_used_today int default 0,
  add column if not exists last_ticket_date text default '';
