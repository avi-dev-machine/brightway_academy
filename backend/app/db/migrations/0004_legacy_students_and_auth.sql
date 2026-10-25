-- Migration 0004: Support for legacy student import (nullable id_no), program tag,
-- clean monthly fee history table, and local ID+passcode credentials.

-- 1. Make student id_no nullable for rows that have no student ID yet
alter table students drop constraint if exists students_id_no_not_blank;
alter table students add constraint students_id_no_not_blank check (id_no is null or length(btrim(id_no)) > 0);
alter table students alter column id_no drop not null;

-- 2. New columns on students
alter table students add column if not exists program text;
alter table students add constraint students_program_check check (program is null or program in ('CERTIFICATE', 'NON_CERTIFICATE'));
alter table students add column if not exists monthly_fee_paise bigint;
alter table students add column if not exists fee_notes text;
alter table students add column if not exists initial_passcode text;
alter table students add column if not exists issues jsonb not null default '[]'::jsonb;
create index if not exists students_program_idx on students (program);

-- 3. Monthly fees breakdown table for organized historical & active fees
create table if not exists student_monthly_fees (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references students (id) on delete cascade,
    period date not null,
    period_label text not null,
    amount_paise bigint,
    status text not null,
    paid_on date,
    raw_entry text,
    note text,
    pending_paise bigint,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint student_monthly_fees_unique_period unique (student_id, period)
);
create index if not exists student_monthly_fees_student_idx on student_monthly_fees (student_id);
create index if not exists student_monthly_fees_period_idx on student_monthly_fees (period);

-- 4. User profile enhancements for ID+Passcode login (admin BWADMIN & student IDs)
alter table user_profiles add column if not exists identifier text;
create unique index if not exists user_profiles_identifier_lower_key on user_profiles (lower(identifier)) where identifier is not null;
alter table user_profiles add column if not exists password_hash text;

-- Triggers for student_monthly_fees
create trigger student_monthly_fees_set_updated_at before update on student_monthly_fees
    for each row execute function set_updated_at();

-- Enable RLS
alter table student_monthly_fees enable row level security;
