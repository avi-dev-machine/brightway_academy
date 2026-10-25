-- Brightway Computer Academy: initial schema.
-- Money is stored as integer paise (bigint). UUID primary keys everywhere.

create or replace function set_updated_at() returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.updated_at := now();
    return new;
end;
$$;

create or replace function prevent_modification() returns trigger
language plpgsql
set search_path = ''
as $$
begin
    raise exception '% on % is not allowed (data preservation rule)', tg_op, tg_table_name;
end;
$$;

-- ---------------------------------------------------------------- settings
create table app_settings (
    key text primary key,
    value jsonb not null,
    updated_by uuid,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------- courses
create table courses (
    id uuid primary key default gen_random_uuid(),
    code text not null,
    name text not null,
    description text,
    duration_months integer,
    default_fee_paise bigint,
    active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint courses_code_key unique (code),
    constraint courses_code_format check (code ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'),
    constraint courses_name_not_blank check (length(btrim(name)) > 0),
    constraint courses_duration_positive check (duration_months is null or duration_months > 0),
    constraint courses_fee_non_negative check (default_fee_paise is null or default_fee_paise >= 0)
);
create unique index courses_name_lower_key on courses (lower(name));

-- ---------------------------------------------------------------- teachers
create table teachers (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    phone text,
    email text,
    active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint teachers_name_not_blank check (length(btrim(name)) > 0)
);
create unique index teachers_email_lower_key on teachers (lower(email)) where email is not null;

-- ---------------------------------------------------------------- CSV import jobs
create table import_jobs (
    id uuid primary key default gen_random_uuid(),
    filename text not null,
    file_sha256 text not null,
    status text not null default 'PREVIEWED',
    total_rows integer not null default 0,
    summary jsonb not null default '{}'::jsonb,
    error_policy text,
    created_by uuid,
    confirmed_by uuid,
    confirmed_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint import_jobs_status_check check (status in ('PREVIEWED', 'COMPLETED', 'FAILED')),
    constraint import_jobs_policy_check check (
        error_policy is null or error_policy in ('STRICT', 'SKIP_ERRORS'))
);
create index import_jobs_sha_idx on import_jobs (file_sha256);

-- ---------------------------------------------------------------- students
create sequence student_id_seq;

create table students (
    id uuid primary key default gen_random_uuid(),
    id_no text not null,
    name text not null,
    guardian_name text,
    address text,
    contact text,
    contact_e164 text,
    course_id uuid references courses (id),
    legacy_course text,
    admission_date date,
    photo_path text,
    id_card_path text,
    status text not null default 'active',
    import_job_id uuid references import_jobs (id),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint students_id_no_key unique (id_no),
    constraint students_id_no_not_blank check (length(btrim(id_no)) > 0),
    constraint students_name_not_blank check (length(btrim(name)) > 0),
    constraint students_status_check check (status in ('active', 'inactive'))
);
-- ID numbers are also unique ignoring case, so "bca001" cannot sit next to "BCA001".
create unique index students_id_no_lower_key on students (lower(id_no));
create index students_course_idx on students (course_id);
create index students_status_idx on students (status);
create index students_name_lower_idx on students (lower(name));

-- ---------------------------------------------------------------- application users
-- One row per Supabase Auth user allowed into the application. The role lives here
-- (server-controlled), never in user-editable JWT metadata.
create table user_profiles (
    user_id uuid primary key,
    email text,
    role text not null,
    student_id uuid references students (id),
    teacher_id uuid references teachers (id),
    active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint user_profiles_student_id_key unique (student_id),
    constraint user_profiles_teacher_id_key unique (teacher_id),
    constraint user_profiles_role_check check (role in ('ADMIN', 'TEACHER', 'STUDENT')),
    constraint user_profiles_role_link check (
        (role = 'ADMIN' and student_id is null and teacher_id is null)
        or (role = 'TEACHER' and teacher_id is not null and student_id is null)
        or (role = 'STUDENT' and student_id is not null and teacher_id is null))
);

-- ---------------------------------------------------------------- batches
create table batches (
    id uuid primary key default gen_random_uuid(),
    course_id uuid not null references courses (id),
    name text not null,
    teacher_id uuid references teachers (id),
    start_date date,
    end_date date,
    schedule text,
    capacity integer,
    active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint batches_course_name_key unique (course_id, name),
    constraint batches_name_not_blank check (length(btrim(name)) > 0),
    constraint batches_capacity_positive check (capacity is null or capacity > 0),
    constraint batches_dates_check check (
        end_date is null or start_date is null or end_date >= start_date)
);
create index batches_teacher_idx on batches (teacher_id);

create table batch_students (
    batch_id uuid not null references batches (id),
    student_id uuid not null references students (id),
    assigned_by uuid,
    assigned_at timestamptz not null default now(),
    primary key (batch_id, student_id)
);
create index batch_students_student_idx on batch_students (student_id);

-- ---------------------------------------------------------------- fees
create table fee_plans (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    course_id uuid references courses (id),
    plan_type text not null,
    -- MONTHLY / ONE_TIME: amount of each fee. INSTALLMENT: total split across installments.
    amount_paise bigint not null,
    installment_count integer not null default 1,
    active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint fee_plans_type_check check (plan_type in ('MONTHLY', 'INSTALLMENT', 'ONE_TIME')),
    constraint fee_plans_amount_positive check (amount_paise > 0),
    constraint fee_plans_installments_range check (installment_count between 1 and 60),
    constraint fee_plans_one_time_single check (plan_type <> 'ONE_TIME' or installment_count = 1)
);
create unique index fee_plans_name_lower_key on fee_plans (lower(name));

create table fees (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references students (id),
    fee_plan_id uuid references fee_plans (id),
    fee_type text not null,
    title text not null,
    installment_no integer,
    amount_paise bigint not null,
    concession_paise bigint not null default 0,
    paid_paise bigint not null default 0,
    due_date date not null,
    status text not null default 'PENDING',
    concession_reason text,
    cancellation_reason text,
    created_by uuid,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint fees_type_check check (fee_type in ('MONTHLY', 'INSTALLMENT', 'ONE_TIME')),
    constraint fees_status_check check (
        status in ('PENDING', 'PARTIALLY_PAID', 'PAID', 'OVERDUE', 'CANCELLED')),
    constraint fees_amount_positive check (amount_paise > 0),
    constraint fees_concession_range check (
        concession_paise >= 0 and concession_paise <= amount_paise),
    constraint fees_paid_non_negative check (paid_paise >= 0),
    constraint fees_installment_positive check (installment_no is null or installment_no > 0),
    constraint fees_plan_installment_key unique (student_id, fee_plan_id, installment_no)
);
create index fees_student_idx on fees (student_id);
create index fees_status_due_idx on fees (status, due_date);

-- ---------------------------------------------------------------- payments
create table payments (
    id uuid primary key default gen_random_uuid(),
    fee_id uuid not null references fees (id),
    student_id uuid not null references students (id),
    amount_paise bigint not null,
    currency text not null default 'INR',
    provider text not null,
    method text,
    status text not null default 'CREATED',
    provider_order_id text,
    provider_payment_id text,
    idempotency_key text,
    reference text,
    notes text,
    failure_reason text,
    requires_review boolean not null default false,
    review_reason text,
    paid_at timestamptz,
    created_by uuid,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint payments_provider_order_id_key unique (provider_order_id),
    constraint payments_provider_payment_id_key unique (provider_payment_id),
    constraint payments_idempotency_key_key unique (idempotency_key),
    constraint payments_amount_positive check (amount_paise > 0),
    constraint payments_provider_check check (provider in ('RAZORPAY', 'MOCK', 'OFFLINE')),
    constraint payments_status_check check (
        status in ('CREATED', 'PENDING', 'SUCCESS', 'FAILED', 'REFUNDED')),
    constraint payments_success_has_paid_at check (status <> 'SUCCESS' or paid_at is not null)
);
create index payments_fee_idx on payments (fee_id);
create index payments_student_idx on payments (student_id);
create index payments_status_created_idx on payments (status, created_at);

-- Every provider webhook delivery, deduplicated by the provider's event id.
create table payment_events (
    id uuid primary key default gen_random_uuid(),
    provider text not null,
    event_id text not null,
    event_type text not null,
    payload jsonb not null,
    status text not null default 'RECEIVED',
    result text,
    received_at timestamptz not null default now(),
    processed_at timestamptz,
    constraint payment_events_provider_event_key unique (provider, event_id),
    constraint payment_events_status_check check (
        status in ('RECEIVED', 'PROCESSED', 'IGNORED', 'FAILED'))
);

-- ---------------------------------------------------------------- receipts
create sequence receipt_number_seq;

create table receipts (
    id uuid primary key default gen_random_uuid(),
    receipt_number text not null,
    payment_id uuid not null references payments (id),
    student_id uuid not null references students (id),
    fee_id uuid not null references fees (id),
    amount_paise bigint not null,
    issued_at timestamptz not null default now(),
    pdf_path text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint receipts_receipt_number_key unique (receipt_number),
    constraint receipts_payment_id_key unique (payment_id),
    constraint receipts_amount_positive check (amount_paise > 0)
);
create index receipts_student_idx on receipts (student_id);

-- ---------------------------------------------------------------- attendance
create table attendance (
    id uuid primary key default gen_random_uuid(),
    batch_id uuid not null references batches (id),
    student_id uuid not null references students (id),
    attendance_date date not null,
    status text not null,
    remarks text,
    marked_by uuid,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint attendance_batch_student_date_key unique (batch_id, student_id, attendance_date),
    constraint attendance_status_check check (status in ('PRESENT', 'ABSENT', 'LATE', 'EXCUSED'))
);
create index attendance_student_date_idx on attendance (student_id, attendance_date);
create index attendance_batch_date_idx on attendance (batch_id, attendance_date);

-- ---------------------------------------------------------------- notifications
create table notifications (
    id uuid primary key default gen_random_uuid(),
    student_id uuid references students (id),
    fee_id uuid references fees (id),
    payment_id uuid references payments (id),
    channel text not null,
    recipient text not null,
    template text not null,
    payload jsonb not null default '{}'::jsonb,
    status text not null default 'QUEUED',
    provider_message_id text,
    attempts integer not null default 0,
    max_attempts integer not null default 3,
    next_attempt_at timestamptz not null default now(),
    last_error text,
    dedupe_key text,
    sent_at timestamptz,
    delivered_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint notifications_dedupe_key_key unique (dedupe_key),
    constraint notifications_channel_check check (channel in ('WHATSAPP', 'SMS', 'EMAIL')),
    constraint notifications_status_check check (
        status in ('QUEUED', 'SENDING', 'SENT', 'DELIVERED', 'FAILED')),
    constraint notifications_attempts_check check (attempts >= 0 and max_attempts > 0)
);
create index notifications_queue_idx on notifications (next_attempt_at) where status = 'QUEUED';
create index notifications_student_idx on notifications (student_id);
create unique index notifications_provider_message_key
    on notifications (channel, provider_message_id) where provider_message_id is not null;

-- Reminder history. The unique key is the reminder deduplication key.
create table fee_reminders (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references students (id),
    fee_id uuid not null references fees (id),
    reminder_stage text not null,
    reminder_date date not null,
    created_at timestamptz not null default now(),
    constraint fee_reminders_dedupe_key unique (student_id, fee_id, reminder_stage, reminder_date)
);

-- ---------------------------------------------------------------- ID cards
create table id_card_templates (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    layout jsonb not null,
    is_default boolean not null default false,
    active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint id_card_templates_name_key unique (name)
);
create unique index id_card_templates_single_default on id_card_templates (is_default) where is_default;

create table id_cards (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references students (id),
    template_id uuid not null references id_card_templates (id),
    file_path text not null,
    generated_by uuid,
    generated_at timestamptz not null default now()
);
create index id_cards_student_idx on id_cards (student_id, generated_at desc);

-- ---------------------------------------------------------------- CSV import rows
create table import_job_rows (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references import_jobs (id),
    row_number integer not null,
    raw jsonb not null,
    normalized jsonb,
    status text not null,
    messages jsonb not null default '[]'::jsonb,
    outcome text,
    student_id uuid references students (id),
    constraint import_job_rows_job_row_key unique (job_id, row_number),
    constraint import_job_rows_status_check check (
        status in ('VALID', 'WARNING', 'ERROR', 'DUPLICATE', 'EXISTS')),
    constraint import_job_rows_outcome_check check (
        outcome is null or outcome in ('IMPORTED', 'SKIPPED'))
);

-- ---------------------------------------------------------------- audit log
create table audit_logs (
    id uuid primary key default gen_random_uuid(),
    actor_user_id uuid,
    action text not null,
    entity_type text not null,
    entity_id text,
    before jsonb,
    after jsonb,
    request_id text,
    created_at timestamptz not null default now()
);
create index audit_logs_entity_idx on audit_logs (entity_type, entity_id);
create index audit_logs_created_idx on audit_logs (created_at desc);
create index audit_logs_actor_idx on audit_logs (actor_user_id);

-- ---------------------------------------------------------------- triggers
do $$
declare
    t text;
begin
    foreach t in array array[
        'app_settings', 'courses', 'teachers', 'import_jobs', 'students', 'user_profiles',
        'batches', 'fee_plans', 'fees', 'payments', 'receipts', 'attendance',
        'notifications', 'id_card_templates'
    ] loop
        execute format(
            'create trigger %I before update on %I for each row execute function set_updated_at()',
            t || '_set_updated_at', t);
    end loop;
end;
$$;

-- Data preservation: students, fees, payments and receipts are never hard-deleted,
-- and the audit log is append-only.
create trigger students_no_delete before delete on students
    for each row execute function prevent_modification();
create trigger fees_no_delete before delete on fees
    for each row execute function prevent_modification();
create trigger payments_no_delete before delete on payments
    for each row execute function prevent_modification();
create trigger receipts_no_delete before delete on receipts
    for each row execute function prevent_modification();
create trigger audit_logs_append_only before update or delete on audit_logs
    for each row execute function prevent_modification();
