-- Duel Phase 1: daily sweep of expired challenge rows.
-- Supabase's free tier includes pg_cron — no external infra needed.
-- Runs once daily; deleting a few thousand small rows is instant, so
-- this schedule is intentionally generous, not tight.

create extension if not exists pg_cron;

select cron.schedule(
  'delete-expired-challenges',
  '0 3 * * *',  -- 3 AM UTC daily
  $$ delete from public.challenges where expires_at < extract(epoch from now()) $$
);