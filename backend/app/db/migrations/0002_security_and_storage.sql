-- All data access goes through the FastAPI backend, which connects as the table owner.
-- Enable RLS on every table with no policies and revoke Data API roles, so the
-- publishable key used by the frontend can never read or write these tables directly.

do $$
declare
    t record;
begin
    for t in select tablename from pg_tables where schemaname = current_schema() loop
        execute format('alter table %I enable row level security', t.tablename);
    end loop;

    if exists (select 1 from pg_roles where rolname = 'anon')
       and exists (select 1 from pg_roles where rolname = 'authenticated') then
        execute format('revoke all on all tables in schema %I from anon, authenticated', current_schema());
        execute format('revoke all on all sequences in schema %I from anon, authenticated', current_schema());
        execute format('revoke all on all functions in schema %I from anon, authenticated', current_schema());
        execute format('alter default privileges in schema %I revoke all on tables from anon, authenticated', current_schema());
        execute format('alter default privileges in schema %I revoke all on sequences from anon, authenticated', current_schema());
        execute format('alter default privileges in schema %I revoke all on functions from anon, authenticated', current_schema());
    end if;
end;
$$;

-- Private storage buckets (Supabase only; skipped on plain PostgreSQL used for tests).
do $$
begin
    if to_regclass('storage.buckets') is not null then
        insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
        values
            ('student-photos', 'student-photos', false, 5242880,
                array['image/jpeg', 'image/png', 'image/webp']),
            ('id-cards', 'id-cards', false, 5242880, array['application/pdf']),
            ('receipts', 'receipts', false, 5242880, array['application/pdf']),
            ('academy-assets', 'academy-assets', false, 10485760,
                array['image/jpeg', 'image/png', 'image/webp'])
        on conflict (id) do nothing;
    end if;
end;
$$;
