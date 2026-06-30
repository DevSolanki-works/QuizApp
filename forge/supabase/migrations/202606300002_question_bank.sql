create table if not exists public.question_bank (
  id uuid primary key default gen_random_uuid(),
  category text not null,
  question text not null,
  options jsonb not null,
  correct_idx int not null,
  difficulty text default 'medium',
  times_used int default 0,
  created_at timestamptz default now()
);

create index if not exists idx_question_bank_category
  on public.question_bank (category);

alter table public.question_bank enable row level security;
